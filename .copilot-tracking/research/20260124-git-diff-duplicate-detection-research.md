<!-- markdownlint-disable-file -->
# Task Research Notes: Git Diff-Based Duplicate Code Detection

## Research Executed

### Current Project Analysis
- `.pre-commit-config.yaml`
  - jscpd hook currently scans entire codebase (`services shared frontend/src`)
  - Runs with `pass_filenames: false` (doesn't use staged files list)
  - No git diff integration
- `.jscpd.json`
  - Configured with 5% threshold
  - Ignores test files, alembic versions, __init__.py

### Tool Capability Analysis
- #githubRepo:"kucherenko/jscpd git diff changed files branch comparison"
  - No native git diff mode in jscpd
  - Tool always scans specified directories completely
  - No `--from-ref` or `--to-ref` options available
  - No incremental or diff-based scanning capability

### Pre-commit Framework Research
- #fetch:"https://pre-commit.com/#passing-arguments-to-hooks"
  - Pre-commit provides `--from-ref` and `--to-ref` options for `pre-commit run`
  - Runs hooks against files changed between git refs
  - Example: `pre-commit run --from-ref HEAD^^^ --to-ref HEAD`
  - Can be used in CI/CD to check only changed files
  - Pre-commit automatically filters staged files for hooks

### Alternative Solutions Research
- GitHub Code Search: duplicate detection tools with git diff support
  - **PMD CPD (Copy/Paste Detector)**: Java-based, no git diff mode
  - **SonarQube**: Full platform, has incremental analysis in commercial version
  - **Simian**: Commercial tool, no git diff mode
  - **duplo**: C/C++ focused, no git diff support
  - **Codacy**: SaaS platform, analyzes PRs incrementally

## Key Discoveries

### Git Diff Integration Options

**Option 1: Pre-commit Framework with File Filtering**
```yaml
- repo: local
  hooks:
    - id: jscpd-diff
      name: Check duplicates in changed files only
      entry: bash -c 'changed_files=$(git diff --cached --name-only --diff-filter=ACM | grep -E "\.(py|ts|tsx|js)$" | tr "\n" " "); if [ -n "$changed_files" ]; then npx jscpd $changed_files --config .jscpd.json; else echo "No relevant files changed"; fi'
      language: system
      pass_filenames: false
      always_run: true
```

**Pros:**
- Works with existing jscpd installation
- Only scans files being committed
- Fast for small changesets
- No new tools required

**Cons:**
- jscpd needs full file paths, not patterns
- May miss duplicates when changed code duplicates existing code
- Requires bash scripting in pre-commit config
- Won't detect if you're adding duplicate of existing code

**Option 2: CI/CD Branch Comparison with Pre-commit**
```yaml
# .github/workflows/ci-cd.yml
- name: Check duplicates in PR
  run: |
    # Get list of changed files between PR base and HEAD
    git fetch origin ${{ github.base_ref }}
    changed_files=$(git diff --name-only origin/${{ github.base_ref }}...HEAD | grep -E "\.(py|ts|tsx|js)$")

    if [ -n "$changed_files" ]; then
      npx jscpd $changed_files --config .jscpd.json
    fi
```

**Pros:**
- Catches duplicates in PR context
- Can compare against main/develop branch
- Integrated into CI pipeline
- Doesn't slow down local commits

**Cons:**
- Only runs in CI, not locally
- Developer doesn't know about issue until PR
- May miss cross-file duplications
- Still uses full file scanning

**Option 3: Two-Phase jscpd Strategy**
```yaml
# Phase 1: Fast check on staged files (pre-commit)
- repo: local
  hooks:
    - id: jscpd-changed
      name: Quick duplicate check on changed files
      entry: bash -c 'changed=$(git diff --cached --name-only --diff-filter=ACM | grep -E "\.(py|ts|tsx|js)$" | tr "\n" " "); [ -n "$changed" ] && npx jscpd $changed --config .jscpd.json --threshold 3 || true'
      language: system
      pass_filenames: false
      stages: [pre-commit]

# Phase 2: Full scan (manual or CI)
- repo: local
  hooks:
    - id: jscpd-full
      name: Full codebase duplicate check
      entry: npx jscpd services shared frontend/src --config .jscpd.json
      language: system
      pass_filenames: false
      stages: [manual]
```

**Pros:**
- Fast pre-commit check
- Comprehensive manual/CI check available
- Developer choice when to run full scan
- Catches most issues early

**Cons:**
- Two separate checks to maintain
- May miss duplicates between new and existing code
- Requires developer discipline for full scan

**Option 4: SonarQube/SonarCloud Integration**
```yaml
# .github/workflows/sonarcloud.yml
- name: SonarCloud Scan
  uses: SonarSource/sonarcloud-github-action@master
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

**Pros:**
- Professional-grade duplicate detection
- Automatic PR integration
- Tracks duplicates over time
- Incremental analysis (only changed code)
- Many other code quality checks included

**Cons:**
- Requires SonarCloud account (free for open source)
- Additional service dependency
- More complex setup
- Data sent to external service

### Limitations of Pure Git Diff Approach

**Critical Issue**: jscpd and similar tools work by:
1. Tokenizing entire files
2. Creating fingerprints of code blocks
3. Comparing fingerprints across all files

**Problem**: If you only scan changed files, you miss:
- New code that duplicates existing code in unchanged files
- Existing code in unchanged files that duplicates your new code

**Example Scenario**:
```python
# File A (existing, unchanged):
def calculate_price(base, tax):
    total = base * (1 + tax)
    return round(total, 2)

# File B (new commit):
def compute_cost(amount, rate):
    result = amount * (1 + rate)
    return round(result, 2)
```

If you only scan File B, you won't detect it duplicates File A.

### Recommended Hybrid Approach

**Strategy**: Multi-tier duplicate detection
1. **Pre-commit (Fast)**: Check staged files against each other
2. **CI Pull Request (Comprehensive)**: Check all changed files against entire codebase
3. **Weekly (Audit)**: Full codebase scan

## Recommended Approach

**Immediate Solution: Comprehensive Pre-commit Check (10-20 seconds)**

This approach runs jscpd on the entire codebase during pre-commit, but only fails if duplicates involve your changed files. This gives you the best of both worlds: comprehensive duplicate detection with immediate feedback.

### Phase 1: Create Duplicate Analysis Script

First, create the script that will analyze jscpd results and filter for your changes:

```python
# scripts/check_commit_duplicates.py
"""
Check if commit introduces duplicates or duplicates existing code.
Only fails if duplicates overlap with actual changed lines (not just changed files).
Designed for pre-commit hook use.
"""
import json
import sys
import subprocess
import re
from pathlib import Path
from typing import Dict, Set, Tuple

def get_changed_line_ranges() -> Dict[str, Set[int]]:
    """
    Get the specific line numbers changed in each staged file.
    Returns: Dict mapping file paths to sets of changed line numbers.
    """
    result = subprocess.run(
        ['git', 'diff', '--cached', '--unified=0'],  # unified=0 shows only changed lines
        capture_output=True,
        text=True,
        check=True
    )

    changed_lines = {}
    current_file = None

    for line in result.stdout.split('\n'):
        # New file diff section
        if line.startswith('+++ b/'):
            current_file = line[6:]  # Remove '+++ b/' prefix
            if current_file and (
                current_file.endswith('.py') or
                current_file.endswith(('.ts', '.tsx', '.js', '.jsx'))
            ) and not any(x in current_file for x in ['tests/', '__pycache__', 'node_modules/', '.min.js']):
                changed_lines[current_file] = set()
            else:
                current_file = None

        # Line range info (e.g., "@@ -10,5 +12,7 @@")
        elif line.startswith('@@') and current_file:
            # Extract new file line range
            match = re.search(r'\+(\d+)(?:,(\d+))?', line)
            if match:
                start_line = int(match.group(1))
                count = int(match.group(2)) if match.group(2) else 1

                # Add all lines in the changed range
                for line_num in range(start_line, start_line + count):
                    changed_lines[current_file].add(line_num)

    # Filter out files with no changed lines tracked
    return {f: lines for f, lines in changed_lines.items() if lines}

def ranges_overlap(changed_lines: Set[int], dup_start: int, dup_end: int) -> bool:
    """Check if duplicate's line range overlaps with changed lines."""
    dup_range = set(range(dup_start, dup_end + 1))
    return bool(changed_lines & dup_range)

def main(report_file: str):
    changed_line_ranges = get_changed_line_ranges()

    if not changed_line_ranges:
        print("✅ No source files changed")
        return 0

    total_changed_lines = sum(len(lines) for lines in changed_line_ranges.values())
    print(f"Checking {len(changed_line_ranges)} files ({total_changed_lines} changed lines) against codebase...")

    if not Path(report_file).exists():
        print(f"⚠️  Report file not found: {report_file}")
        return 0

    with open(report_file) as f:
        report = json.load(f)

    duplicates = report.get('duplicates', [])
    commit_related_duplicates = []

    for dup in duplicates:
        first_file = dup['firstFile']['name']
        second_file = dup['secondFile']['name']
        first_start = dup['firstFile']['start']
        first_end = dup['firstFile']['end']
        second_start = dup['secondFile']['start']
        second_end = dup['secondFile']['end']

        # Check if duplicate overlaps with changed lines in either file
        first_overlaps = (
            first_file in changed_line_ranges and
            ranges_overlap(changed_line_ranges[first_file], first_start, first_end)
        )
        second_overlaps = (
            second_file in changed_line_ranges and
            ranges_overlap(changed_line_ranges[second_file], second_start, second_end)
        )

        if first_overlaps or second_overlaps:
            commit_related_duplicates.append({
                'file1': first_file,
                'lines1': f"{first_start}-{first_end}",
                'file2': second_file,
                'lines2': f"{second_start}-{second_end}",
                'line_count': dup['lines'],
                'tokens': dup['tokens'],
                'fragment': dup.get('fragment', '')[:100],
                'overlaps_file1': first_overlaps,
                'overlaps_file2': second_overlaps,
            })

    if commit_related_duplicates:
        print(f"\n❌ Found {len(commit_related_duplicates)} duplicates overlapping with your changes:\n")
        for i, dup in enumerate(commit_related_duplicates, 1):
            print(f"{i}. {dup['file1']}:{dup['lines1']} ↔ {dup['file2']}:{dup['lines2']}")
            print(f"   {dup['line_count']} lines, {dup['tokens']} tokens")
            if dup['overlaps_file1'] and dup['overlaps_file2']:
                print(f"   ⚠️  Both files have changes in duplicate region")
            elif dup['overlaps_file1']:
                print(f"   ⚠️  Your changes in {dup['file1']} duplicate existing code")
            else:
                print(f"   ⚠️  Your changes in {dup['file2']} duplicate existing code")
            if dup['fragment']:
                print(f"   Preview: {dup['fragment']}...")
            print()
        print("💡 Tip: Extract duplicated code into shared functions/modules")
        print("💡 Or if this is a false positive, bypass with: SKIP=jscpd-comprehensive git commit")
        return 1
    else:
        print(f"✅ No duplicates found in your changed lines")
        return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
```

### Phase 2: Update Pre-commit Configuration

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    # Comprehensive duplicate check (runs jscpd on entire codebase, filters for changed files)
    - id: jscpd-comprehensive
      name: Check for duplicates involving changed files
      entry: bash -c 'npx --yes jscpd services shared frontend/src --config .jscpd.json --format json --output .jscpd-report && uv run python scripts/check_commit_duplicates.py .jscpd-report/jscpd-report.json'
      language: system
      pass_filenames: false
      types_or: [python, ts, tsx, javascript]
      stages: [pre-commit]
      verbose: true

    # Full codebase check with console output (manual, for investigation)
    - id: jscpd-full
      name: Full duplicate code check
      entry: npx --yes jscpd services shared frontend/src --config .jscpd.json
      language: system
      pass_filenames: false
      types_or: [python, ts, tsx, javascript]
      stages: [manual]
```

### Phase 3: Update jscpd Configuration

```json
// .jscpd.json
{
  "threshold": 3,
  "reporters": ["console", "json"],
  "ignore": [
    "**/__pycache__/**",
    "**/node_modules/**",
    "**/coverage/**",
    "**/dist/**",
    "**/build/**",
    "**/.venv/**",
    "**/venv/**",
    "**/*.min.js",
    "**/tests/**",
    "**/alembic/versions/**",
    "**/__init__.py"
  ],
  "format": ["python", "typescript", "javascript"],
  "minLines": 6,
  "minTokens": 50,
  "mode": "mild",
  "output": "./jscpd-report",
  "exitCode": 1
}
```

## Implementation Guidance

### Objectives
- Prevent new duplicate code from being committed
- Catch duplicates between new and existing code
- Maintain fast pre-commit performance
- Provide comprehensive CI validation

### Key Tasks

1. **Update `.pre-commit-config.yaml`**:
   - Add `jscpd-staged` hook for quick pre-commit check
   - Add `jscpd-full` manual hook for comprehensive check
   - Configure with appropriate thresholds

2. **Add CI/CD duplicate detection**:
   - Create new job in `.github/workflows/ci-cd.yml`
   - Configure to run on pull requests only
   - Get changed files vs base branch
   - Run jscpd on entire codebase
   - Filter results for PR-related duplicates

3. **Create analysis script**:
   - Add `scripts/check_pr_duplicates.py`
   - Parse jscpd JSON report
   - Filter duplicates involving changed files
   - Exit with error if duplicates found

4. **Update jscpd config**:
   - Add `json` reporter
   - Set `exitCode: 1` for CI failure
   - Lower threshold to 3% (after cleanup)

### Success Criteria
- Pre-commit runs in < 5 seconds for typical commits
- CI catches duplicates between new and existing code
- Developers can run full scan manually when needed
- Clear error messages guide developers to fix duplicates

### Trade-offs

**Fast Pre-commit Check**:
- ✅ Quick feedback
- ❌ May miss cross-file duplicates

**Comprehensive CI Check**:
- ✅ Catches all duplicates involving changed code
- ❌ Delayed feedback (in CI)

**Manual Full Scan**:
- ✅ Complete duplicate detection
- ❌ Requires developer discipline

### Performance Expectations

- **Pre-commit staged files check**: 2-5 seconds
- **CI full codebase with filtering**: 10-20 seconds
- **Manual full scan**: 15-30 seconds

### Alternative: SonarCloud

For enterprise-grade solution, consider:
```yaml
# sonar-project.properties
sonar.organization=your-org
sonar.projectKey=game-scheduler
sonar.sources=services,shared,frontend/src
sonar.cpd.python.minimumTokens=50
sonar.cpd.ts.minimumLines=6
```

**Pros**: Incremental analysis, PR decoration, trend tracking
**Cons**: External service, requires account, data privacy considerations
comprehensive check**: 10-20 seconds (runs on entire codebase, filters for changed files)
- **Manual full scan with console output**: 15-30 seconds (for investigating specific duplicates)

### Usage Examples

**Normal commit (automatic)**:
```bash
git commit -m "Add new feature"
# Runs jscpd on entire codebase, checks if your changes introduce/duplicate code
# Takes 10-20 seconds
```

**Skip check in emergency** (use sparingly):
```bash
SKIP=jscpd-comprehensive git commit -m "Hotfix"
```

**Manual investigation**:
```bash
pre-commit run jscpd-full --hook-stage manual --all-files
# Shows all duplicates with detailed console output
```

### Optional: Add CI/CD Backup Check

If you want redundancy, you can also add a CI check that runs the same validation:

```yaml
# .github/workflows/ci-cd.yml (add to existing jobs)
  duplicate-detection:
    name: Duplicate Code Detection
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - uses: astral-sh/setup-uv@v3

      - name: Check for duplicates in PR
        run: |
     Create analysis script**:
   - Add `scripts/check_commit_duplicates.py`
   - Parse jscpd JSON report
   - Get staged files using git
   - Filter duplicates involving staged files
   - Exit with error if duplicates found
   - Provide helpful error messages

2. **Update `.pre-commit-config.yaml`**:
   - Replace existing jscpd hook with `jscpd-comprehensive`
   - Configure to run jscpd with JSON output
   - Chain with analysis script
   - Add `jscpd-full` manual hook for detailed investigation

3. **Update jscpd config**:
   - Add `json` reporter (keep `console` for manual runs)
   - Configure output directory: `.jscpd-report`
   - Maintain threshold at current level
   - Add `.jscpd-report/` to `.gitignore`

4. **Optional: Add CI backup check**:
   - Same check as pre-commit for redundancy
   - Catches cases where pre-commit was bypassed10-20 seconds (acceptable for comprehensive check)
- Catches duplicates between new code and existing codebase
- Only fails on duplicates involving changed files (not unrelated duplicates)
- Developers can run detailed scan manually when investigating
- Clear error messages with file paths and line counts
- Provides actionable feedback ("Extract duplicated code into shared functions")

### Trade-offs

**Comprehensive Pre-commit Check**:
- ✅ Immediate feedback before commit
- ✅ Catches all duplicates involving your changes
- ✅ No waiting for CI
- ⚠️ Takes 10-20 seconds (acceptable for quality gate)
- ⚠️ Requires entire codebase to be present

**Why Line-Level Filtering is Critical**:
- ❌ File-level filtering: "File X changed and has duplicates" → fails even for unrelated changes
- ✅ Line-level filtering: "Lines 45-60 you changed duplicate line 120-135 in file Y" → only fails for actual new duplicates
- ✅ Allows commits with unrelated changes to files that have pre-existing duplicates elsewhere
- ✅ Catches the critical case: your new/modified lines duplicating existing code

**Example Scenario**:
- File has pre-existing duplicate at lines 10-30
- You change line 100 (completely unrelated)
- File-level check: ❌ Fails (file has duplicates)
- Line-level check: ✅ Passes (your change didn't add/touch duplicates)
