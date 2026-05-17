"""Phase helper extracted from :mod:`capability_model`."""

from __future__ import annotations

from typing import Iterable

if __package__:
    from . import capability_model as _model
else:
    import capability_model as _model

_REQUIRED_MODEL_NAMES = (
    "FunctionResult",
    "Iterable",
    "State",
    "_step",
)
for _name in _REQUIRED_MODEL_NAMES:
    globals()[_name] = getattr(_model, _name)
del _name

__all__ = ["apply_closure_phase"]


def apply_closure_phase(self, state: State) -> Iterable[FunctionResult]:
    yield _step(
        state,
        label="blocked_unknown_task_kind",
        action="block because task kind is unknown and emit a nonterminal resume notice",
        status="blocked",
        controlled_stop_notice_recorded=True,
        pause_snapshot_written=True,
    )
