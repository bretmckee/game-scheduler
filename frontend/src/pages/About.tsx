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

import { FC, useEffect, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Link,
  Divider,
  CircularProgress,
  Alert,
} from '@mui/material';
import { apiClient } from '../api/client';

interface VersionInfo {
  service: string;
  git_version: string;
  api_version: string;
  api_prefix: string;
}

export const About: FC = () => {
  const [versionInfo, setVersionInfo] = useState<VersionInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchVersionInfo = async () => {
      try {
        const response = await apiClient.get<VersionInfo>('/api/v1/version');
        setVersionInfo(response.data);
      } catch (err) {
        setError('Failed to load version information');
        console.error('Error fetching version:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchVersionInfo();
  }, []);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto' }}>
      <Typography variant="h4" component="h1" gutterBottom>
        About Discord Game Scheduler
      </Typography>

      {error && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Version Information
          </Typography>
          {versionInfo && (
            <Typography variant="body1" sx={{ mt: 2 }}>
              Version {versionInfo.git_version} (API {versionInfo.api_version})
            </Typography>
          )}
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Copyright
          </Typography>
          <Typography variant="body2" paragraph>
            Copyright © 2025-2026 Bret McKee (
            <Link href="mailto:bret.mckee@gmail.com" color="primary">
              bret.mckee@gmail.com
            </Link>
            )
          </Typography>
          <Divider sx={{ my: 2 }} />
          <Typography variant="body2" paragraph>
            This application is part of the Game_Scheduler project.
          </Typography>
          <Typography variant="body2">
            Source code:{' '}
            <Link
              href="https://github.com/game-scheduler/game-scheduler"
              target="_blank"
              rel="noopener noreferrer"
              color="primary"
            >
              github.com/game-scheduler/game-scheduler
            </Link>
          </Typography>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            License
          </Typography>
          <Typography variant="body2" paragraph>
            Game_Scheduler is free software distributed under the MIT License.
          </Typography>
          <Typography variant="body2" paragraph>
            Permission is hereby granted, free of charge, to any person obtaining a copy of this
            software and associated documentation files (the &quot;Software&quot;), to deal in the
            Software without restriction, including without limitation the rights to use, copy,
            modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and
            to permit persons to whom the Software is furnished to do so, subject to the following
            conditions:
          </Typography>
          <Typography variant="body2" paragraph>
            The above copyright notice and this permission notice shall be included in all copies or
            substantial portions of the Software.
          </Typography>
          <Typography variant="body2" paragraph>
            THE SOFTWARE IS PROVIDED &quot;AS IS&quot;, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
            IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
            PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
            HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
            CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR
            THE USE OR OTHER DEALINGS IN THE SOFTWARE.
          </Typography>
          <Typography variant="body2">
            For the full license text, see{' '}
            <Link
              href="https://opensource.org/license/mit/"
              target="_blank"
              rel="noopener noreferrer"
              color="primary"
            >
              https://opensource.org/license/mit/
            </Link>
            .
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
};
