# Copyright 2025-2026 Bret McKee
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


"""
Channel resolver service for validating and resolving #channel mentions.

Handles resolution of Discord channel mentions in game location text,
converting #channel-name references to clickable Discord links.
"""

import re

from shared.discord import client as discord_client_module


class ChannelResolver:
    """Resolves channel mentions in location text to Discord link format."""

    def __init__(self, discord_client: discord_client_module.DiscordAPIClient) -> None:
        """
        Initialize channel resolver.

        Args:
            discord_client: Discord API client for channel lookup
        """
        self.discord_client = discord_client
        # Excluding '#' from the captured name (Discord channel names can't contain '#')
        # keeps markdown headings ("## Section", "### Title") from being parsed as
        # channel-mention attempts.
        self._channel_mention_pattern = re.compile(r"(?<!<)#([^\s<>#]+)")
        self._discord_channel_url_pattern = re.compile(r"https://discord\.com/channels/(\d+)/(\d+)")
        self._snowflake_token_pattern = re.compile(r"<#(\d+)>")

    async def resolve_channel_mentions(
        self,
        location_text: str,
        guild_discord_id: str,
        field_label: str = "Location",
    ) -> tuple[str, list[dict]]:
        """
        Resolve channel mentions in location text.

        Args:
            location_text: User input text to scan (e.g., "Meet in #general") — may be
                the location field or any other free-text field (description, signup
                instructions) that allows channel mentions
            guild_discord_id: Discord guild ID
            field_label: Human-readable name of the field being resolved (e.g.
                "Description"), included in each error so the caller can tell which
                form field an error came from

        Returns:
            Tuple of (resolved_text, validation_errors):
            - resolved_text: Text with valid channels converted to <#id> format
            - validation_errors: List of error dicts for invalid/ambiguous channels
        """
        if not location_text:
            return location_text, []

        url_matches = list(self._discord_channel_url_pattern.finditer(location_text))
        hash_matches = list(self._channel_mention_pattern.finditer(location_text))
        snowflake_matches = list(self._snowflake_token_pattern.finditer(location_text))

        if not url_matches and not hash_matches and not snowflake_matches:
            return location_text, []

        channels = await self.discord_client.get_guild_channels(guild_discord_id)
        text_channels = [ch for ch in channels if ch.get("type") == 0]
        text_channel_ids = {ch["id"] for ch in text_channels}

        resolved, errors = self._resolve_url_mentions(
            location_text, url_matches, guild_discord_id, text_channel_ids, field_label
        )
        errors.extend(
            self._check_snowflake_tokens(snowflake_matches, text_channel_ids, field_label)
        )
        resolved, hash_errors = self._resolve_hash_mentions(
            resolved, hash_matches, text_channels, field_label
        )
        errors.extend(hash_errors)
        return resolved, errors

    def _resolve_url_mentions(
        self,
        resolved: str,
        url_matches: list[re.Match],
        guild_discord_id: str,
        text_channel_ids: set[str],
        field_label: str,
    ) -> tuple[str, list[dict]]:
        errors: list[dict] = []
        for url_match in url_matches:
            url_guild_id = url_match.group(1)
            url_channel_id = url_match.group(2)
            full_url = url_match.group(0)

            if url_guild_id != guild_discord_id:
                continue

            if url_channel_id not in text_channel_ids:
                errors.append({
                    "type": "not_found",
                    "field": field_label,
                    "input": full_url,
                    "reason": (
                        f"Your {field_label} contains a link to a channel that is not a "
                        "valid text channel in this server."
                    ),
                    "suggestions": [],
                })
            else:
                resolved = resolved.replace(full_url, f"<#{url_channel_id}>", 1)
        return resolved, errors

    def _resolve_single_hash_match(
        self,
        resolved: str,
        channel_name: str,
        matching_channels: list[dict],
        text_channels: list[dict],
        field_label: str,
    ) -> tuple[str, dict | None]:
        """Resolve one #channel_name match. Returns (updated_resolved, error_or_None)."""
        if len(matching_channels) == 1:
            resolved = resolved.replace(f"#{channel_name}", f"<#{matching_channels[0]['id']}>", 1)
            return resolved, None
        if len(matching_channels) > 1:
            error = {
                "type": "ambiguous",
                "field": field_label,
                "input": f"#{channel_name}",
                "reason": (
                    f"Your {field_label} contains '#{channel_name}', which matches "
                    "multiple channels in this server."
                ),
                "suggestions": [{"id": ch["id"], "name": ch["name"]} for ch in matching_channels],
            }
            return resolved, error
        if channel_name.isdigit():
            return resolved, None
        similar_channels = [
            ch for ch in text_channels if channel_name.lower() in ch["name"].lower()
        ][:5]
        # Every match reaching this branch is a single '#' immediately followed by
        # non-space text (a run of multiple '#' can never get here — see the pattern
        # comment in __init__), which is exactly what a forgotten-space markdown
        # heading looks like ("#heading" instead of "# heading"). Say so explicitly:
        # this exact confusion previously cost real debugging time.
        error = {
            "type": "not_found",
            "field": field_label,
            "input": f"#{channel_name}",
            "reason": (
                f"Your {field_label} contains '#{channel_name}', which is not a valid "
                "channel name in this server. If you meant this as a Markdown heading, "
                f"Discord requires a space after the '#' — use '# {channel_name}' instead "
                f"of '#{channel_name}'."
            ),
            "suggestions": [{"id": ch["id"], "name": ch["name"]} for ch in similar_channels],
        }
        return resolved, error

    def _resolve_hash_mentions(
        self,
        resolved: str,
        hash_matches: list[re.Match],
        text_channels: list[dict],
        field_label: str,
    ) -> tuple[str, list[dict]]:
        errors: list[dict] = []
        for match in hash_matches:
            channel_name = match.group(1)
            matching_channels = [
                ch for ch in text_channels if ch["name"].lower() == channel_name.lower()
            ]
            resolved, error = self._resolve_single_hash_match(
                resolved, channel_name, matching_channels, text_channels, field_label
            )
            if error is not None:
                errors.append(error)
        return resolved, errors

    def _check_snowflake_tokens(
        self,
        snowflake_matches: list[re.Match],
        text_channel_ids: set[str],
        field_label: str,
    ) -> list[dict]:
        """Validate <#id> tokens against the guild's text channel list."""
        errors: list[dict] = []
        for m in snowflake_matches:
            channel_id = m.group(1)
            if channel_id not in text_channel_ids:
                errors.append({
                    "type": "not_found",
                    "field": field_label,
                    "input": f"<#{channel_id}>",
                    "reason": (
                        f"Your {field_label} contains <#{channel_id}>, which is not a "
                        "valid text channel in this server."
                    ),
                    "suggestions": [],
                })
        return errors


