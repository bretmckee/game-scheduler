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


"""Notification schedule model for database-backed notification system."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, generate_uuid, utc_now

if TYPE_CHECKING:
    from .game import GameSession
    from .participant import GameParticipant


class NotificationSchedule(Base):
    """
    Pre-calculated notification times for scheduled games.

    Each record represents one notification to be sent at a specific time.
    The scheduler daemon queries MIN(notification_time) to determine when
    to wake up next.

    Supports two notification types:
    - reminder: Game-wide reminders (participant_id is NULL)
    - join_notification: Participant-specific join confirmations (participant_id set)
    """

    __tablename__ = "notification_schedule"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    game_id: Mapped[str] = mapped_column(
        ForeignKey("game_sessions.id", ondelete="CASCADE"), index=True
    )
    reminder_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    notification_time: Mapped[datetime] = mapped_column(nullable=False, index=True)
    game_scheduled_at: Mapped[datetime] = mapped_column(nullable=False)
    sent: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(default=utc_now, server_default=func.now())
    notification_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="reminder",
        server_default=text("'reminder'"),
    )
    participant_id: Mapped[str | None] = mapped_column(
        ForeignKey("game_participants.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )

    game: Mapped["GameSession"] = relationship("GameSession")
    participant: Mapped["GameParticipant | None"] = relationship("GameParticipant")

    __table_args__ = (
        UniqueConstraint(
            "game_id", "reminder_minutes", name="uq_notification_schedule_game_reminder"
        ),
    )
