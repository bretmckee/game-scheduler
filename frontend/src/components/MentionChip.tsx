import { FC } from 'react';
import { Chip } from '@mui/material';

interface MentionChipProps {
  username: string;
  displayName: string;
  onClick: () => void;
}

export const MentionChip: FC<MentionChipProps> = ({ username, displayName, onClick }) => {
  return (
    <Chip
      label={`@${username} (${displayName})`}
      onClick={onClick}
      sx={{
        m: 0.5,
        cursor: 'pointer',
        '&:hover': {
          backgroundColor: 'primary.dark',
        },
      }}
      color="primary"
      variant="outlined"
      clickable
    />
  );
};
