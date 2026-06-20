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

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RecurrenceSelector } from '../RecurrenceSelector';

describe('RecurrenceSelector', () => {
  it('renders no recurrence by default', () => {
    const onChange = vi.fn();

    render(<RecurrenceSelector scheduledAt={null} value={null} onChange={onChange} />);

    expect(screen.getByRole('combobox')).toBeInTheDocument();
    expect(screen.getByRole('combobox')).toHaveTextContent('No recurrence');
  });

  it('shows interval field when weekly selected', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    const scheduledAt = new Date(2026, 0, 3); // Saturday

    render(<RecurrenceSelector scheduledAt={scheduledAt} value={null} onChange={onChange} />);

    const select = screen.getByRole('combobox');
    await user.click(select);
    await user.click(screen.getByText('Every N weeks'));

    expect(screen.getByRole('spinbutton')).toBeInTheDocument();
  });

  it('shows interval field when monthly date selected', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    const scheduledAt = new Date(2026, 0, 15);

    render(<RecurrenceSelector scheduledAt={scheduledAt} value={null} onChange={onChange} />);

    const select = screen.getByRole('combobox');
    await user.click(select);
    await user.click(screen.getByText('Every N months on same date'));

    expect(screen.getByRole('spinbutton')).toBeInTheDocument();
  });

  it('shows interval field when monthly weekday selected', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    const scheduledAt = new Date(2026, 0, 2); // 1st Friday

    render(<RecurrenceSelector scheduledAt={scheduledAt} value={null} onChange={onChange} />);

    const select = screen.getByRole('combobox');
    await user.click(select);
    await user.click(screen.getByText('Every N months on same weekday'));

    expect(screen.getByRole('spinbutton')).toBeInTheDocument();
  });

  it('computes weekly rrule correctly', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    const scheduledAt = new Date(2026, 0, 3); // Saturday

    render(<RecurrenceSelector scheduledAt={scheduledAt} value={null} onChange={onChange} />);

    const select = screen.getByRole('combobox');
    await user.click(select);
    await user.click(screen.getByText('Every N weeks'));

    const intervalInput = screen.getByRole('spinbutton');
    await user.clear(intervalInput);
    await user.type(intervalInput, '2');

    expect(onChange).toHaveBeenLastCalledWith('FREQ=WEEKLY;INTERVAL=2;BYDAY=SA');
  });

  it('computes monthly date rrule correctly', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    const scheduledAt = new Date(2026, 0, 15); // 15th

    render(<RecurrenceSelector scheduledAt={scheduledAt} value={null} onChange={onChange} />);

    const select = screen.getByRole('combobox');
    await user.click(select);
    await user.click(screen.getByText('Every N months on same date'));

    expect(onChange).toHaveBeenLastCalledWith('FREQ=MONTHLY;INTERVAL=1;BYMONTHDAY=15');
  });

  it('computes monthly weekday rrule correctly', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    const scheduledAt = new Date(2026, 0, 2); // 1st Friday (Jan 2, 2026)

    render(<RecurrenceSelector scheduledAt={scheduledAt} value={null} onChange={onChange} />);

    const select = screen.getByRole('combobox');
    await user.click(select);
    await user.click(screen.getByText('Every N months on same weekday'));

    const intervalInput = screen.getByRole('spinbutton');
    await user.clear(intervalInput);
    await user.type(intervalInput, '3');

    expect(onChange).toHaveBeenLastCalledWith('FREQ=MONTHLY;INTERVAL=3;BYDAY=1FR');
  });

  it('calls onChange with null when no recurrence selected', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    const scheduledAt = new Date(2026, 0, 3);

    render(<RecurrenceSelector scheduledAt={scheduledAt} value={null} onChange={onChange} />);

    const select = screen.getByRole('combobox');
    await user.click(select);
    await user.click(screen.getByText('Every N weeks'));

    await user.click(select);
    await user.click(screen.getByText('No recurrence'));

    expect(onChange).toHaveBeenLastCalledWith(null);
  });

  it('initializes with weekly rrule value from prop', () => {
    const onChange = vi.fn();
    const scheduledAt = new Date(2026, 0, 3); // Saturday

    render(
      <RecurrenceSelector
        scheduledAt={scheduledAt}
        value="FREQ=WEEKLY;INTERVAL=2;BYDAY=SA"
        onChange={onChange}
      />
    );

    expect(screen.getByRole('combobox')).toHaveTextContent('Every N weeks');
    expect(screen.getByRole('spinbutton')).toHaveValue(2);
  });

  it('initializes with monthly date rrule value from prop', () => {
    const onChange = vi.fn();
    const scheduledAt = new Date(2026, 0, 15);

    render(
      <RecurrenceSelector
        scheduledAt={scheduledAt}
        value="FREQ=MONTHLY;INTERVAL=3;BYMONTHDAY=15"
        onChange={onChange}
      />
    );

    expect(screen.getByRole('combobox')).toHaveTextContent('Every N months on same date');
    expect(screen.getByRole('spinbutton')).toHaveValue(3);
  });

  it('initializes with monthly weekday rrule value from prop', () => {
    const onChange = vi.fn();
    const scheduledAt = new Date(2026, 0, 2); // 1st Friday

    render(
      <RecurrenceSelector
        scheduledAt={scheduledAt}
        value="FREQ=MONTHLY;INTERVAL=1;BYDAY=1FR"
        onChange={onChange}
      />
    );

    expect(screen.getByRole('combobox')).toHaveTextContent('Every N months on same weekday');
    expect(screen.getByRole('spinbutton')).toHaveValue(1);
  });

  it('falls back to no recurrence for unknown rrule format', () => {
    const onChange = vi.fn();
    const scheduledAt = new Date(2026, 0, 3);

    render(
      <RecurrenceSelector
        scheduledAt={scheduledAt}
        value="FREQ=DAILY;INTERVAL=1"
        onChange={onChange}
      />
    );

    expect(screen.getByRole('combobox')).toHaveTextContent('No recurrence');
  });

  it('syncs to new value when remounted with a new key', () => {
    const onChange = vi.fn();
    const scheduledAt = new Date(2026, 0, 3);

    const { rerender } = render(
      <RecurrenceSelector key="none" scheduledAt={scheduledAt} value={null} onChange={onChange} />
    );

    expect(screen.getByRole('combobox')).toHaveTextContent('No recurrence');

    rerender(
      <RecurrenceSelector
        key="FREQ=WEEKLY;INTERVAL=2;BYDAY=SA"
        scheduledAt={scheduledAt}
        value="FREQ=WEEKLY;INTERVAL=2;BYDAY=SA"
        onChange={onChange}
      />
    );

    expect(screen.getByRole('combobox')).toHaveTextContent('Every N weeks');
    expect(screen.getByRole('spinbutton')).toHaveValue(2);
  });
});
