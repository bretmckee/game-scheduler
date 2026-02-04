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

import { FC } from 'react';
import {
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Avatar,
  Chip,
  Box,
  Typography,
} from '@mui/material';
import { Participant, ParticipantType } from '../types';
import { formatParticipantDisplay } from '../utils/formatParticipant';
import { UI } from '../constants/ui';

interface ParticipantListProps {
  participants: Participant[];
  maxPlayers?: number;
}

export const ParticipantList: FC<ParticipantListProps> = ({ participants, maxPlayers }) => {
  if (!participants || participants.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No participants yet
      </Typography>
    );
  }

  // Backend returns participants already sorted (priority participants first, then regular by join time)
  // All participants in the list are active (no status filtering needed)
  const maxSlots = maxPlayers || UI.DEFAULT_MAX_PLAYERS;
  const confirmedParticipants = participants.slice(0, maxSlots);
  const waitlistParticipants = participants.slice(maxSlots);

  return (
    <Box>
      <List>
        {confirmedParticipants.map((participant) => (
          <ListItem key={participant.id}>
            <ListItemAvatar>
              <Avatar>{participant.display_name?.[0]?.toUpperCase() || '?'}</Avatar>
            </ListItemAvatar>
            <ListItemText
              primary={formatParticipantDisplay(participant.display_name, participant.discord_id)}
              secondary={
                participant.position_type === ParticipantType.HOST_ADDED
                  ? 'Added by host'
                  : 'Joined via button'
              }
            />
          </ListItem>
        ))}
      </List>

      {waitlistParticipants.length > 0 && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="body2" sx={{ mb: 1 }}>
            <strong>🎫 Waitlist ({waitlistParticipants.length})</strong>
          </Typography>
          <List>
            {waitlistParticipants.map((participant, index) => (
              <ListItem key={participant.id}>
                <ListItemAvatar>
                  <Avatar sx={{ bgcolor: 'warning.main' }}>{index + 1}</Avatar>
                </ListItemAvatar>
                <ListItemText
                  primary={formatParticipantDisplay(
                    participant.display_name,
                    participant.discord_id
                  )}
                  secondary={
                    participant.position_type === ParticipantType.HOST_ADDED
                      ? 'Added by host'
                      : 'Joined via button'
                  }
                />
                <Chip label="Waitlist" color="warning" size="small" />
              </ListItem>
            ))}
          </List>
        </Box>
      )}
    </Box>
  );
};
