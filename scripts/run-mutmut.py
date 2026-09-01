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


"""Run mutmut via a launcher that avoids its import-time fork crash.

Usage:
    .venv/bin/python scripts/run-mutmut.py run                      # full cold run
    .venv/bin/python scripts/run-mutmut.py run '<wildcard>'         # scoped run
    .venv/bin/python scripts/run-mutmut.py <any other mutmut CLI args>

Why a wrapper: mutmut 3.x calls multiprocessing.set_start_method('fork') at the
module scope of __main__.py without a guard, and each mutant's trampoline lazily
executes ``from mutmut.__main__ import record_trampoline_hit`` on first hit. When
launched with ``python -m mutmut``, the CLI body is registered in sys.modules as
'__main__', so that dotted import re-executes the entire module inside the live
process and raises RuntimeError("context has already been set") -- but only when
imported code calls an in-scope function at import time (FastAPI routes evaluate
Depends(...) during decorator application). This wrapper imports the side-effect-
free package first (shared stats globals such as config and duration_by_test live
in it), then execs __main__.py once under its real dotted name after pre-seeding
sys.modules["mutmut.__main__"]. The cache is present before any trampoline fires,
and forked test workers inherit it, so no process ever re-runs the startup code.
"""

import importlib.util
import sys
from pathlib import Path

# Package import is safe (it only reads the version and declares empty module-level
# stat containers) and required: those shared globals live in the package, are read
# by mutant trampolines, and __main__.py must come from the same distribution.
import mutmut


def _load_mutmut_main_as_dotted_module() -> None:
    """Exec mutmut/__main__.py exactly once, cached under its proper dotted name."""
    pkg_spec = importlib.util.find_spec("mutmut")
    if pkg_spec is None or not pkg_spec.submodule_search_locations:
        message = "mutmut package not found in this environment"
        raise SystemExit(message)
    package_root = Path(next(iter(pkg_spec.submodule_search_locations)))
    # Guard: load __main__.py from the very distribution whose package globals the
    # trampolines will resolve to; a mismatch would silently split state between them.
    if package_root != Path(mutmut.__file__).parent:
        message = f"mutmut distribution mismatch: {mutmut.__file__} vs {package_root}"
        raise SystemExit(message)
    main_path = package_root / "__main__.py"

    spec = importlib.util.spec_from_file_location("mutmut.__main__", main_path)
    if spec is None or spec.loader is None:
        message = f"could not locate {main_path}"
        raise SystemExit(message)
    module = importlib.util.module_from_spec(spec)
    sys.modules["mutmut.__main__"] = module  # cache before exec; this is the fix
    spec.loader.exec_module(module)  # startup code runs exactly once under its dotted name
    # The trailing `if __name__ == '__main__': cli()` guard does not fire for a
    # dotted-name load, so dispatch the CLI entry point ourselves.
    module.cli()


def main() -> int:
    sys.argv[0] = "mutmut"  # cosmetic; the CLI parses sys.argv[1:] itself
    _load_mutmut_main_as_dotted_module()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
