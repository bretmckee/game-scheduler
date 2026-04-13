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


# restore-script.sh
#
# Runs inside the backup container to download and restore a Postgres backup:
#   1. Download the gzipped custom-format dump from S3
#   2. Decompress and restore it with pg_restore
#
# Required environment variables (provided by compose.restore.yaml):
#   RESTORE_BACKUP_KEY       — S3 key of the backup to restore (e.g. backup/slot-0.dump.gz)
#   BACKUP_S3_BUCKET
#   BACKUP_S3_ACCESS_KEY_ID
#   BACKUP_S3_SECRET_ACCESS_KEY
#   BACKUP_S3_REGION
#   BACKUP_S3_ENDPOINT       — optional; set for non-AWS S3-compatible endpoints
#   POSTGRES_HOST
#   POSTGRES_USER
#   POSTGRES_PASSWORD
#   POSTGRES_DB
set -e

BUCKET="${BACKUP_S3_BUCKET}"
REGION="${BACKUP_S3_REGION:-us-east-1}"

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

if [ -z "${RESTORE_BACKUP_KEY}" ]; then
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Error: RESTORE_BACKUP_KEY is not set" >&2
    exit 1
fi

TMPFILE=$(mktemp /tmp/restore-XXXXXX)
trap 'rm -f "${TMPFILE}"' EXIT

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Downloading s3://${BUCKET}/${RESTORE_BACKUP_KEY}..."
aws_s3 cp "s3://${BUCKET}/${RESTORE_BACKUP_KEY}" - | gunzip > "${TMPFILE}"

DUMP_SIZE=$(wc -c < "${TMPFILE}")
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] DEBUG: dump file size: ${DUMP_SIZE} bytes"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] DEBUG: game_sessions data in dump:"
pg_restore --data-only --table=game_sessions -f - "${TMPFILE}" 2>&1 | grep -A 3 "^COPY"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Restoring to ${POSTGRES_HOST}/${POSTGRES_DB}..."
PGPASSWORD="${POSTGRES_PASSWORD}" pg_restore \
    --host="${POSTGRES_HOST}" \
    --username="${POSTGRES_USER}" \
    --dbname="${POSTGRES_DB}" \
    --clean \
    --no-owner \
    --no-privileges \
    --exit-on-error \
    --verbose \
    "${TMPFILE}" 2>&1

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Restore complete."

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] DEBUG: game_sessions rows after restore:"
PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    --host="${POSTGRES_HOST}" \
    --username="${POSTGRES_USER}" \
    --dbname="${POSTGRES_DB}" \
    -c "SELECT id, title FROM game_sessions ORDER BY created_at;"
