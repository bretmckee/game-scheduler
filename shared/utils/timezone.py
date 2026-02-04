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
