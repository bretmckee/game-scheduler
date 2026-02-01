<!-- markdownlint-disable-file -->

# Task Details: Documentation Reorganization by User Persona

## Research Reference

**Source Research**: #file:../research/20260201-documentation-reorganization-by-persona-research.md

## Phase 1: Create User-Facing Documentation

### Task 1.1: Create docs/GUILD-ADMIN.md

Create comprehensive guild administrator guide for bot setup and configuration.

- **Files**:
  - docs/GUILD-ADMIN.md - New file with bot invite, permissions, and configuration instructions
- **Content Sources**:
  - TESTING_E2E.md (lines 70-87) - Bot invite URL patterns
  - services/api/routes/guild_configurations.py - Bot manager role configuration
  - services/api/routes/channel_configurations.py - Channel setup details
  - services/api/routes/game_templates.py - Template management API
- **Success**:
  - Document includes bot invite URL generation with required permissions explanation
  - Bot manager role configuration clearly explained
  - Channel setup for game announcements documented
  - Game template creation and management covered
- **Research References**:
  - #file:../research/20260201-documentation-reorganization-by-persona-research.md (Lines 55-62) - Guild admin content requirements
- **Dependencies**:
  - User clarification on bot invite process and permission requirements

### Task 1.2: Create docs/HOST-GUIDE.md

Create comprehensive game host guide for creating and managing games.

- **Files**:
  - docs/HOST-GUIDE.md - New file with game creation, template usage, and participant management
- **Content Sources**:
  - frontend/src/pages/CreateGame.tsx - Game creation UI workflow
  - frontend/src/components/GameForm.tsx - Template selection patterns
  - services/api/routes/games.py - Game CRUD endpoints
  - services/api/routes/participants.py - Participant management API
  - docs/oauth-flow.md - OAuth login process
- **Success**:
  - Web dashboard access and OAuth login documented
  - Step-by-step game creation guide from CreateGame page
  - Template usage clearly explained
  - Participant management operations covered
  - Host-only features (edit, cancel) documented
- **Research References**:
  - #file:../research/20260201-documentation-reorganization-by-persona-research.md (Lines 64-77) - Game host content requirements
- **Dependencies**:
  - User clarification on game host workflows and terminology

### Task 1.3: Create docs/PLAYER-GUIDE.md

Create simple player guide for joining games and receiving notifications.

- **Files**:
  - docs/PLAYER-GUIDE.md - New file with player interaction instructions
- **Content Sources**:
  - services/bot/views/signup_view.py - Discord button interactions
  - services/bot/handlers/game_message.py - Game announcement message format
  - services/api/routes/participants.py - Signup/leave endpoints
  - shared/models/game_participants.py - Waitlist mechanics
  - services/daemon/notification_scheduler.py - Notification timing
  - services/api/routes/calendar.py - Calendar download feature
- **Success**:
  - Finding games in Discord explained
  - Join/leave button interactions documented
  - Waitlist mechanics clearly explained
  - Notification timing and content described
  - Calendar download feature documented
- **Research References**:
  - #file:../research/20260201-documentation-reorganization-by-persona-research.md (Lines 79-89) - Player content requirements
- **Dependencies**:
  - User clarification on notification UX and edge cases

### Task 1.4: Restructure root README.md as persona gateway

Transform root README from developer-focused to persona gateway.

- **Files**:
  - README.md - Major restructuring to persona gateway format
- **Success**:
  - Opens with project overview (2-3 sentences)
  - Clear sections for each persona with links to appropriate docs
  - Brief architecture overview with link to detailed docs
  - Key features listed prominently
  - Development setup moved to docs/developer/SETUP.md
- **Research References**:
  - #file:../research/20260201-documentation-reorganization-by-persona-research.md (Lines 205-244) - Proposed README structure
- **Dependencies**:
  - Tasks 1.1-1.3 completed (user-facing guides exist)
  - Task 2.1 completed (developer docs organized)

## Phase 2: Reorganize Developer Documentation

### Task 2.1: Create docs/developer/ subdirectory and gateway README

