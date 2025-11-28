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
