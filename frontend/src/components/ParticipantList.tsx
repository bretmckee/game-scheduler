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
import { Participant } from '../types';

interface ParticipantListProps {
  participants: Participant[];
  minPlayers?: number;
  maxPlayers?: number;
}

const formatDisplayName = (displayName: string | null): string => {
  if (!displayName) return 'Unknown User';
  return displayName.startsWith('@') ? displayName : `@${displayName}`;
};

export const ParticipantList: FC<ParticipantListProps> = ({
  participants,
  minPlayers = 1,
  maxPlayers,
}) => {
  if (!participants || participants.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No participants yet
      </Typography>
    );
  }

  // Backend returns participants already sorted (priority participants first, then regular by join time)
  // All participants in the list are active (no status filtering needed)
  const maxSlots = maxPlayers || 10;
  const confirmedParticipants = participants.slice(0, maxSlots);
  const waitlistParticipants = participants.slice(maxSlots);

  const joinedCount = confirmedParticipants.length;
  const playerDisplay = maxPlayers
    ? minPlayers === maxPlayers
      ? `${joinedCount}/${maxPlayers}`
      : `${joinedCount}/${minPlayers}-${maxPlayers}`
    : `${joinedCount}`;

  return (
    <Box>
      <Typography variant="body2" sx={{ mb: 1 }}>
        <strong>{playerDisplay}</strong> players
      </Typography>

      <List>
        {confirmedParticipants.map((participant) => (
          <ListItem key={participant.id}>
            <ListItemAvatar>
              <Avatar>{participant.display_name?.[0]?.toUpperCase() || '?'}</Avatar>
            </ListItemAvatar>
            <ListItemText
              primary={formatDisplayName(participant.display_name)}
              secondary={
                participant.pre_filled_position !== null ? 'Added by host' : 'Joined via button'
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
                  primary={formatDisplayName(participant.display_name)}
                  secondary={
                    participant.pre_filled_position !== null ? 'Added by host' : 'Joined via button'
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
