# Transaction Management

## Overview

This project uses FastAPI's dependency injection system to manage database transactions at the route handler level. Service layer functions **do not commit transactions** - they manipulate the database session and delegate transaction finalization to the route handler.

## Architecture Pattern

### Route-Level Transaction Boundaries

**Correct Pattern:**

```python
# Route handler (services/api/routes/games.py)
@router.post("/games")
async def create_game(
    game_data: GameCreateRequest,
    db: AsyncSession = Depends(get_db),  # Transaction boundary
) -> GameResponse:
    # All service calls within one transaction
    game = await game_service.create_game(db, game_data)
    # get_db() commits here on success, or rolls back on exception
    return game
```

**FastAPI Dependency (shared/database.py):**

```python
async def get_db() -> AsyncGenerator[AsyncSession]:
    """Provide database session with automatic transaction management."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()  # Commit at route boundary
        except Exception:
            await session.rollback()  # Rollback on any error
            raise
        finally:
            await session.close()
```

### Service Layer Pattern

**Service functions should:**
- Manipulate database session (add, update, delete objects)
- Use `flush()` when generated IDs are needed immediately
- **Never call `commit()`** - this breaks atomicity
- Raise exceptions on errors (triggers route-level rollback)
- Document transaction expectations in docstrings

**Example Service Function:**

```python
async def create_guild_config(
    db: AsyncSession,
    guild_discord_id: str,
    **settings: Any,
) -> GuildConfiguration:
    """
    Create new guild configuration.

    Does not commit. Caller must commit transaction.

    Args:
        db: Database session
        guild_discord_id: Discord guild snowflake ID
        **settings: Additional configuration settings

    Returns:
        Created guild configuration
    """
    guild_config = GuildConfiguration(guild_id=guild_discord_id, **settings)
    db.add(guild_config)
    await db.flush()  # Generate ID for immediate use
    return guild_config
```

## Flush vs Commit

### When to Use flush()

Use `flush()` when you need database-generated values (like primary keys) before the transaction completes:

```python
# Create parent object
guild_config = GuildConfiguration(guild_id=guild_discord_id)
db.add(guild_config)
await db.flush()  # Generates guild_config.id

# Use generated ID in child object
channel_config = ChannelConfiguration(
    guild_id=guild_config.id,  # Needs ID from flush
    channel_id=channel_discord_id,
)
db.add(channel_config)
await db.flush()  # Generate channel_config.id

# Create template referencing both IDs
template = GameTemplate(
    guild_id=guild_config.id,
    channel_id=channel_config.id,
    name="Default",
)
db.add(template)

# Route handler will commit all changes atomically
```

**Key Points:**
- `flush()` sends SQL to database but keeps transaction open
- Database generates IDs and returns them to the ORM
- Transaction remains active - can still rollback
- Multiple flushes in one transaction are fine
- Route handler commits or rolls back everything

### Never Use commit() in Services

**❌ WRONG - Breaks Atomicity:**

```python
async def create_guild_config(db: AsyncSession, guild_id: str) -> GuildConfiguration:
    guild_config = GuildConfiguration(guild_id=guild_id)
    db.add(guild_config)
    await db.commit()  # ❌ WRONG - Creates transaction boundary
    await db.refresh(guild_config)
    return guild_config

# Problem: If later code fails, guild is already committed
async def sync_user_guilds(db: AsyncSession, ...):
    guild = await create_guild_config(db, guild_id)  # Commits here
    # If this fails, guild is orphaned in database:
    await create_channel_config(db, guild.id, channel_id)
```

**✅ CORRECT - Maintains Atomicity:**

```python
async def create_guild_config(db: AsyncSession, guild_id: str) -> GuildConfiguration:
    guild_config = GuildConfiguration(guild_id=guild_id)
    db.add(guild_config)
    await db.flush()  # ✅ Generate ID, keep transaction open
    return guild_config

# All operations in one transaction
async def sync_user_guilds(db: AsyncSession, ...):
    guild = await create_guild_config(db, guild_id)
    await create_channel_config(db, guild.id, channel_id)
    # Route handler commits all or rolls back all
```

## Multi-Step Operations

Complex operations involving multiple service calls maintain atomicity through route-level transaction management:

### Guild Sync Example

```python
# Orchestrator (service layer)
async def sync_user_guilds(db: AsyncSession, ...) -> dict[str, int]:
    """
    Sync user's Discord guilds with database.

    Does not commit. Caller must commit transaction.
    """
    for guild_id in new_guild_ids:
        # Create guild
        guild = await create_guild_config(db, guild_id)

        # Create channels
        for channel in channels:
            await create_channel_config(db, guild.id, channel["id"])

        # Create default template
        await create_default_template(db, guild.id, first_channel_id)

    return {"new_guilds": len(new_guild_ids), "new_channels": channel_count}

# Route handler
@router.post("/sync")
async def sync_guilds(db: AsyncSession = Depends(get_db)):
    result = await guild_service.sync_user_guilds(db, ...)
    # get_db() commits here - all guilds, channels, templates atomic
    return result
```

**Atomicity Guarantee:**
- All guilds created OR none created
- Each guild has channels OR guild not created
- Each guild has template OR guild not created
- Failure at any step rolls back entire sync operation

