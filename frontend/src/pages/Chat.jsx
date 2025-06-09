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

  // Load session when sessionId changes
  useEffect(() => {
    if (sessionId && sessionId !== "new") {
      setIsLoadingMessages(true);
      loadSession(sessionId).finally(() => {
        setIsLoadingMessages(false);
      });
    } else if (sessionId === "new" && selectedAgent) {
      // Clear any current session data for a new session
      useChatStore.setState({
        selectedSession: null,
        messages: [],
      });
    }
  }, [sessionId, loadSession, selectedAgent]);

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

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!message.trim() || !selectedAgent) return;

    let sessionToUse = selectedSession;

    // Create a new session if needed
    if (!selectedSession) {
      const newSession = await createSession({
        agent_id: selectedAgent.id,
        title: message.length > 30 ? `${message.substring(0, 30)}...` : message,
      });

      if (newSession) {
        sessionToUse = newSession;
        navigate(`/chat/${newSession.uuid}`);
      } else {
        return; // Failed to create session
      }
    }

    // Send message
    await sendMessage(message, sessionToUse.uuid);
    setMessage("");
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
      <Paper
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
      </Paper>

      <Divider />

      {/* Messages container */}
      <Box
        sx={{
          flex: 1,
          overflow: "auto",
          p: 2,
          backgroundColor: "#f9f9f9",
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
                  backgroundColor: msg.role === "user" ? "#e3f2fd" : "white",
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

      <Divider />

      {/* Message input */}
      <Paper
        component="form"
        onSubmit={handleSendMessage}
        sx={{
          p: 2,
          display: "flex",
          alignItems: "center",
          borderRadius: 0,
          borderTop: "1px solid rgba(0, 0, 0, 0.12)",
        }}
        elevation={4}
      >
        <TextField
          fullWidth
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Type a message..."
          variant="outlined"
          multiline
          maxRows={4}
          disabled={isLoading}
        />
        <Box sx={{ ml: 1, display: "flex", alignItems: "center" }}>
          {isLoading ? (
            <CircularProgress size={24} sx={{ mx: 1 }} />
          ) : (
            <IconButton
              color="primary"
              type="submit"
              disabled={!message.trim() || !selectedAgent}
              size="large"
            >
              <SendIcon />
            </IconButton>
          )}
        </Box>
      </Paper>

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
