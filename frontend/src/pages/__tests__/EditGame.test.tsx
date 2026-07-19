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
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router';
import { EditGame } from '../EditGame';
import { apiClient } from '../../api/client';
import { GameSession, Channel, Participant, ParticipantType } from '../../types';
import { AuthContext } from '../../contexts/AuthContext';

const mockNavigate = vi.fn();
const mockParams = { gameId: 'game123' };

const mockAuthContextValue = {
  user: { id: '1', user_uuid: 'uuid1', username: 'testuser' },
  loading: false,
  login: vi.fn(),
  logout: vi.fn(),
  refreshUser: vi.fn(),
};

vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => mockParams,
  };
});

vi.mock('../../api/client');

describe('EditGame', () => {
  const mockGame: GameSession = {
    id: 'game123',
    title: 'Test Game',
    description: 'Test Description',
    signup_instructions: 'Test signup instructions',
    scheduled_at: '2025-12-01T18:00:00Z',
    where: null,
    max_players: 8,
    guild_id: 'guild123',
    guild_name: 'Test Server',
    channel_id: 'channel123',
    channel_name: 'Test Channel',
    message_id: null,
    host: {
      id: 'host-participant-id',
      game_session_id: 'game123',
      user_id: 'user123',
      discord_id: '123456789',
      display_name: 'Test Host',
      joined_at: '2025-01-01T00:00:00Z',
      position_type: ParticipantType.SELF_ADDED,
      position: 0,
    },
    reminder_minutes: [60, 15],
    notify_role_ids: [],
    expected_duration_minutes: null,
    status: 'SCHEDULED',
    signup_method: 'SELF_SIGNUP',
    participant_count: 3,
    participants: [],
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  };

  const mockChannels: Channel[] = [
    {
      id: 'channel123',
      guild_id: 'guild123',
      channel_id: '987654321',
      channel_name: 'Test Channel',
      is_active: true,
      created_at: '2025-01-01T00:00:00Z',
      updated_at: '2025-01-01T00:00:00Z',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loads and displays game data', async () => {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url.includes('/games/')) {
        return Promise.resolve({ data: mockGame });
      }
      if (url.includes('/channels')) {
        return Promise.resolve({ data: mockChannels });
      }
      if (url.includes('/roles')) {
        return Promise.resolve({ data: [] });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    render(
      <AuthContext.Provider value={mockAuthContextValue}>
        <BrowserRouter>
          <EditGame />
        </BrowserRouter>
      </AuthContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue('Test Game')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Test Description')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Test signup instructions')).toBeInTheDocument();
      expect(screen.getByDisplayValue('8')).toBeInTheDocument();
    });

    // Check reminder selector is present (chips may take longer to render)
    await waitFor(() => {
      expect(screen.getByLabelText('Add Reminder Time')).toBeInTheDocument();
    });
  });

  it('displays loading state initially', () => {
    vi.mocked(apiClient.get).mockImplementation(() => new Promise(() => {}));

    render(
      <AuthContext.Provider value={mockAuthContextValue}>
        <BrowserRouter>
          <EditGame />
        </BrowserRouter>
      </AuthContext.Provider>
    );

    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('displays error when game not found', async () => {
    vi.mocked(apiClient.get).mockRejectedValueOnce(new Error('Game not found'));

    render(
      <AuthContext.Provider value={mockAuthContextValue}>
        <BrowserRouter>
          <EditGame />
        </BrowserRouter>
      </AuthContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByText('Game not found')).toBeInTheDocument();
    });
  });

  it('handles save successfully', async () => {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url.includes('/games/')) {
        return Promise.resolve({ data: mockGame });
      }
      if (url.includes('/channels')) {
        return Promise.resolve({ data: mockChannels });
      }
      if (url.includes('/roles')) {
        return Promise.resolve({ data: [] });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    vi.mocked(apiClient.put).mockResolvedValueOnce({ data: mockGame });

    const user = userEvent.setup();

    render(
      <AuthContext.Provider value={mockAuthContextValue}>
        <BrowserRouter>
          <EditGame />
        </BrowserRouter>
      </AuthContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue('Test Game')).toBeInTheDocument();
    });

    const saveButton = screen.getByText('Save Changes');
    await user.click(saveButton);

    await waitFor(() => {
      expect(apiClient.put).toHaveBeenCalledWith(
        '/api/v1/games/game123',
        expect.any(FormData),
        expect.objectContaining({
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        })
      );
      expect(mockNavigate).toHaveBeenCalledWith('/games/game123');
    });
  });

  it('handles cancel button', async () => {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url.includes('/games/')) {
        return Promise.resolve({ data: mockGame });
      }
      if (url.includes('/channels')) {
        return Promise.resolve({ data: mockChannels });
      }
      if (url.includes('/roles')) {
        return Promise.resolve({ data: [] });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    const user = userEvent.setup();

    render(
      <AuthContext.Provider value={mockAuthContextValue}>
        <BrowserRouter>
          <EditGame />
        </BrowserRouter>
      </AuthContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue('Test Game')).toBeInTheDocument();
    });

    const cancelButton = screen.getByText('Cancel');
    await user.click(cancelButton);

    expect(mockNavigate).toHaveBeenCalledWith('/games/game123');
  });

  it('has required field validation', async () => {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url.includes('/games/')) {
        return Promise.resolve({ data: mockGame });
      }
      if (url.includes('/channels')) {
        return Promise.resolve({ data: mockChannels });
      }
      if (url.includes('/roles')) {
        return Promise.resolve({ data: [] });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    render(
      <AuthContext.Provider value={mockAuthContextValue}>
        <BrowserRouter>
          <EditGame />
        </BrowserRouter>
      </AuthContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue('Test Game')).toBeInTheDocument();
    });

    const titleInput = screen.getByLabelText(/Game Title/i);
    const descriptionInput = screen.getByLabelText(/Description/i);

    expect(titleInput).toHaveAttribute('required');
    expect(descriptionInput).toHaveAttribute('required');
  });

  it('handles update error', async () => {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url.includes('/games/')) {
        return Promise.resolve({ data: mockGame });
      }
      if (url.includes('/channels')) {
        return Promise.resolve({ data: mockChannels });
      }
      if (url.includes('/roles')) {
        return Promise.resolve({ data: [] });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    vi.mocked(apiClient.put).mockRejectedValueOnce({
      response: { data: { detail: 'Update failed' } },
    });

    const user = userEvent.setup();

    render(
      <AuthContext.Provider value={mockAuthContextValue}>
        <BrowserRouter>
          <EditGame />
        </BrowserRouter>
      </AuthContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue('Test Game')).toBeInTheDocument();
    });

    const saveButton = screen.getByText('Save Changes');
    await user.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText('Update failed')).toBeInTheDocument();
    });
  });

  it('shows Save and Archive button when rewards, archive_channel_id, and IN_PROGRESS', async () => {
    const gameWithRewards: GameSession = {
      ...mockGame,
      status: 'IN_PROGRESS',
      rewards: 'A treasure chest',
      archive_channel_id: 'archive-ch-1',
    };

    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url.includes('/games/')) return Promise.resolve({ data: gameWithRewards });
      if (url.includes('/channels')) return Promise.resolve({ data: mockChannels });
      if (url.includes('/roles')) return Promise.resolve({ data: [] });
      return Promise.reject(new Error('Unknown URL'));
    });

    render(
      <AuthContext.Provider value={mockAuthContextValue}>
        <BrowserRouter>
          <EditGame />
        </BrowserRouter>
      </AuthContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByText('Save and Archive')).toBeInTheDocument();
    });
  });

  it('shows channel validation errors when PUT returns 422 with channel invalid_mentions', async () => {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url.includes('/games/')) return Promise.resolve({ data: mockGame });
      if (url.includes('/channels')) return Promise.resolve({ data: mockChannels });
      if (url.includes('/roles')) return Promise.resolve({ data: [] });
      return Promise.reject(new Error('Unknown URL'));
    });

    vi.mocked(apiClient.put).mockRejectedValueOnce({
      response: {
        status: StatusCodes.UNPROCESSABLE_ENTITY,
        data: {
          detail: {
            error: 'invalid_mentions',
            message: 'Some channel mentions could not be resolved',
            invalid_mentions: [
              {
                type: 'not_found',
                input: '#nonexistent',
                reason: "Channel '#nonexistent' not found",
                suggestions: [
                  { id: '789', name: 'general' },
                  { id: '012', name: 'announcements' },
                ],
              },
            ],
            valid_participants: [],
          },
        },
      },
    });

    const user = userEvent.setup();

    render(
      <AuthContext.Provider value={mockAuthContextValue}>
        <BrowserRouter>
          <EditGame />
        </BrowserRouter>
      </AuthContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue('Test Game')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Save Changes'));

    await waitFor(() => {
      expect(screen.getByText('Invalid channel reference')).toBeInTheDocument();
    });

    expect(screen.getByText('#nonexistent')).toBeInTheDocument();
    expect(screen.getByText(/Channel '#nonexistent' not found/)).toBeInTheDocument();
    expect(screen.getByText('#general')).toBeInTheDocument();
  });

  it('channel suggestion click clears channel validation errors in EditGame', async () => {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url.includes('/games/')) return Promise.resolve({ data: mockGame });
      if (url.includes('/channels')) return Promise.resolve({ data: mockChannels });
      if (url.includes('/roles')) return Promise.resolve({ data: [] });
      return Promise.reject(new Error('Unknown URL'));
    });

    vi.mocked(apiClient.put).mockRejectedValueOnce({
      response: {
        status: StatusCodes.UNPROCESSABLE_ENTITY,
        data: {
          detail: {
            error: 'invalid_mentions',
            message: 'Some channel mentions could not be resolved',
            invalid_mentions: [
              {
                type: 'not_found',
                input: '#nonexistent',
                reason: "Channel '#nonexistent' not found",
                suggestions: [{ id: '789', name: 'general' }],
              },
            ],
            valid_participants: [],
          },
        },
      },
    });

    const user = userEvent.setup();

    render(
      <AuthContext.Provider value={mockAuthContextValue}>
        <BrowserRouter>
          <EditGame />
        </BrowserRouter>
      </AuthContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue('Test Game')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Save Changes'));

    await waitFor(() => {
      expect(screen.getByText('Invalid channel reference')).toBeInTheDocument();
    });

    await user.click(screen.getByText('#general'));

    await waitFor(() => {
      expect(screen.queryByText('Invalid channel reference')).not.toBeInTheDocument();
    });
  });

  it('participant suggestion click removes only that error in EditGame', async () => {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url.includes('/games/')) return Promise.resolve({ data: mockGame });
      if (url.includes('/channels')) return Promise.resolve({ data: mockChannels });
      if (url.includes('/roles')) return Promise.resolve({ data: [] });
      return Promise.reject(new Error('Unknown URL'));
    });

    vi.mocked(apiClient.put).mockRejectedValueOnce({
      response: {
        status: StatusCodes.UNPROCESSABLE_ENTITY,
        data: {
          detail: {
            error: 'invalid_mentions',
            message: 'Some mentions could not be resolved',
            invalid_mentions: [
              {
                input: '@user1',
                reason: 'User not found',
                suggestions: [{ discordId: '1', username: 'alice', displayName: 'Alice' }],
              },
              {
                input: '@user2',
                reason: 'User not found',
                suggestions: [{ discordId: '2', username: 'bob', displayName: 'Bob' }],
              },
            ],
            valid_participants: [],
          },
        },
      },
    });

    const user = userEvent.setup();

    render(
      <AuthContext.Provider value={mockAuthContextValue}>
        <BrowserRouter>
          <EditGame />
        </BrowserRouter>
      </AuthContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue('Test Game')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Save Changes'));

    await waitFor(() => {
      expect(screen.getByText('@user1')).toBeInTheDocument();
      expect(screen.getByText('@user2')).toBeInTheDocument();
    });

    await user.click(screen.getByText('@alice (Alice)'));

    await waitFor(() => {
      expect(screen.queryByText('@user1')).not.toBeInTheDocument();
    });
    expect(screen.getByText('@user2')).toBeInTheDocument();
  });

  it('calls PUT with archive_delay_seconds: 1 when Save and Archive is clicked', async () => {
    const gameWithRewards: GameSession = {
      ...mockGame,
      status: 'IN_PROGRESS',
      rewards: 'A treasure chest',
      archive_channel_id: 'archive-ch-1',
    };

    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url.includes('/games/')) return Promise.resolve({ data: gameWithRewards });
      if (url.includes('/channels')) return Promise.resolve({ data: mockChannels });
      if (url.includes('/roles')) return Promise.resolve({ data: [] });
      return Promise.reject(new Error('Unknown URL'));
    });

    vi.mocked(apiClient.put).mockResolvedValueOnce({ data: gameWithRewards });

    const user = userEvent.setup();

    render(
      <AuthContext.Provider value={mockAuthContextValue}>
        <BrowserRouter>
          <EditGame />
        </BrowserRouter>
      </AuthContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByText('Save and Archive')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Save and Archive'));

    await waitFor(() => {
      expect(apiClient.put).toHaveBeenCalledWith(
        '/api/v1/games/game123',
        expect.any(FormData),
        expect.objectContaining({ headers: { 'Content-Type': 'multipart/form-data' } })
      );
      const calls = vi.mocked(apiClient.put).mock.calls;
      expect(calls.length).toBeGreaterThan(0);
      const formData = calls[0]?.[1] as FormData;
      expect(formData.get('archive_delay_seconds')).toBe('1');
      expect(mockNavigate).toHaveBeenCalledWith('/games/game123');
    });
  });

  const selfAddedParticipant = (id: string, name: string, joinedAt: string): Participant => ({
    id,
    game_session_id: 'game123',
    user_id: `user-${id}`,
    discord_id: id,
    display_name: name,
    joined_at: joinedAt,
    position_type: ParticipantType.SELF_ADDED,
    position: 32767,
  });

  it('includes the full disturbed prefix, not just the literally-moved participant, in the submitted payload', async () => {
    const gameWithParticipants: GameSession = {
      ...mockGame,
      participants: [
        selfAddedParticipant('p1', 'P1', '2025-01-01T00:00:00Z'),
        selfAddedParticipant('p2', 'P2', '2025-01-01T00:01:00Z'),
        selfAddedParticipant('p3', 'P3', '2025-01-01T00:02:00Z'),
      ],
    };

    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url.includes('/games/')) return Promise.resolve({ data: gameWithParticipants });
      if (url.includes('/channels')) return Promise.resolve({ data: mockChannels });
      if (url.includes('/roles')) return Promise.resolve({ data: [] });
      return Promise.reject(new Error('Unknown URL'));
    });
    vi.mocked(apiClient.put).mockResolvedValueOnce({ data: gameWithParticipants });

    const user = userEvent.setup();

    render(
      <AuthContext.Provider value={mockAuthContextValue}>
        <BrowserRouter>
          <EditGame />
        </BrowserRouter>
      </AuthContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue('@P1')).toBeInTheDocument();
    });

    // Drag P1 (topmost) past P2 and P3, so it lands last: [P2, P3, P1]
    const draggedRow = screen.getByDisplayValue('@P1').closest('[draggable="true"]')!;
    const dropTargetRow = screen.getByDisplayValue('@P3').closest('[draggable="true"]')!;
    fireEvent.dragStart(draggedRow);
    fireEvent.dragOver(dropTargetRow);
    fireEvent.drop(dropTargetRow);

    await user.click(screen.getByText('Save Changes'));

    await waitFor(() => {
      expect(apiClient.put).toHaveBeenCalled();
    });

    const formData = vi.mocked(apiClient.put).mock.calls[0]![1] as FormData;
    const participantsPayload = JSON.parse(formData.get('participants') as string);

    // All three participants are included, not just the literally-dragged P1
    expect(participantsPayload).toEqual([
      { participant_id: 'p2', position: 1 },
      { participant_id: 'p3', position: 2 },
      { participant_id: 'p1', position: 3 },
    ]);
  });

  it('excludes untouched participants below the highest explicitly-positioned index', async () => {
    const gameWithParticipants: GameSession = {
      ...mockGame,
      participants: [
        selfAddedParticipant('p1', 'P1', '2025-01-01T00:00:00Z'),
        selfAddedParticipant('p2', 'P2', '2025-01-01T00:01:00Z'),
        selfAddedParticipant('p3', 'P3', '2025-01-01T00:02:00Z'),
        selfAddedParticipant('p4', 'P4', '2025-01-01T00:03:00Z'),
      ],
    };

    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url.includes('/games/')) return Promise.resolve({ data: gameWithParticipants });
      if (url.includes('/channels')) return Promise.resolve({ data: mockChannels });
      if (url.includes('/roles')) return Promise.resolve({ data: [] });
      return Promise.reject(new Error('Unknown URL'));
    });
    vi.mocked(apiClient.put).mockResolvedValueOnce({ data: gameWithParticipants });

    const user = userEvent.setup();

    render(
      <AuthContext.Provider value={mockAuthContextValue}>
        <BrowserRouter>
          <EditGame />
        </BrowserRouter>
      </AuthContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue('@P1')).toBeInTheDocument();
    });

    // Drag P1 past P2 and P3, landing just above the untouched P4: [P2, P3, P1, P4]
    const draggedRow = screen.getByDisplayValue('@P1').closest('[draggable="true"]')!;
    const dropTargetRow = screen.getByDisplayValue('@P3').closest('[draggable="true"]')!;
    fireEvent.dragStart(draggedRow);
    fireEvent.dragOver(dropTargetRow);
    fireEvent.drop(dropTargetRow);

    await user.click(screen.getByText('Save Changes'));

    await waitFor(() => {
      expect(apiClient.put).toHaveBeenCalled();
    });

    const formData = vi.mocked(apiClient.put).mock.calls[0]![1] as FormData;
    const participantsPayload = JSON.parse(formData.get('participants') as string);

    expect(participantsPayload).toEqual([
      { participant_id: 'p2', position: 1 },
      { participant_id: 'p3', position: 2 },
      { participant_id: 'p1', position: 3 },
    ]);
    expect(
      participantsPayload.find((p: { participant_id?: string }) => p.participant_id === 'p4')
    ).toBeUndefined();
  });

  it('includes every participant through the new highest explicitly-positioned index after two non-contiguous moves', async () => {
    const gameWithParticipants: GameSession = {
      ...mockGame,
      participants: Array.from({ length: 8 }, (_, i) =>
        selfAddedParticipant(`p${i + 1}`, `P${i + 1}`, `2025-01-01T00:0${i}:00Z`)
      ),
    };

    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url.includes('/games/')) return Promise.resolve({ data: gameWithParticipants });
      if (url.includes('/channels')) return Promise.resolve({ data: mockChannels });
      if (url.includes('/roles')) return Promise.resolve({ data: [] });
      return Promise.reject(new Error('Unknown URL'));
    });
    vi.mocked(apiClient.put).mockResolvedValueOnce({ data: gameWithParticipants });

    const user = userEvent.setup();

    render(
      <AuthContext.Provider value={mockAuthContextValue}>
        <BrowserRouter>
          <EditGame />
        </BrowserRouter>
      </AuthContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue('@P1')).toBeInTheDocument();
    });

    // Move 1: drag P6 (index 5) to index 1 -> [P1, P6, P2, P3, P4, P5, P7, P8]
    fireEvent.dragStart(screen.getByDisplayValue('@P6').closest('[draggable="true"]')!);
    fireEvent.drop(screen.getByDisplayValue('@P2').closest('[draggable="true"]')!);

    // Move 2: drag P8 (now index 7) to index 4 -> [P1, P6, P2, P3, P8, P4, P5, P7]
    fireEvent.dragStart(screen.getByDisplayValue('@P8').closest('[draggable="true"]')!);
    fireEvent.drop(screen.getByDisplayValue('@P4').closest('[draggable="true"]')!);

    await user.click(screen.getByText('Save Changes'));

    await waitFor(() => {
      expect(apiClient.put).toHaveBeenCalled();
    });

    const formData = vi.mocked(apiClient.put).mock.calls[0]![1] as FormData;
    const participantsPayload = JSON.parse(formData.get('participants') as string);

    // Highest explicitly-positioned index is 4 (P8), so indices 0-4 are all included,
    // not just the two literally-dragged participants (P6, P8).
    expect(participantsPayload).toEqual([
      { participant_id: 'p1', position: 1 },
      { participant_id: 'p6', position: 2 },
      { participant_id: 'p2', position: 3 },
      { participant_id: 'p3', position: 4 },
      { participant_id: 'p8', position: 5 },
    ]);
  });

  it('pins the whole prefix above a newly-added participant to explicit positions', async () => {
    const gameWithParticipants: GameSession = {
      ...mockGame,
      participants: [
        selfAddedParticipant('p1', 'P1', '2025-01-01T00:00:00Z'),
        selfAddedParticipant('p2', 'P2', '2025-01-01T00:01:00Z'),
      ],
    };

    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url.includes('/games/')) return Promise.resolve({ data: gameWithParticipants });
      if (url.includes('/channels')) return Promise.resolve({ data: mockChannels });
      if (url.includes('/roles')) return Promise.resolve({ data: [] });
      return Promise.reject(new Error('Unknown URL'));
    });
    vi.mocked(apiClient.put).mockResolvedValueOnce({ data: gameWithParticipants });

    const user = userEvent.setup();

    render(
      <AuthContext.Provider value={mockAuthContextValue}>
        <BrowserRouter>
          <EditGame />
        </BrowserRouter>
      </AuthContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue('@P1')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Add Participant'));

    const mentionInputs = screen.getAllByPlaceholderText('@username or Discord user');
    const newParticipantInput = mentionInputs[mentionInputs.length - 1]!;
    fireEvent.change(newParticipantInput, { target: { value: '@NewGuy' } });

    await user.click(screen.getByText('Save Changes'));

    await waitFor(() => {
      expect(apiClient.put).toHaveBeenCalled();
    });

    const formData = vi.mocked(apiClient.put).mock.calls[0]![1] as FormData;
    const participantsPayload = JSON.parse(formData.get('participants') as string);

    // Harmless side effect: this freezes the already-correct FCFS order of P1/P2
    // into explicit position values, since addParticipant always appends at the
    // last index (the new highest explicitly-positioned index).
    expect(participantsPayload).toEqual([
      { participant_id: 'p1', position: 1 },
      { participant_id: 'p2', position: 2 },
      { mention: '@NewGuy', position: 3 },
    ]);
  });

  it('includes a dragged ROLE_MATCHED participant in the disturbed-prefix payload identically to SELF_ADDED', async () => {
    const roleMatchedParticipant = (id: string, name: string, position: number): Participant => ({
      id,
      game_session_id: 'game123',
      user_id: `user-${id}`,
      discord_id: id,
      display_name: name,
      joined_at: '2025-01-01T00:00:00Z',
      position_type: ParticipantType.ROLE_MATCHED,
      position,
    });

    const gameWithParticipants: GameSession = {
      ...mockGame,
      signup_method: 'ROLE_BASED',
      participants: [roleMatchedParticipant('r1', 'R1', 0), roleMatchedParticipant('r2', 'R2', 1)],
    };

    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url.includes('/games/')) return Promise.resolve({ data: gameWithParticipants });
      if (url.includes('/channels')) return Promise.resolve({ data: mockChannels });
      if (url.includes('/roles')) return Promise.resolve({ data: [] });
      return Promise.reject(new Error('Unknown URL'));
    });
    vi.mocked(apiClient.put).mockResolvedValueOnce({ data: gameWithParticipants });

    const user = userEvent.setup();

    render(
      <AuthContext.Provider value={mockAuthContextValue}>
        <BrowserRouter>
          <EditGame />
        </BrowserRouter>
      </AuthContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue('@R1')).toBeInTheDocument();
    });

    // Drag R1 below R2: [R2, R1]
    fireEvent.dragStart(screen.getByDisplayValue('@R1').closest('[draggable="true"]')!);
    fireEvent.drop(screen.getByDisplayValue('@R2').closest('[draggable="true"]')!);

    await user.click(screen.getByText('Save Changes'));

    await waitFor(() => {
      expect(apiClient.put).toHaveBeenCalled();
    });

    const formData = vi.mocked(apiClient.put).mock.calls[0]![1] as FormData;
    const participantsPayload = JSON.parse(formData.get('participants') as string);

    expect(participantsPayload).toEqual([
      { participant_id: 'r2', position: 1 },
      { participant_id: 'r1', position: 2 },
    ]);
  });
});

