<!-- markdownlint-disable-file -->

# Task Research Notes: Game Template System

## Research Executed

### File Analysis

- `shared/models/guild.py`
  - Current inheritance fields: `default_max_players`, `default_reminder_minutes`, `allowed_host_role_ids`
  - Non-template fields to preserve: `bot_manager_role_ids`, `require_host_role`
  - Docstring references inheritance hierarchy
- `shared/models/channel.py`
  - Current inheritance fields: `max_players`, `reminder_minutes`, `allowed_host_role_ids`
  - Non-template field to preserve: `is_active` (boolean toggle for channel selection in template creation)
  - Has `game_category` field (will be removed, replaced by template name)
  - After inheritance removal, channel config becomes very simple (just is_active flag)
- `shared/models/game.py`
  - Current fields that can be overridden: `max_players`, `reminder_minutes`
  - Existing fields: `notify_role_ids`, `expected_duration_minutes`, `where`, `signup_instructions`
  - No `allowed_player_role_ids` currently (NEW field needed)
- `services/api/services/config.py`
  - `SettingsResolver` class with three methods: `resolve_max_players`, `resolve_reminder_minutes`, `resolve_allowed_host_roles`
  - Used throughout game creation and join logic
  - Implements game > channel > guild > default hierarchy

### Code Search Results

- `SettingsResolver` usage found in:
  - `services/api/services/games.py` - create_game() and join_game()
  - `services/bot/auth/role_checker.py` - check_game_host_permission()
  - `services/api/auth/roles.py` - check_game_host_permission()
- `ConfigurationService` CRUD operations used in:
  - `services/api/routes/guilds.py` - create_guild_config(), update_guild_config(), get_guild_by_id(), get_guild_by_discord_id()
  - `services/api/routes/channels.py` - create_channel_config(), update_channel_config(), get_channel_by_id(), get_channel_by_discord_id()
  - All route files instantiate: `service = ConfigurationService(db)` then call methods
- Inheritance display in frontend:
  - `frontend/src/pages/ChannelConfig.tsx` - InheritancePreview component
  - `frontend/src/pages/GuildConfig.tsx` - Settings descriptions mention inheritance
  - `frontend/src/pages/GuildDashboard.tsx` - Channel display shows inherited settings
- Bot commands with inheritance:
  - `services/bot/commands/config_guild.py` - Sets guild defaults (will be REMOVED - bot_manager_roles moved to web UI, guilds created via manual sync)
  - `services/bot/commands/config_channel.py` - Sets channel overrides (will be REMOVED entirely - only `is_active` left, moved to web UI)
  - Note: Bot does NOT have game creation commands - games are created only via web UI

### External Research

- #githubRepo:"sqlalchemy/sqlalchemy index foreign key composite unique constraint"

  - Composite unique constraints using `UniqueConstraint` in table args
  - Index creation for query optimization: `Index('idx_name', column1, column2)`
  - Foreign key constraints with `ForeignKey` and proper cascade rules
  - Example pattern:
    ```python
    __table_args__ = (
        Index('ix_guild_order', 'guild_id', 'order'),
        UniqueConstraint('guild_id', 'name', name='uq_guild_template_name'),
    )
    ```

- #githubRepo:"discord/discord-api-docs role permissions"
  - Discord role IDs are snowflake strings (64-bit integers as strings)
  - Roles stored as arrays in database, checked via membership
  - Permission hierarchy: Administrator > Manage Guild > Manage Channels
  - Example role check pattern:
    ```python
    user_role_ids = await get_user_roles(user_id, guild_id)
    allowed = any(role_id in allowed_role_ids for role_id in user_role_ids)
    ```

### Project Conventions

- Standards referenced: Python type hints with `Mapped[]`, SQLAlchemy 2.0 declarative syntax
- Instructions followed: `.github/instructions/python.instructions.md`, `.github/instructions/coding-best-practices.instructions.md`
- Database migration pattern: Alembic with numbered migrations in `alembic/versions/`
- Service layer pattern: Separation of models, schemas, services, and routes
- Code organization: Simple database queries in `services/api/database/queries.py`, business logic (CRUD with validation) in `services/api/services/*.py`
- Test mocking: Tests mock specific functions not classes, e.g., `patch("services.api.database.queries.get_guild_by_id")` not `patch("ConfigurationService")`

## Key Discoveries

### ConfigurationService CRUD Operations

The deleted `ConfigurationService` class contained both simple database queries AND business logic operations:

**Read Operations (Simple Queries):**

```python
async def get_guild_by_id(db, guild_id: str) -> GuildConfiguration | None
async def get_guild_by_discord_id(db, guild_discord_id: str) -> GuildConfiguration | None
async def get_channel_by_id(db, channel_id: str) -> ChannelConfiguration | None
async def get_channel_by_discord_id(db, channel_discord_id: str) -> ChannelConfiguration | None
async def get_channels_by_guild(db, guild_id: str) -> list[ChannelConfiguration]
```

