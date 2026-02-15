---
applyTo: '.copilot-tracking/changes/20260215-01-copyright-validation-precommit-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Pre-commit Copyright Validation

## Overview

Implement pre-commit hook to validate copyright headers by generating reference files and checking new files against them to prevent AI agents from adding incorrect copyright headers.

## Objectives

- Generate correct copyright reference files at start of each pre-commit run
- Validate new files against reference files using substring matching
- Fail fast with clear error messages when wrong copyrights are detected
- Prevent commit cycles caused by incorrect AI-generated copyright headers

## Research Summary

### Project Files

- [.pre-commit-config.yaml](.pre-commit-config.yaml) - Existing autocopyright hooks configuration
- [scripts/autocopyright-wrapper.sh](scripts/autocopyright-wrapper.sh) - Current autocopyright wrapper
- [templates/mit-template.jinja2](templates/mit-template.jinja2) - Copyright template
- [pyproject.toml](pyproject.toml) - Project configuration with author info

### External References

- #file:../research/20260215-01-copyright-validation-precommit-research.md - Complete research findings

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/test-driven-development.instructions.md - TDD methodology for Python code
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Commenting standards

## Implementation Checklist

### [ ] Phase 1: Setup and Configuration

- [ ] Task 1.1: Update .gitignore to exclude copyright reference files
  - Details: [.copilot-tracking/details/20260215-01-copyright-validation-precommit-details.md](.copilot-tracking/details/20260215-01-copyright-validation-precommit-details.md) (Lines 12-24)

### [ ] Phase 2: Generate Copyright References Script

- [ ] Task 2.1: Create generate-copyright-references.sh script
  - Details: [.copilot-tracking/details/20260215-01-copyright-validation-precommit-details.md](.copilot-tracking/details/20260215-01-copyright-validation-precommit-details.md) (Lines 26-46)

- [ ] Task 2.2: Make script executable and test generation
  - Details: [.copilot-tracking/details/20260215-01-copyright-validation-precommit-details.md](.copilot-tracking/details/20260215-01-copyright-validation-precommit-details.md) (Lines 48-61)

### [ ] Phase 3: Copyright Check Python Script (TDD)

- [ ] Task 3.1: Create check-copyright.py stub with NotImplementedError
  - Details: [.copilot-tracking/details/20260215-01-copyright-validation-precommit-details.md](.copilot-tracking/details/20260215-01-copyright-validation-precommit-details.md) (Lines 63-77)

- [ ] Task 3.2: Write failing unit tests defining expected behavior
  - Details: [.copilot-tracking/details/20260215-01-copyright-validation-precommit-details.md](.copilot-tracking/details/20260215-01-copyright-validation-precommit-details.md) (Lines 79-95)

- [ ] Task 3.3: Implement check-copyright.py to make tests pass
  - Details: [.copilot-tracking/details/20260215-01-copyright-validation-precommit-details.md](.copilot-tracking/details/20260215-01-copyright-validation-precommit-details.md) (Lines 97-110)

- [ ] Task 3.4: Refactor and add comprehensive edge case tests
  - Details: [.copilot-tracking/details/20260215-01-copyright-validation-precommit-details.md](.copilot-tracking/details/20260215-01-copyright-validation-precommit-details.md) (Lines 112-128)

### [ ] Phase 4: Pre-commit Integration Script

- [ ] Task 4.1: Create check-copyright-precommit.sh script
  - Details: [.copilot-tracking/details/20260215-01-copyright-validation-precommit-details.md](.copilot-tracking/details/20260215-01-copyright-validation-precommit-details.md) (Lines 145-166)

- [ ] Task 4.2: Make script executable and add to pre-commit config
  - Details: [.copilot-tracking/details/20260215-01-copyright-validation-precommit-details.md](.copilot-tracking/details/20260215-01-copyright-validation-precommit-details.md) (Lines 168-186)

### [ ] Phase 5: Integration Testing

- [ ] Task 5.1: Test with files containing wrong copyright headers
  - Details: [.copilot-tracking/details/20260215-01-copyright-validation-precommit-details.md](.copilot-tracking/details/20260215-01-copyright-validation-precommit-details.md) (Lines 188-201)

- [ ] Task 5.2: Test with files containing correct or no copyright headers
  - Details: [.copilot-tracking/details/20260215-01-copyright-validation-precommit-details.md](.copilot-tracking/details/20260215-01-copyright-validation-precommit-details.md) (Lines 203-216)

- [ ] Task 5.3: Verify all file types (.py, .ts, .sh) work correctly
  - Details: [.copilot-tracking/details/20260215-01-copyright-validation-precommit-details.md](.copilot-tracking/details/20260215-01-copyright-validation-precommit-details.md) (Lines 218-230)

## Dependencies

- Python 3.x
- `autocopyright~=1.1.0` (already in pyproject.toml)
- `pre-commit` framework
- Git (for diff operations)
- Bash shell

## Success Criteria

- Pre-commit hook fails fast when wrong copyright headers are detected
- Clear error messages guide users to remove manual copyrights
- No false positives (files with correct or no copyright pass)
- All file types (.py, .ts, .tsx, .sh) validated correctly
- Reference files regenerated fresh on each pre-commit run
- Fast execution (< 100ms overhead for typical commits)
