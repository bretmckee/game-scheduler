<!-- markdownlint-disable-file -->

# Task Details: Game Template System

## Research Reference

**Source Research**: #file:../research/20251201-game-template-system-research.md

## Phase 1: Extract Services & Remove SettingsResolver

### Task 1.1: Create database queries module

Create new module for simple database query operations previously in ConfigurationService.

- **Files**:
  - `services/api/database/__init__.py` - Empty package marker (new)
  - `services/api/database/queries.py` - Read operations for guild and channel configs (new)
- **Success**:
  - Module contains get_guild_by_id, get_guild_by_discord_id, get_channel_by_id, get_channel_by_discord_id, get_channels_by_guild
  - All functions use AsyncSession parameter and return appropriate model types
  - Functions use simple select queries without business logic
- **Research References**:
  - #file:../research/20251201-game-template-system-research.md (Lines 150-170) - ConfigurationService read operations patterns
- **Dependencies**:
  - SQLAlchemy 2.0 async session

### Task 1.2: Create guild and channel services

Create business logic services for create/update operations on guilds and channels.

- **Files**:
  - `services/api/services/guild_service.py` - Create and update operations for guild configs (new)
  - `services/api/services/channel_service.py` - Create and update operations for channel configs (new)
- **Success**:
  - guild_service contains create_guild_config and update_guild_config functions
  - channel_service contains create_channel_config and update_channel_config functions
  - Functions handle session add, commit, refresh pattern
  - Update functions only set non-None values
- **Research References**:
  - #file:../research/20251201-game-template-system-research.md (Lines 170-215) - ConfigurationService create/update operations
- **Dependencies**:
  - Task 1.1 completion
  - SQLAlchemy models

### Task 1.3: Update routes to use new services

Replace ConfigurationService calls in route handlers with new database queries and service functions.

- **Files**:
  - `services/api/routes/guilds.py` - Import and use guild_service, database queries
  - `services/api/routes/channels.py` - Import and use channel_service, database queries
  - `services/api/dependencies/permissions.py` - Replace ConfigurationService usage if present
- **Success**:
  - No references to ConfigurationService remain in routes
  - All database reads use functions from services/api/database/queries
  - All create/update operations use functions from guild_service or channel_service
  - Routes import correct functions and pass AsyncSession parameter
- **Research References**:
  - #file:../research/20251201-game-template-system-research.md (Lines 215-230) - Routes affected and usage patterns
- **Dependencies**:
  - Task 1.2 completion

### Task 1.4: Remove SettingsResolver from game operations

Update game creation, join, and authorization to use direct field access instead of SettingsResolver.

- **Files**:
  - `services/api/services/games.py` - Remove SettingsResolver usage in create_game and join_game
  - `services/api/auth/roles.py` - Remove SettingsResolver from check_game_host_permission
  - `services/bot/auth/role_checker.py` - Remove SettingsResolver from check_game_host_permission
- **Success**:
  - Game operations use game.max_players directly, defaulting to 10 if None
  - Game operations use game.reminder_minutes directly, defaulting to [60, 15] if None
  - Host permission checks access channel/guild allowed_host_role_ids directly
  - No SettingsResolver imports or instantiations remain
- **Research References**:
  - #file:../research/20251201-game-template-system-research.md (Lines 230-260) - SettingsResolver usage patterns and replacement logic
- **Dependencies**:
  - Task 1.3 completion

### Task 1.5: Delete ConfigurationService and update all tests

Remove old service class and update all tests to mock new service structure.

- **Files**:
  - `services/api/services/config.py` - Delete entire file
  - `tests/services/api/services/test_config.py` - Delete entire file
  - `tests/services/api/routes/test_guilds.py` - Update to mock new functions
  - `tests/services/api/routes/test_channels.py` - Update to mock new functions
  - `tests/services/api/services/test_guild_service.py` - Create new test file
  - `tests/services/api/services/test_channel_service.py` - Create new test file
