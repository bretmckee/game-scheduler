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
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router';
import { MyGames } from '../MyGames';
import { AuthContext } from '../../contexts/AuthContext';
import { CurrentUser, Guild, GameListResponse } from '../../types';
import { apiClient } from '../../api/client';

const mockNavigate = vi.fn();

vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('../../api/client');

vi.mock('../../utils/permissions', () => ({
  canUserCreateGames: vi.fn().mockResolvedValue(true),
}));

vi.mock('../../hooks/useGameUpdates', () => ({
  useGameUpdates: vi.fn(),
}));

describe('MyGames - Server Selection Logic', () => {
  const mockUser: CurrentUser = {
    id: 'id-123',
    user_uuid: 'user-123',
    username: 'testuser',
    discordId: 'discord-123',
    avatar: null,
  };

  const mockGuild: Guild = {
    id: '1',
    guild_name: 'Test Server 1',
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  };

  const mockGamesResponse: GameListResponse = {
    games: [],
    total: 0,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === '/api/v1/games') {
        return Promise.resolve({ data: mockGamesResponse });
      }
      return Promise.resolve({ data: { guilds: [] } });
    });
  });

  const renderWithAuth = (user: CurrentUser | null = mockUser) => {
    const mockAuthValue = {
      user,
      login: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
      loading: false,
    };

    return render(
      <BrowserRouter>
        <AuthContext.Provider value={mockAuthValue}>
          <MyGames />
        </AuthContext.Provider>
      </BrowserRouter>
    );
  };

  it('navigates directly to create form when user has one server', async () => {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === '/api/v1/games') {
        return Promise.resolve({ data: mockGamesResponse });
      }
      if (url === '/api/v1/guilds') {
        return Promise.resolve({ data: { guilds: [mockGuild] } });
      }
      return Promise.resolve({ data: { guilds: [] } });
    });

    const user = userEvent.setup();
    renderWithAuth();

    await waitFor(() => {
      expect(screen.getByText('Create New Game')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Create New Game'));

    expect(mockNavigate).toHaveBeenCalledWith('/games/new');
  });

  it('navigates to create form when user has multiple servers', async () => {
    const mockGuilds: Guild[] = [
      mockGuild,
      {
        id: '2',
        guild_name: 'Test Server 2',
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
      },
    ];

    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === '/api/v1/games') {
        return Promise.resolve({ data: mockGamesResponse });
      }
      if (url === '/api/v1/guilds') {
        return Promise.resolve({ data: { guilds: mockGuilds } });
      }
      return Promise.resolve({ data: { guilds: [] } });
    });

    const user = userEvent.setup();
    renderWithAuth();

    const createButton = await screen.findByText('Create New Game', {}, { timeout: 3000 });
    expect(createButton).toBeInTheDocument();

    await user.click(createButton);

    expect(mockNavigate).toHaveBeenCalledWith('/games/new');
  });

  it('hides create button when user has no servers', async () => {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === '/api/v1/games') {
        return Promise.resolve({ data: mockGamesResponse });
      }
      if (url === '/api/v1/guilds') {
        return Promise.resolve({ data: { guilds: [] } });
      }
      return Promise.resolve({ data: { guilds: [] } });
    });

    renderWithAuth();

    // Wait for loading to complete
    await screen.findByText('My Games');

    // Button should not be in the document when there are no guilds
    const createButton = screen.queryByText('Create New Game');
    expect(createButton).not.toBeInTheDocument();
  });

  it('fetches guilds on component mount', async () => {
    renderWithAuth();

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/guilds');
    });
  });
});

describe('MyGames - SSE Integration', () => {
  const mockUser: CurrentUser = {
    id: 'id-123',
    user_uuid: 'user-123',
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

  const mockHostedGame = {
    id: 'game-1',
    title: 'Hosted Game',
    host: { user_id: 'user-123', display_name: 'testuser' },
    status: 'SCHEDULED',
    participant_count: 2,
  };

  const mockJoinedGame = {
    id: 'game-2',
    title: 'Joined Game',
    host: { user_id: 'other-user', display_name: 'other' },
    participants: [{ user_id: 'user-123' }],
    status: 'SCHEDULED',
    participant_count: 3,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('updates hosted game when SSE event received', async () => {
    let sseCallback: ((gameId: string) => void) | undefined;
    const updatedGame = { ...mockHostedGame, participant_count: 3 };

    vi.mocked(apiClient.get)
      .mockResolvedValueOnce({
        data: { games: [mockHostedGame], total: 1 },
      })
      .mockResolvedValueOnce({
        data: { guilds: [] },
      })
      .mockResolvedValueOnce({
        data: updatedGame,
      });

    const { useGameUpdates } = await import('../../hooks/useGameUpdates');
    vi.mocked(useGameUpdates).mockImplementation((_guildId, callback) => {
      sseCallback = callback;
    });

    render(
      <AuthContext.Provider value={mockAuthContext}>
        <BrowserRouter>
          <MyGames />
        </BrowserRouter>
      </AuthContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByText('Hosted Game')).toBeInTheDocument();
    });

    sseCallback!('game-1');

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/games/game-1');
    });
  });

  it('updates joined game when SSE event received', async () => {
    let sseCallback: ((gameId: string) => void) | undefined;
    const updatedGame = { ...mockJoinedGame, participant_count: 4 };

    vi.mocked(apiClient.get)
      .mockResolvedValueOnce({
        data: { games: [mockJoinedGame], total: 1 },
      })
      .mockResolvedValueOnce({
        data: { guilds: [] },
      })
      .mockResolvedValueOnce({
        data: updatedGame,
      });

    const { useGameUpdates } = await import('../../hooks/useGameUpdates');
    vi.mocked(useGameUpdates).mockImplementation((_guildId, callback) => {
      sseCallback = callback;
    });

    render(
      <AuthContext.Provider value={mockAuthContext}>
        <BrowserRouter>
          <MyGames />
        </BrowserRouter>
      </AuthContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByText('Joined Game')).toBeInTheDocument();
    });

    sseCallback!('game-2');

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/games/game-2');
    });
  });
});
