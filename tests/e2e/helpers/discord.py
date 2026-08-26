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


"""Discord test helper for E2E tests."""

import asyncio
from collections.abc import Awaitable, Callable
from enum import StrEnum

import discord

from services.bot.formatters.game_message import (
    _LIST_NUMBER_PREFIX,
    _LIST_NUMBER_SUFFIX,
    _PARTICIPANT_COLUMNS,
    _WAITLIST_COLUMNS,
)
from shared.message_formats import DMPredicates


class DMType(StrEnum):
    """Types of game-related DMs."""

    REMINDER = "reminder"
    JOIN = "join"
    WAITLIST_JOIN = "waitlist_join"
    REMOVAL = "removal"
    PROMOTION = "promotion"
    CLONE_CONFIRMATION = "clone_confirmation"
    REWARDS_REMINDER = "rewards_reminder"
    HOST_ADDED_DROPOUT = "host_added_dropout"


async def wait_for_condition[T](
    check_func: Callable[[], Awaitable[tuple[bool, T | None]]],
    timeout: int = 30,
    interval: float = 1.0,
    description: str = "condition",
) -> T:
    """
    Poll for condition with timeout.

    Generic polling utility that repeatedly calls check_func until it returns
    (True, result) or timeout is reached.

    Args:
        check_func: Async function returning (condition_met: bool, result: T | None)
                   Should return (True, value) when condition met, (False, None) otherwise
        timeout: Maximum seconds to wait
        interval: Seconds between checks
        description: Human-readable description for error messages

    Returns:
        Result value returned by check_func when condition met

    Raises:
        AssertionError: If condition not met within timeout

    Example:
        async def check_message_exists():
            try:
                msg = await channel.fetch_message(msg_id)
                return (True, msg)
            except discord.NotFound:
                return (False, None)

        message = await wait_for_condition(
            check_message_exists,
            timeout=10,
            description="Discord message to appear"
        )
    """
    start_time = asyncio.get_event_loop().time()
    attempt = 0

    while True:
        attempt += 1
        elapsed = asyncio.get_event_loop().time() - start_time

        condition_met, result = await check_func()

        if condition_met:
            print(f"[WAIT] ✓ {description} met after {elapsed:.1f}s (attempt {attempt})")
            return result

        if elapsed >= timeout:
            msg = f"{description} not met within {timeout}s timeout ({attempt} attempts)"
            raise AssertionError(msg)

        if attempt == 1:
            print(f"[WAIT] Waiting for {description} (timeout: {timeout}s, interval: {interval}s)")
        elif attempt % 5 == 0:
            print(
                f"[WAIT] Still waiting for {description}... "
                f"({elapsed:.0f}s elapsed, attempt {attempt})"
            )

        await asyncio.sleep(interval)


