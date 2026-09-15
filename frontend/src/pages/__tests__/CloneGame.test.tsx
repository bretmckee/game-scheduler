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
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router';
import { CloneGame } from '../CloneGame';
import { apiClient } from '../../api/client';
import { AuthContext, type AuthContextType } from '../../contexts/AuthContext';
import { GameSession, ParticipantType, SignupMethod } from '../../types';

const mockNavigate = vi.fn();
const mockParams = { gameId: 'game123' };

vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => mockParams,
  };
});

vi.mock('../../api/client');

vi.mock('@mui/x-date-pickers/LocalizationProvider', () => ({
  LocalizationProvider: ({ children }: { children: unknown }) => children,
}));

vi.mock('@mui/x-date-pickers/DateTimePicker', () => ({
  DateTimePicker: ({
    label,
    value,
    onChange,
    slotProps,
  }: {
    label: string;
    value: Date | null;
    onChange: (v: Date | null) => void;
    slotProps?: { textField?: { required?: boolean; fullWidth?: boolean } };
  }) => (
    <input
      aria-label={label}
      required={slotProps?.textField?.required}
      value={value ? value.toISOString() : ''}
      onChange={(e) => onChange(e.target.value ? new Date(e.target.value) : null)}
    />
  ),
}));

vi.mock('@mui/x-date-pickers/AdapterDateFns', () => ({
  AdapterDateFns: class {},
}));

const mockAuthContextValue: AuthContextType = {
  user: { id: '1', user_uuid: 'uuid1', username: 'testuser' },
  loading: false,
  login: vi.fn(),
  logout: vi.fn(),
  refreshUser: vi.fn(),
};

