<!-- markdownlint-disable-file -->

# Release Changes: Documentation Reorganization by User Persona

**Related Plan**: 20260201-documentation-reorganization-by-persona.plan.md
**Implementation Date**: 2026-02-01

## Summary

Reorganizing project documentation into persona-based structure with user-facing guides and organized developer/deployment documentation.

## Changes

### Added

- docs/GUILD-ADMIN.md - Comprehensive guild administrator guide covering bot invite, permissions, role configuration, channel setup, and game templates
- docs/HOST-GUIDE.md - Complete game host guide covering web dashboard access, OAuth login, game creation with templates, participant management, and host permissions
- docs/PLAYER-GUIDE.md - Simple player guide covering Discord button interactions, join/leave mechanics, waitlist system, notification types and timing, and calendar download feature
- docs/developer/README.md - Placeholder gateway file for developer documentation (to be populated in Phase 2)
- docs/deployment/README.md - Placeholder gateway file for deployment documentation (to be populated in Phase 3)
- docs/developer/SETUP.md - Comprehensive development environment setup guide extracted from README with quick start, development workflow, pre-commit hooks, code quality standards, testing, environment configuration, and production builds
- docs/deployment/quickstart.md - Moved from DEPLOYMENT_QUICKSTART.md with complete deployment quickstart guide for new servers, including environment configuration, build/start procedures, production deployment management, and DLQ migration instructions
- docs/deployment/configuration.md - Moved from RUNTIME_CONFIG.md with comprehensive runtime configuration guide covering frontend configuration, RabbitMQ setup, retry service DLQ processing, and OpenTelemetry observability
- docs/deployment/docker.md - Consolidated Docker deployment guide from DOCKER_PORTS.md and DOCKER_CACHE_OPTIMIZATION.md covering port exposure strategy, debugging infrastructure services, build cache optimization, version management, observability architecture, and common Docker operations
- docs/deployment/version-management.md - Moved from VERSION_MANAGEMENT.md with detailed automatic versioning documentation using setuptools-scm

### Modified

- README.md - Refactored to be concise gateway document (~60 lines vs original 527 lines)
  - Removed extensive architecture details (maintained in docs/developer/architecture.md)
  - Removed detailed development setup (maintained in docs/developer/SETUP.md)
  - Removed pre-commit hooks documentation (maintained in docs/developer/README.md)
  - Removed code quality standards (maintained in docs/developer/README.md)
  - Removed running services individually (maintained in docs/deployment/)
  - Removed building multi-architecture images (maintained in docs/deployment/docker.md)
  - Removed project structure details (maintained in docs/developer/architecture.md)
  - Removed Docker Compose architecture details (maintained in docs/deployment/docker.md)
  - Retained: Quick Links by Role, brief What is Game Scheduler, Key Features, Quick Start sections
