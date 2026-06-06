"""Public facade for packet control-plane transition definitions."""

from __future__ import annotations

from dataclasses import dataclass, replace

from flowguard import FunctionResult
from packet_control_plane_model_state import (
    ApprovedPacket,
    CheckedResult,
    DispatchBlocked,
    ManualResumeCase,
    NodeCase,
    NodePacket,
    NodeResult,
    PMAdvanced,
    PMRepairRequired,
    ResumeRequest,
    ReviewBlock,
    ReviewPass,
    State,
    _packet_from_id,
)
from packet_control_plane_model_transitions_dispatch_results import (
    ControllerResultRelay,
    RouterDirectDispatch,
    WorkerOrControllerResult,
)
from packet_control_plane_model_transitions_issue_resume import (
    ControllerAskPMOnResume,
    ManualResumeLoad,
    PMIssuePacket,
    PMResumeDecision,
)
from packet_control_plane_model_transitions_packet_relay import (
    ControllerEnvelopeOnlyHandoff,
    ControllerEnvelopeRelay,
    ControllerReminderCheck,
    PacketRuntimeWrite,
)
from packet_control_plane_model_transitions_review_pm import (
    PMAdvance,
    PMRepairAfterInvalidOrigin,
    ReviewerResult,
    RuntimeResultEnvelopeCheck,
)

__all__ = [
    "PMIssuePacket",
    "ManualResumeLoad",
    "ControllerAskPMOnResume",
    "PMResumeDecision",
    "PacketRuntimeWrite",
    "ControllerReminderCheck",
    "ControllerEnvelopeOnlyHandoff",
    "ControllerEnvelopeRelay",
    "RouterDirectDispatch",
    "WorkerOrControllerResult",
    "ControllerResultRelay",
    "RuntimeResultEnvelopeCheck",
    "ReviewerResult",
    "PMRepairAfterInvalidOrigin",
    "PMAdvance",
]
