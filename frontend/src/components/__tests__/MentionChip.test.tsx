// Copyright 2025-2026 Bret McKee
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
import { MentionChip } from '../MentionChip';

describe('MentionChip', () => {
  it('renders username and display name correctly', () => {
    const onClick = vi.fn();
    render(<MentionChip username="johndoe" displayName="John Doe" onClick={onClick} />);

    expect(screen.getByText(/@johndoe \(John Doe\)/)).toBeInTheDocument();
  });

  it('calls onClick when clicked', async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();

    render(<MentionChip username="johndoe" displayName="John Doe" onClick={onClick} />);

    const chip = screen.getByText(/@johndoe \(John Doe\)/);
    await user.click(chip);

    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('renders as a clickable chip', () => {
    const onClick = vi.fn();
    render(<MentionChip username="johndoe" displayName="John Doe" onClick={onClick} />);

    const chip = screen.getByText(/@johndoe \(John Doe\)/);
    expect(chip).toBeVisible();
  });
});
