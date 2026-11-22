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

import { describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { ParticipantList } from '../ParticipantList';
import { Participant, ParticipantType } from '../../types';

const makeParticipant = (overrides: Partial<Participant>): Participant => ({
  id: 'p1',
  game_session_id: 'game-1',
  user_id: null,
  discord_id: '111',
  display_name: 'Kallisti',
  joined_at: '2025-01-01T00:00:00Z',
  position_type: ParticipantType.SELF_ADDED,
  position: 0,
  ...overrides,
});

describe('ParticipantList', () => {
  it('renders a confirmed Discord member as an @label member chip', () => {
    render(
      <ParticipantList
        confirmedParticipants={[makeParticipant({})]}
        waitlistParticipants={[]}
        maxPlayers={1}
      />
    );

    expect(screen.getByTestId('member-chip')).toHaveTextContent('@Kallisti');
  });

  it('renders a departed confirmed member as the unknown-member chip', () => {
    render(
      <ParticipantList
        confirmedParticipants={[makeParticipant({ discord_id: '222', display_name: null })]}
        waitlistParticipants={[]}
        maxPlayers={1}
      />
    );

    expect(screen.getByTestId('unknown-member-chip')).toBeInTheDocument();
    expect(screen.queryByText(/<@222>/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Unknown User/)).not.toBeInTheDocument();
  });

  it('renders a departed waitlisted member as the unknown-member chip', () => {
    render(
      <ParticipantList
        confirmedParticipants={[]}
        waitlistParticipants={[makeParticipant({ discord_id: '222', display_name: null })]}
        maxPlayers={0}
      />
    );

    const waitlistItem = screen.getByText('Waitlist').closest('li')!;
    expect(within(waitlistItem).getByTestId('unknown-member-chip')).toBeInTheDocument();
    expect(screen.queryByText(/<@222>/)).not.toBeInTheDocument();
  });

  it('renders a placeholder as plain text without a member chip', () => {
    render(
      <ParticipantList
        confirmedParticipants={[
          makeParticipant({
            discord_id: null,
            display_name: 'Bob from work',
            position_type: ParticipantType.HOST_ADDED,
          }),
        ]}
        waitlistParticipants={[]}
        maxPlayers={1}
      />
    );

    expect(screen.getByText('Bob from work')).toBeInTheDocument();
    expect(screen.queryByTestId('member-chip')).not.toBeInTheDocument();
    expect(screen.queryByTestId('unknown-member-chip')).not.toBeInTheDocument();
  });
});
