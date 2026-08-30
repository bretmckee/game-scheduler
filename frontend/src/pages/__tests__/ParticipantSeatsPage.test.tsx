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
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router';
import { ParticipantSeatsPage } from '../ParticipantSeatsPage';
import { apiClient } from '../../api/client';

vi.mock('../../api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

/** Seats as the /participant-seats endpoint returns them (see shared/schemas/game.py). */
const seatData = [
  { position: 1, discord_id: 'd-bret', name: 'bret' },
  { position: 2, discord_id: 'd-casey', name: null },
];

const stubSeatsApi = (seats: unknown) => {
  vi.mocked(apiClient.get).mockResolvedValue({ data: { seats } } as never);
};

const renderPage = () => {
  return render(
    <MemoryRouter initialEntries={['/games/game-1/participant-seats']}>
      <Routes>
        <Route path="/games/:gameId/participant-seats" element={<ParticipantSeatsPage />} />
      </Routes>
    </MemoryRouter>
  );
};

describe('ParticipantSeatsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders a table with Participant and Position headers and one row per linked user', async () => {
    stubSeatsApi(seatData);

    renderPage();

    // Column headers come from the request.
    const headers = await screen.findAllByRole('columnheader');
    expect(headers.map((el) => el.textContent)).toEqual(['Participant', 'Position']);

    // Each seat row shows its @primary-name next to its 1-based position.
    // casey resolves to null on the server, exercising the @Unknown fallback.
    await screen.findByText('@bret');
    const rows = screen.getAllByRole('row');
    expect(rows).toHaveLength(3); // header row + 2 data rows
    expect(screen.getByText('@bret').closest('tr')).toHaveTextContent('1');
    expect(screen.getByText('@Unknown').closest('tr')).toHaveTextContent('2');
  });

  it('shows an empty-state message when no users are linked yet', async () => {
    stubSeatsApi([]);

    renderPage();

    expect(await screen.findByText('No participants yet.')).toBeInTheDocument();
    expect(screen.queryAllByRole('columnheader')).toHaveLength(0);
  });

  it('falls back to @Unknown for seats whose name could not be resolved', async () => {
    stubSeatsApi([{ position: 1, discord_id: 'd-orphan', name: null }]);

    renderPage();

    expect(await screen.findByText('@Unknown')).toBeInTheDocument();
  });

  it('surfaces the endpoint error detail in an alert', async () => {
    vi.mocked(apiClient.get).mockRejectedValue({
      response: { status: 500, data: { detail: 'boom' } },
    });

    renderPage();

    const alert = await screen.findByRole('alert');
    expect(alert.textContent).toContain('Could not load participant positions: boom');
  });
});