Create developer documentation organization with gateway README.

- **Files**:
  - docs/developer/README.md - New gateway file linking to all developer docs
- **Success**:
  - Links to SETUP.md, architecture.md, TESTING.md created
  - Links to database.md, oauth-flow.md, transaction-management.md included
  - Contributing guidelines section added
  - Code quality standards referenced
- **Research References**:
  - #file:../research/20260201-documentation-reorganization-by-persona-research.md (Lines 139-145) - Developer README content
- **Dependencies**:
  - None (creates foundation for subsequent tasks)

### Task 2.2: Extract development setup to docs/developer/SETUP.md

Move development environment setup from README to dedicated file.

- **Files**:
  - docs/developer/SETUP.md - New file with extracted setup instructions
  - README.md - Remove development setup sections (preserve for reference until verified)
- **Content Sources**:
  - README.md lines ~80-250 - Development Setup, Quick Start, Development Workflow, Pre-commit Hooks
- **Success**:
  - Complete development environment setup documented
  - Quick start instructions preserved
  - Pre-commit hooks configuration included
  - Docker compose development workflow covered
- **Research References**:
  - #file:../research/20260201-documentation-reorganization-by-persona-research.md (Lines 147-152) - Setup content extraction
- **Dependencies**:
  - Task 2.1 completed (docs/developer/ exists)

### Task 2.3: Move architecture documentation to docs/developer/architecture.md

Move architecture documentation from temporary research location to stable docs.

- **Files**:
  - docs/developer/architecture.md - Move from .copilot-tracking/research/20251224-microservice-communication-architecture.md
  - .copilot-tracking/research/20251224-microservice-communication-architecture.md - Mark for deletion in Phase 4
- **Success**:
  - Complete architecture documentation with Mermaid diagrams in stable location
  - All internal references to architecture doc updated
  - Document reformatted as stable documentation (remove research notes)
- **Research References**:
  - #file:../research/20260201-documentation-reorganization-by-persona-research.md (Lines 154-157) - Architecture doc move
- **Dependencies**:
  - Task 2.1 completed (docs/developer/ exists)

### Task 2.4: Consolidate testing documentation into docs/developer/TESTING.md

Merge all testing documentation into single comprehensive guide.

- **Files**:
  - docs/developer/TESTING.md - New consolidated testing documentation
  - TESTING_E2E.md, TESTING_COVERAGE.md, TESTING_OAUTH.md - Mark for deletion in Phase 4
- **Content Sources**:
  - TESTING_E2E.md (650 lines) - E2E test setup with Discord bots
  - TESTING_COVERAGE.md - Test coverage collection
  - TESTING_OAUTH.md - OAuth testing
- **Success**:
  - All testing approaches documented in single file
  - Organized by test type (unit, integration, e2e)
  - Common patterns and helpers section included
  - Test infrastructure setup consolidated
- **Research References**:
  - #file:../research/20260201-documentation-reorganization-by-persona-research.md (Lines 159-163) - Testing consolidation
- **Dependencies**:
  - Task 2.1 completed (docs/developer/ exists)

### Task 2.5: Move existing technical docs to docs/developer/

Move all existing developer-focused technical documentation.

- **Files**:
  - docs/developer/database.md - Move from docs/DATABASE_SCHEMA.md
  - docs/developer/oauth-flow.md - Move from docs/oauth-flow.md
  - docs/developer/transaction-management.md - Move from docs/TRANSACTION_MANAGEMENT.md
  - docs/developer/deferred-events.md - Move from docs/DEFERRED_EVENT_PUBLISHING.md
  - docs/developer/compose-dependencies.md - Move from docs/DOCKER_COMPOSE_DEPENDENCIES.md
  - docs/developer/cloudflare-tunnel.md - Move from docs/CLOUDFLARE_TUNNEL_SETUP.md
  - docs/developer/local-act-testing.md - Move from docs/LOCAL_TESTING_WITH_ACT.md
  - docs/developer/production-readiness.md - Move from docs/PRODUCTION_READINESS_GUILD_ISOLATION.md
