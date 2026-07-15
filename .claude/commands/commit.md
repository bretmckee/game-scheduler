---
description: 'Commit changes with pre-commit validation and code quality checks'
---

<!-- markdownlint-disable-file -->

# Commit Changes with Validation

Pre-commit hooks will automatically validate code quality when you commit. Your role is to review code against project standards before committing.

## Step 1: Review Changed Files Against Standards

1. Check modified files:

   ```bash
   git diff --name-only
   ```

2. Review files against language-specific guidelines:

   | File Type                        | Review Against                                                                                             |
   | -------------------------------- | ---------------------------------------------------------------------------------------------------------- |
   | `*.py`                           | `.github/instructions/python.instructions.md`                                                              |
   | `*.tsx`, `*.ts`, `*.jsx`, `*.js` | `.github/instructions/reactjs.instructions.md`, `.github/instructions/typescript-5-es2022.instructions.md` |
   | All files                        | `.github/instructions/coding-best-practices.instructions.md`                                               |

3. Confirm adherence to:
   - Naming conventions
   - Code structure and patterns
   - Best practices
   - Documentation standards

## Step 2: Pre-commit Hook Failures

Pre-commit hooks validate: compilation, linting, formatting, tests, complexity, and duplicate code.

**If hooks fail**: Fix issues OR follow `.github/instructions/quality-check-overrides.instructions.md` to request an override.

## Step 3: Commit Process

1. Stage changes (prefer naming specific files over a blanket add; review `git status` first if anything unexpected is staged):

   ```bash
   git add <specific files>
   ```

2. Review staged changes:

   ```bash
   git diff --cached
   ```

3. Commit with descriptive message:

   ```bash
   git commit -m "Brief summary (≤50 chars)

   Optional detailed explanation of what changed and why.
   Reference issues: #123"
   ```

**Commit Message Guidelines**:

- Use imperative mood: "Add feature" not "Added feature"
- First line ≤50 characters
- Blank line before detailed explanation
- Reference related issues or tickets

## Execution

1. Execute Step 1 first to review code standards
2. Execute Step 3 to commit (hooks run automatically)
3. If hooks fail, address failures per Step 2
4. Report results of each step
5. Stop if failures cannot be resolved
