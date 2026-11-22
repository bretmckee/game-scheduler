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
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemberChip } from '../MemberChip';

describe('MemberChip', () => {
  it('renders a present member as @label', () => {
    render(<MemberChip member={{ id: '111', label: 'Kallisti' }} />);

    expect(screen.getByTestId('member-chip')).toHaveTextContent('@Kallisti');
    expect(screen.queryByTestId('unknown-member-chip')).not.toBeInTheDocument();
  });

  it('renders labels with spaces and punctuation unmodified', () => {
    render(<MemberChip member={{ id: '111', label: 'Sir Xanthias (GM) | <3' }} />);

    expect(screen.getByTestId('member-chip')).toHaveTextContent('@Sir Xanthias (GM) | <3');
  });

  it('renders a departed member as the distinct unknown-member chip', () => {
    render(<MemberChip member={{ id: '222', label: null }} />);

    const chip = screen.getByTestId('unknown-member-chip');
    expect(chip).toHaveAccessibleName(/no longer in this server/i);
    expect(screen.queryByTestId('member-chip')).not.toBeInTheDocument();
    expect(screen.queryByText(/Unknown User/)).not.toBeInTheDocument();
    expect(chip).not.toHaveTextContent('222');
  });

  it('shows a "no longer in this server" tooltip on the departed chip', async () => {
    const user = userEvent.setup();
    render(<MemberChip member={{ id: '222', label: null }} />);

    await user.hover(screen.getByTestId('unknown-member-chip'));

    expect(await screen.findByRole('tooltip')).toHaveTextContent(/no longer in this server/i);
  });

  it('renders a real member literally named "Unknown User" as a normal chip', () => {
    render(<MemberChip member={{ id: '333', label: 'Unknown User' }} />);

    expect(screen.getByTestId('member-chip')).toHaveTextContent('@Unknown User');
    expect(screen.queryByTestId('unknown-member-chip')).not.toBeInTheDocument();
  });
});
