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
import { Rewards } from '../../constants/rewards';

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
  it('shows rewards entries in edit mode when status is IN_PROGRESS', () => {
    renderForm({ initialData: { ...baseGame, status: 'IN_PROGRESS' } });
    expect(screen.getByLabelText('Reward 1')).toBeInTheDocument();
  });

  it('shows rewards entries in edit mode when status is COMPLETED', () => {
    renderForm({ initialData: { ...baseGame, status: 'COMPLETED' } });
    expect(screen.getByLabelText('Reward 1')).toBeInTheDocument();
  });

  it('hides rewards entries in edit mode when status is SCHEDULED', () => {
    renderForm({ initialData: { ...baseGame, status: 'SCHEDULED' } });
    expect(screen.queryByLabelText('Reward 1')).not.toBeInTheDocument();
    expect(screen.queryByText('+ Add another reward')).not.toBeInTheDocument();
  });

  it('hides rewards entries in create mode', () => {
    renderForm({ mode: 'create', initialData: undefined });
    expect(screen.queryByLabelText('Reward 1')).not.toBeInTheDocument();
  });
});

describe('GameForm - rewards entry list', () => {
  it('pre-populates one text box per reward entry from initialData', () => {
    renderForm({
      initialData: {
        ...baseGame,
        status: 'COMPLETED',
        rewards: ['A golden trophy', 'Line 1\nLine 2'],
      },
    });
    expect(screen.getByLabelText('Reward 1')).toHaveValue('A golden trophy');
    expect(screen.getByLabelText('Reward 2')).toHaveValue('Line 1\nLine 2');
    expect(screen.queryByLabelText('Reward 3')).not.toBeInTheDocument();
  });

  it('starts with a single empty text box when the game has no rewards', () => {
    renderForm({ initialData: { ...baseGame, rewards: null } });
    expect(screen.getByLabelText('Reward 1')).toHaveValue('');
    expect(screen.queryByLabelText('Reward 2')).not.toBeInTheDocument();
  });

  it('limits each entry to the maximum reward length', () => {
    renderForm();
    expect(screen.getByLabelText('Reward 1')).toHaveAttribute(
      'maxlength',
      String(Rewards.MAX_LENGTH)
    );
  });

  it('appends an empty text box when "+ Add another reward" is clicked', async () => {
    const user = userEvent.setup();
    renderForm({ initialData: { ...baseGame, rewards: ['First'] } });

    await user.click(screen.getByText('+ Add another reward'));

    expect(screen.getByLabelText('Reward 1')).toHaveValue('First');
    expect(screen.getByLabelText('Reward 2')).toHaveValue('');
  });

  it('disables "+ Add another reward" at the maximum number of entries', () => {
    const rewards = Array.from({ length: Rewards.MAX_ENTRIES }, (_, i) => `Prize ${i + 1}`);
    renderForm({ initialData: { ...baseGame, rewards } });
    expect(screen.getByText('+ Add another reward').closest('button')).toBeDisabled();
  });

  it('enables "+ Add another reward" one below the maximum number of entries', () => {
    const rewards = Array.from({ length: Rewards.MAX_ENTRIES - 1 }, (_, i) => `Prize ${i + 1}`);
    renderForm({ initialData: { ...baseGame, rewards } });
    expect(screen.getByText('+ Add another reward').closest('button')).toBeEnabled();
  });

  it('hides the remove button when only one entry remains', () => {
    renderForm({ initialData: { ...baseGame, rewards: ['Only'] } });
    expect(screen.queryByRole('button', { name: /remove reward/i })).not.toBeInTheDocument();
  });

  it('removes the chosen entry and keeps the others in order', async () => {
    const user = userEvent.setup();
    renderForm({ initialData: { ...baseGame, rewards: ['First', 'Second', 'Third'] } });

    await user.click(screen.getByRole('button', { name: 'Remove reward 2' }));

    expect(screen.getByLabelText('Reward 1')).toHaveValue('First');
    expect(screen.getByLabelText('Reward 2')).toHaveValue('Third');
    expect(screen.queryByLabelText('Reward 3')).not.toBeInTheDocument();
  });

  it('edits only the entry being typed into', async () => {
    const user = userEvent.setup();
    renderForm({ initialData: { ...baseGame, rewards: ['First', 'Second'] } });

    await user.type(screen.getByLabelText('Reward 2'), '!');

    expect(screen.getByLabelText('Reward 1')).toHaveValue('First');
    expect(screen.getByLabelText('Reward 2')).toHaveValue('Second!');
  });

  it('passes the entry list to onSubmit', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderForm({ initialData: { ...baseGame, rewards: ['First'] }, onSubmit });

    await user.click(screen.getByText('+ Add another reward'));
    await user.type(screen.getByLabelText('Reward 2'), 'Second');
    await user.click(screen.getByText('Save Changes'));

    expect(onSubmit).toHaveBeenCalledOnce();
    expect(onSubmit.mock.calls[0]![0].rewards).toEqual(['First', 'Second']);
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
    renderForm({ initialData: { ...baseGame, rewards: ['Prize'], archive_channel_id: 'arch-1' } });
    expect(screen.queryByText('Save and Archive')).not.toBeInTheDocument();
  });

  it('does not show Save and Archive when rewards is null', () => {
    renderForm({
      initialData: { ...baseGame, rewards: null, archive_channel_id: 'arch-1' },
      onSaveAndArchive: vi.fn(),
    });
    expect(screen.queryByText('Save and Archive')).not.toBeInTheDocument();
  });

  it('does not show Save and Archive when every entry is blank', () => {
    renderForm({
      initialData: { ...baseGame, rewards: ['', '   ', '\n'], archive_channel_id: 'arch-1' },
      onSaveAndArchive: vi.fn(),
    });
    expect(screen.queryByText('Save and Archive')).not.toBeInTheDocument();
  });

  it('shows Save and Archive when any one entry is non-blank', () => {
    renderForm({
      initialData: { ...baseGame, rewards: ['', 'Prize', ' '], archive_channel_id: 'arch-1' },
      onSaveAndArchive: vi.fn(),
    });
    expect(screen.getByText('Save and Archive')).toBeInTheDocument();
  });

  it('shows Save and Archive once a reward is typed into an empty entry', async () => {
    const user = userEvent.setup();
    renderForm({
      initialData: { ...baseGame, rewards: null, archive_channel_id: 'arch-1' },
      onSaveAndArchive: vi.fn(),
    });
    expect(screen.queryByText('Save and Archive')).not.toBeInTheDocument();

    await user.type(screen.getByLabelText('Reward 1'), 'Gold');

    expect(screen.getByText('Save and Archive')).toBeInTheDocument();
  });

  it('does not show Save and Archive when archive_channel_id is missing', () => {
    renderForm({
      initialData: { ...baseGame, rewards: ['Prize'], archive_channel_id: null },
      onSaveAndArchive: vi.fn(),
    });
    expect(screen.queryByText('Save and Archive')).not.toBeInTheDocument();
  });

  it('shows Save and Archive when onSaveAndArchive provided, rewards non-empty, and archive_channel_id set', () => {
    renderForm({
      initialData: { ...baseGame, rewards: ['A treasure chest'], archive_channel_id: 'arch-1' },
      onSaveAndArchive: vi.fn(),
    });
    expect(screen.getByText('Save and Archive')).toBeInTheDocument();
  });

  it('calls onSaveAndArchive when Save and Archive button is clicked', async () => {
    const onSaveAndArchive = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();

    renderForm({
      initialData: { ...baseGame, rewards: ['A treasure chest'], archive_channel_id: 'arch-1' },
      onSaveAndArchive,
    });

    await user.click(screen.getByText('Save and Archive'));
    expect(onSaveAndArchive).toHaveBeenCalledOnce();
    expect(onSaveAndArchive.mock.calls[0]![0].rewards).toEqual(['A treasure chest']);
  });

  it('shows error when onSaveAndArchive rejects', async () => {
    const onSaveAndArchive = vi
      .fn()
      .mockRejectedValue({ response: { data: { detail: 'Archive failed' } } });
    const user = userEvent.setup();

    renderForm({
      initialData: { ...baseGame, rewards: ['A treasure chest'], archive_channel_id: 'arch-1' },
      onSaveAndArchive,
    });

    await user.click(screen.getByText('Save and Archive'));
    expect(await screen.findByText('Archive failed')).toBeInTheDocument();
  });
});
