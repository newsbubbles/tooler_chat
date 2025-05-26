import React, { useState } from 'react';
import {
  Box,
  Drawer,
  Toolbar,
  Typography,
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  Button,
  IconButton,
} from '@mui/material';
import {
  Code as CodeIcon,
  SettingsApplications as SettingsApplicationsIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  FolderOpen as FolderOpenIcon,
} from '@mui/icons-material';

import { useMCPServersStore } from '../contexts/mcpServersStore';
import { useAgentsStore } from '../contexts/agentsStore';
import CreateMCPServerDialog from './dialogs/CreateMCPServerDialog';
import EditMCPServerDialog from './dialogs/EditMCPServerDialog';
import AgentSettingsDialog from './dialogs/AgentSettingsDialog';

function TabPanel(props) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`tabpanel-${index}`}
      aria-labelledby={`tab-${index}`}
      {...other}
      style={{ height: 'calc(100% - 48px)', overflow: 'auto' }}
    >
      {value === index && <Box sx={{ p: 2, height: '100%', overflow: 'auto' }}>{children}</Box>}
    </div>
  );
}

export default function RightPanel({ open, width, onClose }) {
  const [tabValue, setTabValue] = useState(0);
  const [createMCPOpen, setCreateMCPOpen] = useState(false);
  const [editMCPOpen, setEditMCPOpen] = useState(false);
  const [agentSettingsOpen, setAgentSettingsOpen] = useState(false);
  
  const { mcpServers, selectedMCPServer, selectMCPServer, deleteMCPServer, loadMCPServers } = useMCPServersStore();
  const { selectedAgent } = useAgentsStore();

  React.useEffect(() => {
    if (open) {
      loadMCPServers();
    }
  }, [open, loadMCPServers]);

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  const handleMCPServerSelect = (mcpServer) => {
    selectMCPServer(mcpServer);
  };

  const handleCreateMCP = () => {
    setCreateMCPOpen(true);
  };

  const handleEditMCP = () => {
    if (selectedMCPServer) {
      setEditMCPOpen(true);
    }
  };

  const handleDeleteMCP = () => {
    if (selectedMCPServer && window.confirm('Are you sure you want to delete this MCP server?')) {
      deleteMCPServer(selectedMCPServer.uuid);
    }
  };

  const handleAgentSettings = () => {
    setAgentSettingsOpen(true);
  };

  return (
    <>
      <Drawer
        sx={{
          width: width,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: width,
            boxSizing: 'border-box',
          },
        }}
        variant="persistent"
        anchor="right"
        open={open}
      >
        <Toolbar />
        <Box sx={{ width: '100%', height: 'calc(100% - 64px)', display: 'flex', flexDirection: 'column' }}>
          <Tabs
            value={tabValue}
            onChange={handleTabChange}
            aria-label="right panel tabs"
            variant="fullWidth"
          >
            <Tab icon={<CodeIcon />} label="MCP Servers" />
            <Tab 
               icon={<SettingsApplicationsIcon />} 
               label="Agent Settings" 
               disabled={!selectedAgent}
            />
          </Tabs>

          {/* MCP Servers Tab */}
          <TabPanel value={tabValue} index={0}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">MCP Servers</Typography>
              <Button
                variant="outlined"
                startIcon={<AddIcon />}
                size="small"
                onClick={handleCreateMCP}
              >
                Create New
              </Button>
            </Box>
            <List sx={{ width: '100%' }}>
              {mcpServers.map((mcp) => (
                <ListItem
                  key={mcp.uuid}
                  secondaryAction={
                    selectedMCPServer?.uuid === mcp.uuid && (
                      <Box>
                        <IconButton edge="end" aria-label="edit" onClick={handleEditMCP} size="small">
                          <EditIcon />
                        </IconButton>
                        <IconButton edge="end" aria-label="delete" onClick={handleDeleteMCP} size="small">
                          <DeleteIcon />
                        </IconButton>
                      </Box>
                    )
                  }
                  disablePadding
                >
                  <ListItemButton
                    selected={selectedMCPServer?.uuid === mcp.uuid}
                    onClick={() => handleMCPServerSelect(mcp)}
                  >
                    <ListItemIcon>
                      <CodeIcon />
                    </ListItemIcon>
                    <ListItemText
                      primary={mcp.name}
                      secondary={mcp.description || 'No description'}
                      secondaryTypographyProps={{ noWrap: true }}
                    />
                  </ListItemButton>
                </ListItem>
              ))}
            </List>
          </TabPanel>

          {/* Agent Settings Tab */}
          <TabPanel value={tabValue} index={1}>
            {selectedAgent && (
              <>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6">{selectedAgent.name}</Typography>
                  <Button
                    variant="outlined"
                    startIcon={<SettingsApplicationsIcon />}
                    size="small"
                    onClick={handleAgentSettings}
                  >
                    Settings
                  </Button>
                </Box>
                <Typography variant="subtitle1" gutterBottom>
                  Agent Description
                </Typography>
                <Typography variant="body2" paragraph>
                  {selectedAgent.description || 'No description provided.'}
                </Typography>
                <Divider sx={{ my: 2 }} />
                <Typography variant="subtitle1" gutterBottom>
                  Associated MCP Servers
                </Typography>
                <List>
                  {selectedAgent.mcp_servers?.length > 0 ? (
                    selectedAgent.mcp_servers.map((mcp) => (
                      <ListItem key={mcp.uuid} disablePadding>
                        <ListItemButton>
                          <ListItemIcon>
                            <CodeIcon />
                          </ListItemIcon>
                          <ListItemText
                            primary={mcp.name}
                            secondary={mcp.description || 'No description'}
                          />
                        </ListItemButton>
                      </ListItem>
                    ))
                  ) : (
                    <ListItem>
                      <ListItemText primary="No MCP servers associated with this agent." />
                    </ListItem>
                  )}
                </List>
              </>
            )}
          </TabPanel>
        </Box>
      </Drawer>

      {/* Dialogs */}
      <CreateMCPServerDialog open={createMCPOpen} onClose={() => setCreateMCPOpen(false)} />
      <EditMCPServerDialog 
        open={editMCPOpen} 
        onClose={() => setEditMCPOpen(false)} 
        mcpServer={selectedMCPServer} 
      />
      <AgentSettingsDialog 
        open={agentSettingsOpen} 
        onClose={() => setAgentSettingsOpen(false)} 
        agent={selectedAgent}
      />
    </>
  );
}
