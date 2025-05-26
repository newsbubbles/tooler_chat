import React, { useState } from 'react';
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
} from '@mui/material';
import { useAgentsStore } from '../../contexts/agentsStore';

export default function CreateAgentDialog({ open, onClose }) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [error, setError] = useState('');

  const { createAgent, isLoading } = useAgentsStore();

  const resetForm = () => {
    setName('');
    setDescription('');
    setSystemPrompt('');
    setError('');
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // Validate form
    if (!name.trim()) {
      setError('Agent name is required');
      return;
    }

    if (!systemPrompt.trim()) {
      setError('System prompt is required');
      return;
    }

    // Create agent
    const result = await createAgent({
      name: name.trim(),
      description: description.trim(),
      system_prompt: systemPrompt.trim(),
    });

    if (result) {
      handleClose();
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="md">
      <DialogTitle>Create New Agent</DialogTitle>
      <form onSubmit={handleSubmit}>
        <DialogContent>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

          <TextField
            autoFocus
            margin="normal"
            label="Agent Name"
            fullWidth
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            disabled={isLoading}
          />

          <TextField
            margin="normal"
            label="Description (optional)"
            fullWidth
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            multiline
            rows={2}
            disabled={isLoading}
          />

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
            {isLoading ? <CircularProgress size={24} /> : 'Create'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
