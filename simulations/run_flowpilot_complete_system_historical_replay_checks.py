"""Replay historical FlowPilot failure families against the complete runtime."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:  # pragma: no cover
    from . import run_flowpilot_complete_system_runtime_checks as runtime_checks
except ImportError:  # pragma: no cover
    import run_flowpilot_complete_system_runtime_checks as runtime_checks


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_complete_system_historical_replay_results.json"

REQUIRED_REPLAY_IDS = (
    "ack_only_or_dead_worker_not_completion",
    "stale_display_projection_not_authority",
    "stale_unowned_old_artifact_not_authority",
    "wrong_flowguard_target_not_gate_evidence",
    "stale_result_artifact_not_gate_evidence",
    "duplicate_result_not_authority",
    "cockpit_disconnect_uses_chat_route_sign",
    "progress_only_background_not_release",
)


def run_checks() -> dict[str, Any]:
    runtime_report = runtime_checks.run_checks()
    scenarios = {item["name"]: item for item in runtime_report["scenarios"]}
    rows = [
        {
            "replay_id": "ack_only_or_dead_worker_not_completion",
            "source_class": "lease_liveness",
            "status": "passed" if scenarios["dead_worker_replaced"]["ok"] else "failed",
            "evidence": "dead_worker_replaced",
        },
        {
            "replay_id": "stale_display_projection_not_authority",
            "source_class": "display_projection",
            "status": "passed" if scenarios["cockpit_direct_write_rejected"]["ok"] else "failed",
            "evidence": "cockpit_direct_write_rejected",
        },
        {
            "replay_id": "stale_unowned_old_artifact_not_authority",
            "source_class": "old_state_replay",
            "status": "passed" if scenarios["imported_old_artifact_is_read_only"]["ok"] else "failed",
            "evidence": "imported_old_artifact_is_read_only",
        },
        {
            "replay_id": "wrong_flowguard_target_not_gate_evidence",
            "source_class": "flowguard_target",
            "status": "passed" if scenarios["wrong_flowguard_target_blocks_complete_system"]["ok"] else "failed",
            "evidence": "wrong_flowguard_target_blocks_complete_system",
        },
        {
            "replay_id": "stale_result_artifact_not_gate_evidence",
            "source_class": "stale_proof",
            "status": "passed" if scenarios["stale_proof_artifact_blocks_review"]["ok"] else "failed",
            "evidence": "stale_proof_artifact_blocks_review",
        },
        {
            "replay_id": "duplicate_result_not_authority",
            "source_class": "duplicate_output",
            "status": "passed" if scenarios["duplicate_output_blocks_second_result"]["ok"] else "failed",
            "evidence": "duplicate_output_blocks_second_result",
        },
        {
            "replay_id": "cockpit_disconnect_uses_chat_route_sign",
            "source_class": "display_surface_fallback",
            "status": "passed" if scenarios["cockpit_disconnect_records_chat_fallback"]["ok"] else "failed",
            "evidence": "cockpit_disconnect_records_chat_fallback",
        },
        {
            "replay_id": "progress_only_background_not_release",
            "source_class": "release_evidence",
            "status": "passed" if not runtime_report["test_mesh"]["release_gate"]["ok"] else "failed",
            "evidence": "complete_runtime_release_boundary",
        },
    ]
    return {
        "result_type": "flowpilot_complete_system_historical_replay_checks",
        "ok": all(row["status"] == "passed" for row in rows),
        "required_replay_ids": list(REQUIRED_REPLAY_IDS),
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    parser.add_argument("--no-write-results", action="store_true")
    args = parser.parse_args()

    result = run_checks()
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(output, end="")
    if not args.no_write_results:
        args.json_out.write_text(output, encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
