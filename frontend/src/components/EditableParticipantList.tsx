// Copyright 2025 Bret McKee (bret.mckee@gmail.com)
//
// This file is part of Game_Scheduler. (https://github.com/game-scheduler)
//
// Game_Scheduler is free software: you can redistribute it and/or
// modify it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or (at your
// option) any later version.
//
// Game_Scheduler is distributed in the hope that it will be
// useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
// Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License along
// with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.


import { FC, useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  TextField,
  IconButton,
  Button,
  CircularProgress,
  InputAdornment,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import { apiClient } from '../api/client';

export interface ParticipantInput {
  id: string;
  mention: string;
  isValid: boolean | null;
  validationError?: string;
  preFillPosition: number;
}

interface EditableParticipantListProps {
  participants: ParticipantInput[];
  guildId: string;
  onChange: (participants: ParticipantInput[]) => void;
}

export const EditableParticipantList: FC<EditableParticipantListProps> = ({
  participants,
  guildId,
  onChange,
}) => {
  const [validationTimers, setValidationTimers] = useState<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const validateMention = useCallback(
    async (id: string, mention: string) => {
      if (!mention.trim()) {
        onChange(
          participants.map((p) =>
            p.id === id ? { ...p, isValid: null, validationError: undefined } : p
          )
        );
        return;
      }

      onChange(
        participants.map((p) => (p.id === id ? { ...p, isValid: null, validationError: undefined } : p))
      );

      try {
        const response = await apiClient.post<{ valid: boolean; error?: string }>(
          `/api/v1/guilds/${guildId}/validate-mention`,
          { mention }
        );

        onChange(
          participants.map((p) =>
            p.id === id
              ? {
                  ...p,
                  isValid: response.data.valid,
                  validationError: response.data.error,
                }
              : p
          )
        );
      } catch (error) {
        console.error('Validation failed:', error);
        onChange(
          participants.map((p) =>
            p.id === id
              ? {
                  ...p,
                  isValid: false,
                  validationError: 'Validation failed. Please try again.',
                }
              : p
          )
        );
      }
    },
    [guildId, participants, onChange]
  );

  const handleMentionChange = (id: string, newMention: string) => {
    onChange(
      participants.map((p) =>
        p.id === id ? { ...p, mention: newMention, isValid: null, validationError: undefined } : p
      )
    );

    const timer = validationTimers.get(id);
    if (timer) {
      clearTimeout(timer);
    }

    const newTimer = setTimeout(() => {
      validateMention(id, newMention);
    }, 500);

    setValidationTimers(new Map(validationTimers.set(id, newTimer)));
  };

  useEffect(() => {
    return () => {
      validationTimers.forEach((timer) => clearTimeout(timer));
    };
  }, [validationTimers]);

  const addParticipant = () => {
    const newParticipant: ParticipantInput = {
      id: `temp-${Date.now()}-${Math.random()}`,
      mention: '',
      isValid: null,
      preFillPosition: participants.length + 1,
    };
    onChange([...participants, newParticipant]);
  };

  const removeParticipant = (id: string) => {
    const filtered = participants.filter((p) => p.id !== id);
    const reindexed = filtered.map((p, idx) => ({ ...p, preFillPosition: idx + 1 }));
    onChange(reindexed);
  };

  const moveUp = (index: number) => {
    if (index === 0) return;
    const newParticipants = [...participants];
    [newParticipants[index - 1], newParticipants[index]] = [
      newParticipants[index]!,
      newParticipants[index - 1]!,
    ];
    const reindexed = newParticipants.map((p, idx) => ({ ...p, preFillPosition: idx + 1 }));
    onChange(reindexed);
  };

  const moveDown = (index: number) => {
    if (index === participants.length - 1) return;
    const newParticipants = [...participants];
    [newParticipants[index], newParticipants[index + 1]] = [
      newParticipants[index + 1]!,
      newParticipants[index]!,
    ];
    const reindexed = newParticipants.map((p, idx) => ({ ...p, preFillPosition: idx + 1 }));
    onChange(reindexed);
  };

  return (
    <Box sx={{ mb: 3 }}>
      <Typography variant="h6" gutterBottom>
        Pre-populate Participants (Optional)
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Add Discord users who should be included automatically. Use @mentions or user names. Others
        can join via Discord button.
      </Typography>

      {participants.length === 0 ? (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontStyle: 'italic' }}>
          No pre-populated participants (users can join via Discord button)
        </Typography>
      ) : (
        participants.map((p, index) => (
          <Box key={p.id} sx={{ display: 'flex', gap: 1, mb: 1, alignItems: 'flex-start' }}>
            <TextField
              value={p.mention}
              onChange={(e) => handleMentionChange(p.id, e.target.value)}
              placeholder="@username or Discord user"
              error={p.isValid === false}
              helperText={p.validationError}
              fullWidth
              size="small"
              InputProps={{
                endAdornment: p.isValid === null && p.mention.trim() ? (
                  <InputAdornment position="end">
                    <CircularProgress size={20} />
                  </InputAdornment>
                ) : p.isValid === true ? (
                  <InputAdornment position="end">
                    <CheckCircleIcon color="success" fontSize="small" />
                  </InputAdornment>
                ) : p.isValid === false ? (
                  <InputAdornment position="end">
                    <ErrorIcon color="error" fontSize="small" />
                  </InputAdornment>
                ) : null,
              }}
            />
            <IconButton onClick={() => moveUp(index)} disabled={index === 0} size="small">
              <ArrowUpwardIcon />
            </IconButton>
            <IconButton
              onClick={() => moveDown(index)}
              disabled={index === participants.length - 1}
              size="small"
            >
              <ArrowDownwardIcon />
            </IconButton>
            <IconButton onClick={() => removeParticipant(p.id)} size="small" color="error">
              <DeleteIcon />
            </IconButton>
          </Box>
        ))
      )}

      <Button onClick={addParticipant} startIcon={<AddIcon />} variant="outlined" sx={{ mt: 1 }}>
        Add Participant
      </Button>
    </Box>
  );
};
