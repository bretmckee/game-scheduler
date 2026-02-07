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


"""Unit tests for SSE bridge configuration and validation."""

import pytest

from services.api.services.sse_bridge import get_sse_bridge


def test_set_keepalive_interval_validation():
    """Test keepalive interval configuration with validation."""
    bridge = get_sse_bridge()

    # Valid value should succeed
    bridge.set_keepalive_interval(5)
    assert bridge.keepalive_interval_seconds == 5

    # Zero should raise ValueError
    with pytest.raises(ValueError, match="Keepalive interval must be positive"):
        bridge.set_keepalive_interval(0)

    # Negative should raise ValueError
    with pytest.raises(ValueError, match="Keepalive interval must be positive"):
        bridge.set_keepalive_interval(-1)
