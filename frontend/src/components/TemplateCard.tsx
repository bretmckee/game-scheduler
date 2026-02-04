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
import { Card, CardContent, Typography, Box, IconButton, Chip, Stack } from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import StarIcon from '@mui/icons-material/Star';
import StarBorderIcon from '@mui/icons-material/StarBorder';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import { GameTemplate, DiscordRole } from '../types';

interface TemplateCardProps {
  template: GameTemplate;
  roles: DiscordRole[];
  onEdit: (template: GameTemplate) => void;
  onDelete: (template: GameTemplate) => void;
  onSetDefault: (template: GameTemplate) => void;
  dragHandleProps?: any;
}

export const TemplateCard: FC<TemplateCardProps> = ({
  template,
  roles,
  onEdit,
  onDelete,
  onSetDefault,
  dragHandleProps,
}) => {
  const getRoleNames = (roleIds: string[] | null | undefined): string => {
    if (!roleIds || roleIds.length === 0) return 'None';
    return roleIds.map((id) => roles.find((r) => r.id === id)?.name || 'Unknown').join(', ');
  };
  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
          <Box {...dragHandleProps} sx={{ cursor: 'grab', pt: 0.5 }}>
            <DragIndicatorIcon color="action" />
          </Box>

          <Box sx={{ flexGrow: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
              <Typography variant="h6">{template.name}</Typography>
              {template.is_default && <Chip label="Default" size="small" color="primary" />}
            </Box>

            {template.description && (
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {template.description}
              </Typography>
            )}

            <Stack spacing={1}>
              <Typography variant="body2">
                <strong>Channel:</strong> {template.channel_name}
              </Typography>

              {template.max_players !== null && (
                <Typography variant="body2">
                  <strong>Max Players:</strong> {template.max_players}
                </Typography>
              )}

              {template.expected_duration_minutes !== null && (
                <Typography variant="body2">
                  <strong>Duration:</strong> {template.expected_duration_minutes} minutes
                </Typography>
              )}

              {template.reminder_minutes && template.reminder_minutes.length > 0 && (
                <Typography variant="body2">
                  <strong>Reminders:</strong> {template.reminder_minutes.join(', ')} minutes before
                </Typography>
              )}

              {template.where && (
                <Typography variant="body2">
                  <strong>Location:</strong> {template.where}
                </Typography>
              )}

              {template.signup_instructions && (
                <Typography variant="body2">
                  <strong>Signup Instructions:</strong> {template.signup_instructions}
                </Typography>
              )}

              <Typography variant="body2">
                <strong>Notify Roles:</strong> {getRoleNames(template.notify_role_ids)}
              </Typography>

              <Typography variant="body2">
                <strong>Allowed Player Roles:</strong>{' '}
                {getRoleNames(template.allowed_player_role_ids)}
              </Typography>

              <Typography variant="body2">
                <strong>Allowed Host Roles:</strong> {getRoleNames(template.allowed_host_role_ids)}
              </Typography>
            </Stack>
          </Box>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            <IconButton
              size="small"
              onClick={() => onSetDefault(template)}
              title={template.is_default ? 'Already default' : 'Set as default'}
              disabled={template.is_default}
            >
              {template.is_default ? <StarIcon color="primary" /> : <StarBorderIcon />}
            </IconButton>

            <IconButton size="small" onClick={() => onEdit(template)} title="Edit template">
              <EditIcon />
            </IconButton>

            <IconButton
              size="small"
              onClick={() => onDelete(template)}
              title={template.is_default ? 'Cannot delete default template' : 'Delete template'}
              disabled={template.is_default}
              color={template.is_default ? 'default' : 'error'}
            >
              <DeleteIcon />
            </IconButton>
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
};
