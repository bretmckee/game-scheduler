<!-- markdownlint-disable-file -->

# Task Details: Test Assertion Quality (hollow provider assertions)

## Research Reference

**Source Research**: .copilot-tracking/research/20261109-01-test-assertion-quality-research.md

Conventions: Phases 1-2 use TDD (checker is new behavior in existing code; xfail RED then GREEN). Phases 3-5 are retrofitting existing tests (no xfail). Phase 6 is Markdown. Every phase gate: `uv run pytest tests/unit`, `uv run mypy shared/ services/`, and `uv run python scripts/check_test_assertions.py <touched files>` clean. Never run `pytest --testmon`.

Ordering rationale: cleanup phases (3-5) come BEFORE the config trim (Phase 5 end) so each commit passes the pre-commit hook; unnamed `patch(..., return_value=fake)` passes under both the old and new allowlist. The trim lands in the same phase as the last leftover cleanup (research Lines 147).

Cleanup recipe (all sites): build the fake before the `patch`, pass `return_value=`, drop `as name`, delete the empty assertion; keep any real assertions (research Lines 107-121). If the alias is used elsewhere (e.g. `mock_x.return_value` inside another assertion), keep the name only if it is then checked.

## Phase 1: RED - checker xfail tests

### Task 1.1: Add xfail tests for the false-positive fix

Add to tests/unit/scripts/test_check_test_assertions.py, marked `@pytest.mark.xfail(strict=True, reason=...)`, following the file's existing fixture/helper style (read neighbouring tests first):

- alias used only inside another `assert_*` call's arguments (e.g. `send.assert_called_once_with(view=mock_view_cls.return_value)`) -> no violation
- alias used only as an operand of `==`, `!=`, `is`, `is not`, `in` in an `assert` statement -> no violation
- alias used only as bare `assert mock_x` -> still a violation (passes today; add as a regular non-xfail guard test)

- **Files**: tests/unit/scripts/test_check_test_assertions.py
- **Success**: new xfail tests XFAIL for the right reason (not import/syntax error); suite passes; checker clean on the edited file
- **Research References**: research (Lines 15, 92, 157, 182-186)
- **Dependencies**: none

## Phase 2: GREEN - checker false-positive fix

### Task 2.1: Count alias use in assert-call arguments and assert comparisons

In scripts/check_test_assertions.py, extend alias verification (`_alias_has_assert_call` L160, `_alias_has_attr_verification` L174, consumed by `get_unasserted_named_mocks` L188-207) so an alias counts as verified when its attribute chain appears (a) anywhere inside the arguments/keywords of an `assert_*` call, or (b) as an operand of `Compare` with Eq/NotEq/Is/IsNot/In/NotIn inside an `ast.Assert`. Bare `assert mock_x` must not count. Remove the xfail markers from Task 1.1 tests.

- **Files**: scripts/check_test_assertions.py, tests/unit/scripts/test_check_test_assertions.py
- **Success**: all tests pass with xfail markers removed; mypy clean; `uv run python scripts/check_test_assertions.py --all` shows no NEW violation types versus before (only possible reduction)
- **Research References**: research (Lines 15, 157, 182-186)
- **Dependencies**: Task 1.1

## Phase 3: Cleanup - largest provider files

### Task 3.1: Rewrite hollow provider assertions in the five largest files

Files and hollow counts: tests/unit/services/api/routes/test_templates.py (14), tests/unit/shared/discord/test_discord_api_client.py (9), tests/unit/services/bot/events/test_handlers_status_transition.py (8), tests/unit/api/services/test_guild_service_channel_refresh.py (7), tests/unit/services/bot/commands/test_my_games.py (6). Targets are the empty `assert_called_once_with()` / `assert_called_with()` / `assert_awaited*_with()` on patches of `get_db_session`, `get_role_service`, `get_redis_client`, `get_discord_client`, `get_api_config`, `get_config`. For `get_db_session` build `session_cm = MagicMock()` with `__aenter__`/`__aexit__` (research Lines 115-120). Existing idiom: tests/unit/services/api/test_app.py L120.

Find sites: `uv run python - <<'PY'` AST scan or grep `assert_.*called.*_with()` in the file; also confirm by temporarily setting `no-arg-methods` without the providers in a local pyproject edit, running the checker on the file, then REVERTING pyproject.toml (do not commit the trim here).

- **Files**: the five test files above
- **Success**: no empty provider assertions or setup-only `as mock_get_*` names remain in these files; same tests still pass with unchanged real assertions (do not weaken any); checker clean
- **Research References**: research (Lines 26-39, 96-121)
- **Dependencies**: Phase 2 not required, but do after it for a clean checker

## Phase 4: Cleanup - remaining provider files and markers

### Task 4.1: Rewrite remaining provider sites (the 16 other files, 1-5 each)

Enumerate with the AST scan from Task 3.1 (research Lines 26-29: 88 provider assertions total; ~52 remain after Phase 3). Same recipe.

- **Files**: remaining files containing hollow provider assertions (e.g. test_handlers_clone.py, test_handlers_game_reminder.py, test_handlers_recurrence_confirmation.py)
- **Success**: scan finds zero provider-target empty assertions repo-wide in tests/unit (except the two getter-under-test sites handled in Task 5.1)
- **Research References**: research (Lines 26-43, 87-92)
- **Dependencies**: Task 3.1

