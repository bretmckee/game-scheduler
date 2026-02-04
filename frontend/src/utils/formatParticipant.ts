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

/**
 * Formats a participant's display for UI presentation.
 *
 * @param displayName - The participant's display name (nullable)
 * @param discordId - The participant's Discord ID (nullable/optional)
 * @returns Formatted string for display
 *
 * Rules:
 * - Discord users (have discord_id): Prepend @ to display name, or use <@id> if no name
 * - Placeholders (no discord_id): Return as-is without @
 */
export const formatParticipantDisplay = (
  displayName: string | null,
  discordId?: string | null
): string => {
  // If we have a discord_id, this is a Discord user
  if (discordId) {
    // Prefer display name with @ prefix if available
    if (displayName) {
      return displayName.startsWith('@') ? displayName : `@${displayName}`;
    }
    // Fallback to Discord ID format if no display name
    return `<@${discordId}>`;
  }

  // No discord_id means this is a placeholder - return display_name as-is without @
  if (displayName) {
    return displayName;
  }

  return 'Unknown User';
};
