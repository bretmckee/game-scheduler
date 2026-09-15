// Copyright 2026 Bret McKee
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
  Button,
  CircularProgress,
  Alert,
  Container,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  SelectChangeEvent,
  Typography,
} from '@mui/material';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { addDays } from 'date-fns';
import { useNavigate, useParams } from 'react-router';
import { apiClient } from '../api/client';
import { Channel, GameSession, SignupMethod } from '../types';
import { GameForm, GameFormData } from '../components/GameForm';
import { canUserManageBotSettings } from '../utils/permissions';

type CarryoverOption = 'NO' | 'YES' | 'YES_WITH_DEADLINE';

const CARRYOVER_OPTIONS: { value: CarryoverOption; label: string }[] = [
  { value: 'NO', label: 'No — start with an empty roster' },
  { value: 'YES', label: 'Yes — carry over existing players' },
  { value: 'YES_WITH_DEADLINE', label: 'Yes — carry over with confirmation deadline' },
];

const DEFAULT_DAYS_AHEAD = 14;

/**
 * Build the frozen `GameForm` `initialData` for Stage 2, snapshotting the carryover
 * selections as they stood the moment "Continue" was clicked.
 *
 * `GameForm` rebuilds its internal form state whenever the `initialData` object it
 * receives changes identity (see its `initialData`-keyed `useEffect`), so this object
 * must be computed exactly once per Stage-2 mount rather than re-derived from live
 * carryover state -- otherwise toggling a carryover select after Stage 2 has mounted
 * would silently discard any host edits already made to the form (title, description,
 * etc.). Callers must store the result in state and never recompute it while Stage 2 is
 * mounted.
 */
function buildStage2InitialData(
  sourceGame: GameSession,
  playerCarryover: CarryoverOption,
  waitlistCarryover: CarryoverOption
): Partial<GameSession> {
  const keepPlayers = playerCarryover !== 'NO';
  const keepWaitlist = waitlistCarryover !== 'NO';

  const initialData: Partial<GameSession> = {
    ...sourceGame,
    // Cleared so GameForm's own "leave empty = post now" default applies, instead of
    // inheriting the source game's own post time.
    post_at: null,
    scheduled_at: addDays(new Date(sourceGame.scheduled_at), DEFAULT_DAYS_AHEAD).toISOString(),
  };

  if (sourceGame.signup_method === SignupMethod.HOST_SELECTED_WITH_WAITLIST) {
    initialData.confirmed_participants = keepPlayers ? sourceGame.confirmed_participants : [];
    initialData.waitlist_participants = keepWaitlist ? sourceGame.waitlist_participants : [];
  } else {
    initialData.participants = keepPlayers ? sourceGame.participants : [];
  }

  return initialData;
}

