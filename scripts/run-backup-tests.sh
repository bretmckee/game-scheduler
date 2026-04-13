#!/bin/bash
# Copyright 2026 Bret McKee
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


# Run backup/restore tests across four phases using Docker Compose.
#
# Phase 1 — bring up full stack; create gameA (pre-backup)
# Phase 2 — trigger one-shot backup; create gameB (post-backup)
# Phase 3 — restore from backup; bring services back up
# Phase 4 — assert gameA present, gameB absent, gameB embed deleted; cron test
#
# REQUIRED: config/env.e2e must exist with Discord and MinIO credentials
# (see docs/developer/TESTING.md for setup instructions).
#
# Environment variables:
#   SKIP_STARTUP=1   - Skip build/start (use existing stack).  Do NOT use for
#                      first runs or after service code changes.
#   SKIP_CLEANUP=1   - Leave containers running after tests for debugging.
#
# Iterative debugging:
#   First run:       SKIP_CLEANUP=1 ./scripts/run-backup-tests.sh
#   Re-run:          SKIP_STARTUP=1 SKIP_CLEANUP=1 ./scripts/run-backup-tests.sh
#   Final/clean run: SKIP_STARTUP=1 ./scripts/run-backup-tests.sh
#
# AGENT NOTE: This script takes MORE THAN 10 MINUTES to run.
#   - Always use a terminal timeout of at least 900000ms (15 minutes).
#   - Always capture output with tee BEFORE any filtering:
#       scripts/run-backup-tests.sh |& tee output-backup.txt
#   - NEVER pipe directly to grep/tail/head without first saving via tee.

set -e

ENV_FILE="config/env.e2e"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: $ENV_FILE not found"
  echo "Create $ENV_FILE with test Discord and backup credentials."
  echo "See docs/developer/TESTING.md for setup instructions."
  exit 1
fi

source "$ENV_FILE"

if [ -n "$COMPOSE_PROFILES" ]; then
  export COMPOSE_PROFILES
fi

if [ -z "$DISCORD_BOT_TOKEN" ]; then
  echo "ERROR: DISCORD_BOT_TOKEN is required in $ENV_FILE"
  exit 1
fi

# Use a named Docker volume for record files so they're accessible to any
# container user without host-path or UID permission issues.
RECORDS_VOLUME="game-scheduler-backup-records-$$"
docker volume create "${RECORDS_VOLUME}" > /dev/null
# Open the volume root so testuser (non-root) can create files in it.
docker run --rm -v "${RECORDS_VOLUME}:/game-records" busybox chmod 777 /game-records

cleanup() {
  docker volume rm "${RECORDS_VOLUME}" 2>/dev/null || true
  if [ -n "$SKIP_CLEANUP" ]; then
    echo "Skipping backup test environment cleanup (SKIP_CLEANUP is set)"
  else
    echo "Cleaning up backup test environment..."
    docker compose --progress quiet --env-file "$ENV_FILE" down -v
  fi
}
trap cleanup EXIT

# ---------------------------------------------------------------------------
# Phase 1: bring up full stack and create gameA before the backup
# ---------------------------------------------------------------------------
echo "==> Phase 1: starting full stack and creating gameA"

if [ -z "$SKIP_STARTUP" ]; then
  docker compose --progress quiet --env-file "$ENV_FILE" up -d --build system-ready
fi

docker compose --progress quiet --env-file "$ENV_FILE" run \
  --build --no-deps --rm \
  -e GAME_RECORD_FILE=/game-records/game_a.txt \
  -v "${RECORDS_VOLUME}:/game-records" \
  e2e-tests tests/backup/test_backup_create_game.py -v -m backup

echo "==> Phase 1 complete: gameA record saved to volume ${RECORDS_VOLUME}"

# ---------------------------------------------------------------------------
# Phase 2: trigger one-shot backup, then create gameB after the backup
# ---------------------------------------------------------------------------
echo "==> Phase 2: triggering one-shot backup"

# The backup container is already running (started as part of system-ready).
# Use exec so the script runs directly in that container with its environment.
docker compose --progress quiet --env-file "$ENV_FILE" \
  exec backup /usr/local/bin/backup-script.sh

echo "==> Phase 2: backup complete; creating gameB"

docker compose --progress quiet --env-file "$ENV_FILE" run \
  --build --no-deps --rm \
  -e GAME_RECORD_FILE=/game-records/game_b.txt \
  -v "${RECORDS_VOLUME}:/game-records" \
  e2e-tests tests/backup/test_backup_create_game_b.py -v -m backup

echo "==> Phase 2 complete: gameB record saved to volume ${RECORDS_VOLUME}"

# ---------------------------------------------------------------------------
# Phase 3: stop application services, restore from backup, bring back up
# ---------------------------------------------------------------------------
echo "==> Phase 3: stopping application services for restore"

# Determine the S3 key of the backup we just created (always slot 0 on a
# fresh stack run because SLOT_FILE starts absent)
RESTORE_KEY="backup/slot-0.dump.gz"

docker compose --progress quiet --env-file "$ENV_FILE" \
  stop api bot scheduler retry-daemon

echo "==> Phase 3: restoring from ${RESTORE_KEY}"

# Use 'run --rm' rather than 'up --exit-code-from' so that postgres keeps
# running after the restore container exits.  With tmpfs volumes a
# 'docker compose up' teardown would wipe the postgres data directory,
# discarding the just-restored data before Phase 4 can read it.
#
# Prepend COMPOSE_FILE so the restore overlay is appended to whatever files
# are already active (e.g. compose.e2e.yaml from env.e2e).  Explicitly
# passing -f flags overrides COMPOSE_FILE and causes compose to see a
# different postgres config, triggering a container recreate that wipes tmpfs.
RESTORE_BACKUP_KEY="${RESTORE_KEY}" \
  COMPOSE_FILE="${COMPOSE_FILE}:compose.restore.yaml" \
  docker compose --env-file "$ENV_FILE" \
  run --rm restore

echo "==> Phase 3: restore complete; bringing services back up"

# Bot on_ready fires orphaned-embed sweep when it starts here
docker compose --progress quiet --env-file "$ENV_FILE" up -d system-ready

# ---------------------------------------------------------------------------
# Phase 4: post-restore assertions and cron test
# ---------------------------------------------------------------------------
echo "==> Phase 4: running post-restore assertions"

docker compose --progress quiet --env-file "$ENV_FILE" run \
  --build --no-deps --rm \
  -e GAME_A_RECORD_FILE=/game-records/game_a.txt \
  -e GAME_B_RECORD_FILE=/game-records/game_b.txt \
  -v "${RECORDS_VOLUME}:/game-records:ro" \
  e2e-tests tests/backup/test_backup_post_restore.py -v -m backup

echo "==> All backup test phases passed!"
