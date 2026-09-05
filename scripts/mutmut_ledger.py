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


"""Mutation-testing debt ledger: ratchet baseline plus function-scoped gate.

The repo carries surviving mutants its tests do not kill. This tool records
them in a checked-in ledger (mutmut-baseline.json by default) so CI/pre-commit
can block only NEW logic failures instead of demanding the debt be paid first.

Subcommands:
    scope --base <ref>   print one mutmut name pattern per line for every
                          function whose body changed against the resolved
                          base ref (push upstream first, else origin/main,
                          else main) vs the current worktree; stdout carries
                          patterns, human notes go to stderr
    snapshot [--out F]  rebuild the ledger from the live results store; refuses
                         to run while any verdict is missing (a partial store
                         would silently shrink recorded debt)
    gate --base <ref>   scoped mutation run + ratchet comparison against the
                         committed ledger; exit 1 iff a NEW logic survivor
                         appears inside the change set, exit 2 on errors

Locked design decisions:
- Gate semantics are ratchet-only: new failing entries block; fixed or
  replaced entries are reported as stale and removed by re-running snapshot
  once the store holds full fresh verdicts.
- Hard-blocking class is "logic" survivors only. String-literal wording
  changes, timeouts (measured non-deterministic across cold runs: 39 vs 99),
  and no-tests buckets are warnings only.
- Entry identity = (file, mangled family prefix, normalized edit summary).
  Family prefixes follow mutmut's deterministic mangling ({module}.x_{func}
  top-level, {module}.xǁClassǁmethod for methods), so identities survive
  __mutmut_N renumbering when code shifts around. Edit summaries additionally
  carry no generation-time hunk line numbers: canonical_summary() strips the
  per-segment "L<n>: " prefixes before storage and comparison, keeping entry
  identity immune to line-position drift and generated-data regeneration.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import datetime
import json
import os
import re
import subprocess  # noqa: S404 - invoked with shell=False and hardcoded argv lists
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

import libcst as cst

REPO_ROOT = Path(__file__).resolve().parent.parent
LEDGER_DEFAULT = REPO_ROOT / "mutmut-baseline.json"
BLOCKING_CLASS = "logic"
SCOPE_PREFIXES = ("services/", "shared/")
TEST_SCOPE_PREFIX = "tests/"
UNMAPPED_PREVIEW_LIMIT = 5
REGRESSION_PREVIEW_LIMIT = 8
HEURISTIC_TEST_PATH_MIN_PARTS = 3
EDIT_SUMMARY_LIMIT = 240
LEDGER_MAX_BYTES = 2_048_000  # stays ~49KB under check-added-large-files --maxkb=2048
STALE_PREVIEW_LIMIT = 40


def _run_git(*cmd: str) -> subprocess.CompletedProcess[str]:
    """Run a git subcommand; argv is built from fixed literals, never user input."""
    return subprocess.run(  # noqa: S603 - fixed argv list, shell=False
        ["git", *cmd],  # noqa: S607 - resolved via PATH at call time
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _note(message: str) -> None:
    print(f"[ledger] {message}", file=sys.stderr, flush=True)


def load_classifier() -> ModuleType:
    """Load scripts/mutmut-logic-survivors.py under an importable name."""
    path = REPO_ROOT / "scripts" / "mutmut-logic-survivors.py"
    spec = spec_from_file_location("mutmut_logic_survivors", path)
    if spec is None or spec.loader is None:
        message = f"[ledger] could not load classifier module from {path}"
        raise SystemExit(message)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


UPSTREAM_REF_QUERY = ("rev-parse", "--abbrev-ref", "@{upstream}")


def resolve_base_ref(explicit: str | None) -> str:
    """Return a commit-ish to diff against for scope resolution.

    An explicit argument wins verbatim. Otherwise prefer the current branch's
    push upstream so the scope self-heals once work is pushed: while behind it
    the scope covers exactly the pending delta, and at steady state it shrinks
    to a single commit. Falls back to origin/main then local main when no
    upstream is configured or resolvable. Returns the merge-base of HEAD with
    the first candidate that resolves.
    """
    if explicit:
        return explicit
    candidates: list[str] = []
    up = _run_git(*UPSTREAM_REF_QUERY)
    if up.returncode == 0 and up.stdout.strip():
        candidates.append(up.stdout.strip())
    for ref in ("origin/main", "main"):
        if ref not in candidates:
            candidates.append(ref)
    for ref in candidates:
        proc = _run_git("merge-base", "HEAD", ref)
        if proc.returncode == 0 and proc.stdout.strip():
            _note(f"base ref: {ref} -> merge-base {proc.stdout.strip()[:12]}")
            return proc.stdout.strip()
    message = (
        "[ledger] could not determine base ref (tried push upstream, origin/main, main); "
        "pass --base explicitly"
    )
    raise SystemExit(message)


def _diff_py_files(base: str) -> list[str]:
    """Repo-relative Python files differing between `base` and the worktree."""
    proc = _run_git("diff", "--name-only", "-U0", base, "--", "*.py")
    if proc.returncode != 0:
        message = f"[ledger] git diff failed against {base}: {proc.stderr}"
        raise SystemExit(message)
    return [line for line in proc.stdout.splitlines() if line.strip()]


def changed_python_files(base: str) -> list[str]:
    """Source files under services/ or shared/ that differ relative to base.

    Two-dot form on purpose: includes uncommitted local changes so pre-commit
    sees exactly what CI will see after the pending commits land.
    """
    return [f for f in _diff_py_files(base) if f.startswith(SCOPE_PREFIXES)]


def changed_test_files(base: str) -> list[str]:
    """Test files under tests/ that differ relative to base."""
    return [f for f in _diff_py_files(base) if f.startswith(TEST_SCOPE_PREFIX)]


class FunctionSpan:
    """One named function's source span plus its mutmut family prefix."""

    def __init__(self, name: str, start_line: int, end_line: int, family: str) -> None:
        self.name = name
        self.start_line = start_line
        self.end_line = end_line
        self.family = family

    @property
    def pattern(self) -> str:
        return f"{self.family}__mutmut_*"


