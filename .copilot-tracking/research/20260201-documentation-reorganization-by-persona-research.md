<!-- markdownlint-disable-file -->
# Task Research Notes: Documentation Reorganization by User Persona

## Research Executed

### Current Documentation Analysis

Current documentation is heavily developer-focused with limited user/guild-admin content:

**Root-level documentation** (18 files):
- README.md (511 lines) - Architecture + complete development setup
- DEPLOYMENT_QUICKSTART.md - Server deployment for self-hosting
- TESTING_E2E.md (650 lines) - E2E test setup with Discord bots
- TESTING_COVERAGE.md - Test coverage collection
- TESTING_OAUTH.md - OAuth testing
- DOCKER_PORTS.md - Port exposure strategy
- DOCKER_CACHE_OPTIMIZATION.md - BuildKit cache mounts
- VERSION_MANAGEMENT.md - Version tracking with setuptools-scm
- RUNTIME_CONFIG.md (471 lines) - Runtime configuration options
- COPYING.txt - License information

**docs/ subdirectory** (8 files):
- CLOUDFLARE_TUNNEL_SETUP.md - Local dev with Cloudflare Tunnel
- DATABASE_SCHEMA.md - ERD and RLS documentation
- DEFERRED_EVENT_PUBLISHING.md - Event architecture details
- DOCKER_COMPOSE_DEPENDENCIES.md - Dependency graph
- LOCAL_TESTING_WITH_ACT.md - Local GitHub Actions testing
- oauth-flow.md - OAuth sequence diagram
- PRODUCTION_READINESS_GUILD_ISOLATION.md - Multi-tenant security
- TRANSACTION_MANAGEMENT.md (398 lines) - Service layer patterns

**Developer research** (hidden in .copilot-tracking):
- .copilot-tracking/research/20251224-microservice-communication-architecture.md - Complete system architecture with Mermaid diagrams (248 lines)

### Content Classification by Persona

**Guild Admin Content** (currently missing):
- ❌ How to add bot to Discord guild
- ❌ How to configure bot manager roles
- ❌ How to set up channels for game announcements
- ❌ How to create game templates
- ❌ Permissions required for bot invite
- ⚠️ TESTING_E2E.md has bot invite URLs (lines 70-87) but for testing only

**Game Host Content** (currently missing):
- ❌ How to create a game
- ❌ How to edit game details
- ❌ How to manage participants
- ❌ How to use templates
- ❌ Web dashboard access and usage
- ❌ Discord button interactions

**Player Content** (currently missing):
- ❌ How to join/leave games via Discord buttons
- ❌ How to view scheduled games
- ❌ What notifications to expect
- ❌ Calendar download feature

**Developer Content** (exists but scattered):
- ✅ Development setup (README.md)
- ✅ Testing guides (TESTING_E2E.md, TESTING_COVERAGE.md)
- ✅ Architecture (hidden in .copilot-tracking, should be in docs/)
- ✅ Database schema (docs/DATABASE_SCHEMA.md)
- ✅ Transaction patterns (docs/TRANSACTION_MANAGEMENT.md)
- ✅ OAuth flow (docs/oauth-flow.md)
- ✅ Deployment (DEPLOYMENT_QUICKSTART.md)

**Self-Hosting Admin Content** (partially exists):
- ✅ DEPLOYMENT_QUICKSTART.md - Server setup
- ✅ RUNTIME_CONFIG.md - Configuration options
- ✅ DOCKER_PORTS.md - Port management
- ⚠️ Missing: backup/restore procedures, monitoring setup, security hardening

## Key Discoveries

### Persona Identification

Based on the application features and existing documentation, five distinct personas emerge:

1. **Guild Admin** - Discord server owner/admin who adds the bot
   - Needs: Bot invite instructions, permission explanations, role configuration
   - Current gaps: No user-facing documentation exists

2. **Game Host** - User who creates and manages games
   - Needs: Game creation guide, template usage, participant management
   - Current gaps: No user-facing documentation exists

