import React from 'react';
import { Box, Typography, Button, Container, Paper } from '@mui/material';
import { useNavigate } from 'react-router-dom';

export default function NotFound() {
  const navigate = useNavigate();

  return (
    <Container maxWidth="sm">
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
        }}
      >
        <Paper
          elevation={3}
          sx={{
            p: 4,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            width: '100%',
          }}
        >
          <Typography variant="h1" component="h1" align="center" gutterBottom>
            404
          </Typography>
          <Typography variant="h5" align="center" gutterBottom>
            Page Not Found
          </Typography>
          <Typography variant="body1" align="center" paragraph>
            The page you are looking for does not exist or has been moved.
          </Typography>
          <Button variant="contained" color="primary" onClick={() => navigate('/')}>
            Go to Home
          </Button>
        </Paper>
      </Box>
    </Container>
  );
}
