"""Tests for base model utilities."""

from datetime import UTC, datetime

from shared.models.base import generate_uuid, utc_now


def test_utc_now_returns_timezone_naive_datetime():
    """Verify utc_now returns timezone-naive datetime in UTC."""
    now = utc_now()

    assert isinstance(now, datetime)
    assert now.tzinfo is None

    # Verify it's reasonably close to current time
    utc_aware_now = datetime.now(UTC)
    diff = abs((utc_aware_now.replace(tzinfo=None) - now).total_seconds())
    assert diff < 1.0


def test_utc_now_consistent_timing():
    """Verify multiple calls to utc_now are consistent."""
    time1 = utc_now()
    time2 = utc_now()

    assert time1.tzinfo is None
    assert time2.tzinfo is None
    assert time2 >= time1


def test_generate_uuid_returns_string():
    """Verify generate_uuid returns a valid UUID string."""
    uuid = generate_uuid()

    assert isinstance(uuid, str)
    assert len(uuid) == 36
    assert uuid.count("-") == 4


def test_generate_uuid_unique():
    """Verify generate_uuid returns unique values."""
    uuid1 = generate_uuid()
    uuid2 = generate_uuid()

    assert uuid1 != uuid2
