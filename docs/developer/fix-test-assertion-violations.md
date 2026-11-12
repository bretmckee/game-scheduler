# Fixing `check-test-assertions` Violations

The `check-test-assertions` pre-commit hook blocks test functions with weak or
missing assertions. This document explains each violation type and how to fix it.

**The goal is not to silence the checker. The goal is to write tests that
would catch a real bug.** Before reaching for an escape hatch, ask: if someone
changed the arguments passed to this mock, would this test fail? If not, the
test is not actually verifying the behavior it claims to cover.

For broader unit test quality guidance, see
[`.github/instructions/unit-tests.instructions.md`](../../.github/instructions/unit-tests.instructions.md).

## Violation Types

### `test_foo: no assertions`

The function contains no `assert` statement, no mock call-verification call, and
no `pytest.raises` context manager.

**Fix — verify the return value:**

```python
# before
def test_foo():
    result = compute(x)

# after
def test_foo():
    result = compute(x)
    assert result == expected_value
```

**Fix — verify a mock was called correctly:**

```python
# before
async def test_handle_event(handler, mock_deps):
    mock_deps.service.get.return_value = None
    await handler.handle(event)

# after
async def test_handle_event(handler, mock_deps):
    mock_deps.service.get.return_value = None
    await handler.handle(event)
    mock_deps.publisher.publish.assert_not_called()
```

**Fix — explicit "no exception" intent:**

Only use this when the test genuinely has no return value or mock call to verify:

```python
# after
async def test_handle_event_does_not_raise(handler, mock_deps):
    mock_deps.service.get.return_value = None
    await handler.handle(event)
    assert True  # verifies no exception raised
```

### `test_foo: named mock 'mock_x' has no assert_* call`

The function captures a patch with `as mock_x:` but never checks it. The
author named the mock, implying an intent to verify behavior that was never
completed.

The alias counts as checked if any `assert_*` method is called on it (or on an
attribute chain from it), if one of its call-tracking attributes such as
`call_count` or `call_args` is read, if it appears in the arguments of another
`assert_*` call (e.g. `send.assert_called_once_with(view=mock_view_cls.return_value)`),
or if it is an operand of `==`, `!=`, `is`, `is not`, `in`, or `not in` inside
an `assert`. A bare `assert mock_x` does not count — a mock is always truthy.

**First fix — the patch only supplies a fake: drop the name and pass `return_value=`:**

Most of these violations are setup-only patches, typically dependency getters
such as `get_db_session`, `get_config`, `get_api_config`, `get_redis_client`,
`get_role_service`, or `get_discord_client`. Build the fake before the patch,
pass it with `return_value=`, and assert on how the fake was used. Do **not**
add an empty `assert_called_once_with()` on the getter — it proves nothing,
and the checker reports it.

```python
# before — named only so its return value can be configured
def test_foo():
    with patch("module.get_config") as mock_get_config:
        mock_get_config.return_value.frontend_url = "https://example.com"
        result = build_link(game_id)
    assert result == "https://example.com/games/abc"

# after — the fake is built first; no name needed
def test_foo():
    config = MagicMock()
    config.frontend_url = "https://example.com"
    with patch("module.get_config", return_value=config):
        result = build_link(game_id)
    assert result == "https://example.com/games/abc"
```

For a session factory used as `async with get_db_session() as db:`:

```python
session_cm = MagicMock()
session_cm.__aenter__.return_value = mock_db
with patch("module.get_db_session", return_value=session_cm):
    await handler.handle(event)
mock_db.commit.assert_awaited_once()
```

The same applies to any patch that only suppresses a real call — remove the
alias:

```python
# after — alias removed; mock only exists to suppress the real call
def test_foo():
    with patch("module.fn"):
        result = do_thing()
    assert result == 42
```

**Second fix — the call is the behavior: verify it with its arguments:**

```python
def test_foo():
    with patch("module.fn") as mock_x:
        result = do_thing()
    assert result == 42
    mock_x.assert_called_once_with(expected_arg)
```

### `test_foo: \`assert_called_once()\` — prefer assert_called_once_with()`

### `test_foo: \`assert_called_once_with()\` — add arguments or add '# assert-not-weak: <reason>'`

Both violations mean the same thing: the mock's call count is verified but not
what arguments it received. A bug that passes the wrong argument will not be
caught.

**The standard fix is to add the expected arguments:**

```python
# before — call count only; wrong arguments would not be caught
mock_require.assert_called_once()

# after — verifies both the call and its arguments
mock_require.assert_called_once_with(mock_db, game.guild_id, "user123", not_found_detail="Game not found")
```

Use `unittest.mock.ANY` when one argument is an opaque internal object (e.g., a
redis client created inside the function under test) and the other arguments are
the ones that actually matter:

```python
from unittest.mock import ANY

# good: verifies user and guild are correct; redis client is internal
mock_check.assert_called_once_with("user123", guild_config.guild_id, ANY)
```

**The escape hatch — `# assert-not-weak: <reason>`:**

This marker suppresses the violation. It exists for the narrow case where the
function under test genuinely takes no arguments and no `ANY`-based assertion
would add signal. It is **not** a way to close a violation quickly.