- **Success**:
  - No ConfigurationService or SettingsResolver references exist in codebase
  - Route tests patch individual functions not classes
  - New service tests cover create and update operations
  - All tests pass (480+ unit tests)
- **Research References**:
  - #file:../research/20251201-game-template-system-research.md (Lines 150-170, 260-285) - Test update patterns and mock strategies
- **Dependencies**:
  - Task 1.4 completion
  - All previous Phase 1 tasks

## Phase 2: Database Schema Migration

### Task 2.1: Create GameTemplate model

Create new model representing game types with locked and pre-populated settings.

- **Files**:
  - `shared/models/template.py` - New GameTemplate model (new)
  - `shared/models/__init__.py` - Add GameTemplate to exports
- **Success**:
  - Model includes identity fields: id, guild_id, name, description, order, is_default
  - Model includes locked fields: channel_id, notify_role_ids, allowed_player_role_ids, allowed_host_role_ids
  - Model includes pre-populated fields: max_players, expected_duration_minutes, reminder_minutes, where, signup_instructions
  - Model includes timestamps: created_at, updated_at
  - Model has relationships to Guild, Channel, and GameSession
  - Table args include composite indexes and check constraint on order >= 0
- **Research References**:
  - #file:../research/20251201-game-template-system-research.md (Lines 285-365) - Complete GameTemplate model specification
- **Dependencies**:
  - Phase 1 completion

### Task 2.2: Update GuildConfiguration and ChannelConfiguration models

Remove inheritance fields from guild and channel models.

- **Files**:
  - `shared/models/guild.py` - Remove default_max_players, default_reminder_minutes, allowed_host_role_ids; add templates relationship
  - `shared/models/channel.py` - Remove max_players, reminder_minutes, allowed_host_role_ids, game_category
- **Success**:
  - GuildConfiguration only contains bot_manager_role_ids, require_host_role, and templates relationship
  - ChannelConfiguration only contains is_active field
  - All references to removed fields are gone from model docstrings
- **Research References**:
  - #file:../research/20251201-game-template-system-research.md (Lines 52-85) - Guild and channel model after inheritance removal
- **Dependencies**:
  - Task 2.1 completion

### Task 2.3: Update GameSession model for templates

Add template relationship and allowed_player_role_ids to game model.

- **Files**:
  - `shared/models/game.py` - Add template_id FK, allowed_player_role_ids, template relationship
- **Success**:
  - GameSession has template_id as required FK to game_templates
  - GameSession has allowed_player_role_ids as optional JSON field
  - GameSession has template relationship to GameTemplate
- **Research References**:
  - #file:../research/20251201-game-template-system-research.md (Lines 365-380) - GameSession template fields
- **Dependencies**:
  - Task 2.1 completion

### Task 2.4: Create database migration

Create Alembic migration to remove inheritance and add template system.

- **Files**:
  - `alembic/versions/018_replace_inheritance_with_templates.py` - Combined migration (new)
- **Success**:
  - Upgrade removes inheritance fields from guild_configurations and channel_configurations
  - Upgrade creates game_templates table with all fields and indexes
  - Upgrade adds template_id and allowed_player_role_ids to game_sessions
  - Downgrade reverses all changes
  - Migration runs without errors
- **Research References**:
  - #file:../research/20251201-game-template-system-research.md (Lines 710-780) - Complete migration script
- **Dependencies**:
  - Tasks 2.1, 2.2, 2.3 completion

### Task 2.5: Create default template data migration script

Create idempotent script to populate default templates for existing guilds.

- **Files**:
  - `scripts/data_migration_create_default_templates.py` - Template creation script (new)
- **Success**:
  - Script creates "Default" template for each guild without one
  - Script finds first active channel per guild, falls back to any channel
  - Script sets is_default=True, order=0 for created templates
  - Script is idempotent (can run multiple times safely)
  - Script uses datetime.UTC not datetime.utcnow()
  - Script uses .is_(True) for boolean comparisons not == True
