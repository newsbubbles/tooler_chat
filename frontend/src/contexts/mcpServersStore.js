import { create } from 'zustand';
import api from '../services/api';

export const useMCPServersStore = create((set, get) => ({
  mcpServers: [],
  selectedMCPServer: null,
  isLoading: false,
  error: null,

  // Load all MCP servers
  loadMCPServers: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.get('/api/mcp-servers');
      set({ mcpServers: response.data, isLoading: false });
    } catch (error) {
      set({
        error: error.response?.data?.detail || 'Failed to load MCP servers',
        isLoading: false
      });
    }
  },

  // Load a specific MCP server with agents
  loadMCPServerDetails: async (mcpServerUuid) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.get(`/api/mcp-servers/${mcpServerUuid}`);
      // Update the MCP server in the list
      const updatedMCPServers = get().mcpServers.map(mcp => {
        if (mcp.uuid === mcpServerUuid) {
          return response.data;
        }
        return mcp;
      });
      set({ 
        mcpServers: updatedMCPServers,
        selectedMCPServer: response.data,
        isLoading: false 
      });
      return response.data;
    } catch (error) {
      set({
        error: error.response?.data?.detail || 'Failed to load MCP server details',
        isLoading: false
      });
      return null;
    }
  },

  // Select an MCP server
  selectMCPServer: (mcpServer) => {
    if (mcpServer) {
      // Load full MCP server details including agents
      get().loadMCPServerDetails(mcpServer.uuid);
    } else {
      set({ selectedMCPServer: null });
    }
  },

  // Create a new MCP server
  createMCPServer: async (mcpServerData) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.post('/api/mcp-servers', mcpServerData);
      set(state => ({
        mcpServers: [...state.mcpServers, response.data],
        selectedMCPServer: response.data,
        isLoading: false
      }));
      return response.data;
    } catch (error) {
      set({
        error: error.response?.data?.detail || 'Failed to create MCP server',
        isLoading: false
      });
      return null;
    }
  },

  // Update an MCP server
  updateMCPServer: async (mcpServerUuid, mcpServerData) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.put(`/api/mcp-servers/${mcpServerUuid}`, mcpServerData);
      set(state => ({
        mcpServers: state.mcpServers.map(mcp => 
          mcp.uuid === mcpServerUuid ? response.data : mcp
        ),
        selectedMCPServer: state.selectedMCPServer?.uuid === mcpServerUuid ? 
          response.data : state.selectedMCPServer,
        isLoading: false
      }));
      return response.data;
    } catch (error) {
      set({
        error: error.response?.data?.detail || 'Failed to update MCP server',
        isLoading: false
      });
      return null;
    }
  },

  // Delete an MCP server
  deleteMCPServer: async (mcpServerUuid) => {
    set({ isLoading: true, error: null });
    try {
      await api.delete(`/api/mcp-servers/${mcpServerUuid}`);
      // Remove the MCP server from the list
      const updatedMCPServers = get().mcpServers.filter(mcp => mcp.uuid !== mcpServerUuid);
      set(state => ({
        mcpServers: updatedMCPServers,
        selectedMCPServer: state.selectedMCPServer?.uuid === mcpServerUuid ? null : state.selectedMCPServer,
        isLoading: false
      }));
      return true;
    } catch (error) {
      set({
        error: error.response?.data?.detail || 'Failed to delete MCP server',
        isLoading: false
      });
      return false;
    }
  },
}));
