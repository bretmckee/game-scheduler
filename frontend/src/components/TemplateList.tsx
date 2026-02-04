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
import { Box, Typography } from '@mui/material';
import { TemplateCard } from './TemplateCard';
import { GameTemplate, DiscordRole } from '../types';
import { UI } from '../constants/ui';

interface TemplateListProps {
  templates: GameTemplate[];
  roles: DiscordRole[];
  onEdit: (template: GameTemplate) => void;
  onDelete: (template: GameTemplate) => void;
  onSetDefault: (template: GameTemplate) => void;
  onReorder: (templateIds: string[]) => void;
}

export const TemplateList: FC<TemplateListProps> = ({
  templates,
  roles,
  onEdit,
  onDelete,
  onSetDefault,
  onReorder,
}) => {
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);

  const handleDragStart = (index: number) => {
    setDraggedIndex(index);
  };

  const handleDragOver = (index: number, e: React.DragEvent) => {
    e.preventDefault();
    if (draggedIndex === null || draggedIndex === index) return;
    setDragOverIndex(index);
  };

  const handleDragEnd = () => {
    if (draggedIndex === null || dragOverIndex === null || draggedIndex === dragOverIndex) {
      setDraggedIndex(null);
      setDragOverIndex(null);
      return;
    }

    const newTemplates = [...templates];
    const [draggedTemplate] = newTemplates.splice(draggedIndex, 1);
    newTemplates.splice(dragOverIndex, 0, draggedTemplate!);

    const templateIds = newTemplates.map((t) => t.id);
    onReorder(templateIds);

    setDraggedIndex(null);
    setDragOverIndex(null);
  };

  const handleDragLeave = () => {
    setDragOverIndex(null);
  };

  if (templates.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Typography variant="body1" color="text.secondary">
          No templates found. Create your first template to get started.
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      {templates.map((template, index) => (
        <Box
          key={template.id}
          draggable
          onDragStart={() => handleDragStart(index)}
          onDragOver={(e) => handleDragOver(index, e)}
          onDragEnd={handleDragEnd}
          onDragLeave={handleDragLeave}
          sx={{
            opacity: draggedIndex === index ? UI.HOVER_OPACITY : 1,
            transition: 'opacity 0.2s',
            borderTop: dragOverIndex === index ? '2px solid primary.main' : 'none',
          }}
        >
          <TemplateCard
            template={template}
            roles={roles}
            onEdit={onEdit}
            onDelete={onDelete}
            onSetDefault={onSetDefault}
            dragHandleProps={{
              style: { cursor: 'grab' },
            }}
          />
        </Box>
      ))}
    </Box>
  );
};
