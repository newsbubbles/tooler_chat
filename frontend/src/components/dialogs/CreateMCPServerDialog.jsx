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
} from '@mui/material';
import { useMCPServersStore } from '../../contexts/mcpServersStore';

export default function CreateMCPServerDialog({ open, onClose }) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [code, setCode] = useState('');
  const [error, setError] = useState('');

  const { createMCPServer, isLoading } = useMCPServersStore();

  const resetForm = () => {
    setName('');
    setDescription('');
    setCode('');
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
      setError('MCP server name is required');
      return;
    }

    if (!code.trim()) {
      setError('MCP server code is required');
      return;
    }

    // Create MCP server
    const result = await createMCPServer({
      name: name.trim(),
      description: description.trim(),
      code: code.trim(),
    });

    if (result) {
      handleClose();
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="md">
      <DialogTitle>Create New MCP Server</DialogTitle>
      <form onSubmit={handleSubmit}>
        <DialogContent>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

          <TextField
            autoFocus
            margin="normal"
            label="MCP Server Name"
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
            label="MCP Server Code"
            fullWidth
            value={code}
            onChange={(e) => setCode(e.target.value)}
            multiline
            rows={15}
            required
            disabled={isLoading}
            placeholder="Enter the Python code for the MCP server"
            inputProps={{ style: { fontFamily: 'monospace' } }}
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
