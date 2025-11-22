"""
Participant resolver service for validating and resolving @mentions.

Handles resolution of Discord user mentions and placeholder strings for
pre-populating game participant lists.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from services.api.auth import discord_client as discord_client_module
from shared.models import user as user_model

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Validation error for participant resolution."""

    def __init__(self, invalid_mentions: list[dict], valid_participants: list[str]):
        """
        Initialize validation error.

        Args:
            invalid_mentions: List of invalid mention errors
            valid_participants: List of successfully resolved participants
        """
        self.invalid_mentions = invalid_mentions
        self.valid_participants = valid_participants
        super().__init__(f"Failed to resolve {len(invalid_mentions)} mentions")


class ParticipantResolver:
    """Resolves initial participant list from @mentions and placeholders."""

    def __init__(self, discord_client: discord_client_module.DiscordAPIClient):
        """
        Initialize participant resolver.

        Args:
            discord_client: Discord API client for member search
        """
        self.discord_client = discord_client

    async def resolve_initial_participants(
        self,
        guild_discord_id: str,
        participant_inputs: list[str],
        access_token: str,
    ) -> tuple[list[dict], list[dict]]:
        """
        Resolve initial participant list from @mentions and placeholders.

        Args:
            guild_discord_id: Discord guild snowflake ID
            participant_inputs: List of @mentions or placeholder strings
            access_token: User's access token for Discord API calls

        Returns:
            Tuple of (valid_participants, validation_errors)
            valid_participants: List of dicts with type, discord_id/display_name
            validation_errors: List of dicts with input, reason, suggestions
        """
        valid_participants = []
        validation_errors = []

        for input_text in participant_inputs:
            input_text = input_text.strip()

            if not input_text:
                continue

            if input_text.startswith("@"):
                # Discord mention - validate and resolve
                mention_text = input_text[1:].lower()

                try:
                    # Search guild members
                    members = await self._search_guild_members(
                        guild_discord_id, mention_text, access_token
                    )

                    if len(members) == 0:
                        validation_errors.append(
                            {
                                "input": input_text,
                                "reason": "User not found in guild",
                                "suggestions": [],
                            }
                        )
                    elif len(members) == 1:
                        # Single match - use it
                        valid_participants.append(
                            {
                                "type": "discord",
                                "discord_id": members[0]["user"]["id"],
                                "original_input": input_text,
                            }
                        )
                    else:
                        # Multiple matches - disambiguation needed
                        suggestions = [
                            {
                                "discordId": m["user"]["id"],
                                "username": m["user"]["username"],
                                "displayName": (
                                    m.get("nick")
                                    or m["user"].get("global_name")
                                    or m["user"]["username"]
                                ),
                            }
                            for m in members[:5]
                        ]
                        validation_errors.append(
                            {
                                "input": input_text,
                                "reason": "Multiple matches found",
                                "suggestions": suggestions,
                            }
                        )

                except discord_client_module.DiscordAPIError as e:
                    logger.error(
                        f"Discord API error searching guild {guild_discord_id} "
                        f"for query '{mention_text}': {e.status} - {e.message}"
                    )
                    validation_errors.append(
                        {
                            "input": input_text,
                            "reason": f"Discord API error: {e.message}",
                            "suggestions": [],
                        }
                    )
                except Exception as e:
                    logger.error(
                        f"Unexpected error searching guild members for '{mention_text}': {e}",
                        exc_info=True,
                    )
                    validation_errors.append(
                        {
                            "input": input_text,
                            "reason": "Internal error searching for user",
                            "suggestions": [],
                        }
                    )
            else:
                # Placeholder string - always valid
                valid_participants.append(
                    {
                        "type": "placeholder",
                        "display_name": input_text,
                        "original_input": input_text,
                    }
                )

        return valid_participants, validation_errors

    async def _search_guild_members(
        self,
        guild_discord_id: str,
        query: str,
        access_token: str,
    ) -> list[dict]:
        """
        Search guild members by query string.

        Args:
            guild_discord_id: Discord guild snowflake ID
            query: Search query (username, global_name, or nickname)
            access_token: User's access token for Discord API calls

        Returns:
            List of member objects matching the query

        Raises:
            DiscordAPIError: If API call fails
        """
        url = f"https://discord.com/api/v10/guilds/{guild_discord_id}/members/search"
        params = {"query": query, "limit": 10}

        session = await self.discord_client._get_session()

        try:
            async with session.get(
                url,
                params=params,
                headers={"Authorization": f"Bot {self.discord_client.bot_token}"},
            ) as response:
                if response.status != 200:
                    try:
                        response_data = await response.json()
                        error_msg = response_data.get("message", "Unknown error")
                    except Exception:
                        error_msg = f"HTTP {response.status}"

                    logger.error(
                        f"Discord API error searching guild {guild_discord_id}: "
                        f"{response.status} - {error_msg}"
                    )
                    raise discord_client_module.DiscordAPIError(response.status, error_msg)

                response_data = await response.json()
                return response_data

        except discord_client_module.DiscordAPIError:
            raise
        except Exception as e:
            logger.error(
                f"Network error searching guild members in {guild_discord_id}: {e}",
                exc_info=True,
            )
            raise discord_client_module.DiscordAPIError(500, f"Network error: {str(e)}") from e

    async def ensure_user_exists(
        self,
        db: AsyncSession,
        discord_id: str,
    ) -> user_model.User:
        """
        Ensure user exists in database, create if not.

        Args:
            db: Database session
            discord_id: Discord user snowflake ID

        Returns:
            User model instance
        """
        result = await db.execute(
            select(user_model.User).where(user_model.User.discord_id == discord_id)
        )
        user = result.scalar_one_or_none()

        if user is None:
            user = user_model.User(discord_id=discord_id)
            db.add(user)
            await db.flush()

        return user
