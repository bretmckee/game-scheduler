<!-- markdownlint-disable-file -->

# Task Research Notes: Backup and Restore

## Research Executed

### File Analysis

- [compose.yaml](../../../compose.yaml)
  - Three named volumes: `postgres_data`, `rabbitmq_data`, `redis_data`
  - `cloudflared` uses `profiles: [cloudflare]` — pattern for new opt-in `backup` service
  - Postgres image pinned: `postgres:18.1-alpine`
  - All services on `app-network`; no external ports on postgres

- [services/init/main.py](../../../services/init/main.py)
  - Orchestrates 5 phases: wait_postgres → create_database_users → run_migrations → verify_schema → initialize_rabbitmq
  - After completion enters `while True: time.sleep(SECONDS_PER_DAY)` sleep loop (healthcheck marker at `/tmp/init-complete`)
  - Returns exit code 0 on success, 1 on failure — suitable for `depends_on: condition: service_completed_successfully`

- [services/init/database_users.py](../../../services/init/database_users.py)
  - Creates 3 roles: `gamebot_admin` (SUPERUSER), `gamebot_app` (non-superuser, RLS enforced), `gamebot_bot` (BYPASSRLS)
  - All creates are idempotent: `IF NOT EXISTS` guards on every role
  - Reads from env vars: `POSTGRES_ADMIN_USER/PASSWORD`, `POSTGRES_APP_USER/PASSWORD`, `POSTGRES_BOT_USER/PASSWORD`
  - Grants: `CONNECT`, `USAGE`, `CRUD on all tables/sequences`, `ALTER DEFAULT PRIVILEGES` for both postgres and admin users

- [config.template/env.template](../../../config.template/env.template)
  - All 3 DB role env vars already present: `POSTGRES_ADMIN_USER/PASSWORD`, `POSTGRES_APP_USER/PASSWORD`, `POSTGRES_BOT_USER/PASSWORD`
  - `POSTGRES_USER=postgres` / `POSTGRES_PASSWORD` — bootstrap superuser, available for `pg_restore`
  - No backup-related env vars yet

- [shared/messaging/infrastructure.py](../../../shared/messaging/infrastructure.py)
  - `PRIMARY_QUEUE_TTL_MS = 3600000` (1 hour)
  - Dead-letter queues (DLQs) with no TTL, retried every 15 min by retry-daemon
  - Messages published with `DeliveryMode.PERSISTENT`

- [shared/messaging/deferred_publisher.py](../../../shared/messaging/deferred_publisher.py)
  - Queues RabbitMQ events in `session.info` until after DB transaction commits
  - On rollback, events are discarded — DB is always ahead of any RabbitMQ message

- [services/api/services/games.py](../../../services/api/services/games.py)
  - `delete_game()`: deletes DB row first (via deferred publisher), then publishes `GAME_CANCELLED`
  - DB deletion always precedes message publish — backup always captures consistent state

- [shared/models/notification_schedule.py](../../../shared/models/notification_schedule.py), [game_status_schedule.py](../../../shared/models/game_status_schedule.py), [participant_action_schedule.py](../../../shared/models/participant_action_schedule.py)
  - All have `sent`/`executed`/`processed` bool flags
  - Scheduler re-drives unprocessed rows after restore — no scheduled work is lost

### Code Search Results

- `profiles:` in compose.yaml
  - Only `cloudflared` service uses profiles — established pattern for opt-in services

- `alembic_version` table
  - Written by every Alembic migration; present in `pg_dump` output
  - On restore, `init` reads it and migrates forward from the backed-up revision to current HEAD

## Key Discoveries

### Stateful Services

| Service      | Volume          | Backup needed | Reason                                                               |
| ------------ | --------------- | ------------- | -------------------------------------------------------------------- |
| PostgreSQL   | `postgres_data` | **YES**       | Source of truth for all application state                            |
| RabbitMQ     | `rabbitmq_data` | No            | 1hr TTL primary queues; scheduler tables self-drive replay           |
| Redis/Valkey | `redis_data`    | No            | Pure cache with TTLs; all data derivable from Postgres + Discord API |

### Why RabbitMQ Does Not Need Backup

- DB scheduler tables (`sent`/`executed`/`processed` flags) self-drive replay of all scheduled work after restore
- In-flight messages at backup time either complete harmlessly or get re-driven from DB (acceptable duplicates per requirements)
- `DeferredEventPublisher` guarantees DB commit precedes any message publish — DB is always the authoritative source
- Worst-case lost message = stale Discord embed, not lost game data

### Why Redis Does Not Need Backup

- Stores only derived/cached data: display names, sessions, guild/channel configs, game details
- TTLs range from 1 min to 24 hr; all values can be recomputed from Postgres + Discord API
- Cold cache after restore causes brief latency spike only, no data loss

### Backup Format Decision

`pg_dump --format=custom` (not `--format=plain`):