def _function_spans(source: str, dotted_module: str) -> list[FunctionSpan]:
    """Map every FunctionDef/AsyncFunctionDef to a mutmut family prefix.

    Nested defs keep the nearest-enclosing-class chain; decorator lines are
    attributed to the definition they decorate.
    """
    tree = ast.parse(source)
    spans: list[FunctionSpan] = []

    def walk(node: ast.AST, class_chain: list[str]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start = getattr(
                    min((d for d in child.decorator_list), key=lambda d: d.lineno, default=child),
                    "lineno",
                    child.lineno,
                )
                spans.append(
                    FunctionSpan(
                        name=child.name,
                        start_line=start,
                        end_line=child.end_lineno or start,
                        family=(
                            f"{dotted_module}.x{'ǁ'.join(['', *class_chain, child.name])}"
                            if class_chain
                            else f"{dotted_module}.x_{child.name}"
                        ),
                    )
                )
                # descend into the body so nested defs get their own entries too
                walk(child, class_chain)
            elif isinstance(child, ast.ClassDef):
                walk(child, [*class_chain, child.name])
            else:
                walk(child, class_chain)

    walk(tree, [])
    return spans


def innermost_span(spans: list[FunctionSpan], line: int) -> FunctionSpan | None:
    candidates = [s for s in spans if s.start_line <= line <= s.end_line]
    if not candidates:
        return None
    return max(candidates, key=lambda s: s.start_line)


def parse_hunk_ranges(diff_text: str) -> set[int]:
    """New-file line numbers touched by a per-file `git diff -U0` output."""
    touched: set[int] = set()
    new_line = 0
    in_hunk = False
    for raw in diff_text.splitlines():
        if raw.startswith("@@"):
            # header form: @@ -old[,count] +new[,count] @@ [section]
            new_line = int(raw.split()[2].lstrip("+").split(",")[0])
            in_hunk = True
            continue
        if not in_hunk or raw.startswith(("+++", "---")):
            continue
        if raw.startswith("-"):
            # deletion at old position; anchor to the current new-side line
            if new_line > 0:
                touched.add(new_line)
        elif raw.startswith("+"):
            touched.add(new_line)
            new_line += 1
        else:
            new_line += 1
    return touched


def scope_patterns_for_file(base: str, relpath: str) -> tuple[list[str], list[str], set[str]]:
    """Patterns + notes + family prefix set for one changed file.

    The third element uses '*' to mean whole-file scope. A changed line with no
    enclosing named function escalates the whole file so no mutant can slip
    past the gate silently.
    """
    proc = _run_git("diff", "-U0", "--no-color", base, "--", relpath)
    if proc.returncode != 0:
        message = f"[ledger] git diff failed for {relpath}: {proc.stderr}"
        raise SystemExit(message)
    source_path = REPO_ROOT / relpath
    if not source_path.exists():
        _note(f"{relpath}: deleted in change set; nothing to scope")
        return [], [], set()
    source = source_path.read_text(encoding="utf-8")
    dotted_module = Path(relpath).with_suffix("").as_posix().replace("/", ".")
    # mutmut drops '__init__.' from mangled keys (see __main__.py run loop)
    family_root = dotted_module.removesuffix(".__init__")
    spans = _function_spans(source, family_root)
    touched = parse_hunk_ranges(proc.stdout)
    if not touched:
        return [], [], set()

    source_lines = source.splitlines()
    families: dict[str, str] = {}
    unattributed_code: list[int] = []
    for line in sorted(touched):
        span = innermost_span(spans, line)
        if span is not None:
            families.setdefault(span.family, span.name)
            continue
        stripped = source_lines[line - 1].strip() if 0 < line <= len(source_lines) else ""
        # blank or comment-only lines carry no mutation surface; real code
        # outside every named function escalates to file-level scope instead
        if stripped and not stripped.startswith("#"):
            unattributed_code.append(line)

    if unattributed_code:
        note = (
            f"{relpath}: changed lines outside named functions "
            f"(e.g. L{unattributed_code[0]}) -> file-level scope"
        )
        _note(note)
        return [f"{family_root}*"], [note], {"*"}

    patterns = [f"{fam}__mutmut_*" for fam in sorted(families)]
    notes = [f"{relpath}: {len(patterns)} function(s): " + ", ".join(sorted(families.values()))]
    _note(notes[0])
    return patterns, notes, set(families)


# ---------------------------------------------------------------------------
# Execution, entry extraction, ledger IO, and the ratchet gate


# Local copy of mutmut's status map (__main__.py status_by_exit_code) so this
# tool never imports mutmut.__main__ for its module-level fork-startup side effects.
STATUS_TO_CLASS = {
    0: "survived",
    1: "killed",
    3: "killed",
    # Empirically mapped to mutmut's timeout emoji across cold runs
    # (store count always equals the progress-bar timeout tally):
    -24: "timeout",
    5: "notests",
    33: "notests",
    36: "timeout",
    37: "typecheck",
}
EDIT_SUMMARY_LIMIT = 240


def compute_scope(base: str) -> tuple[list[str], dict[str, set[str]]]:
    """Patterns plus family sets per scoped file; '*' sentinel means whole-file.

    Scope is the union of (a) function families of changed source lines and
    (b) every mutant of modules that changed test files import. Part (b)
    catches tests-only PRs weakening killers of untouched code.
    """
    files = changed_python_files(base)
    test_files = changed_test_files(base)
    test_modules, unmapped_tests = map_test_modules(test_files, base)
    if not files and not test_modules:
        _note("no services/shared or attributable test changes relative to base")
        return [], {}
    patterns: list[str] = []
    families_by_file: dict[str, set[str]] = {}
    for relpath in files:
        file_patterns, _, fams = scope_patterns_for_file(base, relpath)
        if file_patterns:
            patterns.extend(file_patterns)
            families_by_file[relpath] = fams
    for relpath in test_modules:
        dotted = Path(relpath).with_suffix("").as_posix().replace("/", ".")
        patterns.append(f"{dotted}.*")
        families_by_file.setdefault(relpath, set()).add("*")
    if unmapped_tests:
        preview = ", ".join(unmapped_tests[:UNMAPPED_PREVIEW_LIMIT]) + (
            " ..." if len(unmapped_tests) > UNMAPPED_PREVIEW_LIMIT else ""
        )
        _note(
            f"WARN: {len(unmapped_tests)} changed test path(s) could not be mapped to a "
            f"source module (attribution skipped): {preview}"
        )
    patterns = sorted(set(patterns))
    _note(
        f"scope resolved: {len(patterns)} pattern(s) across {len(files)} source and "
        f"{len(test_files)} test file(s)"
    )
    return patterns, families_by_file


def resolve_scope(base: str) -> list[str]:
    """Backwards-compatible wrapper returning patterns only."""
    return compute_scope(base)[0]


def _imported_dotted_modules(source_text: str) -> set[str]:
    """Dotted module names a Python file imports, restricted to app packages."""
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return set()
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    return {m for m in modules if m.startswith(("services.", "shared."))}


def _module_relpaths(dotted: str) -> list[str]:
    """Concrete source paths one imported dotted name can refer to.

    An exact module wins; otherwise the package's direct child modules are
    returned so a package-level import still bounds re-check cost sensibly.
    """
    base_dir = REPO_ROOT / dotted.replace(".", "/")
    exact = base_dir.with_suffix(".py")
    if exact.is_file():
        return [str(exact.relative_to(REPO_ROOT))]
    if base_dir.is_dir():
        return sorted(str(p.relative_to(REPO_ROOT)) for p in base_dir.glob("*.py"))
    return []


def _heuristic_module_relpath(test_path: str) -> str | None:
    """Mirror-layout guess: tests/unit/<pkg>/test_<mod>.py <-> <pkg>/<mod>.py."""
    parts = test_path.split("/")
    if len(parts) >= HEURISTIC_TEST_PATH_MIN_PARTS and parts[0] == "tests" and parts[1] == "unit":
        leaf = parts[-1].removesuffix(".py").removeprefix("test_")
        candidate = f"{'/'.join(parts[2:-1])}/{leaf}.py"
        if (REPO_ROOT / candidate).is_file() and candidate.startswith(SCOPE_PREFIXES):
            return candidate
    return None


def _test_file_texts(base: str, test_path: str) -> list[str]:
    """A test file's content from the worktree and from base, whichever exist.

    Deletions and renames lose their import lists unless we also read the base
    version: kills in the baseline were produced by the suite that existed at
    snapshot time, so attribution must span both sides of a changed test file.
    """
    texts: list[str] = []
    path = REPO_ROOT / test_path
    if path.is_file():
        with contextlib.suppress(OSError):
            texts.append(path.read_text(encoding="utf-8"))
    show = _run_git("show", f"{base}:{test_path}")
    if show.returncode == 0 and show.stdout.strip() and (not texts or show.stdout != texts[0]):
        texts.append(show.stdout)
    return texts


def map_test_modules(test_paths: list[str], base: str) -> tuple[list[str], list[str]]:
    """Map changed test files onto the source modules their imports exercise.

    Imports are unioned over the worktree AND the base version of each test so
    deleted/renamed files still attribute to what they used to kill. Returns
    (source relpaths, unmapped test paths); unmapped keeps a documented WARN
    instead of a silent skip so coverage loss is visible at commit time.
    """
    mapped: set[str] = set()
    unmapped: list[str] = []
    for test_path in test_paths:
        candidates: set[str] = set()
        for text in _test_file_texts(base, test_path):
            for dotted in _imported_dotted_modules(text):
                candidates.update(_module_relpaths(dotted))
        heuristic = _heuristic_module_relpath(test_path)
        if heuristic:
            candidates.add(heuristic)
        if candidates:
            mapped.update(candidates)
        else:
            unmapped.append(test_path)
    return sorted(mapped), unmapped


def run_scoped(patterns: list[str]) -> None:
    """Execute the scoped mutation run via the crash-safe launcher."""
    entrypoint = str(REPO_ROOT / "scripts" / "run-mutmut.py")
    proc = subprocess.run(  # noqa: S603 - fixed argv; patterns come from our own resolver
        [sys.executable, entrypoint, "run", *patterns],
        cwd=REPO_ROOT,
        env={**os.environ, "TESTING": "true"},
        capture_output=True,
        text=True,
        check=False,
    )
    raw_tail = (proc.stderr or "").replace("\r", "\n").splitlines()
    tail_lines = [line for line in raw_tail if line.strip()]
    interesting = ("mutations/second", "🎉", "🙁", "⏰")
    stats = [line for line in tail_lines if any(token in line for token in interesting)]
    summary = " | ".join(stats[-3:]) if stats else f"[ledger] scoped run rc={proc.returncode}"
    print(summary)
    if proc.returncode != 0:
        print(tail_lines[-12:], file=sys.stderr)
        message = "[ledger] scoped mutation run failed; see output above"
        raise SystemExit(message)


def family_of(key: str) -> str:
    return key.rpartition("__mutmut_")[0]


CLIP_CHARS = 48


def _clip(text: str) -> str:
    return text if len(text) <= CLIP_CHARS else text[: CLIP_CHARS - 3] + "..."


class _DiffCollator:
    """Accumulates unified-diff hunks into short per-change descriptions."""

    def __init__(self) -> None:
        self.changes: list[str] = []
        self._cur_new = 0
        self._minus_run: list[str] = []
        self._plus_run: list[tuple[int, str]] = []

    def _flush(self) -> None:
        pairs = min(len(self._minus_run), len(self._plus_run))
        for i in range(pairs):
            line_no, new_text = self._plus_run[i]
            where = f"L{line_no}: " if line_no else ""
            old_text = _clip(self._minus_run[i].strip())
            self.changes.append(f"{where}{old_text!r} => {_clip(new_text.strip())!r}")
        self.changes.extend(f"removed {_clip(text.strip())!r}" for text in self._minus_run[pairs:])
        self.changes.extend(f"added {_clip(text.strip())!r}" for _, text in self._plus_run[pairs:])
        self._minus_run.clear()
        self._plus_run.clear()

    def feed_line(self, raw: str) -> None:
        """Consume one raw diff line, tracking the new-file-side position."""
        if raw.startswith("@@"):
            with contextlib.suppress(IndexError, ValueError):
                self._cur_new = int(raw.split()[2].lstrip("+").split(",")[0])
            return
        if raw.startswith("---") or raw.startswith("+++"):
            return
        char = raw[:1]
        if char == "-":
            if self._plus_run:
                self._flush()
            self._minus_run.append(raw[1:])
        elif char == "+":
            self._plus_run.append((self._cur_new, raw[1:]))
            self._cur_new += 1
        elif self._cur_new:
            # context / blank lines advance the new-side position
            self._cur_new += 1

    def render(self) -> str:
        if self._minus_run or self._plus_run:
            self._flush()
        joined = "; ".join(self.changes) if self.changes else "(no textual change detected)"
        if len(joined) > EDIT_SUMMARY_LIMIT:
            return joined[: EDIT_SUMMARY_LIMIT - 4] + " …+"
        return joined


_LINE_PREFIX_RE = re.compile(r"^L\d+: ")


def canonical_summary(text: str) -> str:
    """Strip per-segment generation-time hunk coordinates from an edit summary.

    Entries are identified by (file, family, normalized edit summary). Some
    segments carry an ``L<n>: `` prefix taken from the mutant's diff at
    generation time; those coordinates drift whenever source lines above the
    edit move or generated data regenerates with different hunk alignment,
    which would otherwise make the ratchet report spurious NEW + STALE pairs
    for edits whose semantics never changed. Comparing and storing summaries
    in this coordinate-free form makes entry identity position-independent.
    """
    return "; ".join(_LINE_PREFIX_RE.sub("", seg) for seg in text.split("; "))


def summarize_edit(diff_text: str) -> str:
    """Collapse a mutant's unified diff into one short readable line."""
    collator = _DiffCollator()
    for raw_line in diff_text.splitlines():
        collator.feed_line(raw_line)
    return collator.render()


def _mutant_num(key: str) -> int:
    """Numeric suffix of a ``...__mutmut_N`` store key."""
    return int(key.rpartition("__mutmut_")[2])


def _file_entries(
    relpath: str, fams: set[str], classifier: ModuleType
) -> tuple[dict[str, list] | None, int, int, list[str]]:
    """Extract surviving entries plus currently-killed keys for one file's record."""
    meta_path = REPO_ROOT / "mutants" / f"{relpath}.meta"
    mutant_src = REPO_ROOT / "mutants" / relpath
    if not meta_path.exists():
        _note(f"{relpath}: no result data in store; skipped")
        return None, 0, 0, []
    raw_meta = json.loads(meta_path.read_text(encoding="utf-8"))
    codes = raw_meta["exit_code_by_key"]
    keys = [k for k in codes if fams == {"*"} or family_of(k) in fams]
    if not keys:
        return None, 0, 0, []
    module = cst.parse_module(mutant_src.read_text(encoding="utf-8"))
    unchecked = sum(1 for key in keys if codes[key] is None)
    killed_keys = [
        key
        for key in keys
        if codes[key] is not None and STATUS_TO_CLASS.get(codes[key]) == "killed"
    ]
    file_entries: dict[str, list] = {}
    # Dedup must stay scoped to one function family. Two different functions
    # can legitimately render byte-identical edit text (e.g., both delete a
    # `user_id=None` kwarg line); a file-wide dedup set would let whichever
    # family processed first suppress the other's rows in every stamped
    # baseline, with results depending on processing order and scope mix.
    seen_pairs: dict[str, set[tuple[str, str]]] = {}
    for key in keys:
        code = codes[key]
        if code is None:
            continue
        base_cls = STATUS_TO_CLASS.get(code, "other")
        if base_cls == "killed":
            continue
        diff = classifier.compute_diff(module, key, relpath)
        cls = (
            ("string" if classifier.is_string_only_mutation(diff) else BLOCKING_CLASS)
            if base_cls == "survived"
            else base_cls
        )
        pair = (cls, summarize_edit(diff))
        fam = family_of(key)
        seen_for_fam = seen_pairs.setdefault(fam, set())
        if pair not in seen_for_fam:
            seen_for_fam.add(pair)
            file_entries.setdefault(fam, []).append(list(pair))
    return file_entries, len(keys), unchecked, killed_keys


def extract_entries(
    families_by_file: dict[str, set[str]], classifier: ModuleType
) -> tuple[dict[str, dict[str, list]], dict[str, dict[str, list[int]]], dict[str, int]]:
    """Read live store results restricted to scoped files/families.

    Returns (entries, live_killed, stats). entries maps relpath -> family prefix
    -> [[cls, summary]]; only non-killed verdicts are recorded, 'survived' splits
    into logic (blocking class) vs string via the classifier predicate.
    live_killed maps relpath -> family prefix -> sorted list of mutant numbers
    currently reporting killed, used by the kill-regression check.
    """
    entries: dict[str, dict[str, list]] = {}
    live_killed: dict[str, dict[str, list[int]]] = {}
    stats = {"scanned": 0, "recorded": 0, "unchecked_in_scope": 0}
    for relpath, fams in sorted(families_by_file.items()):
        file_entries, scanned, unchecked, killed_keys = _file_entries(relpath, fams, classifier)
        if file_entries is None:
            continue
        entries[relpath] = file_entries
        stats["scanned"] += scanned
        stats["recorded"] += sum(len(v) for v in file_entries.values())
        stats["unchecked_in_scope"] += unchecked
        if killed_keys:
            per_family: dict[str, set[int]] = {}
            for key in killed_keys:
                per_family.setdefault(family_of(key), set()).add(_mutant_num(key))
            live_killed[relpath] = {fam: sorted(ns) for fam, ns in per_family.items()}
    return entries, live_killed, stats


def load_ledger(path: Path) -> dict:
    if not path.exists():
        _note(f"baseline {path.name} missing; every survivor will count as NEW")
        return {"entries": {}, "killed": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    total = sum(
        len(rows) for fam_map in data.get("entries", {}).values() for rows in fam_map.values()
    )
    killed_total = sum(
        len(ns) for fam_map in data.get("killed", {}).values() for ns in fam_map.values()
    )
    note = (
        f"loaded baseline {path.name}: {total} recorded entry(ies), {killed_total} tracked kill(s)"
    )
    if "killed" not in data:
        note += "; pre-v2 ledger, kill-regression check disabled"
    _note(note)
    return data


def write_ledger(entries: dict, killed: dict, out_path: Path, source_commit: str) -> None:
    # Stored identity must survive line-number drift, so ledger entries carry
    # the coordinate-free summary form from day one of their life.
    canonical_entries = {
        relpath: {
            family: [[cls, canonical_summary(summary)] for cls, summary in rows]
            for family, rows in families.items()
        }
        for relpath, families in entries.items()
    }
    entry_count = sum(len(rows) for fam_map in entries.values() for rows in fam_map.values())
    payload = {
        "_readme": (
            "Mutant debt ledger v2 (ratchet baseline). Regenerate ONLY after a complete "
            "cold run: .venv/bin/python scripts/mutmut_ledger.py snapshot. "
            "'entries' gates NEW non-killed logic survivors; 'killed' tracks which "
            "__mutmut_N were killed so weakened tests that resurrect them are blocked."
        ),
        "version": 2,
        "generated_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "source_commit": source_commit,
        "entries": canonical_entries,
        "killed": killed,
    }
    text = json.dumps(payload, indent=1, sort_keys=True)
    size = len(text.encode("utf-8"))
    if size > LEDGER_MAX_BYTES:
        message = (
            f"[ledger] baseline would be {size // 1024}KB (>{LEDGER_MAX_BYTES // 1024}KB cap); "
            "pay down debt or tighten summaries before committing"
        )
        raise SystemExit(message)
    out_path.write_text(text + "\n", encoding="utf-8")
    _note(f"wrote {out_path.name}: {entry_count} entries, {size // 1024}KB")


def ratchet(baseline_entries: dict, live_entries: dict) -> tuple[list[str], list[str], list[str]]:
    """Compare scoped live results against the ledger partition actually run."""
    fail_lines: list[str] = []
    warn_lines: list[str] = []
    stale_lines: list[str] = []
    for relpath, fams_live in sorted(live_entries.items()):
        base_file = baseline_entries.get(relpath, {})
        for fam, rows in sorted(fams_live.items()):
            func_label = _family_func_label(fam)
            part_fail, part_warn, part_stale = _ratchet_family(
                relpath, func_label, rows, base_file.get(fam, [])
            )
            fail_lines.extend(part_fail)
            warn_lines.extend(part_warn)
            stale_lines.extend(part_stale)
    return fail_lines, warn_lines, stale_lines


def _family_func_label(family: str) -> str:
    """Render a mangled family key as its human-readable function/method name."""
    if "ǁ" in family:  # class-method form: {module}.xǁ{class}ǁ{method}
        return family.rpartition("ǁ")[2]
    _, sep, tail = family.rpartition(".x_")  # module-path form: {module}.x_{func}
    if sep:
        return tail
    return family.rsplit("x_", 1)[-1]


def _ratchet_family(
    relpath: str, func_label: str, rows: list, base_rows: list
) -> tuple[list[str], list[str], list[str]]:
    """Compare one function family's live entries against its baseline rows."""
    fail_lines: list[str] = []
    warn_lines: list[str] = []
    stale_lines: list[str] = []
    # Compare on coordinate-free form so hunk-position drift never reads as
    # new debt; legacy baselines carrying L-prefixed entries match too.
    base_summaries = {canonical_summary(row[1]) for row in base_rows}
    seen_new: set[str] = set()
    for cls, summary in rows:
        canon = canonical_summary(summary)
        if canon in base_summaries or canon in seen_new:
            continue
        seen_new.add(canon)
        line = f"{relpath} | {func_label} | {cls} | {summary}"
        (fail_lines if cls == BLOCKING_CLASS else warn_lines).append(line)
    live_summaries = {canonical_summary(row[1]) for row in rows}
    for cls_b, summary in base_rows:
        # Same coordinate-free comparison as above; keep raw text only for display.
        if canonical_summary(summary) not in live_summaries:
            note = "fixed/replaced; re-run snapshot after a full cold run to shrink the ledger"
            stale_lines.append(
                f"[STALE] {relpath} | {func_label} | was:{cls_b} | {summary[:60]} | {note}"
            )
    return fail_lines, warn_lines, stale_lines


def kill_regressions(
    base_killed: dict[str, dict[str, list[int]]], live_killed: dict[str, dict[str, list[int]]]
) -> list[str]:
    """Baseline-killed mutants that no longer report killed within this run scope.

    Only families actually re-run this time are compared; out-of-scope families
    stay excluded so a clobbered store cannot manufacture false positives.
    """
    lines: list[str] = []
    for relpath, fams_base in sorted(base_killed.items()):
        live_fams = live_killed.get(relpath)
        if not live_fams:
            continue
        for fam, base_ns in sorted(fams_base.items()):
            # Families absent from this run's scope were not re-judged here, so
            # comparing them would report every baseline kill as "lost".
            if fam not in live_fams:
                continue
            live_ns = set(live_fams[fam])
            lost = [n for n in base_ns if n not in live_ns]
            if not lost:
                continue
            label = _family_func_label(fam)
            preview = ", ".join(f"__mutmut_{n}" for n in lost[:REGRESSION_PREVIEW_LIMIT])
            more = (
                f" (+{len(lost) - REGRESSION_PREVIEW_LIMIT} more)"
                if len(lost) > REGRESSION_PREVIEW_LIMIT
                else ""
            )
            lines.append(
                f"{relpath} | {label} | {len(lost)} previously-killed mutant(s) now survive: "
                f"{preview}{more}"
            )
    return lines


def _git_source_commit() -> str:
    sha = _run_git("rev-parse", "--short", "HEAD").stdout.strip()
    dirty = _run_git("status", "--porcelain").stdout.strip()
    return f"{sha}-dirty" if dirty else sha


def cmd_snapshot(args: argparse.Namespace) -> int:
    classifier = load_classifier()
    metas = sorted((REPO_ROOT / "mutants").rglob("*.py.meta"))
    if not metas:
        message = "[ledger] results store empty; do a (cold) mutation run first"
        raise SystemExit(message)
    unchecked_total = 0
    for meta in metas:
        data = json.loads(meta.read_text(encoding="utf-8"))
        unchecked_total += sum(1 for v in data["exit_code_by_key"].values() if v is None)
    if unchecked_total:
        message = (
            f"[ledger] store incomplete: {unchecked_total} mutant(s) without verdicts. "
            "Run a full cold pass first: rm -rf mutants && "
            ".venv/bin/python scripts/run-mutmut.py run "
            "(then re-run snapshot)."
        )
        raise SystemExit(message)
    families_by_file: dict[str, set[str]] = {}
    for meta in metas:
        rel = str(meta.relative_to(REPO_ROOT / "mutants"))[: -len(".meta")]
        families_by_file[rel] = {"*"}
    entries, live_killed, stats = extract_entries(families_by_file, classifier)
    out_path = Path(args.out) if args.out else LEDGER_DEFAULT
    write_ledger(entries, live_killed, out_path, _git_source_commit())
    by_class: dict[str, int] = {}
    for fam_map in entries.values():
        for rows in fam_map.values():
            for cls, _ in rows:
                by_class[cls] = by_class.get(cls, 0) + 1
    killed_total = sum(len(ns) for fams in live_killed.values() for ns in fams.values())
    summary = (
        f"snapshot complete: scanned={stats['scanned']} "
        f"recorded={stats['recorded']} classes={by_class} tracked-kills={killed_total}"
    )
    print(summary)
    return 0


def cmd_gate(args: argparse.Namespace) -> int:
    classifier = load_classifier()
    base = resolve_base_ref(args.base)
    patterns, families_by_file = compute_scope(base)
    if not patterns:
        print("OK: no mutation surface changed relative to base")
        return 0
    run_scoped(patterns)
    live, live_killed, stats = extract_entries(families_by_file, classifier)
    if stats["unchecked_in_scope"]:
        _note(
            f"WARN: {stats['unchecked_in_scope']} scoped mutant(s) have no verdict; "
            "the ratchet below may under-report new failures this time"
        )
    ledger_data = load_ledger(Path(args.baseline) if args.baseline else LEDGER_DEFAULT)
    base_entries = ledger_data.get("entries", {})
    base_killed = ledger_data.get("killed") or {}
    fail_lines, warn_lines, stale_lines = ratchet(base_entries, live)
    regressions = kill_regressions(base_killed, live_killed) if base_killed else []
    print(f"\n=== mutation gate report (scope: {len(patterns)} pattern(s)) ===")
    for line in fail_lines:
        print(f"[FAIL] NEW logic survivor: {line}")
    for line in regressions:
        print(f"[FAIL] KILL REGRESSION (weakened test?): {line}")
    for line in warn_lines:
        print(f"[WARN] new non-blocking entry: {line}")
    for line in stale_lines[:STALE_PREVIEW_LIMIT]:
        print(line)
    if len(stale_lines) > STALE_PREVIEW_LIMIT:
        print(f"... and {len(stale_lines) - STALE_PREVIEW_LIMIT} more stale entries")
    print(
        f"totals: new-logic={len(fail_lines)} kill-regressions={len(regressions)} "
        f"new-other={len(warn_lines)} stale={len(stale_lines)} recorded-now={stats['recorded']}"
    )
    if fail_lines or regressions:
        hint = ""
        if regressions and not fail_lines:
            hint = (
                "\nKilled mutants that survive again mean a changed test lost teeth; "
                "restore/strengthen it (or consciously accept via a fresh cold snapshot)."
            )
        print("\nGATE FAILED: see FAIL lines above." + hint)
        return 1
    print("\nGATE PASSED")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_scope = subparsers.add_parser("scope", help="print mutmut name patterns per line")
    p_scope.add_argument(
        "--base",
        default=None,
        help="explicit base ref (default: resolved via resolve_base_ref)",
    )

    p_snap = subparsers.add_parser("snapshot", help="rebuild the ledger from a complete store")
    p_snap.add_argument("--out", default=None, help=f"output path (default: {LEDGER_DEFAULT.name})")

    p_gate = subparsers.add_parser("gate", help="scoped run + ratchet comparison")
    p_gate.add_argument(
        "--base",
        default=None,
        help="explicit base ref (default: resolved via resolve_base_ref)",
    )
    p_gate.add_argument(
        "--baseline",
        default=None,
        help="ledger file to compare against (default: ./mutmut-baseline.json)",
    )

    args = parser.parse_args()
    if args.command == "scope":
        for pattern in resolve_scope(resolve_base_ref(args.base)):
            print(pattern)
        return 0
    if args.command == "snapshot":
        return cmd_snapshot(args)
    return cmd_gate(args)


if __name__ == "__main__":
    raise SystemExit(main())
