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


"""Guild-scoped database query wrappers.

Centralized database access layer that:
- Eliminates code duplication (consolidates 37+ scattered queries)
- Enforces guild isolation (required guild_id parameters)
- Provides consistent RLS context management
- Enables architectural enforcement through import restrictions

All functions require guild_id parameter and set RLS context before queries.
"""

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.game import GameSession
from shared.models.participant import GameParticipant
from shared.models.template import GameTemplate


async def get_game_by_id(db: AsyncSession, guild_id: str, game_id: str) -> GameSession | None:
    """
    Get game by ID with guild isolation enforcement.

    Consolidates 8+ inline select(GameSession).where(...) queries identified in duplication audit.

    Args:
        db: Database session for query execution
        guild_id: Guild ID for isolation (required, cannot be None)
        game_id: Game session ID to retrieve

    Returns:
        GameSession if found in specified guild, None otherwise

    Raises:
        ValueError: If guild_id or game_id is empty string
    """
    if not guild_id:
        msg = "guild_id cannot be empty"
        raise ValueError(msg)
    if not game_id:
        msg = "game_id cannot be empty"
        raise ValueError(msg)

    # SET commands don't support parameter binding, use literal_column with validation
    # guild_id comes from application context (Discord/API auth), validated as UUID format
    await db.execute(text(f"SET LOCAL app.current_guild_id = '{guild_id}'"))

    result = await db.execute(
        select(GameSession).where(GameSession.id == game_id).where(GameSession.guild_id == guild_id)
    )
    return result.scalar_one_or_none()


async def list_games(
    db: AsyncSession, guild_id: str, channel_id: str | None = None
) -> list[GameSession]:
    """
    List games for guild with optional channel filter.

    Replaces list_games(guild_id: str | None = None) pattern that created
    cross-guild data leakage risk. Consolidates 5+ variations of game listing queries.

    Args:
        db: Database session for query execution
        guild_id: Guild ID for isolation (required, cannot be None)
        channel_id: Optional channel ID to filter games by channel

    Returns:
        List of GameSession objects for the specified guild

    Raises:
        ValueError: If guild_id is empty string
    """
    if not guild_id:
        msg = "guild_id cannot be empty"
        raise ValueError(msg)

    await db.execute(text(f"SET LOCAL app.current_guild_id = '{guild_id}'"))

    query = select(GameSession).where(GameSession.guild_id == guild_id)
    if channel_id:
        query = query.where(GameSession.channel_id == channel_id)

    result = await db.execute(query)
    return list(result.scalars().all())


async def create_game(db: AsyncSession, guild_id: str, game_data: dict) -> GameSession:
    """
    Create game with guild_id enforcement.

    Args:
        db: Database session for query execution
        guild_id: Guild ID for the new game (required, cannot be None)
        game_data: Dictionary of game attributes (guild_id will be overridden if present)

    Returns:
        Created GameSession object with guild_id set

    Raises:
        ValueError: If guild_id is empty string
    """
    if not guild_id:
        msg = "guild_id cannot be empty"
        raise ValueError(msg)

    await db.execute(text(f"SET LOCAL app.current_guild_id = '{guild_id}'"))

    data = game_data.copy()
    data["guild_id"] = guild_id

    game = GameSession(**data)
    db.add(game)
    await db.flush()
    return game


async def update_game(db: AsyncSession, guild_id: str, game_id: str, updates: dict) -> GameSession:
    """
    Update game with guild ownership validation.

    Args:
        db: Database session for query execution
        guild_id: Guild ID for isolation (required, cannot be None)
        game_id: Game session ID to update
        updates: Dictionary of attributes to update

    Returns:
        Updated GameSession object

    Raises:
        ValueError: If guild_id or game_id is empty, or game not found in guild
    """
    if not guild_id:
        msg = "guild_id cannot be empty"
        raise ValueError(msg)
    if not game_id:
        msg = "game_id cannot be empty"
        raise ValueError(msg)

    game = await get_game_by_id(db, guild_id, game_id)
    if not game:
        msg = f"Game {game_id} not found in guild {guild_id}"
        raise ValueError(msg)

    for key, value in updates.items():
        setattr(game, key, value)

    await db.flush()
    return game


