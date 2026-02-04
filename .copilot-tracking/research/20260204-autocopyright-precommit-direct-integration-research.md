<!-- markdownlint-disable-file -->
# Task Research Notes: Autocopyright Pre-commit Direct Integration

## Research Executed

### Current Implementation Analysis
- [.pre-commit-config.yaml](.pre-commit-config.yaml) (Lines 27-46)
  - Two local hooks: `add-copyright-python` and `add-copyright-typescript`
  - Uses `language: python` with `additional_dependencies: ['autocopyright~=1.1.0']`
  - Direct entry commands with autocopyright CLI
  - `pass_filenames: false` for directory-based processing
  - Template path: `./templates/mit-template.jinja2`

- [scripts/add-copyright](scripts/add-copyright)
  - Bash wrapper (currently unused after 20260128 migration)
  - Two separate invocations for Python and TypeScript
  - Returns 0 to avoid pre-commit failure on rewrites

### External Research
- #githubRepo:"Argmaster/autocopyright" official pre-commit configuration
  - Repository provides native `.pre-commit-hooks.yaml`
  - Single `autocopyright` hook with configurable args
  - Uses direct repository reference: `repo: https://github.com/Argmaster/autocopyright`
  - Version tag format: `rev: "v1.1.0"`

- #fetch:https://github.com/Argmaster/autocopyright (README documentation)
  - **Recommended approach**: Use official repository instead of local hooks
  - Hook ID: `autocopyright` (single hook for all file types)
  - Arguments passed as list: `-s`, comment symbol, `-d`, directory, `-g`, glob pattern, `-l`, template path
  - Multiple directories supported with repeated `-d` flags
  - Multiple globs supported with repeated `-g` flags

## Key Discoveries

### Official Pre-commit Hook Configuration

From https://github.com/Argmaster/autocopyright README:

```yaml
repos:
  - repo: https://github.com/Argmaster/autocopyright
    rev: "v1.1.0"
    hooks:
      - id: autocopyright
        args:
          [
            -s,
            "#",
            -d,
            <your-project-source-dir-name>,
            -g,
            "*.py",
            -l,
            <path-to-license-template>,
          ]
```

**Key Features:**
- Single hook handles all file types
- Comment symbol configurable per invocation via `-s` flag
- Multiple directories via repeated `-d` flags
- Multiple globs via repeated `-g` flags
- Template path via `-l` flag
- Version pinned with `rev` tag

### Autocopyright CLI Options

From repository source and documentation:

```
-s, --comment-symbol: Symbol used to indicate comment
-d, --directory: Path to directory to search (multiple allowed)
-g, --glob: File glob used to search directories (multiple allowed)
-e, --exclude: Regex used to exclude files from updates (multiple allowed)
-l, --license: Path to license template
-p, --pool: Size of thread pool used for file IO (default: 4)
-v, --verbose: Increase verbosity level
```

**Return Code Behavior:**
- Returns 1 if files were modified (copyright added)
- Returns 0 if no changes needed
- Pre-commit treats non-zero as failure unless configured otherwise

### Template System

Autocopyright uses Jinja2 templates with special variables:
- `now` - datetime.datetime object (current time)
- `pyproject` - dictionary-like object from pyproject.toml

Our template at [templates/mit-template.jinja2](templates/mit-template.jinja2) already follows this format.

### Current vs. Recommended Approach

**Current Implementation (post-20260128):**
```yaml
  - repo: local
    hooks:
      - id: add-copyright-python
        name: Add copyright headers (Python)
        entry: autocopyright -s "#" -d alembic -d services -d shared -d tests -g "*.py" -l "./templates/mit-template.jinja2"
        language: python
        files: \.py$
        pass_filenames: false
        require_serial: true
        additional_dependencies: ['autocopyright~=1.1.0']

      - id: add-copyright-typescript
        name: Add copyright headers (TypeScript)
        entry: autocopyright -s "//" -d frontend/src -g "*.ts" -g "*.tsx" -l "./templates/mit-template.jinja2"
        language: python
        files: \.(ts|tsx)$
        pass_filenames: false
        require_serial: true
        additional_dependencies: ['autocopyright~=1.1.0']
```

**Recommended Official Repository Approach:**
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
```

## Recommended Approach

**Use the official Argmaster/autocopyright repository** with two separate hook invocations for Python and TypeScript.

### Benefits of Official Repository Approach

1. **Upstream Maintenance**: Automatic updates via `pre-commit autoupdate`
2. **Caching**: Pre-commit caches the repository, faster subsequent runs
3. **Consistency**: Same configuration pattern as other official hooks (ruff, prettier, etc.)
4. **No Local Dependencies**: Eliminates `additional_dependencies` management
5. **Official Support**: Uses the intended configuration method per documentation
6. **Simplified Configuration**: Standard pre-commit pattern, easier to understand

### Implementation Guidance

- **Objectives**: Replace local autocopyright hooks with official repository and remove obsolete wrapper script
- **Key Tasks**:
  1. Replace `repo: local` with `repo: https://github.com/Argmaster/autocopyright`
  2. Update `rev` to `"v1.1.0"` (pinned version)
  3. Change `id` from custom names to `autocopyright` (official hook ID)
  4. Convert `entry` commands to `args` lists
  5. Remove `language: python` and `additional_dependencies` (handled by repo)
  6. Keep `pass_filenames: false` behavior via `files` pattern
  7. Keep `require_serial: true` (autocopyright modifies files)
  8. **Remove `scripts/add-copyright` wrapper script** (no longer needed)
  9. Test with `pre-commit run autocopyright --all-files`

- **Dependencies**:
  - Template file at `templates/mit-template.jinja2` must exist
  - `pyproject.toml` for template variable substitution

- **Success Criteria**:
  - Both hooks execute successfully
  - Copyright headers added/maintained correctly
  - Pre-commit autoupdate works for version management
  - Hook runs without requiring `uv sync` or local installation
  - `scripts/add-copyright` removed from repository
