"""Base SQLAlchemy model configuration."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all database models with common fields."""

    pass


def utc_now() -> datetime:
    """Return current UTC datetime (timezone-naive)."""
    return datetime.now(UTC).replace(tzinfo=None)


def generate_uuid() -> str:
    """Generate UUID string for primary keys."""
    return str(uuid4())
