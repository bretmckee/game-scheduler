import { FC, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Typography,
  Card,
  CardContent,
  CardActionArea,
  Grid,
  Avatar,
  Box,
  CircularProgress,
  Alert,
} from '@mui/material';
import { useAuth } from '../hooks/useAuth';
import { DiscordGuild } from '../types';

const MANAGE_GUILD_PERMISSION = 0x00000020;

const hasManageGuildPermission = (guild: DiscordGuild): boolean => {
  if (guild.owner) return true;
  const permissions = BigInt(guild.permissions);
  return (permissions & BigInt(MANAGE_GUILD_PERMISSION)) !== BigInt(0);
};

export const GuildListPage: FC = () => {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [guilds, setGuilds] = useState<DiscordGuild[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchGuilds = async () => {
      if (!user) {
        return;
      }

      try {
        setLoading(true);
        setError(null);
        
        if (user.guilds) {
          const managedGuilds = user.guilds.filter(hasManageGuildPermission);
          setGuilds(managedGuilds);
        }
      } catch (err) {
        console.error('Failed to fetch guilds:', err);
        setError('Failed to load guilds. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    if (!authLoading) {
      fetchGuilds();
    }
  }, [user, authLoading]);

  if (authLoading || loading) {
    return (
      <Container sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Container>
    );
  }

  if (error) {
    return (
      <Container sx={{ mt: 4 }}>
        <Alert severity="error">{error}</Alert>
      </Container>
    );
  }

  if (guilds.length === 0) {
    return (
      <Container sx={{ mt: 4 }}>
        <Alert severity="info">
          You don't have management permissions in any guilds with the bot. You need the "Manage Server" permission to configure game sessions.
        </Alert>
      </Container>
    );
  }

  return (
    <Container sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" gutterBottom>
        My Guilds
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Select a guild to manage game sessions and configurations.
      </Typography>

      <Grid container spacing={3}>
        {guilds.map((guild) => (
          <Grid item xs={12} sm={6} md={4} key={guild.id}>
            <Card>
              <CardActionArea onClick={() => navigate(`/guilds/${guild.id}`)}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    {guild.icon ? (
                      <Avatar
                        src={`https://cdn.discordapp.com/icons/${guild.id}/${guild.icon}.png`}
                        alt={guild.name}
                        sx={{ width: 56, height: 56 }}
                      />
                    ) : (
                      <Avatar sx={{ width: 56, height: 56 }}>
                        {guild.name.charAt(0).toUpperCase()}
                      </Avatar>
                    )}
                    <Box>
                      <Typography variant="h6">{guild.name}</Typography>
                      {guild.owner && (
                        <Typography variant="caption" color="primary">
                          Owner
                        </Typography>
                      )}
                    </Box>
                  </Box>
                </CardContent>
              </CardActionArea>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Container>
  );
};
