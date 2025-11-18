import { FC, useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Box, CircularProgress, Typography, Container } from '@mui/material';
import { useAuth } from '../hooks/useAuth';
import { apiClient } from '../api/client';

export const AuthCallback: FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { login } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code');
      const state = searchParams.get('state');

      if (!code) {
        setError('No authorization code received');
        return;
      }

      try {
        const response = await apiClient.get(`/api/v1/auth/callback?code=${code}&state=${state || ''}`);
        
        const { access_token, refresh_token, user_id } = response.data;
        login({ access_token, refresh_token, user_id });
        
        navigate('/guilds');
      } catch (err) {
        console.error('OAuth callback error:', err);
        setError('Failed to complete authentication');
        setTimeout(() => navigate('/login'), 3000);
      }
    };

    handleCallback();
  }, [searchParams, login, navigate]);

  return (
    <Container maxWidth="sm">
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '50vh' }}>
        {error ? (
          <Typography variant="h6" color="error">
            {error}
          </Typography>
        ) : (
          <>
            <CircularProgress size={60} />
            <Typography variant="h6" sx={{ mt: 2 }}>
              Completing authentication...
            </Typography>
          </>
        )}
      </Box>
    </Container>
  );
};
