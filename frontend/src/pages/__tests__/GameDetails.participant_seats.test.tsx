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

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route, useLocation } from 'react-router';
import { GameDetails } from '../GameDetails';
import { AuthContext } from '../../contexts/AuthContext';
import { apiClient } from '../../api/client';
import { CurrentUser } from '../../types';

vi.mock('../../api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

const mockUser: CurrentUser = {
  id: 'user-db-id',
  user_uuid: 'user-uuid-123',
  username: 'testuser',
};

const gameFixture = (can_manage: boolean) => ({
  id: 'game-1',
  title: 'Test Game',
  description: 'A test game',
  signup_instructions: null,
  scheduled_at: '2099-12-25T19:00:00Z',
  where: null,
  max_players: 4,
  guild_id: 'guild-1',
  guild_name: 'Test Guild',
  channel_id: 'channel-1',
  channel_name: 'general',
  message_id: null,
  host: {
    id: 'host-participant-id',
    game_session_id: 'game-1',
    user_id: 'other-user-uuid',
    discord_id: 'host-discord-id',
    display_name: 'Host User',
    avatar_url: null,
    joined_at: '2026-01-01T00:00:00Z',
    position_type: 24000,
    position: 0,
  },
  reminder_minutes: null,
  notify_role_ids: null,
  expected_duration_minutes: null,
  status: 'SCHEDULED',
  signup_method: 'SELF_SIGNUP',
  participant_count: 1,
  participants: [],
  can_manage: can_manage,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
});

/** Records the current router location so tests can assert navigation. */
const LocationProbe = () => {
  const location = useLocation();
  return <div data-testid="location-probe" data-path={location.pathname} />;
};

const renderGameDetails = () => {
  const authValue = {
    user: mockUser,
    login: vi.fn(),
    logout: vi.fn(),
    refreshUser: vi.fn(),
    loading: false,
  };
  return render(
    <AuthContext.Provider value={authValue}>
      <MemoryRouter initialEntries={['/games/game-1']}>
        <Routes>
          <Route path="/games/:gameId" element={<GameDetails />} />
          {/* Stand-in for ParticipantSeatsPage; only the route match matters here. */}
          <Route path="/games/:gameId/participant-seats" element={<div>seats page</div>} />
        </Routes>
        <LocationProbe />
      </MemoryRouter>
    </AuthContext.Provider>
  );
};

describe('GameDetails - participants header link to seat positions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders a plain (non-link) Participants header for non-managers and never fetches seats', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: gameFixture(false) } as never);

    renderGameDetails();

    await screen.findByText(/Participants \(1\/4\)/);

    expect(screen.queryByRole('link', { name: /participants/i })).not.toBeInTheDocument();
    // Only the initial game fetch happens - no lazy seats request either.
    expect(apiClient.get).toHaveBeenCalledTimes(1);
    const header = screen.getByText(/Participants \(1\/4\)/);
    await userEvent.click(header);
    expect(apiClient.get).toHaveBeenCalledTimes(1);
  });

  it('renders an underlined link pointing at the participant-seats route for hosts', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: gameFixture(true) } as never);

    renderGameDetails();

    const headerLink = await screen.findByRole('link', { name: /participants/i });
    expect(headerLink).toHaveAttribute('href', '/games/game-1/participant-seats');
    expect(apiClient.get).toHaveBeenCalledTimes(1);
  });

  it('navigates to the participant-seats page when the host clicks the header link', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: gameFixture(true) } as never);
    const user = userEvent.setup();

    renderGameDetails();

    await user.click(await screen.findByRole('link', { name: /participants/i }));

    const probe = screen.getByTestId('location-probe');
    await waitFor(() => {
      expect(probe).toHaveAttribute('data-path', '/games/game-1/participant-seats');
    });
    // The details page made no extra fetch on its own - the new page owns seats.
    expect(apiClient.get).toHaveBeenCalledTimes(1);
  });
});
