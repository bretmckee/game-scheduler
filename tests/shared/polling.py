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
            msg = f"{description} not met within {timeout}s timeout ({attempt} attempts)"
            raise AssertionError(msg)

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
        await asyncio.sleep(seconds)

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
