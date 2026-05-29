from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    old_path = list(sys.path)
    sys.path.insert(0, str(path.parent))
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old_path
    return module


daemon_children = load_module(
    "flowpilot_test_daemon_children",
    ROOT / "simulations" / "flowpilot_persistent_router_daemon_child_models.py",
)
thin_parent_checks = load_module(
    "flowpilot_test_daemon_thin_parent_checks",
    ROOT / "simulations" / "flowpilot_thin_parent_checks.py",
)


class FlowPilotDaemonChildMeshTests(unittest.TestCase):
    def test_daemon_child_reports_are_thin_and_green(self) -> None:
        for family in daemon_children.FAMILIES:
            with self.subTest(family=family):
                report = daemon_children.build_report(family)

                self.assertTrue(report["ok"])
                self.assertLess(
                    report["graph"]["state_count"],
                    thin_parent_checks.HEAVYWEIGHT_STATE_THRESHOLD,
                )
                self.assertEqual(report["parent_partition"], "router_daemon_resume")
                self.assertTrue(report["parent_reattachment"]["parent_consumes_this_child"])

    def test_parent_ledger_consumes_split_daemon_children_not_large_monolith_model(self) -> None:
        ledger = json.loads(thin_parent_checks.LEDGER_PATH.read_text(encoding="utf-8"))
        meta_partitions = ledger["parents"]["meta"]["partitions"]
        router_partition = next(
            partition for partition in meta_partitions if partition["id"] == "router_daemon_resume"
        )
        evidence_ids = set(router_partition["evidence_ids"])

        self.assertNotIn("flowpilot_persistent_router_daemon", evidence_ids)
        self.assertEqual(
            {
                "flowpilot_daemon_startup_lock",
                "flowpilot_daemon_controller_actions",
                "flowpilot_daemon_wait_liveness",
                "flowpilot_daemon_terminal_projection",
            },
            {
                evidence_id
                for evidence_id in evidence_ids
                if evidence_id.startswith("flowpilot_daemon_")
                and evidence_id
                not in {
                    "flowpilot_daemon_reconciliation",
                    "flowpilot_daemon_liveness",
                }
            },
        )


if __name__ == "__main__":
    unittest.main()
