import { FC } from 'react';
import { Alert, AlertTitle, Box, Typography } from '@mui/material';
import { MentionChip } from './MentionChip';

interface ValidationError {
  input: string;
  reason: string;
  suggestions: Array<{
    discordId: string;
    username: string;
    displayName: string;
  }>;
}

interface ValidationErrorsProps {
  errors: ValidationError[];
  onSuggestionClick: (originalInput: string, newUsername: string) => void;
}

export const ValidationErrors: FC<ValidationErrorsProps> = ({ 
  errors, 
  onSuggestionClick 
}) => {
  return (
    <Alert severity="error" sx={{ mb: 2 }}>
      <AlertTitle>Could not resolve some @mentions</AlertTitle>
      {errors.map((err, idx) => (
        <Box key={idx} mb={2}>
          <Typography variant="body2">
            <strong>{err.input}</strong>: {err.reason}
          </Typography>
          {err.suggestions.length > 0 && (
            <Box ml={2} mt={1}>
              <Typography variant="caption" display="block" gutterBottom>
                Did you mean:
              </Typography>
              {err.suggestions.map((sugg) => (
                <MentionChip
                  key={sugg.discordId}
                  username={sugg.username}
                  displayName={sugg.displayName}
                  onClick={() => onSuggestionClick(err.input, `@${sugg.username}`)}
                />
              ))}
            </Box>
          )}
        </Box>
      ))}
    </Alert>
  );
};
