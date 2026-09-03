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
import { resolveMySeating, type SeatingGameLike, type CallerIdentity } from '../seating';

const caller: CallerIdentity = { user_uuid: 'me-uuid', discordId: '111' };

describe('resolveMySeating', () => {
  it('returns null when there is no authenticated caller', () => {
    const game: SeatingGameLike = { confirmed_participants: [{ user_id: 'x' }] };
    expect(resolveMySeating(game)).toBeNull();
    expect(resolveMySeating(game, undefined)).toBeNull();
  });

  it('classifies the host first, even when also seated elsewhere', () => {
    const game: SeatingGameLike = {
      host: { user_id: 'me-uuid' },
      waitlist_participants: [{ user_id: 'me-uuid' }],
    };
    expect(resolveMySeating(game, caller)).toBe('host');
  });

  it('matches the host by Discord id when user ids are absent', () => {
    const game: SeatingGameLike = { host: { discord_id: '111' } };
    expect(resolveMySeating(game, { user_uuid: 'something-else', discordId: '111' })).toBe('host');
  });

  it('classifies a confirmed participant (not host) as "confirmed"', () => {
    const game: SeatingGameLike = {
      host: { user_id: 'someone-else' },
      confirmed_participants: [{ user_id: 'other-1' }, { user_id: 'me-uuid' }],
      waitlist_participants: [],
    };
    expect(resolveMySeating(game, caller)).toBe('confirmed');
  });

  it('falls back to Discord id for confirmed matching when user ids differ', () => {
    const game: SeatingGameLike = {
      host: { user_id: 'nope' },
      confirmed_participants: [{ user_id: null, discord_id: '111' }],
    };
    // Caller's user_uuid does not match the row, but its Discord id does.
    expect(resolveMySeating(game, { user_uuid: 'unrelated-uuid', discordId: '111' })).toBe(
      'confirmed'
    );
  });

  it('classifies a waitlisted-only participant as "waitlist"', () => {
    const game: SeatingGameLike = {
      host: { user_id: 'the-host' },
      confirmed_participants: [{ user_id: 'not-me' }],
      waitlist_participants: [{ user_id: 'me-uuid' }],
    };
    expect(resolveMySeating(game, caller)).toBe('waitlist');
  });

  it('returns null when the caller has no relationship to the game', () => {
    const game: SeatingGameLike = {
      host: { user_id: 'a' },
      confirmed_participants: [{ user_id: 'b' }],
      waitlist_participants: [{ user_id: 'c' }],
    };
    expect(resolveMySeating(game, caller)).toBeNull();
  });

  it('treats missing arrays as empty and reports no seating for an anonymous-shaped caller', () => {
    const game: SeatingGameLike = {};
    expect(resolveMySeating(game, { user_uuid: '', discordId: undefined })).toBeNull();
  });
});
