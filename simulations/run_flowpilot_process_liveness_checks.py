"""Compatibility facade for `run_flowpilot_process_liveness_checks.py`."""

from __future__ import annotations

import inspect
import sys
from typing import Sequence

import flowpilot_process_liveness_checks_runner_impl as _impl

RESULTS_PATH = getattr(_impl, "RESULTS_PATH", None)

for _name in dir(_impl):
    if not (_name.startswith("__") and _name.endswith("__")):
        globals()[_name] = getattr(_impl, _name)


def main(argv: Sequence[str] | None = None) -> int:
    signature = inspect.signature(_impl.main)
    if signature.parameters:
        return _impl.main(None if argv is None else list(argv))
    if argv is None:
        return _impl.main()
    old_argv = sys.argv[:]
    try:
        sys.argv = [__file__, *list(argv)]
        return _impl.main()
    finally:
        sys.argv = old_argv


if __name__ == "__main__":
    raise SystemExit(main())
