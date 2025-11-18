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
    const completeLogin = async (userId: string) => {
      try {
        // Tokens are stored in Redis, fetch user info to complete login
        await apiClient.get('/api/v1/auth/user', {
          headers: { 'X-User-Id': userId }
        });
        
        login({
          user_id: userId,
          access_token: 'stored-in-redis',
          refresh_token: 'stored-in-redis'
        });
        
        navigate('/guilds');
      } catch (err) {
        console.error('Failed to fetch user info:', err);
        setError('Failed to fetch user information');
        setTimeout(() => navigate('/login'), 3000);
      }
    };

    const handleCallback = async () => {
      // Check if we're coming back from API redirect with success
      const successParam = searchParams.get('success');
      const userId = searchParams.get('user_id');
      
      if (successParam === 'true' && userId) {
        await completeLogin(userId);
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
        // API callback redirects browser to this page with success params
        // So we make the call and let the redirect happen
        window.location.href = `/api/v1/auth/callback?code=${code}&state=${state}`;
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
