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

import { FC, useState } from 'react';
import { Box, Typography, TextField, IconButton, Button } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import { UI } from '../constants/ui';
import DeleteIcon from '@mui/icons-material/Delete';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import ErrorIcon from '@mui/icons-material/Error';

export interface ParticipantInput {
  id: string;
  mention: string;
  preFillPosition: number;
  isExplicitlyPositioned?: boolean; // Track if user explicitly moved/added this participant
  isReadOnly?: boolean; // Joined participants can't be edited, only reordered/removed
  validationStatus?: 'valid' | 'unknown' | 'invalid'; // Track validation state
}

interface EditableParticipantListProps {
  participants: ParticipantInput[];
  onChange: (participants: ParticipantInput[]) => void;
}

export const EditableParticipantList: FC<EditableParticipantListProps> = ({
  participants,
  onChange,
}) => {
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);

  const handleMentionChange = (id: string, newMention: string) => {
    onChange(
      participants.map((p) =>
        p.id === id ? { ...p, mention: newMention, validationStatus: 'unknown' as const } : p
      )
    );
  };

  const addParticipant = () => {
    const newParticipant: ParticipantInput = {
      id: `temp-${Date.now()}-${Math.random()}`,
      mention: '',
      preFillPosition: participants.length + 1,
      isExplicitlyPositioned: true, // New participants are explicitly positioned
      validationStatus: 'unknown',
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
      { ...newParticipants[index]!, isExplicitlyPositioned: true }, // Mark moved participant
      newParticipants[index - 1]!, // Other participant keeps its state
    ];
    const reindexed = newParticipants.map((p, idx) => ({
      ...p,
      preFillPosition: idx + 1,
    }));
    onChange(reindexed);
  };

  const moveDown = (index: number) => {
    if (index === participants.length - 1) return;
    const newParticipants = [...participants];
    [newParticipants[index], newParticipants[index + 1]] = [
      newParticipants[index + 1]!, // Other participant keeps its state
      { ...newParticipants[index]!, isExplicitlyPositioned: true }, // Mark moved participant
    ];
    const reindexed = newParticipants.map((p, idx) => ({
      ...p,
      preFillPosition: idx + 1,
    }));
    onChange(reindexed);
  };

  const handleDragStart = (index: number) => {
    setDraggedIndex(index);
  };

  const handleDragOver = (e: React.DragEvent, _index: number) => {
    e.preventDefault(); // Allow drop
  };

  const handleDrop = (e: React.DragEvent, dropIndex: number) => {
    e.preventDefault();

    if (draggedIndex === null || draggedIndex === dropIndex) {
      setDraggedIndex(null);
      return;
    }

    const newParticipants = [...participants];
    const draggedItem = { ...newParticipants[draggedIndex]!, isExplicitlyPositioned: true };

    // Remove dragged item
    newParticipants.splice(draggedIndex, 1);
    // Insert at new position
    newParticipants.splice(dropIndex, 0, draggedItem);

    // Reindex positions
    const reindexed = newParticipants.map((p, idx) => ({
      ...p,
      preFillPosition: idx + 1,
    }));

    onChange(reindexed);
    setDraggedIndex(null);
  };

  const handleDragEnd = () => {
    setDraggedIndex(null);
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
          No participants added by host (users can join via Discord button)
        </Typography>
      ) : (
        participants.map((p, index) => (
          <Box
            key={p.id}
            draggable
            onDragStart={() => handleDragStart(index)}
            onDragOver={(e) => handleDragOver(e, index)}
            onDrop={(e) => handleDrop(e, index)}
            onDragEnd={handleDragEnd}
            sx={{
              display: 'flex',
              gap: 1,
              mb: 1,
              alignItems: 'flex-start',
              cursor: 'move',
              opacity: draggedIndex === index ? UI.HOVER_OPACITY : 1,
              transition: 'opacity 0.2s',
              '&:hover': {
                backgroundColor: 'action.hover',
              },
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexGrow: 1 }}>
              {p.validationStatus === 'valid' && (
                <CheckCircleIcon color="success" fontSize="small" titleAccess="Validated" />
              )}
              {p.validationStatus === 'invalid' && (
                <ErrorIcon color="error" fontSize="small" titleAccess="Validation failed" />
              )}
              {(!p.validationStatus || p.validationStatus === 'unknown') && (
                <HelpOutlineIcon color="action" fontSize="small" titleAccess="Not validated" />
              )}
              <TextField
                value={p.mention}
                onChange={(e) => handleMentionChange(p.id, e.target.value)}
                placeholder="@username or Discord user"
                helperText={p.isReadOnly ? 'Joined player (can reorder or remove)' : undefined}
                fullWidth
                size="small"
                disabled={p.isReadOnly}
              />
            </Box>
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
