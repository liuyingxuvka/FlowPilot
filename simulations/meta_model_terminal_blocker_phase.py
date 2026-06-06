"""Phase helper extracted from :mod:`meta_model`."""

from __future__ import annotations

from typing import Iterable

if __package__:
    from . import meta_model as _model
else:
    import meta_model as _model

_REQUIRED_MODEL_NAMES = (
    "FunctionResult",
    "Iterable",
    "State",
    "_step",
)
for _name in _REQUIRED_MODEL_NAMES:
    globals()[_name] = getattr(_model, _name)
del _name

__all__ = ["apply_terminal_blocker_phase"]


def apply_terminal_blocker_phase(self, state: State) -> Iterable[FunctionResult]:
    yield _step(
        state,
        label="blocked_unhandled_state",
        action="block because no valid transition exists and emit a nonterminal resume notice",
        status="blocked",
        manual_resume_binding_active=False,
        controlled_stop_notice_recorded=True,
        pause_snapshot_written=True,
        active_node="blocked",
    )

