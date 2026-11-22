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

/**
 * A reference to a Discord guild member for display purposes.
 *
 * `label` is the member's live display name; `null` means the member is no
 * longer in the server. Labels are never persisted — they come from the API's
 * live member projection on every read.
 */
export interface MemberRef {
  id: string;
  label: string | null;
}

/**
 * Adapt a participant/host record to a `MemberRef`.
 *
 * Returns `null` for placeholders (no `discord_id`), which render as plain text.
 */
export function toMemberRef(p: {
  discord_id: string | null;
  display_name: string | null;
}): MemberRef | null {
  if (!p.discord_id) {
    return null;
  }
  return { id: p.discord_id, label: p.display_name };
}
