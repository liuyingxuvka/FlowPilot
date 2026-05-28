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
            break_glass.record_patch_validation(
                root,
                run_root,
                patch_id="patch-test",
                command="python simulations/run_flowpilot_controller_break_glass_checks.py",
                result="passed",
                summary="Break-glass model checks passed.",
            )

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
            self.assertEqual(closed["incident"]["closure_review"]["closure_path"], "validated_patch_closure")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_break_glass_close_rejects_unvalidated_permanent_patch(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="flowpilot-break-glass-unvalidated-"))
        try:
            run_root = root / ".flowpilot" / "runs" / "run-test"
            runtime = run_root / "runtime"
            runtime.mkdir(parents=True)
            (runtime / "controller_action_ledger.json").write_text("{}", encoding="utf-8")
            break_glass.open_incident(
                root,
                run_root,
                incident_id="incident-unvalidated",
                trigger_summary="Controller control channel needed a temporary patch.",
                failure_kind="no_legal_next_action",
                sources=[".flowpilot/runs/run-test/runtime/controller_action_ledger.json"],
                normal_lanes=["controller_action_ledger"],
            )
            break_glass.record_patch(
                root,
                run_root,
                incident_id="incident-unvalidated",
                patch_id="patch-unvalidated",
                reason="Temporary control-plane compensation.",
                touched_paths=[".flowpilot/runs/run-test/runtime/controller_action_ledger.json"],
                validation=["python simulations/run_flowpilot_controller_break_glass_checks.py"],
            )

            with self.assertRaisesRegex(SystemExit, "patch validation"):
                break_glass.close_incident(
                    root,
                    run_root,
                    incident_id="incident-unvalidated",
                    disposition="permanent_fix_applied",
                )
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_break_glass_close_allows_explicit_quarantine_for_pending_patch(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="flowpilot-break-glass-quarantine-"))
        try:
            run_root = root / ".flowpilot" / "runs" / "run-test"
            runtime = run_root / "runtime"
            runtime.mkdir(parents=True)
            (runtime / "controller_action_ledger.json").write_text("{}", encoding="utf-8")
            break_glass.open_incident(
                root,
                run_root,
                incident_id="incident-quarantine",
                trigger_summary="Controller control channel evidence was too weak to claim repair.",
                failure_kind="no_legal_next_action",
                sources=[".flowpilot/runs/run-test/runtime/controller_action_ledger.json"],
                normal_lanes=["controller_action_ledger"],
            )
            break_glass.record_patch(
                root,
                run_root,
                incident_id="incident-quarantine",
                patch_id="patch-quarantine",
                reason="Temporary control-plane compensation.",
                touched_paths=[".flowpilot/runs/run-test/runtime/controller_action_ledger.json"],
                validation=["python simulations/run_flowpilot_controller_break_glass_checks.py"],
            )

            closed = break_glass.close_incident(
                root,
                run_root,
                incident_id="incident-quarantine",
                disposition="weak_evidence_quarantined",
            )

            self.assertEqual(closed["incident"]["status"], "quarantined")
            self.assertEqual(closed["incident"]["closure_review"]["closure_path"], "weak_evidence_quarantine")
            patch = read_json(run_root / "controller_break_glass" / "patches" / "patch-quarantine.json")
            self.assertEqual(patch["final_disposition"], "weak_evidence_quarantined")
            self.assertTrue(patch["permanent_fix_needed"])
            self.assertEqual(patch["validation_status"], "pending")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_recovery_supervisor_records_transaction_body_grant_and_reinjection(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="flowpilot-recovery-supervisor-"))
        try:
            run_root = root / ".flowpilot" / "runs" / "run-test"
            runtime = run_root / "runtime"
            runtime.mkdir(parents=True)
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
            (runtime / "controller_action_ledger.json").write_text("{}", encoding="utf-8")
            (runtime / "sealed_result_body.md").write_text("diagnostic body", encoding="utf-8")
            proof_path = runtime / "recovery_supervisor_proof.json"
            proof_path.write_text('{"ok": true}', encoding="utf-8")

            break_glass.open_incident(
                root,
                run_root,
                incident_id="incident-rs",
                trigger_summary="Repeated control blocker prevented legal next action.",
                failure_kind="control_blocker_loop",
                sources=[".flowpilot/runs/run-test/runtime/controller_action_ledger.json"],
                normal_lanes=["pm_repair", "router_next_action"],
            )
            opened = break_glass.open_recovery_transaction(
                root,
                run_root,
                transaction_id="recovery-rs",
                incident_id="incident-rs",
                trigger_summary="Escalate to Recovery Supervisor.",
                failure_kind="control_blocker_loop",
                blocker_ids=["blocker-rs"],
                family_ids=["family-stale-proof"],
                normal_lanes=["pm_repair", "router_next_action"],
                controller_generation_id="controller-gen-1",
                flowguard_obligations=["python simulations/run_flowpilot_recovery_supervisor_checks.py"],
            )
            self.assertEqual(opened["transaction"]["identity_mode"], "recovery_supervisor")
            self.assertTrue(opened["transaction"]["normal_controller_suspended"])
            incident = read_json(run_root / "controller_break_glass" / "incidents" / "incident-rs.json")
            self.assertEqual(incident["related_recovery_transaction_ids"], ["recovery-rs"])

            blocker = break_glass.record_control_plane_blocker(
                root,
                run_root,
                blocker_id="blocker-rs",
                family_id="family-stale-proof",
                status="closed",
                summary="Same-family stale proof blocker was repaired.",
                sources=[".flowpilot/runs/run-test/runtime/controller_action_ledger.json"],
                recovery_transaction_id="recovery-rs",
            )
            self.assertTrue(blocker["ok"])

            grant = break_glass.request_body_access(
                root,
                run_root,
                transaction_id="recovery-rs",
                grant_id="grant-rs",
                body_path=".flowpilot/runs/run-test/runtime/sealed_result_body.md",
                reason="Metadata cannot distinguish the same-family stale-body class.",
                unavailable_role_lanes=["project_manager", "human_reviewer"],
            )
            self.assertFalse(grant["grant"]["normal_controller_body_access_granted"])
            self.assertEqual(grant["grant"]["granted_to_identity"], "recovery_supervisor")

            reinjection = break_glass.record_controller_reinjection(
                root,
                run_root,
                transaction_id="recovery-rs",
                reinjection_id="reinject-rs",
                previous_generation_id="controller-gen-1",
                next_generation_id="controller-gen-2",
                controller_core_path="skills/flowpilot/assets/runtime_kit/cards/roles/controller.md",
                boundary_proof_path=".flowpilot/runs/run-test/runtime/recovery_supervisor_proof.json",
                proof_artifacts=[".flowpilot/runs/run-test/runtime/recovery_supervisor_proof.json"],
            )
            self.assertTrue(reinjection["reinjection"]["old_controller_generation_invalidated"])

            closed = break_glass.close_recovery_transaction(
                root,
                run_root,
                transaction_id="recovery-rs",
                disposition="permanent_fix_applied",
                same_family_evidence=[".flowpilot/runs/run-test/runtime/recovery_supervisor_proof.json"],
            )
            self.assertFalse(closed["transaction"]["normal_controller_suspended"])
            self.assertEqual(closed["transaction"]["status"], "closed")

            index = read_json(run_root / "controller_break_glass" / "index.json")
            self.assertEqual(index["recovery_transactions"][0]["status"], "closed")
            ledger = read_json(run_root / "controller_break_glass" / "control_plane_blocker_ledger.json")
            self.assertEqual(ledger["blockers"][0]["family_id"], "family-stale-proof")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_recovery_supervisor_cannot_close_without_reinjection(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="flowpilot-recovery-supervisor-bad-"))
        try:
            run_root = root / ".flowpilot" / "runs" / "run-test"
            (run_root / "runtime").mkdir(parents=True)
            proof_path = run_root / "runtime" / "proof.json"
            proof_path.write_text('{"ok": true}', encoding="utf-8")
            break_glass.open_recovery_transaction(
                root,
                run_root,
                transaction_id="recovery-no-reinject",
                incident_id="incident-no-reinject",
                trigger_summary="Recovery cannot resume without new Controller core.",
                failure_kind="controller_generation_dirty",
                blocker_ids=[],
                family_ids=["family-controller-generation"],
                normal_lanes=["controller_core"],
                controller_generation_id="controller-gen-1",
                flowguard_obligations=["python simulations/run_flowpilot_recovery_supervisor_checks.py"],
            )
            with self.assertRaises(SystemExit):
                break_glass.close_recovery_transaction(
                    root,
                    run_root,
                    transaction_id="recovery-no-reinject",
                    disposition="permanent_fix_applied",
                    same_family_evidence=[".flowpilot/runs/run-test/runtime/proof.json"],
                )
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
