<!-- markdownlint-disable-file -->

# Release Changes: MIT license migration for Game Scheduler

**Related Plan**: 20260204-mit-license-migration.plan.md
**Implementation Date**: 2026-02-04

## Summary

Migration from AGPL-3.0-or-later to MIT license across all project artifacts, source headers, metadata, and documentation.

## Changes

### Added

- [templates/mit-template.jinja2](templates/mit-template.jinja2) - Created MIT license header template for autocopyright tool based on simplified MIT.md.jinja2 pattern (copyright line without email, full MIT license text)

### Modified

- [COPYING.txt](COPYING.txt) - Replaced AGPL-3.0-or-later license text with MIT license text; updated copyright year to 2025-2026
- [scripts/add-copyright](scripts/add-copyright) - Updated template path from agpl-template.jinja2 to mit-template.jinja2 for both Python and TypeScript/TSX file processing
- [.pre-commit-config.yaml](.pre-commit-config.yaml) - Updated template path from agpl-template.jinja2 to mit-template.jinja2 for both Python and TypeScript pre-commit hooks
- [pyproject.toml](pyproject.toml#L7) - Changed project license metadata from "AGPL-3.0-or-later" to "MIT"
- alembic/\*_/_.py (15 files) - Applied MIT license headers; removed AGPL headers; updated copyright to 2025-2026 for files originally from 2025, kept 2026 for files originally from 2026
- services/\*_/_.py (99 files) - Applied MIT license headers; removed AGPL headers; updated copyright to 2025-2026 for files originally from 2025, kept 2026 for files originally from 2026
- shared/\*_/_.py (56 files) - Applied MIT license headers; removed AGPL headers; updated copyright to 2025-2026 for files originally from 2025, kept 2026 for files originally from 2026
- tests/\*_/_.py (189 files) - Applied MIT license headers; removed AGPL headers; updated copyright to 2025-2026 for files originally from 2025, kept 2026 for files originally from 2026
- frontend/src/\*_/_.ts (12 files) - Applied MIT license headers; removed AGPL headers; updated copyright to 2025-2026 for files originally from 2025, kept 2026 for files originally from 2026
- frontend/src/\*_/_.tsx (44 files) - Applied MIT license headers; removed AGPL headers; updated copyright to 2025-2026 for files originally from 2025, kept 2026 for files originally from 2026

### Removed

- templates/agpl-template.jinja2 - Removed obsolete AGPL header template file
- README.md - Replaced AGPL license references with MIT license; updated copyright year to 2025-2026
- frontend/src/pages/About.tsx - Replaced AGPL license text and GNU URL with MIT license text and OSI MIT URL; updated copyright year to 2025-2026
- frontend/src/pages/**tests**/About.test.tsx - Updated test assertions to verify MIT license text and opensource.org link instead of AGPL and gnu.org

## Release Summary

**Total Files Affected**: 421

### Files Created (1)

- templates/mit-template.jinja2 - MIT license header template for autocopyright tool

### Files Modified (419)

- COPYING.txt - MIT license text replacement
- scripts/add-copyright - Template path update to MIT template
- pyproject.toml - License metadata update to MIT
- README.md - License section updated to MIT with 2025-2026 copyright
- frontend/src/pages/About.tsx - License display updated to MIT with 2025-2026 copyright
- frontend/src/pages/**tests**/About.test.tsx - Test assertions updated for MIT license
- alembic/\*_/_.py (15 files) - MIT license headers with year adjustments
- services/\*_/_.py (99 files) - MIT license headers with year adjustments
- shared/\*_/_.py (56 files) - MIT license headers with year adjustments
- tests/\*_/_.py (189 files) - MIT license headers with year adjustments
- frontend/src/\*_/_.ts (12 files) - MIT license headers with year adjustments
- frontend/src/\*_/_.tsx (44 files) - MIT license headers with year adjustments

### Files Removed (1)

- templates/agpl-template.jinja2 - Obsolete AGPL template removed

### Dependencies & Infrastructure

- **New Dependencies**: None
- **Updated Dependencies**: None
- **Infrastructure Changes**: MIT license template integrated with autocopyright workflow
- **Configuration Updates**: pyproject.toml license metadata changed to MIT

### Deployment Notes

This is a licensing change only. No functional changes to the application. All source files now carry MIT license headers. Users and contributors should be aware of the license change from AGPL-3.0-or-later to MIT.
