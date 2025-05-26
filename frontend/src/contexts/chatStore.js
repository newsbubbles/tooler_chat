import { create } from 'zustand';
import api from '../services/api';

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
      const url = agentId ? `/api/chat/sessions?agent_id=${agentId}` : '/api/chat/sessions';
      const response = await api.get(url);
      set({ sessions: response.data, isLoading: false });
    } catch (error) {
      set({
        error: error.response?.data?.detail || 'Failed to load chat sessions',
        isLoading: false
      });
    }
  },

  // Load a specific chat session with messages
  loadSession: async (sessionUuid) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.get(`/api/chat/sessions/${sessionUuid}`);
      set({
        selectedSession: response.data,
        messages: response.data.messages,
        isLoading: false
      });
      return response.data;
    } catch (error) {
      set({
        error: error.response?.data?.detail || 'Failed to load chat session',
        isLoading: false
      });
      return null;
    }
  },

  // Create a new chat session
  createSession: async (sessionData) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.post('/api/chat/sessions', sessionData);
      set(state => ({
        sessions: [...state.sessions, response.data],
        selectedSession: response.data,
        messages: [],
        isLoading: false
      }));
      return response.data;
    } catch (error) {
      set({
        error: error.response?.data?.detail || 'Failed to create chat session',
        isLoading: false
      });
      return null;
    }
  },

  // Update a chat session
  updateSession: async (sessionUuid, sessionData) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.put(`/api/chat/sessions/${sessionUuid}`, sessionData);
      set(state => ({
        sessions: state.sessions.map(session => 
          session.uuid === sessionUuid ? response.data : session
        ),
        selectedSession: state.selectedSession?.uuid === sessionUuid ? 
          response.data : state.selectedSession,
        isLoading: false
      }));
      return response.data;
    } catch (error) {
      set({
        error: error.response?.data?.detail || 'Failed to update chat session',
        isLoading: false
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
      const updatedSessions = get().sessions.filter(session => session.uuid !== sessionUuid);
      set(state => ({
        sessions: updatedSessions,
        selectedSession: state.selectedSession?.uuid === sessionUuid ? null : state.selectedSession,
        messages: state.selectedSession?.uuid === sessionUuid ? [] : state.messages,
        isLoading: false
      }));
      return true;
    } catch (error) {
      set({
        error: error.response?.data?.detail || 'Failed to delete chat session',
        isLoading: false
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

    try {
      // Add user message to UI immediately
      const userMessage = {
        uuid: `temp-${Date.now()}`,
        role: 'user',
        content,
        timestamp: new Date().toISOString()
      };

      set(state => ({
        messages: [...state.messages, userMessage]
      }));

      // Initialize model message with empty content
      const modelMessage = {
        uuid: `temp-response-${Date.now()}`,
        role: 'model',
        content: '',
        timestamp: new Date().toISOString()
      };

      set(state => ({
        messages: [...state.messages, modelMessage]
      }));

      // Stream the response
      const response = await fetch(`/api/chat/sessions/${sessionUuid}/messages/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth-storage')?.token || ''}`
        },
        body: JSON.stringify({ content })
      });

      if (!response.ok) {
        throw new Error(`Error: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let partialMessage = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        // Decode and concatenate the chunks
        const chunk = decoder.decode(value, { stream: true });
        partialMessage += chunk;

        // Process complete messages (delimited by newlines)
        const lines = partialMessage.split('\n');
        partialMessage = lines.pop() || ''; // Keep the last incomplete line for next iteration

        for (const line of lines) {
          if (line.trim()) {
            try {
              const messageData = JSON.parse(line);
              
              // Update the model's message content
              set(state => ({
                messages: state.messages.map(msg => {
                  if (msg.role === 'model' && msg.uuid === modelMessage.uuid) {
                    return { ...msg, content: messageData.content };
                  }
                  return msg;
                })
              }));
            } catch (e) {
              console.error('Error parsing message:', e, line);
            }
          }
        }
      }

      // Update the session in the sessions list with the updated timestamp
      const updatedSession = { ...get().selectedSession, updated_at: new Date().toISOString() };
      set(state => ({
        sessions: state.sessions.map(session => 
          session.uuid === sessionUuid ? updatedSession : session
        ),
        selectedSession: updatedSession,
        isLoading: false
      }));

      return true;
    } catch (error) {
      set({
        error: error.message || 'Failed to send message',
        isLoading: false
      });
      return false;
    }
  },
}));
