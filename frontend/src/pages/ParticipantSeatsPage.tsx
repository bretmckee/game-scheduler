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
import { Link as RouterLink, useParams } from 'react-router';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import {
  Alert,
  Box,
  CircularProgress,
  Container,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { apiClient } from '../api/client';
import { getErrorMessage } from '../utils/errors';
import { ParticipantSeat, ParticipantSeats } from '../types';

const seatLabel = (seat: ParticipantSeat): string => `@${seat.name || 'Unknown'}`;

/**
 * Standalone page table of a game's linked Discord users and their 1-based
 * positions in canonical order. Placeholder rows never appear - the endpoint
 * excludes them server-side and renumbers seats over real users only.
 */
export const ParticipantSeatsPage: FC = () => {
  const { gameId } = useParams<{ gameId: string }>();
  // null until the first fetch settles: distinguishes "loading" from "empty".
  const [seats, setSeats] = useState<ParticipantSeat[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!gameId) return;

    let cancelled = false;
    const loadSeats = async () => {
      try {
        const response = await apiClient.get<ParticipantSeats>(
          `/api/v1/games/${gameId}/participant-seats`
        );
        if (!cancelled) {
          setSeats(response.data.seats ?? []);
        }
      } catch (err: unknown) {
        if (cancelled) return;
        console.error('Failed to load participant positions:', err);
        const detail = getErrorMessage(err);
        setError(
          detail
            ? `Could not load participant positions: ${detail}`
            : 'Could not load participant positions. Please try again.'
        );
      }
    };

    void loadSeats();
    return () => {
      cancelled = true;
    };
  }, [gameId]);

  return (
    <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="body2" color="primary.main">
        <RouterLink
          to={`/games/${gameId}`}
          style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}
        >
          <ArrowBackIcon fontSize="small" />
          Back to game
        </RouterLink>
      </Typography>

      <Box sx={{ my: 3 }}>
        <Typography variant="h6" gutterBottom>
          Participants
        </Typography>

        {error ? (
          <Alert severity="error">{error}</Alert>
        ) : seats === null ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
            <CircularProgress size={28} />
          </Box>
        ) : seats.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No participants yet.
          </Typography>
        ) : (
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Participant</TableCell>
                  <TableCell align="right">Position</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {seats.map((seat) => (
                  <TableRow key={seat.discord_id}>
                    <TableCell>{seatLabel(seat)}</TableCell>
                    <TableCell align="right">{seat.position}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>
        )}
      </Box>
    </Container>
  );
};
