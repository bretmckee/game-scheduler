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

/**
 * Resolve how the current caller is seated in a game from list/detail data.
 *
 * The API already partitions participants into `confirmed_participants` and
 * `waitlist_participants`, and exposes the host as `host`. This helper maps that
 * data onto a single seating state used for visual cues (e.g. the status border).
 */

/** Structural subset of any participant-like record we can match by identity. */
export interface IdentifiableParticipant {
  user_id?: string | null;
  discord_id?: string | null;
}

/** Structural subset of the authenticated caller's identity. */
export interface CallerIdentity {
  user_uuid?: string | null;
  discordId?: string | null;
}

/** Minimal shape needed to determine seating without importing the full GameSession. */
export interface SeatingGameLike {
  host?: IdentifiableParticipant | null;
  confirmed_participants?: IdentifiableParticipant[] | null;
  waitlist_participants?: IdentifiableParticipant[] | null;
}

export type MySeating = 'host' | 'confirmed' | 'waitlist' | null;

function sameIdentity(participant: IdentifiableParticipant, caller: CallerIdentity): boolean {
  const { user_id, discord_id } = participant;
  if (typeof user_id === 'string' && user_id.length > 0 && user_id === caller.user_uuid) {
    return true;
  }
  // Fall back to Discord id when a linked account is present on both sides.
  if (
    typeof discord_id === 'string' &&
    discord_id.length > 0 &&
    typeof caller.discordId === 'string' &&
    discord_id === caller.discordId
  ) {
    return true;
  }
  return false;
}

/**
 * Determine the caller's seating in a game.
 *
 * Priority: host beats confirmed beats waitlist. Returns `null` when the caller
 * has no known relationship to the game (e.g. anonymous or browsing someone else's game).
 */
export function resolveMySeating(game: SeatingGameLike, caller?: CallerIdentity | null): MySeating {
  if (!caller) {
    return null;
  }

  if (game.host && sameIdentity(game.host, caller)) {
    return 'host';
  }

  if ((game.confirmed_participants ?? []).some((p) => sameIdentity(p, caller))) {
    return 'confirmed';
  }

  if ((game.waitlist_participants ?? []).some((p) => sameIdentity(p, caller))) {
    return 'waitlist';
  }

  return null;
}
