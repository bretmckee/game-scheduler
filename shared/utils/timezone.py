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


"""Timezone handling utilities for UTC timestamps."""

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Get current UTC datetime with timezone info."""
    return datetime.now(UTC)


def to_utc(dt: datetime) -> datetime:
    """
    Convert datetime to UTC.

    Args:
        dt: Datetime object (naive or timezone-aware)

    Returns:
        Timezone-aware datetime in UTC
    """
    if dt.tzinfo is None:
        # Naive datetime, assume UTC
        return dt.replace(tzinfo=UTC)
    # Convert to UTC
    return dt.astimezone(UTC)


def to_unix_timestamp(dt: datetime) -> int:
    """
    Convert datetime to Unix timestamp (seconds since epoch).

    Args:
        dt: Datetime object

    Returns:
        Unix timestamp as integer
    """
    return int(to_utc(dt).timestamp())


def from_unix_timestamp(timestamp: int) -> datetime:
    """
    Convert Unix timestamp to UTC datetime.

    Args:
        timestamp: Unix timestamp (seconds since epoch)

    Returns:
        Timezone-aware datetime in UTC
    """
    return datetime.fromtimestamp(timestamp, tz=UTC)


def to_iso_string(dt: datetime) -> str:
    """
    Convert datetime to ISO 8601 string in UTC.

    Args:
        dt: Datetime object

    Returns:
        ISO 8601 formatted string (e.g., "2025-11-15T19:00:00Z")
    """
    return to_utc(dt).isoformat().replace("+00:00", "Z")


def from_iso_string(iso_str: str) -> datetime:
    """
    Parse ISO 8601 string to UTC datetime.

    Args:
        iso_str: ISO 8601 formatted string

    Returns:
        Timezone-aware datetime in UTC
    """
    # Handle 'Z' suffix
    if iso_str.endswith("Z"):
        iso_str = iso_str[:-1] + "+00:00"
    return datetime.fromisoformat(iso_str).astimezone(UTC)