_USER_MENTION_PATTERN = re.compile(r"<@(\d+)>")


def extract_user_mention_ids(text: str | None) -> set[str]:
    """Extract Discord snowflake IDs from all <@id> user mention tokens in text."""
    if not text:
        return set()
    return set(_USER_MENTION_PATTERN.findall(text))


def render_text_for_display(
    text: str | None,
    channels: list[dict],
    user_id_to_name: dict[str, str],
) -> str | None:
    """
    Replace <#id> and <@id> tokens in text with human-readable equivalents.

    Returns None if text is None. Returns text unchanged when no tokens match.
    Leaves tokens with unknown IDs unchanged.
    """
    if text is None:
        return None
    id_to_channel = {ch["id"]: ch["name"] for ch in channels}

    def _replace_channel(m: re.Match) -> str:
        name = id_to_channel.get(m.group(1))
        return f"#{name}" if name is not None else m.group(0)

    def _replace_user(m: re.Match) -> str:
        name = user_id_to_name.get(m.group(1))
        return f"@{name}" if name is not None else m.group(0)

    text = re.sub(r"<#(\d+)>", _replace_channel, text)
    return _USER_MENTION_PATTERN.sub(_replace_user, text)


def render_where_display(where: str | None, channels: list[dict]) -> str | None:
    """
    Replace `<#id>` tokens in a stored location string with `#name`.

    Returns None if `where` is None or contains no `<#id>` tokens (plain text).
    Leaves tokens with unknown IDs unchanged.
    """
    if where is None:
        return None
    pattern = re.compile(r"<#(\d+)>")
    if not pattern.search(where):
        return None
    id_to_name = {ch["id"]: ch["name"] for ch in channels}

    def _replace(m: re.Match) -> str:
        name = id_to_name.get(m.group(1))
        return f"#{name}" if name is not None else m.group(0)

    return pattern.sub(_replace, where)
