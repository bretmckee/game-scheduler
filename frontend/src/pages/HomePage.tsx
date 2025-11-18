import { FC } from 'react';
import { Box, Typography, Button, Container } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export const HomePage: FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  return (
    <Container maxWidth="md">
      <Box sx={{ textAlign: 'center', py: 8 }}>
        <Typography variant="h2" component="h1" gutterBottom>
          Discord Game Scheduler
        </Typography>
        <Typography variant="h5" color="text.secondary" paragraph>
          Organize and manage game sessions with your Discord community
        </Typography>
        <Box sx={{ mt: 4 }}>
          {user ? (
            <>
              <Button
                variant="contained"
                size="large"
                onClick={() => navigate('/guilds')}
                sx={{ mr: 2 }}
              >
                View My Guilds
              </Button>
              <Button
                variant="outlined"
                size="large"
                onClick={() => navigate('/my-games')}
              >
                My Games
              </Button>
            </>
          ) : (
            <Button
              variant="contained"
              size="large"
              onClick={() => navigate('/login')}
            >
              Login with Discord
            </Button>
          )}
        </Box>
      </Box>
    </Container>
  );
};
