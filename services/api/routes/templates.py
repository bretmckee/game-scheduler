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


"""Game template endpoints."""

# ruff: noqa: B008
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.api import dependencies
from services.api.auth import roles as roles_module
from services.api.database import queries
from services.api.dependencies.discord import get_discord_client
from services.api.services import template_service as template_service_module
from shared import database
from shared.discord import client as discord_client_module
from shared.discord.client import DiscordAPIClient
from shared.models.template import GameTemplate
from shared.schemas import auth as auth_schemas
from shared.schemas import template as template_schemas

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["templates"])


async def build_template_response(
    template: GameTemplate,
    discord_client: DiscordAPIClient,
) -> template_schemas.TemplateResponse:
    """Build TemplateResponse with channel name resolution."""
    channel_name = await discord_client_module.fetch_channel_name_safe(
        template.channel_id, discord_client
    )

    return template_schemas.TemplateResponse(
        id=template.id,
        guild_id=template.guild_id,
        name=template.name,
        description=template.description,
        order=template.order,
        is_default=template.is_default,
        channel_id=template.channel_id,
        channel_name=channel_name,
        notify_role_ids=template.notify_role_ids,
        allowed_player_role_ids=template.allowed_player_role_ids,
        allowed_host_role_ids=template.allowed_host_role_ids,
        max_players=template.max_players,
        expected_duration_minutes=template.expected_duration_minutes,
        reminder_minutes=template.reminder_minutes,
        where=template.where,
        signup_instructions=template.signup_instructions,
        allowed_signup_methods=template.allowed_signup_methods,
        default_signup_method=template.default_signup_method,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat(),
    )


@router.get(
    "/guilds/{guild_id}/templates",
    response_model=list[template_schemas.TemplateListItem],
)
async def list_templates(
    guild_id: str,
    current_user: Annotated[auth_schemas.CurrentUser, Depends(dependencies.auth.get_current_user)],
    db: Annotated[AsyncSession, Depends(database.get_db_with_user_guilds())],
    discord_client: Annotated[DiscordAPIClient, Depends(get_discord_client)],
) -> list[template_schemas.TemplateListItem]:
    """
    List templates for a guild with role-based filtering.

    Templates are filtered by allowed_host_role_ids unless user is guild admin.
    Sorted with default template first, then by order.
    """
    guild_config = await queries.require_guild_by_id(
        db, guild_id, current_user.access_token, current_user.user.discord_id
    )

    # Get templates with permission filtering
    role_service = roles_module.get_role_service()
    template_svc = template_service_module.TemplateService(db)
    templates = await template_svc.get_templates_for_user(
        guild_id,
        current_user.user.discord_id,
        guild_config.guild_id,
        role_service,
        current_user.access_token,
    )

    # Validate that user has access to at least one template
    if not templates:
        # Check if user is admin to provide appropriate error message
        is_admin = await role_service.check_bot_manager_permission(
            current_user.user.discord_id,
            guild_config.guild_id,
            db,
            current_user.access_token,
        )
        if is_admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No templates configured for this server. Please create a template first.",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to perform this operation on this server. "
            "Contact a server manager if you believe this is incorrect.",
        )

    # Convert to response format with channel names
    result = []
    for template in templates:
        channel_name = await discord_client_module.fetch_channel_name_safe(
            template.channel.channel_id, discord_client
        )
        result.append(
            template_schemas.TemplateListItem(
                id=template.id,
                name=template.name,
                description=template.description,
                is_default=template.is_default,
                channel_id=template.channel_id,
                channel_name=channel_name,
                notify_role_ids=template.notify_role_ids,
                allowed_player_role_ids=template.allowed_player_role_ids,
                allowed_host_role_ids=template.allowed_host_role_ids,
                max_players=template.max_players,
                expected_duration_minutes=template.expected_duration_minutes,
                reminder_minutes=template.reminder_minutes,
                where=template.where,
                signup_instructions=template.signup_instructions,
                allowed_signup_methods=template.allowed_signup_methods,
                default_signup_method=template.default_signup_method,
            )
        )

    return result


@router.get("/templates/{template_id}", response_model=template_schemas.TemplateResponse)
async def get_template(
    template_id: str,
    current_user: Annotated[auth_schemas.CurrentUser, Depends(dependencies.auth.get_current_user)],
    db: Annotated[AsyncSession, Depends(database.get_db_with_user_guilds())],
    discord_client: Annotated[DiscordAPIClient, Depends(get_discord_client)],
) -> template_schemas.TemplateResponse:
    """Get template details by ID."""
    template_svc = template_service_module.TemplateService(db)
    template = await template_svc.get_template_by_id(template_id)

    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    # Verify guild membership - returns 404 if not member to prevent info disclosure
    template = await dependencies.permissions.verify_template_access(
        template, current_user.user.discord_id, current_user.access_token, db
    )

    return await build_template_response(template, discord_client)