async def delete_game(db: AsyncSession, guild_id: str, game_id: str) -> None:
    """
    Delete game with guild ownership validation.

    Args:
        db: Database session for query execution
        guild_id: Guild ID for isolation (required, cannot be None)
        game_id: Game session ID to delete

    Raises:
        ValueError: If guild_id or game_id is empty, or game not found in guild
    """
    if not guild_id:
        msg = "guild_id cannot be empty"
        raise ValueError(msg)
    if not game_id:
        msg = "game_id cannot be empty"
        raise ValueError(msg)

    game = await get_game_by_id(db, guild_id, game_id)
    if not game:
        msg = f"Game {game_id} not found in guild {guild_id}"
        raise ValueError(msg)

    await db.delete(game)
    await db.flush()


async def add_participant(
    db: AsyncSession, guild_id: str, game_id: str, user_id: str, data: dict
) -> GameParticipant:
    """
    Add participant to game with guild ownership validation.

    Validates that the game belongs to the specified guild before adding participant.

    Args:
        db: Database session for query execution
        guild_id: Guild ID for isolation (required, cannot be None)
        game_id: Game session ID to add participant to
        user_id: User ID of participant to add
        data: Dictionary of additional participant attributes

    Returns:
        Created GameParticipant object

    Raises:
        ValueError: If guild_id, game_id, or user_id is empty, or game not found in guild
    """
    if not guild_id:
        msg = "guild_id cannot be empty"
        raise ValueError(msg)
    if not game_id:
        msg = "game_id cannot be empty"
        raise ValueError(msg)
    if not user_id:
        msg = "user_id cannot be empty"
        raise ValueError(msg)

    game = await get_game_by_id(db, guild_id, game_id)
    if not game:
        msg = f"Game {game_id} not found in guild {guild_id}"
        raise ValueError(msg)

    data_copy = data.copy()
    data_copy["game_session_id"] = game_id
    data_copy["user_id"] = user_id

    participant = GameParticipant(**data_copy)
    db.add(participant)
    await db.flush()
    return participant


async def remove_participant(db: AsyncSession, guild_id: str, game_id: str, user_id: str) -> None:
    """
    Remove participant from game with guild ownership validation.

    Validates that the game belongs to the specified guild before removing participant.
    Does nothing if participant not found.

    Args:
        db: Database session for query execution
        guild_id: Guild ID for isolation (required, cannot be None)
        game_id: Game session ID to remove participant from
        user_id: User ID of participant to remove

    Raises:
        ValueError: If guild_id, game_id, or user_id is empty, or game not found in guild
    """
    if not guild_id:
        msg = "guild_id cannot be empty"
        raise ValueError(msg)
    if not game_id:
        msg = "game_id cannot be empty"
        raise ValueError(msg)
    if not user_id:
        msg = "user_id cannot be empty"
        raise ValueError(msg)

    game = await get_game_by_id(db, guild_id, game_id)
    if not game:
        msg = f"Game {game_id} not found in guild {guild_id}"
        raise ValueError(msg)

    result = await db.execute(
        select(GameParticipant)
        .where(GameParticipant.game_session_id == game_id)
        .where(GameParticipant.user_id == user_id)
    )
    participant = result.scalar_one_or_none()
    if participant:
        await db.delete(participant)
        await db.flush()


async def list_user_games(db: AsyncSession, guild_id: str, user_id: str) -> list[GameSession]:
    """
    List all games for a user in a guild.

    Joins GameSession and GameParticipant with guild filtering to find all games
    the user is participating in within the specified guild.

    Args:
        db: Database session for query execution
        guild_id: Guild ID for isolation (required, cannot be None)
        user_id: User ID to find games for

    Returns:
        List of GameSession objects the user is participating in

    Raises:
        ValueError: If guild_id or user_id is empty
    """
    if not guild_id:
        msg = "guild_id cannot be empty"
        raise ValueError(msg)
    if not user_id:
        msg = "user_id cannot be empty"
        raise ValueError(msg)

    await db.execute(text(f"SET LOCAL app.current_guild_id = '{guild_id}'"))

    result = await db.execute(
        select(GameSession)
        .join(GameParticipant)
        .where(GameSession.guild_id == guild_id)
        .where(GameParticipant.user_id == user_id)
    )
    return list(result.scalars().all())


