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

    // Renamed from the Phase 8 stub-era "clone submission not yet wired" test now that
    // Phase 9 wires a real submit handler; the assertion is unchanged -- a generic
    // (non-invalid_mentions) submission failure still surfaces via GameForm's own
    // fallback error banner (Task 9.3 refactor).
    it('shows GameForm generic error banner when the clone request fails for an unhandled reason', async () => {
      vi.mocked(apiClient.get).mockImplementation(mockGetImpl);
      vi.mocked(apiClient.post).mockRejectedValueOnce(new Error('Network error'));
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
      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });

  // Task 9.1: written first against Task 8's `throw new Error('Clone submission not yet
  // implemented')` stub (vitest 4 has no `.failing()` marker -- see CloneGame.test.tsx's
  // own Task 8.1 note and GameForm.errors-location.test.tsx for the established
  // convention), run and confirmed failing for a real reason (handleSubmit unconditionally
  // threw, so apiClient.post was never called and the payload assertions below never ran),
  // then Task 9.2 implemented the real handler without changing any assertion, and the
  // tests were re-run and confirmed passing.
  describe('submit handler (Task 9.1/9.2/9.3)', () => {
    const richGame: GameSession = {
      ...mockGame,
      where: 'The Tavern',
      signup_instructions: 'Bring your own dice',
      // 120 (a DurationSelector preset) rather than a custom value -- a non-preset value
      // mounts DurationSelector in "custom" mode, which has a pre-existing infinite
      // render loop bug (an unmemoized onChange prop feeding a useCallback/useEffect
      // pair) unrelated to this phase; see the changes-tracking file's Phase 9 note.
      expected_duration_minutes: 120,
      recur_rule: 'FREQ=WEEKLY',
      remind_host_rewards: true,
      reminders_as_dms: false,
      reminder_minutes: [15, 60],
    };

    const richGetImpl = (url: string) => {
      if (url.includes('/games/')) return Promise.resolve({ data: richGame });
      if (url.includes('/config')) return Promise.resolve({ status: 200, data: {} });
      return Promise.reject(new Error(`Unexpected URL: ${url}`));
    };

    it('posts a multipart clone request mapping every GameFormData field plus Stage 1 carryover/deadline state, and navigates to the new game on success', async () => {
      vi.mocked(apiClient.get).mockImplementation(richGetImpl);
      vi.mocked(apiClient.post).mockResolvedValue({ data: { id: 'cloned-game-id' } });
      const user = userEvent.setup();
      renderCloneGame();

      await waitFor(() => {
        expect(screen.getByText('Test Game To Clone')).toBeInTheDocument();
      });

      // Player carryover: YES_WITH_DEADLINE with a future deadline.
      const playerSelect = screen.getByLabelText('Player Carryover');
      await user.click(playerSelect);
      await user.click(await screen.findByRole('option', { name: /confirmation deadline/i }));
      const playerDeadlineInput = await screen.findByLabelText('Player Confirmation Deadline');
      const playerDeadlineDate = new Date(Date.now() + 3600_000);
      fireEvent.change(playerDeadlineInput, {
        target: { value: playerDeadlineDate.toISOString() },
      });

      // Waitlist carryover: YES (no deadline) -- exercises the sibling carryover field
      // independently of the player deadline set above.
      const waitlistSelect = screen.getByLabelText('Waitlist Carryover');
      await user.click(waitlistSelect);
      await user.click(await screen.findByRole('option', { name: /carry over existing players/i }));

      await user.click(screen.getByRole('button', { name: 'Continue' }));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Create Game' })).toBeInTheDocument();
      });

      // Edit a couple of GameForm fields and attach a new thumbnail to confirm live host
      // edits -- not just carried-over defaults -- round-trip into the outgoing payload.
      const titleInput = await screen.findByLabelText(/^Game Title/);
      await user.clear(titleInput);
      await user.type(titleInput, 'Cloned Title');

      const hostInput = screen.getByLabelText('Game Host');
      await user.type(hostInput, '@newhost');

      const thumbnailInput = screen.getByLabelText(/thumbnail/i) as HTMLInputElement;
      const thumbnailFile = new File(['data'], 'thumb.png', { type: 'image/png' });
      await user.upload(thumbnailInput, thumbnailFile);

      await user.click(screen.getByRole('button', { name: 'Create Game' }));

      await waitFor(() => {
        expect(apiClient.post).toHaveBeenCalled();
      });
      expect(mockNavigate).toHaveBeenCalledWith('/games/cloned-game-id');

      const postCall = vi.mocked(apiClient.post).mock.calls[0];
      expect(postCall).toBeDefined();
      const [url, body, config] = postCall!;
      expect(url).toBe('/api/v1/games/game123/clone');
      expect(config).toEqual({ headers: { 'Content-Type': 'multipart/form-data' } });

      const formData = body as FormData;
      expect(formData.get('scheduled_at')).toBeTruthy();
      expect(formData.get('title')).toBe('Cloned Title');
      expect(formData.get('description')).toBe('A game description');
      expect(formData.get('where')).toBe('The Tavern');
      expect(formData.get('signup_instructions')).toBe('Bring your own dice');
      expect(formData.get('max_players')).toBe('4');
      expect(formData.get('expected_duration_minutes')).toBe('120');
      expect(formData.get('signup_method')).toBe('SELF_SIGNUP');
      expect(formData.get('reminder_minutes')).toBe(JSON.stringify([15, 60]));
      expect(formData.get('participants')).toBe(JSON.stringify(['@ExistingPlayer']));
      expect(formData.get('host')).toBe('@newhost');
      expect(formData.get('remind_host_rewards')).toBe('true');
      expect(formData.get('reminders_as_dms')).toBe('false');
      expect(formData.get('recur_rule')).toBe('FREQ=WEEKLY');
      expect(formData.get('player_carryover')).toBe('YES_WITH_DEADLINE');
      expect(formData.get('waitlist_carryover')).toBe('YES');
      expect(formData.get('player_deadline')).toBe(playerDeadlineDate.toISOString());
      expect(formData.get('waitlist_deadline')).toBeNull();

      const thumbnail = formData.get('thumbnail') as File;
      expect(thumbnail).toBeInstanceOf(File);
      expect(thumbnail.name).toBe('thumb.png');
    });

    it('omits optional text fields and the host override, and sends an empty participants list, when nothing was carried over or edited', async () => {
      vi.mocked(apiClient.get).mockImplementation(mockGetImpl);
      vi.mocked(apiClient.post).mockResolvedValue({ data: { id: 'cloned-game-id-2' } });
      const user = userEvent.setup();
      renderCloneGame();

      await waitFor(() => {
        expect(screen.getByText('Test Game To Clone')).toBeInTheDocument();
      });

      // Default Stage 1 state: both carryovers NO.
      await user.click(screen.getByRole('button', { name: 'Continue' }));
      await user.click(await screen.findByRole('button', { name: 'Create Game' }));

      await waitFor(() => {
        expect(apiClient.post).toHaveBeenCalled();
      });

      const formData = vi.mocked(apiClient.post).mock.calls[0]![1] as FormData;
      expect(formData.get('participants')).toBe('[]');
      expect(formData.get('player_carryover')).toBe('NO');
      expect(formData.get('waitlist_carryover')).toBe('NO');
      expect(formData.get('player_deadline')).toBeNull();
      expect(formData.get('waitlist_deadline')).toBeNull();
      expect(formData.get('host')).toBeNull();
      expect(formData.get('thumbnail')).toBeNull();
      expect(formData.get('image')).toBeNull();
      expect(formData.get('post_at')).toBeNull();
    });

    it('populates GameForm validation state and does not navigate when the clone request returns an invalid_mentions 422 response', async () => {
      vi.mocked(apiClient.get).mockImplementation(mockGetImpl);
      vi.mocked(apiClient.post).mockRejectedValueOnce({
        response: {
          status: 422,
          data: {
            detail: {
              error: 'invalid_mentions',
              message: 'Some mentions could not be resolved',
              invalid_mentions: [
                {
                  input: '@unknownuser',
                  reason: "User '@unknownuser' not found",
                  suggestions: [],
                },
                {
                  type: 'not_found',
                  input: '#nonexistent',
                  reason: "Channel '#nonexistent' not found",
                  suggestions: [],
                },
              ],
              valid_participants: [],
            },
          },
        },
      });
      const user = userEvent.setup();
      renderCloneGame();

      await waitFor(() => {
        expect(screen.getByText('Test Game To Clone')).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: 'Continue' }));
      await user.click(await screen.findByRole('button', { name: 'Create Game' }));

      await waitFor(() => {
        expect(screen.getByText('Could not resolve some @mentions')).toBeInTheDocument();
      });
      expect(screen.getByText(/User '@unknownuser' not found/)).toBeInTheDocument();
      expect(screen.getByText('Invalid channel reference')).toBeInTheDocument();
      expect(screen.getByText(/Channel '#nonexistent' not found/)).toBeInTheDocument();
      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });
});
