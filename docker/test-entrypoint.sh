#!/bin/bash
set -e

echo "=== Starting Test Execution ==="
echo "Timestamp: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "Note: Database initialization handled by init container"

exec "$@"
