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
} from '@mui/material';

export interface RecurrenceSelectorProps {
  scheduledAt: Date | null;
  value: string | null;
  onChange: (rule: string | null) => void;
}

const DAY_ABBRS = ['SU', 'MO', 'TU', 'WE', 'TH', 'FR', 'SA'];
const DAYS_PER_WEEK = 7;
const MAX_ORDINAL_BEFORE_LAST = 5;
const MAX_INTERVAL_WEEKLY = 8;
const MAX_INTERVAL_MONTHLY = 12;

const FREQUENCY_OPTIONS = [
  { label: 'No recurrence', value: 'none' },
  { label: 'Every N weeks', value: 'weekly' },
  { label: 'Every N months on same date', value: 'monthly_date' },
  { label: 'Every N months on same weekday', value: 'monthly_weekday' },
];

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

  return (
    <Box>
      <FormControl fullWidth>
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
        <TextField
          label="Interval"
          type="number"
          value={intervalStr}
          onChange={handleIntervalChange}
          inputProps={{ min: 1, max: maxInterval }}
          sx={{ mt: 2 }}
          fullWidth
        />
      )}
    </Box>
  );
}
