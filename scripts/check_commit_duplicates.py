# Copyright (C) 2024 Bret McKee
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Check if commit introduces duplicates or duplicates existing code.
Only fails if duplicates overlap with actual changed lines (not just changed files).
Designed for pre-commit hook use.
"""

import json
import re
import subprocess
import sys
from pathlib import Path


def _should_track_file(filepath: str) -> bool:
    """Check if file should be tracked for duplicate detection."""
    excluded_paths = ["tests/", "__pycache__", "node_modules/", ".min.js"]

    is_source_file = filepath.endswith(".py") or filepath.endswith((".ts", ".tsx", ".js", ".jsx"))
    is_not_excluded = not any(x in filepath for x in excluded_paths)

    return is_source_file and is_not_excluded


def _extract_line_range_from_hunk(hunk_header: str) -> tuple[int, int]:
    """Extract start line and count from git diff hunk header."""
    match = re.search(r"\+(\d+)(?:,(\d+))?", hunk_header)
    if not match:
        return 0, 0

    start_line = int(match.group(1))
    count = int(match.group(2)) if match.group(2) else 1
    return start_line, count


def _process_diff_line(
    line: str, changed_lines: dict[str, set[int]], current_file: str | None
) -> str | None:
    """
    Process a single line from git diff output.
    Returns updated current_file (or None if file should not be tracked).
    """
    if line.startswith("+++ b/"):
        filepath = line[6:]
        if filepath and _should_track_file(filepath):
            changed_lines[filepath] = set()
            return filepath
        return None

    if line.startswith("@@") and current_file:
        start_line, count = _extract_line_range_from_hunk(line)
        if start_line > 0:
            for line_num in range(start_line, start_line + count):
                changed_lines[current_file].add(line_num)

    return current_file


def get_changed_line_ranges() -> dict[str, set[int]]:
    """
    Get the specific line numbers changed in each staged file.
    Returns: Dict mapping file paths to sets of changed line numbers.
    """
    result = subprocess.run(
        [
            "git",
            "diff",
            "--cached",
            "--unified=0",
        ],  # unified=0 shows only changed lines
        capture_output=True,
        text=True,
        check=True,
    )

    changed_lines = {}
    current_file = None

    for line in result.stdout.split("\n"):
        current_file = _process_diff_line(line, changed_lines, current_file)

    return {f: lines for f, lines in changed_lines.items() if lines}


def ranges_overlap(changed_lines: set[int], dup_start: int, dup_end: int) -> bool:
    """Check if duplicate's line range overlaps with changed lines."""
    dup_range = set(range(dup_start, dup_end + 1))
    return bool(changed_lines & dup_range)


def _build_duplicate_info(dup: dict) -> dict:
    """Extract duplicate information from jscpd report entry."""
    return {
        "first_file": dup["firstFile"]["name"],
        "second_file": dup["secondFile"]["name"],
        "first_start": dup["firstFile"]["start"],
        "first_end": dup["firstFile"]["end"],
        "second_start": dup["secondFile"]["start"],
        "second_end": dup["secondFile"]["end"],
        "line_count": dup["lines"],
        "tokens": dup["tokens"],
        "fragment": dup.get("fragment", ""),
    }


def _check_duplicate_overlap(
    dup_info: dict, changed_line_ranges: dict[str, set[int]]
) -> tuple[bool, bool]:
    """Check if duplicate overlaps with changed lines in either file."""
    first_overlaps = dup_info["first_file"] in changed_line_ranges and ranges_overlap(
        changed_line_ranges[dup_info["first_file"]],
        dup_info["first_start"],
        dup_info["first_end"],
    )
    second_overlaps = dup_info["second_file"] in changed_line_ranges and ranges_overlap(
        changed_line_ranges[dup_info["second_file"]],
        dup_info["second_start"],
        dup_info["second_end"],
    )
    return first_overlaps, second_overlaps


def _format_duplicate_for_output(
    dup_info: dict, first_overlaps: bool, second_overlaps: bool
) -> dict:
    """Format duplicate information for user output."""
    return {
        "file1": dup_info["first_file"],
        "lines1": f"{dup_info['first_start']}-{dup_info['first_end']}",
        "file2": dup_info["second_file"],
        "lines2": f"{dup_info['second_start']}-{dup_info['second_end']}",
        "line_count": dup_info["line_count"],
        "tokens": dup_info["tokens"],
        "fragment": dup_info["fragment"][:100],
        "overlaps_file1": first_overlaps,
        "overlaps_file2": second_overlaps,
    }


def _find_commit_related_duplicates(
    duplicates: list[dict], changed_line_ranges: dict[str, set[int]]
) -> list[dict]:
    """Find duplicates that overlap with changed lines."""
    commit_related = []

    for dup in duplicates:
        dup_info = _build_duplicate_info(dup)
        first_overlaps, second_overlaps = _check_duplicate_overlap(dup_info, changed_line_ranges)

        if first_overlaps or second_overlaps:
            formatted = _format_duplicate_for_output(dup_info, first_overlaps, second_overlaps)
            commit_related.append(formatted)

    return commit_related


def _print_duplicate_report(commit_related_duplicates: list[dict]) -> None:
    """Print formatted duplicate report to console."""
    print(
        f"\n❌ Found {len(commit_related_duplicates)} duplicates overlapping with your changes:\n"
    )
    for i, dup in enumerate(commit_related_duplicates, 1):
        print(f"{i}. {dup['file1']}:{dup['lines1']} ↔ {dup['file2']}:{dup['lines2']}")
        print(f"   {dup['line_count']} lines, {dup['tokens']} tokens")
        if dup["overlaps_file1"] and dup["overlaps_file2"]:
            print("   ⚠️  Both files have changes in duplicate region")
        elif dup["overlaps_file1"]:
            print(f"   ⚠️  Your changes in {dup['file1']} duplicate existing code")
        else:
            print(f"   ⚠️  Your changes in {dup['file2']} duplicate existing code")
        if dup["fragment"]:
            print(f"   Preview: {dup['fragment']}...")
        print()
    print("💡 Tip: Extract duplicated code into shared functions/modules")
    print("💡 Or if this is a false positive, bypass with: SKIP=jscpd-comprehensive git commit")


def main(report_file: str):
    changed_line_ranges = get_changed_line_ranges()

    if not changed_line_ranges:
        print("✅ No source files changed")
        return 0

    total_changed_lines = sum(len(lines) for lines in changed_line_ranges.values())
    print(
        f"Checking {len(changed_line_ranges)} files "
        f"({total_changed_lines} changed lines) against codebase..."
    )

    if not Path(report_file).exists():
        print(f"⚠️  Report file not found: {report_file}")
        return 0

    with open(report_file) as f:
        report = json.load(f)

    duplicates = report.get("duplicates", [])
    commit_related_duplicates = _find_commit_related_duplicates(duplicates, changed_line_ranges)

    if commit_related_duplicates:
        _print_duplicate_report(commit_related_duplicates)
        return 1
    else:
        print("✅ No duplicates found in your changed lines")
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
