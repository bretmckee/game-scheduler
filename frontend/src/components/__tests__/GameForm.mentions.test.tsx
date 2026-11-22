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
import { GameForm, type GameFormData } from '../GameForm';
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
  description: 'A plain description',
  signup_instructions: null,
  scheduled_at: '2099-12-25T19:00:00Z',
  channel_id: 'channel-1',
  status: 'SCHEDULED',
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
    onSubmit: vi.fn().mockResolvedValue(undefined),
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

const submittedData = (onSubmit: ReturnType<typeof vi.fn>): GameFormData => {
  expect(onSubmit).toHaveBeenCalledOnce();
  return onSubmit.mock.calls[0]![0] as GameFormData;
};

describe('GameForm - mention tokens in description and signup instructions', () => {
  it('shows labels in the editor instead of raw tokens', () => {
    renderForm({
      initialData: {
        ...baseGame,
        description: 'Ask <@123|Kallisti> in <#456|lfg-chat>',
        signup_instructions: 'DM <@789|Xanthias (GM)>',
      },
    });

    expect(screen.getByRole('textbox', { name: /description/i })).toHaveValue(
      'Ask @Kallisti in #lfg-chat'
    );
    expect(screen.getByRole('textbox', { name: /signup instructions/i })).toHaveValue(
      'DM @Xanthias (GM)'
    );
  });

  it('submits the collapsed original text when the fields are unedited', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderForm({
      onSubmit,
      initialData: {
        ...baseGame,
        description: 'Ask <@123|Kallisti> in <#456|lfg-chat>',
        signup_instructions: 'DM <@789|Xanthias (GM)>',
      },
    });

    await user.click(screen.getByText('Save Changes'));

    const data = submittedData(onSubmit);
    expect(data.description).toBe('Ask <@123> in <#456>');
    expect(data.signupInstructions).toBe('DM <@789>');
  });

  it('maps known labels back to their tokens after an edit', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderForm({
      onSubmit,
      initialData: { ...baseGame, description: 'Ask <@123|Kallisti> in <#456|lfg-chat>' },
    });

    await user.type(screen.getByRole('textbox', { name: /description/i }), ' today');
    await user.click(screen.getByText('Save Changes'));

    expect(submittedData(onSubmit).description).toBe('Ask <@123> in <#456> today');
  });

  it('drops departed members and unknown channels from the editor and says so', () => {
    renderForm({
      initialData: {
        ...baseGame,
        description: 'Ask <@123|> or <@124|Kallisti> in <#456|>',
        signup_instructions: 'DM <@789|>',
      },
    });

    expect(screen.getByRole('textbox', { name: /description/i })).toHaveValue(
      'Ask  or @Kallisti in '
    );
    expect(screen.getByRole('textbox', { name: /signup instructions/i })).toHaveValue('DM ');
    expect(
      screen.getByText('Removed 3 mention(s) of members or channels no longer in this server')
    ).toBeInTheDocument();
    expect(screen.queryByText(/<@|<#/)).not.toBeInTheDocument();
  });

  it('shows no removal notice when nothing was removed', () => {
    renderForm({ initialData: { ...baseGame, description: 'Ask <@123|Kallisti>' } });

    expect(screen.queryByText(/no longer in this server/)).not.toBeInTheDocument();
  });

  it('does not resubmit a removed mention', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderForm({
      onSubmit,
      initialData: { ...baseGame, description: 'Ask <@123|> or <@124|Kallisti>' },
    });

    await user.click(screen.getByText('Save Changes'));

    expect(submittedData(onSubmit).description).toBe('Ask  or <@124>');
  });

  it('submits token-free text exactly as typed', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderForm({
      onSubmit,
      initialData: { ...baseGame, description: 'Ask @Kallisti', signup_instructions: '' },
    });

    await user.type(screen.getByRole('textbox', { name: /signup instructions/i }), 'DM @Xan');
    await user.click(screen.getByText('Save Changes'));

    const data = submittedData(onSubmit);
    expect(data.description).toBe('Ask @Kallisti');
    expect(data.signupInstructions).toBe('DM @Xan');
  });

  it('resets the editor text when initialData changes after mount', () => {
    const { rerender } = renderForm({ initialData: { ...baseGame, description: 'first' } });

    rerender(
      <AuthContext.Provider value={mockAuthContextValue}>
        <GameForm
          mode="edit"
          guildId="guild123"
          channels={mockChannels}
          onSubmit={vi.fn()}
          onCancel={vi.fn()}
          initialData={{ ...baseGame, description: 'Ask <@123|Kallisti>' }}
        />
      </AuthContext.Provider>
    );

    expect(screen.getByRole('textbox', { name: /description/i })).toHaveValue('Ask @Kallisti');
  });

  it('applies the same conversion to Save and Archive', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const onSaveAndArchive = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderForm({
      onSubmit,
      onSaveAndArchive,
      initialData: {
        ...baseGame,
        status: 'IN_PROGRESS',
        rewards: ['Gold'],
        archive_channel_id: 'archive-1',
        description: 'Ask <@123|Kallisti>',
      },
    });

    await user.click(screen.getByText('Save and Archive'));

    expect(onSaveAndArchive).toHaveBeenCalledOnce();
    expect((onSaveAndArchive.mock.calls[0]![0] as GameFormData).description).toBe('Ask <@123>');
  });
});

