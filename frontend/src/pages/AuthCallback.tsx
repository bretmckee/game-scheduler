import { FC, useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Box, CircularProgress, Typography, Container } from '@mui/material';
import { useAuth } from '../hooks/useAuth';

export const AuthCallback: FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { login } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const completeLogin = async () => {
      try {
        await login();
        navigate('/guilds');
      } catch (err) {
        console.error('Failed to complete login:', err);
        setError('Failed to fetch user information');
        setTimeout(() => navigate('/login'), 3000);
      }
    };

    const handleCallback = async () => {
      const successParam = searchParams.get('success');
      
      if (successParam === 'true') {
        await completeLogin();
        return;
      }

      // Otherwise, we're coming from Discord and need to exchange code
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const errorParam = searchParams.get('error');

      if (errorParam) {
        setError(`Discord authorization failed: ${errorParam}`);
        setTimeout(() => navigate('/login'), 3000);
        return;
      }

      if (!code) {
        setError('No authorization code received from Discord');
        setTimeout(() => navigate('/login'), 3000);
        return;
      }

      if (!state) {
        setError('No state parameter received');
        setTimeout(() => navigate('/login'), 3000);
        return;
      }

      // Validate state matches what we stored
      const storedState = sessionStorage.getItem('oauth_state');
      if (!storedState || storedState !== state) {
        setError('Invalid state parameter (CSRF protection)');
        sessionStorage.removeItem('oauth_state');
        setTimeout(() => navigate('/login'), 3000);
        return;
      }

      sessionStorage.removeItem('oauth_state');

      try {
        // Call the API callback endpoint through the Vite proxy
        // This ensures cookies are set correctly for localhost:3000
        const response = await fetch(`/api/v1/auth/callback?code=${code}&state=${state}`, {
          credentials: 'include'
        });

        if (response.ok) {
          // Callback succeeded, now fetch user info
          await completeLogin();
        } else {
          const data = await response.json().catch(() => ({ detail: 'Unknown error' }));
          setError(data.detail || 'Failed to complete authentication');
          setTimeout(() => navigate('/login'), 3000);
        }
      } catch (err: any) {
        console.error('OAuth callback error:', err);
        const errorMessage = err.response?.data?.detail || 'Failed to complete authentication';
        setError(errorMessage);
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