async def get_template_by_id(
    db: AsyncSession, guild_id: str, template_id: str
) -> GameTemplate | None:
    """
    Get template by ID with guild isolation enforcement.

    Consolidates 6+ inline select(GameTemplate).where(...) queries identified in duplication audit.

    Args:
        db: Database session for query execution
        guild_id: Guild ID for isolation (required, cannot be None)
        template_id: Template ID to retrieve

    Returns:
        GameTemplate object if found, None otherwise

    Raises:
        ValueError: If guild_id or template_id is empty
    """
    if not guild_id:
        msg = "guild_id cannot be empty"
        raise ValueError(msg)
    if not template_id:
        msg = "template_id cannot be empty"
        raise ValueError(msg)

    await db.execute(text(f"SET LOCAL app.current_guild_id = '{guild_id}'"))

    result = await db.execute(
        select(GameTemplate)
        .where(GameTemplate.id == template_id)
        .where(GameTemplate.guild_id == guild_id)
    )
    return result.scalar_one_or_none()


async def list_templates(db: AsyncSession, guild_id: str) -> list[GameTemplate]:
    """
    List all templates for a guild.

    Consolidates 15+ inline template queries identified in duplication audit including
    queries.get_guild_by_id() + template queries pattern.

    Args:
        db: Database session for query execution
        guild_id: Guild ID for isolation (required, cannot be None)

    Returns:
        List of GameTemplate objects for the guild, ordered by order field

    Raises:
        ValueError: If guild_id is empty
    """
    if not guild_id:
        msg = "guild_id cannot be empty"
        raise ValueError(msg)

    await db.execute(text(f"SET LOCAL app.current_guild_id = '{guild_id}'"))

    result = await db.execute(
        select(GameTemplate).where(GameTemplate.guild_id == guild_id).order_by(GameTemplate.order)
    )
    return list(result.scalars().all())


async def create_template(db: AsyncSession, guild_id: str, template_data: dict) -> GameTemplate:
    """
    Create a new template with guild_id enforcement.

    Forces guild_id on the created entity to prevent accidental cross-guild template creation.

    Args:
        db: Database session for query execution
        guild_id: Guild ID for isolation (required, cannot be None)
        template_data: Dictionary of template attributes (excluding guild_id which is forced)

    Returns:
        Created GameTemplate object

    Raises:
        ValueError: If guild_id is empty
    """
    if not guild_id:
        msg = "guild_id cannot be empty"
        raise ValueError(msg)

    await db.execute(text(f"SET LOCAL app.current_guild_id = '{guild_id}'"))

    # Remove guild_id from template_data if present to avoid duplicate parameter error
    template_data_copy = template_data.copy()
    template_data_copy.pop("guild_id", None)

    template = GameTemplate(**template_data_copy, guild_id=guild_id)
    db.add(template)
    await db.flush()
    return template


async def update_template(
    db: AsyncSession, guild_id: str, template_id: str, updates: dict
) -> GameTemplate:
    """
    Update template with ownership validation.

    Validates template belongs to guild before allowing updates,
    preventing cross-guild modifications.

    Args:
        db: Database session for query execution
        guild_id: Guild ID for isolation (required, cannot be None)
        template_id: Template ID to update
        updates: Dictionary of attributes to update

    Returns:
        Updated GameTemplate object

    Raises:
        ValueError: If guild_id or template_id is empty, or template not found in guild
    """
    if not guild_id:
        msg = "guild_id cannot be empty"
        raise ValueError(msg)
    if not template_id:
        msg = "template_id cannot be empty"
        raise ValueError(msg)

    template = await get_template_by_id(db, guild_id, template_id)
    if not template:
        msg = f"Template {template_id} not found in guild {guild_id}"
        raise ValueError(msg)

    for key, value in updates.items():
        setattr(template, key, value)
    await db.flush()
    return template
