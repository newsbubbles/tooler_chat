import { create } from "zustand";
import api from "../services/api";

export const useChatStore = create((set, get) => ({
  sessions: [],
  selectedSession: null,
  messages: [],
  isLoading: false,
  error: null,

  // Load all chat sessions for the current user or for a specific agent
  loadSessions: async (agentId = null) => {
    set({ isLoading: true, error: null });
    try {
      const url = agentId
        ? `/api/chat/sessions?agent_id=${agentId}`
        : "/api/chat/sessions";
      const response = await api.get(url);
      set({ sessions: response.data, isLoading: false });
    } catch (error) {
      set({
        error: error.response?.data?.detail || "Failed to load chat sessions",
        isLoading: false,
      });
    }
  },

  // Load a specific chat session with messages
  loadSession: async (sessionUuid) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.get(`/api/chat/sessions/${sessionUuid}`);

      // Get current temporary messages
      const currentState = get();
      const temporaryMessages = currentState.messages.filter(
        (msg) => msg.isTemporary
      );

      // If we have temporary messages, merge them with server messages
      let finalMessages = response.data.messages;
      if (temporaryMessages.length > 0) {
        // Keep temporary messages and only add new server messages
        const serverMessageIds = new Set(
          response.data.messages.map((msg) => msg.uuid)
        );
        const tempMessagesToKeep = temporaryMessages.filter((msg) => {
          // Keep temporary messages that don't have corresponding server messages
          return !serverMessageIds.has(
            msg.uuid.replace("temp-user-", "").replace("temp-model-", "")
          );
        });

        // If we have ongoing streaming (temporary model message with content), keep it
        const streamingMessage = temporaryMessages.find(
          (msg) => msg.role === "model" && msg.content && msg.isTemporary
        );

        if (streamingMessage) {
          // Don't override with server data if we're streaming
          console.log("🎭 Preserving streaming message during session load");
          set({
            selectedSession: response.data,
            isLoading: false,
          });
          return response.data;
        } else {
          finalMessages = [...response.data.messages, ...tempMessagesToKeep];
        }
      }

      set({
        selectedSession: response.data,
        messages: finalMessages,
        isLoading: false,
      });
      return response.data;
    } catch (error) {
      set({
        error: error.response?.data?.detail || "Failed to load chat session",
        isLoading: false,
      });
      return null;
    }
  },

  // Create a new chat session
  createSession: async (sessionData) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.post("/api/chat/sessions", sessionData);
      set((state) => ({
        sessions: [...state.sessions, response.data],
        selectedSession: response.data,
        messages: [],
        isLoading: false,
      }));
      return response.data;
    } catch (error) {
      set({
        error: error.response?.data?.detail || "Failed to create chat session",
        isLoading: false,
      });
      return null;
    }
  },

  // Update a chat session
  updateSession: async (sessionUuid, sessionData) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.put(
        `/api/chat/sessions/${sessionUuid}`,
        sessionData
      );
      set((state) => ({
        sessions: state.sessions.map((session) =>
          session.uuid === sessionUuid ? response.data : session
        ),
        selectedSession:
          state.selectedSession?.uuid === sessionUuid
            ? response.data
            : state.selectedSession,
        isLoading: false,
      }));
      return response.data;
    } catch (error) {
      set({
        error: error.response?.data?.detail || "Failed to update chat session",
        isLoading: false,
      });
      return null;
    }
  },

  // Delete a chat session
  deleteSession: async (sessionUuid) => {
    set({ isLoading: true, error: null });
    try {
      await api.delete(`/api/chat/sessions/${sessionUuid}`);
      // Remove the session from the sessions list
      const updatedSessions = get().sessions.filter(
        (session) => session.uuid !== sessionUuid
      );
      set((state) => ({
        sessions: updatedSessions,
        selectedSession:
          state.selectedSession?.uuid === sessionUuid
            ? null
            : state.selectedSession,
        messages:
          state.selectedSession?.uuid === sessionUuid ? [] : state.messages,
        isLoading: false,
      }));
      return true;
    } catch (error) {
      set({
        error: error.response?.data?.detail || "Failed to delete chat session",
        isLoading: false,
      });
      return false;
    }
  },

  // Select a chat session
  selectSession: (session) => {
    if (session) {
      get().loadSession(session.uuid);
    } else {
      set({ selectedSession: null, messages: [] });
    }
  },

  // Send a message and receive streaming response
  sendMessage: async (content, sessionUuid) => {
    if (!sessionUuid || !content.trim()) return;

    set({ isLoading: true, error: null });

    let reader = null;

    try {
      // Create unique identifiers
      const timestamp = Date.now();
      const userMessage = {
        uuid: `temp-user-${timestamp}`,
        role: "user",
        content,
        timestamp: new Date().toISOString(),
        isTemporary: true, // Mark as temporary
      };

      const modelMessage = {
        uuid: `temp-model-${timestamp}`,
        role: "model",
        content: "",
        timestamp: new Date().toISOString(),
        isTemporary: true, // Mark as temporary
      };

      // Add both messages at once
      set((state) => ({
        messages: [...state.messages, userMessage, modelMessage],
      }));

      const authStorage = localStorage.getItem("auth-storage");
      const parsedAuth = JSON.parse(authStorage || "{}");
      const authToken = parsedAuth.state.token;

      const response = await fetch(
        `https://app.xsus.ai/api/chat/sessions/${sessionUuid}/messages/stream`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${authToken}`,
          },
          body: JSON.stringify({ content }),
        }
      );

      if (!response.ok) {
        throw new Error(`Error: ${response.status}`);
      }

      if (!response.body) {
        throw new Error("Response body is null");
      }

      reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let longestContent = ""; // Track the longest/most complete content

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        // Decode the chunk
        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;

        // Process complete lines
        const lines = buffer.split("\n");
        buffer = lines.pop() || ""; // Keep the incomplete line in buffer

        for (const line of lines) {
          if (line.trim()) {
            try {
              const messageData = JSON.parse(line);

              if (messageData.content) {
                let currentContent = messageData.content;

                // Skip if this is just the user's input echoed back
                if (currentContent.trim() === content.trim()) {
                  continue;
                }

                // Remove user input from the beginning if it's there
                if (currentContent.startsWith(content)) {
                  currentContent = currentContent
                    .substring(content.length)
                    .trim();
                }

                // Only update if this content is longer than what we have
                // This ensures we always show the most complete version
                if (currentContent.length > longestContent.length) {
                  longestContent = currentContent;

                  // Update the UI with the longest content so far
                  set((state) => ({
                    messages: state.messages.map((msg) => {
                      if (
                        msg.role === "model" &&
                        msg.uuid === modelMessage.uuid &&
                        msg.isTemporary
                      ) {
                        return { ...msg, content: longestContent };
                      }
                      return msg;
                    }),
                  }));
                }
              }
            } catch (e) {
              console.error("Error parsing streaming chunk:", e, "Line:", line);
            }
          }
        }
      }

      // Process any remaining content in buffer
      if (buffer.trim()) {
        try {
          const messageData = JSON.parse(buffer);
          if (messageData.content) {
            let currentContent = messageData.content;

            if (currentContent.trim() !== content.trim()) {
              if (currentContent.startsWith(content)) {
                currentContent = currentContent
                  .substring(content.length)
                  .trim();
              }

              if (currentContent.length > longestContent.length) {
                longestContent = currentContent;

                set((state) => ({
                  messages: state.messages.map((msg) => {
                    if (
                      msg.role === "model" &&
                      msg.uuid === modelMessage.uuid &&
                      msg.isTemporary
                    ) {
                      return { ...msg, content: longestContent };
                    }
                    return msg;
                  }),
                }));
              }
            }
          }
        } catch (e) {
          console.error("Error parsing final chunk:", e);
        }
      }

      // Streaming completed successfully
      // We'll keep the temporary messages and only replace them when:
      // 1. User navigates away and comes back
      // 2. User manually refreshes
      // 3. A new message is sent
      // This prevents the disappearing message issue
      console.log("🎭 Streaming completed, keeping temporary messages in UI");

      // Note: We don't automatically reload the session here to avoid interrupting streaming
      // The session will be reloaded when the user navigates or refreshes

      // Update the session timestamp
      const updatedSession = {
        ...get().selectedSession,
        updated_at: new Date().toISOString(),
      };

      set((state) => ({
        sessions: state.sessions.map((session) =>
          session.uuid === sessionUuid ? updatedSession : session
        ),
        selectedSession: updatedSession,
        isLoading: false,
      }));

      return true;
    } catch (error) {
      console.error("Streaming error:", error);
      set({
        error: error.message || "Failed to send message",
        isLoading: false,
      });
      return false;
    } finally {
      // Always clean up the reader
      if (reader) {
        try {
          reader.releaseLock();
        } catch (e) {
          console.error("Error releasing reader:", e);
        }
      }
    }
  },
}));