These are now in `services/api/database/queries.py` (completed).

**Create/Update Operations (Business Logic):**

```python
async def create_guild_config(db, guild_discord_id: str, **settings) -> GuildConfiguration:
    """Creates GuildConfiguration with guild_id=guild_discord_id, adds to session, commits, refreshes."""
    guild_config = GuildConfiguration(guild_id=guild_discord_id, **settings)
    db.add(guild_config)
    await db.commit()
    await db.refresh(guild_config)
    return guild_config

async def update_guild_config(db, guild_config: GuildConfiguration, **updates) -> GuildConfiguration:
    """Updates fields where value is not None, commits, refreshes."""
    for key, value in updates.items():
        if value is not None:
            setattr(guild_config, key, value)
    await db.commit()
    await db.refresh(guild_config)
    return guild_config

async def create_channel_config(db, guild_id: str, channel_discord_id: str, **settings) -> ChannelConfiguration:
    """Creates ChannelConfiguration with channel_id=channel_discord_id, adds to session, commits, refreshes."""
    channel_config = ChannelConfiguration(guild_id=guild_id, channel_id=channel_discord_id, **settings)
    db.add(channel_config)
    await db.commit()
    await db.refresh(channel_config)
    return channel_config

async def update_channel_config(db, channel_config: ChannelConfiguration, **updates) -> ChannelConfiguration:
    """Updates fields where value is not None, commits, refreshes."""
    for key, value in updates.items():
        if value is not None:
            setattr(channel_config, key, value)
    await db.commit()
    await db.refresh(channel_config)
    return channel_config
```

**Current Problem:**

- Routes still call `service.create_guild_config()` and `service.update_guild_config()` but `service` is undefined
- These need to be moved to either:
  1. New `services/api/services/guild_service.py` and `services/api/services/channel_service.py` (recommended - keeps business logic separate)
  2. Added to `services/api/database/queries.py` (not recommended - mixes concerns)
  3. Inlined in route handlers (not recommended - hard to test)

**Routes Affected:**

- `services/api/routes/guilds.py`: Lines 166 (create_guild_config), 217 (update_guild_config)
- `services/api/routes/channels.py`: Lines 127 (create_channel_config), 175 (update_channel_config)

**Tests Affected:**

- `tests/services/api/routes/test_guilds.py`: 11 tests fail due to missing mocks for create/update operations
  - Test mocks reference `mock_create_guild` and `mock_get_guild_by_discord_id` which don't match current patches
  - Need to add patches for the new service functions once created

### Current Inheritance System Architecture

**Database Schema:**

```python
# Guild Model - Minimal configuration after template migration
class GuildConfiguration:
    bot_manager_role_ids: list[str] | None  # Who can manage templates
    require_host_role: bool  # Whether host role is required (not exposed in bot command)

# Channel Model - Minimal configuration
class ChannelConfiguration:
    is_active: bool  # Only remaining field after template migration

# Game Model - Final override
class GameSession:
    max_players: int | None  # Override channel/guild
    reminder_minutes: list[int] | None  # Override channel/guild
    # No host role override at game level
```

**Resolution Logic:**

```python
class SettingsResolver:
    def resolve_max_players(game, channel, guild) -> int:
        # Game > Channel > Guild > Default (10)
        if game and game.max_players is not None:
            return game.max_players
        if channel and channel.max_players is not None:
            return channel.max_players
        if guild and guild.default_max_players is not None:
            return guild.default_max_players
        return 10

    def resolve_reminder_minutes(game, channel, guild) -> list[int]:
        # Game > Channel > Guild > Default ([60, 15])
        if game and game.reminder_minutes is not None:
            return game.reminder_minutes
        if channel and channel.reminder_minutes is not None:
            return channel.reminder_minutes
        if guild and guild.default_reminder_minutes is not None:
            return guild.default_reminder_minutes
        return [60, 15]

    def resolve_allowed_host_roles(channel, guild) -> list[str]:
        # Channel > Guild > Default ([])
        if channel and channel.allowed_host_role_ids is not None:
            return channel.allowed_host_role_ids
        if guild and guild.allowed_host_role_ids is not None:
            return guild.allowed_host_role_ids
        return []
```

**Usage Locations:**

1. **Game Creation** (`services/api/services/games.py:create_game`)
   - Resolves max_players and reminder_minutes before saving game
   - Inline resolution without using SettingsResolver class
2. **Game Join** (`services/api/services/games.py:join_game`)
   - Uses SettingsResolver to check max_players capacity
3. **Authorization** (`services/api/auth/roles.py`, `services/bot/auth/role_checker.py`)
   - Uses resolve_allowed_host_roles for permission checks
4. **Frontend Display** (`frontend/src/pages/ChannelConfig.tsx`, `frontend/src/pages/GuildConfig.tsx`)
   - Shows inherited values with "inherited from guild" indicators
