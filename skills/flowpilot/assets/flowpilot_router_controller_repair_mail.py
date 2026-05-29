"""Public facade for controller repair mail helpers.

The behavior lives in focused child modules, while this module preserves the
router binding surface used by ``flowpilot_router`` and direct imports.
"""

from __future__ import annotations

from types import ModuleType

import flowpilot_router_controller_repair_mail_pending as _controller_repair_mail_pending
import flowpilot_router_controller_repair_mail_delivery as _controller_repair_mail_delivery
import flowpilot_router_controller_repair_mail_postconditions as _controller_repair_mail_postconditions

from flowpilot_router_controller_repair_mail_pending import (
    _close_waiting_controller_actions_for_external_event,
    _pending_controller_action_id,
    _pending_action_postcondition,
    _receipt_for_pending_controller_action,
    _pending_action_postcondition_satisfied,
)
from flowpilot_router_controller_repair_mail_delivery import (
    _mail_sequence_entry,
    _mail_role_obligation_contract,
    _mail_delivery_matches,
    _find_mail_delivery,
    _count_unique_mail_deliveries,
    _packet_record_for_mail_delivery,
    _mail_delivery_action_envelope_path,
    _mail_delivery_packet_released,
    _ensure_mail_delivery_packet_released,
)
from flowpilot_router_controller_repair_mail_postconditions import (
    _fold_mail_delivery_postcondition,
)

_CHILD_MODULES = (_controller_repair_mail_pending, _controller_repair_mail_delivery, _controller_repair_mail_postconditions,)

OWNER_MODULE = "flowpilot_router_controller_repair"

def _bind_router(router: ModuleType) -> None:
    for child_module in _CHILD_MODULES:
        child_module._bind_router(router)

__all__ = (
    '_close_waiting_controller_actions_for_external_event',
    '_pending_controller_action_id',
    '_pending_action_postcondition',
    '_receipt_for_pending_controller_action',
    '_pending_action_postcondition_satisfied',
    '_mail_sequence_entry',
    '_mail_role_obligation_contract',
    '_mail_delivery_matches',
    '_find_mail_delivery',
    '_count_unique_mail_deliveries',
    '_packet_record_for_mail_delivery',
    '_mail_delivery_action_envelope_path',
    '_mail_delivery_packet_released',
    '_ensure_mail_delivery_packet_released',
    '_fold_mail_delivery_postcondition',
)

_LOCAL_NAMES = set(globals())
