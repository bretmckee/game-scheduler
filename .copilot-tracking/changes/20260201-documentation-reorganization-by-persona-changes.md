<!-- markdownlint-disable-file -->

# Release Changes: Documentation Reorganization by User Persona

**Related Plan**: 20260201-documentation-reorganization-by-persona-plan.instructions.md
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

### Modified

- README.md - Restructured as persona gateway with Quick Links by Role section, linking to all user-facing and technical documentation
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

### Removed