### Game Creation Example

```python
# Service method
async def create_game(
    self,
    game_data: GameCreateRequest,
    host_user_id: str,
) -> GameSession:
    """
    Create game with participants and schedules.

    Does not commit. Caller must commit transaction.
    """
    # Build game session
    game = GameSession(...)
    self.db.add(game)
    await self.db.flush()  # Need game.id for participants

    # Create participants
    for participant_data in valid_participants:
        participant = GameParticipant(
            game_session_id=game.id,
            ...
        )
        self.db.add(participant)

    await self.db.flush()  # Need participant.id for schedules

    # Create notification schedules
    await schedule_service.populate_schedule(game, reminder_minutes)

    # Create status transition schedules
    await self._create_game_status_schedules(game, duration_minutes)

    return game

# Route handler commits entire operation
```

**Atomicity Guarantee:**
- Game, participants, and schedules all created OR none created
- No orphaned games without participants
- No incomplete schedule data

## Error Handling

### Service Layer

Services should raise descriptive exceptions that trigger route-level rollback:

```python
async def create_template(
    self,
    guild_id: str,
    channel_id: str,
    name: str,
) -> GameTemplate:
    """
    Create new template.

    Does not commit. Caller must commit transaction.

    Raises:
        ValueError: If guild or channel not found
    """
    # Validate guild exists
    result = await self.db.execute(
        select(GuildConfiguration).where(GuildConfiguration.id == guild_id)
    )
    guild = result.scalar_one_or_none()
    if guild is None:
        raise ValueError(f"Guild not found: {guild_id}")

    # Create template
    template = GameTemplate(guild_id=guild_id, channel_id=channel_id, name=name)
    self.db.add(template)
    await self.db.flush()

    return template
```

### Route Handler

FastAPI's `get_db()` dependency automatically handles rollback:

```python
@router.post("/templates")
async def create_template(
    template_data: TemplateCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> TemplateResponse:
    try:
        template = await template_service.create_template(
            db,
            template_data.guild_id,
            template_data.channel_id,
            template_data.name,
        )
        # get_db() commits on success
        return template
    except ValueError as e:
        # get_db() rolls back on exception
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception:
        # get_db() rolls back on exception
        raise
```

## Row-Level Security (RLS) Considerations

This project uses PostgreSQL Row-Level Security for multi-tenant isolation. RLS context is **transaction-scoped**:

```python
# Middleware sets RLS context
await db.execute(text("SET LOCAL app.current_guild_ids = '123,456'"))

# All queries in this transaction respect RLS
guild = await create_guild_config(db, '789')  # INSERT with RLS check
channel = await create_channel_config(db, guild.id, '999')  # INSERT with RLS check

# Transaction commits - RLS context active throughout
```

**Critical Point:** Premature commits break RLS context:

```python
# ❌ WRONG - RLS context lost
await db.execute(text("SET LOCAL app.current_guild_ids = '123,456'"))
guild = await create_guild_config(db, '789')
await db.commit()  # ❌ Transaction ends, RLS context lost

# New transaction has NO RLS context - refresh fails
await db.refresh(guild)  # ❌ SELECT blocked by RLS policy
```

**✅ CORRECT - RLS context maintained:**

```python
await db.execute(text("SET LOCAL app.current_guild_ids = '123,456'"))
guild = await create_guild_config(db, '789')
await db.flush()  # ✅ Transaction continues, RLS context active
await db.refresh(guild)  # ✅ SELECT succeeds with RLS context
# Route commits everything atomically
```

## Testing Transaction Behavior

### Unit Tests

Unit tests should verify services **do not commit**:

```python
async def test_create_guild_config():
    mock_db = AsyncMock(spec=AsyncSession)

    result = await create_guild_config(mock_db, "123456")

    # Verify flush called (for ID generation)
    mock_db.flush.assert_awaited_once()

    # Verify commit NOT called
    mock_db.commit.assert_not_awaited()
```

### Integration Tests

Integration tests should verify atomicity of multi-step operations:

```python
async def test_guild_sync_atomicity(admin_db: AsyncSession):
    # Setup: Patch channel creation to fail
    with patch("services.channel_service.create_channel_config") as mock_create:
        mock_create.side_effect = ValueError("Channel creation failed")

        # Execute: Try to sync guild
        with pytest.raises(ValueError):
            await sync_user_guilds(admin_db, access_token, user_id)

        await admin_db.rollback()  # Simulate route-level rollback

    # Verify: Guild was NOT created (rollback successful)
    result = await admin_db.execute(select(GuildConfiguration))
    guilds = result.scalars().all()
    assert len(guilds) == 0  # No orphaned guild
```

## Summary

**Key Principles:**

1. **Route handlers manage transactions** via `Depends(get_db)`
2. **Service functions manipulate sessions** but never commit
3. **Use `flush()` for ID generation** within a transaction
4. **Exceptions trigger rollback** automatically
5. **Multi-step operations are atomic** at route level
6. **RLS context requires single transaction** across operations

**Benefits:**

- ✅ Multi-step operations fully atomic
- ✅ No orphaned data from partial failures
- ✅ Clear separation of concerns
- ✅ Consistent error handling
- ✅ RLS context maintained correctly
- ✅ Easier to test and reason about