- **Success**:
  - All technical documentation in docs/developer/ subdirectory
  - Original files marked for deletion in Phase 4
  - Gateway README updated with links to all moved docs
- **Research References**:
  - #file:../research/20260201-documentation-reorganization-by-persona-research.md (Lines 165-169) - Technical doc moves
- **Dependencies**:
  - Task 2.1 completed (docs/developer/ and gateway README exist)

## Phase 3: Organize Deployment Documentation

### Task 3.1: Create docs/deployment/ subdirectory and gateway README

Create deployment documentation organization with gateway README.

- **Files**:
  - docs/deployment/README.md - New gateway file for self-hosting documentation
- **Success**:
  - Self-hosting overview section created
  - Links to quickstart.md, configuration.md, docker.md
  - System requirements documented
  - Security considerations section added
- **Research References**:
  - #file:../research/20260201-documentation-reorganization-by-persona-research.md (Lines 171-176) - Deployment README content
- **Dependencies**:
  - None (creates foundation for deployment docs)

### Task 3.2: Move deployment quickstart to docs/deployment/quickstart.md

Move deployment quickstart from root to deployment subdirectory.

- **Files**:
  - docs/deployment/quickstart.md - Move from DEPLOYMENT_QUICKSTART.md
  - DEPLOYMENT_QUICKSTART.md - Mark for deletion in Phase 4
- **Success**:
  - Complete deployment quickstart in new location
  - All server setup instructions preserved
  - Gateway README links to quickstart
- **Research References**:
  - #file:../research/20260201-documentation-reorganization-by-persona-research.md (Lines 178-180) - Quickstart move
- **Dependencies**:
  - Task 3.1 completed (docs/deployment/ exists)

### Task 3.3: Move runtime configuration to docs/deployment/configuration.md

Move runtime configuration documentation to deployment subdirectory.

- **Files**:
  - docs/deployment/configuration.md - Move from RUNTIME_CONFIG.md
  - RUNTIME_CONFIG.md - Mark for deletion in Phase 4
- **Success**:
  - Complete runtime configuration options documented
  - Environment variables reference preserved
  - Frontend proxy vs direct API modes explained
  - Gateway README links to configuration
- **Research References**:
  - #file:../research/20260201-documentation-reorganization-by-persona-research.md (Lines 182-187) - Configuration move
- **Dependencies**:
  - Task 3.1 completed (docs/deployment/ exists)

### Task 3.4: Consolidate Docker documentation into docs/deployment/docker.md

Merge all Docker-related deployment documentation.

- **Files**:
  - docs/deployment/docker.md - New consolidated Docker documentation
  - DOCKER_PORTS.md, DOCKER_CACHE_OPTIMIZATION.md - Mark for deletion in Phase 4
  - docs/DOCKER_COMPOSE_DEPENDENCIES.md - Mark for move to developer/ or deletion
- **Content Sources**:
  - DOCKER_PORTS.md - Port exposure strategy
  - DOCKER_CACHE_OPTIMIZATION.md - BuildKit cache mounts
  - docs/DOCKER_COMPOSE_DEPENDENCIES.md - Dependency graph
- **Success**:
  - All Docker deployment topics in single reference
  - Port management strategy documented
  - Cache optimization for deployment builds covered
  - Compose dependency graph included if relevant to deployment
  - Gateway README links to docker documentation
- **Research References**:
  - #file:../research/20260201-documentation-reorganization-by-persona-research.md (Lines 189-194) - Docker consolidation
- **Dependencies**:
  - Task 3.1 completed (docs/deployment/ exists)

## Phase 4: Cleanup and Link Updates

### Task 4.1: Delete moved files from root and docs/

Remove original files after verifying successful moves.

