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


"""
Detect drift between Copilot-native AI config files and their Claude-native conversions.

Watches .github/copilot-instructions.md, .github/{agents,instructions,prompts}/**/*.md,
and .copilot-tracking/planning/prompts/*.md. New or changed files require a human (or the
/sync-claude-config skill) to decide what, if anything, needs converting for Claude Code -
this script only does the mechanical hashing and bookkeeping, never the conversion itself.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

_MANIFEST_RELATIVE_PATH = Path(".claude/config-sync-manifest.json")

_SOURCE_GLOBS: tuple[str, ...] = (
    ".github/copilot-instructions.md",
    ".github/agents/**/*.md",
    ".github/instructions/**/*.md",
    ".github/prompts/**/*.md",
    ".copilot-tracking/planning/prompts/*.md",
)


def repo_root() -> Path:
    """Return the repository root (parent of this script's scripts/ directory)."""
    return Path(__file__).resolve().parent.parent


def find_source_paths(root: Path) -> list[str]:
    """Return sorted repo-relative POSIX paths for every file in the watched scope."""
    paths: set[str] = set()
    for pattern in _SOURCE_GLOBS:
        for match in root.glob(pattern):
            if match.is_file():
                paths.add(match.relative_to(root).as_posix())
    return sorted(paths)


def sha256_of(path: Path) -> str:
    """Return the hex-encoded SHA-256 digest of a file's contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest(manifest_path: Path) -> dict:
    """Load the manifest, returning an empty entry set if it doesn't exist yet."""
    if not manifest_path.exists():
        return {"entries": {}}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def save_manifest(manifest_path: Path, manifest: dict) -> None:
    """Write the manifest back to disk as sorted, pretty-printed JSON."""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest["entries"] = dict(sorted(manifest["entries"].items()))
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def check(root: Path, manifest_path: Path) -> int:
    """
    Compare the current watched files against the manifest, autofixing clean removals.

    Returns 0 if nothing needs human attention, 1 otherwise. Always persists autofixes
    (dropped/removed entries) even when other entries still require attention.
    """
    manifest = load_manifest(manifest_path)
    entries = manifest["entries"]
    current_sources = find_source_paths(root)
    needs_action = False

    for source in current_sources:
        source_hash = sha256_of(root / source)
        entry = entries.get(source)
        if entry is None:
            print(f"NEW: {source} has no conversion recorded. Run /sync-claude-config.")
            needs_action = True
        elif entry["source_hash"] != source_hash:
            print(f"CHANGED: {source} changed since last sync. Run /sync-claude-config.")
            needs_action = True

    for source in [s for s in entries if s not in current_sources]:
        entry = entries.pop(source)
        output = entry.get("output")
        if output is None:
            print(f"REMOVED: {source} is gone; dropping its manifest entry.")
            continue

        output_path = root / output
        if not output_path.exists():
            print(f"REMOVED: {source} is gone; output {output} already gone too.")
            continue

        if sha256_of(output_path) == entry.get("output_hash"):
            output_path.unlink()
            print(f"REMOVED: {source} is gone; deleted its generated output {output}.")
        else:
            print(
                f"CONFLICT: {source} was removed, but its output {output} has been hand-edited "
                f"since generation. Resolve manually, then run: "
                f"scripts/check_ai_config_sync.py forget {source}"
            )
            entries[source] = entry
            needs_action = True

    save_manifest(manifest_path, manifest)
    return 1 if needs_action else 0


def record(root: Path, manifest_path: Path, source: str, output: str | None) -> int:
    """Record the current hash of SOURCE (and OUTPUT, if given) in the manifest."""
    source_path = root / source
    if not source_path.is_file():
        print(f"error: source file not found: {source}", file=sys.stderr)
        return 1

    output_hash: str | None = None
    if output is not None:
        output_path = root / output
        if not output_path.is_file():
            print(f"error: output file not found: {output}", file=sys.stderr)
            return 1
        output_hash = sha256_of(output_path)

    manifest = load_manifest(manifest_path)
    manifest["entries"][source] = {
        "source_hash": sha256_of(source_path),
        "output": output,
        "output_hash": output_hash,
    }
    save_manifest(manifest_path, manifest)
    print(f"recorded {source}" + (f" -> {output}" if output else " (reference-only, no output)"))
    return 0


def forget(manifest_path: Path, source: str) -> int:
    """Remove SOURCE's manifest entry without touching any files."""
    manifest = load_manifest(manifest_path)
    if source not in manifest["entries"]:
        print(f"{source} is not tracked; nothing to do.")
        return 0
    del manifest["entries"][source]
    save_manifest(manifest_path, manifest)
    print(f"forgot {source}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("check", help="Detect drift and autofix clean removals.")

    record_parser = subparsers.add_parser("record", help="Record a source/output pair as in sync.")
    record_parser.add_argument("source")
    record_parser.add_argument("output", nargs="?", default=None)

    forget_parser = subparsers.add_parser("forget", help="Drop a manifest entry, untouched files.")
    forget_parser.add_argument("source")

    args = parser.parse_args(argv)
    root = repo_root()
    manifest_path = root / _MANIFEST_RELATIVE_PATH

    if args.command == "check":
        return check(root, manifest_path)
    if args.command == "record":
        return record(root, manifest_path, args.source, args.output)
    return forget(manifest_path, args.source)


if __name__ == "__main__":
    sys.exit(main())