- docs/HOST-GUIDE.md - Updated troubleshooting section to direct hosts to contact guild administrators for bot permission issues (hosts cannot change permissions themselves)
- docs/GUILD-ADMIN.md - Removed Developer Portal instructions (only relevant for developers/self-hosters), replaced with instructions to obtain pre-generated invite URL from bot owner or deployment docs
- docs/developer/README.md - Populated comprehensive developer gateway with links to setup, architecture, testing, database schema, OAuth flow, transaction management, and contributing guidelines
- docs/developer/SETUP.md - Comprehensive development environment setup guide extracted from README with quick start, development workflow, pre-commit hooks, code quality standards, testing, environment configuration, and production builds; updated to reference deployment guide (not guild admin guide) for bot creation instructions; added explicit dev container documentation as recommended development approach with clarification that all pre-commit hooks work immediately in dev container without manual dependency installation; added context about pre-commit hooks being essential for verifying AI-generated code meets project standards
- docs/developer/architecture.md - Moved and reformatted architecture documentation from research location to stable docs, including system architecture diagrams, event communication patterns, service responsibilities, database-driven scheduling, Row-Level Security, and scalability considerations; verified against current codebase to document only actively used events
- docs/developer/TESTING.md - Consolidated comprehensive testing guide from TESTING_E2E.md, TESTING_COVERAGE.md, and TESTING_OAUTH.md into single document covering unit tests, integration tests, end-to-end tests, coverage collection, OAuth testing, test infrastructure, CI/CD integration, and troubleshooting
- docs/developer/database.md - Moved from docs/DATABASE_SCHEMA.md with consistent lowercase naming
- docs/developer/oauth-flow.md - Moved from docs/oauth-flow.md
- docs/developer/transaction-management.md - Moved from docs/TRANSACTION_MANAGEMENT.md with consistent lowercase naming
- docs/developer/deferred-events.md - Moved from docs/DEFERRED_EVENT_PUBLISHING.md with consistent lowercase naming
- docs/developer/compose-dependencies.md - Moved from docs/DOCKER_COMPOSE_DEPENDENCIES.md with consistent lowercase naming
- docs/developer/cloudflare-tunnel.md - Moved from docs/CLOUDFLARE_TUNNEL_SETUP.md with consistent lowercase naming
- docs/developer/local-act-testing.md - Moved from docs/LOCAL_TESTING_WITH_ACT.md with consistent lowercase naming
- docs/developer/production-readiness.md - Moved from docs/PRODUCTION_READINESS_GUILD_ISOLATION.md with consistent lowercase naming
- docs/deployment/README.md - Populated comprehensive deployment gateway with system requirements, prerequisites, deployment workflow, security considerations, environment configuration files, version management, observability integration, and support resources
- docs/deployment/quickstart.md - Updated internal documentation links to reference new locations (configuration.md instead of RUNTIME_CONFIG.md)
- docs/deployment/docker.md - Consolidated comprehensive Docker guide covering port exposure strategy, debugging infrastructure services, build cache optimization, version management, observability architecture, and common Docker operations
- README.md - Updated documentation link from TESTING_E2E.md to docs/developer/TESTING.md
- config.template/env.template - Updated documentation reference from DOCKER_PORTS.md to docs/deployment/docker.md
- .github/instructions/fastapi-transaction-patterns.instructions.md - Updated documentation reference from docs/TRANSACTION_MANAGEMENT.md to docs/developer/transaction-management.md
- scripts/coverage-report.sh - Updated documentation reference from TESTING_E2E.md to docs/developer/TESTING.md
- scripts/run-e2e-tests.sh - Updated all documentation references from TESTING_E2E.md to docs/developer/TESTING.md
- docs/GUILD-ADMIN.md - Contains navigation links in Next Steps section to HOST-GUIDE, PLAYER-GUIDE, and developer docs (no changes needed)
- docs/HOST-GUIDE.md - Contains navigation links in Next Steps section to GUILD-ADMIN, PLAYER-GUIDE, and developer docs (no changes needed)
- docs/PLAYER-GUIDE.md - Contains navigation links in Next Steps section to HOST-GUIDE, GUILD-ADMIN, and developer docs (no changes needed)

### Removed

- DEPLOYMENT_QUICKSTART.md - Moved to docs/deployment/quickstart.md
- RUNTIME_CONFIG.md - Moved to docs/deployment/configuration.md
- DOCKER_PORTS.md - Consolidated into docs/deployment/docker.md
- DOCKER_CACHE_OPTIMIZATION.md - Consolidated into docs/deployment/docker.md
- TESTING_E2E.md - Consolidated into docs/developer/TESTING.md
- TESTING_COVERAGE.md - Consolidated into docs/developer/TESTING.md
- TESTING_OAUTH.md - Consolidated into docs/developer/TESTING.md
- VERSION_MANAGEMENT.md - Moved to docs/deployment/version-management.md
- .copilot-tracking/research/20251224-microservice-communication-architecture.md - Moved to stable location at docs/developer/architecture.md

## Release Summary

**Total Files Affected**: 37

### Files Created (10)

