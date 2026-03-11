<!-- markdownlint-disable-file -->

# Task Details: Game Announcement Archive Feature

## Research Reference

**Source Research**: #file:../research/20260308-02-game-archive-feature-research.md

## Phase 1: Data Model + Status Enum

### Task 1.1: Add Alembic Migration For Archive Fields

Create a new migration after `f3a2c1d8e9b7` that adds archive columns and foreign keys for templates and game sessions.

- **Files**:
  - alembic/versions/20260311_add_archive_fields.py - add `archive_delay_seconds` and `archive_channel_id` columns and FKs
- **Success**:
  - Migration applies cleanly with `archive_delay_seconds` and `archive_channel_id` columns on both tables
  - FK constraints use `ondelete="SET NULL"`
- **Research References**:
  - #file:../research/20260308-02-game-archive-feature-research.md (Lines 187-213) - migration shape and FK behavior
  - #file:../research/20260308-02-game-archive-feature-research.md (Lines 50-51) - latest down_revision
- **Dependencies**:
  - None

### Task 1.2: Update GameTemplate And GameSession Models

Add archive fields to `GameTemplate` and `GameSession`, and fix `foreign_keys` on channel relationships due to multiple FKs.

- **Files**:
  - shared/models/template.py - add `archive_delay_seconds`, `archive_channel_id`, and explicit `foreign_keys`
  - shared/models/game.py - add `archive_delay_seconds`, `archive_channel_id`, and explicit `foreign_keys`
- **Success**:
  - SQLAlchemy no longer reports ambiguous foreign key relationships
  - Archive fields are nullable and match the migration types
- **Research References**:
  - #file:../research/20260308-02-game-archive-feature-research.md (Lines 83-109) - model fields and relationship notes
- **Dependencies**:
  - Task 1.1 completion

### Task 1.3: Extend Canonical GameStatus For Archiving

Add `ARCHIVED` to the canonical `GameStatus` in `shared/utils/status_transitions.py`, move/add `display_name` there, and update `is_valid_transition` to allow `COMPLETED → ARCHIVED`.

- **Files**:
  - shared/utils/status_transitions.py - add enum value, `display_name`, and transition update
- **Success**:
  - `GameStatus` includes `ARCHIVED` and `display_name` returns "Archived"
  - `is_valid_transition` allows `COMPLETED → ARCHIVED` and blocks `CANCELLED → ARCHIVED`
- **Research References**:
  - #file:../research/20260308-02-game-archive-feature-research.md (Lines 59-64) - consolidation follow-up requirements
  - #file:../research/20260308-02-game-archive-feature-research.md (Lines 111-129) - transition map
- **Dependencies**:
  - Consolidation changes merged (status enum single source)

## Phase 2: API + Services

### Task 2.1: Extend Template Schemas For Archive Fields

Add `archive_delay_seconds`, `archive_channel_id`, and `archive_channel_name` to template schema classes, with appropriate validation and descriptions.

- **Files**:
  - shared/schemas/template.py - update create/update/response/list items
- **Success**:
  - Template schema responses include archive fields and channel name
  - Validation allows `archive_delay_seconds=0` and `None`
- **Research References**:
  - #file:../research/20260308-02-game-archive-feature-research.md (Lines 215-236) - schema field definitions and UX note
- **Dependencies**:
  - Task 1.2 completion

### Task 2.2: Update Template Routes For Archive Fields

Wire archive fields into template create/update response plumbing, including resolving archive channel names via Discord client.

- **Files**:
  - services/api/routes/templates.py - update `build_template_response` and `create_template`
- **Success**:
  - Responses include `archive_channel_name` when configured
  - Create/update passes archive fields through to service layer
- **Research References**:
  - #file:../research/20260308-02-game-archive-feature-research.md (Lines 38-48) - route touch points
  - #file:../research/20260308-02-game-archive-feature-research.md (Lines 238-246) - channel name resolution
  - #file:../research/20260308-02-game-archive-feature-research.md (Lines 259-262) - create route arguments
- **Dependencies**:
  - Task 2.1 completion

### Task 2.3: Copy Archive Fields When Building Game Sessions

Copy archive configuration from the template into new game sessions.

- **Files**:
  - services/api/services/games.py - update `_build_game_session`
- **Success**:
  - Games created from templates carry over archive fields
- **Research References**:
  - #file:../research/20260308-02-game-archive-feature-research.md (Lines 13-19) - copy pattern
  - #file:../research/20260308-02-game-archive-feature-research.md (Lines 248-257) - specific copy logic
- **Dependencies**:
  - Task 1.2 completion

## Phase 3: Bot Scheduling + Announcement Archiving (TDD)

### Task 3.1: Add Failing Unit Tests For Archive Scheduling And Archiving

