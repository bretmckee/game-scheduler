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
  maxPlayers?: number;
}

export const ParticipantList: FC<ParticipantListProps> = ({
  participants,
  maxPlayers,
}) => {
  if (!participants || participants.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No participants yet
      </Typography>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'JOINED':
        return 'success';
      case 'PLACEHOLDER':
        return 'default';
      case 'DROPPED':
        return 'error';
      case 'WAITLIST':
        return 'warning';
      default:
        return 'default';
    }
  };

  return (
    <Box>
      {maxPlayers && (
        <Typography variant="body2" sx={{ mb: 1 }}>
          <strong>
            {participants.filter((p) => p.status === 'JOINED').length}/
            {maxPlayers}
          </strong>{' '}
          players
        </Typography>
      )}

      <List>
        {participants.map((participant) => (
          <ListItem key={participant.id}>
            <ListItemAvatar>
              <Avatar>
                {participant.display_name?.[0]?.toUpperCase() || '?'}
              </Avatar>
            </ListItemAvatar>
            <ListItemText
              primary={participant.display_name || 'Unknown User'}
              secondary={
                participant.is_pre_populated ? 'Pre-populated' : 'Joined via button'
              }
            />
            <Chip
              label={participant.status}
              color={getStatusColor(participant.status)}
              size="small"
            />
          </ListItem>
        ))}
      </List>
    </Box>
  );
};
