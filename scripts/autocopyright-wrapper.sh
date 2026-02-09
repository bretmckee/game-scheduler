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

# Process each file
EXIT_CODE=0
for FILE in "$@"; do
    # Get directory and filename
    DIR=$(dirname "$FILE")
    FILENAME=$(basename "$FILE")

    # Run autocopyright for this specific file using exact glob match
    if ! autocopyright -s "$COMMENT_SYMBOL" -d "$DIR" -g "${FILENAME}" -l "$LICENSE_PATH"; then
        EXIT_CODE=1
    fi
done

exit $EXIT_CODE
