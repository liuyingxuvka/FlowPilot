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


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    sys.path.insert(0, str(path.parent))
    sys.path.insert(0, str(ASSETS_ROOT))
    spec.loader.exec_module(module)
    return module


runtime = load_module("flowpilot_runtime_identity_owner_mesh", RUNTIME_ROOT / "runtime.py")
runtime_runner = load_module(
    "flowpilot_runtime_runner_identity_owner_mesh",
    ROOT / "simulations" / "run_flowpilot_core_runtime_checks.py",
)


def role_result_body(summary: str) -> str:
    return json.dumps(
        {
            "decision": "pass",
            "pm_visible_summary": [summary],
            "current_evidence_refs": ["current-evidence"],
        }
    )


class FlowPilotIdentityOwnerMeshTests(unittest.TestCase):
    def test_wrong_lease_holder_and_self_review_are_blocked(self) -> None:
        ledger, packet_id, worker_lease = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker_lease, packet_id)
        result_id = runtime.submit_result(ledger, worker_lease, packet_id, role_result_body("Worker result."))

        wrong_lease = runtime.lease_agent(ledger, "worker", agent_id="worker-wrong")
        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "lease is not assigned to packet"):
            runtime.ack_lease(ledger, wrong_lease, packet_id)

        reviewer_lease = runtime.lease_agent(
            ledger,
            "reviewer",
            agent_id=ledger["leases"][worker_lease]["agent_id"],
        )
        review_id = runtime.review_result(ledger, result_id, reviewer_lease, decision="accept")

        self.assertIn("self_review", ledger["reviews"][review_id]["blockers"])
        self.assertFalse(ledger["reviews"][review_id]["decision"] == "accept")

    def test_assignment_rejects_wrong_responsibility_and_checker_identity_collision(self) -> None:
        ledger, packet_id, worker_lease = runtime_runner._base_ledger()
        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "assignment responsibility does not match packet"):
            runtime.resolve_role_assignment(ledger, "reviewer", packet_id=packet_id)

        runtime.ack_lease(ledger, worker_lease, packet_id)
        result_id = runtime.submit_result(ledger, worker_lease, packet_id, role_result_body("Worker result."))
        flowguard_packet = next(
            packet["packet_id"]
            for packet in ledger["packets"].values()
            if packet["envelope"]["packet_kind"] == "flowguard_check"
        )
        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "checker role dispatch cannot use target result producer agent id"):
            runtime.lease_agent(
                ledger,
                "flowguard_operator",
                agent_id=ledger["results"][result_id]["producer_agent_id"],
                packet_id=flowguard_packet,
            )


if __name__ == "__main__":
    unittest.main()
