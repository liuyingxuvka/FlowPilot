"""Public runner facade for `run_meta_checks.py`."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path
from typing import Sequence

import meta_checks_runner_impl as _impl

RESULTS_PATH = getattr(_impl, "RESULTS_PATH", None)
_IMPL_DIR = Path(__file__).resolve().parent
_SYNC_NAMES = (
    "RESULTS_PATH",
    "PROOF_PATH",
    "LAYERED_RESULTS_PATH",
    "LAYERED_PROOF_PATH",
    "_run_sharded_graph_checks",
)

for _name in dir(_impl):
    if not (_name.startswith("__") and _name.endswith("__")):
        globals()[_name] = getattr(_impl, _name)


def _sync_impl_state() -> None:
    for name in _SYNC_NAMES:
        if name in globals():
            setattr(_impl, name, globals()[name])


def _sync_public_state() -> None:
    for name in _SYNC_NAMES:
        if hasattr(_impl, name):
            globals()[name] = getattr(_impl, name)


def _call_impl(func, *args, **kwargs):
    _sync_impl_state()
    old_path = list(sys.path)
    if str(_IMPL_DIR) not in sys.path:
        sys.path.insert(0, str(_IMPL_DIR))
    try:
        return func(*args, **kwargs)
    finally:
        sys.path[:] = old_path
        _sync_public_state()


def _current_input_fingerprint() -> str:
    return _call_impl(_impl._current_input_fingerprint)


def _valid_proof(input_fingerprint: str) -> tuple[bool, str]:
    return _call_impl(_impl._valid_proof, input_fingerprint)


def _write_proof(*, ok: bool, input_fingerprint: str) -> None:
    return _call_impl(_impl._write_proof, ok=ok, input_fingerprint=input_fingerprint)


def _valid_layered_proof(input_fingerprint: str) -> tuple[bool, str]:
    return _call_impl(_impl._valid_layered_proof, input_fingerprint)


def main(argv: Sequence[str] | None = None) -> int:
    signature = inspect.signature(_impl.main)
    if signature.parameters:
        return _call_impl(_impl.main, None if argv is None else list(argv))
    if argv is None:
        return _call_impl(_impl.main)
    old_argv = sys.argv[:]
    try:
        sys.argv = [__file__, *list(argv)]
        return _call_impl(_impl.main)
    finally:
        sys.argv = old_argv


if __name__ == "__main__":
    raise SystemExit(main())
