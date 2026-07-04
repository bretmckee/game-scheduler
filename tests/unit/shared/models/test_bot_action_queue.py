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


"""Tests for BotActionQueue model."""

from sqlalchemy import inspect

from shared.models.bot_action_queue import BotActionQueue


class TestBotActionQueueModel:
    """Test suite for BotActionQueue model."""

    def test_tablename(self) -> None:
        """ORM model maps to the correct table name."""
        assert BotActionQueue.__tablename__ == "bot_action_queue"

    def test_instantiate_with_action_type(self) -> None:
        """Can instantiate with required action_type field."""
        row = BotActionQueue(action_type="game_created")
        assert row.action_type == "game_created"

    def test_optional_fields(self) -> None:
        """All optional fields can be set and read back."""
        row = BotActionQueue(
            action_type="game_cancelled",
            game_id="game-abc",
            channel_id="123456789012345678",
            message_id="987654321098765432",
            user_id="user-xyz",
            discord_id="111222333444555666",
            payload={"extra": "data"},
        )
        assert row.game_id == "game-abc"
        assert row.channel_id == "123456789012345678"
        assert row.message_id == "987654321098765432"
        assert row.user_id == "user-xyz"
        assert row.discord_id == "111222333444555666"
        assert row.payload == {"extra": "data"}

    def test_id_column_exists(self) -> None:
        """Model has an id column."""
        mapper = inspect(BotActionQueue)
        columns = {c.key for c in mapper.mapper.column_attrs}
        assert "id" in columns

    def test_action_type_not_nullable(self) -> None:
        """action_type column is not nullable."""
        mapper = inspect(BotActionQueue)
        table = mapper.mapper.local_table
        col = table.c["action_type"]
        assert col.nullable is False

    def test_enqueued_at_column_exists(self) -> None:
        """Model has an enqueued_at column."""
        mapper = inspect(BotActionQueue)
        columns = {c.key for c in mapper.mapper.column_attrs}
        assert "enqueued_at" in columns

    def test_primary_key_is_id(self) -> None:
        """Primary key is the id column."""
        mapper = inspect(BotActionQueue)
        table = mapper.mapper.local_table
        pk_names = {col.name for col in table.primary_key.columns}
        assert pk_names == {"id"}
