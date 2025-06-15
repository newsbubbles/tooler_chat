import React, { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Box,
  Paper,
  Typography,
  TextField,
  IconButton,
  CircularProgress,
  Button,
  Divider,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from "@mui/material";
import {
  Send as SendIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
} from "@mui/icons-material";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { materialLight } from "react-syntax-highlighter/dist/esm/styles/prism";
import remarkGfm from "remark-gfm";

import { useChatStore } from "../contexts/chatStore";
import { useAgentsStore } from "../contexts/agentsStore";

export default function Chat() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const messagesEndRef = useRef(null);
  const [message, setMessage] = useState("");
  const [title, setTitle] = useState("");
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [isSendingMessage, setIsSendingMessage] = useState(false); // Add this flag

  const {
    selectedSession,
    messages,
    isLoading,
    loadSession,
    createSession,
    updateSession,
    deleteSession,
    sendMessage,
  } = useChatStore();

  const { selectedAgent } = useAgentsStore();

  // Load session when sessionId changes, but not if we're currently sending a message
  useEffect(() => {
    if (isSendingMessage) {
      console.log("🎭 Skipping session load - currently sending message");
      return; // Don't reload session while sending message
    }

    if (sessionId === "new") {
      // Always handle "new" chat, regardless of temporary messages
      console.log("🎭 Setting up new chat");
      if (selectedAgent) {
        useChatStore.setState({
          selectedSession: null,
          messages: [],
        });
      }
      return;
    }

    // Check if we have any temporary messages (streaming or recently sent)
    // Only for existing sessions, not for new chats
    const hasTemporaryMessages = messages.some((msg) => msg.isTemporary);

    if (hasTemporaryMessages) {
      console.log("🎭 Skipping session load - have temporary messages");
      return;
    }

    if (sessionId && sessionId !== "new") {
      console.log("🎭 Loading session:", sessionId);
      setIsLoadingMessages(true);
      loadSession(sessionId).finally(() => {
        setIsLoadingMessages(false);
      });
    }
  }, [
    sessionId,
    loadSession,
    selectedAgent,
    isSendingMessage,
    messages.length,
  ]); // Add messages.length to dependencies

  // Update title when session changes
  useEffect(() => {
    if (selectedSession) {
      setTitle(selectedSession.title);
    } else if (selectedAgent) {
      setTitle(`New Chat with ${selectedAgent.name}`);
    } else {
      setTitle("Select an agent to start a new chat");
    }
  }, [selectedSession, selectedAgent]);

  // Scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    console.log("🎭 Chat component - messages updated:", messages);
    console.log("🎭 Messages length:", messages.length);
    if (messages.length > 0) {
      console.log("🎭 Last message:", messages[messages.length - 1]);
    }
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!message.trim() || !selectedAgent) return;

    setIsSendingMessage(true); // Set flag to prevent session reload

    let sessionToUse = selectedSession;

    try {
      // Create a new session if needed
      if (!selectedSession) {
        const newSession = await createSession({
          agent_id: selectedAgent.id,
          title:
            message.length > 30 ? `${message.substring(0, 30)}...` : message,
        });

        if (newSession) {
          sessionToUse = newSession;
          // Navigate but don't trigger useEffect yet
          navigate(`/chat/${newSession.uuid}`, { replace: true });
        } else {
          setIsSendingMessage(false);
          return; // Failed to create session
        }
      }

      // Send message
      await sendMessage(message, sessionToUse.uuid);
      setMessage("");
    } finally {
      setIsSendingMessage(false); // Always clear the flag
    }
  };

  const handleTitleUpdate = async () => {
    if (selectedSession && title.trim()) {
      await updateSession(selectedSession.uuid, { title: title.trim() });
    }
    setIsEditingTitle(false);
  };

  const handleDeleteSession = async () => {
    if (selectedSession) {
      await deleteSession(selectedSession.uuid);
      navigate("/chat");
    }
    setDeleteDialogOpen(false);
  };

  const CodeBlock = ({ node, inline, className, children, ...props }) => {
    const match = /language-(\w+)/.exec(className || "");
    return !inline && match ? (
      <SyntaxHighlighter
        style={materialLight}
        language={match[1]}
        PreTag="div"
        {...props}
      >
        {String(children).replace(/\n$/, "")}
      </SyntaxHighlighter>
    ) : (
      <code className={className} {...props}>
        {children}
      </code>
    );
  };

  if (!selectedAgent) {
    return (
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
          p: 4,
        }}
      >
        <Typography variant="h5" gutterBottom>
          Select an agent to start chatting
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Use the sidebar on the left to choose an agent and create a new chat
          session.
        </Typography>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        position: "relative",
      }}
    >
      {/* Chat header */}
      {/* <Paper
        elevation={1}
        sx={{
          p: 2,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderRadius: 0,
          zIndex: 10,
        }}
      >
        {isEditingTitle ? (
          <Box sx={{ display: "flex", alignItems: "center", width: "100%" }}>
            <TextField
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              variant="outlined"
              size="small"
              autoFocus
              fullWidth
            />
            <Button onClick={handleTitleUpdate} sx={{ ml: 1 }}>
              Save
            </Button>
          </Box>
        ) : (
          <Box sx={{ display: "flex", alignItems: "center" }}>
            <Typography variant="h6" sx={{ mr: 1 }}>
              {title}
            </Typography>
            {selectedSession && (
              <IconButton size="small" onClick={() => setIsEditingTitle(true)}>
                <EditIcon fontSize="small" />
              </IconButton>
            )}
          </Box>
        )}

        {selectedSession && (
          <IconButton color="error" onClick={() => setDeleteDialogOpen(true)}>
            <DeleteIcon />
          </IconButton>
        )}
      </Paper> */}

      {/* <Divider /> */}

      {/* Messages container */}
      <Box
        sx={{
          flex: 1,
          overflow: "auto",
          p: 2,
        }}
      >
        {isLoadingMessages ? (
          <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
            <CircularProgress />
          </Box>
        ) : messages.length === 0 ? (
          <Box sx={{ textAlign: "center", p: 4 }}>
            <Typography variant="body1" color="text.secondary">
              No messages yet. Start the conversation!
            </Typography>
          </Box>
        ) : (
          messages.map((msg) => (
            <Box
              key={msg.uuid}
              sx={{
                mb: 2,
                display: "flex",
                flexDirection: "column",
                alignItems: msg.role === "user" ? "flex-end" : "flex-start",
              }}
            >
              <Paper
                elevation={1}
                sx={{
                  p: 2,
                  maxWidth: "80%",
                  borderRadius: 2,
                }}
              >
                <Typography
                  variant="caption"
                  display="block"
                  gutterBottom
                  color="text.secondary"
                >
                  {msg.role === "user" ? "You" : selectedAgent?.name || "Agent"}
                </Typography>
                <Box sx={{ "& pre": { maxWidth: "100%", overflow: "auto" } }}>
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      code: CodeBlock,
                    }}
                  >
                    {msg.content}
                  </ReactMarkdown>
                </Box>
              </Paper>
            </Box>
          ))
        )}
        <div ref={messagesEndRef} />
      </Box>

      {/* Message input */}
      <Box
        sx={{
          p: 3,
        }}
      >
        <Paper
          sx={{
            borderRadius: "16px 16px 27px 27px",
            backgroundColor: "#232323",

            boxShadow: "none",
            p: 2,
          }}
          elevation={0}
        >
          {/* Text input only */}
          <Box
            sx={{
              mb: 1, // Space between text input and icons below
            }}
          >
            <TextField
              fullWidth
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  if (
                    message.trim() &&
                    selectedAgent &&
                    !isLoading &&
                    !isSendingMessage
                  ) {
                    handleSendMessage(e);
                  }
                }
              }}
              placeholder="What can I do for you?"
              variant="standard"
              multiline
              maxRows={4}
              disabled={isLoading || isSendingMessage}
              sx={{
                "& .MuiInputBase-root": {
                  color: "#fff",
                  fontSize: "16px",
                  "&::before": {
                    display: "none",
                  },
                  "&::after": {
                    display: "none",
                  },
                  "&:hover::before": {
                    display: "none",
                  },
                },
                "& .MuiInputBase-input": {
                  padding: "2px 0",
                  "&::placeholder": {
                    color: "#888",
                    opacity: 1,
                  },
                },
              }}
            />
          </Box>

          {/* Icons and send button below the text input */}
          <Box
            component="form"
            onSubmit={handleSendMessage}
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            {/* Left side icons */}
            <Box sx={{ display: "flex", alignItems: "center" }}>
              <IconButton
                size="small"
                sx={{
                  color: "#888",
                  "&:hover": {
                    backgroundColor: "rgba(255, 255, 255, 0.1)",
                  },
                }}
              >
                🎤
              </IconButton>
              <IconButton
                size="small"
                sx={{
                  color: "#888",
                  ml: 1,
                  "&:hover": {
                    backgroundColor: "rgba(255, 255, 255, 0.1)",
                  },
                }}
              >
                📎
              </IconButton>
            </Box>

            {/* Send button */}
            <Box sx={{ display: "flex", alignItems: "center" }}>
              {isLoading || isSendingMessage ? (
                <CircularProgress size={24} sx={{ color: "#fff" }} />
              ) : (
                <IconButton
                  color="primary"
                  type="submit"
                  // disabled={!message.trim() || !selectedAgent}
                  size="large"
                  sx={{
                    backgroundColor: "#EB5C1F",
                    color: "#fff",
                    borderRadius: "50%",
                    width: 40,
                    height: 40,
                    "&:hover": {
                      backgroundColor: "#D14A15",
                    },
                  }}
                >
                  <SendIcon />
                </IconButton>
              )}
            </Box>
          </Box>
        </Paper>
      </Box>

      {/* Delete confirmation dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
      >
        <DialogTitle>Delete Chat Session</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete this chat session? This action
            cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleDeleteSession} color="error">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
