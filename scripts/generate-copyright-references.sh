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

for ext in py ts sh; do
    ref_file=".copyright.$ext"
    case "$ext" in
        py|sh) symbol="#" ;;
        ts) symbol="//" ;;
    esac

    echo "" > "$ref_file"
    if autocopyright -s "$symbol" -d "." -g ".copyright.$ext" -l "./templates/mit-template.jinja2" >/dev/null 2>&1; then
        echo "ERROR: autocopyright did not update $ref_file (expected non-zero exit)" >&2
        exit 1
    fi

    if [ ! -s "$ref_file" ]; then
        echo "ERROR: Failed to generate $ref_file or file is empty" >&2
        exit 1
    fi
done
