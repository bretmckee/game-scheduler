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

import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { About } from '../About';
import { apiClient } from '../../api/client';

vi.mock('../../api/client');

describe('About', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockVersionInfo = {
    service: 'api',
    git_version: '0.0.1.dev478+gd128f6a',
    api_version: '1.0.0',
    api_prefix: '/api/v1',
  };

  it('displays loading state initially', () => {
    vi.mocked(apiClient.get).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    render(<About />);

    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('fetches and displays version information', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockVersionInfo });

    render(<About />);

    await waitFor(() => {
      expect(
        screen.getByText(/Version 0\.0\.1\.dev478\+gd128f6a \(API 1\.0\.0\)/)
      ).toBeInTheDocument();
    });
  });

  it('calls /api/v1/version endpoint', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockVersionInfo });

    render(<About />);

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/version');
    });
  });

  it('displays error message when fetch fails', async () => {
    vi.mocked(apiClient.get).mockRejectedValue(new Error('Network error'));

    render(<About />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load version information')).toBeInTheDocument();
    });
  });

  it('displays copyright information', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockVersionInfo });

    render(<About />);

    await waitFor(() => {
      expect(screen.getByText(/Copyright © 2025-2026 Bret McKee/)).toBeInTheDocument();
    });

    expect(screen.getByText('bret.mckee@gmail.com')).toBeInTheDocument();
  });

  it('displays license information', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockVersionInfo });

    render(<About />);

    await waitFor(() => {
      expect(screen.getByText(/distributed under the MIT License/)).toBeInTheDocument();
    });

    expect(screen.getByText(/WITHOUT WARRANTY OF ANY KIND/)).toBeInTheDocument();
  });

  it('includes link to GitHub repository', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockVersionInfo });

    render(<About />);

    await waitFor(() => {
      const link = screen.getByRole('link', { name: /game-scheduler/ });
      expect(link).toHaveAttribute('href', 'https://github.com/game-scheduler/game-scheduler');
    });
  });

  it('includes link to license text', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockVersionInfo });

    render(<About />);

    await waitFor(() => {
      const link = screen.getByRole('link', { name: /opensource.org/ });
      expect(link).toHaveAttribute('href', 'https://opensource.org/license/mit/');
    });
  });

  it('displays version in correct format', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockVersionInfo });

    render(<About />);

    await waitFor(() => {
      expect(screen.getByText(/Version .+ \(API .+\)/)).toBeInTheDocument();
    });
  });

  it('shows warning alert on error but still displays other content', async () => {
    vi.mocked(apiClient.get).mockRejectedValue(new Error('Network error'));

    render(<About />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load version information')).toBeInTheDocument();
    });

    // Other content should still be visible
    expect(screen.getByText('Copyright')).toBeInTheDocument();
    expect(screen.getByText('License')).toBeInTheDocument();
  });

  it('handles empty version response gracefully', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        service: 'api',
        git_version: '',
        api_version: '',
        api_prefix: '/api/v1',
      },
    });

    render(<About />);

    await waitFor(() => {
      expect(screen.getByText('Version Information')).toBeInTheDocument();
    });

    // Should not crash with empty versions - checking for content containing "Version" and "API" in parentheses
    expect(
      screen.getByText((content, element) => {
        return element?.tagName === 'P' && /Version.*\(API.*\)/.test(content);
      })
    ).toBeInTheDocument();
  });

  it('displays page title', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockVersionInfo });

    render(<About />);

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: 'About Discord Game Scheduler' })
      ).toBeInTheDocument();
    });
  });

  it('displays all main sections', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockVersionInfo });

    render(<About />);

    await waitFor(() => {
      expect(screen.getByText('Version Information')).toBeInTheDocument();
    });

    expect(screen.getByText('Copyright')).toBeInTheDocument();
    expect(screen.getByText('License')).toBeInTheDocument();
  });
});
