---
name: sync-claude-config
description: Reconcile Copilot-native AI config (.github/copilot-instructions.md, .github/agents, .github/instructions, .github/prompts, .copilot-tracking/planning/prompts) against their Claude-native equivalents under .claude/. Invoke whenever scripts/check_ai_config_sync.py check reports a new or changed source file, or whenever the user asks to sync/convert Copilot config for Claude.
---

# Sync Claude Config

This skill keeps Claude-native config (`.claude/agents/*.md`, `.claude/commands/*.md`) from
silently drifting out of sync with the hand-maintained Copilot-native files that `scripts/check_ai_config_sync.py`
watches. The script does the mechanical hashing and bookkeeping; this skill does the judgment
call of what, if anything, a changed source file needs on the Claude side.

## Step 1: See what's outstanding

Run:

```
uv run python scripts/check_ai_config_sync.py check
```

This autofixes clean removals on its own (deletes an orphaned output whose hash still matches
what was last generated, and drops the manifest entry) and prints one line per file that needs a
decision: `NEW: <path> has no conversion recorded.` `CHANGED: <path> changed since last sync.` or
`CONFLICT: <path> was removed, but its output has been hand-edited since generation.`

## Step 2: For each NEW or CHANGED source, decide what it needs

Read the file. It falls into one of two buckets:

- **Plain convention content** — style/workflow guidance with no Copilot-specific syntax baked
  into what it asks the reader to _produce_ (most of `.github/instructions/*.instructions.md`).
  `CLAUDE.md` already points directly at these files and Claude reads them fine as-is — frontmatter
  like `applyTo:` is harmless metadata Claude correctly ignores. These need no `.claude/` output.
  Record them as reference-only:

  ```
  uv run python scripts/check_ai_config_sync.py record <source>
  ```

- **Persona/workflow content with a Copilot-specific output contract** — `.github/agents/*.agent.md`,
  `.github/prompts/*.prompt.md`, and `.copilot-tracking/planning/prompts/*.md` (the generated
  implementation-prompt files, which live for a whole plan's lifecycle and are what Claude actually
  executes against — not ephemeral). These reference Copilot chat-variable syntax that means
  nothing to Claude Code and sometimes instruct the reader to reproduce it verbatim. Translate:

  - Frontmatter: replace Copilot's `tools: [...]` id list and `mode:`/`model:` fields with Claude
    subagent frontmatter (`name`, `description`, `tools` using Claude's own tool names, optionally
    `model`).
  - `#file:X` → a plain path reference (Claude reads the path directly, no resolution syntax needed).
  - `#codebase` / `#search` / `#usages` / `#findTestFiles` → Grep/Glob/Read.
  - `#fetch:<url>` → WebFetch.
  - `#githubRepo:"..."` → WebFetch/WebSearch against the repo, or `gh` via Bash.
  - Anything referencing a tool Claude Code has no equivalent for (e.g. Microsoft-specific
    connectors carried over from a template) → drop it, and say so in your summary to the user
    rather than inventing a fake equivalent.
  - `${input:name:default}` (Copilot prompt-file typed inputs) → plain prose stating the default
    behavior, noting the user can override it by telling Claude directly.
  - A "you MUST preserve this exact callout format" instruction that names Copilot chat-variable
    syntax → rewrite the instruction to ask for a plain citation format instead (e.g. `Source: <url>`
    or a markdown link). Reproducing dead Copilot syntax in Claude's own output is the one failure
    mode worth actively guarding against here.

  Before writing the output file, check whether the target path already exists **and is not
  already recorded as this source's output in the manifest** — if so, stop and ask the user rather
  than overwrite what may be a hand-written native file.

  After writing the output, record the pair:

  ```
  uv run python scripts/check_ai_config_sync.py record <source> <output>
  ```

## Step 3: Handle CONFLICT lines (hand-edited output, source removed)

Show the user the current (hand-edited) output content and ask what they want: keep it as a
permanent native file (in which case just leave it — it's already off the manifest's radar once
you `forget` it), delete it (delete the file yourself), or something else. Once resolved, clear the
stale entry:

```
uv run python scripts/check_ai_config_sync.py forget <source>
```

## Step 4: Report back

Summarize what you converted, what you recorded as reference-only, and anything you skipped or
need the user's input on (collisions, conflicts, dropped tool references). Keep it to a short list
— this is bookkeeping, not a design discussion.
