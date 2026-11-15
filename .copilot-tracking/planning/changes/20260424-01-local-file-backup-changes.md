# Changes: Local File Backup Support

## Overview

Replace the five-variable `BACKUP_S3_BUCKET` + S3-creds pattern with a single `BACKUP_DEST`
URL and add `file://` dispatch to backup and restore scripts.

## Added

- `backup_write` helper function in [docker/backup-script.sh](../../../docker/backup-script.sh) — dispatches on `s3://` vs `file://` scheme to write a backup
- `backup_read` helper function in [docker/restore-script.sh](../../../docker/restore-script.sh) — dispatches on `s3://` vs `file://` scheme to read a backup
- `backup_data` named volume in [compose.yaml](../../../compose.yaml) — provides persistent local storage for `file://` backups

## Modified

- [docker/backup-script.sh](../../../docker/backup-script.sh) — replaced `BUCKET`/`BACKUP_S3_BUCKET` with `BACKUP_DEST`; derived `BACKUP_KEY` from `BACKUP_DEST`; replaced `aws_s3 cp` tail with `backup_write`
- [docker/restore-script.sh](../../../docker/restore-script.sh) — replaced `BUCKET`/`BACKUP_S3_BUCKET` and `RESTORE_BACKUP_KEY` with `RESTORE_SRC`; added `backup_read`; updated header comments
- [compose.yaml](../../../compose.yaml) — replaced `BACKUP_S3_BUCKET` with `BACKUP_DEST`; made S3 cred vars optional with `:-` defaults; added `backup_data` volume mount and top-level volume declaration
- [compose.restore.yaml](../../../compose.restore.yaml) — replaced `BACKUP_S3_BUCKET` + `RESTORE_BACKUP_KEY` with `BACKUP_DEST` + `RESTORE_SRC`; made S3 cred vars optional
- [compose.e2e.yaml](../../../compose.e2e.yaml) — replaced `BACKUP_S3_BUCKET: test-backups` with `BACKUP_DEST: s3://test-backups`
- [config.template/env.template](../../../config.template/env.template) — replaced Backup Configuration section: `BACKUP_S3_BUCKET` → `BACKUP_DEST` with scheme examples; S3 creds annotated as conditional
- [config/env.dev](../../../config/env.dev) — updated Backup Configuration section to match template
- [config/env.prod](../../../config/env.prod) — updated Backup Configuration section to match template
- [config/env.staging](../../../config/env.staging) — updated Backup Configuration section to match template
- [config/env.e2e](../../../config/env.e2e) — replaced `BACKUP_S3_BUCKET=test-backups` with `BACKUP_DEST=s3://test-backups`
- [config/env.int](../../../config/env.int) — updated commented-out Backup Configuration section to use `BACKUP_DEST` (outside plan: the plan asked to verify; the old `BACKUP_S3_BUCKET` comment was updated to `BACKUP_DEST` to stay consistent)
- [scripts/restore.sh](../../../scripts/restore.sh) — replaced `BACKUP_S3_BUCKET`-based listing and `RESTORE_BACKUP_KEY` pass-through with `BACKUP_DEST`-based listing and `RESTORE_SRC` (outside plan: scripts/restore.sh was not in the plan details but contained old variable names)
- [scripts/run-backup-tests.sh](../../../scripts/run-backup-tests.sh) — replaced `RESTORE_KEY`/`RESTORE_BACKUP_KEY` with `RESTORE_SRC` derived from `BACKUP_DEST` (outside plan: scripts/run-backup-tests.sh was not in the plan details but contained old variable names)

## Removed

- `BACKUP_S3_BUCKET` environment variable — replaced by `BACKUP_DEST` everywhere
- `RESTORE_BACKUP_KEY` environment variable — replaced by `RESTORE_SRC` everywhere
