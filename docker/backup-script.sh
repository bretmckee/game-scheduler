#!/bin/sh
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


# backup-script.sh
#
# Runs a single Postgres backup cycle:
#   1. Insert a backup_metadata row (timestamp is thus included in the dump)
#   2. pg_dump to custom format, gzip, write via backup_write (s3:// or file://)
#
# Destination key format: ${BACKUP_DEST}/slot-<N>.dump.gz  where N cycles 0..(RETENTION_COUNT-1)
set -ex

RETENTION_COUNT="${BACKUP_RETENTION_COUNT:-14}"
BACKUP_DEST="${BACKUP_DEST}"
REGION="${BACKUP_S3_REGION:-us-east-1}"

# Build the database URL when running directly (e.g. docker compose run backup
# /usr/local/bin/backup-script.sh) rather than via the cron entrypoint.
if [ -z "${BACKUP_DATABASE_URL}" ]; then
    BACKUP_DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST:-postgres}:${POSTGRES_PORT:-5432}/${POSTGRES_DB}"
fi

# Build aws s3 command, adding --endpoint-url only when BACKUP_S3_ENDPOINT is set
aws_s3() {
    if [ -n "${BACKUP_S3_ENDPOINT}" ]; then
        AWS_ACCESS_KEY_ID="${BACKUP_S3_ACCESS_KEY_ID}" \
        AWS_SECRET_ACCESS_KEY="${BACKUP_S3_SECRET_ACCESS_KEY}" \
        aws --region "${REGION}" --endpoint-url "${BACKUP_S3_ENDPOINT}" s3 "$@"
    else
        AWS_ACCESS_KEY_ID="${BACKUP_S3_ACCESS_KEY_ID}" \
        AWS_SECRET_ACCESS_KEY="${BACKUP_S3_SECRET_ACCESS_KEY}" \
        aws --region "${REGION}" s3 "$@"
    fi
}

# Determine which slot to write this run (slot cycles 0..RETENTION_COUNT-1)
SLOT_FILE=/var/lib/backup-slot
if [ -f "${SLOT_FILE}" ]; then
    LAST_SLOT=$(cat "${SLOT_FILE}")
    SLOT=$(( (LAST_SLOT + 1) % RETENTION_COUNT ))
else
    SLOT=0
fi

BACKUP_KEY="${BACKUP_DEST}/slot-${SLOT}.dump.gz"

backup_write() {
    case "$1" in
        s3://*)   aws_s3 cp - "$1" ;;
        file://*) cat > "${1#file://}" ;;
        *)        echo "Unknown backup destination scheme: $1" >&2; exit 1 ;;
    esac
}

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting backup to ${BACKUP_KEY}"

# Insert backup_metadata row before dumping so the timestamp is in the dump
psql "${BACKUP_DATABASE_URL}" -c "INSERT INTO backup_metadata (backed_up_at) VALUES (now());"

# Diagnostic: show row counts before dump to confirm data is visible
COUNT_SQL="SELECT 'game_sessions' AS tbl, count(*) FROM game_sessions UNION ALL SELECT 'game_participants', count(*) FROM game_participants UNION ALL SELECT 'guild_configurations', count(*) FROM guild_configurations;"
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] DEBUG: row counts before backup:"
psql "${BACKUP_DATABASE_URL}" -c "${COUNT_SQL}" 2>&1 || true

# Dump, compress, and upload in one pipeline to avoid writing a temp file
pg_dump \
    --format=custom \
    --no-password \
    "${BACKUP_DATABASE_URL}" \
  | gzip \
  | backup_write "${BACKUP_KEY}"

# Persist the slot so the next run advances to the next slot
echo "${SLOT}" > "${SLOT_FILE}"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Backup complete: ${BACKUP_KEY}"
