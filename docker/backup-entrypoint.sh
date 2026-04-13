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


# backup-entrypoint.sh
#
# Constructs a psql-compatible database URL from POSTGRES_* vars, writes the
# cron schedule to a crontab file, then execs supercronic in the foreground.
# supercronic inherits the full container environment so no env-file sourcing
# is needed.
set -ex

# Construct a psql/pg_dump-compatible URL from the individual POSTGRES_* vars
# supplied by compose.yaml.  The POSTGRES_USER (superuser) has full dump rights.
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
export BACKUP_DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST:-postgres}:${POSTGRES_PORT}/${POSTGRES_DB}"

if [ -n "${BACKUP_SCHEDULE:-}" ]; then
    SCHEDULE="${BACKUP_SCHEDULE}"
else
    # Default: midnight yesterday — a valid schedule that won't fire for ~364 days.
    # Avoids hardcoded impossible dates (e.g. Feb 31) that confuse some cron daemons.
    yesterday_epoch=$(( $(date -u +%s) - 86400 ))
    SCHEDULE="0 0 $(date -u -d @${yesterday_epoch} +%-d) $(date -u -d @${yesterday_epoch} +%-m) *"
fi
CRONTAB_FILE=/etc/backup-cron

printf '%s /usr/local/bin/backup-script.sh\n' "${SCHEDULE}" > "${CRONTAB_FILE}"

exec /usr/local/bin/supercronic -debug "${CRONTAB_FILE}"
