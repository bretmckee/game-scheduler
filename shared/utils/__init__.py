# Copyright 2025 Bret McKee (bret.mckee@gmail.com)
#
# This file is part of Game_Scheduler. (https://github.com/game-scheduler)
#
# Game_Scheduler is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Game_Scheduler is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
# Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.


"""Shared utility modules."""

from shared.utils.discord import (
    DiscordPermissions,
    build_oauth_url,
    format_channel_mention,
    format_discord_timestamp,
    format_role_mention,
    format_user_mention,
    has_permission,
    parse_mention,
)
from shared.utils.participant_sorting import sort_participants
from shared.utils.timezone import (
    from_iso_string,
    from_unix_timestamp,
    to_iso_string,
    to_unix_timestamp,
    to_utc,
    utcnow,
)

__all__ = [
    "DiscordPermissions",
    "build_oauth_url",
    "format_channel_mention",
    # Discord utilities
    "format_discord_timestamp",
    "format_role_mention",
    "format_user_mention",
    "from_iso_string",
    "from_unix_timestamp",
    "has_permission",
    "parse_mention",
    # Participant utilities
    "sort_participants",
    "to_iso_string",
    "to_unix_timestamp",
    "to_utc",
    # Timezone utilities
    "utcnow",
]
