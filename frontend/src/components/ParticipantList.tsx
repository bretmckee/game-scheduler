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
  confirmedParticipants: Participant[];
  waitlistParticipants: Participant[];
  maxPlayers?: number;
}

export const ParticipantList: FC<ParticipantListProps> = ({
  confirmedParticipants,
  waitlistParticipants,
  maxPlayers,
}) => {
  const maxSlots = maxPlayers || UI.DEFAULT_MAX_PLAYERS;
  const openSlots = Math.max(0, maxSlots - confirmedParticipants.length);

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
        {Array.from({ length: openSlots }).map((_, i) => (
          <ListItem key={`open-slot-${i}`}>
            <ListItemAvatar>
              <Avatar sx={{ bgcolor: 'action.disabledBackground' }}>—</Avatar>
            </ListItemAvatar>
            <ListItemText
              primary={
                <Typography variant="body2" sx={{ fontStyle: 'italic', color: 'text.secondary' }}>
                  open slot
                </Typography>
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
