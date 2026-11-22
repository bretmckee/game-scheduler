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
import { toMemberRef } from '../memberRef';

describe('toMemberRef', () => {
  it('maps a present member to its id and live label', () => {
    expect(toMemberRef({ discord_id: '111', display_name: 'Kallisti' })).toEqual({
      id: '111',
      label: 'Kallisti',
    });
  });

  it('maps a departed member (discord_id set, no name) to a null label', () => {
    expect(toMemberRef({ discord_id: '222', display_name: null })).toEqual({
      id: '222',
      label: null,
    });
  });

  it('returns null for a placeholder (no discord_id)', () => {
    expect(toMemberRef({ discord_id: null, display_name: 'Bob from work' })).toBeNull();
  });
});
