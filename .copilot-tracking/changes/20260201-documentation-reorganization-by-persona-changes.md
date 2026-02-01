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

### Modified

- README.md - Restructured as persona gateway with Quick Links by Role section, linking to all user-facing and technical documentation
- docs/HOST-GUIDE.md - Updated troubleshooting section to direct hosts to contact guild administrators for bot permission issues (hosts cannot change permissions themselves)
- docs/GUILD-ADMIN.md - Removed Developer Portal instructions (only relevant for developers/self-hosters), replaced with instructions to obtain pre-generated invite URL from bot owner or deployment docs

### Removed
