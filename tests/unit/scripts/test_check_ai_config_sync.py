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


"""Unit tests for scripts/check_ai_config_sync.py."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

_SCRIPT_PATH = Path(__file__).parent.parent.parent.parent / "scripts" / "check_ai_config_sync.py"
_spec = importlib.util.spec_from_file_location("check_ai_config_sync", _SCRIPT_PATH)
_mod: ModuleType = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

sync = _mod


def _manifest_path(root: Path) -> Path:
    return root / ".claude" / "config-sync-manifest.json"


def _write(root: Path, rel_path: str, content: str = "content") -> Path:
    path = root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def test_find_source_paths_matches_watched_scope(tmp_path: Path):
    _write(tmp_path, ".github/copilot-instructions.md")
    _write(tmp_path, ".github/agents/task-planner.agent.md")
    _write(tmp_path, ".github/instructions/python.instructions.md")
    _write(tmp_path, ".github/prompts/commit.prompt.md")
    _write(tmp_path, ".copilot-tracking/planning/prompts/implement-foo.prompt.md")
    _write(tmp_path, ".copilot-tracking/research/foo-research.md")
    _write(tmp_path, "README.md")

    found = sync.find_source_paths(tmp_path)

    assert found == [
        ".copilot-tracking/planning/prompts/implement-foo.prompt.md",
        ".github/agents/task-planner.agent.md",
        ".github/copilot-instructions.md",
        ".github/instructions/python.instructions.md",
        ".github/prompts/commit.prompt.md",
    ]


def test_check_flags_new_source_and_exits_nonzero(tmp_path: Path):
    _write(tmp_path, ".github/instructions/python.instructions.md")

    exit_code = sync.check(tmp_path, _manifest_path(tmp_path))

    assert exit_code == 1


def test_check_is_clean_after_recording(tmp_path: Path):
    _write(tmp_path, ".github/instructions/python.instructions.md")
    manifest_path = _manifest_path(tmp_path)
    sync.record(tmp_path, manifest_path, ".github/instructions/python.instructions.md", None)

    exit_code = sync.check(tmp_path, manifest_path)

    assert exit_code == 0


def test_check_flags_changed_source(tmp_path: Path):
    source = _write(tmp_path, ".github/instructions/python.instructions.md", "v1")
    manifest_path = _manifest_path(tmp_path)
    sync.record(tmp_path, manifest_path, ".github/instructions/python.instructions.md", None)

    source.write_text("v2")
    exit_code = sync.check(tmp_path, manifest_path)

    assert exit_code == 1


def test_check_autofixes_clean_removal(tmp_path: Path):
    source = _write(tmp_path, ".github/agents/task-planner.agent.md")
    output = _write(tmp_path, ".claude/agents/task-planner.md")
    manifest_path = _manifest_path(tmp_path)
    sync.record(
        tmp_path,
        manifest_path,
        ".github/agents/task-planner.agent.md",
        ".claude/agents/task-planner.md",
    )

    source.unlink()
    exit_code = sync.check(tmp_path, manifest_path)

    assert exit_code == 0
    assert not output.exists()
    manifest = json.loads(manifest_path.read_text())
    assert ".github/agents/task-planner.agent.md" not in manifest["entries"]


def test_check_drops_entry_when_output_already_gone(tmp_path: Path):
    source = _write(tmp_path, ".github/agents/task-planner.agent.md")
    output_path = tmp_path / ".claude/agents/task-planner.md"
    output_path.parent.mkdir(parents=True)
    output_path.write_text("generated")
    manifest_path = _manifest_path(tmp_path)
    sync.record(
        tmp_path,
        manifest_path,
        ".github/agents/task-planner.agent.md",
        ".claude/agents/task-planner.md",
    )

    source.unlink()
    output_path.unlink()
    exit_code = sync.check(tmp_path, manifest_path)

    assert exit_code == 0
    manifest = json.loads(manifest_path.read_text())
    assert manifest["entries"] == {}


def test_check_blocks_dirty_removal(tmp_path: Path):
    source = _write(tmp_path, ".github/agents/task-planner.agent.md")
    output = _write(tmp_path, ".claude/agents/task-planner.md")
    manifest_path = _manifest_path(tmp_path)
    sync.record(
        tmp_path,
        manifest_path,
        ".github/agents/task-planner.agent.md",
        ".claude/agents/task-planner.md",
    )

    source.unlink()
    output.write_text("hand-edited content")
    exit_code = sync.check(tmp_path, manifest_path)

    assert exit_code == 1
    assert output.exists()
    manifest = json.loads(manifest_path.read_text())
    assert ".github/agents/task-planner.agent.md" in manifest["entries"]


def test_record_reference_only_entry_has_no_output(tmp_path: Path):
    _write(tmp_path, ".github/instructions/python.instructions.md")
    manifest_path = _manifest_path(tmp_path)

    sync.record(tmp_path, manifest_path, ".github/instructions/python.instructions.md", None)

    manifest = json.loads(manifest_path.read_text())
    entry = manifest["entries"][".github/instructions/python.instructions.md"]
    assert entry["output"] is None
    assert entry["output_hash"] is None


def test_record_missing_source_fails(tmp_path: Path):
    exit_code = sync.record(
        tmp_path,
        _manifest_path(tmp_path),
        ".github/instructions/missing.instructions.md",
        None,
    )

    assert exit_code == 1


def test_record_missing_output_fails(tmp_path: Path):
    _write(tmp_path, ".github/agents/task-planner.agent.md")

    exit_code = sync.record(
        tmp_path,
        _manifest_path(tmp_path),
        ".github/agents/task-planner.agent.md",
        ".claude/agents/task-planner.md",
    )

    assert exit_code == 1


def test_forget_removes_tracked_entry(tmp_path: Path):
    _write(tmp_path, ".github/instructions/python.instructions.md")
    manifest_path = _manifest_path(tmp_path)
    sync.record(tmp_path, manifest_path, ".github/instructions/python.instructions.md", None)

    exit_code = sync.forget(manifest_path, ".github/instructions/python.instructions.md")

    assert exit_code == 0
    manifest = json.loads(manifest_path.read_text())
    assert manifest["entries"] == {}


def test_forget_untracked_source_is_a_noop(tmp_path: Path):
    exit_code = sync.forget(_manifest_path(tmp_path), ".github/instructions/never-tracked.md")

    assert exit_code == 0


def test_main_check_returns_nonzero_exit_via_cli(tmp_path: Path, monkeypatch):
    _write(tmp_path, ".github/instructions/python.instructions.md")
    monkeypatch.setattr(sync, "repo_root", lambda: tmp_path)

    assert sync.main(["check"]) == 1

    manifest_path = _manifest_path(tmp_path)
    sync.record(tmp_path, manifest_path, ".github/instructions/python.instructions.md", None)

    assert sync.main(["check"]) == 0