3. **Player** - User who joins/leaves games
   - Needs: Simple "how to use" guide, button explanations, notification info
   - Current gaps: No user-facing documentation exists

4. **Developer** - Contributor to the codebase
   - Needs: Architecture, setup, testing, conventions
   - Current state: Well-documented but scattered across root and docs/

5. **Self-Hosting Admin** - Deployer running their own instance
   - Needs: Deployment, configuration, monitoring, maintenance
   - Current state: Deployment covered, monitoring/maintenance partially documented

### Documentation Organization Patterns

**Option A: Subdirectories per Persona**
```
docs/
├── guild-admin/
│   ├── README.md (Getting Started)
│   ├── bot-invite.md
│   ├── role-configuration.md
│   └── template-management.md
├── host/
│   ├── README.md (Getting Started)
│   ├── creating-games.md
│   └── managing-participants.md
├── player/
│   └── README.md (Quick Start Guide)
├── developer/
│   ├── README.md (Development Overview)
│   ├── architecture.md
│   ├── testing.md
│   └── database.md
└── deployment/
    ├── README.md (Deployment Overview)
    ├── quickstart.md
    └── monitoring.md
```

**Benefits:**
- Clear separation of concerns
- Easy to find all documentation for a specific persona
- Can include persona-specific images/diagrams in subdirectories
- Scales well as documentation grows

**Drawbacks:**
- More navigation required (extra click to find docs)
- Harder to see "all available docs" at a glance

**Option B: Persona-Specific README Files**
```
docs/
├── README-GUILD-ADMIN.md
├── README-HOST.md
├── README-PLAYER.md
├── README-DEVELOPER.md
├── README-DEPLOYMENT.md
├── architecture.md (linked from developer)
├── testing.md (linked from developer)
└── database.md (linked from developer)
```

**Benefits:**
- All personas visible in single directory listing
- Less navigation (everything at one level)
- Quick access pattern: "Open docs/, find my persona README"

**Drawbacks:**
- Directory becomes cluttered as docs grow
- Harder to organize related images/assets
- Less clear ownership of shared technical docs

**Option C: Hybrid Approach**
```
README.md (Project overview + persona gateway)
docs/
├── GUILD-ADMIN.md (Getting Started)
├── HOST-GUIDE.md (Game Management)
├── PLAYER-GUIDE.md (Quick Start)
├── developer/
│   ├── README.md (Development Overview)
│   ├── SETUP.md (moved from root)
│   ├── TESTING.md (consolidated testing docs)
│   ├── architecture.md (moved from .copilot-tracking)
│   ├── database.md
│   ├── oauth-flow.md
│   └── transaction-management.md
└── deployment/
    ├── README.md (Self-Hosting Overview)
    ├── quickstart.md
    ├── configuration.md
    └── docker.md
```

**Benefits:**
- Simple docs for end-users at top level (guild admin, host, player)
- Complex docs organized in subdirectories (developer, deployment)
- Matches user complexity: simpler personas = simpler file structure
- Root README acts as gateway to all personas

**Drawbacks:**
- Mixed organizational pattern (flat + nested)
- Requires careful naming to distinguish user guides from technical docs

### Recommended Approach: Option C (Hybrid)

**Rationale:**
1. **End-user simplicity**: Guild admins, hosts, and players need straightforward single-file guides
2. **Developer depth**: Developers need organized, deep technical documentation
3. **Gateway pattern**: Root README becomes the entry point directing users to appropriate content
4. **Migration friendly**: Existing developer docs move to `docs/developer/` without URL breakage concerns
5. **Scalability**: Simple guides stay simple, complex areas can expand with subdirectories

### Missing Content to Create

**Content Creation Methodology:**
All user-facing documentation should be created by:
1. Extracting information from codebase, API routes, and frontend components
2. Reviewing actual feature implementations to document current behavior
3. Interacting with user to clarify workflows, terminology, and edge cases
4. Validating against actual Discord bot interactions and web dashboard UX

