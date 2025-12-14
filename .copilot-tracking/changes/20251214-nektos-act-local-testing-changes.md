<!-- markdownlint-disable-file -->

# Release Changes: Local GitHub Actions Testing with nektos/act

**Related Plan**: 20251214-nektos-act-local-testing-plan.instructions.md
**Implementation Date**: 2025-12-14

## Summary

Enable local testing of GitHub Actions workflows using nektos/act to reduce CI/CD iteration time and catch issues before pushing to GitHub.

## Changes

### Added

- `.actrc` - Project-level act configuration with recommended settings for workflow execution
- `.secrets.example` - Template secrets file showing required format with placeholders
- `.env.act.example` - Template for act-specific environment variables with test service URLs
- `docs/LOCAL_TESTING_WITH_ACT.md` - Comprehensive usage documentation for local workflow testing

### Modified

- `.devcontainer/Dockerfile` - Added nektos/act v0.2.83 installation for local GitHub Actions testing (verified functional)
- `.gitignore` - Added entries for .secrets, .env.act, and .artifacts/ to prevent committing act-related files

### Removed

None

## Testing Verification

- ✅ Act version 0.2.83 verified functional
- ✅ Workflow listing successful (`act -l` shows 5 jobs: unit-tests, integration-tests, lint, frontend-test, build-and-publish)
- ✅ Dry run successful for unit-tests job with matrix strategy (Python 3.11, 3.12)
- ✅ Docker image configuration correct (catthehacker/ubuntu:act-latest)
- ✅ All workflow steps parsed and validated without errors
