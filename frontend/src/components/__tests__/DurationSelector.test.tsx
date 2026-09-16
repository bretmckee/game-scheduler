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

import { describe, it, test, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useEffect, useRef, useState } from 'react';
import { DurationSelector } from '../DurationSelector';

// A genuine infinite render loop never yields control back to the test
// runner, so it would hang the process rather than fail fast. This budget
// converts that hang into a fast, deterministic failure: any render count
// past what a stabilizing component needs (a handful of renders) proves an
// unbounded render/effect/setState cycle is underway.
const RENDER_BUDGET = 50;

/**
 * Reproduces how GameForm actually wires DurationSelector: `onChange` is a
 * plain (non-memoized) function that is recreated on every render, and it
 * updates state via a spread into a *new* object even when the value it
 * receives is unchanged (mirroring GameForm's
 * `setFormData((prev) => ({ ...prev, expectedDurationMinutes: minutes }))`).
 * A parent that behaves this way is a realistic, not contrived, caller.
 */
function NonMemoizedOnChangeHarness({ initial }: { initial: number | null }) {
  const renderCount = useRef(0);

  // Counting/checking happens in an effect (after commit), not during
  // render, since refs may only be read or written outside of render (see
  // the react-hooks/refs lint rule) - reading or mutating one during render
  // is itself an impurity the rule flags.
  useEffect(() => {
    renderCount.current += 1;
    if (renderCount.current > RENDER_BUDGET) {
      throw new Error(
        `NonMemoizedOnChangeHarness exceeded ${RENDER_BUDGET} renders - infinite render loop`
      );
    }
  });

  const [formState, setFormState] = useState<{ expectedDurationMinutes: number | null }>({
    expectedDurationMinutes: initial,
  });

  // Intentionally NOT wrapped in useCallback - this is the real-world shape
  // of GameForm.tsx's handleDurationChange.
  const handleDurationChange = (minutes: number | null) => {
    setFormState((prev) => ({ ...prev, expectedDurationMinutes: minutes }));
  };

  return (
    <DurationSelector value={formState.expectedDurationMinutes} onChange={handleDurationChange} />
  );
}

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

  // Regression test for an infinite render loop: mounting with a non-preset
  // (custom) duration while the parent's onChange is not memoized used to
  // hang the page. See root-cause note in DurationSelector.tsx.
  //
  // Written RED-first against unmodified DurationSelector (vitest 4 removed
  // the .failing() marker, see GameForm.errors-location.test.tsx for the same
  // note), then implemented GREEN without changing any assertion below.
  test('should not enter an infinite render loop when mounted with a non-preset value and a non-memoized onChange', () => {
    expect(() => render(<NonMemoizedOnChangeHarness initial={90} />)).not.toThrow();

    // The custom hours/minutes fields must reflect the initial non-preset
    // value once rendering has stabilized.
    expect(screen.getByLabelText('Hours')).toHaveValue(1);
    expect(screen.getByLabelText('Minutes')).toHaveValue(30);
  });
});
