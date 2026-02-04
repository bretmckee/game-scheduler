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


"""Channel configuration endpoints."""

# ruff: noqa: B008
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.api import dependencies
from services.api.database import queries
from services.api.dependencies import permissions
from services.api.services import channel_service
from shared import database
from shared.discord import client as discord_client_module
from shared.models.channel import ChannelConfiguration
from shared.schemas import auth as auth_schemas
from shared.schemas import channel as channel_schemas

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/channels", tags=["channels"])


async def _build_channel_config_response(
    channel_config: ChannelConfiguration,
) -> channel_schemas.ChannelConfigResponse:
    """Build channel configuration response with channel name."""
    channel_name = await discord_client_module.fetch_channel_name_safe(channel_config.channel_id)
    return channel_schemas.ChannelConfigResponse(
        id=channel_config.id,
        guild_id=channel_config.guild_id,
        guild_discord_id=channel_config.guild.guild_id,
        channel_id=channel_config.channel_id,
        channel_name=channel_name,
        is_active=channel_config.is_active,
        created_at=channel_config.created_at.isoformat(),
        updated_at=channel_config.updated_at.isoformat(),
    )


@router.get("/{channel_id}", response_model=channel_schemas.ChannelConfigResponse)
async def get_channel(
    channel_id: str,
    current_user: Annotated[auth_schemas.CurrentUser, Depends(dependencies.auth.get_current_user)],
    db: Annotated[AsyncSession, Depends(database.get_db)],
) -> channel_schemas.ChannelConfigResponse:
    """
    Get channel configuration by database UUID.

    Requires user to be member of the parent guild.
    """

    channel_config = await queries.get_channel_by_id(db, channel_id)

    if not channel_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel configuration not found",
        )

    # Verify guild membership, returns 404 if not member to prevent information disclosure
    await permissions.verify_guild_membership(channel_config.guild.guild_id, current_user, db)

    return await _build_channel_config_response(channel_config)


@router.post(
    "",
    response_model=channel_schemas.ChannelConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_channel_config(
    request: channel_schemas.ChannelConfigCreateRequest,
    _current_user: Annotated[
        auth_schemas.CurrentUser, Depends(permissions.require_manage_channels)
    ],
    db: Annotated[AsyncSession, Depends(database.get_db)],
) -> channel_schemas.ChannelConfigResponse:
    """
    Create channel configuration.

    Requires MANAGE_CHANNELS permission in the guild.
    """
    existing = await queries.get_channel_by_discord_id(db, request.channel_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Channel configuration already exists",
        )

    channel_config = await channel_service.create_channel_config(
        db,
        guild_id=request.guild_id,
        channel_discord_id=request.channel_id,
        is_active=request.is_active,
    )

    return await _build_channel_config_response(channel_config)


@router.put("/{channel_id}", response_model=channel_schemas.ChannelConfigResponse)
async def update_channel_config(
    channel_id: str,
    request: channel_schemas.ChannelConfigUpdateRequest,
    _current_user: Annotated[
        auth_schemas.CurrentUser, Depends(permissions.require_manage_channels)
    ],
    db: Annotated[AsyncSession, Depends(database.get_db)],
) -> channel_schemas.ChannelConfigResponse:
    """
    Update channel configuration.

    Requires MANAGE_CHANNELS permission in the guild.
    """
    channel_config = await queries.get_channel_by_id(db, channel_id)
    if not channel_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel configuration not found",
        )

    updates = request.model_dump(exclude_unset=True)
    channel_config = await channel_service.update_channel_config(channel_config, **updates)

    return await _build_channel_config_response(channel_config)