**GUILD-ADMIN.md** (new):
- Prerequisites: Discord server ownership/admin permissions
- Bot invite URL generation (extract from TESTING_E2E.md and adapt)
- Required permissions explanation (review Discord bot permissions in code)
- Bot manager role configuration (extract from guild_configurations model/API)
- Channel setup for game announcements (extract from channel_configurations)
- Creating and managing game templates (extract from game_templates API/frontend)

**HOST-GUIDE.md** (new):
- Accessing the web dashboard (extract frontend URL and routes)
- Discord OAuth login process (extract from oauth-flow.md and frontend auth)
- Creating a game (step-by-step from CreateGame page/API)
- Using templates (extract from frontend GameForm template selection)
- Managing participants (extract from API participant endpoints)
- Editing game details (extract from frontend edit flows)
- Canceling games (extract from API game cancellation)
- Understanding host-only features (extract from bot manager permissions)

**PLAYER-GUIDE.md** (new):
- Finding scheduled games in Discord (describe bot announcement messages)
- Joining a game (extract Discord button interactions from bot code)
- Leaving a game (extract Discord button interactions from bot code)
- Understanding waitlist mechanics (extract from game_participants logic)
- Notification timing (extract from notification_schedule system)
- Calendar download feature (extract from calendar download API)
- Viewing game details (extract from Discord message embeds)

**docs/developer/README.md** (new gateway):
- Link to SETUP.md (development environment)
- Link to architecture.md (system design)
- Link to TESTING.md (consolidated testing guide)
- Link to database.md, oauth-flow.md, transaction-management.md
- Contributing guidelines
- Code quality standards (ruff rules)

**docs/developer/SETUP.md** (moved from README.md):
- Extract "Development Setup" section (lines ~80-250)
- Quick Start, Development Workflow, Pre-commit Hooks
- Keep focused on getting a dev environment running

**docs/developer/TESTING.md** (consolidated):
- Merge content from TESTING_E2E.md, TESTING_COVERAGE.md, TESTING_OAUTH.md
- Organize by test type (unit, integration, e2e)
- Common patterns and helpers

**docs/developer/architecture.md** (moved):
- Move from .copilot-tracking/research/20251224-microservice-communication-architecture.md
- This is stable architecture documentation, not temporary research

**docs/deployment/README.md** (new gateway):
- Self-hosting overview
- Link to quickstart.md, configuration.md, docker.md
- System requirements
- Security considerations

**docs/deployment/quickstart.md** (moved from DEPLOYMENT_QUICKSTART.md):
- Current content from root-level file

**docs/deployment/configuration.md** (moved from RUNTIME_CONFIG.md):
- Runtime configuration options
- Environment variables
- Frontend proxy vs direct API modes

**docs/deployment/docker.md** (consolidated):
- Move DOCKER_PORTS.md
- Move DOCKER_CACHE_OPTIMIZATION.md
- Move DOCKER_COMPOSE_DEPENDENCIES.md content
- Single reference for Docker-related deployment topics

### Root README.md Restructuring

**Current Structure:**
1. Architecture section (lines 13-58)
2. Development Setup (lines 60-250)
3. Code Quality Standards (lines 251-300)
4. Access Services (lines 301-320)
5. Project Structure (lines 460-490)
6. Docker Compose Architecture (lines 491-511)

**Proposed New Structure:**
```markdown
# Game Scheduler

A Discord game scheduling system with web dashboard and automated notifications.

## What is Game Scheduler?

[Brief 2-3 sentence explanation]

## For Guild Admins

Want to add this bot to your Discord server?
→ See [Guild Admin Guide](docs/GUILD-ADMIN.md)

## For Game Hosts

Want to create and manage games?
→ See [Host Guide](docs/HOST-GUIDE.md)

## For Players

Want to join games and receive notifications?
→ See [Player Guide](docs/PLAYER-GUIDE.md)

## For Developers

Want to contribute or run a development environment?
→ See [Developer Documentation](docs/developer/README.md)

## For Self-Hosters

Want to deploy your own instance?
→ See [Deployment Guide](docs/deployment/README.md)

## Key Features

- Discord bot with button interactions
- Web dashboard with Discord OAuth
- Multi-channel support
- Automated notifications
- Game templates

## Architecture Overview

[Brief architecture description with link to docs/developer/architecture.md]

## License

[Existing license section]
```

