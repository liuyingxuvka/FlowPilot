"""FlowGuard facade for the FlowPilot packet control-plane model."""

from __future__ import annotations

from flowguard import Workflow
from packet_control_plane_model_invariants import INVARIANTS
from packet_control_plane_model_state import *  # noqa: F403
from packet_control_plane_model_transitions import *  # noqa: F403

EXTERNAL_INPUTS = (
    NodeCase("valid_worker_packet", "pass", "worker"),
    NodeCase("cockpit_missing_major_packet", "pass", "worker"),
    NodeCase("missing_physical_files_packet", "block", "worker"),
    NodeCase("controller_handoff_leaks_body_packet", "block", "controller"),
    NodeCase("missing_mutual_reminder_packet", "block", "controller"),
    NodeCase("controller_reads_body_packet", "block", "controller"),
    NodeCase("controller_executes_body_packet", "block", "controller"),
    NodeCase("missing_current_assignment_packet", "block", "worker"),
    NodeCase("private_delivery_packet", "block", "worker"),
    NodeCase("unopened_packet", "block", "worker"),
    NodeCase("packet_open_envelope_only_packet", "block", "worker"),
    NodeCase("packet_open_ledger_only_packet", "block", "worker"),
    NodeCase("wrong_delivery_packet", "block", "worker"),
    NodeCase("body_hash_mismatch_packet", "block", "worker"),
    NodeCase("body_hash_identity_stale_packet", "block", "worker"),
    NodeCase("stale_packet_body_packet", "block", "worker"),
    NodeCase("missing_output_contract_packet", "block", "worker"),
    NodeCase("contract_recipient_mismatch_packet", "block", "worker"),
    NodeCase("result_path_escape_packet", "block", "worker"),
    NodeCase("controller_origin_packet", "pass", "controller"),
    NodeCase("result_wrong_role_packet", "block", "human_like_reviewer"),
    NodeCase("agent_id_role_string_packet", "block", "worker"),
    NodeCase("invalid_agent_id_packet", "block", "worker"),
    NodeCase("result_without_ledger_packet", "block", "worker"),
    NodeCase("missing_result_current_assignment_packet", "block", "worker"),
    NodeCase("missing_result_mutual_reminder_packet", "block", "worker"),
    NodeCase("unopened_result_packet", "block", "worker"),
    NodeCase("result_open_envelope_only_packet", "block", "worker"),
    NodeCase("result_open_ledger_only_packet", "block", "worker"),
    NodeCase("result_body_hash_mismatch_packet", "block", "worker"),
    NodeCase("stale_result_body_packet", "block", "worker"),
    NodeCase("missing_reminder_packet", "pass", "worker"),
    HeartbeatCase("heartbeat_valid_packet"),
    HeartbeatCase("heartbeat_missing_state"),
    HeartbeatCase("heartbeat_ambiguous_worker_state"),
    HeartbeatCase("heartbeat_worker_result_pending_review"),
    HeartbeatCase("heartbeat_missing_reminder"),
)

def initial_state() -> State:
    return State()

def terminal_predicate(current_output, state, trace) -> bool:
    del state, trace
    return isinstance(current_output, (PMAdvanced, PMRepairRequired, DispatchBlocked))

def build_workflow() -> Workflow:
    return Workflow(
        (
            PMIssuePacket(),
            HeartbeatResumeLoad(),
            ControllerAskPMOnResume(),
            PMResumeDecision(),
            PacketRuntimeWrite(),
            ControllerReminderCheck(),
            ControllerEnvelopeOnlyHandoff(),
            ControllerEnvelopeRelay(),
            RouterDirectDispatch(),
            WorkerOrControllerResult(),
            ControllerResultRelay(),
            ReviewerResultEnvelopeCheck(),
            ReviewerResult(),
            PMRepairAfterInvalidOrigin(),
            PMAdvance(),
        ),
        name="flowpilot_packet_control_plane",
    )
