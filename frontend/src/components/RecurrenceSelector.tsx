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

import { useState } from 'react';
import {
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
  TextField,
  Box,
  Typography,
} from '@mui/material';

export interface RecurrenceSelectorProps {
  scheduledAt: Date | null;
  value: string | null;
  onChange: (rule: string | null) => void;
}

const DAY_ABBRS = ['SU', 'MO', 'TU', 'WE', 'TH', 'FR', 'SA'];
const FULL_DAY_NAMES = [
  'Sunday',
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
];
const DAYS_PER_WEEK = 7;
const MAX_ORDINAL_BEFORE_LAST = 5;
const MAX_INTERVAL_WEEKLY = 8;
const MAX_INTERVAL_MONTHLY = 12;
const ORDINAL_MOD_100 = 100;
const ORDINAL_MOD_10 = 10;
const ORDINAL_TEEN_LOW = 11;
const ORDINAL_TEEN_HIGH = 13;
const ORDINAL_RD = 3;

function ordinalLabel(n: number): string {
  if (n === -1) return 'last';
  const mod100 = n % ORDINAL_MOD_100;
  const mod10 = n % ORDINAL_MOD_10;
  if (mod100 >= ORDINAL_TEEN_LOW && mod100 <= ORDINAL_TEEN_HIGH) return `${n}th`;
  if (mod10 === 1) return `${n}st`;
  if (mod10 === 2) return `${n}nd`;
  if (mod10 === ORDINAL_RD) return `${n}rd`;
  return `${n}th`;
}

function weekdayOccurrence(date: Date): string {
  const rawOrd = Math.ceil(date.getDate() / DAYS_PER_WEEK);
  const ord = rawOrd >= MAX_ORDINAL_BEFORE_LAST ? -1 : rawOrd;
  return `${ordinalLabel(ord)} ${FULL_DAY_NAMES[date.getDay()]}`;
}

function frequencyDescription(frequency: string, date: Date): string {
  if (frequency === 'weekly') return `on ${FULL_DAY_NAMES[date.getDay()]}`;
  if (frequency === 'monthly_weekday') return `on the ${weekdayOccurrence(date)}`;
  if (frequency === 'monthly_date') return `on the ${ordinalLabel(date.getDate())}`;
  return '';
}

const FREQUENCY_OPTIONS = [
  { label: 'No recurrence', value: 'none' },
  { label: 'Weekly', value: 'weekly' },
  { label: 'Monthly (date)', value: 'monthly_date' },
  { label: 'Monthly (weekday)', value: 'monthly_weekday' },
];

const FREQUENCY_UNIT: Record<string, [string, string]> = {
  weekly: ['week', 'weeks'],
  monthly_date: ['month', 'months'],
  monthly_weekday: ['month', 'months'],
};

function computeRrule(
  frequency: string,
  interval: number,
  scheduledAt: Date | null
): string | null {
  if (frequency === 'none' || !scheduledAt) return null;

  const dow = DAY_ABBRS[scheduledAt.getDay()];

  if (frequency === 'weekly') {
    return `FREQ=WEEKLY;INTERVAL=${interval};BYDAY=${dow}`;
  }
  if (frequency === 'monthly_date') {
    return `FREQ=MONTHLY;INTERVAL=${interval};BYMONTHDAY=${scheduledAt.getDate()}`;
  }
  // monthly_weekday
  const rawOrd = Math.ceil(scheduledAt.getDate() / DAYS_PER_WEEK);
  const ord = rawOrd >= MAX_ORDINAL_BEFORE_LAST ? -1 : rawOrd;
  return `FREQ=MONTHLY;INTERVAL=${interval};BYDAY=${ord}${dow}`;
}

function parseRrule(rule: string): { frequency: string; interval: number } | null {
  const parts = Object.fromEntries(rule.split(';').map((p) => p.split('=')));
  const freq = parts['FREQ'];
  const interval = parseInt(parts['INTERVAL'] ?? '1', 10);
  if (freq === 'WEEKLY') return { frequency: 'weekly', interval };
  if (freq === 'MONTHLY') {
    if (parts['BYMONTHDAY']) return { frequency: 'monthly_date', interval };
    if (parts['BYDAY']) return { frequency: 'monthly_weekday', interval };
  }
  return null;
}

export function RecurrenceSelector({ scheduledAt, value, onChange }: RecurrenceSelectorProps) {
  const [frequency, setFrequency] = useState<string>(() => {
    if (!value) return 'none';
    return parseRrule(value)?.frequency ?? 'none';
  });
  const [intervalStr, setIntervalStr] = useState<string>(() => {
    if (!value) return '1';
    return (parseRrule(value)?.interval ?? 1).toString();
  });

  const handleFrequencyChange = (event: SelectChangeEvent) => {
    const freq = event.target.value;
    setFrequency(freq);
    if (freq === 'none') {
      onChange(null);
    } else {
      const val = parseInt(intervalStr, 10);
      if (!isNaN(val) && val >= 1) {
        onChange(computeRrule(freq, val, scheduledAt));
      }
    }
  };

  const handleIntervalChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const str = event.target.value;
    setIntervalStr(str);
    const val = parseInt(str, 10);
    if (isNaN(val) || val < 1) return;
    onChange(computeRrule(frequency, val, scheduledAt));
  };

  const maxInterval = frequency === 'weekly' ? MAX_INTERVAL_WEEKLY : MAX_INTERVAL_MONTHLY;
  const unitWord = FREQUENCY_UNIT[frequency]?.[parseInt(intervalStr, 10) === 1 ? 0 : 1] ?? '';

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      <FormControl sx={{ minWidth: 160 }}>
        <InputLabel>Recurrence</InputLabel>
        <Select value={frequency} onChange={handleFrequencyChange} label="Recurrence">
          {FREQUENCY_OPTIONS.map((option) => (
            <MenuItem key={option.value} value={option.value}>
              {option.label}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {frequency !== 'none' && (
        <>
          <Typography variant="body1">every</Typography>
          <TextField
            type="number"
            value={intervalStr}
            onChange={handleIntervalChange}
            inputProps={{ min: 1, max: maxInterval, 'aria-label': 'Interval' }}
            sx={{ width: 80 }}
          />
          <Typography variant="body1">{unitWord}</Typography>
          {scheduledAt && (
            <Typography variant="body1" sx={{ whiteSpace: 'nowrap' }}>
              {frequencyDescription(frequency, scheduledAt)}
            </Typography>
          )}
        </>
      )}
    </Box>
  );
}