- **Research References**:
  - #file:../research/20251201-game-template-system-research.md (Lines 780-840) - Data migration script with patterns
- **Dependencies**:
  - Task 2.4 completion

## Phase 3: Template Service & Schemas

### Task 3.1: Create template schemas

Create Pydantic schemas for template create, update, response, and list operations.

- **Files**:
  - `shared/schemas/template.py` - Template schemas (new)
  - `shared/schemas/__init__.py` - Add template schema exports
- **Success**:
  - TemplateCreateRequest includes all template fields with validation
  - TemplateUpdateRequest allows partial updates
  - TemplateResponse includes resolved channel_name
  - TemplateListItem provides minimal dropdown data
  - All schemas use proper Field validators and descriptions
- **Research References**:
  - #file:../research/20251201-game-template-system-research.md (Lines 600-670) - Complete schema specifications
- **Dependencies**:
  - Phase 2 completion

### Task 3.2: Create TemplateService

Create service class for template CRUD operations with authorization.

- **Files**:
  - `services/api/services/template_service.py` - TemplateService class (new)
- **Success**:
  - Service includes get_templates_for_user with role filtering
  - Service includes create_default_template for guild initialization
  - Service includes set_default to manage is_default flag
  - Service includes delete_template with is_default protection
  - Service includes standard CRUD operations (get, create, update)
  - Service includes reorder_templates for drag-to-reorder
  - All methods use AsyncSession and proper transaction handling
- **Research References**:
  - #file:../research/20251201-game-template-system-research.md (Lines 420-520) - Complete TemplateService implementation
- **Dependencies**:
  - Task 3.1 completion

### Task 3.3: Update game schemas for template-based creation

Modify game creation schema to require template_id and make fields optional overrides.

- **Files**:
  - `shared/schemas/game.py` - Update GameCreateRequest
- **Success**:
  - GameCreateRequest requires template_id field
  - Fields like max_players, reminder_minutes become optional overrides
  - Channel_id removed (comes from template)
  - Notify_role_ids removed (comes from template)
  - Allowed_player_role_ids removed (comes from template)
- **Research References**:
  - #file:../research/20251201-game-template-system-research.md (Lines 670-690) - Updated game schema
- **Dependencies**:
  - Task 3.1 completion

### Task 3.4: Create template service tests

Create comprehensive unit tests for template service operations.

- **Files**:
  - `tests/services/api/services/test_template_service.py` - Template service tests (new)
- **Success**:
  - Tests cover get_templates_for_user with role filtering
  - Tests cover create_default_template
  - Tests cover set_default (unsetting others)
  - Tests cover delete_template with is_default protection
  - Tests cover standard CRUD operations
  - Tests cover reorder operations
  - All tests use proper fixtures and mocks
- **Research References**:
  - #file:../research/20251201-game-template-system-research.md (Lines 840-880) - Test patterns
- **Dependencies**:
  - Task 3.2 completion

## Phase 4: Template API Endpoints

### Task 4.1: Create guild sync endpoint

Create endpoint to manually sync user's Discord guilds with database.

- **Files**:
  - `services/api/routes/guilds.py` - Add POST /guilds/sync endpoint
  - `services/api/services/guild_service.py` - Add sync_user_guilds function
- **Success**:
  - Endpoint fetches user's Discord guilds with MANAGE_GUILD permission
  - Endpoint fetches bot's current guild list
  - Endpoint computes new_guilds = (bot guilds ∩ user admin guilds) - existing guilds
  - Endpoint creates GuildConfiguration and ChannelConfiguration for new guilds
  - Endpoint creates default template for each new guild
  - Endpoint returns count of newly created guilds
  - Endpoint requires authentication
- **Research References**:
  - #file:../research/20251201-game-template-system-research.md (Lines 880-930) - Guild sync implementation
