from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS_ROOT = ROOT / "skills" / "flowpilot" / "assets"
RUNTIME_ROOT = ASSETS_ROOT / "flowpilot_core_runtime"
sys.path.insert(0, str(ASSETS_ROOT))


def load_runtime():
    spec = importlib.util.spec_from_file_location("flowpilot_runtime_terminal_coverage_mesh", RUNTIME_ROOT / "runtime.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    sys.path.insert(0, str(RUNTIME_ROOT))
    sys.path.insert(0, str(ASSETS_ROOT))
    spec.loader.exec_module(module)
    return module


runtime = load_runtime()


class FlowPilotTerminalCoverageMeshTests(unittest.TestCase):
    def test_terminal_segment_targets_always_include_flowguard_coverage_governance(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        runtime.create_route(ledger, "Route", ["Do work"])

        targets = runtime._terminal_backward_replay_segment_targets(ledger)  # noqa: SLF001

        self.assertIn("flowguard-coverage-governance", [target["segment_id"] for target in targets])

    def test_terminal_replay_cannot_skip_flowguard_coverage_governance_segment(self) -> None:
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
        payload = {
            "final_artifact_refs": [
                {"id": "delivered-product", "status": "closed", "basis": "Directly inspected."}
            ],
            "acceptance_item_closure": [
                {"id": "acc-001", "status": "closed", "basis": "Current acceptance evidence."}
            ],
            "route_segment_replay": [
                {
                    "segment_id": target["segment_id"],
                    "segment_kind": target["segment_kind"],
                    "status": "closed",
                    "basis": "Current evidence closes this segment.",
                }
                for target in targets
                if target["segment_id"] != "flowguard-coverage-governance"
            ],
            "waiver_records": [],
            "final_blockers": [],
        }

        check = runtime._terminal_backward_replay_result_violation(packet, {"body": json.dumps(payload)})  # noqa: SLF001

        self.assertFalse(check.ok)
        self.assertIn("flowguard-coverage-governance", check.blocked_reason)


if __name__ == "__main__":
    unittest.main()
