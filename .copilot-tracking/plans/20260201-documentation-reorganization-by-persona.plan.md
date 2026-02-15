---
applyTo: '.copilot-tracking/changes/20260201-documentation-reorganization-by-persona-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Documentation Reorganization by User Persona

## Overview

Reorganize project documentation into persona-based structure with user-facing guides and organized developer/deployment documentation.

## Objectives

- Create clear documentation paths for each user persona (Guild Admin, Host, Player, Developer, Self-Hoster)
- Move user-facing content to simple single-file guides at docs/ level
- Organize complex technical content in docs/developer/ and docs/deployment/ subdirectories
- Restructure root README as persona gateway
- Move architecture documentation from .copilot-tracking to stable location

## Research Summary

### Project Files

- README.md - Current architecture + development setup requiring restructuring
- TESTING_E2E.md - Bot invite URLs and testing setup (lines 70-87 have invite patterns)
- docs/oauth-flow.md - OAuth sequence for HOST-GUIDE reference
- services/api/routes/ - Feature inventory for user guide content
- frontend/src/pages/ - User workflow patterns
- services/bot/ - Discord button interactions
- .copilot-tracking/research/20251224-microservice-communication-architecture.md - Architecture doc to move

### External References

- #file:../research/20260201-documentation-reorganization-by-persona-research.md - Complete documentation audit and reorganization strategy

### Standards References

- #file:../../.github/instructions/markdown.instructions.md - Documentation formatting standards

## Implementation Checklist

### [x] Phase 1: Create User-Facing Documentation

- [x] Task 1.1: Create docs/GUILD-ADMIN.md
  - Details: .copilot-tracking/details/20260201-documentation-reorganization-by-persona-details.md (Lines 12-29)

- [x] Task 1.2: Create docs/HOST-GUIDE.md
  - Details: .copilot-tracking/details/20260201-documentation-reorganization-by-persona-details.md (Lines 31-48)

- [x] Task 1.3: Create docs/PLAYER-GUIDE.md
  - Details: .copilot-tracking/details/20260201-documentation-reorganization-by-persona-details.md (Lines 50-67)

- [x] Task 1.4: Restructure root README.md as persona gateway
  - Details: .copilot-tracking/details/20260201-documentation-reorganization-by-persona-details.md (Lines 69-86)
  - Used placeholder README files to unblock - content populated in later phases

### [x] Phase 2: Reorganize Developer Documentation

- [x] Task 2.1: Create docs/developer/ subdirectory and gateway README
  - Details: .copilot-tracking/details/20260201-documentation-reorganization-by-persona-details.md (Lines 90-107)

- [x] Task 2.2: Extract development setup to docs/developer/SETUP.md
  - Details: .copilot-tracking/details/20260201-documentation-reorganization-by-persona-details.md (Lines 109-126)

- [x] Task 2.3: Move architecture documentation to docs/developer/architecture.md
  - Details: .copilot-tracking/details/20260201-documentation-reorganization-by-persona-details.md (Lines 128-145)

- [x] Task 2.4: Consolidate testing documentation into docs/developer/TESTING.md
  - Details: .copilot-tracking/details/20260201-documentation-reorganization-by-persona-details.md (Lines 147-164)

- [x] Task 2.5: Move existing technical docs to docs/developer/
  - Details: .copilot-tracking/details/20260201-documentation-reorganization-by-persona-details.md (Lines 166-183)

### [x] Phase 3: Organize Deployment Documentation

- [x] Task 3.1: Create docs/deployment/ subdirectory and gateway README
  - Details: .copilot-tracking/details/20260201-documentation-reorganization-by-persona-details.md (Lines 187-204)

- [x] Task 3.2: Move deployment quickstart to docs/deployment/quickstart.md
  - Details: .copilot-tracking/details/20260201-documentation-reorganization-by-persona-details.md (Lines 206-223)

- [x] Task 3.3: Move runtime configuration to docs/deployment/configuration.md
  - Details: .copilot-tracking/details/20260201-documentation-reorganization-by-persona-details.md (Lines 225-242)

- [x] Task 3.4: Consolidate Docker documentation into docs/deployment/docker.md
  - Details: .copilot-tracking/details/20260201-documentation-reorganization-by-persona-details.md (Lines 244-261)

### [x] Phase 4: Cleanup and Link Updates

- [x] Task 4.1: Delete moved files from root and docs/
  - Details: .copilot-tracking/details/20260201-documentation-reorganization-by-persona-details.md (Lines 265-282)

- [x] Task 4.2: Update all internal documentation links
  - Details: .copilot-tracking/details/20260201-documentation-reorganization-by-persona-details.md (Lines 284-301)

- [x] Task 4.3: Add navigation links between related documents
  - Details: .copilot-tracking/details/20260201-documentation-reorganization-by-persona-details.md (Lines 303-320)

- [x] Task 4.4: Update .github/instructions references to moved files
  - Details: .copilot-tracking/details/20260201-documentation-reorganization-by-persona-details.md (Lines 322-339)

## Dependencies

- Markdown formatting tools (markdownlint)
- Access to codebase for content extraction (services/api/routes/, frontend/src/pages/, services/bot/)
- User interaction for clarifying terminology and workflows

## Success Criteria

- All five personas can find their documentation in ≤2 clicks from root README
- User-facing guides (GUILD-ADMIN, HOST-GUIDE, PLAYER-GUIDE) accurately reflect current feature implementations
- Developer documentation is organized in docs/developer/ with comprehensive coverage
- Deployment documentation is organized in docs/deployment/ with all self-hosting information
- Architecture documentation moved from .copilot-tracking to stable docs/developer/ location
- No broken internal links in any documentation files
- All code/script references updated to new documentation locations
- Root README serves as effective persona gateway with clear navigation