5. **Bot Commands** (`services/bot/commands/config_channel.py`)
   - Displays resolved settings in embeds

**Test Coverage:**

- `tests/services/api/services/test_config.py` - 12 test methods for SettingsResolver
- Tests verify each level of inheritance and system defaults

### Template System Requirements

**Design Summary:**

Templates represent **game types** (e.g., "D&D Campaign", "Board Game Night") and provide two categories of settings:

1. **Locked Settings** (manager-only, host cannot edit):

   - `channel_id` - Which channel games are posted to
   - `notify_role_ids` - Roles to notify when game created
   - `allowed_player_role_ids` - Roles allowed to join (NEW)
   - `allowed_host_role_ids` - Roles allowed to use this template

2. **Pre-populated Settings** (host-editable defaults):
   - `max_players`
   - `expected_duration_minutes`
   - `reminder_minutes`
   - `where`
   - `signup_instructions`

**Key Constraints:**

- Templates associated with guild only (not channel)
- Host must select a template (no template-free game creation)
- Templates only visible to users with matching `allowed_host_role_ids`
- When guild created, auto-create "Default" template with `is_default=True`
- The `is_default` template cannot be deleted (ensures at least one template exists)
- Only one template per guild can be marked `is_default`
- Templates have `order` field for sorting in dropdown
- Dropdown sorted: default first, then by order

### Complete Examples

**GameTemplate Model:**

```python
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, generate_uuid, utc_now

if TYPE_CHECKING:
    from .guild import GuildConfiguration
    from .channel import ChannelConfiguration
    from .game import GameSession

class GameTemplate(Base):
    """
    Game template defines game type with locked and pre-populated settings.

    Templates are guild-scoped and represent game types (e.g., "D&D Campaign").
    Host selects template at game creation. Locked fields cannot be changed by host,
    while pre-populated fields provide defaults that host can edit.
    """

    __tablename__ = "game_templates"

    # Identity & Metadata
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    guild_id: Mapped[str] = mapped_column(ForeignKey("guild_configurations.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now)

    # Locked Fields (manager-only, host cannot edit)
    channel_id: Mapped[str] = mapped_column(ForeignKey("channel_configurations.id"))
    notify_role_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    allowed_player_role_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    allowed_host_role_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # Pre-populated Fields (host-editable defaults)
    max_players: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expected_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reminder_minutes: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    where: Mapped[str | None] = mapped_column(Text, nullable=True)
    signup_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    guild: Mapped["GuildConfiguration"] = relationship("GuildConfiguration", back_populates="templates")
    channel: Mapped["ChannelConfiguration"] = relationship("ChannelConfiguration")
    games: Mapped[list["GameSession"]] = relationship("GameSession", back_populates="template")

    # Constraints and Indexes
    __table_args__ = (
        Index('ix_game_templates_guild_order', 'guild_id', 'order'),
        Index('ix_game_templates_guild_default', 'guild_id', 'is_default'),
        CheckConstraint('order >= 0', name='ck_template_order_positive'),
    )

    def __repr__(self) -> str:
        return f"<GameTemplate(id={self.id}, name={self.name}, guild_id={self.guild_id})>"
```

**Updated GameSession Model:**

```python
# Add to GameSession model
template_id: Mapped[str] = mapped_column(ForeignKey("game_templates.id"))
allowed_player_role_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

# Add relationship
template: Mapped["GameTemplate"] = relationship("GameTemplate", back_populates="games")
```

**Template Service:**

```python
class TemplateService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_templates_for_user(
        self,
        guild_id: str,
        user_role_ids: list[str],
        is_admin: bool = False
    ) -> list[GameTemplate]:
        """Get templates user can access, sorted for dropdown."""
        result = await self.db.execute(
            select(GameTemplate)
            .where(GameTemplate.guild_id == guild_id)
            .order_by(
                GameTemplate.is_default.desc(),  # Default first
                GameTemplate.order.asc()         # Then by order
            )
        )
        templates = list(result.scalars().all())

        # Filter by allowed_host_role_ids
        if not is_admin:
            templates = [
                t for t in templates
                if not t.allowed_host_role_ids  # Empty = anyone
                or any(role_id in t.allowed_host_role_ids for role_id in user_role_ids)
            ]

        return templates

    async def create_default_template(self, guild_id: str, channel_id: str) -> GameTemplate:
        """Create default template when guild is added."""
        template = GameTemplate(
            guild_id=guild_id,
            name="Default",
            description="Default game template",
            is_default=True,
            channel_id=channel_id,
            order=0,
        )
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def set_default(self, template_id: str) -> GameTemplate:
        """Set a template as default, unsetting others."""
        template = await self.db.get(GameTemplate, template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        # Unset other defaults in same guild
        await self.db.execute(
            update(GameTemplate)
            .where(
                GameTemplate.guild_id == template.guild_id,
                GameTemplate.id != template_id
            )
            .values(is_default=False)
        )

        template.is_default = True
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def delete_template(self, template_id: str) -> None:
        """Delete template. Cannot delete is_default template."""
        template = await self.db.get(GameTemplate, template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        if template.is_default:
            raise ValueError("Cannot delete the default template")

        await self.db.delete(template)
        await self.db.commit()
```

