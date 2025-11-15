"""
Timezone handling utilities for UTC storage and display.

All timestamps are stored in UTC in the database and converted for display
by the client (Discord or web browser).
"""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Get current UTC datetime with timezone info."""
    return datetime.now(UTC)


def ensure_utc(dt: datetime) -> datetime:
    """
    Ensure datetime has UTC timezone.
    
    Args:
        dt: Datetime object (naive or timezone-aware)
        
    Returns:
        Datetime with UTC timezone
        
    Raises:
        ValueError: If datetime has non-UTC timezone
    """
    if dt.tzinfo is None:
        # Assume naive datetime is already UTC
        return dt.replace(tzinfo=UTC)
    elif dt.tzinfo == UTC:
        return dt
    else:
        raise ValueError(f"Datetime must be UTC, got {dt.tzinfo}")


def to_unix_timestamp(dt: datetime) -> int:
    """
    Convert UTC datetime to Unix timestamp for Discord.
    
    Discord timestamp format: <t:unix_timestamp:F>
    
    Args:
        dt: UTC datetime
        
    Returns:
        Unix timestamp (seconds since epoch)
    """
    dt_utc = ensure_utc(dt)
    return int(dt_utc.timestamp())


def from_unix_timestamp(timestamp: int | float) -> datetime:
    """
    Convert Unix timestamp to UTC datetime.
    
    Args:
        timestamp: Unix timestamp (seconds since epoch)
        
    Returns:
        UTC datetime with timezone info
    """
    return datetime.fromtimestamp(timestamp, tz=UTC)


def format_discord_timestamp(dt: datetime, format_code: str = "F") -> str:
    """
    Format datetime as Discord timestamp string.
    
    Discord automatically converts to user's local timezone.
    
    Args:
        dt: UTC datetime
        format_code: Discord format code
            - F: Full date/time (default)
            - f: Short date/time  
            - D: Date only
            - T: Time only
            - R: Relative time (e.g., "in 2 hours")
            
    Returns:
        Discord timestamp string (e.g., "<t:1731700800:F>")
    """
    unix_ts = to_unix_timestamp(dt)
    return f"<t:{unix_ts}:{format_code}>"


def validate_future_datetime(dt: datetime, min_hours_ahead: int = 0) -> datetime:
    """
    Validate that datetime is in the future.
    
    Args:
        dt: Datetime to validate
        min_hours_ahead: Minimum hours in the future required
        
    Returns:
        Validated UTC datetime
        
    Raises:
        ValueError: If datetime is not sufficiently in the future
    """
    dt_utc = ensure_utc(dt)
    now = utc_now()

    if dt_utc <= now:
        raise ValueError("Datetime must be in the future")

    if min_hours_ahead > 0:
        min_time = now.replace(
            hour=now.hour + min_hours_ahead,
            minute=0,
            second=0,
            microsecond=0
        )
        if dt_utc < min_time:
            raise ValueError(f"Datetime must be at least {min_hours_ahead} hours in the future")

    return dt_utc
