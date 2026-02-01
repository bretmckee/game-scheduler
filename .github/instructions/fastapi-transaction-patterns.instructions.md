---
description: "FastAPI transaction management patterns and service layer conventions"
applyTo: "services/api/routes/*.py,services/api/services/*.py"
---

# FastAPI Transaction Management Patterns

## Core Principle

**Route handlers manage transactions. Service functions manipulate sessions.**

## Mandatory Rules

### Route Handlers MUST

1. **Use dependency injection for database sessions:**
   ```python
   from fastapi import Depends
   from sqlalchemy.ext.asyncio import AsyncSession
   from shared.database import get_db, get_db_with_user_guilds

   @router.post("/items")
   async def create_item(
       item_data: ItemCreate,
       db: AsyncSession = Depends(get_db),  # ✅ Transaction boundary
   ):
       item = await item_service.create(db, item_data)
       # get_db() commits automatically on success
       return item
   ```

2. **Use `get_db()` for standard operations**
3. **Use `get_db_with_user_guilds()` for operations requiring user guild context**
4. **Let dependency handle commit/rollback automatically**
5. **NEVER manually call `await db.commit()` in route handlers**
6. **NEVER manually call `await db.rollback()` in route handlers**

### Service Functions MUST

1. **Include transaction expectation in docstring:**
   ```python
   async def create_item(db: AsyncSession, data: dict) -> Item:
       """
       Create new item.

       Does not commit. Caller must commit transaction.

       Args:
           db: Database session
           data: Item data

       Returns:
           Created item
       """
       item = Item(**data)
       db.add(item)
       await db.flush()  # Only if need ID immediately
       return item
   ```

2. **NEVER call `await db.commit()`**
3. **Use `await db.flush()` only when generated IDs are needed immediately**
4. **Raise exceptions on errors (triggers automatic rollback)**
5. **Document flush usage if present**

### Service Classes MUST

**For class-based services (like `GameService`, `TemplateService`):**

```python
class ItemService:
    def __init__(self, db: AsyncSession) -> None:
        """Initialize service with database session."""
        self.db = db

    async def create(self, data: dict) -> Item:
        """
        Create new item.

        Does not commit. Caller must commit transaction.
        """
        item = Item(**data)
        self.db.add(item)
        await self.db.flush()  # If need ID
        return item

    async def update(self, item: Item, updates: dict) -> Item:
        """
        Update existing item.

        Does not commit. Caller must commit transaction.
        """
        for key, value in updates.items():
            setattr(item, key, value)
        return item
```

## Flush vs Commit

### ✅ Use flush() When

You need database-generated values before transaction completes:

```python
# Parent object needs ID for child relationship
parent = Parent(name="Parent")
db.add(parent)
await db.flush()  # Generate parent.id

child = Child(parent_id=parent.id, name="Child")
db.add(child)
# Route handler will commit both atomically
```

### ❌ NEVER Use commit() In Services

Breaks atomicity:

```python
# ❌ WRONG - Breaks transaction boundaries
async def create_parent(db: AsyncSession) -> Parent:
    parent = Parent(name="Parent")
    db.add(parent)
    await db.commit()  # ❌ Creates orphan if child creation fails
    return parent

async def create_parent_with_child(db: AsyncSession):
    parent = await create_parent(db)  # Commits here
    child = Child(parent_id=parent.id)  # If this fails, parent already committed
    db.add(child)
```

```python
# ✅ CORRECT - Maintains atomicity
async def create_parent(db: AsyncSession) -> Parent:
    parent = Parent(name="Parent")
    db.add(parent)
    await db.flush()  # ✅ Generate ID, keep transaction open
    return parent

async def create_parent_with_child(db: AsyncSession):
    parent = await create_parent(db)
    child = Child(parent_id=parent.id)
    db.add(child)
    # Route handler commits both or rolls back both
```

## Multi-Step Operations

Orchestrator functions must maintain transaction boundaries:

```python
async def sync_resources(db: AsyncSession, resource_ids: list[str]) -> dict:
    """
    Sync multiple resources in one transaction.

    Does not commit. Caller must commit transaction.
    """
    results = {"created": 0, "updated": 0}

    for resource_id in resource_ids:
        # Each helper uses flush(), not commit()
        resource = await create_or_update_resource(db, resource_id)

        # Create related records
        await create_related_records(db, resource.id)

        results["created" if resource.is_new else "updated"] += 1

    # Route handler commits all changes atomically
    return results
```

