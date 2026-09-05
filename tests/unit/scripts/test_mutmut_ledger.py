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

import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from mutmut_ledger import (
    _file_entries,
    canonical_summary,
    kill_regressions,
    ratchet,
    resolve_base_ref,
)


def _git_result(returncode: int, stdout: str = "", stderr: str = "") -> SimpleNamespace:
    """Minimal stand-in for the CompletedProcess fields _run_git callers read."""
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


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


def test_canonical_summary_strips_generation_time_line_prefixes() -> None:
    """Hunk coordinates are drift-prone and must not be part of entry identity."""
    prefixed = "L68: 'self.db' => 'None'; removed ')'"
    assert canonical_summary(prefixed) == "'self.db' => 'None'; removed ')'"
    multi_segment = "L12: 'a=1' => 'b=2'; L40: 'x' => 'y'; removed 'z='"
    assert canonical_summary(multi_segment) == "'a=1' => 'b=2'; 'x' => 'y'; removed 'z='"
    assert canonical_summary("removed 'user_id=None,'") == "removed 'user_id=None,'"
    assert canonical_summary("(no textual change detected)") == "(no textual change detected)"


def test_ratchet_ignores_line_number_drift_between_baseline_and_live() -> None:
    """The same edit rendered with vs without L prefixes is identical debt."""
    base = {
        "services/api/services/games.py": {"fam_a": [["logic", "L68: 'a=1' => 'b=2'; removed ')'"]]}
    }
    live = {"services/api/services/games.py": {"fam_a": [["logic", "'a=1' => 'b=2'; removed ')'"]]}}
    fails, warns, stale = ratchet(base, live)
    assert fails == [] and warns == [] and stale == []


def test_ratchet_still_flags_genuinely_new_logic_survivors() -> None:
    """Canonicalization must not mask edits that are truly absent from baseline."""
    base = {"bot.py": {"fam_b": [["string", "'hi' => 'bye'"]]}}
    live = {
        "bot.py": {
            "fam_b": [
                ["logic", "x = 1 => x = 2"],
                ["string", "'hi' => 'bye'"],
            ]
        }
    }
    fails, warns, stale = ratchet(base, live)
    assert len(fails) == 1
    assert "bot.py" in fails[0] and "x = 1 => x = 2" in fails[0]
    assert warns == [] and stale == []


def test_resolve_base_prefers_push_upstream(monkeypatch) -> None:
    """With a configured upstream, its merge-base wins over main refs."""
    calls: list[tuple[str, ...]] = []

    def fake_run_git(*cmd: str) -> SimpleNamespace:
        calls.append(cmd)
        if cmd[:3] == ("rev-parse", "--abbrev-ref", "@{upstream}"):
            return _git_result(0, stdout="origin/develop\n")
        if cmd[:2] == ("merge-base", "HEAD") and cmd[2] == "origin/develop":
            return _git_result(0, stdout="abc1234567890123456789\n")
        return _git_result(128, stderr="not a git repository (fake)")

    monkeypatch.setattr("mutmut_ledger._run_git", fake_run_git)
    assert resolve_base_ref(None) == "abc1234567890123456789"
    assert [c for c in calls if c[0] == "merge-base"] == [("merge-base", "HEAD", "origin/develop")]


def test_resolve_base_falls_back_to_main_when_no_upstream(monkeypatch) -> None:
    """Without an upstream ref, resolution degrades to origin/main then main."""
    merge_attempts: list[str] = []

    def fake_run_git(*cmd: str) -> SimpleNamespace:
        if cmd[:3] == ("rev-parse", "--abbrev-ref", "@{upstream}"):
            return _git_result(128, stderr="no upstream configured")
        if cmd[:2] == ("merge-base", "HEAD"):
            merge_attempts.append(cmd[2])
            if cmd[2] == "origin/main":
                return _git_result(128, stderr="unknown ref origin/main")
            return _git_result(0, stdout="deadbeefcafe\n")
        raise AssertionError(f"unexpected git argv: {cmd}")

    monkeypatch.setattr("mutmut_ledger._run_git", fake_run_git)
    assert resolve_base_ref(None) == "deadbeefcafe"
    assert merge_attempts == ["origin/main", "main"]


def test_resolve_base_explicit_arg_short_circuits(monkeypatch) -> None:
    """An explicit --base must be used verbatim with no git queries at all."""

    def explode(*_cmd: str) -> SimpleNamespace:
        message = "_run_git must not be called for an explicit base"
        raise AssertionError(message)

    monkeypatch.setattr("mutmut_ledger._run_git", explode)
    assert resolve_base_ref("v1.2.3-rc1") == "v1.2.3-rc1"


def test_file_entries_dedup_is_per_function_not_file_wide(tmp_path, monkeypatch) -> None:
    """Two functions rendering identical edit text must both keep their debt rows.

    A file-wide dedup set lets whichever family is processed first silently
    suppress the later one's pairs in every stamped baseline (measured incident:
    games.py _add_new_mentions lost its removed-kwarg survivors to an earlier
    _create_participant_* family with byte-identical summaries). Within-function
    duplicates still collapse to a single row.
    """
    store_root = tmp_path / "mutants"
    source_relpath = "pkg/mod.py"
    (store_root / "pkg").mkdir(parents=True)
    (store_root / source_relpath).write_text(
        "def f():\n    user_id=None\n    return user_id\n\n\n"
        "def g():\n    user_id=None\n    return user_id\n",
        encoding="utf-8",
    )
    codes = {
        # two different functions, byte-identical surviving mutant edits
        "a.b.x_f__mutmut_1": 0,
        "a.b.x_g__mutmut_1": 0,
        # same function again with the identical edit: must collapse to one row
        "a.b.x_f__mutmut_2": 0,
    }
    (store_root / f"{source_relpath}.meta").write_text(
        json.dumps({"exit_code_by_key": codes}), encoding="utf-8"
    )

    classifier = ModuleType("fake_classifier")
    # A real minimal unified diff so summarize_edit renders it deterministically;
    # both families receive identical text so their pairs would collide under a
    # file-wide dedup but must be kept separate per family.
    hunk = "--- pkg/mod.py\n+++ pkg/mod.py\n@@ -1 +1 @@\n-user_id=None\n+user_id=1\n"
    classifier.compute_diff = lambda module, name, path: hunk
    classifier.is_string_only_mutation = lambda diff: False

    monkeypatch.setattr("mutmut_ledger.REPO_ROOT", tmp_path)
    entries, scanned, unchecked, _killed = _file_entries(source_relpath, {"*"}, classifier)

    assert scanned == 3 and unchecked == 0
    assert entries is not None
    assert set(entries) == {"a.b.x_f", "a.b.x_g"}, "both families must be present"
    assert len(entries["a.b.x_f"]) == 1, "within-function duplicate must still collapse"
    assert len(entries["a.b.x_g"]) == 1, "cross-function identical text must NOT be suppressed"
    row_f = entries["a.b.x_f"][0]
    row_g = entries["a.b.x_g"][0]
    assert row_f == row_g, "identical edits render identically (dedup collision candidate)"
    assert row_f[0] == "logic"