**Game Creation with Templates:**

```python
# services/api/services/games.py
async def create_game(
    self,
    game_data: GameCreateRequest,
    host_user_id: str,
    access_token: str,
) -> GameSession:
    # Fetch template
    template = await self.db.get(GameTemplate, game_data.template_id)
    if not template:
        raise ValueError(f"Template not found: {game_data.template_id}")

    # Verify user can use this template
    user_role_ids = await self.role_service.get_user_role_ids(...)
    if template.allowed_host_role_ids:
        if not any(role_id in template.allowed_host_role_ids for role_id in user_role_ids):
            raise PermissionError("User does not have required role for this template")

    # Create game with locked fields from template
    game = GameSession(
        template_id=template.id,
        guild_id=template.guild_id,
        channel_id=template.channel_id,  # Locked by template
        notify_role_ids=template.notify_role_ids,  # Locked by template
        allowed_player_role_ids=template.allowed_player_role_ids,  # Locked by template

        # Host-editable fields (use template defaults if not provided)
        max_players=game_data.max_players or template.max_players,
        expected_duration_minutes=game_data.expected_duration_minutes or template.expected_duration_minutes,
        reminder_minutes=game_data.reminder_minutes or template.reminder_minutes,
        where=game_data.where or template.where,
        signup_instructions=game_data.signup_instructions or template.signup_instructions,

        # Always host-controlled
        title=game_data.title,
        description=game_data.description,
        scheduled_at=game_data.scheduled_at,
        host_id=host_user_id,
    )

    self.db.add(game)
    await self.db.commit()
    return game
```

### API and Schema Documentation

**Template Schemas:**

```python
# shared/schemas/template.py
from pydantic import BaseModel, Field

class TemplateCreateRequest(BaseModel):
    """Create game template."""
    guild_id: str = Field(..., description="Guild UUID")
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, description="Template description")
    order: int = Field(default=0, ge=0)
    is_default: bool = Field(default=False)

    # Locked fields
    channel_id: str = Field(..., description="Channel UUID")
    notify_role_ids: list[str] | None = None
    allowed_player_role_ids: list[str] | None = None
    allowed_host_role_ids: list[str] | None = None

    # Pre-populated fields
    max_players: int | None = Field(None, ge=1, le=100)
    expected_duration_minutes: int | None = Field(None, ge=1)
    reminder_minutes: list[int] | None = None
    where: str | None = None
    signup_instructions: str | None = None

class TemplateResponse(BaseModel):
    """Template response."""
    id: str
    guild_id: str
    name: str
    description: str | None
    order: int
    is_default: bool

    # Locked fields
    channel_id: str
    channel_name: str  # Resolved from Discord
    notify_role_ids: list[str] | None
    allowed_player_role_ids: list[str] | None
    allowed_host_role_ids: list[str] | None

    # Pre-populated fields
    max_players: int | None
    expected_duration_minutes: int | None
    reminder_minutes: list[int] | None
    where: str | None
    signup_instructions: str | None

    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}

class TemplateListItem(BaseModel):
    """Template list item for dropdown."""
    id: str
    name: str
    description: str | None
    is_default: bool
    channel_name: str

    model_config = {"from_attributes": True}
```

**Updated Game Schemas:**

```python
# shared/schemas/game.py
class GameCreateRequest(BaseModel):
    """Create game with template."""
    template_id: str = Field(..., description="Template UUID")

    # Always required
    title: str = Field(..., min_length=1, max_length=200)
    scheduled_at: datetime

    # Optional overrides of template defaults
    description: str | None = None
    max_players: int | None = Field(None, ge=1, le=100)
    expected_duration_minutes: int | None = Field(None, ge=1)
    reminder_minutes: list[int] | None = None
    where: str | None = None
    signup_instructions: str | None = None
    initial_participants: list[ParticipantInput] | None = None
```

### Configuration Examples

**Combined Migration (Remove Inheritance + Add Templates):**

