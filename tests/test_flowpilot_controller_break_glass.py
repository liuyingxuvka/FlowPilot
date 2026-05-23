from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))
sys.path.insert(0, str(ROOT / "tests"))

import flowpilot_controller_break_glass as break_glass  # noqa: E402
import flowpilot_router as router  # noqa: E402
from router_runtime.common import FlowPilotRouterRuntimeTestBase, read_json  # noqa: E402


PLAYBOOK_PATH = "skills/flowpilot/assets/runtime_kit/cards/system/controller_break_glass_repair.md"


class FlowPilotControllerBreakGlassPromptTests(unittest.TestCase):
    def test_playbook_is_registered_and_controller_visible(self) -> None:
        playbook = ROOT / PLAYBOOK_PATH
        self.assertTrue(playbook.exists())
        text = playbook.read_text(encoding="utf-8")
        self.assertIn("When To Use", text)
        self.assertIn("When Not To Use", text)
        self.assertIn("Forbidden Actions", text)
        self.assertIn("Final Reporting", text)

        manifest = json.loads((ROOT / "skills/flowpilot/assets/runtime_kit/manifest.json").read_text(encoding="utf-8"))
        entry = next((item for item in manifest["cards"] if item.get("id") == "controller.break_glass_repair"), None)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["audience"], "controller")
        self.assertEqual(entry["path"], "cards/system/controller_break_glass_repair.md")

        controller_card = (ROOT / "skills/flowpilot/assets/runtime_kit/cards/roles/controller.md").read_text(encoding="utf-8")
        self.assertIn(PLAYBOOK_PATH, controller_card)
        self.assertIn("not for ordinary", controller_card.lower())

    def test_controller_table_prompt_repeats_restrictive_reminder(self) -> None:
        prompt = router._controller_table_prompt()  # type: ignore[attr-defined]
        self.assertIn("break_glass_reminder", prompt)
        reminder = prompt["break_glass_reminder"]
        self.assertEqual(reminder["playbook_path"], PLAYBOOK_PATH)
        self.assertIn(PLAYBOOK_PATH, prompt["text"])
        self.assertIn("only if normal FlowPilot control flow itself appears broken", prompt["text"])
        self.assertIn("ordinary project bugs", prompt["text"])
        self.assertIn("worker defects", prompt["text"])
        self.assertFalse(prompt["sealed_body_reads_allowed"])

    def test_break_glass_helper_records_incident_and_patch(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="flowpilot-break-glass-"))
        try:
            run_root = root / ".flowpilot" / "runs" / "run-test"
            (run_root / "runtime").mkdir(parents=True)
            (root / ".flowpilot").mkdir(exist_ok=True)
            (root / ".flowpilot" / "current.json").write_text(
                json.dumps(
                    {
                        "schema_version": "flowpilot.current.v1",
                        "current_run_id": "run-test",
                        "current_run_root": ".flowpilot/runs/run-test",
                        "status": "running",
                    }
                ),
                encoding="utf-8",
            )
            (run_root / "runtime" / "controller_action_ledger.json").write_text("{}", encoding="utf-8")

            opened = break_glass.open_incident(
                root,
                run_root,
                incident_id="incident-test",
                trigger_summary="Controller ledger and daemon status could not produce a legal next action.",
                failure_kind="no_legal_next_action",
                sources=[".flowpilot/runs/run-test/runtime/controller_action_ledger.json"],
                normal_lanes=["controller_action_ledger", "router_daemon_status"],
            )
            self.assertTrue(opened["ok"])
            incident_path = Path(opened["incident_path"])
            self.assertTrue(incident_path.exists())
            incident = json.loads(incident_path.read_text(encoding="utf-8"))
            self.assertEqual(incident["schema_version"], break_glass.INCIDENT_SCHEMA)
            self.assertTrue(incident["forbidden_actions_acknowledged"]["sealed_body_access"])

            patched = break_glass.record_patch(
                root,
                run_root,
                incident_id="incident-test",
                patch_id="patch-test",
                reason="Temporary control-plane compensation.",
                touched_paths=[".flowpilot/runs/run-test/runtime/controller_action_ledger.json"],
                validation=["python simulations/run_flowpilot_controller_break_glass_checks.py"],
            )
            self.assertTrue(patched["ok"])
            patch = json.loads(Path(patched["patch_path"]).read_text(encoding="utf-8"))
            self.assertEqual(patch["schema_version"], break_glass.PATCH_SCHEMA)
            self.assertTrue(patch["temporary"])
            self.assertTrue(patch["forbidden_actions_preserved"]["gate_approval"])

            index = read_json(run_root / "controller_break_glass" / "index.json")
            self.assertEqual(index["schema_version"], break_glass.INDEX_SCHEMA)
            self.assertEqual(index["incidents"][0]["incident_id"], "incident-test")
            self.assertEqual(index["patches"][0]["patch_id"], "patch-test")
            closed = break_glass.close_incident(
                root,
                run_root,
                incident_id="incident-test",
                disposition="permanent_fix_applied",
            )
            self.assertTrue(closed["ok"])
            finalized_patch = read_json(run_root / "controller_break_glass" / "patches" / "patch-test.json")
            self.assertEqual(finalized_patch["final_disposition"], "permanent_fix_applied")
            self.assertFalse(finalized_patch["temporary"])
            self.assertFalse(finalized_patch["permanent_fix_needed"])
            self.assertEqual(closed["incident"]["patch_finalization"]["finalized_patch_count"], 1)
        finally:
            shutil.rmtree(root, ignore_errors=True)


class FlowPilotControllerBreakGlassRuntimeTests(FlowPilotRouterRuntimeTestBase):
    def test_daemon_status_standby_and_patrol_expose_reminder(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        self.force_startup_fact_role_wait(root)

        standby = router.foreground_controller_standby(root, max_seconds=0, poll_seconds=0.01, bounded_diagnostic=True)
        self.assertIn("break_glass_reminder", standby)
        self.assertEqual(standby["break_glass_reminder"]["playbook_path"], PLAYBOOK_PATH)
        self.assertIn("break_glass_reminder", standby["continuous_standby_task"])
        self.assertIn(PLAYBOOK_PATH, standby["continuous_standby_task"]["codex_plan_sync"]["plan_item"])

        run_root = self.run_root_for(root)
        status = read_json(run_root / "runtime" / "router_daemon_status.json")
        self.assertIn("break_glass_reminder", status)
        self.assertEqual(status["break_glass_reminder"]["playbook_path"], PLAYBOOK_PATH)

        patrol = router.controller_patrol_timer(root, seconds=0)
        self.assertIn("break_glass_reminder", patrol)
        self.assertEqual(patrol["break_glass_reminder"]["playbook_path"], PLAYBOOK_PATH)
        self.assertIn("ordinary project bugs", patrol["break_glass_reminder"]["text"])


if __name__ == "__main__":
    unittest.main()
