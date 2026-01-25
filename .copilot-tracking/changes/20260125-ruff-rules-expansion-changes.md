<!-- markdownlint-disable-file -->

# Release Changes: Ruff Linting Rules Expansion

**Related Plan**: 20260125-ruff-rules-expansion-plan.instructions.md
**Implementation Date**: 2026-01-25

## Summary

Incrementally expanding Ruff linting rules across 7 phases to address 878 violations, fixing all issues before enabling each rule category to maintain zero-violation baseline.

## Changes

### Added

### Modified

- services/init/database_users.py - Fixed SQL injection vulnerability (S608) by using sql.Identifier for safe SQL construction
- services/init/verify_schema.py - Fixed SQL injection vulnerability (S608) by using sql.Identifier for table names
- services/init/migrations.py - Fixed subprocess security issues (S603/S607) by using shutil.which() for absolute executable paths
- scripts/check_commit_duplicates.py - Fixed subprocess security issues (S603/S607) by using shutil.which() for absolute executable paths

### Removed
