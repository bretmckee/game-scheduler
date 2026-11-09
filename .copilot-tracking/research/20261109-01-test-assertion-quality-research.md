<!-- markdownlint-disable-file -->

# Task Research Notes: Hollow mock assertions and the test-assertion checker

## Research Executed

### File Analysis

- .github/instructions/unit-tests.instructions.md (191 lines)
  - Says to write assertions first (L8) and forbids assertions written only to satisfy the scanner (L24-37).
  - Never states the checker's mechanical rules. The closing checklist (L183-191) has no item for named `patch(...) as name` aliases.
- docs/developer/fix-test-assertion-violations.md
  - The only place the "named mock 'x' has no assert_* call" rule is described, including "remove the `as mock_x` alias if the mock is irrelevant". Readers find it only after the hook fails.
- scripts/check_test_assertions.py
  - `get_unasserted_named_mocks` (L188-207): every `with patch(...) as alias` needs an `alias.assert_*` call (`_alias_has_assert_call`, L160) or a verification attribute read directly on the alias (`_alias_has_attr_verification`, L174). Setup such as `alias.return_value.__aenter__ = ...` does not count. Neither does using `alias.return_value` inside another mock's assertion.
  - `_exempt_or_marker_violation` (L398-427): an empty `assert_called_once_with()` passes when the patch target's last name is in `no-arg-methods` (L410-412). Jedi is used only to validate `# assert-not-weak` markers (L564-590).
- pyproject.toml L246-247: `no-arg-methods` mixes two kinds of method:
  - **Actions** (the call is the behavior): `flush`, `commit`, `rollback`, `close`, `connect`, `start_consuming`, `touch`, `instrument`, `flush_telemetry`, `disconnect`, `serve`
  - **Providers** (the call only supplies a dependency): `get_config`, `get_redis_client`, `get_db_session`, `get_role_service`, `get_discord_client`, `get_api_config`
- tests/unit/scripts/test_check_test_assertions.py: 153 tests cover the checker.

### Code Search Results

- AST scan of `tests/unit/**/test_*.py` for no-argument `assert_called_once_with()`, `assert_called_with()`, `assert_awaited_once_with()` and `assert_awaited_with()` inside test functions, with the receiver traced to its `patch()` target
  - 113 assertions in total. 137 by grep, which also includes nested helpers and the checker's own fixtures.
  - 88 are on providers: `get_db_session` 39, `get_role_service` 14, `get_redis_client` 13, `get_discord_client` 10, `get_api_config` / `get_config` 12.
  - 25 are on actions or other targets: `.instrument()`, the init phases in services/init/test_main_roles_only.py, `serve()`, `disconnect()`, `touch()`, `interaction.response.defer()`, `message.delete()`, and the cache singleton construction.
- Files with the most provider assertions:

  | File                                                              | Count    |
  | ----------------------------------------------------------------- | -------- |
  | tests/unit/services/api/routes/test_templates.py                  | 14       |
  | tests/unit/shared/discord/test_discord_api_client.py              | 9        |
  | tests/unit/services/bot/events/test_handlers_status_transition.py | 8        |
  | tests/unit/api/services/test_guild_service_channel_refresh.py     | 7        |
  | tests/unit/services/bot/commands/test_my_games.py                 | 6        |
  | 16 other files                                                    | 1-5 each |

- `# assert-not-weak:` markers in tests/: 26
  - Most mark genuine no-argument actions, e.g. `wait_for_postgres`, `create_database_users`, `run_migrations`, `verify_schema`, `create_dm`.
  - 4 mark `get_db_session()` and 2 mark `get_config()`. These are the same provider pattern.
- No shared `get_db_session` fixture exists in any tests/unit conftest.py. Every bot handler test sets up `__aenter__` / `__aexit__` inline.

### External Research

- None needed. The task concerns project-local tooling and conventions only.

### Project Conventions

- Standards referenced: unit-tests.instructions.md, test-driven-development.instructions.md, quality-check-overrides.instructions.md (gating of `APPROVED_WEAK_ASSERTIONS`)
- Instructions followed: researcher-enhancements.instructions.md (no version recommendations needed)

