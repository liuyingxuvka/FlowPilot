"""Compatibility facade for FlowPilot router controller scheduler ledgers."""

from __future__ import annotations

from types import ModuleType

import flowpilot_router_controller_scheduler_ledgers_actions as _ledger_child_actions
import flowpilot_router_controller_scheduler_ledgers_ownership as _ledger_child_ownership
import flowpilot_router_controller_scheduler_ledgers_scheduler as _ledger_child_scheduler
from flowpilot_router_controller_scheduler_ledgers_actions import (
    _controller_action_completion_class,
    _controller_action_ledger_has_prompt_header,
    _controller_action_ledger_summary,
    _ensure_controller_action_ledger,
    _rebuild_controller_action_ledger,
    _write_controller_action_ledger,
)
from flowpilot_router_controller_scheduler_ledgers_ownership import (
    _empty_router_ownership_ledger,
    _ensure_router_ownership_ledger,
    _read_router_ownership_ledger,
    _record_router_ownership_entry,
    _router_ownership_counts,
    _router_ownership_ledger_summary,
    _write_router_ownership_ledger,
)
from flowpilot_router_controller_scheduler_ledgers_scheduler import (
    _action_is_startup_scoped,
    _controller_action_open_for,
    _empty_router_scheduler_ledger,
    _ensure_router_scheduler_ledger,
    _prepare_router_scheduled_action,
    _read_router_scheduler_ledger,
    _record_router_scheduler_row,
    _router_scheduler_barrier_kind,
    _router_scheduler_ledger_summary,
    _router_scheduler_progress_class,
    _router_scheduler_scope_for_action,
    _update_router_scheduler_row,
    _write_router_scheduler_ledger,
)

_LEDGER_CHILD_MODULES = (
    _ledger_child_scheduler,
    _ledger_child_ownership,
    _ledger_child_actions,
)


def _bind_router(router: ModuleType) -> None:
    for child_module in _LEDGER_CHILD_MODULES:
        child_module._bind_router(router)


__all__ = (
    '_empty_router_scheduler_ledger',
    '_read_router_scheduler_ledger',
    '_write_router_scheduler_ledger',
    '_ensure_router_scheduler_ledger',
    '_router_scheduler_ledger_summary',
    '_router_scheduler_scope_for_action',
    '_action_is_startup_scoped',
    '_router_scheduler_progress_class',
    '_router_scheduler_barrier_kind',
    '_prepare_router_scheduled_action',
    '_record_router_scheduler_row',
    '_update_router_scheduler_row',
    '_controller_action_open_for',
    '_router_ownership_counts',
    '_empty_router_ownership_ledger',
    '_read_router_ownership_ledger',
    '_write_router_ownership_ledger',
    '_ensure_router_ownership_ledger',
    '_router_ownership_ledger_summary',
    '_record_router_ownership_entry',
    '_controller_action_completion_class',
    '_controller_action_ledger_has_prompt_header',
    '_write_controller_action_ledger',
    '_rebuild_controller_action_ledger',
    '_ensure_controller_action_ledger',
    '_controller_action_ledger_summary',
)

_LOCAL_NAMES = set(globals())
