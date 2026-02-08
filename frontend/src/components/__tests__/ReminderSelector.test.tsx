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
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ReminderSelector } from '../ReminderSelector';

describe('ReminderSelector', () => {
  it('should render with empty array', () => {
    const onChange = vi.fn();

    render(<ReminderSelector value={[]} onChange={onChange} />);
    expect(screen.getByRole('combobox')).toBeInTheDocument();
    expect(screen.getByLabelText('Add Reminder Time')).toBeInTheDocument();
  });

  it('should display preset options in dropdown', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    render(<ReminderSelector value={[]} onChange={onChange} />);

    const select = screen.getByRole('combobox');
    await user.click(select);

    expect(screen.getByText('5 minutes')).toBeInTheDocument();
    expect(screen.getByText('30 minutes')).toBeInTheDocument();
    expect(screen.getByText('1 hour')).toBeInTheDocument();
    expect(screen.getByText('2 hours')).toBeInTheDocument();
    expect(screen.getByText('1 day')).toBeInTheDocument();
    expect(screen.getByText('Custom...')).toBeInTheDocument();
  });

  it('should add preset value when selected', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    render(<ReminderSelector value={[]} onChange={onChange} />);

    const select = screen.getByRole('combobox');
    await user.click(select);

    const option = screen.getByText('5 minutes');
    await user.click(option);

    expect(onChange).toHaveBeenCalledWith([5]);
  });

  it('should display selected values as chips', () => {
    const onChange = vi.fn();

    render(<ReminderSelector value={[5, 60, 1440]} onChange={onChange} />);

    expect(screen.getByText('5 minutes')).toBeInTheDocument();
    expect(screen.getByText('1 hour')).toBeInTheDocument();
    expect(screen.getByText('1 day')).toBeInTheDocument();
  });

  it('should display custom values with minutes label', () => {
    const onChange = vi.fn();

    render(<ReminderSelector value={[15, 45]} onChange={onChange} />);

    expect(screen.getByText('15 minutes')).toBeInTheDocument();
    expect(screen.getByText('45 minutes')).toBeInTheDocument();
  });

  it('should remove value when chip delete clicked', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    render(<ReminderSelector value={[5, 60]} onChange={onChange} />);

    const deleteButtons = screen.getAllByTestId('CancelIcon');
    expect(deleteButtons[0]).toBeDefined();
    await user.click(deleteButtons[0]!);

    expect(onChange).toHaveBeenCalledWith([60]);
  });

  it('should sort values in ascending order after adding', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    render(<ReminderSelector value={[60, 1440]} onChange={onChange} />);

    const select = screen.getByRole('combobox');
    await user.click(select);
    await user.click(screen.getByText('5 minutes'));

    expect(onChange).toHaveBeenCalledWith([5, 60, 1440]);
  });

  it('should disable already selected presets in dropdown', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    render(<ReminderSelector value={[5, 60]} onChange={onChange} />);

    const select = screen.getByRole('combobox');
    await user.click(select);

    const listbox = screen.getByRole('listbox');
    const options = within(listbox).getAllByRole('option');
    const option5min = options.find((opt) => opt.textContent === '5 minutes');
    const option60min = options.find((opt) => opt.textContent === '1 hour');

    expect(option5min).toHaveAttribute('aria-disabled', 'true');
    expect(option60min).toHaveAttribute('aria-disabled', 'true');
  });

  it('should show custom input when Custom selected', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    render(<ReminderSelector value={[]} onChange={onChange} />);

    const select = screen.getByRole('combobox');
    await user.click(select);
    await user.click(screen.getByText('Custom...'));

    expect(screen.getByLabelText('Custom Minutes')).toBeInTheDocument();
    expect(screen.getByText('Add')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });

  it('should add custom value when Add clicked', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    render(<ReminderSelector value={[]} onChange={onChange} />);

    const select = screen.getByRole('combobox');
    await user.click(select);
    await user.click(screen.getByText('Custom...'));

    const customInput = screen.getByLabelText('Custom Minutes');
    await user.type(customInput, '45');
    await user.click(screen.getByText('Add'));

    expect(onChange).toHaveBeenCalledWith([45]);
  });

  it('should cancel custom mode when Cancel clicked', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    render(<ReminderSelector value={[]} onChange={onChange} />);

    const select = screen.getByRole('combobox');
    await user.click(select);
    await user.click(screen.getByText('Custom...'));

    await user.click(screen.getByText('Cancel'));

    expect(screen.queryByLabelText('Custom Minutes')).not.toBeInTheDocument();
  });

  it('should clear custom input after adding value', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    render(<ReminderSelector value={[]} onChange={onChange} />);

    const select = screen.getByRole('combobox');
    await user.click(select);
    await user.click(screen.getByText('Custom...'));

    const customInput = screen.getByLabelText('Custom Minutes');
    await user.type(customInput, '45');
    await user.click(screen.getByText('Add'));

    expect(screen.queryByLabelText('Custom Minutes')).not.toBeInTheDocument();
  });

  it('should reject custom value below minimum (1)', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    render(<ReminderSelector value={[]} onChange={onChange} />);

    const select = screen.getByRole('combobox');
    await user.click(select);
    await user.click(screen.getByText('Custom...'));

    const customInput = screen.getByLabelText('Custom Minutes');
    await user.type(customInput, '0');
    await user.click(screen.getByText('Add'));

    expect(onChange).not.toHaveBeenCalled();
  });

  it('should reject custom value above maximum (10080)', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    render(<ReminderSelector value={[]} onChange={onChange} />);

    const select = screen.getByRole('combobox');
    await user.click(select);
    await user.click(screen.getByText('Custom...'));

    const customInput = screen.getByLabelText('Custom Minutes');
    await user.type(customInput, '10081');
    await user.click(screen.getByText('Add'));

    expect(onChange).not.toHaveBeenCalled();
  });

  it('should reject duplicate custom values', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    render(<ReminderSelector value={[45]} onChange={onChange} />);

    const select = screen.getByRole('combobox');
    await user.click(select);
    await user.click(screen.getByText('Custom...'));

    const customInput = screen.getByLabelText('Custom Minutes');
    await user.type(customInput, '45');
    await user.click(screen.getByText('Add'));

    expect(onChange).not.toHaveBeenCalled();
  });

  it('should reject non-integer custom values', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    render(<ReminderSelector value={[]} onChange={onChange} />);

    const select = screen.getByRole('combobox');
    await user.click(select);
    await user.click(screen.getByText('Custom...'));

    const customInput = screen.getByLabelText('Custom Minutes');
    await user.type(customInput, '45.5');
    await user.click(screen.getByText('Add'));

    expect(onChange).not.toHaveBeenCalled();
  });

  it('should display error state', () => {
    const onChange = vi.fn();

    render(
      <ReminderSelector value={[]} onChange={onChange} error={true} helperText="Test error" />
    );

    expect(screen.getByText('Test error')).toBeInTheDocument();
  });

  it('should display helper text when provided', () => {
    const onChange = vi.fn();

    render(<ReminderSelector value={[]} onChange={onChange} helperText="Select reminder times" />);

    expect(screen.getByText('Select reminder times')).toBeInTheDocument();
  });

  it('should handle multiple preset selections', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    render(<ReminderSelector value={[5]} onChange={onChange} />);

    const select = screen.getByRole('combobox');
    await user.click(select);
    await user.click(screen.getByText('30 minutes'));

    expect(onChange).toHaveBeenCalledWith([5, 30]);
  });

  it('should keep dropdown value empty after selection', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    render(<ReminderSelector value={[]} onChange={onChange} />);

    const select = screen.getByRole('combobox');
    await user.click(select);
    await user.click(screen.getByText('5 minutes'));

    const selectAfter = screen.getByRole('combobox');
    expect(selectAfter.textContent).toBe('​');
  });
});
