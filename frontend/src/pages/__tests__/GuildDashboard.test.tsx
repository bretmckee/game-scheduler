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
import { MemoryRouter, Route, Routes } from 'react-router';
import { GuildDashboard } from '../GuildDashboard';
import { apiClient } from '../../api/client';
import { Guild } from '../../types';

vi.mock('../../api/client', () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

vi.mock('../../hooks/useGameUpdates', () => ({
  useGameUpdates: vi.fn(),
}));

vi.mock('../../utils/permissions', () => ({
  canUserCreateGames: vi.fn().mockResolvedValue(false),
}));

const mockGuild: Guild = {
  id: 'guild-1',
  guild_name: 'Test Guild',
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
};

const renderWithRoute = (guildId = 'guild-1') =>
  render(
    <MemoryRouter initialEntries={[`/guilds/${guildId}`]}>
      <Routes>
        <Route path="/guilds/:guildId" element={<GuildDashboard />} />
      </Routes>
    </MemoryRouter>
  );

describe('GuildDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading spinner initially', () => {
    vi.mocked(apiClient.get).mockImplementation(() => new Promise(() => {}));
    renderWithRoute();
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('shows guild name as heading after load', async () => {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === '/api/v1/guilds/guild-1') {
        return Promise.resolve({ data: mockGuild });
      }
      if (url === '/api/v1/guilds/guild-1/config') {
        return Promise.reject({ response: { status: 403 } });
      }
      return Promise.resolve({ data: { games: [], total: 0 } });
    });

    renderWithRoute();

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /test guild/i })).toBeInTheDocument();
    });
  });

  it('renders no Tabs or tab panel after load', async () => {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === '/api/v1/guilds/guild-1') {
        return Promise.resolve({ data: mockGuild });
      }
      if (url === '/api/v1/guilds/guild-1/config') {
        return Promise.reject({ response: { status: 403 } });
      }
      return Promise.resolve({ data: { games: [], total: 0 } });
    });

    renderWithRoute();

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /test guild/i })).toBeInTheDocument();
    });

    expect(screen.queryByRole('tab')).toBeNull();
    expect(screen.queryByRole('tablist')).toBeNull();
    expect(screen.queryByRole('tabpanel')).toBeNull();
  });

  it('embeds BrowseGames content (games filter dropdowns visible)', async () => {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === '/api/v1/guilds/guild-1') {
        return Promise.resolve({ data: mockGuild });
      }
      if (url === '/api/v1/guilds/guild-1/config') {
        return Promise.reject({ response: { status: 403 } });
      }
      return Promise.resolve({ data: { games: [], total: 0 } });
    });

    renderWithRoute();

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /test guild/i })).toBeInTheDocument();
    });

    // BrowseGames filter controls should be present (Channel + Status dropdowns)
    await waitFor(() => {
      const comboboxes = screen.getAllByRole('combobox');
      expect(comboboxes.length).toBeGreaterThanOrEqual(2);
    });
  });

  it('shows "Create a Game" button in header when user has canCreateGames', async () => {
    const { canUserCreateGames } = await import('../../utils/permissions');
    vi.mocked(canUserCreateGames).mockResolvedValue(true);

    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === '/api/v1/guilds/guild-1') {
        return Promise.resolve({ data: mockGuild });
      }
      if (url === '/api/v1/guilds/guild-1/config') {
        return Promise.reject({ response: { status: 403 } });
      }
      return Promise.resolve({ data: { games: [], total: 0 } });
    });

    renderWithRoute();

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /test guild/i })).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /create a game/i })).toBeInTheDocument();
    });
  });

  it('does not show "Create a Game" button when user lacks canCreateGames', async () => {
    const { canUserCreateGames } = await import('../../utils/permissions');
    vi.mocked(canUserCreateGames).mockResolvedValue(false);

    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === '/api/v1/guilds/guild-1') {
        return Promise.resolve({ data: mockGuild });
      }
      if (url === '/api/v1/guilds/guild-1/config') {
        return Promise.reject({ response: { status: 403 } });
      }
      return Promise.resolve({ data: { games: [], total: 0 } });
    });

    renderWithRoute();

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /test guild/i })).toBeInTheDocument();
    });

    expect(screen.queryByRole('button', { name: /create a game/i })).toBeNull();
  });
});
