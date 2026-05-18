"""Compatibility facade for controller deliverable repair helpers.

The behavior lives in focused child modules, while this module preserves the
legacy private import surface used by ``flowpilot_router`` and direct imports.
"""

from __future__ import annotations

from types import ModuleType

import flowpilot_router_controller_repair_deliverable_contracts as _controller_repair_deliverable_contracts
import flowpilot_router_controller_repair_deliverable_projection as _controller_repair_deliverable_projection
import flowpilot_router_controller_repair_deliverable_resolution as _controller_repair_deliverable_resolution

from flowpilot_router_controller_repair_deliverable_contracts import (
    _controller_boundary_required_deliverable,
    _controller_action_required_deliverables,
    _controller_deliverable_contract,
    _missing_deliverables_for_apply_result,
)
from flowpilot_router_controller_repair_deliverable_projection import (
    _update_controller_action_entry_fields,
    _defer_controller_postcondition_reconciliation_retry,
    _sync_controller_boundary_confirmation_from_artifact,
    _controller_boundary_flags_synced,
    _router_scheduler_row_for_controller_entry,
    _done_controller_receipt_for_entry,
    _reconcile_controller_boundary_confirmation_projection,
)
from flowpilot_router_controller_repair_deliverable_resolution import (
    _mark_controller_deliverable_repair_resolved,
    _controller_deliverable_failed_repair_ids,
    _controller_repair_action_is_pending,
    _write_controller_deliverable_budget_blocker,
)

_CHILD_MODULES = (_controller_repair_deliverable_contracts, _controller_repair_deliverable_projection, _controller_repair_deliverable_resolution,)

OWNER_MODULE = "flowpilot_router_controller_repair"

def _bind_router(router: ModuleType) -> None:
    for child_module in _CHILD_MODULES:
        child_module._bind_router(router)

__all__ = (
    '_controller_boundary_required_deliverable',
    '_controller_action_required_deliverables',
    '_controller_deliverable_contract',
    '_missing_deliverables_for_apply_result',
    '_update_controller_action_entry_fields',
    '_defer_controller_postcondition_reconciliation_retry',
    '_sync_controller_boundary_confirmation_from_artifact',
    '_controller_boundary_flags_synced',
    '_router_scheduler_row_for_controller_entry',
    '_done_controller_receipt_for_entry',
    '_reconcile_controller_boundary_confirmation_projection',
    '_mark_controller_deliverable_repair_resolved',
    '_controller_deliverable_failed_repair_ids',
    '_controller_repair_action_is_pending',
    '_write_controller_deliverable_budget_blocker',
)

_LOCAL_NAMES = set(globals())
