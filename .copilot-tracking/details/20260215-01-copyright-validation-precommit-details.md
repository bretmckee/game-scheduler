<!-- markdownlint-disable-file -->

# Task Details: Pre-commit Copyright Validation

## Research Reference

**Source Research**: #file:../research/20260215-01-copyright-validation-precommit-research.md

## Phase 1: Setup and Configuration

### Task 1.1: Update .gitignore to exclude copyright reference files

Add copyright reference files to .gitignore since they are build artifacts that should not be tracked in version control.

- **Files**:
  - [.gitignore](.gitignore) - Add three lines for reference files
- **Success**:
  - `.copyright.py`, `.copyright.ts`, and `.copyright.sh` listed in .gitignore
  - Reference files ignored by git status
- **Research References**:
  - #file:../research/20260215-01-copyright-validation-precommit-research.md (Lines 98-103) - Configuration changes section
- **Dependencies**:
  - None

## Phase 2: Generate Copyright References Script

### Task 2.1: Create generate-copyright-references.sh script

Create shell script that generates three reference copyright files (.py, .ts, .sh) using autocopyright. This script will be called at the start of each pre-commit run to ensure reference files are always current.

- **Files**:
  - [scripts/generate-copyright-references.sh](scripts/generate-copyright-references.sh) - New script to generate reference files
