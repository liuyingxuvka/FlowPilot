from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS_ROOT = ROOT / "skills" / "flowpilot" / "assets"
sys.path.insert(0, str(ASSETS_ROOT))

from flowpilot_core_runtime import packet_result_contracts, runtime  # noqa: E402


class FlowPilotReviewerQualityMeshTests(unittest.TestCase):
    def test_terminal_contract_is_five_field_quality_replay_not_legacy_review_shape(self) -> None:
        required = packet_result_contracts.required_fields_for_family("review.terminal_backward_replay")
        forbidden = packet_result_contracts.forbidden_fields_for_family("review.terminal_backward_replay")

        self.assertEqual(
            required,
            (
                "final_artifact_refs",
                "acceptance_item_closure",
                "route_segment_replay",
                "waiver_records",
                "final_blockers",
            ),
        )
        for old_field in (
            "pm_visible_summary",
            "reviewed_by_role",
            "passed",
            "findings",
            "blockers",
            "pm_suggestion_items",
            "contract_self_check",
        ):
            self.assertIn(old_field, forbidden)

    def test_terminal_replay_rejects_legacy_summary_pass_fields(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        runtime.create_route(ledger, "Route", ["Do work"])
        targets = runtime._terminal_backward_replay_segment_targets(ledger)  # noqa: SLF001
        packet_id = runtime.issue_task_packet(
            ledger,
            "reviewer",
            "Terminal replay",
            json.dumps({"segment_targets": targets}),
            packet_kind="review",
            route_scope=runtime.TERMINAL_BACKWARD_REPLAY_SCOPE,
        )
        packet = ledger["packets"][packet_id]
        payload = packet_result_contracts.minimal_valid_shape_for_family("review.terminal_backward_replay")
        payload["route_segment_replay"] = [
            {
                "segment_id": target["segment_id"],
                "segment_kind": target["segment_kind"],
                "status": "closed",
                "basis": "Current evidence closes this segment.",
            }
            for target in targets
        ]
        payload["pm_visible_summary"] = ["old field must be rejected"]
        payload["passed"] = True

        check = runtime._terminal_backward_replay_result_violation(packet, {"body": json.dumps(payload)})  # noqa: SLF001

        self.assertFalse(check.ok)
        self.assertIn("pm_visible_summary", check.forbidden_fields_seen)
        self.assertIn("passed", check.forbidden_fields_seen)


if __name__ == "__main__":
    unittest.main()
