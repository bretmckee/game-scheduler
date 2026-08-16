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
import { ExportButton } from '../ExportButton';
import { mintCalendarExportToken } from '../../api/calendarExport';

vi.mock('../../api/calendarExport', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../api/calendarExport')>()),
  mintCalendarExportToken: vi.fn(),
}));

describe('ExportButton', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(window, 'location', {
      writable: true,
      value: { href: '' },
    });
    vi.spyOn(window, 'alert').mockImplementation(() => {});
  });

  it('mints a token and navigates to the public calendar URL on click', async () => {
    vi.mocked(mintCalendarExportToken).mockResolvedValue('abc123');

    render(<ExportButton gameId="game-1" />);
    await userEvent.click(screen.getByRole('button', { name: /export to calendar/i }));

    await waitFor(() => {
      expect(mintCalendarExportToken).toHaveBeenCalledWith('game-1');
    });
    expect(window.location.href).toBe('/api/v1/public/calendar/abc123.ics');
  });

  it('shows a permission-denied alert on 403 mint failure', async () => {
    vi.mocked(mintCalendarExportToken).mockRejectedValue({
      response: { status: 403 },
    });

    render(<ExportButton gameId="game-1" />);
    await userEvent.click(screen.getByRole('button', { name: /export to calendar/i }));

    await waitFor(() => {
      expect(mintCalendarExportToken).toHaveBeenCalledWith('game-1');
    });
    await waitFor(() => {
      expect(window.alert).toHaveBeenCalledWith(
        'You must be the host or a participant to export this game.'
      );
    });
  });

  it('shows a generic alert on other mint failures', async () => {
    vi.mocked(mintCalendarExportToken).mockRejectedValue(new Error('Network error'));

    render(<ExportButton gameId="game-1" />);
    await userEvent.click(screen.getByRole('button', { name: /export to calendar/i }));

    await waitFor(() => {
      expect(mintCalendarExportToken).toHaveBeenCalledWith('game-1');
    });
    await waitFor(() => {
      expect(window.alert).toHaveBeenCalledWith('Failed to export calendar. Please try again.');
    });
  });

  it('renders the export button', () => {
    render(<ExportButton gameId="game-1" />);
    expect(screen.getByRole('button', { name: /export to calendar/i })).toBeInTheDocument();
  });
});