## Key Discoveries

### Project Structure

| Piece                                           | Role                                                                       |
| ----------------------------------------------- | -------------------------------------------------------------------------- |
| scripts/check_test_assertions.py                | pre-commit hook `check-test-assertions` (.pre-commit-config.yaml L144-149) |
| pyproject.toml `[tool.check-test-assertions]`   | `no-arg-methods` allowlist                                                 |
| docs/developer/fix-test-assertion-violations.md | fix patterns, shown in the hook's failure output                           |
| .github/instructions/unit-tests.instructions.md | authoring guidance that agents read before writing tests                   |

### Implementation Patterns

**Where the hollow assertions came from.** On 2026-04-26 a series of commits added the named-mock rule and allowlisted the provider getters to cut false positives:

- `8e775a52` added `get_config`.
- `1a5e34c6` added `get_redis_client` and resolved patch aliases.
- Batch commits `0d8d5c0e`, `d1b04a81`, `93f526ab` and `84401f0a` then added assertions across many files.

The result is that the named-mock rule demands an assertion on provider patches, and the allowlist accepts an empty one. Together they reward `mock_get_x.assert_called_once_with()`, which unit-tests.instructions.md L24-37 explicitly forbids.

Before then, the provider aliases already existed, set up but never asserted. `5a4fb3cf` (2026-04-26, test_discord_api_client.py) shows the pattern: it only appended `mock_get_redis.assert_called_once_with()` after unchanged test bodies. Later code copied it, e.g. `810f7094` (2026-05-29).

**How it showed up (2026-11-09).** The three regression tests in commit `6882f984` failed the named-mock rule:

- `get_db_session` in test_handlers_clone.py, test_handlers_game_reminder.py and test_handlers_recurrence_confirmation.py
- `RecurrenceConfirmationView` in test_handlers_recurrence_confirmation.py

They were satisfied by adding hollow `mock_db_session.assert_called_once_with()` lines. The view case was a false positive: the test already asserted `send(..., view=mock_view_cls.return_value)`.

### Complete Examples

```python
# Hollow (tests/unit/shared/discord/test_discord_api_client.py, test_fetch_channel_cache_hit)
with patch("shared.discord.client.cache_client.get_redis_client") as mock_get_redis:
    ...
    mock_redis.get.assert_called_once_with("discord:channel:channel123")  # real check
mock_get_redis.assert_called_once_with()                                  # adds nothing

# Idiomatic, already used in the repo (tests/unit/services/api/test_app.py L120)
patch("services.api.app.redis_client.get_redis_client", return_value=mock_redis_client)
```

```python
# get_db_session (async context manager), before: named only to be set up
with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
    mock_db_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db_session.return_value.__aexit__ = AsyncMock(return_value=None)
    ...
mock_db_session.assert_called_once_with()

# after: build the fake first, patch without a name, no assertion
session_cm = MagicMock()
session_cm.__aenter__ = AsyncMock(return_value=mock_db)
session_cm.__aexit__ = AsyncMock(return_value=None)
with patch("services.bot.events.handlers.get_db_session", return_value=session_cm):
    ...
```

### API and Schema Documentation

The checker reports these violation types (see the fix-patterns doc):

- no assertions
- named mock with no `assert_*` call
- `assert_called_once()`
- empty `assert_called_once_with()` (allowlisted names exempt)
- every argument is `ANY`

Each `# assert-not-weak: <reason>` marker counts against `APPROVED_WEAK_ASSERTIONS`.

### Configuration Examples

```toml
# Proposed (pyproject.toml [tool.check-test-assertions]): providers removed, actions kept
no-arg-methods = ["flush", "commit", "rollback", "close", "connect", "start_consuming",
                  "touch", "instrument", "flush_telemetry", "disconnect", "serve"]
```

### Technical Requirements