### Task 4.2: Remove the 6 provider `# assert-not-weak:` markers

Rewrite 4 `get_db_session` sites in test_handlers_join_notification.py (L86, L141, L176, L215) and 2 `get_config` sites in test_game_message.py (L547, L1312): unnamed patch with `return_value=`, delete assertion and marker. Include the three `6882f984` tests: keep `mock_view_cls.assert_called_once_with(str(sample_game.id))`; drop the hollow `mock_db_session` assertion.

- **Files**: tests/unit/services/bot/events/test_handlers_join_notification.py (path: locate via grep), tests/unit/services/bot/.../test_game_message.py (locate via grep)
- **Success**: marker count in tests/ drops 25 -> 19; checker clean
- **Research References**: research (Lines 44-46, 87-92, 164-165)
- **Dependencies**: Task 4.1

## Phase 5: Hollow non-provider markers, getter-under-test sites, config trim

### Task 5.1: Fix two hollow non-provider markers and two getter-under-test tests

- test_game_message.py L1277 `mock_formatter_class.assert_called_once_with()` and test_channels.py L231 `mock_result.scalar_one.assert_called_once_with()`: remove assertion and marker (setup only; unnamed/return_value form where the alias is then unused).
- `test_lifespan_initializes_redis` (tests/unit/services/api/test_app.py ~L113): keep the getter assertion, add `# assert-not-weak: <reason: lifespan calling get_redis_client is the behavior>`.
- `test_get_redis_lazy_initialization` (test_cache.py L144): change bare `assert_called_once()` to `assert_called_once_with()` and add the marker with reason.
- `test_main_uses_config_values` (test_api_main.py ~L114): drop empty assertion on `mock_config`; keep `uvicorn.Config` kwarg checks.

Marker net effect: 25 - 6 (provider, Task 4.2) - 2 (hollow) + 2 (getter) = 19. Adding markers is gated by `_check_marker_quota` / `APPROVED_WEAK_ASSERTIONS` (see quality-check-overrides.instructions.md); the user must supply `APPROVED_WEAK_ASSERTIONS=2` (or the project's mechanism) for the commit. Flag this to the user rather than bypassing.

- **Files**: test_game_message.py, test_channels.py, test_app.py, test_cache.py, test_api_main.py (locate via grep)
- **Success**: tests pass; markers present only where the call is the behavior
- **Research References**: research (Lines 51, 160-164, 188)
- **Dependencies**: Phase 4

### Task 5.2: Trim `no-arg-methods` and add checker regression test

pyproject.toml L247: set `no-arg-methods = ["flush", "commit", "rollback", "close", "connect", "start_consuming", "touch", "instrument", "flush_telemetry", "disconnect", "serve"]`. Add a checker test that an empty `assert_called_once_with()` on `patch("...get_db_session") as m` is reported (verify how the test supplies config; if the tests use a fixed config rather than pyproject, also assert via the real pyproject value). Run `uv run python scripts/check_test_assertions.py --all`; it must report zero violations. Fix any stragglers found.

- **Files**: pyproject.toml, tests/unit/scripts/test_check_test_assertions.py
- **Success**: `--all` clean; full unit suite passes; no named provider patch lacks a real check
- **Research References**: research (Lines 17-21, 138-141, 147, 177, 187-190)
- **Dependencies**: Task 5.1

## Phase 6: Docs

### Task 6.1: Update authoring guidance and fix-patterns docs

- .github/instructions/unit-tests.instructions.md: add section "What the Pre-Commit Checker Enforces" listing the seven violation types (no assertions; named mock with no `assert_*`; `assert_called_once()`; empty `assert_called_once_with()` with allowlist exemption, noting empty awaited and `_called_with` forms are not checked; all-`ANY` arguments; `# assert-not-weak:` marker on a call whose target takes parameters (Jedi); marker quota vs `APPROVED_WEAK_ASSERTIONS`), the rule "only name a patch you intend to check; supply setup-only fakes with `return_value=`", and the command `uv run python scripts/check_test_assertions.py <files>`. Add checklist item to the closing list (L183-191): every `patch(...) as name` has an `assert_*` call, or the `as name` is removed.
- docs/developer/fix-test-assertion-violations.md: make the unnamed `return_value=` patch the first fix for the named-mock violation; remove wording suggesting asserting a getter with no arguments.

- **Files**: the two Markdown files
- **Success**: markdownlint/prettier pre-commit hooks pass; content matches the checker's actual behavior (spot-check against scripts/check_test_assertions.py)
- **Research References**: research (Lines 9-13, 125-133, 167-170)
- **Dependencies**: Phase 5 (documents final behavior)

## Dependencies

- scripts/check_test_assertions.py, pre-commit `check-test-assertions` hook, `uv`, pytest

## Success Criteria

- Checker suite passes with 3 new behavior tests plus provider regression test
- `uv run python scripts/check_test_assertions.py --all` reports no violations
- Marker count 25 -> 19; `uv run pytest tests/unit` and mypy pass