- **Success**:
  - Script creates `.copyright.py`, `.copyright.ts`, `.copyright.sh` in project root
  - Uses correct comment symbols for each file type (# for py/sh, // for ts)
  - Calls autocopyright with proper arguments
- **Research References**:
  - #file:../research/20260215-01-copyright-validation-precommit-research.md (Lines 51-68) - Script implementation
- **Dependencies**:
  - Task 1.1 completion (gitignore updated)

### Task 2.2: Make script executable and test generation

Set executable permissions and verify the script generates valid reference files with correct copyright headers.

- **Files**:
  - [scripts/generate-copyright-references.sh](scripts/generate-copyright-references.sh) - Set executable bit
- **Success**:
  - Script has executable permissions (chmod +x)
  - Running script successfully creates all three reference files
  - Reference files contain "Copyright 2026 Bret McKee"
- **Research References**:
  - #file:../research/20260215-01-copyright-validation-precommit-research.md (Lines 18-28) - Current project setup
- **Dependencies**:
  - Task 2.1 completion

## Phase 3: Copyright Check Python Script (TDD)

### Task 3.1: Create check-copyright.py stub with NotImplementedError

Create initial Python script structure with argument parsing and NotImplementedError to enable test-first development.

- **Files**:
  - [scripts/check-copyright.py](scripts/check-copyright.py) - New stub script
- **Success**:
  - Script accepts two command-line arguments (copyright_file, source_file)
  - Raises NotImplementedError when called
  - Has shebang line and proper error handling for wrong argument count
- **Research References**:
  - #file:../research/20260215-01-copyright-validation-precommit-research.md (Lines 37-49) - Script specification
- **Dependencies**:
  - None (can proceed in parallel with Phase 2)

### Task 3.2: Write failing unit tests defining expected behavior

Create comprehensive unit tests that define the expected behavior of the copyright checker. Tests will initially fail because the stub raises NotImplementedError, but are written to verify the actual validation logic (exit codes, error messages, file handling).

- **Files**:
  - [tests/unit/test_check_copyright.py](tests/unit/test_check_copyright.py) - New test file
- **Success**:
  - Tests define expected behavior: exit code 0 for valid cases (no copyright, correct copyright)
  - Tests define expected behavior: exit code 1 for invalid cases (wrong copyright)
  - Tests verify error message content for failures
  - All tests fail because stub raises NotImplementedError
- **Research References**:
  - #file:../research/20260215-01-copyright-validation-precommit-research.md (Lines 116-122) - Testing plan and scenarios
- **Dependencies**:
  - Task 3.1 completion

### Task 3.3: Implement check-copyright.py to make tests pass

Implement the actual copyright validation logic using simple substring matching. Read both files and check if expected copyright is present when any copyright exists. This implementation should make all the tests from Task 3.2 pass.

- **Files**:
  - [scripts/check-copyright.py](scripts/check-copyright.py) - Replace NotImplementedError with implementation
- **Success**:
  - Reads copyright reference file and source file
  - Passes if "Copyright" not in source OR expected copyright substring found
  - Fails with exit code 1 and clear message if wrong copyright detected
  - All tests from Task 3.2 now pass without modification
- **Research References**:
  - #file:../research/20260215-01-copyright-validation-precommit-research.md (Lines 37-49) - Implementation specification
- **Dependencies**:
  - Task 3.2 completion

### Task 3.4: Refactor and add comprehensive edge case tests

Refactor code for clarity and add edge case tests (empty files, permission errors, encoding issues) while keeping all tests green.

- **Files**:
  - [scripts/check-copyright.py](scripts/check-copyright.py) - Refactor for readability
  - [tests/unit/test_check_copyright.py](tests/unit/test_check_copyright.py) - Add edge case tests
- **Success**:
  - Code follows Python best practices and project conventions
  - Edge cases covered: empty files, file not found, partial copyright matches
  - All tests pass including new edge case tests
  - Code has appropriate error handling
- **Research References**:
  - #file:../../.github/instructions/python.instructions.md - Python coding standards
- **Dependencies**:
  - Task 3.3 completion

## Phase 4: Pre-commit Integration Script

### Task 4.1: Create check-copyright-precommit.sh script

Create shell script that orchestrates the copyright check: generates references, finds new files via git diff, and validates each applicable file.

- **Files**:
  - [scripts/check-copyright-precommit.sh](scripts/check-copyright-precommit.sh) - New integration script
- **Success**:
  - Calls generate-copyright-references.sh at start
  - Uses `git diff --cached --name-only --diff-filter=A` to find new files
  - Maps file extensions to reference files (.py→.copyright.py, etc.)
  - Calls check-copyright.py for each applicable file
  - Returns non-zero exit code if any check fails
- **Research References**:
  - #file:../research/20260215-01-copyright-validation-precommit-research.md (Lines 70-96) - Script implementation
- **Dependencies**:
  - Phase 2 completion (generate script exists)
  - Phase 3 completion (check script exists)

### Task 4.2: Make script executable and add to pre-commit config

Set executable permissions and add new hook to .pre-commit-config.yaml before existing autocopyright hooks.

- **Files**:
  - [scripts/check-copyright-precommit.sh](scripts/check-copyright-precommit.sh) - Set executable bit
  - [.pre-commit-config.yaml](.pre-commit-config.yaml) - Add new local hook
- **Success**:
  - Script has executable permissions
  - New hook added under `repo: local` section
  - Hook configuration includes: name, entry, language: script, files pattern, pass_filenames: false, require_serial: true
  - Hook runs before autocopyright hooks (placement matters)
- **Research References**:
  - #file:../research/20260215-01-copyright-validation-precommit-research.md (Lines 105-114) - Pre-commit configuration
- **Dependencies**:
  - Task 4.1 completion

## Phase 5: Integration Testing

### Task 5.1: Test with files containing wrong copyright headers

Create test files with incorrect copyright headers and verify pre-commit hook catches them.

- **Files**:
  - Temporary test files in git staging area
- **Success**:
  - Pre-commit fails when adding file with "Copyright 2025-2026"
  - Pre-commit fails when adding file with hallucinated author name
  - Error message clearly states the problem and solution
  - Hook exits with non-zero status
- **Research References**:
  - #file:../research/20260215-01-copyright-validation-precommit-research.md (Lines 116-122) - Testing plan scenarios 1-2
- **Dependencies**:
  - Phase 4 completion (hook installed)

### Task 5.2: Test with files containing correct or no copyright headers

Verify pre-commit hook allows files with correct copyright or no copyright to pass.

- **Files**:
  - Temporary test files in git staging area
- **Success**:
  - Pre-commit passes when adding file without copyright header
  - Pre-commit passes when adding file with "Copyright 2026 Bret McKee"
  - No false positives reported
  - Hook exits with zero status
- **Research References**:
  - #file:../research/20260215-01-copyright-validation-precommit-research.md (Lines 116-122) - Testing plan scenarios 3-4
- **Dependencies**:
  - Phase 4 completion (hook installed)

### Task 5.3: Verify all file types (.py, .ts, .sh) work correctly

Test copyright validation across all supported file types to ensure consistent behavior.

- **Files**:
  - Temporary test files of each type in git staging area
- **Success**:
  - .py files validated against .copyright.py reference
  - .ts and .tsx files validated against .copyright.ts reference
  - .sh files validated against .copyright.sh reference
  - All file types show correct pass/fail behavior
- **Research References**:
  - #file:../research/20260215-01-copyright-validation-precommit-research.md (Lines 116-122) - Testing plan scenario 5
- **Dependencies**:
  - Phase 4 completion (hook installed)

## Dependencies

- Python 3.x with standard library
- autocopyright package (already installed)
- pre-commit framework
- Git
- Bash shell

## Success Criteria

- All unit tests pass for check-copyright.py
- Pre-commit hook fails fast on wrong copyright headers
- Pre-commit hook passes files with correct or no copyright
- All file types (.py, .ts, .tsx, .sh) validated correctly
- Clear error messages guide users to fix issues
- No performance degradation (< 100ms overhead)
- Reference files excluded from git tracking