describe('CloneGame', () => {
  const existingParticipant = {
    id: 'participant1',
    game_session_id: 'game123',
    user_id: 'user111',
    discord_id: '111',
    display_name: 'ExistingPlayer',
    joined_at: '2026-01-01T00:00:00Z',
    position_type: ParticipantType.SELF_ADDED,
    position: 0,
  };

  const mockGame: GameSession = {
    id: 'game123',
    title: 'Test Game To Clone',
    description: 'A game description',
    signup_instructions: null,
    scheduled_at: '2026-09-01T18:00:00Z',
    where: null,
    max_players: 4,
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
      joined_at: '2026-01-01T00:00:00Z',
      position_type: ParticipantType.SELF_ADDED,
      position: 0,
    },
    reminder_minutes: [],
    notify_role_ids: [],
    expected_duration_minutes: null,
    status: 'SCHEDULED',
    signup_method: SignupMethod.SELF_SIGNUP,
    participant_count: 1,
    participants: [existingParticipant],
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  };

  const mockGetImpl = (url: string) => {
    if (url.includes('/games/')) {
      return Promise.resolve({ data: mockGame });
    }
    if (url.includes('/config')) {
      return Promise.resolve({ status: 200, data: {} });
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderCloneGame = () =>
    render(
      <AuthContext.Provider value={mockAuthContextValue}>
        <BrowserRouter>
          <CloneGame />
        </BrowserRouter>
      </AuthContext.Provider>
    );

  // Task 8.1: written RED-first against the minimal Stage-1-shell stub (vitest 4 removed
  // the `.failing()` marker, see GameForm.errors-location.test.tsx for the same
  // convention), confirmed failing for real reasons (no carryover selects/pickers, no
  // Stage 2 mount), then implemented GREEN in Task 8.2 without changing any assertion
  // below.
  describe('two-stage GameForm-based screen (Task 8.1/8.2)', () => {
    it('renders Stage 1 carryover selects, deadline pickers, and a Continue button', async () => {
      vi.mocked(apiClient.get).mockImplementation(mockGetImpl);
      const user = userEvent.setup();
      renderCloneGame();

      await waitFor(() => {
        expect(screen.getByText('Test Game To Clone')).toBeInTheDocument();
      });

      expect(screen.getByLabelText('Player Carryover')).toBeInTheDocument();
      expect(screen.getByLabelText('Waitlist Carryover')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Continue' })).toBeInTheDocument();

      const playerSelect = screen.getByLabelText('Player Carryover');
      await user.click(playerSelect);
      const option = await screen.findByRole('option', { name: /confirmation deadline/i });
      await user.click(option);

      expect(screen.getByLabelText('Player Confirmation Deadline')).toBeInTheDocument();
    });

    it('clicking Continue reveals GameForm fields pre-populated from the source game', async () => {
      vi.mocked(apiClient.get).mockImplementation(mockGetImpl);
      const user = userEvent.setup();
      renderCloneGame();

      await waitFor(() => {
        expect(screen.getByText('Test Game To Clone')).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: 'Continue' }));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Create Game' })).toBeInTheDocument();
      });
      expect(screen.getByDisplayValue('Test Game To Clone')).toBeInTheDocument();
      expect(screen.getByDisplayValue('A game description')).toBeInTheDocument();
    });

    it('does not pre-populate the participant editor when playerCarryover is NO (default)', async () => {
      vi.mocked(apiClient.get).mockImplementation(mockGetImpl);
      const user = userEvent.setup();
      renderCloneGame();

      await waitFor(() => {
        expect(screen.getByText('Test Game To Clone')).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: 'Continue' }));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Create Game' })).toBeInTheDocument();
      });
      expect(screen.queryByDisplayValue('@ExistingPlayer')).not.toBeInTheDocument();
    });

    it('pre-populates the participant editor when playerCarryover is YES before Continue', async () => {
      vi.mocked(apiClient.get).mockImplementation(mockGetImpl);
      const user = userEvent.setup();
      renderCloneGame();

      await waitFor(() => {
        expect(screen.getByText('Test Game To Clone')).toBeInTheDocument();
      });

      const playerSelect = screen.getByLabelText('Player Carryover');
      await user.click(playerSelect);
      const option = await screen.findByRole('option', { name: /carry over existing players/i });
      await user.click(option);

      await user.click(screen.getByRole('button', { name: 'Continue' }));

      await waitFor(() => {
        expect(screen.getByDisplayValue('@ExistingPlayer')).toBeInTheDocument();
      });
    });

    it('toggling playerCarryover after Stage 2 has mounted does not clear host-edited title text', async () => {
      vi.mocked(apiClient.get).mockImplementation(mockGetImpl);
      const user = userEvent.setup();
      renderCloneGame();

      await waitFor(() => {
        expect(screen.getByText('Test Game To Clone')).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: 'Continue' }));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Create Game' })).toBeInTheDocument();
      });

      // MUI's required-field label renders a literal " *" text node, so match loosely.
      const titleInput = await screen.findByLabelText(/^Game Title/);
      await user.clear(titleInput);
      await user.type(titleInput, 'Edited Title');
      expect(screen.getByDisplayValue('Edited Title')).toBeInTheDocument();

      const playerSelect = screen.getByLabelText('Player Carryover');
      await user.click(playerSelect);
      const option = await screen.findByRole('option', { name: /carry over existing players/i });
      await user.click(option);

      expect(screen.getByDisplayValue('Edited Title')).toBeInTheDocument();
    });
  });

  // Task 8.3: tests for behavior already implemented by Task 8.2 (no RED phase needed --
  // see .github/instructions/test-driven-development.instructions.md's "Writing Tests for
  // Already-Correct Code" section).
  describe('edge cases (Task 8.3)', () => {
    it('strips confirmed_participants/waitlist_participants -- not participants -- for a HOST_SELECTED_WITH_WAITLIST source game', async () => {
      const confirmedParticipant = {
        id: 'confirmed1',
        game_session_id: 'game123',
        user_id: 'user222',
        discord_id: '222',
        display_name: 'ConfirmedPlayer',
        joined_at: '2026-01-01T00:00:00Z',
        position_type: ParticipantType.SELF_ADDED,
        position: 0,
      };
      const waitlistedParticipant = {
        id: 'waitlisted1',
        game_session_id: 'game123',
        user_id: 'user333',
        discord_id: '333',
        display_name: 'WaitlistedPlayer',
        joined_at: '2026-01-01T00:00:00Z',
        position_type: ParticipantType.SELF_ADDED,
        position: 1,
      };
      const waitlistGame: GameSession = {
        ...mockGame,
        signup_method: SignupMethod.HOST_SELECTED_WITH_WAITLIST,
        max_players: 1,
        participants: [],
        confirmed_participants: [confirmedParticipant],
        waitlist_participants: [waitlistedParticipant],
      };
      vi.mocked(apiClient.get).mockImplementation((url: string) => {
        if (url.includes('/games/')) return Promise.resolve({ data: waitlistGame });
        if (url.includes('/config')) return Promise.resolve({ status: 200, data: {} });
        return Promise.reject(new Error(`Unexpected URL: ${url}`));
      });
      const user = userEvent.setup();
      renderCloneGame();

      await waitFor(() => {
        expect(screen.getByText('Test Game To Clone')).toBeInTheDocument();
      });

      // Player carryover YES (keep confirmed); waitlist carryover stays NO (drop waitlisted).
      const playerSelect = screen.getByLabelText('Player Carryover');
      await user.click(playerSelect);
      const option = await screen.findByRole('option', { name: /carry over existing players/i });
      await user.click(option);

      await user.click(screen.getByRole('button', { name: 'Continue' }));

      await waitFor(() => {
        expect(screen.getByDisplayValue('@ConfirmedPlayer')).toBeInTheDocument();
      });
      expect(screen.queryByDisplayValue('@WaitlistedPlayer')).not.toBeInTheDocument();
    });

    it('does not crash and leaves file inputs empty when the source game has a thumbnail/banner', async () => {
      const imageGame: GameSession = {
        ...mockGame,
        has_thumbnail: true,
        has_image: true,
      };
      vi.mocked(apiClient.get).mockImplementation((url: string) => {
        if (url.includes('/games/')) return Promise.resolve({ data: imageGame });
        if (url.includes('/config')) return Promise.resolve({ status: 200, data: {} });
        return Promise.reject(new Error(`Unexpected URL: ${url}`));
      });
      const user = userEvent.setup();
      renderCloneGame();

      await waitFor(() => {
        expect(screen.getByText('Test Game To Clone')).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: 'Continue' }));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Create Game' })).toBeInTheDocument();
      });

      // Images carry over by reference server-side (Phase 6); GameForm's file inputs stay
      // empty/optional so the host can still attach a genuinely new file (create mode
      // never shows the "Remove Thumbnail/Banner" buttons, which are edit-mode-only).
      expect(screen.getByRole('button', { name: 'Choose Thumbnail' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Choose Banner' })).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Remove Thumbnail' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Remove Banner' })).not.toBeInTheDocument();
    });

    it('shows a loading spinner while fetching the source game', () => {
      vi.mocked(apiClient.get).mockImplementation(() => new Promise(() => {}));
      renderCloneGame();
      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });

    it('shows an error and a Back button when the fetch fails', async () => {
      const user = userEvent.setup();
      vi.mocked(apiClient.get).mockRejectedValueOnce(new Error('Network error'));
      renderCloneGame();

      await waitFor(() => {
        expect(screen.getByText('Failed to load game. Please try again.')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Back'));
      expect(mockNavigate).toHaveBeenCalledWith(-1);
    });

    it('blocks Continue with an error when the player deadline is missing', async () => {
      vi.mocked(apiClient.get).mockImplementation(mockGetImpl);
      const user = userEvent.setup();
      renderCloneGame();

      await waitFor(() => {
        expect(screen.getByText('Test Game To Clone')).toBeInTheDocument();
      });

      const playerSelect = screen.getByLabelText('Player Carryover');
      await user.click(playerSelect);
      const option = await screen.findByRole('option', { name: /confirmation deadline/i });
      await user.click(option);

      await user.click(screen.getByRole('button', { name: 'Continue' }));

      await waitFor(() => {
        expect(screen.getByText(/player deadline is required/i)).toBeInTheDocument();
      });
      expect(screen.queryByRole('button', { name: 'Create Game' })).not.toBeInTheDocument();
    });

    it('blocks Continue with an error when the player deadline is in the past', async () => {
      vi.mocked(apiClient.get).mockImplementation(mockGetImpl);
      const user = userEvent.setup();
      renderCloneGame();

      await waitFor(() => {
        expect(screen.getByText('Test Game To Clone')).toBeInTheDocument();
      });

      const playerSelect = screen.getByLabelText('Player Carryover');
      await user.click(playerSelect);
      const option = await screen.findByRole('option', { name: /confirmation deadline/i });
      await user.click(option);

      const deadlineInput = await screen.findByLabelText('Player Confirmation Deadline');
      const pastDate = new Date(Date.now() - 3600000);
      fireEvent.change(deadlineInput, { target: { value: pastDate.toISOString() } });

      await user.click(screen.getByRole('button', { name: 'Continue' }));

      await waitFor(() => {
        expect(screen.getByText(/player deadline must be in the future/i)).toBeInTheDocument();
      });
      expect(screen.queryByRole('button', { name: 'Create Game' })).not.toBeInTheDocument();
    });

    it('blocks Continue with an error when the waitlist deadline is missing', async () => {
      vi.mocked(apiClient.get).mockImplementation(mockGetImpl);
      const user = userEvent.setup();
      renderCloneGame();

      await waitFor(() => {
        expect(screen.getByText('Test Game To Clone')).toBeInTheDocument();
      });

      const waitlistSelect = screen.getByLabelText('Waitlist Carryover');
      await user.click(waitlistSelect);
      const option = await screen.findByRole('option', { name: /confirmation deadline/i });
      await user.click(option);

      await user.click(screen.getByRole('button', { name: 'Continue' }));

      await waitFor(() => {
        expect(screen.getByText(/waitlist deadline is required/i)).toBeInTheDocument();
      });
      expect(screen.queryByRole('button', { name: 'Create Game' })).not.toBeInTheDocument();
    });

    it('blocks Continue with an error when the waitlist deadline is in the past', async () => {
      vi.mocked(apiClient.get).mockImplementation(mockGetImpl);
      const user = userEvent.setup();
      renderCloneGame();

      await waitFor(() => {
        expect(screen.getByText('Test Game To Clone')).toBeInTheDocument();
      });

      const waitlistSelect = screen.getByLabelText('Waitlist Carryover');
      await user.click(waitlistSelect);
      const option = await screen.findByRole('option', { name: /confirmation deadline/i });
      await user.click(option);

      const deadlineInput = await screen.findByLabelText('Waitlist Confirmation Deadline');
      const pastDate = new Date(Date.now() - 3600000);
      fireEvent.change(deadlineInput, { target: { value: pastDate.toISOString() } });

      await user.click(screen.getByRole('button', { name: 'Continue' }));

      await waitFor(() => {
        expect(screen.getByText(/waitlist deadline must be in the future/i)).toBeInTheDocument();
      });
      expect(screen.queryByRole('button', { name: 'Create Game' })).not.toBeInTheDocument();
    });

    it('clicking Cancel in Stage 2 navigates back to the source game', async () => {
      vi.mocked(apiClient.get).mockImplementation(mockGetImpl);
      const user = userEvent.setup();
      renderCloneGame();

      await waitFor(() => {
        expect(screen.getByText('Test Game To Clone')).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: 'Continue' }));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Create Game' })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: 'Cancel' }));
      expect(mockNavigate).toHaveBeenCalledWith('/games/game123');
    });

    it('surfaces an error when Stage 2 is submitted (clone submission not yet wired)', async () => {
      vi.mocked(apiClient.get).mockImplementation(mockGetImpl);
      const user = userEvent.setup();
      renderCloneGame();

      await waitFor(() => {
        expect(screen.getByText('Test Game To Clone')).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: 'Continue' }));

      const submitButton = await screen.findByRole('button', { name: 'Create Game' });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Failed to submit. Please try again.')).toBeInTheDocument();
      });
    });
  });
});
