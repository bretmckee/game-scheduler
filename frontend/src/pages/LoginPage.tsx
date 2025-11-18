// Copyright 2025 Bret McKee (bret.mckee@gmail.com)
//
// This file is part of Game_Scheduler. (https://github.com/game-scheduler)
//
// Game_Scheduler is free software: you can redistribute it and/or
// modify it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or (at your
// option) any later version.
//
// Game_Scheduler is distributed in the hope that it will be
// useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
// Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License along
// with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.


import { FC } from 'react';
import { Box, Button, Container, Typography, Paper } from '@mui/material';

const DISCORD_CLIENT_ID = import.meta.env.VITE_DISCORD_CLIENT_ID || '';
const REDIRECT_URI = `${window.location.origin}/auth/callback`;

export const LoginPage: FC = () => {
  const handleLogin = () => {
    const scopes = ['identify', 'guilds', 'guilds.members.read'];
    const authUrl = `https://discord.com/api/oauth2/authorize?client_id=${DISCORD_CLIENT_ID}&redirect_uri=${encodeURIComponent(REDIRECT_URI)}&response_type=code&scope=${scopes.join('%20')}`;
    window.location.href = authUrl;
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
          <Button
            variant="contained"
            size="large"
            onClick={handleLogin}
            sx={{ mt: 2 }}
          >
            Login with Discord
          </Button>
        </Paper>
      </Box>
    </Container>
  );
};
