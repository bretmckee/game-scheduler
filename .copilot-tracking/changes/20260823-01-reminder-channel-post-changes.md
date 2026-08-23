# Changes: Move Game Reminders from DMs to Location Channel/Thread Posts

## Phase 1: Location Channel Resolution Helper

### Task 1.1: Unit tests for `extract_single_channel_id` (RED)

- Added import of `extract_single_channel_id` plus 7 behavioral test cases to
  `tests/unit/shared/utils/test_discord_utils.py`:
  - `None` input → `None`
  - Empty string → `None`
  - Plain text with no mention → `None`
  - Exactly one `<#id>` token → ID returned
  - One mention with surrounding prose → ID returned
  - Two mentions → `None` (ambiguous)
  - Unresolved `#name` mention → `None` (only snowflake tokens count)

### Task 1.2: Implement `extract_single_channel_id` (GREEN)

- Added module-level compiled regex `_CHANNEL_SNOWFLAKE_TOKEN = re.compile(r"<#(\d+)>")`
  and the pure helper `extract_single_channel_id(where: str | None) -> str | None`
  to `shared/utils/discord.py`. Returns the captured channel ID only when exactly
  one `<#id>` token is present; otherwise `None`.
- Added `import re` to the module imports.

**Verification**: `uv run pytest tests/unit` — 2525 passed; `uv run mypy shared/ services/` — clean.
