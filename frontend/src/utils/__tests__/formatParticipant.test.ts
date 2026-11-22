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

import { describe, it, expect } from 'vitest';
import { formatParticipantDisplay } from '../formatParticipant';

describe('formatParticipantDisplay', () => {
  it('prefixes a present Discord member with @', () => {
    expect(formatParticipantDisplay('Kallisti', '111')).toBe('@Kallisti');
  });

  it('does not double the @ when the name already starts with one', () => {
    expect(formatParticipantDisplay('@Kallisti', '111')).toBe('@Kallisti');
  });

  it('returns a placeholder name as-is', () => {
    expect(formatParticipantDisplay('Bob from work', null)).toBe('Bob from work');
  });

  it('returns empty text for a departed member instead of a raw <@id>', () => {
    expect(formatParticipantDisplay(null, '222')).toBe('');
  });

  it('returns empty text for a nameless placeholder instead of "Unknown User"', () => {
    expect(formatParticipantDisplay(null, null)).toBe('');
  });
});
