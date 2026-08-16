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

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { StatusCodes } from 'http-status-codes';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router';
import { DownloadCalendar } from '../DownloadCalendar';
import { AuthContext } from '../../contexts/AuthContext';
import { CurrentUser } from '../../types';
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

describe('DownloadCalendar', () => {
  const mockUser: CurrentUser = {
    id: 'id-123',
    user_uuid: 'user-123',
    username: 'testuser',
    discordId: 'discord-123',
    avatar: null,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // jsdom doesn't implement real navigation; replace `location` with a
    // plain writable object so assigning `href` is observable in assertions.
    Object.defineProperty(window, 'location', {
      writable: true,
      value: { href: '' },
    });
  });

  afterEach(() => {
    cleanup();
  });

  const renderWithAuth = (user: CurrentUser | null = mockUser, loading = false) => {
    const mockAuthValue = {
      user,
      login: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
      loading,
    };

    return render(
      <MemoryRouter initialEntries={['/download-calendar/game-123']}>
        <AuthContext.Provider value={mockAuthValue}>
          <Routes>
            <Route path="/download-calendar/:gameId" element={<DownloadCalendar />} />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    );
  };

  it('shows loading state while authenticating', () => {
    renderWithAuth(null, true);
    expect(screen.getByText('Authenticating...')).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('mints a token and navigates to the public calendar URL', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { token: 'abc123' } });

    renderWithAuth(mockUser, false);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/export/game/game-123/token');
    });

    expect(window.location.href).toBe('/api/v1/public/calendar/abc123.ics');
  });

  it('shows permission denied message on 403', async () => {
    vi.mocked(apiClient.post).mockRejectedValue({
      response: { status: StatusCodes.FORBIDDEN },
    });

    renderWithAuth(mockUser, false);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/export/game/game-123/token');
    });

    await waitFor(
      () => {
        expect(
          screen.getByText('You do not have permission to download this calendar.')
        ).toBeInTheDocument();
      },
      { timeout: 3000 }
    );
  });

  it('shows not found message on 404', async () => {
    vi.mocked(apiClient.post).mockRejectedValue({
      response: { status: StatusCodes.NOT_FOUND },
    });

    renderWithAuth(mockUser, false);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/export/game/game-123/token');
    });

    await waitFor(
      () => {
        expect(screen.getByText('Game not found.')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );
  });

  it('shows generic error message on other failures', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('Network error'));

    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    renderWithAuth(mockUser, false);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/export/game/game-123/token');
    });

    await waitFor(
      () => {
        expect(
          screen.getByText('An error occurred while downloading the calendar.')
        ).toBeInTheDocument();
      },
      { timeout: 3000 }
    );

    expect(consoleErrorSpy).toHaveBeenCalledWith('Calendar download error:', expect.any(Error));

    consoleErrorSpy.mockRestore();
  });

  it('closing the error alert navigates to /my-games', async () => {
    vi.mocked(apiClient.post).mockRejectedValue({
      response: { status: StatusCodes.NOT_FOUND },
    });

    renderWithAuth(mockUser, false);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/export/game/game-123/token');
    });

    await waitFor(
      () => {
        expect(screen.getByText('Game not found.')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );

    const closeButton = screen.getByRole('button', { name: /close/i });
    closeButton.click();

    expect(mockNavigate).toHaveBeenCalledWith('/my-games');
  });
});
