import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material';

import Layout from './components/Layout';
import Login from './pages/Login';
import Register from './pages/Register';
import Chat from './pages/Chat';
import NotFound from './pages/NotFound';
import LogViewer from './pages/Admin/LogViewer';
import ProtectedRoute from './components/ProtectedRoute';
import { useAuthStore } from './contexts/authStore';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#2196f3',
    },
    secondary: {
      main: '#f50057',
    },
    background: {
      default: '#f5f5f5',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
        },
      },
    },
  },
});

function App() {
  const { isAuthenticated, isAdmin } = useAuthStore();

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Routes>
        <Route path="/login" element={!isAuthenticated ? <Login /> : <Navigate to="/" />} />
        <Route path="/register" element={!isAuthenticated ? <Register /> : <Navigate to="/" />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/chat" />} />
          <Route path="chat" element={<Chat />} />
          <Route path="chat/:sessionId" element={<Chat />} />
          {/* Admin routes */}
          <Route 
            path="admin/logs" 
            element={isAdmin ? <LogViewer /> : <Navigate to="/" />} 
          />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </ThemeProvider>
  );
}

export default App;
