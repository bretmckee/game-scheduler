---
description: 'Unit test quality standards — prevent coverage theater, require behavioral assertions'
applyTo: '**/test_*.py'
---

# Unit Test Quality Standards

## When Generating Test Code: Start With the Assertions

When writing a test, the first question is not "how do I call this function?" — it is "what assertions would prove this function is working correctly?"

The assertions are the test. Setup, mocks, and fixtures are scaffolding. A test body that calls a function but asserts nothing is not a test — it proves only that no exception was raised.

**Before writing any test body:** identify the concrete behavior to verify. Write or plan your assertions first, then write the setup around them.

Coverage measures which lines were executed, not whether behavior was verified. Missing coverage is evidence of untested paths. Present coverage says nothing about test quality.

## Core Principle: Tests Must Be Falsifiable

A unit test is only valuable if a wrong implementation would cause it to fail. A test that passes regardless of what the code does provides false confidence and is worse than no test — it teaches the coverage tool that a branch is "covered" while hiding real bugs.

**Before writing a test, ask:** if I swap two arguments, delete a return value, or invert a condition, will this test catch it? If the answer is no, the test needs more assertions.

## The Scanner Is a Floor, Not a Target

The pre-commit checker flags common patterns of weak assertions. Satisfying the checker is the minimum bar — not the goal. The goal is tests that catch real bugs.

**Do not write assertions whose only purpose is to silence the checker.** If the only way to satisfy a violation is to add an assertion that doesn't verify anything meaningful, the right response is to write a better test, not to add a hollow assertion.

Examples of gaming the scanner that are explicitly prohibited:

- Adding `assert True` to a test that has observable behavior that should be verified
- Replacing `assert_called_once()` with `assert mock.call_count == 1` to avoid the weak-assert check
- Using `assert_called_once_with(ANY, ANY)` when the actual arguments are available and verifiable
- Adding `# assert-not-weak: <reason>` to avoid writing real argument assertions

When you encounter a scanner violation, ask: **what is the code under test actually doing that I should be verifying?** Answer that question, then write the assertion. The scanner violation will resolve as a side effect.

## Required: Every Test Function Must Have at Least One Assertion

Every `test_*` function must contain at least one of:

- An `assert` statement
- A mock call-verification call (`assert_called_once_with`, `assert_called_with`, `assert_any_call`, `assert_not_called`, `assert_awaited_once_with`, etc.)
- A `pytest.raises(...)` context manager

A test body that only calls the function under test and makes no assertions does not verify behavior — it only verifies that no exception is raised.

```python
# BAD: no assertion — only proves no exception was raised
async def test_handle_game_created_not_found(handlers, mock_deps):
    mock_deps.game_service.get_game.return_value = None
    await handlers.handle_game_created({"game_id": "123"})

# GOOD: asserts the downstream call was suppressed
async def test_handle_game_created_not_found(handlers, mock_deps):
    mock_deps.game_service.get_game.return_value = None
    await handlers.handle_game_created({"game_id": "123"})
    mock_deps.publisher.publish_game_created.assert_not_called()
```

If the intent genuinely is "no exception raised," make that explicit:

```python
# ACCEPTABLE: explicit intent, not an oversight
async def test_handle_game_created_not_found_does_not_raise(handlers, mock_deps):
    mock_deps.game_service.get_game.return_value = None
    # No downstream action expected when game is not found
    await handlers.handle_game_created({"game_id": "123"})
    assert True  # documents the intent: no exception is the assertion
```

## Mock Call Verification: Use `assert_called_once_with`, Not `assert_called_once`

`assert_called_once()` confirms the mock was invoked but ignores what arguments were passed. `assert_called_once_with(...)` verifies both invocation and arguments. Almost always prefer the latter.

```python
# BAD: confirms a call happened but not what was passed
mock_session.add.assert_called_once()

# GOOD: verifies the correct object was passed
mock_session.add.assert_called_once_with(expected_participant)
```

