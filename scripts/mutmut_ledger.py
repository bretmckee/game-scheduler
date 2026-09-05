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
                         function whose body changed between the merge-base
                         and the current worktree (stdout); human notes go to
                         stderr
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
  __mutmut_N renumbering when code shifts around.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import datetime
import json
import os
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
EDIT_SUMMARY_LIMIT = 240
LEDGER_MAX_BYTES = 950_000  # stays under the 1MB pre-commit large-file cap
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


def resolve_base_ref(explicit: str | None) -> str:
    """Return a commit-ish to diff against: explicit arg or merge-base with main."""
    if explicit:
        return explicit
    for ref in ("origin/main", "main"):
        proc = _run_git("merge-base", "HEAD", ref)
        if proc.returncode == 0 and proc.stdout.strip():
            _note(f"base ref: {ref} -> merge-base {proc.stdout.strip()[:12]}")
            return proc.stdout.strip()
    message = (
        "[ledger] could not determine base ref (tried origin/main, main); pass --base explicitly"
    )
    raise SystemExit(message)


def changed_python_files(base: str) -> list[str]:
    """Repo-relative Python files differing between `base` and the worktree.

    Two-dot form on purpose: includes uncommitted local changes so pre-commit
    sees exactly what CI will see after the pending commits land.
    """
    proc = _run_git("diff", "--name-only", "-U0", base, "--", "*.py")
    if proc.returncode != 0:
        message = f"[ledger] git diff failed against {base}: {proc.stderr}"
        raise SystemExit(message)
    return [line for line in proc.stdout.splitlines() if line.startswith(SCOPE_PREFIXES)]


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
    """Patterns plus family sets per scoped file; '*' sentinel means whole-file."""
    files = changed_python_files(base)
    if not files:
        _note("no services/ or shared/ Python changes relative to base; nothing to check")
        return [], {}
    patterns: list[str] = []
    families_by_file: dict[str, set[str]] = {}
    for relpath in files:
        file_patterns, _, fams = scope_patterns_for_file(base, relpath)
        if file_patterns:
            patterns.extend(file_patterns)
            families_by_file[relpath] = fams
    patterns = sorted(set(patterns))
    _note(f"scope resolved: {len(patterns)} pattern(s) across {len(files)} changed file(s)")
    return patterns, families_by_file


def resolve_scope(base: str) -> list[str]:
    """Backwards-compatible wrapper returning patterns only."""
    return compute_scope(base)[0]


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


def summarize_edit(diff_text: str) -> str:
    """Collapse a mutant's unified diff into one short readable line."""
    collator = _DiffCollator()
    for raw_line in diff_text.splitlines():
        collator.feed_line(raw_line)
    return collator.render()


def _file_entries(
    relpath: str, fams: set[str], classifier: ModuleType
) -> tuple[dict[str, list] | None, int, int]:
    """Extract surviving entries from one source file's mutation store record."""
    meta_path = REPO_ROOT / "mutants" / f"{relpath}.meta"
    mutant_src = REPO_ROOT / "mutants" / relpath
    if not meta_path.exists():
        _note(f"{relpath}: no result data in store; skipped")
        return None, 0, 0
    raw_meta = json.loads(meta_path.read_text(encoding="utf-8"))
    codes = raw_meta["exit_code_by_key"]
    keys = [k for k in codes if fams == {"*"} or family_of(k) in fams]
    if not keys:
        return None, 0, 0
    module = cst.parse_module(mutant_src.read_text(encoding="utf-8"))
    unchecked = sum(1 for key in keys if codes[key] is None)
    file_entries: dict[str, list] = {}
    seen_pairs: set[tuple[str, str]] = set()
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
        if pair not in seen_pairs:
            seen_pairs.add(pair)
            file_entries.setdefault(family_of(key), []).append(list(pair))
    return file_entries, len(keys), unchecked


def extract_entries(
    families_by_file: dict[str, set[str]], classifier: ModuleType
) -> tuple[dict[str, dict[str, list]], dict[str, int]]:
    """Read live store results restricted to scoped files/families.

    Returns (entries, stats); entries maps relpath -> family prefix -> [[cls, summary]].
    Only non-killed verdicts are recorded; 'survived' splits into logic (blocking
    class) vs string via the classifier predicate.
    """
    entries: dict[str, dict[str, list]] = {}
    stats = {"scanned": 0, "recorded": 0, "unchecked_in_scope": 0}
    for relpath, fams in sorted(families_by_file.items()):
        file_entries, scanned, unchecked = _file_entries(relpath, fams, classifier)
        if file_entries is None:
            continue
        entries[relpath] = file_entries
        stats["scanned"] += scanned
        stats["recorded"] += sum(len(v) for v in file_entries.values())
        stats["unchecked_in_scope"] += unchecked
    return entries, stats


