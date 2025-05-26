import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  Typography,
  Divider,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Avatar,
  Menu,
  MenuItem,
  useTheme,
  useMediaQuery,
  Button,
} from '@mui/material';
import {
  Menu as MenuIcon,
  ChevronLeft as ChevronLeftIcon,
  Add as AddIcon,
  SmartToy as SmartToyIcon,
  Settings as SettingsIcon,
  Logout as LogoutIcon,
  AccountCircle as AccountCircleIcon,
} from '@mui/icons-material';

import { useAuthStore } from '../contexts/authStore';
import { useAgentsStore } from '../contexts/agentsStore';
import { useChatStore } from '../contexts/chatStore';
import RightPanel from './RightPanel';
import CreateAgentDialog from './dialogs/CreateAgentDialog';

const drawerWidth = 280;
const rightPanelWidth = 280;

export default function Layout() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [drawerOpen, setDrawerOpen] = useState(!isMobile);
  const [rightPanelOpen, setRightPanelOpen] = useState(!isMobile);
  const [anchorEl, setAnchorEl] = useState(null);
  const [createAgentDialogOpen, setCreateAgentDialogOpen] = useState(false);

  const { user, logout } = useAuthStore();
  const { agents, selectedAgent, selectAgent, loadAgents } = useAgentsStore();
  const { sessions, selectedSession, selectSession, loadSessions } = useChatStore();

  // Load agents and sessions on component mount
  React.useEffect(() => {
    loadAgents();
  }, [loadAgents]);

  const handleDrawerToggle = () => {
    setDrawerOpen(!drawerOpen);
  };

  const handleRightPanelToggle = () => {
    setRightPanelOpen(!rightPanelOpen);
  };

  const handleMenuClick = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    handleMenuClose();
    logout();
  };

  const handleAgentSelect = (agent) => {
    selectAgent(agent);
    loadSessions(agent.id);
    if (isMobile) {
      setDrawerOpen(false);
    }
  };

  const handleSessionSelect = (session) => {
    selectSession(session);
    if (isMobile) {
      setDrawerOpen(false);
    }
  };

  const handleCreateAgent = () => {
    setCreateAgentDialogOpen(true);
  };

  return (
    <Box sx={{ display: 'flex', height: '100vh' }}>
      {/* Top AppBar */}
      <AppBar
        position="fixed"
        sx={{
          zIndex: (theme) => theme.zIndex.drawer + 1,
          transition: theme.transitions.create(['width', 'margin'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen,
          }),
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            onClick={handleDrawerToggle}
            edge="start"
            sx={{ mr: 2 }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            Tooler Chat
          </Typography>
          <IconButton color="inherit" onClick={handleRightPanelToggle}>
            <SettingsIcon />
          </IconButton>
          <IconButton
            size="large"
            aria-label="account of current user"
            aria-controls="menu-appbar"
            aria-haspopup="true"
            onClick={handleMenuClick}
            color="inherit"
          >
            <Avatar sx={{ width: 32, height: 32 }}>
              {user?.username ? user.username.charAt(0).toUpperCase() : 'U'}
            </Avatar>
          </IconButton>
          <Menu
            id="menu-appbar"
            anchorEl={anchorEl}
            anchorOrigin={{
              vertical: 'bottom',
              horizontal: 'right',
            }}
            keepMounted
            transformOrigin={{
              vertical: 'top',
              horizontal: 'right',
            }}
            open={Boolean(anchorEl)}
            onClose={handleMenuClose}
          >
            <MenuItem onClick={handleMenuClose}>
              <ListItemIcon>
                <AccountCircleIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText primary="Profile" />
            </MenuItem>
            <MenuItem onClick={handleLogout}>
              <ListItemIcon>
                <LogoutIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText primary="Logout" />
            </MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>

      {/* Left Drawer - Agents & Sessions */}
      <Drawer
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
          },
        }}
        variant={isMobile ? 'temporary' : 'persistent'}
        anchor="left"
        open={drawerOpen}
        onClose={isMobile ? handleDrawerToggle : undefined}
      >
        <Toolbar />
        <Box sx={{ overflow: 'auto', display: 'flex', flexDirection: 'column', height: '100%' }}>
          <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6">Agents</Typography>
            <Button
              startIcon={<AddIcon />}
              size="small"
              onClick={handleCreateAgent}
              variant="outlined"
            >
              New Agent
            </Button>
          </Box>
          <List>
            {agents.map((agent) => (
              <ListItem key={agent.uuid} disablePadding>
                <ListItemButton
                  selected={selectedAgent?.uuid === agent.uuid}
                  onClick={() => handleAgentSelect(agent)}
                >
                  <ListItemIcon>
                    <SmartToyIcon color={agent.is_default ? 'primary' : 'inherit'} />
                  </ListItemIcon>
                  <ListItemText primary={agent.name} secondary={agent.is_default ? 'Default' : ''} />
                </ListItemButton>
              </ListItem>
            ))}
          </List>

          {selectedAgent && (
            <>
              <Divider />
              <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="h6">Sessions</Typography>
                <Button
                  startIcon={<AddIcon />}
                  size="small"
                  onClick={() => selectSession(null)}
                  variant="outlined"
                >
                  New Chat
                </Button>
              </Box>
              <List sx={{ flex: 1, overflow: 'auto' }}>
                {sessions.map((session) => (
                  <ListItem key={session.uuid} disablePadding>
                    <ListItemButton
                      selected={selectedSession?.uuid === session.uuid}
                      onClick={() => handleSessionSelect(session)}
                    >
                      <ListItemText
                        primary={session.title}
                        secondary={new Date(session.updated_at).toLocaleString()}
                      />
                    </ListItemButton>
                  </ListItem>
                ))}
              </List>
            </>
          )}
        </Box>
      </Drawer>

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 0,
          width: `calc(100% - ${drawerOpen ? drawerWidth : 0}px - ${rightPanelOpen ? rightPanelWidth : 0}px)`,
          height: '100vh',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <Toolbar />
        <Box sx={{ flex: 1, overflow: 'auto' }}>
          <Outlet />
        </Box>
      </Box>

      {/* Right Panel - MCPs & Project Structure */}
      <RightPanel open={rightPanelOpen} width={rightPanelWidth} onClose={handleRightPanelToggle} />

      {/* Dialogs */}
      <CreateAgentDialog
        open={createAgentDialogOpen}
        onClose={() => setCreateAgentDialogOpen(false)}
      />
    </Box>
  );
}