Write unit tests with real assertions marked as expected failures for archive schedule creation and announcement deletion/repost.

- **Files**:
  - tests/services/bot/events/test_handlers.py - add xfail tests for scheduling and archive announcement behavior
- **Success**:
  - Tests compile and fail as expected under xfail/failing markers
- **Research References**:
  - #file:../research/20260308-02-game-archive-feature-research.md (Lines 131-185) - handler behavior and archive flow
  - #file:../research/20260308-02-game-archive-feature-research.md (Lines 267-274) - test cases
- **Dependencies**:
  - Task 1.3 completion

### Task 3.2: Implement Archive Scheduling And Announcement Archive Flow

Update `_handle_status_transition_due` to schedule ARCHIVED transitions, and implement `_archive_game_announcement` that deletes the original and optionally reposts to the archive channel.

- **Files**:
  - services/bot/events/handlers.py - schedule ARCHIVED status, add `_archive_game_announcement`, call after transition
- **Success**:
  - ARCHIVED schedule rows are created only when `archive_delay_seconds` is set
  - ARCHIVED transition deletes the original announcement and posts to archive channel if configured
- **Research References**:
  - #file:../research/20260308-02-game-archive-feature-research.md (Lines 131-185) - scheduling and archive behavior
- **Dependencies**:
  - Task 3.1 completion

### Task 3.3: Remove Xfail Markers And Harden Edge Cases

Remove xfail markers and add edge case coverage (delay=0, no message_id, delete-only mode).

- **Files**:
  - tests/services/bot/events/test_handlers.py - remove xfail, extend assertions
- **Success**:
  - Tests pass with real assertions
  - Edge cases behave as documented
- **Research References**:
  - #file:../research/20260308-02-game-archive-feature-research.md (Lines 153-154) - delay=0 semantics
  - #file:../research/20260308-02-game-archive-feature-research.md (Lines 267-274) - edge case tests
- **Dependencies**:
  - Task 3.2 completion

## Phase 4: Integration + E2E + Docs (TDD)

### Task 4.1: Add Failing Integration Tests For Template And Game Archive Fields

Add integration tests with expected failures covering template create/update and game creation field copying.

- **Files**:
  - tests/services/api/routes/test_templates.py - add xfail tests for template archive fields
  - tests/integration/test_games_archive_fields.py - add xfail tests for game creation archive fields
- **Success**:
  - Integration tests compile and fail as expected under xfail/failing markers
- **Research References**:
  - #file:../research/20260308-02-game-archive-feature-research.md (Lines 284-295) - integration scenarios
- **Dependencies**:
  - Task 2.3 completion

### Task 4.2: Implement Integration Behavior And Remove Xfail Markers

Implement API/schema/service behavior for archive fields and remove xfail markers after functionality is complete.

- **Files**:
  - shared/schemas/template.py - ensure archive fields wired through
  - services/api/routes/templates.py - ensure create/update/response logic for archive fields
  - services/api/services/games.py - ensure archive fields copied
  - tests/services/api/routes/test_templates.py - remove xfail markers
  - tests/integration/test_games_archive_fields.py - remove xfail markers
- **Success**:
  - Integration tests pass with real assertions
- **Research References**:
  - #file:../research/20260308-02-game-archive-feature-research.md (Lines 38-48) - routes wiring
  - #file:../research/20260308-02-game-archive-feature-research.md (Lines 215-257) - schema and service updates
- **Dependencies**:
  - Task 4.1 completion

### Task 4.3: Add E2E Archive Tests And Test Infrastructure Updates

Add E2E coverage for archive transitions, plus helper support and environment variable documentation.

- **Files**:
  - tests/e2e/test_game_archive.py - new e2e tests
  - tests/e2e/helpers/discord.py - add `wait_for_message_deleted` helper
  - tests/e2e/conftest.py - add `discord_archive_channel_id` fixture
  - docs/developer/TESTING.md - document `DISCORD_ARCHIVE_CHANNEL_ID`
- **Success**:
  - E2E tests cover archive delete-only and repost modes
  - Test env includes archive channel id and helper supports deletion checks
- **Research References**:
  - #file:../research/20260308-02-game-archive-feature-research.md (Lines 296-352) - e2e test plan and env var
- **Dependencies**:
  - Task 3.3 completion
  - Task 4.2 completion

## Dependencies

- Alembic migrations
- SQLAlchemy models
- Pytest (unit, integration, e2e)
- Discord test environment with archive channel

## Success Criteria

- Templates and games support archive fields end-to-end
- ARCHIVED transitions are scheduled and executed correctly
- Announcements are deleted and optionally reposted to archive channels
- Unit, integration, and e2e tests pass
