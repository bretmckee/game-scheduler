// Copyright 2026 Bret McKee
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
import { Chip, Tooltip } from '@mui/material';
import PersonOffIcon from '@mui/icons-material/PersonOff';
import { MemberRef } from '../types/memberRef';

interface MemberChipProps {
  member: MemberRef;
}

const DEPARTED_TOOLTIP = 'No longer in this server';

/**
 * Renders a Discord member as an `@label` chip, or as a visually distinct
 * "unknown member" chip when the member has left the server.
 *
 * The departed chip is distinguished by styling and test id rather than by its
 * text, so a real member whose name happens to match can never be mistaken
 * for it.
 */
export const MemberChip: FC<MemberChipProps> = ({ member }) => {
  if (member.label === null) {
    return (
      <Tooltip title={DEPARTED_TOOLTIP}>
        <Chip
          data-testid="unknown-member-chip"
          aria-label={`Unknown member, ${DEPARTED_TOOLTIP.toLowerCase()}`}
          icon={<PersonOffIcon />}
          label="unknown member"
          size="small"
          variant="outlined"
          sx={{ borderStyle: 'dashed', color: 'text.disabled', fontStyle: 'italic' }}
        />
      </Tooltip>
    );
  }

  return (
    <Chip
      data-testid="member-chip"
      label={`@${member.label}`}
      size="small"
      variant="outlined"
      color="primary"
    />
  );
};
