from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS_ROOT = ROOT / "skills" / "flowpilot" / "assets"
RUNTIME_ROOT = ASSETS_ROOT / "flowpilot_core_runtime"
sys.path.insert(0, str(ASSETS_ROOT))


def load_runtime():
    spec = importlib.util.spec_from_file_location("flowpilot_runtime_breakglass_mesh", RUNTIME_ROOT / "runtime.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    sys.path.insert(0, str(RUNTIME_ROOT))
    sys.path.insert(0, str(ASSETS_ROOT))
    spec.loader.exec_module(module)
    return module


runtime = load_runtime()


def ledger_with_repair_blockers(count: int, *, verified_recovery_at: int | None = None) -> tuple[dict, str]:
    ledger = runtime.new_ledger("Goal", "Contract")
    runtime.create_route(ledger, "Route", ["Do work"])
    root_cause_key = runtime._flowguard_missing_evidence_root_cause_key(  # noqa: SLF001
        subject_packet_id="packet-subject",
        target_result_id="result-subject",
        repair_blocker_id="",
    )
    last_id = ""
    for index in range(count):
        blocker_id = f"blocker-root-{index}"
        row = {
            "blocker_id": blocker_id,
            "status": "active",
            "gate_kind": "flowguard_review_handoff",
            "blocker_class": "missing_matching_flowguard_report",
            "required_recheck_role": "flowguard_operator",
            "repair_target_packet_id": "packet-subject",
            "target_result_id": "result-subject",
            "root_cause_loop_key": root_cause_key,
        }
        if verified_recovery_at is not None and index == verified_recovery_at:
            row["lineage_verified_closed_by"] = "normal-business-node"
        ledger["active_blockers"][blocker_id] = row
        last_id = blocker_id
    return ledger, last_id


class FlowPilotBreakGlassMeshTests(unittest.TestCase):
    def test_repair_loop_threshold_matrix_routes_first_four_to_pm_and_fifth_to_break_glass(self) -> None:
        for count in (1, 2, 3, 4, 5, 6):
            with self.subTest(count=count):
                ledger, blocker_id = ledger_with_repair_blockers(count)
                review = runtime._repair_loop_break_glass_review(ledger, ledger["active_blockers"][blocker_id])  # noqa: SLF001

                self.assertEqual(review["attempt_count"], count)
                self.assertEqual(review["threshold_exceeded"], count >= 5)
                self.assertEqual(
                    review["required_action"],
                    "controller_break_glass_diagnosis" if count >= 5 else "ordinary_pm_repair_allowed",
                )

    def test_verified_normal_recovery_resets_repair_loop_threshold(self) -> None:
        ledger, blocker_id = ledger_with_repair_blockers(6, verified_recovery_at=2)
        review = runtime._repair_loop_break_glass_review(ledger, ledger["active_blockers"][blocker_id])  # noqa: SLF001

        self.assertFalse(review["threshold_exceeded"])
        self.assertEqual(review["required_action"], "ordinary_pm_repair_allowed")
        self.assertTrue(review["verified_recovery_before_current_blocker"])


if __name__ == "__main__":
    unittest.main()