## Error Handling

Services raise exceptions, routes handle HTTP responses:

```python
# Service layer
async def delete_item(db: AsyncSession, item_id: str) -> None:
    """
    Delete item.

    Does not commit. Caller must commit transaction.

    Raises:
        ValueError: If item not found
    """
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    if item is None:
        raise ValueError(f"Item not found: {item_id}")

    await db.delete(item)

# Route handler
@router.delete("/items/{item_id}")
async def delete_item_endpoint(
    item_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        await item_service.delete(db, item_id)
        # get_db() commits on success
        return {"status": "deleted"}
    except ValueError as e:
        # get_db() rolls back automatically
        raise HTTPException(status_code=404, detail=str(e)) from e
```

## Testing Patterns

### Unit Tests

Verify services don't commit:

```python
async def test_create_item_no_commit():
    mock_db = AsyncMock(spec=AsyncSession)

    await create_item(mock_db, {"name": "Test"})

    # Verify flush called (if needed for ID generation)
    mock_db.flush.assert_awaited_once()

    # Verify commit NOT called
    mock_db.commit.assert_not_awaited()
```

### Integration Tests

Verify atomicity:

```python
async def test_multi_step_atomicity(admin_db: AsyncSession):
    # Force failure in second step
    with patch("services.create_child") as mock:
        mock.side_effect = ValueError("Simulated failure")

        with pytest.raises(ValueError):
            await create_parent_with_child(admin_db, parent_data, child_data)

        await admin_db.rollback()

    # Verify parent was NOT created (rollback successful)
    result = await admin_db.execute(select(Parent))
    assert len(result.scalars().all()) == 0
```

## Common Violations to Avoid

### ❌ Manual Commit in Route Handler

```python
# ❌ WRONG
@router.post("/items")
async def create_item(db: AsyncSession = Depends(get_db)):
    item = await item_service.create(db, data)
    await db.commit()  # ❌ Unnecessary - get_db() handles this
    return item
```

### ❌ Commit in Service Function

```python
# ❌ WRONG
async def create_item(db: AsyncSession, data: dict) -> Item:
    item = Item(**data)
    db.add(item)
    await db.commit()  # ❌ Breaks atomicity
    return item
```

### ❌ Multiple Commits in Orchestrator

```python
# ❌ WRONG
async def sync_resources(db: AsyncSession, ids: list[str]):
    for id in ids:
        resource = await create_resource(db, id)
        await db.commit()  # ❌ Breaks atomicity

        await create_related(db, resource.id)
        await db.commit()  # ❌ Partial changes committed
```

### ❌ Missing Transaction Docstring

```python
# ❌ WRONG - No transaction documentation
async def create_item(db: AsyncSession, data: dict) -> Item:
    """Create new item."""  # ❌ Missing transaction note
    item = Item(**data)
    db.add(item)
    return item
```

## Checklist for New Code

When writing new service functions:

- [ ] Docstring includes "Does not commit. Caller must commit transaction."
- [ ] No `await db.commit()` calls
- [ ] Only use `await db.flush()` if need generated IDs immediately
- [ ] Raise descriptive exceptions on errors
- [ ] Route handler uses `Depends(get_db)` or `Depends(get_db_with_user_guilds())`
- [ ] Unit tests verify no commit calls
- [ ] Integration tests verify multi-step atomicity

When modifying existing service functions:

- [ ] Check for and remove any `await db.commit()` calls
- [ ] Replace with `await db.flush()` only if IDs needed
- [ ] Add transaction docstring if missing
- [ ] Update tests to verify no commits
- [ ] Test rollback scenarios

## Summary

**The Golden Rules:**

1. Route handlers = Transaction boundaries
2. Service functions = Session manipulation
3. flush() = Get IDs mid-transaction
4. commit() = NEVER in services
5. Exceptions = Automatic rollback
6. Multi-step = Atomic at route level

**See Also:**

- [docs/developer/transaction-management.md](../../docs/developer/transaction-management.md) - Comprehensive documentation
- [shared/database.py](../../shared/database.py) - Dependency implementation
