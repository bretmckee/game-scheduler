# Changes: GitHub Actions CI/CD Pipeline

Tracks changes made while implementing `.copilot-tracking/planning/plans/20260329-01-github-actions-ci-cd.plan.md`.

---

## Added

- `tests/unit/scripts/test_check_commit_duplicates.py` — new unit tests covering `get_changed_line_ranges()` diff-source selection and `main()` `compare_branch` passthrough (Task 1.1)

## Modified

- `pyproject.toml` — added `pathspec>=0.12.0` to `[dependency-groups] dev` (required by `check_commit_duplicates.py` script used in pre-commit)
- `scripts/check_commit_duplicates.py` — added optional `compare_branch` parameter to `get_changed_line_ranges()` and `main()`; added `--compare-branch` argparse argument to `__main__` entry point (Task 1.2)
