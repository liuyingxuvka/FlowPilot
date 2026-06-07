"""Role-facing controller-action handler facade."""

from __future__ import annotations

from flowpilot_router_action_handlers_role_binding import *
from flowpilot_router_action_handlers_role_misc import *
from flowpilot_router_action_handlers_resume import *

__all__ = (
    "CURRENT_ROLE_AGENT_BINDING_PAYLOAD_FIELD",
    "CURRENT_ROLE_AGENT_BINDING_RESULT",
    "_normalize_current_role_agent_binding",
    "_write_current_role_agent_binding",
    "_apply_open_current_role_agent",
    "_apply_inject_role_io_protocol",
    "_apply_deliver_mail",
    "_apply_controller_repair_work_packet",
    "_apply_load_role_recovery_state",
    "_apply_recover_role_bindings",
    "_apply_load_resume_state",
    "_apply_rehydrate_role_bindings",
    "_apply_write_display_surface_status",
    "_apply_handle_control_blocker",
)
