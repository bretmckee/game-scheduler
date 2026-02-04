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


"""Template service for game template CRUD operations."""

from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from services.api.auth import roles as roles_module
from shared.models.template import GameTemplate


class TemplateService:
    """Service for managing game templates."""

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize template service.

        Args:
            db: Database session
        """
        self.db = db

    async def get_templates_for_user(
        self,
        guild_id: str,
        user_id: str,
        discord_guild_id: str,
        role_service: roles_module.RoleVerificationService,
        access_token: str | None = None,
    ) -> list[GameTemplate]:
        """
        Get templates user can access, sorted for dropdown.

        Templates are sorted with default first, then by order.
        Non-admin users only see templates they have access to based on
        allowed_host_role_ids.

        Args:
            guild_id: Guild UUID (database ID)
            user_id: Discord user ID
            discord_guild_id: Discord guild ID (snowflake)
            role_service: Role service for permission checking
            access_token: User's Discord access token

        Returns:
            List of accessible templates
        """
        result = await self.db.execute(
            select(GameTemplate)
            .where(GameTemplate.guild_id == guild_id)
            .options(selectinload(GameTemplate.channel))
            .order_by(
                GameTemplate.is_default.desc(),
                GameTemplate.order.asc(),
            )
        )
        all_templates = list(result.scalars().all())

        # Filter templates using centralized permission check
        templates = []
        for template in all_templates:
            can_host = await role_service.check_game_host_permission(
                user_id,
                discord_guild_id,
                self.db,
                template.allowed_host_role_ids,
                access_token,
            )
            if can_host:
                templates.append(template)

        return templates

    async def get_template_by_id(self, template_id: str) -> GameTemplate | None:
        """
        Get template by ID.

        Args:
            template_id: Template UUID

        Returns:
            Template or None if not found
        """
        result = await self.db.execute(
            select(GameTemplate)
            .where(GameTemplate.id == template_id)
            .options(selectinload(GameTemplate.channel))
        )
        return result.scalar_one_or_none()

    async def create_template(
        self,
        guild_id: str,
        channel_id: str,
        name: str,
        **fields: Any,  # noqa: ANN401
    ) -> GameTemplate:
        """
        Create new template.

        Does not commit. Caller must commit transaction.

        Args:
            guild_id: Guild UUID
            channel_id: Channel UUID
            name: Template name
            **fields: Additional template fields

        Returns:
            Created template
        """
        template = GameTemplate(
            guild_id=guild_id,
            channel_id=channel_id,
            name=name,
            **fields,
        )
        self.db.add(template)
        await self.db.flush()
        return template

    async def create_default_template(self, guild_id: str, channel_id: str) -> GameTemplate:
        """
        Create default template for guild initialization.

        Does not commit. Caller must commit transaction.

        Args:
            guild_id: Guild UUID
            channel_id: Channel UUID for default template

        Returns:
            Created default template
        """
        template = GameTemplate(
            guild_id=guild_id,
            name="Default",
            description="Default game template",
            is_default=True,
            channel_id=channel_id,
            order=0,
        )
        self.db.add(template)
        await self.db.flush()
        return template

    async def update_template(
        self,
        template: GameTemplate,
        **updates: Any,  # noqa: ANN401
    ) -> GameTemplate:
        """
        Update template.

        Does not commit. Caller must commit transaction.

        Args:
            template: Existing template
            **updates: Fields to update (only non-None values are applied)

        Returns:
            Updated template
        """
        for key, value in updates.items():
            if value is not None:
                setattr(template, key, value)

        return template

    async def set_default(self, template_id: str) -> GameTemplate:
        """
        Set template as default, unsetting others in the same guild.

        Does not commit. Caller must commit transaction.

        Args:
            template_id: Template UUID to set as default

        Returns:
            Updated template

        Raises:
            ValueError: If template not found
        """
        result = await self.db.execute(
            select(GameTemplate)
            .where(GameTemplate.id == template_id)
            .options(selectinload(GameTemplate.channel))
        )
        template = result.scalar_one_or_none()
        if not template:
            msg = f"Template not found: {template_id}"
            raise ValueError(msg)

        await self.db.execute(
            update(GameTemplate)
            .where(
                GameTemplate.guild_id == template.guild_id,
                GameTemplate.id != template_id,
            )
            .values(is_default=False)
        )

        template.is_default = True
        return template

    async def delete_template(self, template_id: str) -> None:
        """
        Delete template.

        Does not commit. Caller must commit transaction.

        Args:
            template_id: Template UUID to delete

        Raises:
            ValueError: If template not found or is default template
        """
        result = await self.db.execute(select(GameTemplate).where(GameTemplate.id == template_id))
        template = result.scalar_one_or_none()
        if not template:
            msg = f"Template not found: {template_id}"
            raise ValueError(msg)

        if template.is_default:
            msg = "Cannot delete the default template"
            raise ValueError(msg)

        await self.db.delete(template)

    async def reorder_templates(self, template_orders: list[dict[str, int]]) -> list[GameTemplate]:
        """
        Bulk reorder templates.

        Does not commit. Caller must commit transaction.

        Args:
            template_orders: List of dicts with template_id and order

        Returns:
            List of updated templates
        """
        templates = []
        for item in template_orders:
            template_id = item.get("template_id")
            order = item.get("order")

            if template_id is None or order is None:
                continue

            result = await self.db.execute(
                select(GameTemplate)
                .where(GameTemplate.id == template_id)
                .options(selectinload(GameTemplate.channel))
            )
            template = result.scalar_one_or_none()
            if template:
                template.order = order
                templates.append(template)

        return templates
