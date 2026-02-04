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
import { StatusCodes } from 'http-status-codes';
import { useParams, useNavigate } from 'react-router';
import { Box, CircularProgress, Typography, Alert } from '@mui/material';
import { useAuth } from '../hooks/useAuth';
import { Time } from '../constants/time';

export const DownloadCalendar: FC = () => {
  const { gameId } = useParams<{ gameId: string }>();
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const hasDownloaded = useRef(false);

  const downloadCalendar = async () => {
    setDownloading(true);
    try {
      const response = await fetch(`/api/v1/export/game/${gameId}`, {
        credentials: 'include',
      });

      if (!response.ok) {
        if (response.status === StatusCodes.FORBIDDEN) {
          setError('You do not have permission to download this calendar.');
        } else if (response.status === StatusCodes.NOT_FOUND) {
          setError('Game not found.');
        } else {
          setError('Failed to download calendar.');
        }
        return;
      }

      const contentDisposition = response.headers.get('Content-Disposition');
      const filenameMatch = contentDisposition?.match(/filename="?(.+)"?/i);
      const filename = filenameMatch?.[1] || `game-${gameId}.ics`;

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      setTimeout(() => navigate('/my-games'), Time.MILLISECONDS_PER_SECOND);
    } catch (err) {
      setError('An error occurred while downloading the calendar.');
      console.error('Calendar download error:', err);
    } finally {
      setDownloading(false);
    }
  };

  useEffect(() => {
    // Prevent duplicate downloads (React StrictMode runs effects twice)
    if (hasDownloaded.current) return;

    if (!authLoading && user && gameId && !downloading) {
      hasDownloaded.current = true;
      downloadCalendar();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, authLoading, gameId]);

  if (authLoading || downloading) {
    return (
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
          gap: 2,
        }}
      >
        <CircularProgress />
        <Typography variant="body1">
          {authLoading ? 'Authenticating...' : 'Downloading calendar...'}
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
          p: 3,
        }}
      >
        <Alert severity="error" onClose={() => navigate('/my-games')}>
          {error}
        </Alert>
      </Box>
    );
  }

  return null;
};
