from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from flowguard import Explorer  # noqa: E402

import packet_control_plane_model as model  # noqa: E402


def main() -> int:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=1,
        terminal_predicate=model.terminal_predicate,
        required_labels=(
            "pm_packet_issued",
            "controller_reminder_checked",
            "controller_missing_pm_reminder",
            "reviewer_dispatch_approved",
            "worker_result",
            "review_pass",
            "pm_advanced",
            "review_block_invalid_role_origin",
            "reviewer_dispatch_blocked",
            "heartbeat_state_loaded",
            "heartbeat_resume_pm_requested",
            "heartbeat_pm_packet_issued",
            "heartbeat_pm_missing_controller_reminder",
            "heartbeat_loaded_worker_result_for_review",
            "heartbeat_ambiguous_worker_blocked",
            "heartbeat_missing_state_blocked",
        ),
    ).explore()
    print(report.format_text())
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
