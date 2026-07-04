# Copyright 2026 Bret McKee
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


"""ORM model for the bot action queue."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, generate_uuid


class BotActionQueue(Base):
    """
    Durable queue for pending bot actions.

    Each row represents one pending action for the bot to execute.
    The action_type field determines which handler processes it.
    Rows are deleted by the handler after successful processing,
    within the same transaction — crash safety via Postgres atomicity.

    A DB trigger fires pg_notify('bot_action_queue_changed', '') on INSERT
    so the bot listener wakes up immediately.
    """

    __tablename__ = "bot_action_queue"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
        server_default=func.gen_random_uuid().cast(String),
    )
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    game_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    channel_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    message_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    discord_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    enqueued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
