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

import { useState, useEffect, useCallback } from 'react';
import {
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormHelperText,
  TextField,
  Box,
} from '@mui/material';

export interface DurationSelectorProps {
  value: number | null;
  onChange: (minutes: number | null) => void;
  error?: boolean;
  helperText?: string;
}

const MINUTES_PER_HOUR = 60;
const PRESET_TWO_HOURS = 120;
const PRESET_FOUR_HOURS = 240;

const PRESET_OPTIONS = [
  { label: '2 hours', value: PRESET_TWO_HOURS },
  { label: '4 hours', value: PRESET_FOUR_HOURS },
  { label: 'Custom...', value: 'custom' },
];

export function DurationSelector({ value, onChange, error, helperText }: DurationSelectorProps) {
  const isPresetValue = value === PRESET_TWO_HOURS || value === PRESET_FOUR_HOURS;
  const initialCustomMode = value !== null && !isPresetValue;

  const [isCustomMode, setIsCustomMode] = useState(initialCustomMode);
  const [customHours, setCustomHours] = useState<string>(() => {
    if (initialCustomMode && value !== null) {
      const hours = Math.floor(value / MINUTES_PER_HOUR);
      return hours > 0 ? hours.toString() : '';
    }
    return '';
  });
  const [customMinutes, setCustomMinutes] = useState<string>(() => {
    if (initialCustomMode && value !== null) {
      const minutes = value % MINUTES_PER_HOUR;
      return minutes > 0 ? minutes.toString() : '';
    }
    return '';
  });

  const getSelectedValue = () => {
    if (value === null) return '';
    if (value === PRESET_TWO_HOURS || value === PRESET_FOUR_HOURS) return value;
    return 'custom';
  };

  const handleChange = (event: { target: { value: string | number } }) => {
    const selectedValue = event.target.value;
    if (selectedValue === 'custom') {
      setIsCustomMode(true);
      setCustomHours('');
      setCustomMinutes('');
      onChange(null);
    } else {
      setIsCustomMode(false);
      if (typeof selectedValue === 'number') {
        onChange(selectedValue);
      } else {
        onChange(Number(selectedValue));
      }
    }
  };

  const handleCustomChange = useCallback(() => {
    const hours = customHours ? parseInt(customHours, 10) : 0;
    const minutes = customMinutes ? parseInt(customMinutes, 10) : 0;
    const totalMinutes = hours * MINUTES_PER_HOUR + minutes;
    onChange(totalMinutes > 0 ? totalMinutes : null);
  }, [customHours, customMinutes, onChange]);

  useEffect(() => {
    if (isCustomMode) {
      handleCustomChange();
    }
  }, [customHours, customMinutes, isCustomMode, handleCustomChange]);

  const handleHoursChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setCustomHours(event.target.value);
  };

  const handleMinutesChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setCustomMinutes(event.target.value);
  };

  return (
    <Box>
      <FormControl fullWidth error={error}>
        <InputLabel>Expected Duration</InputLabel>
        <Select value={getSelectedValue()} onChange={handleChange} label="Expected Duration">
          {PRESET_OPTIONS.map((option) => (
            <MenuItem key={option.value} value={option.value}>
              {option.label}
            </MenuItem>
          ))}
        </Select>
        {!isCustomMode && helperText && <FormHelperText>{helperText}</FormHelperText>}
      </FormControl>

      {isCustomMode && (
        <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
          <TextField
            label="Hours"
            type="number"
            value={customHours}
            onChange={handleHoursChange}
            inputProps={{ min: 0, max: 24 }}
            error={error}
            sx={{ flex: 1 }}
          />
          <TextField
            label="Minutes"
            type="number"
            value={customMinutes}
            onChange={handleMinutesChange}
            inputProps={{ min: 0, max: 59 }}
            error={error}
            sx={{ flex: 1 }}
          />
        </Box>
      )}

      {isCustomMode && helperText && <FormHelperText error={error}>{helperText}</FormHelperText>}
    </Box>
  );
}
