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
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { Layout } from '../Layout';
import { AuthContext } from '../../contexts/AuthContext';
import { CurrentUser } from '../../types';
import { vi } from 'vitest';

const mockUser: CurrentUser = {
  id: '123',
  user_uuid: 'uuid-123',
  username: 'testuser',
  discordId: '123',
};

const renderWithAuth = (user: CurrentUser | null) => {
  return render(
    <MemoryRouter>
      <AuthContext.Provider
        value={{
          user,
          loading: false,
          login: vi.fn(),
          logout: vi.fn(),
          refreshUser: vi.fn(),
        }}
      >
        <Layout />
      </AuthContext.Provider>
    </MemoryRouter>
  );
};

describe('Layout', () => {
  it('shows a Help link to the wiki when logged in', () => {
    renderWithAuth(mockUser);

    const link = screen.getByRole('link', { name: 'Help' });
    expect(link).toHaveAttribute('href', 'https://github.com/game-scheduler/game-scheduler/wiki');
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('shows a Help link to the wiki when logged out', () => {
    renderWithAuth(null);

    const link = screen.getByRole('link', { name: 'Help' });
    expect(link).toHaveAttribute('href', 'https://github.com/game-scheduler/game-scheduler/wiki');
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  });
});
