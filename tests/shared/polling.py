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


"""Polling utilities for waiting on database conditions in tests."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session


async def _poll_until_condition(
    fetch_row: Callable[[], Awaitable[Any]],
    predicate: Callable[[Any], bool],
    get_elapsed: Callable[[], float],
    sleep: Callable[[float], Awaitable[None]],
    timeout: int,
    interval: float,
    description: str,
) -> Any:
    """Core polling logic for both async and sync versions."""
    attempt = 0

    while True:
        attempt += 1
        elapsed = get_elapsed()

        if elapsed >= timeout:
            raise AssertionError(
                f"{description} not met within {timeout}s timeout ({attempt} attempts)"
            )

        row = await fetch_row()

        if row and predicate(row):
            print(f"[WAIT] ✓ {description} met after {elapsed:.1f}s (attempt {attempt})")
            return row

        if attempt == 1:
            print(f"[WAIT] Waiting for {description} (timeout: {timeout}s, interval: {interval}s)")
        elif attempt % 5 == 0:
            print(
                f"[WAIT] Still waiting for {description}... "
                f"({elapsed:.0f}s elapsed, attempt {attempt})"
            )

        await sleep(interval)


async def wait_for_db_condition_async(
    db_session: AsyncSession,
    query: str,
    params: dict,
    predicate: Callable[[Any], bool],
    timeout: int = 10,
    interval: float = 0.5,
    description: str = "database condition",
) -> Any:
    """
    Poll database query until predicate satisfied (async version).

    Args:
        db_session: SQLAlchemy async session
        query: SQL query string
        params: Query parameters
        predicate: Function returning True when result matches expectation
        timeout: Maximum seconds to wait
        interval: Seconds between queries
        description: Human-readable description

    Returns:
        Query result when predicate satisfied

    Raises:
        AssertionError: If condition not met within timeout

    Example:
        result = await wait_for_db_condition_async(
            db_session,
            "SELECT message_id FROM game_sessions WHERE id = :game_id",
            {"game_id": game_id},
            lambda row: row[0] is not None,
            description="message_id population"
        )
        message_id = result[0]
    """
    start_time = asyncio.get_event_loop().time()

    async def fetch_row() -> Any:
        result = await db_session.execute(text(query), params)
        return result.fetchone()

    async def async_sleep(seconds: float) -> None:
        await asyncio.sleep(seconds)

    return await _poll_until_condition(
        fetch_row=fetch_row,
        predicate=predicate,
        get_elapsed=lambda: asyncio.get_event_loop().time() - start_time,
        sleep=async_sleep,
        timeout=timeout,
        interval=interval,
        description=description,
    )


def wait_for_db_condition_sync(
    db_session: Session,
    query: str,
    params: dict,
    predicate: Callable[[Any], bool],
    timeout: int = 10,
    interval: float = 0.5,
    description: str = "database condition",
) -> Any:
    """
    Poll database query until predicate satisfied (sync version).

    Args:
        db_session: SQLAlchemy sync session
        query: SQL query string
        params: Query parameters
        predicate: Function returning True when result matches expectation
        timeout: Maximum seconds to wait
        interval: Seconds between queries
        description: Human-readable description

    Returns:
        Query result when predicate satisfied

    Raises:
        AssertionError: If condition not met within timeout

    Example:
        result = wait_for_db_condition_sync(
            db_session,
            "SELECT sent FROM notification_schedule WHERE id = :id",
            {"id": notif_id},
            lambda row: row[0] is True,
            description="notification marked as sent"
        )
    """
    start_time = time.time()

    async def fetch_row() -> Any:
        result = db_session.execute(text(query), params)
        return result.fetchone()

    async def async_sleep(seconds: float) -> None:
        time.sleep(seconds)

    return asyncio.run(
        _poll_until_condition(
            fetch_row=fetch_row,
            predicate=predicate,
            get_elapsed=lambda: time.time() - start_time,
            sleep=async_sleep,
            timeout=timeout,
            interval=interval,
            description=description,
        )
    )
