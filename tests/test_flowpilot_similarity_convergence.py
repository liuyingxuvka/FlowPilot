from __future__ import annotations

import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIMULATIONS = ROOT / "simulations"
if str(SIMULATIONS) not in sys.path:
    sys.path.insert(0, str(SIMULATIONS))

import flowpilot_similarity_convergence_model as model  # noqa: E402
import run_flowpilot_similarity_convergence_checks as runner  # noqa: E402


class FlowPilotSimilarityConvergenceTests(unittest.TestCase):
    def test_similarity_convergence_report_is_green_and_has_groups(self) -> None:
        report = model.build_report()

        self.assertTrue(report["ok"], report)
        self.assertTrue(report["similarity_ok"])
        self.assertTrue(report["existing_model_preflight_ok"])
        self.assertTrue(report["architecture_reduction_ok"])
        self.assertTrue(report["known_bad_ok"])
        self.assertGreaterEqual(report["summary"]["maintenance_group_count"], 4)

        group_ids = {
            group["group_id"]
            for group in report["similarity_review"]["maintenance_groups"]
        }
        self.assertTrue(any("packet_result_research" in group_id for group_id in group_ids))
        self.assertTrue(any("ack_single_card_return" in group_id for group_id in group_ids))

        false_friend_rationales = report["similarity_handoff"]["false_friend_rationales"]
        self.assertTrue(
            any("route_display_refresh" in rationale for rationale in false_friend_rationales)
        )

    def test_known_bad_cases_are_rejected(self) -> None:
        report = model.build_report()
        self.assertTrue(report["known_bad_ok"])
        rejected = {case["name"]: case for case in report["known_bad_sanity_checks"]}
        self.assertEqual(
            {
                "missing_maintenance_test_path",
                "stale_model_signature_evidence",
                "missing_current_similarity_evidence",
                "unsafe_branch_fold_without_replay",
            },
            set(rejected),
        )
        for case in rejected.values():
            self.assertTrue(case["ok"], case)

    def test_runner_writes_json_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "similarity.json"
            with redirect_stdout(StringIO()):
                exit_code = runner.main(["--json-out", str(output_path)])

            self.assertEqual(exit_code, 0)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertTrue(payload["ok"], payload)
            self.assertEqual(payload["result_type"], model.RESULT_TYPE)


if __name__ == "__main__":
    unittest.main()