## Recommended Approach

**User Decision: Hybrid Approach (Option C) CONFIRMED**

**Execution Strategy:**
- Planning agent will organize and execute implementation phases
- User-facing docs created by extracting from code/APIs with user clarification as needed
- Files moved directly to new locations with reference updates (no redirects needed)

**Phase 1: Create User-Facing Documentation**
1. Create `docs/GUILD-ADMIN.md` - Extract bot setup from code/TESTING_E2E.md, clarify with user
2. Create `docs/HOST-GUIDE.md` - Extract from CreateGame frontend/API, clarify workflows with user
3. Create `docs/PLAYER-GUIDE.md` - Extract from Discord bot interactions, clarify UX with user
4. Update root `README.md` with persona gateway structure

**Phase 2: Reorganize Developer Documentation**
5. Create `docs/developer/` subdirectory
6. Create `docs/developer/README.md` as gateway
7. Move development setup: Extract from README.md → `docs/developer/SETUP.md`
8. Move architecture: `.copilot-tracking/research/20251224-microservice-communication-architecture.md` → `docs/developer/architecture.md`
9. Consolidate testing: Merge TESTING_E2E.md + TESTING_COVERAGE.md + TESTING_OAUTH.md → `docs/developer/TESTING.md`
10. Move existing technical docs: DATABASE_SCHEMA.md, oauth-flow.md, TRANSACTION_MANAGEMENT.md → `docs/developer/`
11. Move CLOUDFLARE_TUNNEL_SETUP.md, LOCAL_TESTING_WITH_ACT.md → `docs/developer/`

**Phase 3: Organize Deployment Documentation**
12. Create `docs/deployment/` subdirectory
13. Create `docs/deployment/README.md` as gateway
14. Move DEPLOYMENT_QUICKSTART.md → `docs/deployment/quickstart.md`
15. Move RUNTIME_CONFIG.md → `docs/deployment/configuration.md`
16. Consolidate Docker docs: DOCKER_PORTS.md + DOCKER_CACHE_OPTIMIZATION.md → `docs/deployment/docker.md`
17. Move VERSION_MANAGEMENT.md → `docs/deployment/` (relates to deployment versioning)

**Phase 4: Cleanup**
18. Delete old files from root after moving
19. Update all internal documentation links (README, compose files, scripts)
20. Add navigation links between related documents
21. Update any .github/instructions references to moved files

## Implementation Guidance

**Objectives:**
- Create clear documentation paths for each user persona
- Reduce developer-focused content in root README
- Move architecture doc from .copilot-tracking to stable location
- Establish scalable documentation structure

**Key Tasks:**
1. Write user-facing guides (GUILD-ADMIN, HOST-GUIDE, PLAYER-GUIDE)
2. Restructure root README as persona gateway
3. Organize developer docs in `docs/developer/`
4. Organize deployment docs in `docs/deployment/`
5. Update all cross-references and links

**Dependencies:**
- Review TESTING_E2E.md lines 70-87 for bot invite URL patterns
- Extract OAuth login flow from docs/oauth-flow.md for HOST-GUIDE
- Review API routes in services/api/routes/ for feature inventory
- Review frontend pages in frontend/src/pages/ for user workflows
- Review Discord bot interactions in services/bot/ for button behaviors
- Review game_participants logic for waitlist mechanics
- Review notification_schedule system for timing details
- Interact with user to clarify terminology, workflows, and edge cases

**Success Criteria:**
- Each persona can find their documentation in ≤2 clicks
- Root README provides clear entry point for all personas
- User-facing docs accurately reflect current feature implementations
- Developer docs are organized and comprehensive
- No broken internal links
- Architecture documentation is in stable location (not .copilot-tracking)
- All references in code/scripts updated to new locations