- **Files to Delete**:
  - DEPLOYMENT_QUICKSTART.md (moved to docs/deployment/quickstart.md)
  - RUNTIME_CONFIG.md (moved to docs/deployment/configuration.md)
  - DOCKER_PORTS.md (consolidated into docs/deployment/docker.md)
  - DOCKER_CACHE_OPTIMIZATION.md (consolidated into docs/deployment/docker.md)
  - TESTING_E2E.md (consolidated into docs/developer/TESTING.md)
  - TESTING_COVERAGE.md (consolidated into docs/developer/TESTING.md)
  - TESTING_OAUTH.md (consolidated into docs/developer/TESTING.md)
  - docs/DATABASE_SCHEMA.md (moved to docs/developer/database.md)
  - docs/oauth-flow.md (moved to docs/developer/oauth-flow.md)
  - docs/TRANSACTION_MANAGEMENT.md (moved to docs/developer/transaction-management.md)
  - docs/DEFERRED_EVENT_PUBLISHING.md (moved to docs/developer/deferred-events.md)
  - docs/DOCKER_COMPOSE_DEPENDENCIES.md (consolidated or moved)
  - docs/CLOUDFLARE_TUNNEL_SETUP.md (moved to docs/developer/cloudflare-tunnel.md)
  - docs/LOCAL_TESTING_WITH_ACT.md (moved to docs/developer/local-act-testing.md)
  - docs/PRODUCTION_READINESS_GUILD_ISOLATION.md (moved to docs/developer/production-readiness.md)
  - .copilot-tracking/research/20251224-microservice-communication-architecture.md (moved to docs/developer/architecture.md)
- **Success**:
  - All moved files deleted after verification
  - No duplicate documentation exists
- **Research References**:
  - #file:../research/20260201-documentation-reorganization-by-persona-research.md (Lines 196-198) - Cleanup phase
- **Dependencies**:
  - All Phase 1-3 tasks completed (new files created and content verified)

### Task 4.2: Update all internal documentation links

Update cross-references in all documentation files to reflect new locations.

- **Files**:
  - README.md - Update all internal links to docs/ files
  - All docs/ files - Update cross-references to moved documentation
  - compose.*.yaml files - Update documentation reference comments if present
  - scripts/*.sh - Update documentation references in script comments
- **Search Pattern**: Find references to moved files (e.g., "TESTING_E2E.md", "DEPLOYMENT_QUICKSTART.md")
- **Success**:
  - No broken internal links in any documentation
  - All references to moved files updated to new paths
  - Relative links work correctly from all locations
- **Research References**:
  - #file:../research/20260201-documentation-reorganization-by-persona-research.md (Lines 200-202) - Link updates
- **Dependencies**:
  - Task 4.1 completed (files moved and originals deleted)

### Task 4.3: Add navigation links between related documents

Create navigation paths between related documentation.

- **Files**:
  - All docs/ files - Add "Related Documentation" sections at bottom
  - Gateway README files - Ensure comprehensive linking to related content
- **Success**:
  - Related documents linked at bottom of each file
  - Gateway READMEs provide clear navigation to all subdocuments
  - User personas can easily navigate to related topics
  - Developer topics interconnected appropriately
- **Research References**:
  - #file:../research/20260201-documentation-reorganization-by-persona-research.md (Lines 204-206) - Navigation links
- **Dependencies**:
  - Task 4.2 completed (all links updated)

### Task 4.4: Update .github/instructions references to moved files

Update instruction files that reference moved documentation.

- **Files**:
  - .github/instructions/*.instructions.md - Update all documentation references
  - .github/copilot-instructions.md - Update documentation references if present
- **Search Pattern**: Find references to moved documentation files in instruction files
- **Success**:
  - All instruction file references updated to new documentation locations
  - No broken references in GitHub Copilot instruction files
  - Instruction files accurately reference stable documentation locations
- **Research References**:
  - #file:../research/20260201-documentation-reorganization-by-persona-research.md (Lines 208-210) - Instruction updates
- **Dependencies**:
  - Task 4.1 completed (files in final locations)

## Dependencies

- Markdown formatting tools (markdownlint)
- Access to codebase for content extraction
- User interaction for terminology and workflow clarification

## Success Criteria

- All five personas can navigate to their documentation in ≤2 clicks
- User-facing documentation accurately reflects current features
- Technical documentation comprehensively organized
- No broken links in any documentation
- All code references updated
