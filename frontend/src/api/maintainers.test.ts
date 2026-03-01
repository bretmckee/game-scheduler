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
import { apiClient } from './client';
import { toggleMaintainerMode, refreshMaintainers } from './maintainers';

vi.mock('./client');

describe('maintainers API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('toggleMaintainerMode', () => {
    it('calls POST /api/v1/maintainers/toggle', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: {} });
      await toggleMaintainerMode();
      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/maintainers/toggle');
    });

    it('resolves on 200 response', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: {} });
      await expect(toggleMaintainerMode()).resolves.toBeUndefined();
    });

    it('rejects on 4xx response', async () => {
      vi.mocked(apiClient.post).mockRejectedValue({ response: { status: 403 } });
      await expect(toggleMaintainerMode()).rejects.toMatchObject({ response: { status: 403 } });
    });
  });

  describe('refreshMaintainers', () => {
    it('calls POST /api/v1/maintainers/refresh', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: {} });
      await refreshMaintainers();
      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/maintainers/refresh');
    });

    it('resolves on 200 response', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: {} });
      await expect(refreshMaintainers()).resolves.toBeUndefined();
    });

    it('rejects on 4xx response', async () => {
      vi.mocked(apiClient.post).mockRejectedValue({ response: { status: 403 } });
      await expect(refreshMaintainers()).rejects.toMatchObject({ response: { status: 403 } });
    });
  });
});
