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

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { StatusCodes } from 'http-status-codes';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router';
import { DownloadCalendar } from '../DownloadCalendar';
import { AuthContext } from '../../contexts/AuthContext';
import { CurrentUser } from '../../types';

const mockNavigate = vi.fn();

vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

globalThis.fetch = vi.fn();
globalThis.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
globalThis.URL.revokeObjectURL = vi.fn();

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

  it('downloads calendar when authenticated', async () => {
    const mockBlob = new Blob(['calendar data'], { type: 'text/calendar' });
    const mockResponse = {
      ok: true,
      headers: {
        get: vi.fn(() => 'attachment; filename="Test-Game_2025-12-19.ics"'),
      },
      blob: vi.fn().mockResolvedValue(mockBlob),
    };

    vi.mocked(globalThis.fetch).mockResolvedValue(mockResponse as any);

    renderWithAuth(mockUser, false);

    await waitFor(() => {
      expect(screen.getByText('Downloading calendar...')).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith('/api/v1/export/game/game-123', {
        credentials: 'include',
      });
    });

    expect(globalThis.URL.createObjectURL).toHaveBeenCalledWith(mockBlob);
  });

  it('uses default filename when Content-Disposition header is missing', async () => {
    const mockBlob = new Blob(['calendar data'], { type: 'text/calendar' });
    const mockResponse = {
      ok: true,
      headers: {
        get: vi.fn(() => null),
      },
      blob: vi.fn().mockResolvedValue(mockBlob),
    };

    vi.mocked(globalThis.fetch).mockResolvedValue(mockResponse as any);

    renderWithAuth(mockUser, false);

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith('/api/v1/export/game/game-123', {
        credentials: 'include',
      });
    });

    expect(globalThis.URL.createObjectURL).toHaveBeenCalledWith(mockBlob);
  });

  it('shows permission denied error for 403 response', async () => {
    const mockResponse = {
      ok: false,
      status: StatusCodes.FORBIDDEN,
    };

    vi.mocked(globalThis.fetch).mockResolvedValue(mockResponse as any);

    renderWithAuth(mockUser, false);

    await waitFor(
      () => {
        expect(
          screen.getByText('You do not have permission to download this calendar.')
        ).toBeInTheDocument();
      },
      { timeout: 3000 }
    );
  });

  it('shows not found error for 404 response', async () => {
    const mockResponse = {
      ok: false,
      status: StatusCodes.NOT_FOUND,
    };

    vi.mocked(globalThis.fetch).mockResolvedValue(mockResponse as any);

    renderWithAuth(mockUser, false);

    await waitFor(
      () => {
        expect(screen.getByText('Game not found.')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );
  });

  it('shows generic error for other error status codes', async () => {
    const mockResponse = {
      ok: false,
      status: StatusCodes.INTERNAL_SERVER_ERROR,
    };

    vi.mocked(globalThis.fetch).mockResolvedValue(mockResponse as any);

    renderWithAuth(mockUser, false);

    await waitFor(
      () => {
        expect(screen.getByText('Failed to download calendar.')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );
  });

  it('shows generic error when fetch throws exception', async () => {
    vi.mocked(globalThis.fetch).mockRejectedValue(new Error('Network error'));

    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    renderWithAuth(mockUser, false);

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

  it('navigates to my-games when error alert is closed', async () => {
    const mockResponse = {
      ok: false,
      status: StatusCodes.NOT_FOUND,
    };

    vi.mocked(globalThis.fetch).mockResolvedValue(mockResponse as any);

    renderWithAuth(mockUser, false);

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
