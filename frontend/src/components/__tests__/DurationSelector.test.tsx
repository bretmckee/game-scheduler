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
import { DurationSelector } from '../DurationSelector';

describe('DurationSelector', () => {
  it('should render with null value', () => {
    const onChange = vi.fn();

    render(<DurationSelector value={null} onChange={onChange} />);
    expect(screen.getByRole('combobox')).toBeInTheDocument();
  });

  it('should display 2 hours preset when value is 120', () => {
    const onChange = vi.fn();

    render(<DurationSelector value={120} onChange={onChange} />);
    expect(screen.getByRole('combobox')).toHaveTextContent('2 hours');
  });

  it('should display 4 hours preset when value is 240', () => {
    const onChange = vi.fn();

    render(<DurationSelector value={240} onChange={onChange} />);
    expect(screen.getByRole('combobox')).toHaveTextContent('4 hours');
  });

  it('should display Custom when value is not a preset', () => {
    const onChange = vi.fn();

    render(<DurationSelector value={150} onChange={onChange} />);
    expect(screen.getByRole('combobox')).toHaveTextContent('Custom...');
  });

  it('should call onChange when preset selected', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    render(<DurationSelector value={null} onChange={onChange} />);

    const select = screen.getByRole('combobox');
    await user.click(select);

    const option = screen.getByText('2 hours');
    await user.click(option);

    expect(onChange).toHaveBeenCalledWith(120);
  });

  it('should display error state', () => {
    const onChange = vi.fn();

    render(
      <DurationSelector value={120} onChange={onChange} error={true} helperText="Test error" />
    );

    expect(screen.getByText('Test error')).toBeInTheDocument();
  });

  it('should show custom input fields when Custom selected', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    render(<DurationSelector value={120} onChange={onChange} />);

    const select = screen.getByRole('combobox');
    await user.click(select);

    const customOption = screen.getByText('Custom...');
    await user.click(customOption);

    expect(onChange).toHaveBeenCalledWith(null);
    expect(screen.getByLabelText('Hours')).toBeInTheDocument();
    expect(screen.getByLabelText('Minutes')).toBeInTheDocument();
  });

  it('should calculate total minutes from hours and minutes input', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    render(<DurationSelector value={null} onChange={onChange} />);

    const select = screen.getByRole('combobox');
    await user.click(select);
    await user.click(screen.getByText('Custom...'));

    onChange.mockClear();

    const hoursInput = screen.getByLabelText('Hours');
    await user.type(hoursInput, '2');

    await new Promise((resolve) => setTimeout(resolve, 10));
    expect(onChange).toHaveBeenCalledWith(120);
  });

  it('should add hours and minutes together', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    render(<DurationSelector value={null} onChange={onChange} />);

    const select = screen.getByRole('combobox');
    await user.click(select);
    await user.click(screen.getByText('Custom...'));

    onChange.mockClear();

    await user.type(screen.getByLabelText('Hours'), '1');
    await user.type(screen.getByLabelText('Minutes'), '30');

    await new Promise((resolve) => setTimeout(resolve, 10));
    const calls = onChange.mock.calls;
    expect(calls.length).toBeGreaterThan(0);
    const lastCall = calls[calls.length - 1];
    expect(lastCall?.[0]).toBe(90);
  });

  it('should initialize custom mode with existing non-preset value', () => {
    const onChange = vi.fn();

    render(<DurationSelector value={150} onChange={onChange} />);

    expect(screen.getByLabelText('Hours')).toHaveValue(2);
    expect(screen.getByLabelText('Minutes')).toHaveValue(30);
  });

  it('should handle hours validation range (0-24)', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    render(<DurationSelector value={null} onChange={onChange} />);

    await user.click(screen.getByRole('combobox'));
    await user.click(screen.getByText('Custom...'));

    const hoursInput = screen.getByLabelText('Hours');
    expect(hoursInput).toHaveAttribute('min', '0');
    expect(hoursInput).toHaveAttribute('max', '24');
  });

  it('should handle minutes validation range (0-59)', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    render(<DurationSelector value={null} onChange={onChange} />);

    await user.click(screen.getByRole('combobox'));
    await user.click(screen.getByText('Custom...'));

    const minutesInput = screen.getByLabelText('Minutes');
    expect(minutesInput).toHaveAttribute('min', '0');
    expect(minutesInput).toHaveAttribute('max', '59');
  });

  it('should handle empty custom inputs as zero', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    render(<DurationSelector value={null} onChange={onChange} />);

    await user.click(screen.getByRole('combobox'));
    await user.click(screen.getByText('Custom...'));

    onChange.mockClear();

    await user.type(screen.getByLabelText('Hours'), '2');
    await user.clear(screen.getByLabelText('Hours'));

    await new Promise((resolve) => setTimeout(resolve, 10));
    expect(onChange).toHaveBeenCalledWith(null);
  });

  it('should propagate error prop to custom inputs', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    render(
      <DurationSelector value={null} onChange={onChange} error={true} helperText="Error message" />
    );

    await user.click(screen.getByRole('combobox'));
    await user.click(screen.getByText('Custom...'));

    expect(screen.getByText('Error message')).toBeInTheDocument();
  });

  it('should switch from custom back to preset', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    render(<DurationSelector value={150} onChange={onChange} />);

    expect(screen.getByLabelText('Hours')).toBeInTheDocument();

    await user.click(screen.getByRole('combobox'));
    await user.click(screen.getByText('2 hours'));

    expect(onChange).toHaveBeenCalledWith(120);
    expect(screen.queryByLabelText('Hours')).not.toBeInTheDocument();
  });
});
