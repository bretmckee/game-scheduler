<!-- markdownlint-disable-file -->

# Task Research: Game Model Refactor (Remove min_players, Add where field)

## Overview

This research documents the changes needed to:

1. Remove the `min_players` field from the game data model (no longer useful)
2. Add a `where` field to store game location information

## Current Game Model Structure

### Database Model

**File**: `shared/models/game.py` (Lines 29-68)

Current GameSession model includes:

- `min_players: Mapped[int]` - Field to be removed
- No location/where field - Need to add

```python
class GameSession(Base):
    """Game session with scheduling and participant management."""
    __tablename__ = "game_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    signup_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column()
    min_players: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # TO REMOVE
    max_players: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # ... other fields
```

### API Schemas

**File**: `shared/schemas/game.py`

Current schema includes min_players in three places:

1. **GameCreateRequest** (Line 24): `min_players: int = Field(1, description="Minimum players required (default: 1)", ge=1)`
2. **GameUpdateRequest** (Line 66): `min_players: int | None = Field(None, ge=1)`
3. **GameResponse** (Line 116): `min_players: int = Field(1, description="Minimum players required")`

No `where` field exists in any schema.

### Frontend Types

**File**: `frontend/src/types/index.ts` (Lines 33-58)

```typescript
export interface GameSession {
  id: string;
  title: string;
  description: string;
  signup_instructions: string | null;
  scheduled_at: string;
  min_players: number | null; // TO REMOVE
  max_players: number | null;
  // ... other fields
  // Missing: where field
}
```

## Impact Analysis

### Files Affected by min_players Removal

**Database & Models:**

1. `shared/models/game.py` - Remove field from GameSession model
2. `alembic/versions/004_add_min_players_field.py` - Existing migration (reference only)
3. New migration needed: `alembic/versions/XXX_remove_min_players_add_where.py`

**API Layer:** 4. `shared/schemas/game.py` - Remove from GameCreateRequest, GameUpdateRequest, GameResponse 5. `services/api/routes/games.py` - Remove validation logic (Lines 64-68) 6. `services/api/services/games.py` - Remove validation in create_game() (Lines 129-133) and update_game() (Lines 483-493)

**Frontend:** 7. `frontend/src/types/index.ts` - Remove min_players from GameSession interface 8. `frontend/src/pages/CreateGame.tsx` - Remove min_players input field 9. `frontend/src/pages/EditGame.tsx` - Remove min_players input field 10. `frontend/src/components/GameCard.tsx` - Update participant count display (currently shows "X/min-max") 11. `frontend/src/components/ParticipantList.tsx` - Update participant count display

**Tests:** 12. `tests/services/api/routes/test_games_timezone.py` - Remove min_players from test data 13. `tests/services/api/services/test_games_promotion.py` - Remove min_players from test data 14. `tests/services/api/services/test_games_edit_participants.py` - Remove min_players from test data 15. `tests/services/api/routes/test_games_participant_count.py` - Remove min_players from test data 16. Frontend test files - Update mock GameSession objects

### Files Affected by Adding where Field

**Database & Models:**

1. `shared/models/game.py` - Add `where` field as optional Text field
2. New migration: `alembic/versions/XXX_remove_min_players_add_where.py` - Add where column

**API Layer:** 3. `shared/schemas/game.py` - Add where to GameCreateRequest, GameUpdateRequest, GameResponse 4. `services/api/routes/games.py` - Add where to response building (Line 360) 5. `services/api/services/games.py` - Handle where in create_game() and update_game()

**Discord Bot:** 6. `services/bot/formatters/game_message.py` - Add where field display in embed (after "When" field, Line 76-81) 7. `services/bot/events/handlers.py` - Pass where field to format_game_announcement() (Line 547-577)

**Frontend:** 8. `frontend/src/types/index.ts` - Add where to GameSession interface 9. `frontend/src/pages/CreateGame.tsx` - Add where input field 10. `frontend/src/pages/EditGame.tsx` - Add where input field 11. `frontend/src/pages/GameDetails.tsx` - Display where field below "When:" (Line 209) 12. `frontend/src/components/GameCard.tsx` - Display where field in game cards (after "When:", Line 81)

**Tests:** 13. All test files with GameSession creation - Add where field to test data

## Display Positioning Requirements

### Discord Messages

Current Discord embed structure (from `services/bot/formatters/game_message.py`):

```python
embed.add_field(name="When", value=..., inline=False)  # Line 76-80
embed.add_field(name="Players", value=..., inline=True)  # Line 82
embed.add_field(name="Host", value=..., inline=True)  # Line 84
# ... other fields
```

**Required Change**: Add where field immediately after "When" field:

```python
embed.add_field(name="When", value=..., inline=False)
if where:
    embed.add_field(name="Where", value=where, inline=False)
embed.add_field(name="Players", value=..., inline=True)
```

