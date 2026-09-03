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
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { GameForm } from '../GameForm';
import { Channel, CurrentUser } from '../../types';
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

/** True when `a` appears before `b` in document order. */
function precedes(a: Element, b: Element): boolean {
  // NOTE: parenthesize the bit test — `===` binds tighter than `&`.
  return (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
}

const renderGameForm = (props = {}) => {
  const defaultProps = {
    mode: 'create' as const,
    guildId: 'guild123',
    channels: mockChannels,
    onSubmit: vi.fn(),
    onCancel: vi.fn(),
    ...props,
  };

  return render(
    <AuthContext.Provider value={mockAuthContextValue}>
      <GameForm {...defaultProps} />
    </AuthContext.Provider>
  );
};

// Written RED-first against unmodified GameForm (vitest 4 removed the .failing()
// marker), then implemented GREEN without changing any assertion below.
describe('GameForm aggregate error placement near the submit controls', () => {
  it('shows the blocked-submit message below the last form field and above the submit button', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();

    renderGameForm({ onSubmit });

    // Make Max Players invalid so submit is blocked client-side ("Please fix all validation errors...")
    const maxPlayersField = screen.getByLabelText(/Max Players/i);
    await user.clear(maxPlayersField);
    await user.click(maxPlayersField);
    await user.paste('0');
    await user.tab();

    await waitFor(() => {
      expect(screen.getByText(/must be at least 1/i)).toBeInTheDocument();
    });

    // Dispatch the form submission directly (same pattern CloneGame.test.tsx uses) so the
    // assertion does not depend on jsdom's implicit-submission behavior.
    fireEvent.submit(document.querySelector('form')!);

    const message = await waitFor(() =>
      screen.findByText(/fix all validation errors before submitting/i)
    );
    expect(message).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();

    // The message must sit next to the action buttons at the bottom of this long form —
    // where the user just clicked — instead of being stranded above the title up top.
    const anchorField = screen.getByLabelText(/Max Players/i);
    const submitButton = screen.getByRole('button', { name: /Create Game/i });
    expect(precedes(anchorField, message)).toBe(true);
    expect(precedes(message, submitButton)).toBe(true);
  });

  it('places backend participant mention errors above the action buttons', () => {
    renderGameForm({
      validationErrors: [
        {
          input: '@baduser',
          reason: 'User not found in server',
          suggestions: [],
        },
      ],
    });

    const maxPlayersInput = screen.getByLabelText(/max players/i);
    const submitButton = screen.getByRole('button', { name: /create game/i });
    const message = screen.getByText(/User not found in server/i);
    expect(message).toBeInTheDocument();

    expect(precedes(maxPlayersInput, message)).toBe(true);
    expect(precedes(message, submitButton)).toBe(true);
  });

  it('places channel reference errors above the action buttons', () => {
    renderGameForm({
      channelValidationErrors: [
        {
          type: 'channel_reference',
          input: '#nowhere',
          reason: 'Channel not found on this server',
          suggestions: [],
        },
      ],
    });

    const maxPlayersInput = screen.getByLabelText(/max players/i);
    const submitButton = screen.getByRole('button', { name: /create game/i });
    const message = screen.getByText(/Channel not found on this server/i);
    expect(message).toBeInTheDocument();

    expect(precedes(maxPlayersInput, message)).toBe(true);
    expect(precedes(message, submitButton)).toBe(true);
  });

  it('renders no aggregate error blocks when there are no errors', () => {
    renderGameForm();

    expect(screen.queryByText(/fix all validation errors/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/could not resolve some @mentions/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/invalid channel reference/i)).not.toBeInTheDocument();
  });
});
