<!-- markdownlint-disable-file -->

# Task Details: Suppress Notify-Role Ping for HOST_SELECTED Games

## Research Reference

**Source Research**: .copilot-tracking/research/20260913-01-notify-role-self-signup-research.md

## Phase 1: Suppress `notify_role_ids` ping for `HOST_SELECTED` games

### Task 1.1: RED - Add a failing (xfail) test asserting no role mention for `HOST_SELECTED` games

`format_game_announcement` already exists and currently pings `notify_role_ids` unconditionally regardless of `signup_method` (research: "no existing coupling between `notify_role_ids` and `signup_method`"). This is an enhancement to already-existing production code, so there is no stub to create; follow the TDD "no stub, prove RED via xfail" workflow. Add one new test to `TestFormatGameAnnouncement` in `tests/unit/services/bot/formatters/test_game_message.py`, placed alongside the existing `test_format_game_announcement_with_regular_roles`/`_with_mixed_roles`/`_with_everyone_role` tests (lines 1679-1812), following their exact structure (same `patch` context managers for `discord.Embed`/`GameView`, same kwargs shape):

```python
@pytest.mark.xfail(
    reason="notify_role_ids not yet suppressed for HOST_SELECTED games",
    strict=True,
)
def test_format_game_announcement_host_selected_suppresses_role_mention(self):
    """Test format_game_announcement omits role mentions for HOST_SELECTED games."""
    scheduled_at = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)
    role_id = "987654321"
    host_id = "111111111"

    with (
        patch("services.bot.formatters.game_message.discord.Embed") as mock_embed_class,
        patch("services.bot.formatters.game_message.GameView") as mock_view_class,
    ):
        mock_embed_class.return_value = MagicMock()
        mock_view_class.from_game_data.return_value = MagicMock()

        content, _embed, _view = format_game_announcement(
            game_id="game-123",
            game_title="Test Game",
            description="Test description",
            scheduled_at=scheduled_at,
            host_id=host_id,
            participant_ids=[],
            overflow_ids=[],
            current_count=0,
            max_players=5,
            status="SCHEDULED",
            signup_method="HOST_SELECTED",
            notify_role_ids=[role_id],
        )

        assert content == format_discord_mention(host_id)
```

