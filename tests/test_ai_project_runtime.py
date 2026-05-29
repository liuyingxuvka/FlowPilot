from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = ROOT / "skills" / "flowpilot" / "assets" / "ai_project_runtime"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    old_path = list(sys.path)
    old_module = sys.modules.get(name)
    sys.modules[name] = module
    sys.path.insert(0, str(path.parent))
    sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old_path
        if old_module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = old_module
    return module


runtime = load_module("ai_project_runtime_under_test", RUNTIME_ROOT / "runtime.py")
runtime_runner = load_module(
    "ai_project_runtime_runner_under_test",
    ROOT / "simulations" / "run_ai_project_runtime_checks.py",
)
development_runner = load_module(
    "ai_project_runtime_development_runner_under_test",
    ROOT / "simulations" / "run_ai_project_runtime_development_checks.py",
)


class AIProjectRuntimeTests(unittest.TestCase):
    def test_runtime_assets_exist_and_document_boundaries(self) -> None:
        runtime_files = {path.name for path in RUNTIME_ROOT.iterdir() if path.is_file()}
        for required_file in {
            "__init__.py",
            "README.md",
            "runtime.py",
            "cli.py",
            "run_shell.py",
            "host.py",
            "router.py",
            "packets.py",
            "flowguard_orders.py",
            "review_closure.py",
            "cockpit.py",
            "migration.py",
        }:
            with self.subTest(required_file=required_file):
                self.assertIn(required_file, runtime_files)
        readme = (RUNTIME_ROOT / "README.md").read_text(encoding="utf-8")
        for phrase in (
            "The ledger is the truth",
            "ACK and progress are liveness only",
            "FlowGuard work orders must name the modeled target",
            "Forbidden authority: old runtime state",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, readme)

    def test_replacement_worker_can_finish_but_closed_worker_late_output_is_blocked(self) -> None:
        report = runtime_runner.replacement_worker_success()
        self.assertTrue(report["ok"], report)
        self.assertTrue(report["accepted"])
        self.assertIn("closed_or_inactive_lease", report["details"]["late_result_blockers"])

    def test_wrong_flowguard_target_self_review_stale_route_and_stale_evidence_block(self) -> None:
        for scenario_name in (
            "wrong_flowguard_target_blocks",
            "self_review_blocks",
            "stale_route_output_blocks",
            "stale_evidence_blocks",
        ):
            with self.subTest(scenario=scenario_name):
                report = runtime_runner.SCENARIOS[scenario_name]()
                self.assertTrue(report["ok"], report)
                self.assertFalse(report["accepted"])

    def test_ack_and_progress_do_not_complete_packet(self) -> None:
        report = runtime_runner.ack_only_timeout_stays_incomplete()
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["details"]["before_timeout"]["action_type"], "wait_for_result")
        self.assertEqual(report["details"]["after_timeout"]["action_type"], "replace_lease")

    def test_public_console_hides_sealed_bodies(self) -> None:
        report = runtime_runner.console_does_not_leak_sealed_bodies()
        self.assertTrue(report["ok"], report)
        self.assertFalse(report["details"]["leaked"])
        rendered = json.dumps(report, sort_keys=True)
        self.assertNotIn("SEALED_TASK_BODY", rendered)
        self.assertNotIn("SEALED_RESULT_BODY", rendered)

    def test_router_closes_only_after_backward_chain_and_validation(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime_runner._complete_happy_path(ledger, packet_id, worker)

        self.assertEqual(ledger["closure"]["decision"], "complete")
        self.assertEqual(runtime.router_next_action(ledger).action_type, "terminal_complete")
        self.assertEqual(
            [item["kind"] for item in ledger["closure"]["backward_chain"]],
            ["goal", "route", "packet", "result", "review", "flowguard"],
        )

    def test_runtime_testmesh_does_not_overclaim_release_evidence(self) -> None:
        report = runtime_runner.run_checks()
        self.assertTrue(report["ok"], report)
        self.assertTrue(report["test_mesh"]["parent_gates"]["routine_runtime_gate"]["ok"])
        self.assertFalse(report["test_mesh"]["parent_gates"]["release_runtime_gate"]["ok"])
        rows = {row["id"]: row for row in report["test_mesh"]["rows"]}
        self.assertEqual(rows["background_meta_capability"]["status"], "not_run")
        self.assertEqual(rows["install_surface_parity"]["status"], "not_run")

    def test_flowguard_development_model_accepts_order_and_rejects_hazards(self) -> None:
        report = development_runner.run_checks()
        self.assertTrue(report["ok"], report)
        self.assertTrue(report["flowguard"]["ok"])
        self.assertTrue(report["target_plan"]["ok"])
        self.assertTrue(report["hazard_detection"]["ok"])
        self.assertIn("fixed_six_roles_reintroduced", report["hazard_detection"]["hazards"])


if __name__ == "__main__":
    unittest.main()
