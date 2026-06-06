"""Public facade for Controller scheduler receipt helpers.

This public facade preserves the original import path while focused
child modules own the implementation groups.
"""

from __future__ import annotations

from types import ModuleType


_BOUND_ROUTER: ModuleType | None = None
def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    if _BOUND_ROUTER is router:
        return
    _BOUND_ROUTER = router
    current = globals()
    local_names = current.get('_LOCAL_NAMES', set())
    for name, value in vars(router).items():
        if name.startswith('__') and name.endswith('__'):
            continue
        if name in local_names:
            continue
        current[name] = value
    for child_module in globals().get("_OWNER_CHILD_MODULES", ()):
        if hasattr(child_module, "_bind_router"):
            child_module._bind_router(router)


import flowpilot_router_controller_scheduler_receipts_writes as _owner_child_0
import flowpilot_router_controller_scheduler_receipts_effects as _owner_child_1
import flowpilot_router_controller_scheduler_receipts_pending as _owner_child_2
import flowpilot_router_controller_scheduler_receipts_scheduled as _owner_child_3
import flowpilot_router_controller_scheduler_receipts_packet_folds as _owner_child_4
from flowpilot_router_controller_scheduler_receipts_writes import *
from flowpilot_router_controller_scheduler_receipts_effects import *
from flowpilot_router_controller_scheduler_receipts_pending import *
from flowpilot_router_controller_scheduler_receipts_scheduled import *
from flowpilot_router_controller_scheduler_receipts_packet_folds import *

_OWNER_CHILD_MODULES = (
    _owner_child_0,
    _owner_child_1,
    _owner_child_2,
    _owner_child_3,
    _owner_child_4,
)

__all__ = (
    '_write_controller_action_entry',
    '_write_controller_receipt',
    '_maybe_write_controller_receipt_for_pending',
    '_reconcile_controller_receipts',
    '_apply_stateful_receipt_postcondition',
    '_pending_return_matches_wait_target_reminder',
    '_mark_pending_return_wait_reminded',
    '_apply_wait_target_reminder_receipt',
    '_boot_action_meta',
    '_matching_bootstrap_pending_action',
    '_apply_startup_bootloader_receipt_effects',
    '_apply_done_controller_receipt_effects',
    'CONTROLLER_RECEIPT_EVIDENCE_FOLD_REGISTRY',
    '_registered_controller_receipt_evidence_fold_actions',
    '_apply_registered_controller_receipt_evidence_fold',
    '_router_scheduler_row_for_controller_entry',
    '_done_controller_receipt_for_entry',
    '_clear_pending_after_reconciled_controller_receipt',
    '_apply_controller_repair_work_packet_receipt',
    '_reconcile_pending_controller_action_receipt',
    '_scheduler_row_reconciliation_for_entry',
    '_backfill_scheduler_row_from_reconciled_controller_action',
    '_clear_pending_controller_action_if_matches',
    '_reconcile_scheduled_controller_action_receipts',
)

_LOCAL_NAMES = set(globals())