- docs/GUILD-ADMIN.md - Comprehensive guild administrator guide with bot setup, permissions, and template management
- docs/HOST-GUIDE.md - Complete game host guide with dashboard usage and game management workflows
- docs/PLAYER-GUIDE.md - Simple player guide with Discord button interactions and calendar features
- docs/developer/SETUP.md - Development environment setup guide with quick start and pre-commit hooks
- docs/developer/architecture.md - System architecture documentation with diagrams and event communication patterns
- docs/developer/TESTING.md - Consolidated testing guide covering unit, integration, and E2E testing
- docs/deployment/quickstart.md - Deployment quickstart for new servers with environment configuration
- docs/deployment/configuration.md - Runtime configuration guide for frontend, RabbitMQ, and observability
- docs/deployment/docker.md - Comprehensive Docker deployment guide with port strategy and optimization
- docs/deployment/version-management.md - Automatic versioning documentation using setuptools-scm

### Files Modified (22)

- README.md - Refactored to be concise gateway document (~60 lines vs original 527 lines) with persona-based Quick Links, brief description, key features, and quick start sections
- docs/developer/README.md - Populated comprehensive developer gateway with all technical documentation links
- docs/deployment/README.md - Populated comprehensive deployment gateway with system requirements and workflow
- docs/GUILD-ADMIN.md - Updated to remove Developer Portal instructions (now in deployment docs)
- docs/HOST-GUIDE.md - Updated troubleshooting section to direct hosts to guild administrators
- docs/developer/SETUP.md - Enhanced with dev container documentation and pre-commit hook context
- docs/developer/architecture.md - Reformatted and verified against current codebase (actively used events only)
- docs/developer/database.md - Moved from docs/DATABASE_SCHEMA.md with consistent lowercase naming
- docs/developer/oauth-flow.md - Moved from docs/oauth-flow.md
- docs/developer/transaction-management.md - Moved from docs/TRANSACTION_MANAGEMENT.md with consistent lowercase naming
- docs/developer/deferred-events.md - Moved from docs/DEFERRED_EVENT_PUBLISHING.md with consistent lowercase naming
- docs/developer/compose-dependencies.md - Moved from docs/DOCKER_COMPOSE_DEPENDENCIES.md with consistent lowercase naming
- docs/developer/cloudflare-tunnel.md - Moved from docs/CLOUDFLARE_TUNNEL_SETUP.md with consistent lowercase naming
- docs/developer/local-act-testing.md - Moved from docs/LOCAL_TESTING_WITH_ACT.md with consistent lowercase naming
- docs/developer/production-readiness.md - Moved from docs/PRODUCTION_READINESS_GUILD_ISOLATION.md with consistent lowercase naming
- docs/deployment/quickstart.md - Updated internal documentation links to new locations
- config.template/env.template - Updated documentation reference to docs/deployment/docker.md
- .github/instructions/fastapi-transaction-patterns.instructions.md - Updated documentation reference to docs/developer/transaction-management.md
- scripts/coverage-report.sh - Updated documentation reference to docs/developer/TESTING.md
- scripts/run-e2e-tests.sh - Updated all documentation references to docs/developer/TESTING.md
- docs/GUILD-ADMIN.md, docs/HOST-GUIDE.md, docs/PLAYER-GUIDE.md - Verified navigation links in Next Steps sections (already present)

### Files Removed (9)

- DEPLOYMENT_QUICKSTART.md
- RUNTIME_CONFIG.md
- DOCKER_PORTS.md
- DOCKER_CACHE_OPTIMIZATION.md
- TESTING_E2E.md
- TESTING_COVERAGE.md
- TESTING_OAUTH.md
- VERSION_MANAGEMENT.md
- .copilot-tracking/research/20251224-microservice-communication-architecture.md

### Dependencies & Infrastructure

- **New Dependencies**: None
- **Updated Dependencies**: None
- **Infrastructure Changes**: None
- **Configuration Updates**: Documentation paths updated in config.template/env.template and scripts

### Deployment Notes

This is a documentation-only reorganization. No code changes, database migrations, or service restarts are required. All documentation is now organized by user persona:

- **Guild Admins**: docs/GUILD-ADMIN.md
- **Game Hosts**: docs/HOST-GUIDE.md
- **Players**: docs/PLAYER-GUIDE.md
- **Developers**: docs/developer/ (gateway at docs/developer/README.md)
- **Self-Hosters**: docs/deployment/ (gateway at docs/deployment/README.md)

All internal documentation links have been updated. No broken links remain.
