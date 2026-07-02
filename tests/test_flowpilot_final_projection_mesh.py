from __future__ import annotations

import importlib.util
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


runtime = load_module("flowpilot_runtime_final_projection_mesh", RUNTIME_ROOT / "runtime.py")
runtime_runner = load_module(
    "flowpilot_runtime_runner_final_projection_mesh",
    ROOT / "simulations" / "run_flowpilot_core_runtime_checks.py",
)


class FlowPilotFinalProjectionMeshTests(unittest.TestCase):
    def test_final_projection_rejects_stale_assignment_and_repairs_to_current_accepted_result(self) -> None:
        ledger, packet_id, worker_lease = runtime_runner._base_ledger()
        runtime_runner._complete_happy_path(ledger, packet_id, worker_lease)
        accepted_packet = runtime._accepted_result_packets_for_active_route(ledger)[0]  # noqa: SLF001
        accepted_packet_id = accepted_packet["packet_id"]
        accepted_result_id = accepted_packet["accepted_result_id"]
        original_lease_id = ledger["results"][accepted_result_id]["producer_lease_id"]
        stale_lease_id = runtime._next_id(ledger, "lease")  # noqa: SLF001
        ledger["leases"][stale_lease_id] = {
            **ledger["leases"][original_lease_id],
            "lease_id": stale_lease_id,
            "agent_id": "stale-worker",
            "status": "active",
            "packet_id": accepted_packet_id,
            "ack_received": True,
        }
        ledger["packets"][accepted_packet_id]["assigned_lease_id"] = stale_lease_id

        health = runtime.accepted_packet_lease_health(ledger)
        preflight = runtime.final_return_preflight(ledger)

        self.assertFalse(health["ok"])
        self.assertFalse(preflight["allowed"])
        self.assertIn(f"accepted_packet_lease_health:{accepted_packet_id}", preflight["blockers"])

        repair = runtime.repair_accepted_packet_assignment(ledger, accepted_packet_id)
        repaired_health = runtime.accepted_packet_lease_health(ledger)

        self.assertEqual(repair["assigned_lease_id"], original_lease_id)
        self.assertTrue(repaired_health["ok"])

    def test_superseded_packet_is_noncurrent_target_not_current_final_evidence(self) -> None:
        ledger, packet_id, worker_lease = runtime_runner._base_ledger()
        runtime_runner._complete_happy_path(ledger, packet_id, worker_lease)
        accepted_packet_id = runtime._accepted_result_packets_for_active_route(ledger)[0]["packet_id"]  # noqa: SLF001
        ledger["packets"][accepted_packet_id]["status"] = "superseded_after_repair"

        violation = runtime._packet_current_target_violation(ledger, accepted_packet_id)  # noqa: SLF001

        self.assertEqual(violation, "noncurrent_packet_status:superseded_after_repair")


if __name__ == "__main__":
    unittest.main()
