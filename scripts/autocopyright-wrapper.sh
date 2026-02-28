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


# Wrapper for autocopyright that accepts file arguments from pre-commit
# Calls autocopyright once per file with a regex matching that specific file

set -e

# Change to repository root (parent of scripts directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# Parse options until we hit the file list
COMMENT_SYMBOL=""
LICENSE_PATH=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -s)
            COMMENT_SYMBOL="$2"
            shift 2
            ;;
        -l)
            LICENSE_PATH="$2"
            shift 2
            ;;
        *)
            # Remaining args are files
            break
            ;;
    esac
done

# Exit successfully if no files provided
if [[ $# -eq 0 ]]; then
    exit 0
fi

# Exit successfully if no files provided
if [[ $# -eq 0 ]]; then
    exit 0
fi

# Extract unique top-level directories and file extensions from file paths
# E.g., services/api/routes/games.py -> services, *.py
#       shared/models/game.py -> shared, *.py
#       frontend/src/App.tsx -> frontend/src, *.tsx (to avoid node_modules)
declare -A TOP_DIRS
declare -A EXTENSIONS
for FILE in "$@"; do
    # Skip files in excluded directories
    if [[ "$FILE" =~ (node_modules|\.venv|venv|__pycache__|\.git|\.pytest_cache|\.mypy_cache|htmlcov|coverage|dist|build) ]]; then
        continue
    fi

    # Get the first two components for frontend files, otherwise just first
    if [[ "$FILE" == frontend/* ]]; then
        TOP_DIR=$(echo "$FILE" | cut -d'/' -f1-2)
    else
        TOP_DIR=$(echo "$FILE" | cut -d'/' -f1)
    fi
    TOP_DIRS["$TOP_DIR"]=1

    # Extract file extension
    EXT="${FILE##*.}"
    EXTENSIONS["*.$EXT"]=1
done

# Build -d arguments for each unique top-level directory
DIR_ARGS=()
for DIR in "${!TOP_DIRS[@]}"; do
    DIR_ARGS+=(-d "$DIR")
done

# Build -g arguments for each unique extension
GLOB_ARGS=()
for PATTERN in "${!EXTENSIONS[@]}"; do
    GLOB_ARGS+=(-g "$PATTERN")
done

# Call autocopyright once to scan all top-level directories with all patterns
autocopyright -s "$COMMENT_SYMBOL" "${DIR_ARGS[@]}" "${GLOB_ARGS[@]}" -l "$LICENSE_PATH"
