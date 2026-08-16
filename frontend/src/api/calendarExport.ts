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

import { apiClient } from './client';

/**
 * Mints a short-lived, single-purpose token for downloading a game's
 * calendar export, then returns it. The caller navigates the browser to
 * `buildCalendarExportUrl(token)` to complete the download.
 */
export async function mintCalendarExportToken(gameId: string): Promise<string> {
  const response = await apiClient.post<{ token: string }>(`/api/v1/export/game/${gameId}/token`);
  return response.data.token;
}

/** Builds the public, unauthenticated `.ics` URL for a minted token. */
export function buildCalendarExportUrl(token: string): string {
  return `/api/v1/public/calendar/${token}.ics`;
}
