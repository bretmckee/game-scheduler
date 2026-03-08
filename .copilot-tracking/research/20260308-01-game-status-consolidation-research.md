<!-- markdownlint-disable-file -->

# Task Research Notes: GameStatus Enum Consolidation

## Research Executed

### File Analysis

- `shared/models/game.py`
  - Defines `GameStatus(StrEnum)` with values: SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED
  - Includes `display_name` property returning human-readable strings
  - Used by `GameSession` model for column `default` and `server_default`
  - Re-exported via `shared/models/__init__.py`

- `shared/utils/status_transitions.py`
  - Defines a **second, independent** `GameStatus(StrEnum)` with the same four values
  - No `display_name` property
  - Contains `is_valid_transition()` and `get_next_status()` which reference this local definition
  - Imported only internally within this file

- `shared/models/__init__.py`
  - Re-exports `GameStatus` from `shared.models.game` in `__all__`

### Code Search Results

- `from shared.models.game import.*GameStatus`
  - 7 files import from `shared.models.game`: bot formatter, 4 test files, e2e tests, scheduler tests
- `from shared.utils.status_transitions import.*GameStatus`
  - 0 external files — the duplicate in `status_transitions.py` is consumed only within that module
- `from shared.models import.*GameStatus`
  - No direct import of `GameStatus` via `shared.models` package (it's re-exported but not imported that way in any source file)

### Affected Files (full list)

All files that import `GameStatus` from `shared.models.game` — these require **no change** since `shared/models/game.py` will be kept as the public import path (it will just re-export from `shared.utils.status_transitions`):

| File                                      | Current import                              | Change needed                                   |
| ----------------------------------------- | ------------------------------------------- | ----------------------------------------------- |
| `shared/models/game.py`                   | defines locally                             | **Replace** definition with import from utils   |
| `shared/utils/status_transitions.py`      | defines locally                             | **Replace** local definition, use single source |
| `shared/models/__init__.py`               | `from .game import GameStatus`              | No change                                       |
| `services/bot/formatters/game_message.py` | `from shared.models.game import GameStatus` | No change                                       |
| All 6 test files                          | `from shared.models.game import GameStatus` | No change                                       |

## Key Discoveries

### Canonical Location Decision

`shared/utils/status_transitions.py` is the correct canonical home because:

1. It already owns the transition rules (`is_valid_transition`, `get_next_status`) that are tightly coupled to the enum values
2. It contains no model/ORM code — no circular import risk
3. `shared/models/game.py` can safely import from `shared/utils/` (utils has no model dependency)
4. The opposite direction (`status_transitions` importing from `models`) would create a circular dependency since models import from base, and utils should not depend on models

### The `display_name` Property

Currently only on the `models/game.py` version. Must be **moved** to the canonical definition in `status_transitions.py`. It must also be extended for `ARCHIVED`:

```python
@property
def display_name(self) -> str:
    display_map = {
        "SCHEDULED": "Scheduled",
        "IN_PROGRESS": "In Progress",
        "COMPLETED": "Completed",
        "CANCELLED": "Cancelled",
        "ARCHIVED": "Archived",
    }
    return display_map[self.value]
```

### ARCHIVED Status Addition

Add `ARCHIVED = "ARCHIVED"` to the enum at this stage so the consolidation and the new value land together. The `is_valid_transition` and `get_next_status` updates for ARCHIVED are documented in the archive research doc.

### `server_default` in SQLAlchemy Column

`GameSession.status` uses `server_default=text(f"'{GameStatus.SCHEDULED.value}'")`. Since `GameStatus.SCHEDULED.value` is just the string `"SCHEDULED"`, this is unaffected by moving the definition — the value is evaluated at class-definition time.

## Recommended Approach

**Single-source: define in `shared/utils/status_transitions.py`, import in `shared/models/game.py`.**

Steps:

1. Edit `shared/utils/status_transitions.py`:
   - Add `ARCHIVED = "ARCHIVED"` to `GameStatus`
   - Add `display_name` property (with ARCHIVED mapping)
   - Update `is_valid_transition` valid_transitions dict: `GameStatus.COMPLETED: [GameStatus.ARCHIVED]`
   - Update `get_next_status`: no change needed (auto-transition stops at COMPLETED; ARCHIVED is triggered separately by the scheduler after a delay)
2. Edit `shared/models/game.py`:
   - Remove the local `class GameStatus(StrEnum)` definition entirely
   - Add `from shared.utils.status_transitions import GameStatus` at the top imports
3. No changes needed to `shared/models/__init__.py` or any consumer file — the re-export chain is preserved

## Implementation Guidance

- **Objectives**: Eliminate the duplicate `GameStatus` definition; add `ARCHIVED` value; preserve all existing import paths
- **Key Tasks**:
  1. Extend `GameStatus` in `status_transitions.py` (add ARCHIVED, add display_name)
  2. Update `is_valid_transition` in `status_transitions.py`
  3. Remove duplicate from `game.py`, add import
- **Dependencies**: None — this is purely internal refactoring; no migration required (no DB schema change for the status column; `ARCHIVED` is a new valid string value)
- **Success Criteria**:
  - `grep -r "class GameStatus" .` returns exactly one result
  - All existing tests pass unchanged
  - `from shared.models.game import GameStatus` still works (via re-export)
  - `from shared.models import GameStatus` still works
  - `from shared.utils.status_transitions import GameStatus` works
