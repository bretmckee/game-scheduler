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
import { GameForm } from '../GameForm';
import { Channel, CurrentUser, GameSession, ParticipantType } from '../../types';
import { AuthContext, type AuthContextType } from '../../contexts/AuthContext';

const mockAuthContextValue: AuthContextType = {
  user: {
    id: 'test-user-id',
    user_uuid: 'test-user-uuid',
    discordId: 'user123',
    username: 'testuser',
    guilds: [],
  } as CurrentUser,
  loading: false,
  login: vi.fn(),
  logout: vi.fn(),
  refreshUser: vi.fn(),
};

const mockChannels: Channel[] = [
  {
    id: 'channel-1',
    guild_id: 'guild123',
    channel_id: 'discord-channel-1',
    channel_name: 'general',
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

const baseGame: Partial<GameSession> = {
  id: 'game-1',
  title: 'Test Game',
  description: 'A test game description',
  signup_instructions: null,
  scheduled_at: '2099-12-25T19:00:00Z',
  channel_id: 'channel-1',
  status: 'IN_PROGRESS',
  signup_method: 'SELF_SIGNUP',
  max_players: 4,
  participants: [],
  host: {
    id: 'host-1',
    game_session_id: 'game-1',
    user_id: 'user-1',
    discord_id: '111',
    display_name: 'Host',
    joined_at: '2026-01-01T00:00:00Z',
    position_type: ParticipantType.SELF_ADDED,
    position: 0,
  },
};

const renderForm = (props: Partial<Parameters<typeof GameForm>[0]> = {}) => {
  const defaultProps = {
    mode: 'edit' as const,
    guildId: 'guild123',
    channels: mockChannels,
    onSubmit: vi.fn(),
    onCancel: vi.fn(),
    initialData: baseGame,
    ...props,
  };

  return render(
    <AuthContext.Provider value={mockAuthContextValue}>
      <GameForm {...defaultProps} />
    </AuthContext.Provider>
  );
};

describe('GameForm - rewards field visibility', () => {
  it('shows rewards textarea in edit mode when status is IN_PROGRESS', () => {
    renderForm({ initialData: { ...baseGame, status: 'IN_PROGRESS' } });
    expect(screen.getByLabelText('Rewards')).toBeInTheDocument();
  });

  it('shows rewards textarea in edit mode when status is COMPLETED', () => {
    renderForm({ initialData: { ...baseGame, status: 'COMPLETED' } });
    expect(screen.getByLabelText('Rewards')).toBeInTheDocument();
  });

  it('hides rewards textarea in edit mode when status is SCHEDULED', () => {
    renderForm({ initialData: { ...baseGame, status: 'SCHEDULED' } });
    expect(screen.queryByLabelText('Rewards')).not.toBeInTheDocument();
  });

  it('hides rewards textarea in create mode', () => {
    renderForm({ mode: 'create', initialData: undefined });
    expect(screen.queryByLabelText('Rewards')).not.toBeInTheDocument();
  });

  it('pre-populates rewards field from initialData', () => {
    renderForm({ initialData: { ...baseGame, status: 'COMPLETED', rewards: 'A golden trophy' } });
    expect(screen.getByDisplayValue('A golden trophy')).toBeInTheDocument();
  });
});

describe('GameForm - remindHostRewards checkbox', () => {
  it('shows checkbox in create mode', () => {
    renderForm({ mode: 'create', initialData: undefined });
    expect(
      screen.getByLabelText('Remind me to add rewards when the game completes')
    ).toBeInTheDocument();
  });

  it('shows checkbox in edit mode', () => {
    renderForm();
    expect(
      screen.getByLabelText('Remind me to add rewards when the game completes')
    ).toBeInTheDocument();
  });

  it('checkbox is unchecked by default', () => {
    renderForm({ mode: 'create', initialData: undefined });
    const checkbox = screen.getByLabelText(
      'Remind me to add rewards when the game completes'
    ) as HTMLInputElement;
    expect(checkbox.checked).toBe(false);
  });

  it('checkbox reflects remind_host_rewards from initialData', () => {
    renderForm({ initialData: { ...baseGame, remind_host_rewards: true } });
    const checkbox = screen.getByLabelText(
      'Remind me to add rewards when the game completes'
    ) as HTMLInputElement;
    expect(checkbox.checked).toBe(true);
  });

  it('checkbox can be toggled', async () => {
    const user = userEvent.setup();
    renderForm({ mode: 'create', initialData: undefined });
    const checkbox = screen.getByLabelText(
      'Remind me to add rewards when the game completes'
    ) as HTMLInputElement;
    expect(checkbox.checked).toBe(false);
    await user.click(checkbox);
    expect(checkbox.checked).toBe(true);
  });
});

describe('GameForm - Save and Archive button', () => {
  it('does not show Save and Archive when onSaveAndArchive is not provided', () => {
    renderForm({ initialData: { ...baseGame, rewards: 'Prize', archive_channel_id: 'arch-1' } });
    expect(screen.queryByText('Save and Archive')).not.toBeInTheDocument();
  });

  it('does not show Save and Archive when rewards is empty', () => {
    renderForm({
      initialData: { ...baseGame, rewards: '', archive_channel_id: 'arch-1' },
      onSaveAndArchive: vi.fn(),
    });
    expect(screen.queryByText('Save and Archive')).not.toBeInTheDocument();
  });

  it('does not show Save and Archive when archive_channel_id is missing', () => {
    renderForm({
      initialData: { ...baseGame, rewards: 'Prize', archive_channel_id: null },
      onSaveAndArchive: vi.fn(),
    });
    expect(screen.queryByText('Save and Archive')).not.toBeInTheDocument();
  });

  it('shows Save and Archive when onSaveAndArchive provided, rewards non-empty, and archive_channel_id set', () => {
    renderForm({
      initialData: { ...baseGame, rewards: 'A treasure chest', archive_channel_id: 'arch-1' },
      onSaveAndArchive: vi.fn(),
    });
    expect(screen.getByText('Save and Archive')).toBeInTheDocument();
  });

  it('calls onSaveAndArchive when Save and Archive button is clicked', async () => {
    const onSaveAndArchive = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();

    renderForm({
      initialData: { ...baseGame, rewards: 'A treasure chest', archive_channel_id: 'arch-1' },
      onSaveAndArchive,
    });

    await user.click(screen.getByText('Save and Archive'));
    expect(onSaveAndArchive).toHaveBeenCalledOnce();
  });

  it('shows error when onSaveAndArchive rejects', async () => {
    const onSaveAndArchive = vi
      .fn()
      .mockRejectedValue({ response: { data: { detail: 'Archive failed' } } });
    const user = userEvent.setup();

    renderForm({
      initialData: { ...baseGame, rewards: 'A treasure chest', archive_channel_id: 'arch-1' },
      onSaveAndArchive,
    });

    await user.click(screen.getByText('Save and Archive'));
    expect(await screen.findByText('Archive failed')).toBeInTheDocument();
  });
});