### Web Pages

Current structure in `frontend/src/pages/GameDetails.tsx`:

```tsx
<Typography variant="body1" paragraph>
  <strong>When:</strong> {formatDateTime(game.scheduled_at)}
</Typography>
// Next: Host information
```

**Required Change**: Add where field immediately after "When":

```tsx
<Typography variant="body1" paragraph>
  <strong>When:</strong> {formatDateTime(game.scheduled_at)}
</Typography>;
{
  game.where && (
    <Typography variant="body1" paragraph>
      <strong>Where:</strong> {game.where}
    </Typography>
  );
}
```

Similar pattern needed in `GameCard.tsx`.

## Database Migration Strategy

**Safe Incremental Approach:**

The implementation uses a phased approach to ensure the system remains functional at every step:

### Phase 1: Add where field (Phases 1-4 of plan)

1. Add `where` column to database as nullable TEXT (safe - doesn't break anything)
2. Update model to include where field
3. Add where to API schemas and service layer
4. Add where to Discord bot formatters
5. Add where to frontend forms and displays

After Phase 1 completes, the system fully supports the where field while min_players still works.

### Phase 2: Remove min_players (Phases 5-7 of plan)

1. Remove min_players from API schemas (frontend still has it, but API ignores it)
2. Remove min_players validation from routes and services
3. Remove min_players from frontend (forms, displays, types)
4. Remove min_players from SQLAlchemy model (database column still exists - safe)
5. Drop min_players column from database (last step, all code already updated)

This approach ensures:

- System never breaks during implementation
- Each phase can be tested independently
- Changes can be rolled back at any point
- Database schema changes happen when all code is ready

### Migration Files

Two separate migration files:

**Migration 014: Add where field**

```python
def upgrade() -> None:
    """Add where field to game_sessions table."""
    op.add_column(
        "game_sessions",
        sa.Column("where", sa.Text(), nullable=True),
    )

def downgrade() -> None:
    """Remove where field from game_sessions table."""
    op.drop_column("game_sessions", "where")
```

**Migration 015: Remove min_players field** (run after all code updated)

```python
def upgrade() -> None:
    """Remove min_players field from game_sessions table."""
    op.drop_column("game_sessions", "min_players")

def downgrade() -> None:
    """Restore min_players field to game_sessions table."""
    op.add_column(
        "game_sessions",
        sa.Column("min_players", sa.Integer(), nullable=False, server_default="1"),
    )
```

## Field Specifications

### where Field

- **Type**: Text (nullable)
- **Database**: `Text`, `nullable=True`
- **SQLAlchemy**: `Mapped[str | None]`
- **Pydantic**: `str | None = Field(None, description="Game location (optional)", max_length=500)`
- **TypeScript**: `where: string | null`
- **Display**: Below "When:" field in both Discord and web interfaces
- **Optional**: Yes, not required for game creation
- **Max Length**: 500 characters (reasonable for location descriptions)

## Participant Count Display Changes

Currently displays as: "X/min-max" (e.g., "3/2-8")

After removal of min_players: "X/max" (e.g., "3/8")

Files affected:

- `frontend/src/components/GameCard.tsx`
- `frontend/src/components/ParticipantList.tsx`

## Form Field Ordering

### Create/Edit Game Forms

Current order (simplified):

1. Title
2. Scheduled Time (When)
3. Description
4. Min Players (TO REMOVE)
5. Max Players
6. Other fields...

Desired order:

1. Title
2. Scheduled Time (When)
3. Where (NEW)
4. Description
5. Max Players
6. Other fields...

## Success Criteria

1. **Database**:

   - `min_players` column removed from `game_sessions` table
   - `where` column added to `game_sessions` table as nullable text
   - Migration reversible

2. **API**:

   - All schemas updated (remove min_players, add where)
   - All validation logic for min_players removed
   - where field accepted in create/update endpoints
   - where field returned in all game responses

3. **Discord Bot**:

   - where field displayed in Discord embeds below "When" field
   - Field only shown if populated

4. **Frontend**:

   - where input field in create/edit forms (positioned below scheduled time)
   - where displayed in GameDetails page below "When:"
   - where displayed in GameCard components
   - min_players input removed from all forms
   - Participant count displays as "X/max" format

5. **Tests**:
   - All tests updated to remove min_players
   - All tests updated with where field where appropriate
   - All tests pass

## References

- Existing min_players implementation: Phase 7 of main plan
- Migration pattern: `alembic/versions/004_add_min_players_field.py`
- Discord embed structure: `services/bot/formatters/game_message.py`
- Web display pattern: `frontend/src/pages/GameDetails.tsx` and `frontend/src/components/GameCard.tsx`