```python
# alembic/versions/018_replace_inheritance_with_templates.py
def upgrade() -> None:
    # STEP 1: Remove inheritance fields from guild_configurations
    op.drop_column('guild_configurations', 'default_max_players')
    op.drop_column('guild_configurations', 'default_reminder_minutes')
    op.drop_column('guild_configurations', 'allowed_host_role_ids')

    # STEP 2: Remove inheritance fields from channel_configurations
    op.drop_column('channel_configurations', 'max_players')
    op.drop_column('channel_configurations', 'reminder_minutes')
    op.drop_column('channel_configurations', 'allowed_host_role_ids')
    op.drop_column('channel_configurations', 'game_category')

    # STEP 3: Create game_templates table
    op.create_table(
        'game_templates',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('guild_id', sa.String(36), sa.ForeignKey('guild_configurations.id'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),

        # Locked fields
        sa.Column('channel_id', sa.String(36), sa.ForeignKey('channel_configurations.id'), nullable=False),
        sa.Column('notify_role_ids', sa.JSON(), nullable=True),
        sa.Column('allowed_player_role_ids', sa.JSON(), nullable=True),
        sa.Column('allowed_host_role_ids', sa.JSON(), nullable=True),

        # Pre-populated fields
        sa.Column('max_players', sa.Integer(), nullable=True),
        sa.Column('expected_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('reminder_minutes', sa.JSON(), nullable=True),
        sa.Column('where', sa.Text(), nullable=True),
        sa.Column('signup_instructions', sa.Text(), nullable=True),

        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # STEP 4: Create indexes for templates
    op.create_index('ix_game_templates_guild_id', 'game_templates', ['guild_id'])
    op.create_index('ix_game_templates_guild_order', 'game_templates', ['guild_id', 'order'])
    op.create_index('ix_game_templates_guild_default', 'game_templates', ['guild_id', 'is_default'])

    # STEP 5: Add template_id to game_sessions
    op.add_column('game_sessions', sa.Column('template_id', sa.String(36), sa.ForeignKey('game_templates.id'), nullable=True))
    op.add_column('game_sessions', sa.Column('allowed_player_role_ids', sa.JSON(), nullable=True))
    op.create_index('ix_game_sessions_template_id', 'game_sessions', ['template_id'])

    # STEP 6: Create default template for each guild
    # Note: This needs to be done via data migration script, not in migration
    # See data_migration_create_default_templates.py

def downgrade() -> None:
    # Remove template system
    op.drop_index('ix_game_sessions_template_id', 'game_sessions')
    op.drop_column('game_sessions', 'allowed_player_role_ids')
    op.drop_column('game_sessions', 'template_id')
    op.drop_table('game_templates')

    # Restore inheritance fields
    op.add_column('guild_configurations', sa.Column('default_max_players', sa.Integer(), nullable=True))
    op.add_column('guild_configurations', sa.Column('default_reminder_minutes', sa.JSON(), nullable=True))
    op.add_column('guild_configurations', sa.Column('allowed_host_role_ids', sa.JSON(), nullable=True))

    op.add_column('channel_configurations', sa.Column('max_players', sa.Integer(), nullable=True))
    op.add_column('channel_configurations', sa.Column('reminder_minutes', sa.JSON(), nullable=True))
    op.add_column('channel_configurations', sa.Column('allowed_host_role_ids', sa.JSON(), nullable=True))
    op.add_column('channel_configurations', sa.Column('game_category', sa.String(50), nullable=True))
```

**Data Migration Script:**

```python
# scripts/data_migration_create_default_templates.py
"""
Create default template for each guild after migration 018.
Run with: uv run python scripts/data_migration_create_default_templates.py
"""
import asyncio
from sqlalchemy import select
from shared.database import get_async_session
from shared.models.guild import GuildConfiguration
from shared.models.channel import ChannelConfiguration
from shared.models.template import GameTemplate
from datetime import datetime

async def create_default_templates():
    async with get_async_session() as db:
        # Get all guilds
        result = await db.execute(select(GuildConfiguration))
        guilds = result.scalars().all()

        for guild in guilds:
            # Check if default template already exists
            existing = await db.execute(
                select(GameTemplate)
                .where(
                    GameTemplate.guild_id == guild.id,
                    GameTemplate.is_default == True
                )
            )
            if existing.scalar_one_or_none():
                print(f"Default template already exists for guild {guild.guild_id}")
                continue

            # Get first active channel, or any channel if none active
            channel_result = await db.execute(
                select(ChannelConfiguration)
                .where(ChannelConfiguration.guild_id == guild.id)
                .where(ChannelConfiguration.is_active == True)
            )
            channel = channel_result.scalar_one_or_none()

            if not channel:
                # No active channel, get any channel
                channel_result = await db.execute(
                    select(ChannelConfiguration)
                    .where(ChannelConfiguration.guild_id == guild.id)
                )
                channel = channel_result.scalar_one_or_none()

            if not channel:
                print(f"No channels found for guild {guild.guild_id}, skipping")
                continue

            # Create default template
            template = GameTemplate(
                guild_id=guild.id,
                name="Default",
                description="Default game template",
                is_default=True,
                channel_id=channel.id,
                order=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(template)
            print(f"Created default template for guild {guild.guild_id}")

        await db.commit()
        print("Data migration complete!")

if __name__ == "__main__":
    asyncio.run(create_default_templates())
```

### Technical Requirements

**Database Constraints:**

