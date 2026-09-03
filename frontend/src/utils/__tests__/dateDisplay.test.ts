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
import {
  MAX_RELATIVE_FUTURE_DAYS,
  formatScheduleDate,
  relativeScheduleLabel,
} from '../dateDisplay';

const MS_PER_DAY = 86400000;

describe('formatScheduleDate', () => {
  it('renders long weekday + medium date + short time under en-US', () => {
    const out = formatScheduleDate('2026-09-04T11:00:00Z', 'en-US');

    // Full weekday name leads the string (avoids hardcoding which weekday Sep 4 is).
    expect(out).toMatch(/^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s/);
    expect(out).toMatch(/Sep\s+4,\s+2026/);
    expect(out).toMatch(/\d{1,2}:\d{2}\s*[AP]M/);
  });

  it('pads the hour and shows AM for a morning start', () => {
    const out = formatScheduleDate('2026-09-04T07:05:00Z', 'en-US');
    expect(out).toMatch(/[:]?0?7:05\s*AM/);
  });

  it('returns an empty string when the input does not parse as a date', () => {
    expect(formatScheduleDate('not-a-date', 'en-US')).toBe('');
    expect(formatScheduleDate('', 'en-US')).toBe('');
  });
});

describe('relativeScheduleLabel', () => {
  // Reference instant for every case below; deterministic regardless of CI clock.
  const now = new Date('2026-09-02T15:30:00Z');

  it("labels a game starting within the next minute as 'now'", () => {
    expect(relativeScheduleLabel('2026-09-02T15:30:20Z', now)).toBe('now'); // +20s
    expect(relativeScheduleLabel('2026-09-02T15:30:45Z', now)).toBe('now'); // +45s
  });

  it('uses minutes for anything under two hours (floored)', () => {
    expect(relativeScheduleLabel('2026-09-02T15:31:00Z', now)).toBe('in 1 minute'); // +1m singular
    expect(relativeScheduleLabel('2026-09-02T16:15:00Z', now)).toBe('in 45 minutes'); // +45m
    expect(relativeScheduleLabel('2026-09-02T17:05:00Z', now)).toBe('in 95 minutes'); // +95m
    expect(relativeScheduleLabel('2026-09-02T17:29:00Z', now)).toBe('in 119 minutes'); // +119m, top of the <2h band
  });

  it('switches from minutes to hours at exactly two hours', () => {
    expect(relativeScheduleLabel('2026-09-02T17:30:00Z', now)).toBe('in 2 hours'); // +120m boundary
  });

  it('uses hours between two and twenty-four hours (floored, conservative)', () => {
    expect(relativeScheduleLabel('2026-09-02T18:00:00Z', now)).toBe('in 2 hours'); // +2h30m -> floor 2
    expect(relativeScheduleLabel('2026-09-02T19:30:00Z', now)).toBe('in 4 hours'); // +4h
    expect(relativeScheduleLabel('2026-09-03T15:29:00Z', now)).toBe('in 23 hours'); // just under +24h
  });

  it('switches from hours to days at twenty-four hours and labels future days as "in N days"', () => {
    expect(relativeScheduleLabel('2026-09-03T15:30:00Z', now)).toBe('in 1 day'); // exactly +24h
    // Sep 2 -> Oct 2 is exactly 30 calendar days.
    expect(relativeScheduleLabel('2026-10-02T18:00:00Z', now)).toBe('in 30 days');
  });

  it('returns null for distant-future dates beyond the relative window', () => {
    // Boundary derived from the exported cap so this can't drift if the value changes.
    const base = new Date('2026-01-01T12:00:00Z').getTime();
    const atLimit = new Date(base + MAX_RELATIVE_FUTURE_DAYS * MS_PER_DAY).toISOString();
    const overLimit = new Date(base + (MAX_RELATIVE_FUTURE_DAYS + 1) * MS_PER_DAY).toISOString();

    expect(relativeScheduleLabel(atLimit, base)).toBe(`in ${MAX_RELATIVE_FUTURE_DAYS} days`);
    expect(relativeScheduleLabel(overLimit, base)).toBeNull();
  });

  it('returns null once a game has already started (past or exactly now)', () => {
    expect(relativeScheduleLabel(now.toISOString(), now)).toBeNull(); // delta 0
    expect(relativeScheduleLabel('2026-09-02T15:29:59Z', now)).toBeNull(); // -1s
    expect(relativeScheduleLabel('2026-09-01T12:00:00Z', now)).toBeNull(); // yesterday
    expect(relativeScheduleLabel('2026-08-26T12:00:00Z', now)).toBeNull(); // a week ago
  });

  it('accepts an epoch-ms reference and returns null for unparseable input', () => {
    const ref = now.getTime();
    // +4h from the epoch-ms reference.
    expect(relativeScheduleLabel('2026-09-02T19:30:00Z', ref)).toBe('in 4 hours');
    expect(relativeScheduleLabel('garbage', now)).toBeNull();
  });
});
