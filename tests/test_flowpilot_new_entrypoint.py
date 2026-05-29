from __future__ import annotations

import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
if str(ASSETS) not in sys.path:
    sys.path.insert(0, str(ASSETS))

flowpilot_new = importlib.import_module("flowpilot_new")
run_shell = importlib.import_module("ai_project_runtime.run_shell")
entrypoint_runner = importlib.import_module("simulations.run_flowpilot_new_entrypoint_checks")


class FlowPilotNewEntrypointTests(unittest.TestCase):
    def test_start_rehearsal_reuses_old_startup_ui_and_enters_new_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = flowpilot_new.start_run(
                root,
                run_id="run-new-entry",
                headless_startup_text="Build a tiny project through new FlowPilot.",
                require_formal_ui=False,
            )

            self.assertTrue(result["ok"], result)
            self.assertEqual(result["mode"], "rehearsal")
            self.assertEqual(result["next_action"]["action_type"], "lease_agent")
            self.assertEqual(result["next_action"]["responsibility"], "pm")
            shell = run_shell.load_run_shell(root, run_id="run-new-entry")
            ledger = run_shell.load_run_ledger(shell)
            self.assertTrue(ledger["startup_intake"]["current_run_authority"])
            self.assertTrue(ledger["contract_frozen"])
            self.assertEqual(ledger["active_route_version"], 1)
            self.assertEqual(len(ledger["packets"]), 1)
            packet = next(iter(ledger["packets"].values()))
            self.assertEqual(packet["envelope"]["responsibility"], "pm")
            rendered = json.dumps(result["status"], sort_keys=True)
            self.assertNotIn("Build a tiny project through new FlowPilot.", rendered)
            self.assertIn("flowpilot_startup_intake.ps1", " ".join(flowpilot_new.startup_ui_command(root, "run-new-entry")[0]))

    def test_fake_end_to_end_rehearsal_reaches_final_closure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = flowpilot_new.run_fake_e2e(
                root,
                run_id="run-e2e",
                startup_text="Build and validate a toy command.",
            )

            self.assertTrue(result["ok"], result)
            self.assertEqual(result["closure"]["decision"], "complete")
            self.assertEqual(result["next_action"]["action_type"], "terminal_complete")
            shell = run_shell.load_run_shell(root, run_id="run-e2e")
            ledger = run_shell.load_run_ledger(shell)
            self.assertEqual(next(iter(ledger["reviews"].values()))["decision"], "accept")
            self.assertEqual(next(iter(ledger["flowguard_work_orders"].values()))["modeled_target"], "development_process")
            status = json.loads((shell.run_root / "console" / "status.json").read_text(encoding="utf-8"))
            self.assertFalse(status["sealed_bodies_visible"])

    def test_formal_mode_rejects_headless_startup_result_as_formal_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            command_result = flowpilot_new.start_run(
                root,
                run_id="run-formal-source",
                headless_startup_text="Headless text should stay rehearsal-only.",
                require_formal_ui=False,
            )
            result_path = Path(command_result["run"]["run_root"]) / "startup_intake" / "startup_intake_result.json"
            with self.assertRaisesRegex(Exception, "formal FlowPilot startup requires"):
                flowpilot_new._assert_formal_interactive_result(result_path)

    def test_flowguard_new_entrypoint_model_is_green_and_catches_hazards(self) -> None:
        result = entrypoint_runner.run_checks()
        self.assertTrue(result["ok"], result)
        self.assertIn("old_router_authority", result["hazard_detection"]["hazards"])
        self.assertIn("monitor_ui_required", result["hazard_detection"]["hazards"])
        self.assertIn("headless_formal_overclaim", result["hazard_detection"]["hazards"])


if __name__ == "__main__":
    unittest.main()