- Unique template names per guild (case-sensitive)
- Only one `is_default=True` per guild (enforced in application layer)
- Cannot delete `is_default` template (enforced in application layer)
- `order` must be >= 0 (check constraint)
- All templates must have a valid `channel_id`

**Authorization Requirements:**

- Template CRUD: Requires bot manager role or guild admin
- Template visibility: Filter by `allowed_host_role_ids` for non-admins
- Game creation: Verify user has role in template's `allowed_host_role_ids`

**Data Migration Requirements:**

- Create default template for each existing guild
- Set channel_id to first active channel (or any channel if none active)
- Leave all pre-populated fields NULL initially
- Set `is_default=True`, `order=0`

**Frontend Requirements:**

- Template management UI (CRUD operations, drag-to-reorder)
- Template selection dropdown in game creation
- Visual distinction between locked and editable fields
- Show template description on hover/selection
- Remove inheritance preview components
- Add channel `is_active` toggle to guild dashboard (replaces `/config-channel` bot command)
- Add bot manager roles configuration to guild settings (replaces `/config-guild` bot command)
- Add "Refresh Guilds" button that syncs user's Discord guilds with database (creates missing guild/channel configs)

**Bot Command Requirements:**

- Remove `/config-channel` command entirely (channel `is_active` toggle moved to web UI)
- Remove `/config-guild` command entirely (bot manager roles moved to web UI)
- No privileged intents needed - guild discovery handled manually by user
- Bot continues to handle Join/Leave button interactions on game announcements (no template involvement)

**Guild Discovery & Initialization:**

