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
import { ServerSelectionDialog } from '../ServerSelectionDialog';
import { Guild } from '../../types';

describe('ServerSelectionDialog', () => {
  const mockGuilds: Guild[] = [
    {
      id: '1',
      guild_name: 'Test Server 1',
      created_at: '2025-01-01T00:00:00Z',
      updated_at: '2025-01-01T00:00:00Z',
    },
    {
      id: '2',
      guild_name: 'Test Server 2',
      created_at: '2025-01-01T00:00:00Z',
      updated_at: '2025-01-01T00:00:00Z',
    },
  ];

  it('renders dialog when open', () => {
    const onClose = vi.fn();
    const onSelect = vi.fn();

    render(
      <ServerSelectionDialog
        open={true}
        onClose={onClose}
        guilds={mockGuilds}
        onSelect={onSelect}
      />
    );

    expect(screen.getByText('Select Server')).toBeInTheDocument();
    expect(screen.getByText('Test Server 1')).toBeInTheDocument();
    expect(screen.getByText('Test Server 2')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    const onClose = vi.fn();
    const onSelect = vi.fn();

    render(
      <ServerSelectionDialog
        open={false}
        onClose={onClose}
        guilds={mockGuilds}
        onSelect={onSelect}
      />
    );

    expect(screen.queryByText('Select Server')).not.toBeInTheDocument();
  });

  it('calls onSelect when server is clicked', async () => {
    const onClose = vi.fn();
    const onSelect = vi.fn();
    const user = userEvent.setup();

    render(
      <ServerSelectionDialog
        open={true}
        onClose={onClose}
        guilds={mockGuilds}
        onSelect={onSelect}
      />
    );

    await user.click(screen.getByText('Test Server 1'));

    expect(onSelect).toHaveBeenCalledWith(mockGuilds[0]);
  });

  it('calls onClose when Cancel button is clicked', async () => {
    const onClose = vi.fn();
    const onSelect = vi.fn();
    const user = userEvent.setup();

    render(
      <ServerSelectionDialog
        open={true}
        onClose={onClose}
        guilds={mockGuilds}
        onSelect={onSelect}
      />
    );

    await user.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(onClose).toHaveBeenCalled();
  });

  it('renders all guilds in the list', () => {
    const onClose = vi.fn();
    const onSelect = vi.fn();

    render(
      <ServerSelectionDialog
        open={true}
        onClose={onClose}
        guilds={mockGuilds}
        onSelect={onSelect}
      />
    );

    mockGuilds.forEach((guild) => {
      expect(screen.getByText(guild.guild_name)).toBeInTheDocument();
    });
  });

  it('handles empty guilds array', () => {
    const onClose = vi.fn();
    const onSelect = vi.fn();

    render(<ServerSelectionDialog open={true} onClose={onClose} guilds={[]} onSelect={onSelect} />);

    expect(screen.getByText('Select Server')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Test Server/ })).not.toBeInTheDocument();
  });
});
