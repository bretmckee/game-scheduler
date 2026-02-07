#!/usr/bin/env bash
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


# SPDX-FileCopyrightText: 2025 Bret McKee
# SPDX-License-Identifier: MIT

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
COVERAGE_DIR="$FRONTEND_DIR/coverage"

cd "$FRONTEND_DIR"

set +e
npm run test:coverage -- --run --test-timeout=10000
test_exit_code=$?
set -e

mkdir -p "$COVERAGE_DIR"

if [ -f "$COVERAGE_DIR/lcov.info" ]; then
  sed "s|^SF:src/|SF:frontend/src/|g" "$COVERAGE_DIR/lcov.info" > "$COVERAGE_DIR/lcov-fixed.info"
else
  touch "$COVERAGE_DIR/lcov-fixed.info"
fi

exit $test_exit_code
