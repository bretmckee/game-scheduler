# Copyright 2025-2026 Bret McKee
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


"""Signup method types for game sessions."""

from enum import StrEnum


class SignupMethod(StrEnum):
    """Game signup method controlling participant addition."""

    SELF_SIGNUP = "SELF_SIGNUP"
    HOST_SELECTED = "HOST_SELECTED"

    @property
    def display_name(self) -> str:
        """User-friendly display name."""
        display_map = {
            "SELF_SIGNUP": "Self Signup",
            "HOST_SELECTED": "Host Selected",
        }
        return display_map[self.value]

    @property
    def description(self) -> str:
        """Description for UI tooltip/helper text."""
        description_map = {
            "SELF_SIGNUP": "Players can join the game by clicking the Discord button",
            "HOST_SELECTED": "Only the host can add players (Discord button disabled)",
        }
        return description_map[self.value]
