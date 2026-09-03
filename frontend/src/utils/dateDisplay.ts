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
 * Date display helpers for game schedule fields ("When:").
 *
 * These are pure functions so they can be unit-tested deterministically with an
 * injected reference time (`now`) and locale, independent of the host environment.
 */

// Millisecond units built from named factors (not raw literals at use sites) so the
// relative-label thresholds below stay readable and lint-clean.
const MINUTES_PER_HOUR = 60;
// A full day's worth of hours — also used directly below to mean "less than a day".
const HOURS_PER_DAY = 24;
const MS_PER_MINUTE = 60_000;
const MS_PER_HOUR = MINUTES_PER_HOUR * MS_PER_MINUTE;
const MS_PER_DAY = HOURS_PER_DAY * MS_PER_HOUR;

/** Whole-minute distance out before schedule hints stop using minutes and use hours/days instead. */
const SWITCH_TO_MINUTES_BELOW = 120;

/** Upper bound (days ahead) for showing a future relative label such as "in N days". */
export const MAX_RELATIVE_FUTURE_DAYS = 3650;

/** Whole-UTC-midnight timestamp for the date containing `ms` (calendar-day bucket in UTC). */
function utcStartOfDayMs(ms: number): number {
  const d = new Date(ms);
  return Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
}

/**
 * Format an ISO datetime into the "When:" field value: long weekday + medium date
 * + short time (e.g. "Friday, Sep 4, 2026, 11:00 AM" under the en-US locale).
 *
 * @param isoString ISO-8601 date string from the API.
 * @param locale Optional BCP-47 tag; defaults to the runtime/user locale.
 * @returns Localized string, or '' when the input does not parse as a valid date.
 */
export function formatScheduleDate(isoString: string, locale?: string): string {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) {
    return '';
  }
  return date.toLocaleString(locale ?? undefined, {
    weekday: 'long',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  });
}

/**
 * Relative-time label for a scheduled game ("in 95 minutes", "in 4 hours", ...).
 *
 * The difference is measured over absolute elapsed time from `now`. Labels are only
 * produced while a game is still upcoming (`delta > 0`); once it has started we return
 * `null` so the list stays focused on helping players be ready for their NEXT game.
 *   - starting within the next minute   -> 'now'
 *   - [1 minute, 2 hours)               -> 'in N minutes' (floored)
 *   - [2 hours, 24 hours)               -> 'in N hours'   (floored, conservative)
 *   - >= 24 hours                        -> 'in N days', as whole-UTC calendar days up to
 *                                           {@link MAX_RELATIVE_FUTURE_DAYS}.
 *
 * @param isoString ISO-8601 date string from the API.
 * @param now Reference instant (defaults to the current wall clock). Injectable for tests.
 * @returns A short human label, or `null` when no relative context should be shown.
 */
export function relativeScheduleLabel(isoString: string, now?: Date | number): string | null {
  const target = new Date(isoString);
  if (Number.isNaN(target.getTime())) {
    return null;
  }

  const referenceMs = typeof now === 'number' ? now : now ? now.getTime() : Date.now();
  if (!Number.isFinite(referenceMs)) {
    return null;
  }

  // No label once the game has started — this only helps players prepare ahead of time.
  const deltaMs = target.getTime() - referenceMs;
  if (deltaMs <= 0) {
    return null;
  }
  if (deltaMs < MS_PER_MINUTE) {
    return 'now'; // starting within the next minute
  }

  const totalMinutes = Math.floor(deltaMs / MS_PER_MINUTE);
  if (totalMinutes < SWITCH_TO_MINUTES_BELOW) {
    return `in ${totalMinutes} minute${totalMinutes === 1 ? '' : 's'}`;
  }

  const totalHours = Math.floor(totalMinutes / MINUTES_PER_HOUR);
  if (totalHours < HOURS_PER_DAY) {
    return `in ${totalHours} hour${totalHours === 1 ? '' : 's'}`;
  }

  // A day or more out: a stable whole-UTC calendar-day difference, capped for very far games.
  const diffDays = Math.round(
    (utcStartOfDayMs(target.getTime()) - utcStartOfDayMs(referenceMs)) / MS_PER_DAY
  );
  if (diffDays > MAX_RELATIVE_FUTURE_DAYS) {
    return null;
  }
  return `in ${diffDays} day${diffDays === 1 ? '' : 's'}`;
}
