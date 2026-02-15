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


set -e

SCRIPT_DIR=$(dirname "$0")

get_reference_file() {
    case "$1" in
        *.py) echo ".copyright.py" ;;
        *.ts|*.tsx) echo ".copyright.ts" ;;
        *.sh) echo ".copyright.sh" ;;
    esac
}

"$SCRIPT_DIR/generate-copyright-references.sh"

new_files=$(git diff --cached --name-only --diff-filter=A)
[ -z "$new_files" ] && exit 0

exit_code=0
for file in $new_files; do
    case "$file" in
        *.py|*.ts|*.tsx|*.sh)
            ref_file=$(get_reference_file "$file")
            [ -n "$ref_file" ] && python3 "$SCRIPT_DIR/check-copyright.py" "$ref_file" "$file" || exit_code=1
            ;;
    esac
done
exit $exit_code
