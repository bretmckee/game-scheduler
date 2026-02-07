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

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import userEvent from '@testing-library/user-event';
import { GameCard } from '../GameCard';
import { GameSession, ParticipantType } from '../../types';
import { apiClient } from '../../api/client';
import { AuthContext } from '../../contexts/AuthContext';

vi.mock('../../api/client', () => ({
  apiClient: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

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

const mockAuthContext = {
  user: null,
  login: vi.fn(),
  logout: vi.fn(),
  refreshToken: vi.fn(),
  loading: false,
  refreshUser: vi.fn(),
};

const renderWithAuth = (ui: React.ReactElement) => {
  return render(
    <AuthContext.Provider value={mockAuthContext}>
      <MemoryRouter>{ui}</MemoryRouter>
    </AuthContext.Provider>
  );
};

describe('GameCard', () => {
  it('renders game title and description', () => {
    renderWithAuth(<GameCard game={mockGame} />);

    expect(screen.getByText('D&D Session')).toBeInTheDocument();
    expect(screen.getByText('Epic adventure awaits')).toBeInTheDocument();
  });

  it('displays host avatar when avatar_url is present', () => {
    renderWithAuth(<GameCard game={mockGame} />);

    const avatar = screen.getByAltText('DungeonMaster');
    expect(avatar).toBeInTheDocument();
    expect(avatar).toHaveAttribute(
      'src',
      'https://cdn.discordapp.com/avatars/123456789/abc123.png'
    );
  });

  it('displays host name with avatar', () => {
    renderWithAuth(<GameCard game={mockGame} />);

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

    renderWithAuth(<GameCard game={gameWithoutAvatar} />);

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

    renderWithAuth(<GameCard game={gameWithoutAvatar} />);

    const avatar = screen.getByText('D');
    expect(avatar).toBeInTheDocument();
  });

  it('displays game status and player count', () => {
    renderWithAuth(<GameCard game={mockGame} />);

    expect(screen.getByText('SCHEDULED')).toBeInTheDocument();
    expect(screen.getByText(/3\/6/)).toBeInTheDocument();
  });

  it('displays formatted scheduled time', () => {
    renderWithAuth(<GameCard game={mockGame} />);

    expect(screen.getByText(/When:/)).toBeInTheDocument();
  });

  it('displays where information when present', () => {
    renderWithAuth(<GameCard game={mockGame} />);

    expect(screen.getByText(/Where:/)).toBeInTheDocument();
    expect(screen.getByText(/Discord/)).toBeInTheDocument();
  });

  it('displays duration when present', () => {
    renderWithAuth(<GameCard game={mockGame} />);

    expect(screen.getByText(/Duration:/)).toBeInTheDocument();
    expect(screen.getByText(/3h/)).toBeInTheDocument();
  });

  it('hides actions when showActions is false', () => {
    renderWithAuth(<GameCard game={mockGame} showActions={false} />);

    expect(screen.queryByText('View Details')).not.toBeInTheDocument();
  });

  it('shows actions by default', () => {
    renderWithAuth(<GameCard game={mockGame} />);

    expect(screen.getByText('View Details')).toBeInTheDocument();
  });

  it('avatar has proper alt text for accessibility', () => {
    renderWithAuth(<GameCard game={mockGame} />);

    const avatar = screen.getByAltText('DungeonMaster');
    expect(avatar).toBeInTheDocument();
  });
});

describe('GameCard - Join/Leave Functionality', () => {
  const mockUser = {
    id: 'user-1',
    user_uuid: 'user-uuid-1',
    username: 'testuser',
  };

  const mockAuthContext = {
    user: mockUser,
    login: vi.fn(),
    logout: vi.fn(),
    refreshToken: vi.fn(),
    loading: false,
    refreshUser: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows join button for non-participant when game is scheduled', () => {
    render(
      <AuthContext.Provider value={mockAuthContext}>
        <MemoryRouter>
          <GameCard game={mockGame} />
        </MemoryRouter>
      </AuthContext.Provider>
    );

    expect(screen.getByText('Join')).toBeInTheDocument();
    expect(screen.queryByText('Leave')).not.toBeInTheDocument();
  });

  it('shows leave button for participant when game is scheduled', async () => {
    const gameWithUser: GameSession = {
      ...mockGame,
      participants: [
        {
          ...mockGame.host,
          user_id: 'user-uuid-1',
          display_name: 'testuser',
        },
      ],
    };

    render(
      <AuthContext.Provider value={mockAuthContext}>
        <MemoryRouter>
          <GameCard game={gameWithUser} />
        </MemoryRouter>
      </AuthContext.Provider>
    );

    expect(screen.getByText('Leave')).toBeInTheDocument();
    expect(screen.queryByText('Join')).not.toBeInTheDocument();
  });

  it('shows join button for host who is not yet a participant', () => {
    const gameWithUserAsHost: GameSession = {
      ...mockGame,
      host: {
        ...mockGame.host,
        user_id: 'user-uuid-1',
      },
      participants: [],
    };

    render(
      <AuthContext.Provider value={mockAuthContext}>
        <MemoryRouter>
          <GameCard game={gameWithUserAsHost} />
        </MemoryRouter>
      </AuthContext.Provider>
    );

    expect(screen.getByText('Join')).toBeInTheDocument();
    expect(screen.queryByText('Leave')).not.toBeInTheDocument();
  });

  it('does not show join/leave buttons when game is not scheduled', () => {
    const completedGame: GameSession = {
      ...mockGame,
      status: 'COMPLETED',
    };

    render(
      <AuthContext.Provider value={mockAuthContext}>
        <MemoryRouter>
          <GameCard game={completedGame} />
        </MemoryRouter>
      </AuthContext.Provider>
    );

    expect(screen.queryByText('Join')).not.toBeInTheDocument();
    expect(screen.queryByText('Leave')).not.toBeInTheDocument();
  });

  it('calls join API and updates game on join button click', async () => {
    const user = userEvent.setup();
    const updatedGame: GameSession = {
      ...mockGame,
      participant_count: 4,
    };
    const onGameUpdate = vi.fn();

    vi.mocked(apiClient.post).mockResolvedValue({ data: {} });
    vi.mocked(apiClient.get).mockResolvedValue({ data: updatedGame });

    render(
      <AuthContext.Provider value={mockAuthContext}>
        <MemoryRouter>
          <GameCard game={mockGame} onGameUpdate={onGameUpdate} />
        </MemoryRouter>
      </AuthContext.Provider>
    );

    const joinButton = screen.getByText('Join');
    await user.click(joinButton);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/games/game-1/join');
      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/games/game-1');
      expect(onGameUpdate).toHaveBeenCalledWith(updatedGame);
    });
  });

  it('calls leave API and updates game on leave button click', async () => {
    const user = userEvent.setup();
    const gameWithUser: GameSession = {
      ...mockGame,
      participants: [
        {
          ...mockGame.host,
          user_id: 'user-uuid-1',
        },
      ],
    };
    const updatedGame: GameSession = {
      ...mockGame,
      participant_count: 2,
    };
    const onGameUpdate = vi.fn();

    vi.mocked(apiClient.post).mockResolvedValue({ data: {} });
    vi.mocked(apiClient.get).mockResolvedValue({ data: updatedGame });

    render(
      <AuthContext.Provider value={mockAuthContext}>
        <MemoryRouter>
          <GameCard game={gameWithUser} onGameUpdate={onGameUpdate} />
        </MemoryRouter>
      </AuthContext.Provider>
    );

    const leaveButton = screen.getByText('Leave');
    await user.click(leaveButton);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/games/game-1/leave');
      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/games/game-1');
      expect(onGameUpdate).toHaveBeenCalledWith(updatedGame);
    });
  });

  it('refetches game state when join fails', async () => {
    const user = userEvent.setup();
    const onGameUpdate = vi.fn();
    const errorResponse = {
      response: {
        data: {
          detail: 'Game is full',
        },
      },
    };

    vi.mocked(apiClient.post).mockRejectedValue(errorResponse);
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockGame });

    render(
      <AuthContext.Provider value={mockAuthContext}>
        <MemoryRouter>
          <GameCard game={mockGame} onGameUpdate={onGameUpdate} />
        </MemoryRouter>
      </AuthContext.Provider>
    );

    const joinButton = screen.getByText('Join');
    await user.click(joinButton);

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith(`/api/v1/games/${mockGame.id}`);
      expect(onGameUpdate).toHaveBeenCalledWith(mockGame);
    });
  });

  it('refetches game state when join fails with generic error', async () => {
    const user = userEvent.setup();
    const onGameUpdate = vi.fn();

    vi.mocked(apiClient.post).mockRejectedValue(new Error('Network error'));
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockGame });

    render(
      <AuthContext.Provider value={mockAuthContext}>
        <MemoryRouter>
          <GameCard game={mockGame} onGameUpdate={onGameUpdate} />
        </MemoryRouter>
      </AuthContext.Provider>
    );

    const joinButton = screen.getByText('Join');
    await user.click(joinButton);

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith(`/api/v1/games/${mockGame.id}`);
      expect(onGameUpdate).toHaveBeenCalledWith(mockGame);
    });
  });

  it('disables buttons during loading state', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.post).mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 100))
    );

    render(
      <AuthContext.Provider value={mockAuthContext}>
        <MemoryRouter>
          <GameCard game={mockGame} />
        </MemoryRouter>
      </AuthContext.Provider>
    );

    const joinButton = screen.getByText('Join');
    await user.click(joinButton);

    expect(joinButton).toBeDisabled();
  });

  it('refetches game state when leave fails', async () => {
    const user = userEvent.setup();
    const onGameUpdate = vi.fn();
    const gameWithParticipant: GameSession = {
      ...mockGame,
      participants: [
        {
          id: 'participant-2',
          game_session_id: mockGame.id,
          user_id: 'user-uuid-1',
          discord_id: '987654321',
          display_name: 'testuser',
          avatar_url: null,
          joined_at: '2025-12-20T11:00:00Z',
          position_type: ParticipantType.SELF_ADDED,
          position: 1,
        },
      ],
    };

    vi.mocked(apiClient.post).mockRejectedValue(new Error('Network error'));
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockGame });

    render(
      <AuthContext.Provider value={{ ...mockAuthContext, user: mockUser }}>
        <MemoryRouter>
          <GameCard game={gameWithParticipant} onGameUpdate={onGameUpdate} />
        </MemoryRouter>
      </AuthContext.Provider>
    );

    const leaveButton = screen.getByText('Leave');
    await user.click(leaveButton);

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith(`/api/v1/games/${mockGame.id}`);
      expect(onGameUpdate).toHaveBeenCalledWith(mockGame);
    });
  });
});
