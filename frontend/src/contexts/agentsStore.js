import { create } from "zustand";
import api from "../services/api";

export const useAgentsStore = create((set, get) => ({
  agents: [],
  selectedAgent: null,
  isLoading: false,
  error: null,

  // Load all agents
  loadAgents: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.get("/api/agents");
      set({ agents: response.data, isLoading: false });

      // If there's no selected agent yet, select the default Tooler agent
      if (!get().selectedAgent) {
        const defaultAgent = response.data.find((agent) => agent.is_default);
        if (defaultAgent) {
          get().selectAgent(defaultAgent);
        }
      }
    } catch (error) {
      set({
        error: error.response?.data?.detail || "Failed to load agents",
        isLoading: false,
      });
    }
  },

  // Load a specific agent with MCP servers
  loadAgentDetails: async (agentUuid) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.get(`/api/agents/${agentUuid}`);
      // Update the agent in the agents list
      const updatedAgents = get().agents.map((agent) => {
        if (agent.uuid === agentUuid) {
          return response.data;
        }
        return agent;
      });
      set({
        agents: updatedAgents,
        selectedAgent: response.data,
        isLoading: false,
      });
      return response.data;
    } catch (error) {
      set({
        error: error.response?.data?.detail || "Failed to load agent details",
        isLoading: false,
      });
      return null;
    }
  },

  // Select an agent
  selectAgent: (agent) => {
    if (agent) {
      // Load full agent details including MCP servers
      get().loadAgentDetails(agent.uuid);
    } else {
      set({ selectedAgent: null });
    }
  },

  // Create a new agent
  createAgent: async (agentData) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.post("/api/agents", agentData);
      set((state) => ({
        agents: [...state.agents, response.data],
        selectedAgent: response.data,
        isLoading: false,
      }));
      return response.data;
    } catch (error) {
      set({
        error: error.response?.data?.detail || "Failed to create agent",
        isLoading: false,
      });
      return null;
    }
  },

  // Update an agent
  updateAgent: async (agentUuid, agentData) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.put(`/api/agents/${agentUuid}`, agentData);
      set((state) => ({
        agents: state.agents.map((agent) =>
          agent.uuid === agentUuid ? response.data : agent
        ),
        selectedAgent:
          state.selectedAgent?.uuid === agentUuid
            ? response.data
            : state.selectedAgent,
        isLoading: false,
      }));
      return response.data;
    } catch (error) {
      set({
        error: error.response?.data?.detail || "Failed to update agent",
        isLoading: false,
      });
      return null;
    }
  },

  // Delete an agent
  deleteAgent: async (agentUuid) => {
    set({ isLoading: true, error: null });
    try {
      await api.delete(`/api/agents/${agentUuid}`);
      // Remove the agent from the agents list
      const updatedAgents = get().agents.filter(
        (agent) => agent.uuid !== agentUuid
      );
      set((state) => ({
        agents: updatedAgents,
        selectedAgent:
          state.selectedAgent?.uuid === agentUuid ? null : state.selectedAgent,
        isLoading: false,
      }));
      return true;
    } catch (error) {
      set({
        error: error.response?.data?.detail || "Failed to delete agent",
        isLoading: false,
      });
      return false;
    }
  },

  // Associate an MCP server with the selected agent
  addMCPServerToAgent: async (mcpServerId) => {
    const { selectedAgent } = get();
    if (!selectedAgent) return false;

    set({ isLoading: true, error: null });
    try {
      await api.post(`/api/agents/${selectedAgent.uuid}/mcp-servers`, {
        mcp_server_id: mcpServerId,
      });

      // Reload agent details to get updated MCP servers
      await get().loadAgentDetails(selectedAgent.uuid);
      return true;
    } catch (error) {
      set({
        error:
          error.response?.data?.detail || "Failed to add MCP server to agent",
        isLoading: false,
      });
      return false;
    }
  },

  // Remove an MCP server from the selected agent
  removeMCPServerFromAgent: async (mcpServerId) => {
    const { selectedAgent } = get();
    if (!selectedAgent) return false;

    set({ isLoading: true, error: null });
    try {
      await api.delete(`/api/agents/${selectedAgent.uuid}/mcp-servers`, {
        data: { mcp_server_id: mcpServerId },
      });

      // Reload agent details to get updated MCP servers
      await get().loadAgentDetails(selectedAgent.uuid);
      return true;
    } catch (error) {
      set({
        error:
          error.response?.data?.detail ||
          "Failed to remove MCP server from agent",
        isLoading: false,
      });
      return false;
    }
  },
}));