- "Refresh Guilds" button only visible when: (user admin guilds - bot's guilds in database) is non-empty
- This means button only shows when user is admin of a guild where bot was recently added
- User clicks "Refresh Guilds" button
- Frontend calls `POST /api/v1/guilds/sync` endpoint
- Backend fetches user's guilds (with MANAGE_GUILD filter) and bot's current guild list
- Computes: new_guilds = (bot's guilds ∩ user admin guilds) - guilds already in database
- For each guild in new_guilds: Auto-create GuildConfiguration and ChannelConfiguration records
- Returns count of newly created guilds
- This approach avoids needing GUILD intent on bot, limits API calls, and only shows to relevant users

## Recommended Approach

Replace the current three-level inheritance system (Guild → Channel → Game) with a template-based system where templates represent game types and provide both locked and pre-populated settings.

### Implementation Strategy

This approach maintains system viability throughout by removing old code, updating the database, then adding new functionality layer by layer.

**Phase 1: Remove Inheritance Code & Update Database (CRITICAL - Must Complete All Substeps)**

**CRITICAL DEPENDENCIES:** This phase removes old code but routes still need create/update operations. Must complete ALL substeps before system is functional.

**Substep 1.1: Remove SettingsResolver from Service Layer**

1. Remove SettingsResolver class from `services/api/services/config.py`
2. Update `services/api/services/games.py`:
   - Remove SettingsResolver instantiation
   - Use `game.max_players` directly, defaulting to 10 if None
   - Use `game.reminder_minutes` directly, defaulting to [60, 15] if None
3. Update role checking services:
   - `services/bot/auth/role_checker.py` - check_game_host_permission()
   - `services/api/auth/roles.py` - check_game_host_permission()
   - Replace SettingsResolver calls with direct channel/guild field access

**Substep 1.2: Extract Database Query Operations**

1. Create `services/api/database/__init__.py` (empty package marker)
2. Create `services/api/database/queries.py` with read operations:
   ```python
   async def get_guild_by_id(db: AsyncSession, guild_id: str) -> GuildConfiguration | None
   async def get_guild_by_discord_id(db: AsyncSession, guild_discord_id: str) -> GuildConfiguration | None
   async def get_channel_by_id(db: AsyncSession, channel_id: str) -> ChannelConfiguration | None
   async def get_channel_by_discord_id(db: AsyncSession, channel_discord_id: str) -> ChannelConfiguration | None
   async def get_channels_by_guild(db: AsyncSession, guild_id: str) -> list[ChannelConfiguration]
   ```
3. Update routes to import and use these functions:
   - `services/api/routes/guilds.py` - Replace `service = ConfigurationService(db)` and `service.get_*` calls
   - `services/api/routes/channels.py` - Replace `service = ConfigurationService(db)` and `service.get_*` calls
   - `services/api/dependencies/permissions.py` - Replace any ConfigurationService usage

**Substep 1.3: Create Business Logic Services**

1. Create `services/api/services/guild_service.py`:

   ```python
   async def create_guild_config(db: AsyncSession, guild_discord_id: str, **settings) -> GuildConfiguration:
       """Create guild with guild_id=guild_discord_id, add to session, commit, refresh."""
       guild_config = GuildConfiguration(guild_id=guild_discord_id, **settings)
       db.add(guild_config)
       await db.commit()
       await db.refresh(guild_config)
       return guild_config

   async def update_guild_config(db: AsyncSession, guild_config: GuildConfiguration, **updates) -> GuildConfiguration:
       """Update fields where value is not None, commit, refresh."""
       for key, value in updates.items():
           if value is not None:
               setattr(guild_config, key, value)
       await db.commit()
       await db.refresh(guild_config)
       return guild_config
   ```

2. Create `services/api/services/channel_service.py`:

   ```python
   async def create_channel_config(db: AsyncSession, guild_id: str, channel_discord_id: str, **settings) -> ChannelConfiguration:
       """Create channel with channel_id=channel_discord_id, add to session, commit, refresh."""
       channel_config = ChannelConfiguration(guild_id=guild_id, channel_id=channel_discord_id, **settings)
       db.add(channel_config)
       await db.commit()
       await db.refresh(channel_config)
       return channel_config

   async def update_channel_config(db: AsyncSession, channel_config: ChannelConfiguration, **updates) -> ChannelConfiguration:
       """Update fields where value is not None, commit, refresh."""
       for key, value in updates.items():
           if value is not None:
               setattr(channel_config, key, value)
       await db.commit()
       await db.refresh(channel_config)
       return channel_config
   ```

3. Update routes to import and use these services:
   - `services/api/routes/guilds.py` - Import `guild_service`, replace `service.create_guild_config()` with `await guild_service.create_guild_config(db, ...)`
   - `services/api/routes/channels.py` - Import `channel_service`, replace `service.create_channel_config()` with `await channel_service.create_channel_config(db, ...)`

**Substep 1.4: Delete Old ConfigurationService**

1. Delete `services/api/services/config.py` entirely (contains SettingsResolver and ConfigurationService)
2. Delete `tests/services/api/services/test_config.py` (SettingsResolver tests)

**Substep 1.5: Update All Tests**

1. Update `tests/services/api/routes/test_guilds.py`:
   - Replace `patch("services.api.services.config.ConfigurationService")` with individual function patches:
     - Read ops: `patch("services.api.database.queries.get_guild_by_id")` or `patch("services.api.database.queries.get_guild_by_discord_id")`
     - Create ops: `patch("services.api.services.guild_service.create_guild_config")`
     - Update ops: `patch("services.api.services.guild_service.update_guild_config")`
   - Remove `mock_service = AsyncMock()` and `mock_service_class.return_value` patterns
   - Directly set return values: `mock_get_guild_by_id.return_value = mock_guild_config`
   - Match patch names to actual function being mocked (e.g., `create_guild_config` test should patch `get_guild_by_discord_id` not `get_guild_by_id`)
2. Update `tests/services/api/routes/test_channels.py` similarly for channel operations
3. Create `tests/services/api/services/test_guild_service.py` for new service unit tests
4. Create `tests/services/api/services/test_channel_service.py` for new service unit tests

**Substep 1.6: Remove Frontend Inheritance UI**

1. Delete `frontend/src/components/InheritancePreview.tsx`
2. Delete `frontend/src/components/__tests__/InheritancePreview.test.tsx`
3. Update `frontend/src/pages/ChannelConfig.tsx`:
   - Remove InheritancePreview import and usage
   - Remove "Resolved Settings Preview" Card
4. Update `frontend/src/pages/GuildConfig.tsx`:
   - Update field descriptions to remove inheritance mentions
5. Update `frontend/src/pages/GuildDashboard.tsx`:
   - Remove "Default Settings" display card

**Substep 1.7: Remove Bot Commands**

1. Delete `services/bot/commands/config_guild.py`
2. Delete `services/bot/commands/config_channel.py`
3. Delete `tests/services/bot/commands/test_config_guild.py`
4. Delete `tests/services/bot/commands/test_config_channel.py`
5. Update `services/bot/commands/__init__.py`:
   - Remove config_guild and config_channel command registrations

**Substep 1.8: Create Database Migrations**

1. Create `alembic/versions/018_replace_inheritance_with_templates.py`:
   - Remove `default_max_players`, `default_reminder_minutes` from guild_configurations
   - Remove `max_players`, `reminder_minutes`, `allowed_host_role_ids` from channel_configurations
   - Create `game_templates` table
   - Add `template_id` (FK to game_templates) and `allowed_player_role_ids` to game_sessions
2. Create `scripts/data_migration_create_default_templates.py`:
   - Idempotent script to create default template for each guild
   - Finds first active channel per guild
   - Creates template with order=0, is_default=True
   - Use `.is_(True)` for SQLAlchemy boolean comparisons, not `== True`
   - Use `datetime.UTC` not `datetime.utcnow()`

**Substep 1.9: Verify All Tests Pass**

1. Run unit tests: `uv run pytest tests/services/ tests/shared/ -v`
2. Run integration tests: `uv run pytest tests/integration/ -v` (requires database)
3. Fix any remaining import errors or test failures
4. Verify Docker builds succeed: `docker compose build api bot frontend`
5. Run linting: `uv run ruff check .` for Python, `cd frontend && npm run lint` for TypeScript

**CHECKPOINT:** After completing Phase 1, the system should:

- Have NO SettingsResolver references anywhere
- Have NO ConfigurationService references anywhere
- Have database query operations in `services/api/database/queries.py`
- Have CRUD business logic in `services/api/services/guild_service.py` and `channel_service.py`
- Have ALL tests passing (480+ unit tests, ~10 integration tests)
- Have inheritance fields removed from models (via migration)
- Have template system added to models (via migration)
- Have working create/update operations for guilds and channels
- Have all routes functional with new service structure

**Phase 2: Add Template Models & Services**

1. Create `GameTemplate` model with all fields
2. Add `template_id` and `allowed_player_role_ids` to `GameSession` model
3. Update Guild model to add `templates` relationship
4. Create `TemplateService` with CRUD operations
5. Add template schemas (create, update, response, list)
6. Add template tests (CRUD, authorization, is_default protection)

**Phase 3: API Template Endpoints**

1. Create manual guild sync endpoint:
   - `POST /api/v1/guilds/sync` - Fetch user's guilds from Discord, compute intersection with bot's guilds, create missing GuildConfiguration and ChannelConfiguration records
2. Create template API endpoints:
   - `GET /api/v1/guilds/{guild_id}/templates` - List templates for user
   - `GET /api/v1/templates/{template_id}` - Get template details
   - `POST /api/v1/guilds/{guild_id}/templates` - Create template
   - `PUT /api/v1/templates/{template_id}` - Update template
   - `DELETE /api/v1/templates/{template_id}` - Delete template
   - `POST /api/v1/templates/{template_id}/set-default` - Set as default
   - `POST /api/v1/templates/reorder` - Bulk reorder templates
3. Update game creation endpoint to require and validate template_id
4. Add authorization checks for template visibility and usage

**Phase 4: Frontend Template Management**

1. Add "Refresh Guilds" button to guild page:
   - Only show button if user has admin guilds not in current guild list
   - Check: GET user's Discord guilds with MANAGE_GUILD, compare to existing guild configs
   - Calls `POST /api/v1/guilds/sync` endpoint when clicked
   - Shows loading state during sync
   - Displays success message with count of new guilds/channels created
   - Button disappears after sync if no more missing guilds
2. Add template management page with CRUD operations:
   - List view with drag-to-reorder
   - Create/edit form with locked vs editable field sections
   - Delete confirmation (block is_default)
   - Set default toggle
3. Update game creation form:
   - Add template dropdown (filtered by user roles)
   - Show template description on selection
   - Pre-populate editable fields from template
   - Show locked fields as read-only
   - Remove channel selection (comes from template)
4. Update guild/channel config pages:
   - Remove inheritance settings sections
   - Keep bot manager roles, allowed channels, etc.
5. Add template indication to game display

### Benefits Over Inheritance

1. **Clearer Semantics**: Templates represent game types, not configuration layers
2. **Enforced Constraints**: Some settings (channel, roles) are truly locked
3. **Better UX**: Host sees "D&D Campaign" vs "Board Game Night" instead of nested settings
4. **Simpler Logic**: No resolution chain, values come directly from template
5. **Role-Based Visibility**: Templates naturally support role-based access
6. **Flexible Defaults**: Each template can have different defaults
7. **Easier Testing**: No complex inheritance resolution to test
8. **Cleaner Codebase**: Removes 300+ lines of inheritance resolution logic

### Implementation Benefits

1. **Single Migration**: One atomic change instead of staged migration reduces complexity
2. **No Dual Maintenance**: Don't need to support both systems simultaneously
3. **Immediate Clarity**: System behavior is clear from day one
4. **Simpler Rollback**: Single migration to revert if issues arise
5. **Faster Development**: Skip the temporary state of supporting both systems

## Implementation Guidance

- **Objectives**: Replace inheritance system with template-based game types in single clean transition
- **Key Tasks**:
  1. Remove SettingsResolver and all inheritance resolution logic
  2. Remove inheritance fields from Guild and Channel models
  3. Create GameTemplate model and combined migration
  4. Run data migration script to create default templates
  5. Build TemplateService with CRUD operations
  6. Update game creation/join to use template values directly
  7. Build template API endpoints with authorization
  8. Update frontend for template management
  9. Update bot commands for template workflow
  10. Replace inheritance tests with template tests
- **Dependencies**:
  - SQLAlchemy models must support relationships
  - Role service needed for template visibility filtering
  - Discord API for resolving channel names in responses
  - Data migration script must run after schema migration
- **Success Criteria**:
  - All games created via template selection
  - No SettingsResolver or inheritance code remains
  - Default template exists for all guilds
  - Templates properly enforce locked vs editable fields
  - Frontend shows template management UI with drag-to-reorder
  - Bot commands use template workflow
  - Tests cover template CRUD, authorization, and is_default protection
