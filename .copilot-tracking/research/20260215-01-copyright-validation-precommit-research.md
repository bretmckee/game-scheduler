<!-- markdownlint-disable-file -->

# Task Research Notes: Pre-commit Copyright Validation

## Problem Statement

AI coding agents frequently add copyright headers with errors (wrong years like "2025-2026", hallucinated names, wrong formats). Despite instructions to avoid manual copyrights, this creates unnecessary commit cycles:

1. First commit fails with wrong copyright
2. Agent removes copyright
3. Second commit succeeds, autocopyright adds correct header
4. Files must be re-added and committed again

## Solution: Generate Reference Files and Validate

Generate correct copyright reference files at start of each pre-commit run, then validate new files against them using simple substring matching.

**Why This Approach:**

- Simple and fast: Generate 3 reference files once per commit, then O(n) substring checks
- Always accurate: Uses autocopyright's own output as source of truth
- Always current: Regenerated every run, handles year changes automatically
- No complexity: No template parsing, date checking, or staleness detection
- Git ignored: Reference files are build artifacts, not tracked

## Current Project Setup

- `.pre-commit-config.yaml`: Has existing `autocopyright-python`, `autocopyright-typescript`, `autocopyright-shell` hooks
- `scripts/autocopyright-wrapper.sh`: Wrapper that calls autocopyright per-file
- `templates/mit-template.jinja2`: Template with `Copyright {{ now.year }} {{ pyproject.project.authors[0].name }}`
- `pyproject.toml`: Author = "Bret McKee", depends on `autocopyright~=1.1.0`
- `autocopyright` has no check/validation mode - only modifies files

## Recommended Approach

**Architecture:**

- Generate 3 reference files at pre-commit start: `.copyright.py`, `.copyright.ts`, `.copyright.sh`
- Validate new files with simple substring check: `if expected in content`
- Add reference files to `.gitignore` (build artifacts, not tracked)

**Pre-commit Flow:**

1. Regenerate all 3 reference files (always fresh)
2. For each new file (git diff --diff-filter=A), check if it has wrong copyright
3. Pass if no copyright OR correct copyright
4. Fail fast with clear message if wrong copyright

## Implementation Plan

### Scripts to Create

**1. scripts/check-copyright.py**

```python
#!/usr/bin/env python3
import sys

if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} <copyright_file> <source_file>")
    sys.exit(2)

copyright_file, source_file = sys.argv[1:]

with open(copyright_file) as f:
    expected = f.read()
with open(source_file) as f:
    content = f.read()

if "Copyright" not in content or expected in content:
    sys.exit(0)  # Pass: no copyright or correct copyright

print(f"ERROR: Wrong copyright in {source_file}")
print("Remove the manual copyright - autocopyright will add the correct one")
sys.exit(1)
```

**2. scripts/generate-copyright-references.sh**

```bash
#!/bin/bash
set -e

for ext in py ts sh; do
    ref_file=".copyright.$ext"
    case "$ext" in
        py|sh) symbol="#" ;;
        ts) symbol="//" ;;
    esac

    echo "" > "$ref_file"
    autocopyright -s "$symbol" -d "." -g ".copyright.$ext" -l "./templates/mit-template.jinja2"
done
```

**3. scripts/check-copyright-precommit.sh**

```bash
#!/bin/bash
set -e

SCRIPT_DIR=$(dirname "$0")

get_reference_file() {
    case "$1" in
        *.py) echo ".copyright.py" ;;
        *.ts|*.tsx) echo ".copyright.ts" ;;
        *.sh) echo ".copyright.sh" ;;
    esac
}

# Always regenerate
"$SCRIPT_DIR/generate-copyright-references.sh"

# Check new files only
new_files=$(git diff --cached --name-only --diff-filter=A)
[ -z "$new_files" ] && exit 0

exit_code=0
for file in $new_files; do
    case "$file" in
        *.py|*.ts|*.tsx|*.sh)
            ref_file=$(get_reference_file "$file")
            [ -n "$ref_file" ] && python3 "$SCRIPT_DIR/check-copyright.py" "$ref_file" "$file" || exit_code=1
            ;;
    esac
done
exit $exit_code
```

### Configuration Changes

**Add to .gitignore:**

```
.copyright.py
.copyright.ts
.copyright.sh
```

**Add to .pre-commit-config.yaml** (before existing autocopyright hooks):

```yaml
- repo: local
  hooks:
    - id: check-copyright-headers
      name: Check for manual copyright headers
      entry: scripts/check-copyright-precommit.sh
      language: script
      files: \.(py|ts|tsx|sh)$
      pass_filenames: false
      require_serial: true
```

## Testing Plan

1. Add file with "Copyright 2025-2026" → should fail
2. Add file with hallucinated author → should fail
3. Add file without copyright → should pass
4. Add file with correct "Copyright 2026 Bret McKee" → should pass
5. Test all file types: .py, .ts, .sh

## Success Criteria

- Pre-commit fails fast on wrong copyright with clear error
- No false positives/negatives
- Fast (< 100ms overhead for typical commits)
- Always current (year changes handled automatically)
