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
import { render, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router';
import { EditGame } from '../EditGame';
import { apiClient } from '../../api/client';
import { GameForm } from '../../components/GameForm';
import type { GameFormData } from '../../components/GameForm';
import { GameSession, Channel, ParticipantType } from '../../types';
import { AuthContext } from '../../contexts/AuthContext';

vi.mock('../../components/GameForm', () => ({ GameForm: vi.fn() }));

vi.mock('../../api/client');

const mockNavigate = vi.fn();

vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ gameId: 'game123' }),
  };
});

describe('EditGame - handleSaveAndArchive optional field branches', () => {
  const mockAuthContextValue = {
    user: { id: '1', user_uuid: 'uuid1', username: 'testuser' },
    loading: false,
    login: vi.fn(),
    logout: vi.fn(),
    refreshUser: vi.fn(),
  };

  const initialParticipant = {
    id: 'participant-to-remove',
    game_session_id: 'game123',
    user_id: 'user-x',
    discord_id: '999999',
    display_name: 'User X',
    joined_at: '2025-01-01T00:00:00Z',
    position_type: ParticipantType.HOST_ADDED,
    position: 1,
  };

  const baseGame: GameSession = {
    id: 'game123',
    title: 'Test Game',
    description: 'Test Description',
    signup_instructions: '',
    scheduled_at: '2025-12-01T18:00:00Z',
    where: null,
    max_players: 8,
    guild_id: 'guild123',
    guild_name: 'Test Server',
    channel_id: 'channel123',
    channel_name: 'Test Channel',
    message_id: null,
    host: {
      id: 'host-id',
      game_session_id: 'game123',
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
    status: 'IN_PROGRESS',
    signup_method: 'SELF_SIGNUP',
    participant_count: 1,
    participants: [initialParticipant],
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    rewards: 'A shiny badge',
    archive_channel_id: 'archive-ch-1',
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

  const baseFormData: GameFormData = {
    title: 'Test Game',
    description: 'Test Description',
    signupInstructions: '',
    scheduledAt: new Date('2025-12-01T18:00:00Z'),
    where: '',
    channelId: 'channel123',
    maxPlayers: '8',
    reminderMinutes: '',
    reminderMinutesArray: [],
    expectedDurationMinutes: null,
    participants: [],
    signupMethod: 'SELF_SIGNUP',
    thumbnailFile: null,
    imageFile: null,
    removeThumbnail: false,
    removeImage: false,
    rewards: 'A shiny badge',
    remindHostRewards: false,
  };

  function setupMocks() {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url.includes('/games/')) return Promise.resolve({ data: baseGame });
      if (url.includes('/channels')) return Promise.resolve({ data: mockChannels });
      if (url.includes('/roles')) return Promise.resolve({ data: [] });
      return Promise.reject(new Error('Unknown URL'));
    });
    vi.mocked(apiClient.put).mockResolvedValueOnce({ data: baseGame });
  }

  function renderEditGame() {
    return render(
      <AuthContext.Provider value={mockAuthContextValue}>
        <BrowserRouter>
          <EditGame />
        </BrowserRouter>
      </AuthContext.Provider>
    );
  }

  async function getOnSaveAndArchive(): Promise<(formData: GameFormData) => Promise<void>> {
    await waitFor(() => {
      expect(vi.mocked(GameForm).mock.calls.length).toBeGreaterThan(0);
    });
    const props = vi.mocked(GameForm).mock.calls.at(-1)?.[0] as any;
    expect(props.onSaveAndArchive).toBeDefined();
    return props.onSaveAndArchive;
  }

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(GameForm).mockReturnValue(null as any);
  });

  it('appends expected_duration_minutes when non-null', async () => {
    setupMocks();
    renderEditGame();
    const onSaveAndArchive = await getOnSaveAndArchive();

    await onSaveAndArchive({ ...baseFormData, expectedDurationMinutes: 90 });

    await waitFor(() => {
      const putFormData = vi.mocked(apiClient.put).mock.calls[0]?.[1] as FormData;
      expect(putFormData.get('expected_duration_minutes')).toBe('90');
    });
  });

  it('appends participants with real ids and removed_participant_ids', async () => {
    setupMocks();
    renderEditGame();
    const onSaveAndArchive = await getOnSaveAndArchive();

    await onSaveAndArchive({
      ...baseFormData,
      participants: [
        {
          id: 'real-participant-id',
          mention: '@Player (Player#1234)',
          preFillPosition: 1,
          isExplicitlyPositioned: true,
        },
      ],
    });

    await waitFor(() => {
      const putFormData = vi.mocked(apiClient.put).mock.calls[0]?.[1] as FormData;
      const participants = putFormData.get('participants') as string;
      expect(participants).toContain('real-participant-id');
      const removed = putFormData.get('removed_participant_ids') as string;
      expect(removed).toContain('participant-to-remove');
    });
  });

  it('uses mention field for temp-id participants', async () => {
    setupMocks();
    renderEditGame();
    const onSaveAndArchive = await getOnSaveAndArchive();

    await onSaveAndArchive({
      ...baseFormData,
      participants: [
        {
          id: 'temp-abc123',
          mention: '@NewPlayer',
          preFillPosition: 1,
          isExplicitlyPositioned: true,
        },
      ],
    });

    await waitFor(() => {
      const putFormData = vi.mocked(apiClient.put).mock.calls[0]?.[1] as FormData;
      const participants = putFormData.get('participants') as string;
      expect(participants).toContain('@NewPlayer');
      expect(participants).not.toContain('temp-');
    });
  });

  it('appends thumbnail and image files to FormData', async () => {
    setupMocks();
    renderEditGame();
    const onSaveAndArchive = await getOnSaveAndArchive();

    await onSaveAndArchive({
      ...baseFormData,
      thumbnailFile: new File(['thumb'], 'thumbnail.jpg', { type: 'image/jpeg' }),
      imageFile: new File(['img'], 'banner.jpg', { type: 'image/jpeg' }),
    });

    await waitFor(() => {
      const putFormData = vi.mocked(apiClient.put).mock.calls[0]?.[1] as FormData;
      expect(putFormData.get('thumbnail')).toBeInstanceOf(File);
      expect(putFormData.get('image')).toBeInstanceOf(File);
    });
  });

  it('appends remove_thumbnail and remove_image flags', async () => {
    setupMocks();
    renderEditGame();
    const onSaveAndArchive = await getOnSaveAndArchive();

    await onSaveAndArchive({ ...baseFormData, removeThumbnail: true, removeImage: true });

    await waitFor(() => {
      const putFormData = vi.mocked(apiClient.put).mock.calls[0]?.[1] as FormData;
      expect(putFormData.get('remove_thumbnail')).toBe('true');
      expect(putFormData.get('remove_image')).toBe('true');
    });
  });
});