@router.post(
    "/guilds/{guild_id}/templates",
    response_model=template_schemas.TemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_template(
    guild_id: str,
    request: template_schemas.TemplateCreateRequest,
    current_user: Annotated[auth_schemas.CurrentUser, Depends(dependencies.auth.get_current_user)],
    db: Annotated[AsyncSession, Depends(database.get_db_with_user_guilds())],
    discord_client: Annotated[DiscordAPIClient, Depends(get_discord_client)],
) -> template_schemas.TemplateResponse:
    """Create new template (requires bot manager role)."""
    await queries.require_guild_by_id(
        db, guild_id, current_user.access_token, current_user.user.discord_id
    )

    # Verify bot manager permission using dependency
    role_service = roles_module.get_role_service()
    await dependencies.permissions.require_bot_manager(guild_id, current_user, role_service, db)

    template_svc = template_service_module.TemplateService(db)
    template = await template_svc.create_template(
        guild_id=guild_id,
        channel_id=request.channel_id,
        name=request.name,
        description=request.description,
        order=request.order,
        is_default=request.is_default,
        notify_role_ids=request.notify_role_ids,
        allowed_player_role_ids=request.allowed_player_role_ids,
        allowed_host_role_ids=request.allowed_host_role_ids,
        max_players=request.max_players,
        expected_duration_minutes=request.expected_duration_minutes,
        reminder_minutes=request.reminder_minutes,
        where=request.where,
        signup_instructions=request.signup_instructions,
    )

    return await build_template_response(template, discord_client)


@router.put("/templates/{template_id}", response_model=template_schemas.TemplateResponse)
async def update_template(
    template_id: str,
    request: template_schemas.TemplateUpdateRequest,
    current_user: Annotated[auth_schemas.CurrentUser, Depends(dependencies.auth.get_current_user)],
    db: Annotated[AsyncSession, Depends(database.get_db_with_user_guilds())],
    discord_client: Annotated[DiscordAPIClient, Depends(get_discord_client)],
) -> template_schemas.TemplateResponse:
    """Update template (requires bot manager role)."""
    template_svc = template_service_module.TemplateService(db)
    template = await template_svc.get_template_by_id(template_id)

    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    # Verify bot manager permission using dependency
    role_service = roles_module.get_role_service()
    await dependencies.permissions.require_bot_manager(
        template.guild_id, current_user, role_service, db
    )

    # Update template
    updated_template = await template_svc.update_template(
        template,
        **request.model_dump(exclude_unset=True),
    )

    return await build_template_response(updated_template, discord_client)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: str,
    current_user: Annotated[auth_schemas.CurrentUser, Depends(dependencies.auth.get_current_user)],
    db: Annotated[AsyncSession, Depends(database.get_db_with_user_guilds())],
) -> None:
    """Delete template (requires bot manager role, cannot delete is_default)."""
    template_svc = template_service_module.TemplateService(db)
    template = await template_svc.get_template_by_id(template_id)

    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    # Verify bot manager permission using dependency
    role_service = roles_module.get_role_service()
    await dependencies.permissions.require_bot_manager(
        template.guild_id, current_user, role_service, db
    )

    # Prevent deleting default template
    if template.is_default:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the default template",
        )

    await template_svc.delete_template(template_id)


@router.post(
    "/templates/{template_id}/set-default",
    response_model=template_schemas.TemplateResponse,
)
async def set_default_template(
    template_id: str,
    current_user: Annotated[auth_schemas.CurrentUser, Depends(dependencies.auth.get_current_user)],
    db: Annotated[AsyncSession, Depends(database.get_db_with_user_guilds())],
    discord_client: Annotated[DiscordAPIClient, Depends(get_discord_client)],
) -> template_schemas.TemplateResponse:
    """Set template as default (requires bot manager role)."""
    template_svc = template_service_module.TemplateService(db)
    template = await template_svc.get_template_by_id(template_id)

    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    # Verify bot manager permission using dependency
    role_service = roles_module.get_role_service()
    await dependencies.permissions.require_bot_manager(
        template.guild_id, current_user, role_service, db
    )

    updated_template = await template_svc.set_default(template_id)

    return await build_template_response(updated_template, discord_client)


@router.post("/templates/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_templates(
    request: template_schemas.TemplateReorderRequest,
    current_user: Annotated[auth_schemas.CurrentUser, Depends(dependencies.auth.get_current_user)],
    db: Annotated[AsyncSession, Depends(database.get_db_with_user_guilds())],
) -> None:
    """Bulk reorder templates (requires bot manager role)."""
    if not request.template_orders:
        return

    # Extract template IDs from template_orders
    template_ids = [next(iter(item.keys())) for item in request.template_orders]

    # Get first template to check guild and permissions
    template_svc = template_service_module.TemplateService(db)
    first_template = await template_svc.get_template_by_id(template_ids[0])

    if not first_template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    # Verify bot manager permission using dependency
    role_service = roles_module.get_role_service()
    await dependencies.permissions.require_bot_manager(
        first_template.guild_id, current_user, role_service, db
    )

    await template_svc.reorder_templates(request.template_orders)