describe('EditGame - post_at scheduling field', () => {
  const mockGameWithPostAt: GameSession = {
    id: 'game456',
    title: 'Scheduled Game',
    description: 'A game with a pending announcement',
    signup_instructions: null,
    scheduled_at: '2099-12-01T18:00:00Z',
    post_at: '2099-11-20T09:00:00Z',
    where: null,
    max_players: 4,
    guild_id: 'guild123',
    guild_name: 'Test Server',
    channel_id: 'channel123',
    channel_name: 'Test Channel',
    message_id: null,
    host: {
      id: 'host-participant-id',
      game_session_id: 'game456',
      user_id: 'user123',
      discord_id: '123456789',
      display_name: 'Test Host',
      joined_at: '2025-01-01T00:00:00Z',
      position_type: ParticipantType.SELF_ADDED,
      position: 0,
    },
    reminder_minutes: [60],
    notify_role_ids: [],
    expected_duration_minutes: null,
    status: 'SCHEDULED',
    signup_method: 'SELF_SIGNUP',
    participant_count: 0,
    participants: [],
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockParams.gameId = 'game456';
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === '/api/v1/games/game456') {
        return Promise.resolve({ data: mockGameWithPostAt });
      }
      if (url === '/api/v1/guilds/guild123/channels') {
        return Promise.resolve({ data: [] });
      }
      if (url === '/api/v1/guilds/guild123/roles') {
        return Promise.resolve({ data: [] });
      }
      return Promise.resolve({ data: [] });
    });
  });

  afterEach(() => {
    mockParams.gameId = 'game123';
  });

  const renderWithAuth = () => {
    return render(
      <BrowserRouter>
        <AuthContext.Provider value={mockAuthContextValue}>
          <EditGame />
        </AuthContext.Provider>
      </BrowserRouter>
    );
  };

  it('pre-populates the "Schedule Posting (optional)" field from game.post_at', async () => {
    renderWithAuth();

    await waitFor(() => {
      expect(screen.getByRole('textbox', { name: /game title/i })).toBeInTheDocument();
    });

    expect(screen.getByText(/Leave empty to post immediately/)).toBeInTheDocument();
  });

  it('sends post_at in FormData when form is submitted with pre-populated post_at', async () => {
    vi.mocked(apiClient.put).mockResolvedValueOnce({ data: mockGameWithPostAt });
    const user = userEvent.setup();
    renderWithAuth();

    await waitFor(() => {
      expect(screen.getByDisplayValue('Scheduled Game')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Save Changes'));

    await waitFor(() => {
      expect(apiClient.put).toHaveBeenCalled();
    });

    const formData = vi.mocked(apiClient.put).mock.calls[0]![1] as FormData;
    expect(formData.get('post_at')).toBe('2099-11-20T09:00:00.000Z');
  });

  it('sends clear_post_at when "Post immediately" checkbox is checked before submit', async () => {
    vi.mocked(apiClient.put).mockResolvedValueOnce({ data: mockGameWithPostAt });
    const user = userEvent.setup();
    renderWithAuth();

    await waitFor(() => {
      expect(screen.getByRole('checkbox', { name: /Post immediately/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('checkbox', { name: /Post immediately/i }));
    await user.click(screen.getByText('Save Changes'));

    await waitFor(() => {
      expect(apiClient.put).toHaveBeenCalled();
    });

    const formData = vi.mocked(apiClient.put).mock.calls[0]![1] as FormData;
    expect(formData.get('clear_post_at')).toBe('true');
    expect(formData.get('post_at')).toBeNull();
  });
});

describe('EditGame - recur_rule field', () => {
  const mockGameWithRecurrence: GameSession = {
    id: 'game789',
    title: 'Recurring Game',
    description: 'A game that repeats weekly',
    signup_instructions: null,
    scheduled_at: '2099-12-01T18:00:00Z',
    where: null,
    max_players: 4,
    guild_id: 'guild123',
    guild_name: 'Test Server',
    channel_id: 'channel123',
    channel_name: 'Test Channel',
    message_id: null,
    host: {
      id: 'host-participant-id',
      game_session_id: 'game789',
      user_id: 'user123',
      discord_id: '123456789',
      display_name: 'Test Host',
      joined_at: '2025-01-01T00:00:00Z',
      position_type: ParticipantType.SELF_ADDED,
      position: 0,
    },
    reminder_minutes: [],
    notify_role_ids: [],
    expected_duration_minutes: null,
    status: 'SCHEDULED',
    signup_method: 'SELF_SIGNUP',
    participant_count: 0,
    participants: [],
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    recur_rule: 'FREQ=WEEKLY;INTERVAL=2;BYDAY=MO',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockParams.gameId = 'game789';
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === '/api/v1/games/game789') {
        return Promise.resolve({ data: mockGameWithRecurrence });
      }
      if (url === '/api/v1/guilds/guild123/channels') {
        return Promise.resolve({ data: [] });
      }
      if (url === '/api/v1/guilds/guild123/roles') {
        return Promise.resolve({ data: [] });
      }
      return Promise.resolve({ data: [] });
    });
  });

  afterEach(() => {
    mockParams.gameId = 'game123';
  });

  const renderWithAuth = () => {
    return render(
      <BrowserRouter>
        <AuthContext.Provider value={mockAuthContextValue}>
          <EditGame />
        </AuthContext.Provider>
      </BrowserRouter>
    );
  };

  it('sends recur_rule in FormData when game has recurrence', async () => {
    vi.mocked(apiClient.put).mockResolvedValueOnce({ data: mockGameWithRecurrence });
    const user = userEvent.setup();
    renderWithAuth();

    await waitFor(() => {
      expect(screen.getByDisplayValue('Recurring Game')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Save Changes'));

    await waitFor(() => {
      expect(apiClient.put).toHaveBeenCalled();
    });

    const formData = vi.mocked(apiClient.put).mock.calls[0]![1] as FormData;
    expect(formData.get('recur_rule')).toBe('FREQ=WEEKLY;INTERVAL=2;BYDAY=MO');
  });
});