describe('GameForm - suggestion picks record the chosen ID', () => {
  const oldnameError = [
    {
      input: '@oldname',
      reason: 'User not found',
      suggestions: [{ discordId: '123', username: 'newname', displayName: 'New Name' }],
    },
  ];

  it('submits the picked member as a token after a chip pick (2a regression)', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderForm({
      onSubmit,
      validationErrors: oldnameError,
      initialData: {
        ...baseGame,
        description: 'Hosted by @oldname, join now',
        signup_instructions: 'Contact @oldname first',
      },
    });

    await user.click(screen.getByText('@newname (New Name)'));
    await user.click(screen.getByText('Save Changes'));

    const data = submittedData(onSubmit);
    expect(data.description).toBe('Hosted by <@123>, join now');
    expect(data.signupInstructions).toBe('Contact <@123> first');
  });

  it('keeps the pick when the host edits the text afterwards', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderForm({
      onSubmit,
      validationErrors: oldnameError,
      initialData: { ...baseGame, description: 'Hosted by @oldname' },
    });

    await user.click(screen.getByText('@newname (New Name)'));
    await user.type(screen.getByRole('textbox', { name: /description/i }), ' tonight');
    await user.click(screen.getByText('Save Changes'));

    expect(submittedData(onSubmit).description).toBe('Hosted by <@123> tonight');
  });

  it('resolves two members with the same display name to the one that was picked', async () => {
    // Kallisti: both members display as "Kallisti", so the editor text does not change
    // on the pick, but the submit must carry the chosen member's ID.
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderForm({
      onSubmit,
      validationErrors: [
        {
          input: '@Kallisti',
          reason: 'Multiple matches found',
          suggestions: [
            { discordId: '201', username: 'kal_one', displayName: 'Kallisti' },
            { discordId: '202', username: 'kal_two', displayName: 'Kallisti' },
          ],
        },
      ],
      initialData: { ...baseGame, description: 'Ask @Kallisti' },
    });

    await user.click(screen.getByText('@kal_two (Kallisti)'));

    expect(screen.getByRole('textbox', { name: /description/i })).toHaveValue('Ask @Kallisti');
    await user.click(screen.getByText('Save Changes'));
    expect(submittedData(onSubmit).description).toBe('Ask <@202>');
  });

  it('keeps existing tokens intact when a pick lands in otherwise unedited text', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderForm({
      onSubmit,
      validationErrors: oldnameError,
      initialData: { ...baseGame, description: 'Hosted by @oldname with <@555|Xanthias>' },
    });

    await user.click(screen.getByText('@newname (New Name)'));
    await user.click(screen.getByText('Save Changes'));

    expect(submittedData(onSubmit).description).toBe('Hosted by <@123> with <@555>');
  });

  it('inserts the channel name and submits the picked channel ID', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderForm({
      onSubmit,
      channelValidationErrors: [
        {
          type: 'ambiguous',
          input: '#lfg',
          reason: "Multiple channels match '#lfg'",
          suggestions: [
            { id: '901', name: 'lfg' },
            { id: '902', name: 'lfg' },
          ],
        },
      ],
      initialData: {
        ...baseGame,
        description: 'Meet in #lfg',
        signup_instructions: 'Post in #lfg',
      },
    });

    await user.click(screen.getAllByRole('button', { name: '#lfg' })[1]!);

    expect(screen.getByRole('textbox', { name: /description/i })).toHaveValue('Meet in #lfg');
    await user.click(screen.getByText('Save Changes'));
    const data = submittedData(onSubmit);
    expect(data.description).toBe('Meet in <#902>');
    expect(data.signupInstructions).toBe('Post in <#902>');
  });
});
