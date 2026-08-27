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

describe('GameForm - remindersAsDms checkbox', () => {
  it('hides checkbox when no reminder times are set (create mode)', () => {
    renderForm({ mode: 'create', initialData: undefined });
    expect(screen.queryByLabelText('Always send reminders as DMs')).not.toBeInTheDocument();
  });

  it('shows checkbox in edit mode when initialData has reminder_minutes', () => {
    renderForm({ initialData: { ...baseGame, reminder_minutes: [30] } });
    expect(screen.getByLabelText('Always send reminders as DMs')).toBeInTheDocument();
  });

  it('shows checkbox in create mode when initialData has reminder_minutes', () => {
    renderForm({ mode: 'create', initialData: { reminder_minutes: [30] } });
    expect(screen.getByLabelText('Always send reminders as DMs')).toBeInTheDocument();
  });

  it('checkbox is checked by default when reminders exist and no value is set', () => {
    renderForm({ initialData: { ...baseGame, reminder_minutes: [30] } });
    const checkbox = screen.getByLabelText('Always send reminders as DMs') as HTMLInputElement;
    expect(checkbox.checked).toBe(true);
  });

  it('checkbox reflects explicit false from initialData', () => {
    renderForm({ initialData: { ...baseGame, reminder_minutes: [30], reminders_as_dms: false } });
    const checkbox = screen.getByLabelText('Always send reminders as DMs') as HTMLInputElement;
    expect(checkbox.checked).toBe(false);
  });

  it('checkbox can be toggled off', async () => {
    const user = userEvent.setup();
    renderForm({ initialData: { ...baseGame, reminder_minutes: [30] } });
    const checkbox = screen.getByLabelText('Always send reminders as DMs') as HTMLInputElement;
    expect(checkbox.checked).toBe(true);
    await user.click(checkbox);
    expect(checkbox.checked).toBe(false);
  });
});
