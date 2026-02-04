// Copyright 2025-2026 Bret McKee
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

import { FC, useState } from 'react';
import { Box, Button, Container, Typography, Paper, Alert } from '@mui/material';
import { apiClient } from '../api/client';

const REDIRECT_URI = `${window.location.origin}/auth/callback`;

export const LoginPage: FC = () => {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.get('/api/v1/auth/login', {
        params: { redirect_uri: REDIRECT_URI },
      });

      const { authorization_url, state } = response.data;

      if (!authorization_url || !state) {
        throw new Error('Invalid response: missing authorization_url or state');
      }

      // Store state in sessionStorage for CSRF validation
      sessionStorage.setItem('oauth_state', state);

      // Redirect to Discord OAuth2 authorization page
      window.location.href = authorization_url;
    } catch (err: unknown) {
      console.error('Login initiation failed:', err);

      const errorMessage =
        err instanceof Error ? err.message : 'Failed to initiate login. Please try again.';
      setError(errorMessage);
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="sm">
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', mt: 8 }}>
        <Paper sx={{ p: 4, width: '100%', textAlign: 'center' }}>
          <Typography variant="h4" component="h1" gutterBottom>
            Welcome to Discord Game Scheduler
          </Typography>
          <Typography variant="body1" color="text.secondary" paragraph>
            Sign in with your Discord account to get started
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mt: 2, mb: 2 }}>
              {error}
            </Alert>
          )}

          <Button
            variant="contained"
            size="large"
            onClick={handleLogin}
            disabled={loading}
            sx={{ mt: 2 }}
          >
            {loading ? 'Connecting to Discord...' : 'Login with Discord'}
          </Button>
        </Paper>
      </Box>
    </Container>
  );
};