class DiscordTestHelper:
    """
    Helper class for Discord API interactions in E2E tests.

    Provides methods to fetch and verify Discord messages, embeds, and DMs
    during end-to-end testing of the game scheduling bot.
    """

    def __init__(self, bot_token: str):
        """
        Initialize Discord test helper.

        Args:
            bot_token: Discord bot authentication token
        """
        # MESSAGE_CONTENT intent is required to fetch embeds, attachments, and content
        # via REST API, even though it's not a gateway event
        intents = discord.Intents(message_content=True)
        self.client = discord.Client(intents=intents)
        self.bot_token = bot_token
        self._connected = False

    async def __aenter__(self):
        """Context manager entry - connect to Discord."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - disconnect from Discord."""
        await self.disconnect()

    async def connect(self) -> None:
        """Connect to Discord using bot token."""
        if not self._connected:
            await self.client.login(self.bot_token)
            self._connected = True

    async def disconnect(self) -> None:
        """Disconnect from Discord."""
        if self._connected:
            await self.client.close()
            self._connected = False

    async def get_message(self, channel_id: str, message_id: str) -> discord.Message:
        """
        Fetch specific message from channel.

        Args:
            channel_id: Discord channel snowflake ID
            message_id: Discord message snowflake ID

        Returns:
            Discord Message object
        """
        channel = await self.client.fetch_channel(int(channel_id))
        if not isinstance(channel, discord.TextChannel | discord.Thread | discord.DMChannel):
            msg = f"Channel {channel_id} does not support messages"
            raise ValueError(msg)

        return await channel.fetch_message(int(message_id))

    async def delete_message(self, channel_id: str, message_id: str) -> None:
        """
        Delete a message from a Discord channel.

        Args:
            channel_id: Discord channel snowflake ID
            message_id: Discord message snowflake ID
        """
        channel = await self.client.fetch_channel(int(channel_id))
        message = await channel.fetch_message(int(message_id))
        await message.delete()

    async def create_thread(
        self, channel_id: str, name: str, auto_archive_duration: int = 60
    ) -> discord.Thread:
        """
        Create a public thread in a text channel.

        Args:
            channel_id: Discord channel snowflake ID of the parent text channel
            name: Thread name (3-100 characters)
            auto_archive_duration: Minutes before an idle thread archives (60/1440/4320/10080)

        Returns:
            The created Thread object
        """
        channel = await self.client.fetch_channel(int(channel_id))
        if not isinstance(channel, discord.TextChannel):
            msg = f"Channel {channel_id} is not a text channel; cannot start a thread"
            raise ValueError(msg)
        # Without an explicit type (or seed message), discord.py creates a PRIVATE
        # thread, which non-participant bots cannot see via REST or gateway events.
        thread = await channel.create_thread(
            name=name,
            auto_archive_duration=auto_archive_duration,
            type=discord.ChannelType.public_thread,
        )
        assert thread.type == discord.ChannelType.public_thread, (
            f"Expected public thread but got {thread.type!r}; private threads are "
            "invisible to non-participating bots and would break downstream assertions"
        )
        return thread

    async def get_recent_messages(self, channel_id: str, limit: int = 10) -> list[discord.Message]:
        """
        Fetch recent messages from channel.

        Args:
            channel_id: Discord channel snowflake ID
            limit: Maximum number of messages to retrieve

        Returns:
            List of recent Discord messages
        """
        channel = await self.client.fetch_channel(int(channel_id))
        if not isinstance(channel, discord.TextChannel | discord.Thread | discord.DMChannel):
            msg = f"Channel {channel_id} does not support message history"
            raise ValueError(msg)
        return [msg async for msg in channel.history(limit=limit)]

    async def find_message_by_embed_title(
        self, channel_id: str, title: str, limit: int = 10
    ) -> discord.Message | None:
        """
        Find message with specific embed title.

        Args:
            channel_id: Discord channel snowflake ID
            title: Embed title to search for
            limit: Maximum number of messages to search

        Returns:
            Message with matching embed title, or None if not found
        """
        messages = await self.get_recent_messages(channel_id, limit)
        for msg in messages:
            if msg.embeds and msg.embeds[0].title == title:
                return msg
        return None

    async def get_user_recent_dms(self, user_id: str, limit: int = 5) -> list[discord.Message]:
        """
        Fetch recent DM messages sent to user by the bot.

        Args:
            user_id: Discord user snowflake ID
            limit: Maximum number of DMs to retrieve

        Returns:
            List of recent DM messages sent by bot
        """
        user = await self.client.fetch_user(int(user_id))
        dm_channel = await user.create_dm()
        return [
            msg
            async for msg in dm_channel.history(limit=limit)
            if msg.author.id == self.client.user.id
        ]

    async def find_game_reminder_dm(self, user_id: str, game_title: str) -> discord.Message | None:
        """
        Find DM reminder for specific game.

        Args:
            user_id: Discord user snowflake ID
            game_title: Title of the game to find reminder for

        Returns:
            DM message containing game reminder, or None if not found
        """
        dms = await self.get_user_recent_dms(user_id, limit=10)
        for dm in dms:
            # Check content for game title (reminders are plain text, not embeds)
            if (
                dm.content
                and game_title in dm.content
                and "starts <t:" in dm.content
                and ":F>" in dm.content
            ):
                return dm
        return None

    def extract_embed_field_value(self, embed: discord.Embed, field_name: str) -> str | None:
        """
        Extract value from embed field by name.

        Args:
            embed: Discord embed object
            field_name: Name of the field to extract

        Returns:
            Field value string, or None if field not found
        """
        for field in embed.fields:
            if field.name == field_name:
                return field.value
        return None

    def _build_field_map(self, embed: discord.Embed) -> dict[str, str]:
        """
        Build mapping of embed field names to values.

        Args:
            embed: Discord embed object

        Returns:
            Dictionary mapping field names to field values
        """
        field_map = {}
        for field in embed.fields:
            if field.name:
                field_map[field.name] = field.value
        return field_map

    def _verify_basic_embed_structure(self, embed: discord.Embed, expected_title: str) -> None:
        """Verify embed has expected title and author format."""
        assert embed.title == expected_title, f"Title mismatch: {embed.title}"
        assert embed.author and embed.author.name, "Embed should have author with name"
        assert embed.author.name.startswith("@"), (
            f"Author should start with '@': {embed.author.name}"
        )

    def _verify_game_time_field(
        self, field_map: dict[str, str], expected_game_time: str | None
    ) -> None:
        """Verify Game Time field has Discord timestamp format."""
        game_time_field = None
        for name in field_map:
            if "Game Time" in name:
                game_time_field = field_map[name]
                break
        assert game_time_field is not None, "Game Time field missing"
        assert "<t:" in game_time_field, (
            f"Game Time should contain Discord timestamp: {game_time_field}"
        )
        if expected_game_time:
            assert expected_game_time in game_time_field, (
                f"Game Time timestamp mismatch: {game_time_field}"
            )

    def _verify_optional_fields(
        self,
        field_map: dict[str, str],
        expected_run_time: str | None,
        expected_location: str | None,
        expected_voice_channel: str | None,
    ) -> None:
        """Verify optional Run Time, Where, and Voice Channel fields."""
        if expected_run_time:
            run_time_field = field_map.get("Run Time")
            assert run_time_field is not None, "Run Time field missing when duration expected"
            assert expected_run_time in run_time_field, f"Run Time mismatch: {run_time_field}"

        if expected_location:
            where_field = field_map.get("Where")
            assert where_field is not None, "Where field missing when location expected"
            assert expected_location in where_field, f"Where field mismatch: {where_field}"

        if expected_voice_channel:
            voice_channel_field = field_map.get("Voice Channel")
            assert voice_channel_field is not None, "Voice Channel field missing when expected"
            assert expected_voice_channel in voice_channel_field, (
                f"Voice Channel mismatch: {voice_channel_field}"
            )

    def _find_participants_field(self, embed: discord.Embed) -> tuple[str, str]:
        """Find the players field(s) and return (field_name, combined_value).

        Players always span _PARTICIPANT_COLUMNS side-by-side embed
        columns (see GameMessageFormatter._add_participant_fields), so the
        combined value concatenates all of them in display order (each
        column's numbers are contiguous with the next, so this preserves
        1..N ordering).
        """
        fields = embed.fields
        for i, field in enumerate(fields):
            if field.name and "Players" in field.name:
                columns = [f.value or "" for f in fields[i : i + _PARTICIPANT_COLUMNS]]
                combined = "\n".join(v for v in columns if v and v != "\u200b")
                return field.name, combined
        msg = "Players field missing"
        raise AssertionError(msg)

    def _verify_participants_numbering(
        self, participants_value: str, verify_numbered_participants: bool
    ) -> None:
        """Verify player list has correct numbering format."""
        if (
            verify_numbered_participants
            and participants_value
            and participants_value not in ("None yet", "No players yet")
        ):
            lines = participants_value.split("\n")
            for i, line in enumerate(lines, start=1):
                if line.strip():
                    expected = f"{_LIST_NUMBER_PREFIX}{i}{_LIST_NUMBER_SUFFIX}"
                    assert line.startswith(expected), (
                        f"Participant line {i} should start with '{expected}': {line}"
                    )

    def _check_waitlist_numbering(self, waitlist_columns: list[str]) -> None:
        """Assert waitlist numbering starts at 1 and is contiguous across columns.

        The waitlist always spans _WAITLIST_COLUMNS columns (see
        GameMessageFormatter._add_participant_fields), split into
        contiguous chunks - column 1 holds the first chunk, column 2 the
        next, and so on - so each column's numbers pick up exactly where
        the previous column left off (not a row-major/interleaved split,
        which would read out of order on Discord's mobile client, which
        stacks fields as full columns instead of gridding them like
        desktop).
        """
        running_count = 0
        for column_value in waitlist_columns:
            lines = [line for line in column_value.split("\n") if line.strip()]
            for line in lines:
                running_count += 1
                expected = f"{_LIST_NUMBER_PREFIX}{running_count}{_LIST_NUMBER_SUFFIX}"
                assert line.startswith(expected), (
                    f"Waitlist line should start with '{expected}': {line}"
                )

    def _verify_waitlist_field(
        self,
        embed: discord.Embed,
        verify_numbered_participants: bool,
    ) -> None:
        """Verify waitlist field(s) and numbering if present."""
        fields = embed.fields
        waitlist_columns = None
        for i, field in enumerate(fields):
            if field.name and "Waitlist" in field.name:
                waitlist_columns = [f.value or "" for f in fields[i : i + _WAITLIST_COLUMNS]]
                break
        if waitlist_columns and verify_numbered_participants:
            self._check_waitlist_numbering(waitlist_columns)

    def _verify_links_field(self, field_map: dict[str, str], expected_game_id: str | None) -> None:
        """Verify Add to Calendar field contains calendar URLs if game_id provided."""
        if expected_game_id:
            links_field = field_map.get("Add to Calendar")
            assert links_field is not None, "Add to Calendar field missing when game_id provided"
            assert f"/download-calendar/{expected_game_id}" in links_field, (
                f"Add to Calendar field should contain calendar URL: {links_field}"
            )
            assert "calendar.google.com" in links_field, (
                f"Add to Calendar field should contain Google Calendar quick-add URL: {links_field}"
            )

    def verify_game_embed(
        self,
        embed: discord.Embed,
        expected_title: str,
        expected_host_id: str,
        expected_max_players: int,
        expected_game_time: str | None = None,
        expected_run_time: str | None = None,
        expected_location: str | None = None,
        expected_voice_channel: str | None = None,
        expected_game_id: str | None = None,
        verify_numbered_participants: bool = True,
    ) -> None:
        """
        Verify game announcement embed structure and content.

        Args:
            embed: Discord embed object to verify
            expected_title: Expected game title
            expected_host_id: Expected Discord host user ID
            expected_max_players: Expected maximum player count
            expected_game_time: Optional timestamp to verify in Game Time field
            expected_run_time: Optional duration text to verify in Run Time field
            expected_location: Optional location text to verify in Where field
            expected_voice_channel: Optional voice channel name to verify
            expected_game_id: Optional game ID to verify Links field contains calendar URL
            verify_numbered_participants: Whether to verify participant list numbering
                (default True)

        Raises:
            AssertionError: If embed does not match expected values
        """
        self._verify_basic_embed_structure(embed, expected_title)

        field_map = self._build_field_map(embed)

        self._verify_game_time_field(field_map, expected_game_time)
        self._verify_optional_fields(
            field_map, expected_run_time, expected_location, expected_voice_channel
        )

        participants_field_name, participants_field_value = self._find_participants_field(embed)
        assert f"/{expected_max_players}" in participants_field_name, (
            f"Max players incorrect in field name: {participants_field_name}"
        )

        self._verify_participants_numbering(participants_field_value, verify_numbered_participants)
        self._verify_waitlist_field(embed, verify_numbered_participants)
        self._verify_links_field(field_map, expected_game_id)

        assert embed.footer and embed.footer.text, "Embed should have footer with status"

    async def wait_for_message(
        self,
        channel_id: str,
        message_id: str,
        timeout: int = 10,
        interval: float = 0.5,
    ) -> discord.Message:
        """
        Wait for Discord message to exist.

        Polls channel.fetch_message() until message found or timeout.
        Useful after API operations that create/update Discord messages.

        Args:
            channel_id: Discord channel snowflake
            message_id: Discord message snowflake
            timeout: Maximum seconds to wait
            interval: Seconds between fetch attempts

        Returns:
            Discord Message object

        Raises:
            AssertionError: If message not found within timeout
        """

        async def check_message():
            try:
                msg = await self.get_message(channel_id, message_id)
                return (True, msg)
            except (discord.NotFound, discord.HTTPException):
                return (False, None)

        return await wait_for_condition(
            check_message,
            timeout=timeout,
            interval=interval,
            description=f"message {message_id} in channel {channel_id}",
        )

    async def wait_for_message_update(
        self,
        channel_id: str,
        message_id: str,
        check_func: Callable[[discord.Message], bool],
        timeout: int = 10,
        interval: float = 1.0,
        description: str = "message update",
    ) -> discord.Message:
        """
        Wait for Discord message to match condition.

        Polls message until check_func returns True. Useful for verifying
        embed updates, content changes, etc.

        Args:
            channel_id: Discord channel snowflake
            message_id: Discord message snowflake
            check_func: Function that returns True when message matches expected state
            timeout: Maximum seconds to wait
            interval: Seconds between checks
            description: Human-readable description for logging

        Returns:
            Updated Discord Message object

        Example:
            # Wait for embed title to change
            updated_msg = await helper.wait_for_message_update(
                channel_id,
                message_id,
                lambda msg: msg.embeds[0].title == "New Title",
                description="embed title update"
            )
        """

        async def check_update():
            try:
                msg = await self.get_message(channel_id, message_id)
                if check_func(msg):
                    return (True, msg)
                return (False, None)
            except (discord.NotFound, discord.HTTPException):
                return (False, None)

        return await wait_for_condition(
            check_update,
            timeout=timeout,
            interval=interval,
            description=description,
        )

    async def wait_for_message_deleted(
        self,
        channel_id: str,
        message_id: str,
        timeout: int = 30,
        interval: float = 1.0,
    ) -> None:
        """
        Wait for Discord message to be deleted.

        Polls channel.fetch_message() until Discord returns NotFound.

        Args:
            channel_id: Discord channel snowflake
            message_id: Discord message snowflake
            timeout: Maximum seconds to wait
            interval: Seconds between checks
        """

        async def check_deleted():
            try:
                await self.get_message(channel_id, message_id)
                return (False, None)
            except discord.NotFound:
                return (True, True)
            except discord.HTTPException:
                return (False, None)

        await wait_for_condition(
            check_deleted,
            timeout=timeout,
            interval=interval,
            description=f"message {message_id} deletion in channel {channel_id}",
        )

    async def wait_for_dm_matching(
        self,
        user_id: str,
        predicate: Callable[[discord.Message], bool],
        timeout: int = 150,
        interval: float = 5.0,
        description: str = "DM",
    ) -> discord.Message:
        """
        Wait for DM matching predicate.

        Polls user's DM channel until message matching predicate found.
        Uses longer default timeout since DMs may be delayed by notification
        daemon polling intervals.

        Args:
            user_id: Discord user snowflake
            predicate: Function returning True for matching DM
            timeout: Maximum seconds to wait (default 150s for daemon delays)
            interval: Seconds between DM channel checks
            description: Human-readable description for logging

        Returns:
            Matching Discord Message object

        Example:
            # Wait for game reminder DM
            reminder_dm = await helper.wait_for_dm_matching(
                user_id,
                lambda dm: (
                    "Test Game" in dm.content
                    and "starts <t:" in dm.content
                    and ":F>" in dm.content
                ),
                description="game reminder DM"
            )
        """

        async def check_dms():
            dms = await self.get_user_recent_dms(user_id, limit=15)
            for dm in dms:
                if predicate(dm):
                    return (True, dm)
            return (False, None)

        return await wait_for_condition(
            check_dms,
            timeout=timeout,
            interval=interval,
            description=description,
        )

    async def wait_for_channel_message(
        self,
        channel_id: str,
        predicate: Callable[[discord.Message], bool],
        timeout: int = 150,
        interval: float = 5.0,
        limit: int = 15,
        description: str = "channel message",
    ) -> discord.Message:
        """
        Wait for a recent message in a channel matching a predicate.

        Polls channel history until a message matching predicate is found.
        Uses the same default timeout as DM waits since posts may be delayed
        by notification daemon polling intervals.

        Args:
            channel_id: Discord channel snowflake
            predicate: Function returning True for the matching message
            timeout: Maximum seconds to wait (default 150s for daemon delays)
            interval: Seconds between history scans
            limit: Number of recent messages to scan each poll
            description: Human-readable description for logging

        Returns:
            Matching Discord Message object
        """

        async def check_messages():
            messages = await self.get_recent_messages(channel_id, limit)
            for msg in messages:
                if predicate(msg):
                    return (True, msg)
            return (False, None)

        return await wait_for_condition(
            check_messages,
            timeout=timeout,
            interval=interval,
            description=description,
        )

    async def wait_for_recent_dm(
        self,
        user_id: str,
        game_title: str,
        dm_type: DMType = DMType.REMINDER,
        timeout: int = 150,
        interval: float = 5.0,
    ) -> discord.Message:
        """
        Wait for specific type of game-related DM.

        Convenience wrapper around wait_for_dm_matching for common DM types.
        Uses centralized predicates from shared.message_formats to ensure
        tests stay in sync with production message formats.

        Args:
            user_id: Discord user snowflake
            game_title: Title of game to find DM for
            dm_type: Type of DM (DMType.REMINDER, JOIN, REMOVAL, or PROMOTION)
            timeout: Maximum seconds to wait
            interval: Seconds between checks

        Returns:
            Matching Discord Message object
        """
        predicates = {
            DMType.REMINDER: DMPredicates.reminder(game_title),
            DMType.JOIN: DMPredicates.join(game_title),
            DMType.WAITLIST_JOIN: DMPredicates.join_waitlist(game_title),
            DMType.REMOVAL: DMPredicates.removal(game_title),
            DMType.PROMOTION: DMPredicates.promotion(game_title),
            DMType.CLONE_CONFIRMATION: DMPredicates.clone_confirmation(game_title),
            DMType.REWARDS_REMINDER: DMPredicates.rewards_reminder(game_title),
            DMType.HOST_ADDED_DROPOUT: DMPredicates.host_added_dropout(game_title),
        }

        return await self.wait_for_dm_matching(
            user_id,
            predicates[dm_type],
            timeout=timeout,
            interval=interval,
            description=f"{dm_type.value} DM for '{game_title}'",
        )

    async def wait_for_embed_images(
        self,
        channel_id: str,
        message_id: str,
        expect_thumbnail: bool = False,
        expect_image: bool = False,
        timeout: int = 30,
        interval: float = 2.0,
    ) -> discord.Message:
        """
        Poll a message until Discord has populated embed image dimensions.

        Discord fetches images asynchronously after a message is posted, then sets
        width/height on the embed proxy URLs. This method retries until those
        dimensions are non-zero so the caller can assert them reliably.

        Args:
            channel_id: Discord channel snowflake ID
            message_id: Discord message snowflake ID
            expect_thumbnail: Whether to wait for thumbnail dimensions
            expect_image: Whether to wait for image (banner) dimensions
            timeout: Maximum seconds to wait
            interval: Seconds between fetches

        Returns:
            Discord Message with populated image dimensions
        """

        async def check_images() -> tuple[bool, discord.Message | None]:
            msg = await self.get_message(channel_id, message_id)
            if not msg.embeds:
                return (False, None)
            embed = msg.embeds[0]
            if expect_thumbnail and (embed.thumbnail is None or not embed.thumbnail.width):
                return (False, None)
            if expect_image and (embed.image is None or not embed.image.width):
                return (False, None)
            return (True, msg)

        return await wait_for_condition(
            check_images,
            timeout=timeout,
            interval=interval,
            description="Discord embed image dimensions to be populated",
        )

    def verify_embed_images(
        self,
        embed: discord.Embed,
        expect_thumbnail: bool = False,
        expect_image: bool = False,
        expected_thumbnail_url_fragment: str | None = None,
        expected_image_url_fragment: str | None = None,
    ) -> None:
        """
        Verify embed has expected thumbnail and/or image with Discord-validated dimensions.

        Checks that Discord successfully fetched and rendered the images by validating
        that width and height are set (Discord sets these after fetching the image).

        Args:
            embed: Discord embed object to verify
            expect_thumbnail: Whether thumbnail should be present
            expect_image: Whether image should be present
            expected_thumbnail_url_fragment: Optional URL fragment to verify in thumbnail URL
            expected_image_url_fragment: Optional URL fragment to verify in image URL

        Raises:
            AssertionError: If embed images don't match expectations
        """
        if expect_thumbnail:
            assert embed.thumbnail is not None, "Expected embed to have thumbnail"
            assert embed.thumbnail.url is not None, "Thumbnail should have URL"
            assert embed.thumbnail.width is not None, (
                "Thumbnail width should be set (proves Discord fetched image)"
            )
            assert embed.thumbnail.height is not None, (
                "Thumbnail height should be set (proves Discord fetched image)"
            )
            assert embed.thumbnail.width > 0, (
                f"Thumbnail width should be > 0: {embed.thumbnail.width}"
            )
            assert embed.thumbnail.height > 0, (
                f"Thumbnail height should be > 0: {embed.thumbnail.height}"
            )

            if expected_thumbnail_url_fragment:
                assert expected_thumbnail_url_fragment in embed.thumbnail.url, (
                    f"Thumbnail URL should contain '{expected_thumbnail_url_fragment}': "
                    f"{embed.thumbnail.url}"
                )
        else:
            assert embed.thumbnail is None or embed.thumbnail.url is None, (
                "Expected embed to NOT have thumbnail"
            )

        if expect_image:
            assert embed.image is not None, "Expected embed to have image"
            assert embed.image.url is not None, "Image should have URL"
            assert embed.image.width is not None, (
                "Image width should be set (proves Discord fetched image)"
            )
            assert embed.image.height is not None, (
                "Image height should be set (proves Discord fetched image)"
            )
            assert embed.image.width > 0, f"Image width should be > 0: {embed.image.width}"
            assert embed.image.height > 0, f"Image height should be > 0: {embed.image.height}"

            if expected_image_url_fragment:
                assert expected_image_url_fragment in embed.image.url, (
                    f"Image URL should contain '{expected_image_url_fragment}': {embed.image.url}"
                )
        else:
            assert embed.image is None or embed.image.url is None, (
                "Expected embed to NOT have image"
            )