- **Dependencies**:
  - Phase 3 completion

### Task 4.2: Create template API endpoints

Create RESTful endpoints for template CRUD operations.

- **Files**:
  - `services/api/routes/templates.py` - Template router (new)
  - `services/api/main.py` - Register templates router
- **Success**:
  - GET /guilds/{guild_id}/templates - List templates with role filtering
  - GET /templates/{template_id} - Get single template
  - POST /guilds/{guild_id}/templates - Create template (requires bot manager role)
  - PUT /templates/{template_id} - Update template (requires bot manager role)
  - DELETE /templates/{template_id} - Delete template (requires bot manager role, blocks is_default)
  - POST /templates/{template_id}/set-default - Set as default (requires bot manager role)
  - POST /templates/reorder - Bulk reorder (requires bot manager role)
  - All endpoints use proper authorization checks
  - All endpoints return appropriate schemas
- **Research References**:
  - #file:../research/20251201-game-template-system-research.md (Lines 930-1000) - API endpoint patterns
- **Dependencies**:
  - Phase 3 completion

### Task 4.3: Update game creation endpoint for templates

Modify game creation to require and validate template selection.

- **Files**:
  - `services/api/services/games.py` - Update create_game method
  - `services/api/routes/games.py` - Verify endpoint uses updated service
- **Success**:
  - create_game fetches template by template_id
  - create_game validates user has role in template's allowed_host_role_ids
  - create_game sets locked fields from template (channel_id, notify_role_ids, allowed_player_role_ids)
  - create_game uses template defaults for optional fields if not provided
  - create_game raises appropriate errors for missing template or unauthorized user
- **Research References**:
  - #file:../research/20251201-game-template-system-research.md (Lines 520-580) - Game creation with templates
- **Dependencies**:
  - Task 4.2 completion

### Task 4.4: Create template endpoint tests

Create integration tests for template API endpoints.

- **Files**:
  - `tests/services/api/routes/test_templates.py` - Template endpoint tests (new)
- **Success**:
  - Tests cover list templates with role filtering
  - Tests cover create template with authorization
  - Tests cover update template
  - Tests cover delete template with is_default protection
  - Tests cover set_default endpoint
  - Tests cover reorder endpoint
  - Tests verify proper authorization checks
  - All tests use proper fixtures and database setup
- **Research References**:
  - #file:../research/20251201-game-template-system-research.md (Lines 930-1000) - Endpoint testing patterns
- **Dependencies**:
  - Tasks 4.2, 4.3 completion

## Phase 5: Frontend Template Management

### Task 5.1: Create template management components

Build React components for template CRUD and management UI.

- **Files**:
  - `frontend/src/pages/TemplateManagement.tsx` - Main template management page (new)
  - `frontend/src/components/TemplateList.tsx` - Template list with drag-to-reorder (new)
  - `frontend/src/components/TemplateForm.tsx` - Create/edit template form (new)
  - `frontend/src/components/TemplateCard.tsx` - Individual template display (new)
  - `frontend/src/api/templates.ts` - Template API client functions (new)
- **Success**:
  - TemplateManagement page shows list of templates with reorder capability
  - TemplateForm distinguishes locked vs pre-populated fields visually
  - TemplateList supports drag-to-reorder with visual feedback
  - Forms validate required fields and constraints
  - Delete operations show confirmation dialog
  - Cannot delete is_default template (UI prevents)
  - Set default toggle works correctly
- **Research References**:
  - #file:../research/20251201-game-template-system-research.md (Lines 880-930) - Frontend template patterns
- **Dependencies**:
  - Phase 4 completion

### Task 5.2: Add guild sync functionality

Add "Refresh Guilds" button to guild page for manual guild sync.

- **Files**:
  - `frontend/src/pages/GuildDashboard.tsx` - Add refresh button and sync logic
  - `frontend/src/api/guilds.ts` - Add syncUserGuilds API function
