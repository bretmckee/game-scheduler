<!-- markdownlint-disable-file -->

# Task Changes: Backup and Restore

## Overview

Implement automated 12-hour Postgres backups to S3-compatible storage and a script-driven restore flow, including post-restore orphaned Discord embed cleanup.

## Phase 1: INIT_ROLES_ONLY Flag — COMPLETE

### Added

- `tests/unit/services/init/test_main_roles_only.py` — Four unit tests covering: flag set → exits 0 after role creation, skips migrations/schema/rabbitmq; flag set → logs INIT_ROLES_ONLY message; flag absent → all five phases run; flag empty → all five phases run.

### Modified

- `services/init/main.py` — Added `import os`; added `INIT_ROLES_ONLY` check after `create_database_users()` that logs and returns 0 immediately when truthy, skipping migrations, schema verification, and RabbitMQ init.

---

## Phase 2: backup_metadata Model and Migration — COMPLETE

### Added

- `shared/models/backup_metadata.py` — BackupMetadata ORM model mapping to backup_metadata table with integer PK and TIMESTAMPTZ backed_up_at column.
- `alembic/versions/20260412_add_backup_metadata.py` — Migration creating the backup_metadata table; downgrade drops it.
- `tests/unit/shared/models/test_backup_metadata.py` — Five unit tests covering table name, pk, column nullability, instantiation, and **all** export.

### Modified

- `shared/models/__init__.py` — Added BackupMetadata import and export.

---

## Phase 3: Backup Infrastructure — COMPLETE

### Added

- `docker/backup.Dockerfile` — postgres:18.1-alpine base with aws-cli and dcron installed; copies and execs backup-entrypoint.sh.
- `docker/backup-entrypoint.sh` — Writes runtime env vars to /etc/backup-env (chmod 600), installs cron job sourcing that file, then execs crond -f.
- `docker/backup-script.sh` — Inserts backup_metadata row, then pg_dump | gzip | aws s3 cp using 14-slot rotation; BACKUP_S3_ENDPOINT optional.

---

## Phase 4: Compose Changes — COMPLETE

### Added

- `compose.restore.yaml` — Override compose file for restore; sets `INIT_ROLES_ONLY=true` on the `init` service and defines the `restore` service using the backup image with `restore-script.sh` entrypoint.
- `config.template/env.template` — Added `BACKUP_S3_BUCKET`, `BACKUP_S3_ACCESS_KEY_ID`, `BACKUP_S3_SECRET_ACCESS_KEY`, `BACKUP_S3_REGION`, `BACKUP_S3_ENDPOINT`, `BACKUP_RETENTION_COUNT`, and `BACKUP_SCHEDULE` env var entries.

### Modified

- `compose.yaml` — Added `backup` service under the `backup` profile.

---

## Phase 5: Restore Script — COMPLETE

### Added

- `docker/restore-script.sh` — Runs inside the backup container to download a gzipped custom-format dump from S3 and restore it with `pg_restore`.
- `scripts/restore.sh` — Interactive user-facing restore script: lists S3 backups using the backup container image, prompts for selection and `yes` confirmation, then runs the full destroy-and-restore sequence via `compose.restore.yaml`.

### Modified

- `docker/backup.Dockerfile` — Added `COPY` and `chmod +x` for `restore-script.sh` so it is available inside the backup image at `/usr/local/bin/restore-script.sh`.

---

## Phase 6: Orphaned Embed Sweep — NOT STARTED

### Added

### Modified

### Removed

---

<!-- Merged from the former .copilot-tracking/changes/ copy of this log -->

---

plan: '.copilot-tracking/planning/plans/20260408-01-backup-restore.plan.md'
---

# Change Record: Backup and Restore

## Summary

Implement automated 12-hour Postgres backups to S3-compatible storage and a script-driven restore flow, including post-restore orphaned Discord embed cleanup.

## Changes

### Phase 1: INIT_ROLES_ONLY Flag

#### Added

- `tests/unit/init/test_init_roles_only.py` — unit tests for INIT_ROLES_ONLY environment variable behavior in the init service

#### Modified

- `services/init/main.py` — added INIT_ROLES_ONLY environment variable check that exits after phase 2 (role creation) when set to a truthy value

### Phase 2: backup_metadata Model and Migration

#### Added

- `tests/unit/models/test_backup_metadata.py` — unit tests for BackupMetadata ORM model confirming table name and column types
- `shared/models/backup_metadata.py` — BackupMetadata SQLAlchemy model with id and backed_up_at columns
- `alembic/versions/20260408_add_backup_metadata.py` — Alembic migration creating the backup_metadata table

#### Modified

- `shared/models/__init__.py` — exported BackupMetadata from shared models package

### Phase 3: Backup Infrastructure

#### Added

- `docker/backup.Dockerfile` — multi-stage Dockerfile for the backup service using postgres:17-alpine and AWS CLI
- `docker/backup-script.sh` — backup script that inserts a backup_metadata row, runs pg_dump to S3, and retains the last N backups
- `docker/backup-entrypoint.sh` — entrypoint that runs the backup on a 12-hour cron schedule

### Phase 4: Compose Changes

#### Added

- `compose.restore.yaml` — Docker Compose override for the one-shot restore workflow

#### Modified

- `compose.yaml` — added backup service under the `backup` profile using a cron-based schedule
- `config.template/env.template` — added backup-related environment variables (S3 bucket, prefix, region, endpoint, access key, secret key, retain count)

### Phase 5: Restore Script

#### Added

- `scripts/restore.sh` — interactive restore script that lists available backups from S3, prompts for selection and confirmation, and runs the restore via Docker Compose

### Phase 6: Orphaned Embed Sweep

#### Added

- `tests/unit/bot/test_sweep_orphaned_embeds.py` — unit tests for \_sweep_orphaned_embeds covering: no backup_metadata rows (skip), rows present with missing game (delete), rows present with existing game (no delete)

#### Modified

- `services/bot/bot.py` — added \_sweep_orphaned_embeds coroutine that deletes Discord embeds for games absent from the DB after a restore, called from on_ready and on_resumed via \_trigger_sweep

### Phase 7: pytest backup Marker and E2E Test Infrastructure

#### Modified

- `pyproject.toml` — added `backup` pytest marker and excluded it from default addopts filter alongside `e2e` and `integration`
- `compose.e2e.yaml` — added `minio` (always-on S3-compatible storage) and `minio-init` (creates test bucket idempotently) services to the e2e stack
- `config/env.e2e` — backup env vars already present pointing at MinIO; no additional changes needed (Task 7.3 was pre-implemented)