Before using it, answer both questions:

1. Does the function under test actually take no arguments?
2. Is the call count itself meaningful to this test, or is this mock incidental?

If the answer to (2) is "incidental," the right fix is to remove the `as` alias
and pass any fake with `return_value=` (see the named-mock fix above), not to
add a marker. This covers dependency getters such as `get_config` and
`get_db_session`: they take no arguments, but asserting that they were called
proves nothing. If the answer to (1) is "it does take arguments
but they are complex," use `ANY` for the parts you cannot easily reference.

The marker **requires a reason** after the colon — `# assert-not-weak: <reason>`.
A reason is mandatory; a bare `# assert-not-weak` is not recognized and will not
suppress the violation.

The marker can appear **inline** on the assertion line or on the **preceding line**
as a standalone comment. The preceding-line form is useful when the inline form
would exceed the line length limit:

```python
# inline form — reason is bounded by line length
mock_message.delete.assert_called_once_with()  # assert-not-weak: delete() passes no args

# preceding-line form — reason has no line length constraint
# assert-not-weak: lifespan calling get_redis_client() is the behavior under test
mock_get_redis_client.assert_called_once_with()
```

```python
# wrong use: bare assert_called_once() is weaker — use assert_called_once_with() instead
mock_get_config.assert_called_once()  # assert-not-weak: ...  ← DO NOT DO THIS

# wrong use: the getter only supplies a fake — unname the patch instead
mock_get_config.assert_called_once_with()  # assert-not-weak: ...  ← DO NOT DO THIS

# wrong use: the function takes real arguments but this is easier than writing them out
mock_get_client.assert_called_once_with()  # assert-not-weak: ...  ← DO NOT DO THIS
```

**Auto-exempted methods:**

Action methods that genuinely take no arguments are automatically exempted —
no annotation needed. The exemption applies when the mocked method name (e.g.
`mock_db.flush.assert_called_once()`) or the last component of the patch target
is in the list configured in `pyproject.toml`:

```toml
[tool.check-test-assertions]
no-arg-methods = ["flush", "commit", "rollback", "close", "connect", ...]
```

If an action method in the codebase genuinely takes no arguments and its call
is meaningful (e.g., a Discord color property accessor like `Color.green()`),
add it to this list rather than annotating every call site. Do **not** add
dependency getters (`get_config`, `get_db_session`, ...) — an empty assertion
on a getter is hollow; unname the patch and pass `return_value=` instead.

Not checked: the empty awaited forms (`assert_awaited_once_with()`) and
`assert_called_with()`. The same standard applies to them anyway.

**The `# assert-not-weak` marker is counted and gated:**

Each `# assert-not-weak: <reason>` added in a commit is counted by the pre-commit
hook, except markers where Jedi can confirm the patched function takes no
arguments. The commit is blocked if the count exceeds `APPROVED_WEAK_ASSERTIONS`:

```bash
# permits exactly 2 assert-not-weak annotations in this commit
APPROVED_WEAK_ASSERTIONS=2 git commit -m "..."
```

This mirrors the `APPROVED_OVERRIDES` mechanism for lint suppressions. It means
mass-annotating violations is impossible without the user explicitly typing a
number they would need to justify. If you find yourself setting
`APPROVED_WEAK_ASSERTIONS` to a large number, that is a signal to stop and write
real assertions instead.

The only legitimate use is for calls where the function under test creates the
argument internally (e.g., `asyncio.create_task` receiving an opaque coroutine)
and even `ANY` would not add meaningful signal. That scenario is rare. If the
method takes real arguments that can be named in the test, use
`assert_called_once_with(...)` with those arguments.

Before setting `APPROVED_WEAK_ASSERTIONS`, follow the approval process in
`.github/instructions/quality-check-overrides.instructions.md` — explain why
the code cannot be written to pass the check, what alternatives were considered,
and get explicit user confirmation.

```python
# legitimate: coroutine is created internally; call count confirms the task was scheduled
mock_create_task.assert_called_once()  # assert-not-weak: coroutine is opaque internal detail

# wrong: Embed takes title, description, color — those should be verified
mock_embed_class.assert_called_once()  # assert-not-weak: ...  ← DO NOT DO THIS
```

## Choosing the Right Assertion

| Situation                            | Preferred assertion                                           |
| ------------------------------------ | ------------------------------------------------------------- |
| Return value exists                  | `assert result == expected`                                   |
| Side-effect only (void function)     | `mock.assert_called_once_with(args)`                          |
| Mock must not be called              | `mock.assert_not_called()`                                    |
| Exception expected                   | `pytest.raises(ExceptionType)`                                |
| No return value, no mock to verify   | `assert True  # verifies no exception raised`                 |
| Method is in `no-arg-methods` config | `mock.method.assert_called_once_with()` — auto-exempted       |
| Patch only supplies a fake (getter)  | `patch(..., return_value=fake)` — no name, no assertion       |
| Args truly opaque (rare, gated)      | `mock.assert_called_once_with()  # assert-not-weak: <reason>` |