- **Success**:
  - Button only visible when (user admin guilds - bot's guilds in database) is non-empty
  - Button calls POST /guilds/sync endpoint on click
  - Shows loading state during sync operation
  - Displays success message with count of new guilds created
  - Button disappears after sync if no more missing guilds
  - Handles errors gracefully
- **Research References**:
  - #file:../research/20251201-game-template-system-research.md (Lines 880-930) - Guild sync UI requirements
- **Dependencies**:
  - Task 4.1 completion

### Task 5.3: Update game creation form for templates

Modify game creation to use template selection instead of channel selection.

- **Files**:
  - `frontend/src/pages/CreateGame.tsx` - Replace channel dropdown with template dropdown
  - `frontend/src/api/games.ts` - Update createGame to use template_id
- **Success**:
  - Template dropdown shows templates filtered by user roles
  - Dropdown sorted with default first, then by order
  - Template selection pre-populates editable fields
  - Locked fields displayed as read-only with template values
  - Channel selection removed (comes from template)
  - Form validates template_id is provided
  - Shows template description on hover or selection
- **Research References**:
  - #file:../research/20251201-game-template-system-research.md (Lines 520-580, 600-670) - Template-based game creation
- **Dependencies**:
  - Task 4.3 completion

### Task 5.4: Remove inheritance UI components

Delete components and code related to inheritance display.

- **Files**:
  - `frontend/src/components/InheritancePreview.tsx` - Delete entire file
  - `frontend/src/components/__tests__/InheritancePreview.test.tsx` - Delete entire file
  - `frontend/src/pages/ChannelConfig.tsx` - Remove InheritancePreview usage
  - `frontend/src/pages/GuildConfig.tsx` - Remove inheritance mentions from descriptions
  - `frontend/src/pages/GuildDashboard.tsx` - Remove "Default Settings" card
- **Success**:
  - No InheritancePreview component exists
  - Guild and channel config pages don't mention inheritance
  - No "inherited from guild" indicators remain
  - Channel config page simplified (only is_active toggle)
- **Research References**:
  - #file:../research/20251201-game-template-system-research.md (Lines 230-260) - Frontend inheritance removal
- **Dependencies**:
  - Tasks 5.1, 5.2, 5.3 completion

### Task 5.5: Create frontend template tests

Create unit tests for template management components.

- **Files**:
  - `frontend/src/components/__tests__/TemplateList.test.tsx` - Template list tests (new)
  - `frontend/src/components/__tests__/TemplateForm.test.tsx` - Template form tests (new)
  - `frontend/src/pages/__tests__/TemplateManagement.test.tsx` - Template page tests (new)
- **Success**:
  - Tests cover template list rendering and interactions
  - Tests cover drag-to-reorder functionality
  - Tests cover form validation and submission
  - Tests cover delete confirmation dialog
  - Tests cover is_default protection
  - Tests use proper mocks for API calls
- **Research References**:
  - #file:../../.github/instructions/reactjs.instructions.md - React testing patterns
- **Dependencies**:
  - Task 5.4 completion

## Phase 6: Bot Command Cleanup

### Task 6.1: Remove bot config commands

Delete bot commands that are now handled in web UI.

- **Files**:
  - `services/bot/commands/config_guild.py` - Delete entire file
  - `services/bot/commands/config_channel.py` - Delete entire file
  - `services/bot/commands/__init__.py` - Remove command registrations
  - `tests/services/bot/commands/test_config_guild.py` - Delete entire file
  - `tests/services/bot/commands/test_config_channel.py` - Delete entire file
- **Success**:
  - No /config-guild command exists
  - No /config-channel command exists
  - Command registration updated to exclude removed commands
  - No test failures from missing commands
  - Bot still handles Join/Leave button interactions
- **Research References**:
  - #file:../research/20251201-game-template-system-research.md (Lines 260-285) - Bot command removal
- **Dependencies**:
  - Phase 5 completion (web UI must be functional first)