Use `unittest.mock.ANY` when exact argument values are not the point of the test, such as for log message strings:

```python
from unittest.mock import ANY

# GOOD: verifies error was logged with the exception, not the exact message wording
mock_logger.error.assert_called_once_with(ANY, caught_exception)
```

## Do Not Verify Only That Code Ran

Tests that set up mocks and call the function under test without verifying the outcome are coverage theater. The mock return values used during setup are also assertions about expected behavior — if a mock returns a specific value, the test should verify that value was used correctly.

```python
# BAD: sets up 5 mocks, calls the function, asserts nothing
async def test_process_event(handler, mock_db, mock_publisher, mock_cache, mock_logger):
    mock_db.execute.return_value = mock_result
    mock_result.scalar_one_or_none.return_value = mock_game
    await handler.process_event(event)
    # no assertions

# GOOD: verifies what actually happened with the returned game
async def test_process_event(handler, mock_db, mock_publisher, mock_cache, mock_logger):
    mock_db.execute.return_value = mock_result
    mock_result.scalar_one_or_none.return_value = mock_game
    await handler.process_event(event)
    mock_publisher.publish_game_updated.assert_called_once_with(mock_game.id)
```

## Prefer Behavioral Assertions Over Call-Count Assertions

Asserting on return values, state changes, or specific argument values is stronger than asserting only that a method was called. Call-count assertions (e.g., `assert_called_once`) are appropriate for side-effect-only functions where no return value exists.

```python
# WEAK: only verifies flush was called once
mock_session.flush.assert_called_once()

# STRONGER: verifies the object was added before flush
mock_session.add.assert_called_once_with(new_record)
mock_session.flush.assert_called_once()
```

## Negative Assertions Require a Trigger

`assert_not_called()` is only meaningful when the test exercises a code path that would call the mock if the condition being tested were different. A test that calls `assert_not_called()` on a mock that has no reason to be called in any scenario is not testing anything.

```python
# BAD: mock_redis.delete can never be called here — not testing anything
async def test_some_path(handler):
    await handler.run()
    mock_redis.delete.assert_not_called()

# GOOD: another code path does call mock_redis.delete; this test verifies it's
# suppressed when the condition is False
async def test_cache_not_invalidated_when_flag_is_false(handler, mock_redis):
    await handler.run(invalidate=False)
    mock_redis.delete.assert_not_called()
```

## One Behavior Per Test

Each test function should verify one specific behavior or scenario. Long test functions with many mocks and many assertions usually indicate multiple behaviors that should be split into separate tests with clear names.

```python
# BAD: testing two distinct behaviors in one function
async def test_participant_removal(handler, mock_db, mock_publisher):
    # scenario 1
    mock_participant.status = "WAITLISTED"
    await handler.remove_participant(event)
    mock_publisher.publish_promoted.assert_called_once()
    # scenario 2
    mock_participant.status = "CONFIRMED"
    await handler.remove_participant(event)
    mock_publisher.publish_removed.assert_called_once()

# GOOD: separate tests with clear names
async def test_waitlisted_participant_removal_triggers_promotion(handler, mock_db, mock_publisher):
    mock_participant.status = "WAITLISTED"
    await handler.remove_participant(event)
    mock_publisher.publish_promoted.assert_called_once_with(mock_participant.id)

async def test_confirmed_participant_removal_publishes_removed(handler, mock_db, mock_publisher):
    mock_participant.status = "CONFIRMED"
    await handler.remove_participant(event)
    mock_publisher.publish_removed.assert_called_once_with(mock_participant.id)
```

## Telemetry: Assert on Metric Calls When the Metric Is the Feature

Do not skip metric assertions just because "it's just telemetry." If a function's purpose includes emitting a counter or histogram, the test should verify the metric was incremented with the correct labels.

```python
# GOOD: metric increment is part of the observable contract
mock_counter.add.assert_called_once_with(1, {"reason": "on_ready", "status": "success"})
```

Use `unittest.mock.ANY` for description strings or unit strings if those details are not the focus.

