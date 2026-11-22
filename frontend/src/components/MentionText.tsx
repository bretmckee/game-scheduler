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

import { FC, Fragment, ReactNode } from 'react';
import { Chip, Tooltip } from '@mui/material';
import { MemberChip } from './MemberChip';
import { MentionSegment, parseTokens } from '../utils/mentionTokens';

interface MentionTextProps {
  text: string | null | undefined;
  /** Truncate to this many visible characters, never cutting a mention in half. */
  maxLength?: number;
}

const UNKNOWN_CHANNEL_TOOLTIP = 'Channel not found in this server';
const ELLIPSIS = '...';

function visibleLength(segment: MentionSegment): number {
  if (segment.kind === 'text') {
    return segment.text.length;
  }
  return segment.label === null ? 0 : segment.label.length + 1;
}

/**
 * Keep whole segments until `maxLength` visible characters are used. A text
 * segment may be cut; a mention that does not fit is dropped entirely.
 */
function truncateSegments(segments: MentionSegment[], maxLength: number): MentionSegment[] {
  const total = segments.reduce((sum, segment) => sum + visibleLength(segment), 0);
  if (total <= maxLength) {
    return segments;
  }

  const kept: MentionSegment[] = [];
  let remaining = maxLength;
  for (const segment of segments) {
    const length = visibleLength(segment);
    if (length <= remaining) {
      kept.push(segment);
      remaining -= length;
      continue;
    }
    if (segment.kind === 'text' && remaining > 0) {
      kept.push({ kind: 'text', text: segment.text.substring(0, remaining) });
    }
    break;
  }

  const last = kept[kept.length - 1];
  if (last?.kind === 'text') {
    kept[kept.length - 1] = { kind: 'text', text: last.text.trimEnd() + ELLIPSIS };
  } else {
    kept.push({ kind: 'text', text: ELLIPSIS });
  }
  return kept;
}

function renderSegment(segment: MentionSegment): ReactNode {
  if (segment.kind === 'text') {
    return segment.text;
  }
  if (segment.kind === 'user') {
    return <MemberChip member={{ id: segment.id, label: segment.label }} />;
  }
  if (segment.label === null) {
    return (
      <Tooltip title={UNKNOWN_CHANNEL_TOOLTIP}>
        <Chip
          data-testid="unknown-channel-chip"
          aria-label={`Unknown channel, ${UNKNOWN_CHANNEL_TOOLTIP.toLowerCase()}`}
          label="unknown channel"
          size="small"
          variant="outlined"
          sx={{ borderStyle: 'dashed', color: 'text.disabled', fontStyle: 'italic' }}
        />
      </Tooltip>
    );
  }
  return (
    <Chip data-testid="channel-chip" label={`#${segment.label}`} size="small" variant="outlined" />
  );
}

/**
 * Renders game text containing `<@id|label>` / `<#id|label>` tokens, showing
 * members and channels as chips. Token-free text renders unchanged.
 */
export const MentionText: FC<MentionTextProps> = ({ text, maxLength }) => {
  if (!text) {
    return null;
  }
  const parsed = parseTokens(text);
  const segments = maxLength === undefined ? parsed : truncateSegments(parsed, maxLength);
  return (
    <>
      {segments.map((segment, index) => (
        <Fragment key={index}>{renderSegment(segment)}</Fragment>
      ))}
    </>
  );
};
