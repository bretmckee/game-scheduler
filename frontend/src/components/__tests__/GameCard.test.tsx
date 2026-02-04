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

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { GameCard } from '../GameCard';
import { GameSession, ParticipantType } from '../../types';

const mockGame: GameSession = {
  id: 'game-1',
  title: 'D&D Session',
  description: 'Epic adventure awaits',
  signup_instructions: null,
  scheduled_at: '2025-12-25T19:00:00Z',
  where: 'Discord',
  max_players: 6,
  guild_id: 'guild-1',
  guild_name: 'Test Server',
  channel_id: 'channel-1',
  channel_name: 'game-chat',
  message_id: null,
  host: {
    id: 'participant-1',
    game_session_id: 'game-1',
    user_id: 'user-1',
    discord_id: '123456789',
    display_name: 'DungeonMaster',
    avatar_url: 'https://cdn.discordapp.com/avatars/123456789/abc123.png',
    joined_at: '2025-12-20T10:00:00Z',
    position_type: ParticipantType.SELF_ADDED,
    position: 0,
  },
  reminder_minutes: [60, 15],
  notify_role_ids: null,
  expected_duration_minutes: 180,
  status: 'SCHEDULED',
  signup_method: 'SELF_SIGNUP',
  participant_count: 3,
  created_at: '2025-12-20T10:00:00Z',
  updated_at: '2025-12-20T10:00:00Z',
};

describe('GameCard', () => {
  it('renders game title and description', () => {
    render(
      <MemoryRouter>
        <GameCard game={mockGame} />
      </MemoryRouter>
    );

    expect(screen.getByText('D&D Session')).toBeInTheDocument();
    expect(screen.getByText('Epic adventure awaits')).toBeInTheDocument();
  });

  it('displays host avatar when avatar_url is present', () => {
    render(
      <MemoryRouter>
        <GameCard game={mockGame} />
      </MemoryRouter>
    );

    const avatar = screen.getByAltText('DungeonMaster');
    expect(avatar).toBeInTheDocument();
    expect(avatar).toHaveAttribute(
      'src',
      'https://cdn.discordapp.com/avatars/123456789/abc123.png'
    );
  });

  it('displays host name with avatar', () => {
    render(
      <MemoryRouter>
        <GameCard game={mockGame} />
      </MemoryRouter>
    );

    expect(screen.getByText('Host:')).toBeInTheDocument();
    expect(screen.getByText('DungeonMaster')).toBeInTheDocument();
  });

  it('displays initial fallback when avatar_url is null', () => {
    const gameWithoutAvatar: GameSession = {
      ...mockGame,
      host: {
        ...mockGame.host,
        avatar_url: null,
      },
    };

    render(
      <MemoryRouter>
        <GameCard game={gameWithoutAvatar} />
      </MemoryRouter>
    );

    const avatar = screen.getByText('D');
    expect(avatar).toBeInTheDocument();
    expect(screen.getByText('Host:')).toBeInTheDocument();
    expect(screen.getByText('DungeonMaster')).toBeInTheDocument();
  });

  it('displays initial fallback when avatar_url is undefined', () => {
    const gameWithoutAvatar: GameSession = {
      ...mockGame,
      host: {
        ...mockGame.host,
        avatar_url: undefined,
      },
    };

    render(
      <MemoryRouter>
        <GameCard game={gameWithoutAvatar} />
      </MemoryRouter>
    );

    const avatar = screen.getByText('D');
    expect(avatar).toBeInTheDocument();
  });

  it('displays game status and player count', () => {
    render(
      <MemoryRouter>
        <GameCard game={mockGame} />
      </MemoryRouter>
    );

    expect(screen.getByText('SCHEDULED')).toBeInTheDocument();
    expect(screen.getByText(/3\/6/)).toBeInTheDocument();
  });

  it('displays formatted scheduled time', () => {
    render(
      <MemoryRouter>
        <GameCard game={mockGame} />
      </MemoryRouter>
    );

    expect(screen.getByText(/When:/)).toBeInTheDocument();
  });

  it('displays where information when present', () => {
    render(
      <MemoryRouter>
        <GameCard game={mockGame} />
      </MemoryRouter>
    );

    expect(screen.getByText(/Where:/)).toBeInTheDocument();
    expect(screen.getByText(/Discord/)).toBeInTheDocument();
  });

  it('displays duration when present', () => {
    render(
      <MemoryRouter>
        <GameCard game={mockGame} />
      </MemoryRouter>
    );

    expect(screen.getByText(/Duration:/)).toBeInTheDocument();
    expect(screen.getByText(/3h/)).toBeInTheDocument();
  });

  it('hides actions when showActions is false', () => {
    render(
      <MemoryRouter>
        <GameCard game={mockGame} showActions={false} />
      </MemoryRouter>
    );

    expect(screen.queryByText('View Details')).not.toBeInTheDocument();
  });

  it('shows actions by default', () => {
    render(
      <MemoryRouter>
        <GameCard game={mockGame} />
      </MemoryRouter>
    );

    expect(screen.getByText('View Details')).toBeInTheDocument();
  });

  it('avatar has proper alt text for accessibility', () => {
    render(
      <MemoryRouter>
        <GameCard game={mockGame} />
      </MemoryRouter>
    );

    const avatar = screen.getByAltText('DungeonMaster');
    expect(avatar).toBeInTheDocument();
  });
});
