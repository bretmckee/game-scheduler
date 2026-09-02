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


"""Unit tests for scripts/mutmut_ledger.py gate comparison helpers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from mutmut_ledger import kill_regressions


def test_kill_regression_reports_lost_muts_within_reran_family() -> None:
    """A family re-run this scope that lost kills must still be reported."""
    base = {"bot.py": {"fam_a": [1, 2, 3], "fam_b": [9]}}
    live = {"bot.py": {"fam_a": [1, 2]}}  # fam_a rerun, lost mutant 3; fam_b not rerun
    lines = kill_regressions(base, live)
    assert any("bot.py" in line and "__mutmut_3" in line for line in lines)


def test_kill_regression_skips_families_not_in_live_scope() -> None:
    """Families absent from the run scope must stay excluded (per docstring)."""
    base = {"bot.py": {"fam_a": [1, 2], "fam_b": [7, 8, 9]}}
    live = {"bot.py": {"fam_a": [1, 2]}}  # only fam_a was rerun this time
    lines = kill_regressions(base, live)
    assert lines == []