Requires `import pytest` in the test module if not already present, and confirm `format_discord_mention` is already imported (used elsewhere in the file's mention-assembly assertions, e.g. `test_format_game_announcement_mentions_host_and_confirmed_participants` at line 1814) — reuse rather than re-import. `pytest.mark.xfail(strict=True)` is required so the suite errors if the marker is left in place after Task 1.2.

- **Files**:
  - `tests/unit/services/bot/formatters/test_game_message.py` - add the new xfail test inside `TestFormatGameAnnouncement` (class starts line 1189), immediately after `test_format_game_announcement_with_mixed_roles` (ends line 1812)
- **Success**:
  - `uv run pytest tests/unit/services/bot/formatters/test_game_message.py -k host_selected_suppresses_role_mention -v` shows `1 xfailed` (proves the assertion is capable of detecting the current unsuppressed behavior — content today would be `f"<@&{role_id}> {format_discord_mention(host_id)}"`, not just the host mention)
  - No other existing test in the file is modified
- **Research References**:
  - .copilot-tracking/research/20260913-01-notify-role-self-signup-research.md (Lines 23-24 - `format_game_announcement` mention-loop mechanics, lines 791-803 of the source file) - confirms current unconditional mention-building behavior to prove RED against
  - .copilot-tracking/research/20260913-01-notify-role-self-signup-research.md (Lines 92-93 - Implementation Guidance Key Task 2, naming the exact new test case and file to extend)
  - .copilot-tracking/research/20260913-01-notify-role-self-signup-research.md (Lines 102-106 - resolved Open Questions confirming scope is `HOST_SELECTED` only, evaluated fresh on every render)
- **Dependencies**:
  - None - first task of the phase.

### Task 1.2: GREEN - Gate the role-mention loop on `signup_method` and remove the xfail marker

Implement the minimal production-code change in `services/bot/formatters/game_message.py`:

1. Change the import at line 44 from `from shared.models import GameStatus` to `from shared.models import GameStatus, SignupMethod` (matches the existing single-line re-export style; `SignupMethod` is already exported from `shared/models/__init__.py`).
2. Replace the mention-building loop at lines 791-797:

   ```python
   mentions = []
   for role_id in notify_role_ids or []:
       # Special handling: @everyone uses literal string, not <@&guild_id>
       if guild_id and role_id == guild_id:
           mentions.append("@everyone")
       else:
           mentions.append(f"<@&{role_id}>")
   ```

   with a version that skips role mentions entirely for `HOST_SELECTED` games (no user can self-join, per research's "Self-signup eligibility is a simple per-game property today" finding):

   ```python
   mentions = []
   if signup_method != SignupMethod.HOST_SELECTED.value:
       for role_id in notify_role_ids or []:
           # Special handling: @everyone uses literal string, not <@&guild_id>
           if guild_id and role_id == guild_id:
               mentions.append("@everyone")
           else:
               mentions.append(f"<@&{role_id}>")
   ```

   Leave the host-mention and participant-mention logic (lines 799-803) untouched — only the role-mention portion is gated.

3. Remove the `@pytest.mark.xfail(...)` marker from `test_format_game_announcement_host_selected_suppresses_role_mention` added in Task 1.1. Do NOT modify its assertion.

- **Files**:
  - `services/bot/formatters/game_message.py` - modify import (line 44) and mention-loop gate (lines 791-797)
  - `tests/unit/services/bot/formatters/test_game_message.py` - remove only the `xfail` marker from the Task 1.1 test
- **Success**:
  - `uv run pytest tests/unit/services/bot/formatters/test_game_message.py -k host_selected_suppresses_role_mention -v` shows `1 passed`
  - `uv run pytest tests/unit/services/bot/formatters/test_game_message.py -q` fully green (no regression in the surrounding `TestFormatGameAnnouncement` class, e.g. `test_format_game_announcement_with_regular_roles`/`_with_mixed_roles`/`_with_everyone_role` all still pass since they use `signup_method="SELF_SIGNUP"`)
  - `uv run mypy shared/ services/` clean
- **Research References**:
  - .copilot-tracking/research/20260913-01-notify-role-self-signup-research.md (Lines 81-85 - Recommended Approach: exact gate location and mechanics, "iterate `notify_role_ids or [] if signup_method != SignupMethod.HOST_SELECTED else []`")
  - .copilot-tracking/research/20260913-01-notify-role-self-signup-research.md (Lines 75-77 - "No configuration surface exists" confirms this is a pure code conditional, no schema/migration/config work)
  - .copilot-tracking/research/20260913-01-notify-role-self-signup-research.md (Lines 20 - `game_view.py` precedent for comparing `signup_method: str` against `SignupMethod.HOST_SELECTED.value`)
- **Dependencies**:
  - Task 1.1 complete (xfail test exists and is confirmed RED before this GREEN step).

### Task 1.3: Add regression coverage confirming the other three signup methods still ping

Writing tests for already-correct code (the ping behavior for `SELF_SIGNUP`, `HOST_SELECTED_WITH_WAITLIST`, and `ROLE_BASED` is unchanged by Task 1.2) — no `xfail`, no stub; write assertions directly and run them immediately per the "Writing Tests for Already-Correct Code" TDD rule. `SELF_SIGNUP` already has direct coverage via the three pre-existing tests at lines 1679/1723/1768 (unmodified, still green after Task 1.2 — that alone is regression evidence for `SELF_SIGNUP`). Add two new tests to `TestFormatGameAnnouncement`, one for `HOST_SELECTED_WITH_WAITLIST` and one for `ROLE_BASED`, each structured exactly like `test_format_game_announcement_with_regular_roles` (line 1723) but with `signup_method` swapped:

```python
def test_format_game_announcement_host_selected_with_waitlist_still_pings(self):
    """Test format_game_announcement still pings notify_role_ids for HOST_SELECTED_WITH_WAITLIST."""
    scheduled_at = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)
    role_id = "987654321"

    with (
        patch("services.bot.formatters.game_message.discord.Embed"),
        patch("services.bot.formatters.game_message.GameView"),
    ):
        content, _embed, _view = format_game_announcement(
            game_id="game-123",
            game_title="Test Game",
            description="Test description",
            scheduled_at=scheduled_at,
            host_id="host-456",
            participant_ids=[],
            overflow_ids=[],
            current_count=0,
            max_players=5,
            status="SCHEDULED",
            signup_method="HOST_SELECTED_WITH_WAITLIST",
            notify_role_ids=[role_id],
        )

        assert content is not None
        assert f"<@&{role_id}>" in content


def test_format_game_announcement_role_based_still_pings(self):
    """Test format_game_announcement still pings notify_role_ids for ROLE_BASED games."""
    scheduled_at = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)
    role_id = "987654321"

    with (
        patch("services.bot.formatters.game_message.discord.Embed"),
        patch("services.bot.formatters.game_message.GameView"),
    ):
        content, _embed, _view = format_game_announcement(
            game_id="game-123",
            game_title="Test Game",
            description="Test description",
            scheduled_at=scheduled_at,
            host_id="host-456",
            participant_ids=[],
            overflow_ids=[],
            current_count=0,
            max_players=5,
            status="SCHEDULED",
            signup_method="ROLE_BASED",
            notify_role_ids=[role_id],
        )

        assert content is not None
        assert f"<@&{role_id}>" in content
```

The `assert f"<@&{role_id}>" in content` plus the sibling `HOST_SELECTED` suppression test from Task 1.1 together satisfy the unit-tests negative-assertion rule (a claim that something is absent needs a sibling test proving it is present under a different, adjacent condition).

- **Files**:
  - `tests/unit/services/bot/formatters/test_game_message.py` - add the two regression tests inside `TestFormatGameAnnouncement`, adjacent to the Task 1.1 test
- **Success**:
  - `uv run pytest tests/unit/services/bot/formatters/test_game_message.py -q` fully green including the two new tests and all pre-existing tests in the class
  - `uv run pytest tests/unit -q` passes with zero failures/errors, no `xfail` markers remaining anywhere in this change
  - `uv run mypy shared/ services/` clean
- **Research References**:
  - .copilot-tracking/research/20260913-01-notify-role-self-signup-research.md (Lines 92-93 - Implementation Guidance Key Task 2, "regression case confirming SELF_SIGNUP/HOST_SELECTED_WITH_WAITLIST/ROLE_BASED are all unaffected (still ping)")
  - .copilot-tracking/research/20260913-01-notify-role-self-signup-research.md (Lines 106 - resolved Open Question #3: scope confirmed as `HOST_SELECTED` only; `ROLE_BASED` continues to ping unconditionally since every user can still self-join it)
  - .copilot-tracking/research/20260913-01-notify-role-self-signup-research.md (Lines 96-97 - Success Criteria: no regression for the three unaffected signup methods)
- **Dependencies**:
  - Task 1.2 complete (production gate implemented; these tests must pass against the post-fix code, proving no regression).

### Task 1.4: Add e2e coverage proving the real Discord message omits/includes the ping, including across an edit transition

Unit tests (Tasks 1.1-1.3) prove `format_game_announcement`'s own logic in isolation. This task additionally proves the fix works end-to-end (API → DB → RabbitMQ → bot → real Discord message), using the existing signup-method e2e suite rather than a new file, since it already creates real games, waits for real posted/updated messages, and covers exactly the `HOST_SELECTED`/`SELF_SIGNUP` scenarios and the edit transition between them.

1. Add a session-scoped fixture to `tests/e2e/test_signup_methods.py` reusing the test-role env var already required by `tests/e2e/test_role_based_signup.py` (lines 54-62) rather than adding a new required env var:

   ```python
   @pytest.fixture(scope="session")
   def notify_role_id() -> str:
       """Discord role ID used to verify notify-role ping presence/absence."""
       value = os.environ.get("DISCORD_TEST_ROLE_A_ID", "")
       if not value:
           pytest.fail(
               "DISCORD_TEST_ROLE_A_ID not set — see TESTING.md 'Role-Based Signup E2E Test Roles'"
           )
       return value
   ```

   Requires `import os` in the test module if not already present.

2. Extend `test_host_selected_disables_join_button` (line 144): add `notify_role_id` to its parameters, add `"notify_role_ids": json.dumps([notify_role_id])` to `game_data`, and after the existing button assertions add:

   ```python
   assert f"<@&{notify_role_id}>" not in message.content, (
       "HOST_SELECTED game should not ping notify_role_ids"
   )
   ```

3. Extend `test_self_signup_enables_join_button` (line 58) the same way, asserting the mention IS present — this is the required sibling "present" case proving the "absent" assertion in step 2 is meaningful and not just an empty/always-false check:

   ```python
   assert f"<@&{notify_role_id}>" in message.content, (
       "SELF_SIGNUP game should still ping notify_role_ids"
   )
   ```

4. Extend `test_edit_game_signup_method_self_to_host` (line 321): add `notify_role_id` to its parameters and `"notify_role_ids": json.dumps([notify_role_id])` to the initial `game_data` (omit it from `update_data` — per `services/api/routes/games.py` line 752, leaving `notify_role_ids` unset on the `PUT` keeps the previously-set value, so no change there is needed). After the existing `initial_message`/`updated_message` button assertions, add:

   ```python
   assert f"<@&{notify_role_id}>" in initial_message.content, (
       "SELF_SIGNUP game should ping notify_role_ids"
   )
   assert f"<@&{notify_role_id}>" not in updated_message.content, (
       "Editing to HOST_SELECTED should remove the notify_role_ids ping"
   )
   ```

5. Extend `test_edit_game_signup_method_host_to_self` (mirror image of step 4, starting `HOST_SELECTED` and editing to `SELF_SIGNUP`) the same way, asserting the mention is absent from `initial_message.content` and present in `updated_message.content` — this is the direct end-to-end proof of the resolved open question that a transition into a joinable `signup_method` correctly (re-)pings.

- **Files**:
  - `tests/e2e/test_signup_methods.py` - add the `notify_role_id` fixture and extend the four named tests with mention assertions
- **Success**:
  - `SKIP_STARTUP=1 SKIP_CLEANUP=1 ./scripts/run-e2e-tests.sh tests/e2e/test_signup_methods.py` (per `.github/instructions/test-execution.instructions.md`, always captured via `tee`) passes all four extended tests plus the two untouched tests in the file
  - No other e2e test file is modified
- **Research References**:
  - .copilot-tracking/research/20260913-01-notify-role-self-signup-research.md (Lines 102-104 - resolved Open Questions: scope is `HOST_SELECTED` only, transitions correctly re-ping, `ROLE_BASED` unaffected) - this task is the end-to-end proof of those resolutions
- **Dependencies**:
  - Task 1.2 complete (production gate implemented; e2e assertions must pass against the post-fix code).
  - Full e2e stack running (`scripts/run-e2e-tests.sh`) and `DISCORD_TEST_ROLE_A_ID` configured per `docs/developer/TESTING.md`.

## Dependencies

- `pytest` `xfail(strict=True)` marker support (already used elsewhere in the repo per `.github/instructions/test-driven-development.instructions.md`).
- `uv run pytest tests/unit` and `uv run mypy shared/ services/` as the phase-completion gates (no frontend files are touched by this change, so the frontend build/test gates do not apply).
- `scripts/run-e2e-tests.sh`, scoped to `tests/e2e/test_signup_methods.py`, as the Task 1.4 completion gate (per `.github/instructions/test-execution.instructions.md` - always capture full output with `tee`).

## Success Criteria

- `format_game_announcement` omits `notify_role_ids` mentions in `content` when `signup_method == "HOST_SELECTED"`, verified by a passing (non-xfail) test.
- `SELF_SIGNUP`, `HOST_SELECTED_WITH_WAITLIST`, and `ROLE_BASED` all continue to ping `notify_role_ids`, each verified by a passing test.
- `uv run pytest tests/unit` green; `uv run mypy shared/ services/` clean.
- A real Discord message reflects the same behavior end-to-end, including across a `signup_method` edit transition, verified by `tests/e2e/test_signup_methods.py`.
- Diff is confined to `services/bot/formatters/game_message.py` (import + conditional), `tests/unit/services/bot/formatters/test_game_message.py` (new tests), and `tests/e2e/test_signup_methods.py` (extended tests) - no schema, migration, or config changes anywhere.
