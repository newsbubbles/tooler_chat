import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  CircularProgress,
  Alert,
  Box,
  Typography,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemButton,
  IconButton,
  Checkbox,
  FormControlLabel,
} from '@mui/material';
import {
  Code as CodeIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
} from '@mui/icons-material';

import { useAgentsStore } from '../../contexts/agentsStore';
import { useMCPServersStore } from '../../contexts/mcpServersStore';

export default function AgentSettingsDialog({ open, onClose, agent }) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [error, setError] = useState('');
  const [showAssociateMCPServers, setShowAssociateMCPServers] = useState(false);
  const [associatedMCPServerIds, setAssociatedMCPServerIds] = useState(new Set());

  const { updateAgent, isLoading, addMCPServerToAgent, removeMCPServerFromAgent } = useAgentsStore();
  const { mcpServers, loadMCPServers } = useMCPServersStore();

  // Initialize form with agent data
  useEffect(() => {
    if (agent && open) {
      setName(agent.name || '');
      setDescription(agent.description || '');
      setSystemPrompt(agent.system_prompt || '');
      
      // Set associated MCP servers
      if (agent.mcp_servers) {
        const mcpIds = new Set(agent.mcp_servers.map(mcp => mcp.id));
        setAssociatedMCPServerIds(mcpIds);
      } else {
        setAssociatedMCPServerIds(new Set());
      }
      
      // Load available MCP servers
      loadMCPServers();
    }
  }, [agent, open, loadMCPServers]);

  const handleClose = () => {
    setShowAssociateMCPServers(false);
    onClose();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!agent) return;
    
    setError('');

    // Validate form
    if (!name.trim() && !agent.is_default) {
      setError('Agent name is required');
      return;
    }

    if (!systemPrompt.trim()) {
      setError('System prompt is required');
      return;
    }

    // Prepare update data
    const updateData = {};
    
    // For default agent, only allow system_prompt updates
    if (agent.is_default) {
      updateData.system_prompt = systemPrompt.trim();
    } else {
      updateData.name = name.trim();
      updateData.description = description.trim();
      updateData.system_prompt = systemPrompt.trim();
    }

    // Update agent
    const result = await updateAgent(agent.uuid, updateData);

    if (result) {
      handleClose();
    }
  };

  const toggleMCPServer = async (mcpServer) => {
    if (!agent) return;
    
    const isAssociated = agent.mcp_servers?.some(mcp => mcp.id === mcpServer.id) || false;
    
    if (isAssociated) {
      // Remove MCP server from agent
      await removeMCPServerFromAgent(mcpServer.id);
    } else {
      // Add MCP server to agent
      await addMCPServerToAgent(mcpServer.id);
    }
  };

  if (!agent) return null;

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="md">
      <DialogTitle>{agent.is_default ? 'Tooler Agent Settings' : 'Edit Agent'}</DialogTitle>
      {showAssociateMCPServers ? (
        // MCP Servers Association View
        <>
          <DialogContent>
            <Typography variant="h6" gutterBottom>
              Associated MCP Servers
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Select MCP servers to associate with this agent. These will be available as tools during chat.
            </Typography>
            <List>
              {mcpServers.map((mcpServer) => {
                const isAssociated = agent.mcp_servers?.some(mcp => mcp.id === mcpServer.id) || false;
                
                return (
                  <ListItem 
                    key={mcpServer.uuid} 
                    disablePadding
                    secondaryAction={
                      <IconButton 
                        edge="end" 
                        onClick={() => toggleMCPServer(mcpServer)}
                        disabled={isLoading}
                      >
                        {isAssociated ? <DeleteIcon color="error" /> : <AddIcon color="primary" />}
                      </IconButton>
                    }
                  >
                    <ListItemButton disabled={isLoading}>
                      <ListItemIcon>
                        <CodeIcon />
                      </ListItemIcon>
                      <ListItemText 
                        primary={mcpServer.name}
                        secondary={mcpServer.description || 'No description'}
                      />
                    </ListItemButton>
                  </ListItem>
                );
              })}
            </List>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setShowAssociateMCPServers(false)} color="primary">
              Back to Settings
            </Button>
          </DialogActions>
        </>
      ) : (
        // Main Settings View
        <form onSubmit={handleSubmit}>
          <DialogContent>
            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

            {!agent.is_default && (
              <TextField
                autoFocus
                margin="normal"
                label="Agent Name"
                fullWidth
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                disabled={isLoading || agent.is_default}
              />
            )}

            {!agent.is_default && (
              <TextField
                margin="normal"
                label="Description"
                fullWidth
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                multiline
                rows={2}
                disabled={isLoading || agent.is_default}
              />
            )}

            <TextField
              margin="normal"
              label="System Prompt"
              fullWidth
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              multiline
              rows={12}
              required
              disabled={isLoading}
              placeholder="Enter the system prompt that defines the agent's behavior"
            />

            <Box sx={{ mt: 2 }}>
              <Button 
                variant="outlined" 
                onClick={() => setShowAssociateMCPServers(true)}
                startIcon={<CodeIcon />}
                disabled={isLoading}
              >
                Manage Associated MCP Servers
              </Button>
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleClose} disabled={isLoading}>
              Cancel
            </Button>
            <Button 
              type="submit" 
              variant="contained" 
              color="primary" 
              disabled={isLoading}
            >
              {isLoading ? <CircularProgress size={24} /> : 'Save'}
            </Button>
          </DialogActions>
        </form>
      )}
    </Dialog>
  );
}