export const CloneGame: FC = () => {
  const { gameId } = useParams<{ gameId: string }>();
  const navigate = useNavigate();

  const [sourceGame, setSourceGame] = useState<GameSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [isBotManager, setIsBotManager] = useState(false);

  const [playerCarryover, setPlayerCarryover] = useState<CarryoverOption>('NO');
  const [waitlistCarryover, setWaitlistCarryover] = useState<CarryoverOption>('NO');
  const [playerDeadline, setPlayerDeadline] = useState<Date | null>(null);
  const [waitlistDeadline, setWaitlistDeadline] = useState<Date | null>(null);
  const [continueError, setContinueError] = useState<string | null>(null);

  // Non-null once "Continue" has been clicked -- Stage 2's frozen GameForm initialData,
  // and the flag for whether Stage 2 is mounted.
  const [stage2InitialData, setStage2InitialData] = useState<Partial<GameSession> | null>(null);

  useEffect(() => {
    if (!gameId) return;

    const fetchGame = async () => {
      try {
        setLoading(true);
        setFetchError(null);
        const response = await apiClient.get<GameSession>(`/api/v1/games/${gameId}`);
        setSourceGame(response.data);
      } catch {
        setFetchError('Failed to load game. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchGame();
  }, [gameId]);

  // No /guilds/{id}/roles or /guilds/{id}/channels fetch is needed here (GameForm has no
  // roles prop, and the clone screen's single channel is synthesized from sourceGame
  // below) -- only the bot-manager check CreateGame.tsx already makes the same way.
  useEffect(() => {
    if (!sourceGame) return;
    let cancelled = false;

    canUserManageBotSettings(sourceGame.guild_id).then((result) => {
      if (!cancelled) setIsBotManager(result);
    });

    return () => {
      cancelled = true;
    };
  }, [sourceGame]);

  const handleContinue = () => {
    if (!sourceGame) return;

    const now = new Date();
    if (playerCarryover === 'YES_WITH_DEADLINE') {
      if (!playerDeadline) {
        setContinueError('Player deadline is required when using deadline carryover.');
        return;
      }
      if (playerDeadline <= now) {
        setContinueError('Player deadline must be in the future.');
        return;
      }
    }
    if (waitlistCarryover === 'YES_WITH_DEADLINE') {
      if (!waitlistDeadline) {
        setContinueError('Waitlist deadline is required when using deadline carryover.');
        return;
      }
      if (waitlistDeadline <= now) {
        setContinueError('Waitlist deadline must be in the future.');
        return;
      }
    }

    setContinueError(null);
    setStage2InitialData(buildStage2InitialData(sourceGame, playerCarryover, waitlistCarryover));
  };

  // Phase 9 wires this to POST /api/v1/games/{gameId}/clone as multipart form data; Phase
  // 8 covers Stage 1/Stage 2 rendering only.
  const handleSubmit = async (_formData: GameFormData): Promise<void> => {
    throw new Error('Clone submission not yet implemented');
  };

  if (loading) {
    return (
      <Container maxWidth="sm" sx={{ mt: 4, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  if (fetchError || !sourceGame) {
    return (
      <Container maxWidth="sm" sx={{ mt: 4 }}>
        <Alert severity="error">{fetchError ?? 'Game not found'}</Alert>
        <Button sx={{ mt: 2 }} onClick={() => navigate(-1)}>
          Back
        </Button>
      </Container>
    );
  }

  // Design Note 7: a single-item channel list synthesized directly from the source
  // game's own channel, not a /guilds/{id}/channels fetch (clone has no channel-override
  // field, per the backend contract).
  const channels: Channel[] = [
    {
      id: sourceGame.channel_id,
      guild_id: sourceGame.guild_id,
      channel_id: sourceGame.channel_id,
      channel_name: sourceGame.channel_name ?? '',
      is_active: true,
      created_at: '',
      updated_at: '',
    },
  ];

  return (
    <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
      <Paper sx={{ p: 4, mb: 3 }}>
        <Typography variant="h5" gutterBottom>
          Clone Game
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Cloning: <strong>{sourceGame.title}</strong>
        </Typography>

        {continueError && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {continueError}
          </Alert>
        )}

        <LocalizationProvider dateAdapter={AdapterDateFns}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <FormControl fullWidth>
              <InputLabel id="player-carryover-label">Player Carryover</InputLabel>
              <Select
                labelId="player-carryover-label"
                value={playerCarryover}
                label="Player Carryover"
                onChange={(e: SelectChangeEvent<CarryoverOption>) =>
                  setPlayerCarryover(e.target.value as CarryoverOption)
                }
              >
                {CARRYOVER_OPTIONS.map((opt) => (
                  <MenuItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {playerCarryover === 'YES_WITH_DEADLINE' && (
              <DateTimePicker
                label="Player Confirmation Deadline"
                value={playerDeadline}
                onChange={(value) => setPlayerDeadline(value)}
                slotProps={{
                  textField: { required: true, fullWidth: true },
                }}
              />
            )}

            <FormControl fullWidth>
              <InputLabel id="waitlist-carryover-label">Waitlist Carryover</InputLabel>
              <Select
                labelId="waitlist-carryover-label"
                value={waitlistCarryover}
                label="Waitlist Carryover"
                onChange={(e: SelectChangeEvent<CarryoverOption>) =>
                  setWaitlistCarryover(e.target.value as CarryoverOption)
                }
              >
                {CARRYOVER_OPTIONS.map((opt) => (
                  <MenuItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {waitlistCarryover === 'YES_WITH_DEADLINE' && (
              <DateTimePicker
                label="Waitlist Confirmation Deadline"
                value={waitlistDeadline}
                onChange={(value) => setWaitlistDeadline(value)}
                slotProps={{
                  textField: { required: true, fullWidth: true },
                }}
              />
            )}

            {/* Continue is only needed to move from Stage 1 to Stage 2; once Stage 2 has
                mounted, the carryover controls above stay editable in place. */}
            {!stage2InitialData && (
              <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                <Button variant="contained" onClick={handleContinue}>
                  Continue
                </Button>
              </Box>
            )}
          </Box>
        </LocalizationProvider>
      </Paper>

      {stage2InitialData && (
        <GameForm
          mode="create"
          initialData={stage2InitialData}
          guildId={sourceGame.guild_id}
          guildName={sourceGame.guild_name ?? undefined}
          canChangeChannel={false}
          isBotManager={isBotManager}
          channels={channels}
          onSubmit={handleSubmit}
          onCancel={() => navigate(`/games/${gameId}`)}
        />
      )}
    </Container>
  );
};
