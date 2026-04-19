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


"""Unit tests for refresh_display_name_on_login projection-based migration."""

from unittest.mock import AsyncMock, MagicMock, patch

from services.api.services.login_refresh import refresh_display_name_on_login


def _make_guild(guild_id: str) -> MagicMock:
    guild = MagicMock()
    guild.guild_id = guild_id
    return guild


def _make_session(guilds: list) -> AsyncMock:
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    result = MagicMock()
    result.scalars.return_value.all.return_value = guilds
    mock_session.execute = AsyncMock(return_value=result)
    mock_session.commit = AsyncMock()
    return mock_session


class TestRefreshDisplayNameProjectionMigration:
    """Tests for projection-based member data reads in refresh_display_name_on_login."""

    async def test_upserts_display_name_from_projection(self):
        """Uses projection get_member instead of Discord REST; resolves flat dict fields."""
        member = {
            "roles": ["role1", "role2"],
            "nick": "ProjNick",
            "global_name": "ProjGlobal",
            "username": "projuser",
            "avatar_url": "https://cdn.discordapp.com/avatars/usr123/hash.png?size=64",
        }
        mock_cache = AsyncMock()
        mock_session = _make_session([_make_guild("guild123")])

        with (
            patch(
                "services.api.services.login_refresh.member_projection.get_user_guilds",
                new=AsyncMock(return_value=["guild123"]),
            ),
            patch(
                "services.api.services.login_refresh.member_projection.get_member",
                new=AsyncMock(return_value=member),
            ),
            patch(
                "services.api.services.login_refresh.setup_rls_and_convert_guild_ids",
                new=AsyncMock(),
            ),
            patch("services.api.services.login_refresh.clear_current_guild_ids"),
            patch(
                "services.api.services.login_refresh.AsyncSessionLocal",
                return_value=mock_session,
            ),
            patch(
                "services.api.services.login_refresh.cache_client.get_redis_client",
                return_value=mock_cache,
            ),
            patch("services.api.services.login_refresh.UserDisplayNameService") as mock_svc_cls,
        ):
            mock_svc = AsyncMock()
            mock_svc_cls.return_value = mock_svc

            await refresh_display_name_on_login("usr123")

        mock_svc.upsert_batch.assert_called_once()
        entries = mock_svc.upsert_batch.call_args[0][0]
        assert len(entries) == 1
        assert entries[0]["display_name"] == "ProjNick"
        assert (
            entries[0]["avatar_url"] == "https://cdn.discordapp.com/avatars/usr123/hash.png?size=64"
        )
        assert entries[0]["user_discord_id"] == "usr123"
        assert entries[0]["guild_discord_id"] == "guild123"

    async def test_user_absent_from_projection_returns_early(self):
        """When get_user_guilds returns None, function returns without DB writes."""
        mock_cache = AsyncMock()

        with (
            patch(
                "services.api.services.login_refresh.member_projection.get_user_guilds",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "services.api.services.login_refresh.cache_client.get_redis_client",
                return_value=mock_cache,
            ),
            patch("services.api.services.login_refresh.clear_current_guild_ids"),
            patch("services.api.services.login_refresh.UserDisplayNameService") as mock_svc_cls,
        ):
            await refresh_display_name_on_login("usr123")

        mock_svc_cls.assert_not_called()

    async def test_member_absent_from_projection_skips_guild(self):
        """When get_member returns None for a guild, that guild is silently skipped."""
        mock_cache = AsyncMock()
        mock_session = _make_session([_make_guild("guild123")])

        with (
            patch(
                "services.api.services.login_refresh.member_projection.get_user_guilds",
                new=AsyncMock(return_value=["guild123"]),
            ),
            patch(
                "services.api.services.login_refresh.member_projection.get_member",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "services.api.services.login_refresh.setup_rls_and_convert_guild_ids",
                new=AsyncMock(),
            ),
            patch("services.api.services.login_refresh.clear_current_guild_ids"),
            patch(
                "services.api.services.login_refresh.AsyncSessionLocal",
                return_value=mock_session,
            ),
            patch(
                "services.api.services.login_refresh.cache_client.get_redis_client",
                return_value=mock_cache,
            ),
            patch("services.api.services.login_refresh.UserDisplayNameService") as mock_svc_cls,
        ):
            mock_svc = AsyncMock()
            mock_svc_cls.return_value = mock_svc

            await refresh_display_name_on_login("usr123")

        mock_svc.upsert_batch.assert_called_once_with([])

    async def test_display_name_falls_back_to_global_name_then_username(self):
        """Display name resolution: nick → global_name → username on flat projection dict."""
        member_no_nick = {
            "roles": [],
            "nick": None,
            "global_name": "GlobalName",
            "username": "baseuser",
            "avatar_url": None,
        }
        mock_cache = AsyncMock()
        mock_session = _make_session([_make_guild("guild123")])

        with (
            patch(
                "services.api.services.login_refresh.member_projection.get_user_guilds",
                new=AsyncMock(return_value=["guild123"]),
            ),
            patch(
                "services.api.services.login_refresh.member_projection.get_member",
                new=AsyncMock(return_value=member_no_nick),
            ),
            patch(
                "services.api.services.login_refresh.setup_rls_and_convert_guild_ids",
                new=AsyncMock(),
            ),
            patch("services.api.services.login_refresh.clear_current_guild_ids"),
            patch(
                "services.api.services.login_refresh.AsyncSessionLocal",
                return_value=mock_session,
            ),
            patch(
                "services.api.services.login_refresh.cache_client.get_redis_client",
                return_value=mock_cache,
            ),
            patch("services.api.services.login_refresh.UserDisplayNameService") as mock_svc_cls,
        ):
            mock_svc = AsyncMock()
            mock_svc_cls.return_value = mock_svc

            await refresh_display_name_on_login("usr123")

        entries = mock_svc.upsert_batch.call_args[0][0]
        assert entries[0]["display_name"] == "GlobalName"

    async def test_role_cache_written_from_projection_roles(self):
        """Role IDs from projection member dict are written to the TTL role cache."""
        member = {
            "roles": ["role1", "role2"],
            "nick": None,
            "global_name": None,
            "username": "user",
            "avatar_url": None,
        }
        mock_cache = AsyncMock()
        mock_session = _make_session([_make_guild("guild123")])

        with (
            patch(
                "services.api.services.login_refresh.member_projection.get_user_guilds",
                new=AsyncMock(return_value=["guild123"]),
            ),
            patch(
                "services.api.services.login_refresh.member_projection.get_member",
                new=AsyncMock(return_value=member),
            ),
            patch(
                "services.api.services.login_refresh.setup_rls_and_convert_guild_ids",
                new=AsyncMock(),
            ),
            patch("services.api.services.login_refresh.clear_current_guild_ids"),
            patch(
                "services.api.services.login_refresh.AsyncSessionLocal",
                return_value=mock_session,
            ),
            patch(
                "services.api.services.login_refresh.cache_client.get_redis_client",
                return_value=mock_cache,
            ),
            patch("services.api.services.login_refresh.UserDisplayNameService") as mock_svc_cls,
        ):
            mock_svc = AsyncMock()
            mock_svc_cls.return_value = mock_svc

            await refresh_display_name_on_login("usr123")

        mock_cache.set_json.assert_called_once_with(
            "user_roles:usr123:guild123",
            ["role1", "role2", "guild123"],
            ttl=300,
        )
