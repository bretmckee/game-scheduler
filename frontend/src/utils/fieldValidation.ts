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

import { Time } from '../constants/time';

export interface ValidationResult {
  isValid: boolean;
  error?: string;
  warning?: string;
  value?: unknown;
}

const MILLISECONDS_PER_HOUR = 3600000;

export function validateDuration(minutes: number | null | undefined): ValidationResult {
  if (minutes === null || minutes === undefined || minutes === 0) {
    return { isValid: true };
  }

  if (minutes < 1) {
    return { isValid: false, error: 'Duration must be at least 1 minute' };
  }

  const MAX_DURATION_MINUTES = 1440;
  if (minutes > MAX_DURATION_MINUTES) {
    return {
      isValid: false,
      error: `Duration cannot exceed ${MAX_DURATION_MINUTES} minutes (1 day)`,
    };
  }

  return { isValid: true };
}

export function validateMaxPlayers(value: string): ValidationResult {
  if (!value || value.trim() === '') {
    return { isValid: false, error: 'Max players is required' };
  }

  const num = Number(value);
  if (isNaN(num) || !Number.isInteger(num)) {
    return { isValid: false, error: 'Max players must be a valid number' };
  }

  if (num < 1) {
    return { isValid: false, error: 'Max players must be at least 1' };
  }

  const MAX_PLAYERS = 100;
  if (num > MAX_PLAYERS) {
    return { isValid: false, error: `Max players cannot exceed ${MAX_PLAYERS}` };
  }

  return { isValid: true, value: num };
}

export function validateCharacterLimit(
  value: string,
  maxLength: number,
  fieldName: string
): ValidationResult {
  const length = value.length;

  if (length > maxLength) {
    return {
      isValid: false,
      error: `${fieldName} exceeds maximum length of ${maxLength} characters (current: ${length})`,
    };
  }

  const WARNING_THRESHOLD = 0.95;
  if (length >= maxLength * WARNING_THRESHOLD) {
    return {
      isValid: true,
      warning: `${fieldName} is at ${length}/${maxLength} characters (95% of limit)`,
    };
  }

  return { isValid: true };
}

export function validateFutureDate(
  date: Date | null | undefined,
  minHoursInFuture: number = 0
): ValidationResult {
  if (!date) {
    return { isValid: false, error: 'A valid date is required' };
  }

  const now = new Date();
  const minFutureTime = new Date(now.getTime() + minHoursInFuture * MILLISECONDS_PER_HOUR);

  if (date < minFutureTime) {
    if (minHoursInFuture === 0) {
      return { isValid: false, error: 'Date must be in the future' };
    }
    return {
      isValid: false,
      error: `Date must be at least ${minHoursInFuture} hours in the future`,
    };
  }

  return { isValid: true };
}

export const MAX_REMINDER_MINUTES = 10080;

const MIN_REMINDER_MINUTES = 1;

export function computeMaxReminderMinutes(scheduledAt: Date | null | undefined): number {
  if (!scheduledAt) return MAX_REMINDER_MINUTES;
  return Math.max(
    MIN_REMINDER_MINUTES,
    Math.floor((scheduledAt.getTime() - new Date().getTime()) / Time.MILLISECONDS_PER_MINUTE) - 1
  );
}

export function validateReminderMinutes(
  minutes: number[],
  scheduledAt: Date | null | undefined
): ValidationResult {
  const maxMinutes = computeMaxReminderMinutes(scheduledAt);
  const invalidValues = minutes.filter(
    (val) => val < MIN_REMINDER_MINUTES || val > maxMinutes || !Number.isInteger(val)
  );
  if (invalidValues.length > 0) {
    return {
      isValid: false,
      error: `All reminder values must be integers between 1 and ${maxMinutes} minutes`,
    };
  }
  return { isValid: true };
}

export function validateCustomReminderInput(
  input: string,
  maxMinutes: number,
  existingValues: number[]
): string | null {
  if (!input.trim() || isNaN(parseInt(input, 10))) {
    return 'Please enter a valid number';
  }
  if (!Number.isInteger(parseFloat(input))) {
    return 'Please enter a whole number';
  }
  const num = parseInt(input, 10);
  if (num < MIN_REMINDER_MINUTES) {
    return `Reminder must be at least ${MIN_REMINDER_MINUTES} minute`;
  }
  if (num > maxMinutes) {
    return `That time is in the past. Max value is currently ${maxMinutes}`;
  }
  if (existingValues.includes(num)) {
    return 'This reminder time is already added';
  }
  return null;
}