- Binary format: smaller, faster restore via parallel workers (`pg_restore -j`)
- Logical dump: compatible across major Postgres versions (critical for upgrade use case)
- Carries full schema + data + `alembic_version` — exact snapshot restorable anywhere

### Full Restore vs Data-Only Restore

**Full restore** (`pg_restore`): recreates schema + data from the backup — exact point-in-time snapshot. Schema matches data guaranteed.

**Data-only restore** (`pg_restore --data-only`): loads rows into an existing schema. Rejected because: if a migration ran between backup time and restore time, schema won't match data and restore fails or silently corrupts.

**Decision: full restore only.**

### Role Creation Problem

`pg_dump` does not include roles — they are cluster-level objects. `pg_restore` will fail on ownership/permission assignments if roles don't exist. Options evaluated:

1. **Manual psql commands in restore script** — diverges from `database_users.py`; roles become duplicated
2. **Run `init` fully before restore** — also runs Alembic migrations, creating schema that `pg_restore` then conflicts with
3. **`INIT_ROLES_ONLY` flag in `init`** — roles created by the single authoritative source; init exits after step 2, skipping migrations/schema/rabbitmq

**Decision: Option 3 — add `INIT_ROLES_ONLY=true` env var to `services/init/main.py`.**

Sequence with flag:

- wait_for_postgres → create_database_users → check flag → `return 0` if set

### Alembic Migration on Restore

After full restore, `alembic_version` contains the revision current at backup time. When `docker compose up` runs `init` normally (without `INIT_ROLES_ONLY`), Alembic applies any migrations added since the backup. This is the standard forward-migration path — restore just sets the starting point.

Caveat: destructive migrations (DROP COLUMN, DROP TABLE) since the backup will execute and that data is gone. But this is a general migration concern, not specific to restore, and additive migrations are the norm.

## Recommended Approach

### Backup

- **Timing**: cron inside a long-running `backup` compose service, `0 */12 * * *` (every 12 hours)
- **Format**: `pg_dump --format=custom | gzip | aws s3 cp`
- **Destination**: S3-compatible (AWS S3, Cloudflare R2, Backblaze B2)
- **Retention**: 14 slots (7 days at 12-hour intervals), slot-based rotation (overwrite oldest)
- **User**: `POSTGRES_ADMIN_USER` (superuser) for complete schema + data dump
- **Profile**: `profiles: [backup]` — opt-in, matches `cloudflared` pattern

### Restore

Hybrid approach: `scripts/restore.sh` handles the human/destructive steps; `compose.restore.yaml` handles the Docker sequencing.

**`scripts/restore.sh`**:

1. List available S3 backups (using backup container image)
2. Prompt user to select one
3. Confirm before destroying volumes
4. `docker compose down`
5. `docker volume rm postgres_data redis_data`
6. `RESTORE_BACKUP_KEY=<selected> docker compose -f compose.yaml -f compose.restore.yaml up --exit-code-from restore`
7. `docker compose up -d` on success

**`compose.restore.yaml`**:

```yaml
services:
  init:
    environment:
      INIT_ROLES_ONLY: 'true'
  restore:
    image: # same backup image (postgres:18.1-alpine + aws-cli)
    depends_on:
      postgres:
        condition: service_healthy
      init:
        condition: service_completed_successfully
    environment:
      RESTORE_BACKUP_KEY: ${RESTORE_BACKUP_KEY}
```

The `depends_on` chain handles sequencing: postgres healthy → init creates roles and exits 0 → restore downloads and runs `pg_restore`. After compose exits, `docker compose up -d` starts everything normally; `init` runs again, finds roles already exist (idempotent), and runs Alembic to migrate forward.

## Implementation Guidance

- **Objectives**:
  - Automatic 12-hour Postgres backups to S3-compatible storage
  - Simple, script-driven restore that is hard to get wrong
  - Support major-version Postgres upgrades via logical dump/restore

- **Key Tasks**:
  - Add `INIT_ROLES_ONLY` flag to `services/init/main.py`
  - Create `docker/backup.Dockerfile` (postgres:18.1-alpine + aws-cli)
  - Create `docker/backup-entrypoint.sh` (write cron env file, install cron job, exec crond)
  - Create `docker/backup-script.sh` (pg_dump | gzip | aws s3 cp, 14-slot rotation)
  - Add `backup` service to `compose.yaml` with `profiles: [backup]`
  - Create `compose.restore.yaml` with `init` override and `restore` service
  - Create `scripts/restore.sh`
  - Add backup env vars block to `config.template/env.template`

- **New Env Vars**:
  - `BACKUP_S3_BUCKET`
  - `BACKUP_S3_ACCESS_KEY_ID`
  - `BACKUP_S3_SECRET_ACCESS_KEY`
  - `BACKUP_S3_REGION`
  - `BACKUP_S3_ENDPOINT` (optional, for R2/B2 compatible endpoints)
  - `BACKUP_RETENTION_COUNT=14`
  - `BACKUP_SCHEDULE=0 */12 * * *`

