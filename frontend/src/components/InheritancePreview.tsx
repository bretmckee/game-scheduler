import { FC } from 'react';
import { Box, Typography, Chip } from '@mui/material';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';

interface InheritancePreviewProps {
  label: string;
  value: string | number | number[] | null;
  inherited: boolean;
  inheritedFrom?: string;
}

export const InheritancePreview: FC<InheritancePreviewProps> = ({
  label,
  value,
  inherited,
  inheritedFrom = 'guild',
}) => {
  const displayValue = Array.isArray(value) ? value.join(', ') : (value ?? 'Not set');

  return (
    <Box sx={{ mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
      <Typography variant="body2" color="text.secondary">
        {label}:
      </Typography>
      <Typography variant="body2" fontWeight={inherited ? 'normal' : 'bold'}>
        {displayValue}
      </Typography>
      {inherited && (
        <Chip
          icon={<InfoOutlinedIcon />}
          label={`Inherited from ${inheritedFrom}`}
          size="small"
          variant="outlined"
          sx={{ fontSize: '0.7rem', height: '20px' }}
        />
      )}
    </Box>
  );
};