## What the Pre-Commit Checker Enforces

The `check-test-assertions` pre-commit hook (`scripts/check_test_assertions.py`) reports these violations. Run it directly on the files you touched before committing:

```bash
uv run python scripts/check_test_assertions.py <files>
```

1. **No assertions** — the test has no `assert` statement, no `assert_*` mock call, and no `pytest.raises`.
2. **Named mock with no verification** — a `with patch(...) as name:` or `patch.object(...) as name:` alias is never checked. It counts as checked if any of these happens: an `assert_*` method is called on it or on an attribute chain from it; one of its call-tracking attributes (`called`, `call_count`, `await_count`, `call_args`, `call_args_list`, ...) is read; it appears in another `assert_*` call's arguments; or it is an operand of `==`, `!=`, `is`, `is not`, `in`, or `not in` inside an `assert`. A bare `assert mock_x` does not count, because a mock is always truthy.
3. **Bare `assert_called_once()`** — use `assert_called_once_with(...)`. Adding a `# assert-not-weak:` marker to a bare `assert_called_once()` is itself a violation.
4. **Empty `assert_called_once_with()`** — exempt only when the mocked method name, or the last component of the patch target, is listed in `[tool.check-test-assertions] no-arg-methods` in `pyproject.toml`, when the test reads `.call_args`/`.call_args_list` on the same mock, or when the line carries a `# assert-not-weak: <reason>` marker. The allowlist holds action methods such as `flush`, `commit`, and `close`, not dependency getters. The empty awaited forms (`assert_awaited_once_with()`) and `assert_called_with()` are not checked; do not take that as permission to write them.
5. **All-`ANY` arguments** — `assert_called_once_with(ANY, ...)` or `assert_awaited_once_with(ANY, ...)` where every argument is `ANY`.
6. **Marker on a call that takes parameters** — when Jedi can resolve the patch target and it has required parameters, a `# assert-not-weak:` marker on its empty assertion is reported.
7. **Marker quota** — in the pre-commit hook, `# assert-not-weak:` markers added in the staged diff that Jedi cannot verify as no-argument are counted, and the commit is blocked if the count exceeds `APPROVED_WEAK_ASSERTIONS` (see `quality-check-overrides.instructions.md`).

**Only name a patch you intend to check.** When a patch only supplies a setup fake, such as a dependency getter like `get_db_session`, `get_config`, or `get_redis_client`, build the fake first and pass it with `return_value=`. Then verify how the fake was used.

```python
# BAD: the name exists only to satisfy the checker; the empty assertion proves nothing
with patch("services.bot.events.handlers.get_config") as mock_get_config:
    mock_get_config.return_value.frontend_url = "https://example.com"
    await handlers.notify(game)
mock_get_config.assert_called_once_with()

# GOOD: setup-only fake, no name; assertions target the behavior
config = MagicMock()
config.frontend_url = "https://example.com"
with patch("services.bot.events.handlers.get_config", return_value=config):
    await handlers.notify(game)
mock_send.assert_awaited_once_with(game.host.discord_id, ANY)
```

For a session factory used as `async with get_db_session() as db:`, use `session_cm = MagicMock()` with `session_cm.__aenter__.return_value = mock_db` and patch with `return_value=session_cm`.

Keep a getter assertion only when the getter call is the behavior under test, such as a startup routine that must create a client. In that case add `# assert-not-weak: <reason>`.

## Coverage Theater Checklist

Before committing a test, verify it does not fall into these patterns:

- [ ] Function body has at least one `assert`, `assert_called*`, or `pytest.raises`
- [ ] Mock call verifications use `assert_called_once_with(...)` not just `assert_called_once()`
- [ ] Every `patch(...) as name` has an `assert_*` call (or other real check), or the `as name` is removed
- [ ] If a mock returns a value, the test asserts something about how that value was used
- [ ] `assert_not_called()` is only used when a sibling test for the same mock _does_ call it
- [ ] The test name describes a specific behavior, not just "test it runs"