- **Dependencies**:
  - `INIT_ROLES_ONLY` flag must be implemented before `compose.restore.yaml` can be written
  - `backup.Dockerfile` must exist before `compose.yaml` backup service and `compose.restore.yaml` restore service

- **Success Criteria**:
  - `docker compose --profile backup up -d` starts automated backup without affecting other services
  - `scripts/restore.sh` completes a full restore with no manual steps beyond selection and confirmation
  - After restore, all services start and Alembic migrates forward from backup revision
  - Restore script works for Postgres major version upgrades (e.g., 17 → 18)
  - No backup-specific logic duplicated between backup script and restore script

## Post-Restore Orphaned Embed Cleanup

### The Problem

After a restore, the database is rolled back to a point-in-time snapshot. Any game created **after** the backup timestamp no longer exists in the DB. But the Discord embed posted for that game still exists in the announcement channel — the restore has no way to reach Discord. On bot startup these are orphaned embeds: interactive messages with Join/Leave buttons whose game IDs are unknown to the system.

Without cleanup:

- Users can click Join/Leave on the embed — the API returns 404, interaction fails silently or with an error
- The embed sits in the channel indefinitely, confusing players and admins

### `backup_metadata` Table

A new `backup_metadata` table records when each backup was taken. The backup script inserts a row using the existing `POSTGRES_ADMIN_USER` connection (already required for `pg_dump`) immediately before dumping, so the timestamp is included in the dump automatically.

```sql
CREATE TABLE backup_metadata (
    id SERIAL PRIMARY KEY,
    backed_up_at TIMESTAMPTZ NOT NULL
);
```

The backup script inserts one row per run:

```bash
psql "$ADMIN_DATABASE_URL" -c "INSERT INTO backup_metadata (backed_up_at) VALUES (now());"
pg_dump ...
```

No new credentials are needed — the admin user already has full access.

### Solution: Startup Sweep on `on_ready` / `on_resumed`

When the bot connects, query `backup_metadata` for the most recent `backed_up_at` timestamp. If present, use it as the `channel.history()` cutoff (minus a small buffer for in-flight games). If absent (fresh install with no backups), skip the sweep entirely.

**Algorithm**:

1. Query `SELECT backed_up_at FROM backup_metadata ORDER BY backed_up_at DESC LIMIT 1`
2. If no row → skip sweep (fresh install)
3. Set `cutoff = backed_up_at - timedelta(minutes=5)` (buffer for games being created at backup time)
4. Query all `channel_configurations` that have a Discord `channel_id`
5. For each channel, call `channel.history(after=cutoff, limit=None)`
6. For each message where `message.author.id == self.user.id`:
   - Find a button with `custom_id` matching `join_game_{uuid}` or `leave_game_{uuid}`
   - Extract the UUID
   - Query DB: does a `GameSession` with this `id` exist?
   - If not → `await message.delete()`

**Filtering approach**: `message.author.id == self.user.id`

This was explicitly discussed and confirmed as the correct filter. The Discord docs confirm that without `MESSAGE_CONTENT` intent, `components` are empty for other users' messages (so `if message.components:` would also work), but `author.id` comparison is the same cost, explicit, and requires no intent assumptions.

**Relevant code**:

- `services/bot/bot.py` line 177 (`on_ready`), line 352 (`on_resumed`) — insertion points
- `services/bot/views/game_view.py` line 81 — `custom_id=f"join_game_{game_id}"` format
- `services/bot/handlers/button_handler.py` line 67 — `custom_id.replace("join_game_", "")` — same extraction pattern
- `shared/models/channel.py` line 48 — `channel_id` snowflake on `ChannelConfiguration`
- `shared/models/game.py` line 65 — `channel_id` FK to `channel_configurations`; line 74 — `message_id` snowflake

**Key Tasks** (additions to Implementation Guidance above):

- Add Alembic migration for `backup_metadata` table
- Add `BackupMetadata` SQLAlchemy model in `shared/models/`
- Insert row into `backup_metadata` in `backup-script.sh` before `pg_dump`
- Add `_sweep_orphaned_embeds()` coroutine in `services/bot/bot.py`; call from `on_ready` and `on_resumed`
- Query `backup_metadata` for cutoff; skip sweep if no rows
- Use `channel.history(after=cutoff)` with author ID filter
- Extract UUID from `join_game_` prefix and DB-lookup; delete on miss

**Success Criteria** (additions):

- After a restore, bot startup deletes all embeds whose game UUIDs are absent from the DB
- Sweep window is bounded by the actual backup timestamp, not an arbitrary fixed window
- Fresh installs (no `backup_metadata` rows) skip the sweep entirely
- Live game embeds (game exists in DB) are not touched
- Sweep runs without Discord rate-limit errors
