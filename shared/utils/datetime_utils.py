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


"""Datetime utility functions for consistent formatting."""

from datetime import UTC, datetime


def format_datetime_as_utc(dt: datetime) -> str:
    """
    Format a naive datetime as UTC ISO8601 with 'Z' suffix.

    This function assumes the input datetime is in UTC and explicitly marks it
    as such for serialization. It converts Python's "+00:00" timezone format
    to the more standard "Z" (Zulu time) suffix.

    Args:
        dt: A naive datetime object assumed to be in UTC timezone

    Returns:
        ISO8601 formatted string with 'Z' suffix (e.g., "2025-12-20T15:30:00Z")

    Examples:
        >>> dt = datetime(2025, 12, 20, 15, 30, 0)
        >>> format_datetime_as_utc(dt)
        '2025-12-20T15:30:00Z'

        >>> # Midnight case (no offset applied)
        >>> dt = datetime(2025, 11, 27, 0, 15, 0)
        >>> format_datetime_as_utc(dt)
        '2025-11-27T00:15:00Z'
    """
    return dt.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")
