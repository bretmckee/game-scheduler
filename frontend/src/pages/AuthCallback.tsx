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

import { FC, useEffect, useState, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { Box, CircularProgress, Typography, Container } from '@mui/material';
import { useAuth } from '../hooks/useAuth';
import { UI } from '../constants/ui';

export const AuthCallback: FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { login } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const hasProcessed = useRef(false);

  useEffect(() => {
    // Prevent duplicate processing (React StrictMode runs effects twice)
    if (hasProcessed.current) return;
    hasProcessed.current = true;
    const completeLogin = async () => {
      try {
        await login();
        const returnUrl = sessionStorage.getItem('returnUrl');
        sessionStorage.removeItem('returnUrl');
        navigate(returnUrl || '/my-games');
      } catch (err) {
        console.error('Failed to complete login:', err);
        setError('Failed to fetch user information');
        setTimeout(() => navigate('/login'), UI.ANIMATION_DELAY_STANDARD);
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
        setTimeout(() => navigate('/login'), UI.ANIMATION_DELAY_STANDARD);
        return;
      }

      if (!code) {
        setError('No authorization code received from Discord');
        setTimeout(() => navigate('/login'), UI.ANIMATION_DELAY_STANDARD);
        return;
      }

      if (!state) {
        setError('No state parameter received');
        setTimeout(() => navigate('/login'), UI.ANIMATION_DELAY_STANDARD);
        return;
      }

      // Clear stored state (backend validates it)
      sessionStorage.removeItem('oauth_state');

      try {
        // Call the API callback endpoint through the Vite proxy
        // This ensures cookies are set correctly for localhost:3000
        const response = await fetch(`/api/v1/auth/callback?code=${code}&state=${state}`, {
          credentials: 'include',
        });

        if (response.ok) {
          // Callback succeeded, now fetch user info
          await completeLogin();
        } else {
          const data = await response.json().catch(() => ({ detail: 'Unknown error' }));
          setError(data.detail || 'Failed to complete authentication');
          setTimeout(() => navigate('/login'), UI.ANIMATION_DELAY_STANDARD);
        }
      } catch (err: unknown) {
        console.error('OAuth callback error:', err);
        const errorMessage =
          (err as any).response?.data?.detail || 'Failed to complete authentication';
        setError(errorMessage);
        setTimeout(() => navigate('/login'), UI.ANIMATION_DELAY_STANDARD);
      }
    };

    handleCallback();
  }, [searchParams]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Container maxWidth="sm">
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '50vh',
        }}
      >
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