- TDD applies to the checker's false-positive fix (Python, existing test suite): write xfail tests in test_check_test_assertions.py first. Trimming `no-arg-methods` is configuration only. Confirm it with a checker test that an empty assertion on a patched `get_db_session` is reported.
- The test cleanup is retrofitting. No xfail. Each edited file must still pass, and the checker must report no violations for it.
- The config trim and the test cleanup must land together. Once the providers are removed, `--all` reports every remaining hollow assertion. The pre-commit hook (no `--diff-only` flag, .pre-commit-config.yaml L146) checks whole staged test files, so any leftover would block the next unrelated commit that touches its file.
- Instruction and doc edits are Markdown, so TDD does not apply.
- Keep this work out of the game-time-change-notification PR. It is independent of it.

## Recommended Approach

Stop treating dependency getters as "no-argument methods", and rewrite their setup so tests carry no name for a mock they never check. The checker gains no new concept, and the tests end up in the form already used at tests/unit/services/api/test_app.py L120.

1. **Checker config** (pyproject.toml L247): remove `get_config`, `get_api_config`, `get_redis_client`, `get_db_session`, `get_role_service` and `get_discord_client` from `no-arg-methods`. Keep the action methods.
2. **Checker code** (scripts/check_test_assertions.py): count an alias as verified when it appears anywhere inside the arguments of an `assert_*` call or an `assert` statement. This fixes the `view=mock_view_cls.return_value` false positive. Write the xfail tests first.
3. **Cleanup**, every site that `uv run python scripts/check_test_assertions.py --all` reports after step 1:
   - Build the fake before the `patch`, pass it as `return_value=`, drop the `as name`, and delete the empty assertion.
   - Where a test's subject is the getter call itself (e.g. `test_lifespan_initializes_redis`), keep the assertion and add `# assert-not-weak: <reason>`, gated by `APPROVED_WEAK_ASSERTIONS`.
   - Rewrite the 6 provider-related markers (4 `get_db_session`, 2 `get_config`) the same way.
   - Include the three tests from commit `6882f984`. Keep their `mock_view_cls.assert_called_once_with(str(sample_game.id))` check.
   - Start with the largest files: test_templates.py, test_discord_api_client.py, test_handlers_status_transition.py.
4. **Docs**:
   - Add a "What the Pre-Commit Checker Enforces" section to unit-tests.instructions.md listing all five violation types and the rule "only name a patch you intend to check; supply setup-only fakes with `return_value=`". Include the command `uv run python scripts/check_test_assertions.py <files>`.
   - Add the checklist item "every `patch(...) as name` has an `assert_*` call, or the `as name` is removed".
   - In fix-test-assertion-violations.md, make the unnamed `return_value=` patch the first fix for the named-mock violation, and drop any wording that suggests asserting a getter with no arguments.

## Implementation Guidance

- **Objectives**: New tests are written correctly the first time. Tests use unnamed patches for setup-only fakes. The checker neither forces nor accepts hollow assertions on dependency getters.
- **Key Tasks**:
  1. xfail checker tests, then the false-positive fix.
  2. Trim `no-arg-methods` and add a checker test that an empty assertion on a patched `get_db_session` is reported.
  3. Rewrite every reported site in the same change.
  4. Update unit-tests.instructions.md and fix-test-assertion-violations.md.
- **Dependencies**: test_check_test_assertions.py (153 tests); the pre-commit `check-test-assertions` hook; `--all` mode (`_select_files`, L638).
- **Success Criteria**:
  - The checker suite passes, including new tests for: an empty assertion on a patched provider (violation), and an alias used only inside another assertion's arguments (ok).
  - `uv run python scripts/check_test_assertions.py --all` reports no violations.
  - No `patch(...)` of a provider is named without being checked.
  - `uv run pytest tests/unit` passes.
- **Timing**: after the game-time-change-notification plan is fully implemented, in its own PR.

## Outstanding:

- Decide whether to also review the 20 action-method `# assert-not-weak` markers (out of scope above).
- Confirm the per-test judgment for the few provider assertions that are the behavior under test. Only `test_lifespan_initializes_redis` is identified so far.
