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



cd "$(dirname "$0")/.."

COVERAGE_MODE=false
if [[ "${1:-}" == "--coverage" ]]; then
    COVERAGE_MODE=true
fi

PYTEST_ARGS=(
    tests/unit
    --timeout=30
    '--override-ini=addopts='
    -qq
)

if [[ "$COVERAGE_MODE" == "true" ]]; then
    cp .testmondata .testmondata.pre-run 2>/dev/null || true

    output=$(uv run pytest "${PYTEST_ARGS[@]}" \
        --testmon \
        -p no:randomly \
        --cov \
        --cov-report=xml \
        '--cov-report=' 2>&1)
    rc=$?

    if [[ $rc -ne 0 ]]; then
        echo "$output"
        mv .testmondata.pre-run .testmondata 2>/dev/null || rm -f .testmondata
        exit $rc
    fi

    rm -f .testmondata.pre-run
else
    output=$(uv run pytest "${PYTEST_ARGS[@]}" --testmon-nocollect 2>&1)
    rc=$?

    if [[ $rc -ne 0 ]]; then
        echo "$output"
        exit $rc
    fi
fi