def load_ledger(path: Path) -> dict:
    if not path.exists():
        _note(f"baseline {path.name} missing; every survivor will count as NEW")
        return {"entries": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    total = sum(
        len(rows) for fam_map in data.get("entries", {}).values() for rows in fam_map.values()
    )
    _note(f"loaded baseline {path.name}: {total} recorded entry(ies)")
    return data


def write_ledger(entries: dict, out_path: Path, source_commit: str) -> None:
    entry_count = sum(len(rows) for fam_map in entries.values() for rows in fam_map.values())
    payload = {
        "_readme": (
            "Mutant debt ledger (ratchet baseline). Regenerate ONLY after a complete "
            "cold run: .venv/bin/python scripts/mutmut_ledger.py snapshot. "
            "The gate blocks NEW 'logic' entries not present in this file."
        ),
        "version": 1,
        "generated_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "source_commit": source_commit,
        "entries": entries,
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
    base_summaries = {row[1] for row in base_rows}
    seen_new: set[str] = set()
    for cls, summary in rows:
        if summary in base_summaries or summary in seen_new:
            continue
        seen_new.add(summary)
        line = f"{relpath} | {func_label} | {cls} | {summary}"
        (fail_lines if cls == BLOCKING_CLASS else warn_lines).append(line)
    live_summaries = {row[1] for row in rows}
    for cls_b, summary in base_rows:
        if summary not in live_summaries:
            note = "fixed/replaced; re-run snapshot after a full cold run to shrink the ledger"
            stale_lines.append(
                f"[STALE] {relpath} | {func_label} | was:{cls_b} | {summary[:60]} | {note}"
            )
    return fail_lines, warn_lines, stale_lines


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
    entries, stats = extract_entries(families_by_file, classifier)
    out_path = Path(args.out) if args.out else LEDGER_DEFAULT
    write_ledger(entries, out_path, _git_source_commit())
    by_class: dict[str, int] = {}
    for fam_map in entries.values():
        for rows in fam_map.values():
            for cls, _ in rows:
                by_class[cls] = by_class.get(cls, 0) + 1
    summary = (
        f"snapshot complete: scanned={stats['scanned']} "
        f"recorded={stats['recorded']} classes={by_class}"
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
    live, stats = extract_entries(families_by_file, classifier)
    if stats["unchecked_in_scope"]:
        _note(
            f"WARN: {stats['unchecked_in_scope']} scoped mutant(s) have no verdict; "
            "the ratchet below may under-report new failures this time"
        )
    baseline = load_ledger(Path(args.baseline) if args.baseline else LEDGER_DEFAULT)["entries"]
    fail_lines, warn_lines, stale_lines = ratchet(baseline, live)
    print(f"\n=== mutation gate report (scope: {len(patterns)} pattern(s)) ===")
    for line in fail_lines:
        print(f"[FAIL] NEW logic survivor: {line}")
    for line in warn_lines:
        print(f"[WARN] new non-blocking entry: {line}")
    for line in stale_lines[:STALE_PREVIEW_LIMIT]:
        print(line)
    if len(stale_lines) > STALE_PREVIEW_LIMIT:
        print(f"... and {len(stale_lines) - STALE_PREVIEW_LIMIT} more stale entries")
    print(
        f"totals: new-logic={len(fail_lines)} new-other={len(warn_lines)} "
        f"stale={len(stale_lines)} recorded-now={stats['recorded']}"
    )
    if fail_lines:
        print("\nGATE FAILED: fix or test the new logic survivors above before merging.")
        return 1
    print("\nGATE PASSED")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_scope = subparsers.add_parser("scope", help="print mutmut name patterns per line")
    p_scope.add_argument(
        "--base", default=None, help="explicit base ref (default: merge-base with main)"
    )

    p_snap = subparsers.add_parser("snapshot", help="rebuild the ledger from a complete store")
    p_snap.add_argument("--out", default=None, help=f"output path (default: {LEDGER_DEFAULT.name})")

    p_gate = subparsers.add_parser("gate", help="scoped run + ratchet comparison")
    p_gate.add_argument(
        "--base", default=None, help="explicit base ref (default: merge-base with main)"
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
