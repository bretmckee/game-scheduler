<!-- markdownlint-disable-file -->

# Task Details: Autocopyright Official Repository Migration

## Research Reference

**Source Research**: #file:../research/20260204-autocopyright-precommit-direct-integration-research.md

## Phase 1: Update Pre-commit Configuration

### Task 1.1: Replace local autocopyright hooks with official repository

Replace the current local autocopyright hooks with official repository configuration using proper args format.

- **Files**:
  - .pre-commit-config.yaml (Lines 27-46) - Replace local hooks section with official repository
- **Success**:
  - Repository source changes from `repo: local` to `repo: https://github.com/Argmaster/autocopyright`
  - Version pinned with `rev: "v1.1.0"`
  - Two hooks defined with `id: autocopyright` and distinct names
  - Arguments converted from entry commands to args list format
  - `language: python` and `additional_dependencies` removed
  - `files:` patterns and `require_serial: true` preserved
- **Research References**:
  - #file:../research/20260204-autocopyright-precommit-direct-integration-research.md (Lines 51-131) - Official configuration format and comparison
- **Dependencies**:
  - None - this is the primary change

**Configuration Pattern:**
```yaml
  - repo: https://github.com/Argmaster/autocopyright
    rev: "v1.1.0"
    hooks:
      - id: autocopyright
        name: Add copyright headers (Python)
        args:
          - -s
          - "#"
          - -d
          - alembic
          - -d
          - services
          - -d
          - shared
          - -d
          - tests
          - -g
          - "*.py"
          - -l
          - ./templates/mit-template.jinja2
        files: \.py$
        require_serial: true

      - id: autocopyright
        name: Add copyright headers (TypeScript)
        args:
          - -s
          - "//"
          - -d
          - frontend/src
          - -g
          - "*.ts"
          - -g
          - "*.tsx"
          - -l
          - ./templates/mit-template.jinja2
        files: \.(ts|tsx)$
        require_serial: true
```

### Task 1.2: Verify hook configuration syntax and file patterns

Ensure the new configuration preserves all functional requirements from the previous local hooks.

- **Files**:
  - .pre-commit-config.yaml - Review updated configuration
- **Success**:
  - Python hook processes alembic, services, shared, tests directories
  - TypeScript hook processes frontend/src directory
  - Comment symbols correct: `#` for Python, `//` for TypeScript
  - Template path correct: `./templates/mit-template.jinja2`
  - File patterns match previous configuration
  - No syntax errors in YAML
- **Research References**:
  - #file:../research/20260204-autocopyright-precommit-direct-integration-research.md (Lines 60-85) - CLI options and argument format
- **Dependencies**:
  - Task 1.1 completion

## Phase 2: Remove Obsolete Files

### Task 2.1: Delete scripts/add-copyright wrapper script

Remove the obsolete bash wrapper script that is no longer needed with the official repository approach.

- **Files**:
  - scripts/add-copyright - Delete this file
- **Success**:
  - scripts/add-copyright file removed from repository
  - No references to scripts/add-copyright in configuration files
  - Git shows file as deleted in status
- **Research References**:
  - #file:../research/20260204-autocopyright-precommit-direct-integration-research.md (Lines 17-21) - Wrapper script context
  - #file:../research/20260204-autocopyright-precommit-direct-integration-research.md (Lines 153-160) - Implementation guidance including removal
- **Dependencies**:
  - Phase 1 completion to ensure hooks work without wrapper

## Phase 3: Testing and Validation

### Task 3.1: Test Python copyright hook execution

Verify the Python copyright hook works correctly with the official repository configuration.

- **Files**:
  - None - testing only
- **Success**:
  - Command `pre-commit run autocopyright --files services/api/main.py` succeeds
  - Command `pre-commit run autocopyright --all-files` processes all Python files
  - Copyright headers maintained on existing files
  - No errors about missing dependencies or commands
  - Hook execution completes in reasonable time
- **Research References**:
  - #file:../research/20260204-autocopyright-precommit-direct-integration-research.md (Lines 133-145) - Benefits including caching
- **Dependencies**:
  - Phase 1 completion

### Task 3.2: Test TypeScript copyright hook execution

Verify the TypeScript copyright hook works correctly with the official repository configuration.

- **Files**:
  - None - testing only
- **Success**:
  - Command `pre-commit run autocopyright --files frontend/src/App.tsx` succeeds
  - TypeScript copyright hook processes .ts and .tsx files
  - Copyright headers use `//` comment syntax
  - No interference with Python hook
  - Hook execution completes successfully
- **Research References**:
  - #file:../research/20260204-autocopyright-precommit-direct-integration-research.md (Lines 113-131) - TypeScript configuration example
- **Dependencies**:
  - Task 3.1 completion

### Task 3.3: Verify pre-commit autoupdate functionality

Ensure pre-commit can manage autocopyright version updates automatically.

- **Files**:
  - None - testing only
- **Success**:
  - Command `pre-commit autoupdate --repo https://github.com/Argmaster/autocopyright` recognizes the repository
  - Pre-commit can check for newer versions
  - Version tag format `v1.1.0` follows official release pattern
  - No errors about unsupported repository format
- **Research References**:
  - #file:../research/20260204-autocopyright-precommit-direct-integration-research.md (Lines 136-137) - Automatic updates benefit
- **Dependencies**:
  - Phase 1 completion

## Dependencies

- Pre-commit framework
- templates/mit-template.jinja2 template file
- pyproject.toml for template variables

## Success Criteria

- Official repository configured with pinned v1.1.0 version
- Both hooks execute without errors
- Copyright headers maintained correctly
- scripts/add-copyright removed
- Pre-commit autoupdate functional
- No local dependencies required
