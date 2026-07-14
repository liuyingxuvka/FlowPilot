from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase, read_json
from scripts.test_tier import background as test_tier_background


INSTALLED_CLI_TIMEOUT_SECONDS = 180.0


class FlowPilotShadowLauncherChaosReplayTests(FlowPilotRouterRuntimeTestBase):
    def copied_installed_skill_router(self, root: Path) -> Path:
        install_root = root / "skills-install" / "flowpilot"
        shutil.copytree(ROOT / "skills" / "flowpilot", install_root)
        router_script = install_root / "assets" / "flowpilot_router.py"
        self.assertTrue(router_script.exists())
        return router_script

    def run_installed_cli(
        self,
        router_script: Path,
        root: Path,
        args: list[str],
        *,
        timeout: float = INSTALLED_CLI_TIMEOUT_SECONDS,
    ) -> dict:
        command = [sys.executable, str(router_script), "--root", str(root), *args]
        if "--json" not in command:
            command.append("--json")
        completed = subprocess.run(
            command,
            cwd=router_script.parent,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        payload = json.loads(completed.stdout)
        self.assertIsInstance(payload, dict)
        return payload

    def stop_opened_daemon(self, router_script: Path, root: Path, started: dict) -> dict:
        spawn_info = {}
        for item in started.get("folded_applied_actions", []):
            result = item.get("result") if isinstance(item, dict) else {}
            if isinstance(result, dict) and isinstance(result.get("spawn_info"), dict):
                spawn_info = result["spawn_info"]
        child_pid = spawn_info.get("pid")
        if not isinstance(child_pid, int) or child_pid <= 0:
            try:
                state = self.run_installed_cli(router_script, root, ["state"])
                run_root = root / str(state.get("run_root") or "")
                lock = read_json(run_root / "runtime" / "router_daemon.lock")
                child_pid = (lock.get("owner") or {}).get("pid")
            except (AssertionError, OSError, ValueError, json.JSONDecodeError):
                child_pid = None
        stopped = self.run_installed_cli(router_script, root, ["daemon-stop", "--reason", "shadow_launcher_test_cleanup"])
        if not isinstance(child_pid, int) or child_pid <= 0:
            return stopped
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            try:
                os.kill(child_pid, 0)
            except OSError:
                return stopped
            time.sleep(0.1)
        try:
            os.kill(child_pid, signal.SIGTERM)
        except OSError:
            return stopped
        return stopped

    def test_installed_launcher_shadow_start_reaches_releasable_standard_state(self) -> None:
        root = self.make_project()
        router_script = self.copied_installed_skill_router(root)

        started = self.run_installed_cli(router_script, root, ["start"])
        stopped = {}
        try:
            self.assertTrue(started["folded_applied_actions"])
            self.assertEqual(started["folded_stop_reason"], "requires_user_host_or_role_boundary")
            self.assertTrue((root / ".flowpilot" / "current.json").exists())
            state = self.run_installed_cli(router_script, root, ["state"])
            self.assertTrue(state["run_root"])
            run_root = root / state["run_root"]
            self.assertTrue((run_root / "router_state.json").exists())
            self.assertTrue((run_root / "runtime" / "router_daemon.lock").exists())
        finally:
            stopped = self.stop_opened_daemon(router_script, root, started)

        lock = read_json(run_root / "runtime" / "router_daemon.lock")
        self.assertTrue(stopped["ok"])
        self.assertIn(lock["status"], {"released", "terminal_stopped", "error"})

    def test_crash_recovery_bundle_handles_dead_daemon_duplicate_resume_and_progress_only_proof(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_runtime_entry(root)

        lock_path = run_root / "runtime" / "router_daemon.lock"
        lock = read_json(lock_path)
        lock["last_tick_at"] = "2000-01-01T00:00:00Z"
        lock["owner"] = {"pid": 999999999, "process_name": "missing-shadow-daemon"}
        router.write_json(lock_path, lock)

        router.record_external_event(root, "manual_resume_requested")
        first_action = router.next_action(root)
        router.record_external_event(root, "manual_resume_requested")
        second_action = router.next_action(root)
        self.assertEqual(first_action["action_type"], "load_resume_state")
        self.assertEqual(second_action["action_type"], "load_resume_state")
        self.assertEqual(
            first_action["router_daemon_resume_recovery"]["decision"],
            "restart_router_daemon_from_current_state",
        )

        router.apply_action(root, "load_resume_state")
        resume_evidence = read_json(run_root / "continuation" / "resume_reentry.json")
        self.assertTrue(resume_evidence["router_daemon_liveness_checked"])
        self.assertTrue(resume_evidence["router_daemon_restarted_if_dead"])
        self.assertTrue(read_json(router.run_state_path(run_root))["flags"]["resume_state_loaded"])

        with tempfile.TemporaryDirectory(prefix="flowpilot-shadow-bg-proof-") as tmp_name:
            proof_root = Path(tmp_name)
            paths = test_tier_background.artifact_paths(proof_root, "shadow_launcher_progress_only")
            paths["combined"].parent.mkdir(parents=True, exist_ok=True)
            paths["combined"].write_text("model regression still running\n", encoding="utf-8")
            progress = test_tier_background.classify_background_artifact(
                proof_root,
                "shadow_launcher_progress_only",
            )
        self.assertEqual(progress["status"], "progress_only")
        self.assertFalse(progress["ok"])
        self.assertIn("missing_exit", progress["reasons"])

    def test_peer_conflict_keeps_current_run_authority_and_rejects_stale_peer_proof(self) -> None:
        root = self.make_project()
        run_a = self.write_minimal_run(root, "run-a")
        run_b = self.write_minimal_run(root, "run-b")
        self.write_current_focus(root, run_b)
        state_a = read_json(router.run_state_path(run_a))
        state_b = read_json(router.run_state_path(run_b))
        router._acquire_router_daemon_lock(root, run_a, state_a)  # type: ignore[attr-defined]
        router._acquire_router_daemon_lock(root, run_b, state_b)  # type: ignore[attr-defined]

        proof_dir = root / ".flowpilot" / "peer-proofs"
        proof_paths = test_tier_background.artifact_paths(proof_dir, "peer_shadow_proof")
        proof_paths["combined"].parent.mkdir(parents=True, exist_ok=True)
        proof_paths["out"].write_text("peer run proof passed\n", encoding="utf-8")
        proof_paths["err"].write_text("", encoding="utf-8")
        proof_paths["combined"].write_text("peer run proof passed\n", encoding="utf-8")
        proof_paths["exit"].write_text("0\n", encoding="utf-8")
        proof_paths["meta"].write_text(
            json.dumps(
                {
                    "name": "peer_shadow_proof",
                    "status": "passed",
                    "exit_code": 0,
                    "proof_reused": False,
                    "run_id": "run-a",
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        stopped = router.stop_router_daemon(root, reason="shadow_peer_stop", run_root=run_a)
        current = read_json(root / ".flowpilot" / "current.json")
        peer_proof = json.loads(proof_paths["meta"].read_text(encoding="utf-8"))
        peer_evidence = test_tier_background.classify_background_artifact(proof_dir, "peer_shadow_proof")

        self.assertEqual(stopped["run_id"], "run-a")
        self.assertEqual(current["run_id"], "run-b")
        self.assertEqual(read_json(run_a / "runtime" / "router_daemon.lock")["status"], "released")
        self.assertEqual(read_json(run_b / "runtime" / "router_daemon.lock")["status"], "active")
        self.assertTrue(peer_evidence["ok"])
        self.assertNotEqual(peer_proof["run_id"], current["run_id"])
        self.assertFalse(read_json(router.run_state_path(run_a))["daemon_mode_enabled"])
        self.assertTrue(read_json(router.run_state_path(run_b))["daemon_mode_enabled"])

    def test_current_pointer_and_installed_assets_resolve_to_current_standard_state(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-current-pointer")
        router.write_json(
            root / ".flowpilot" / "current.json",
            {
                "schema_version": "flowpilot.current.v1",
                "run_id": run_root.name,
                "run_root": router.project_relative(root, run_root),
                "status": "running",
                "updated_at": router.utc_now(),
            },
        )
        copied_router = self.copied_installed_skill_router(root)

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = router.main(["--root", str(root), "state", "--json"])
        payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0, payload)
        self.assertEqual(Path(payload["run_root"]), run_root)
        self.assertEqual(payload["run_state"]["run_id"], "run-current-pointer")
        self.assertTrue(copied_router.exists())
        self.assertTrue((copied_router.parent / "flowpilot_router_cli.py").exists())

    def required_malformed_package_classes(self) -> tuple[str, ...]:
        return (
            "missing_runtime_envelope",
            "wrong_event_schema",
            "controller_visible_body_leak",
            "wrong_author_role",
            "stale_hash_or_path",
        )

    def _reject_missing_runtime_envelope(self, root: Path) -> None:
        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "reviewer_reports_startup_facts",
                {"report_path": ".flowpilot/runs/missing/report.json", "report_hash": "0" * 64},
            )

    def _reject_wrong_event_schema(self, root: Path) -> None:
        envelope, envelope_path, _ = self.legacy_startup_fact_runtime_envelope(root, "shadow_bad/wrong_schema")
        event_path = root / envelope_path
        envelope["schema_version"] = "flowpilot.untrusted_event_envelope.v0"
        event_path.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        event_hash = hashlib.sha256(event_path.read_bytes()).hexdigest()
        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "reviewer_reports_startup_facts",
                {"event_envelope_ref": {"path": envelope_path, "hash": event_hash}},
            )

    def _reject_controller_visible_body_leak(self, root: Path) -> None:
        with self.assertRaises(role_output_runtime.RoleOutputRuntimeError):
            role_output_runtime.update_output_progress(
                root,
                output_type="startup_fact_report",
                role="human_like_reviewer",
                agent_id="agent-reviewer-shadow-leak",
                progress=50,
                message="The sealed body findings are ready.",
            )

    def _reject_wrong_author_role(self, root: Path) -> None:
        with self.assertRaises(role_output_runtime.RoleOutputRuntimeError):
            role_output_runtime.submit_output(
                root,
                output_type="startup_fact_report",
                role="project_manager",
                agent_id="agent-pm-wrong-startup-fact-author",
                event_name="reviewer_reports_startup_facts",
                body=self.legacy_startup_fact_report_body(root),
            )

    def _reject_stale_hash_or_path(self, root: Path) -> None:
        _, envelope_path, _ = self.legacy_startup_fact_runtime_envelope(root, "shadow_bad/stale_hash")
        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "reviewer_reports_startup_facts",
                {"event_envelope_ref": {"path": envelope_path, "hash": "0" * 64}},
            )

    def test_malformed_fake_ai_package_generator_rejects_finite_bad_classes(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)

        rejectors = {
            "missing_runtime_envelope": self._reject_missing_runtime_envelope,
            "wrong_event_schema": self._reject_wrong_event_schema,
            "controller_visible_body_leak": self._reject_controller_visible_body_leak,
            "wrong_author_role": self._reject_wrong_author_role,
            "stale_hash_or_path": self._reject_stale_hash_or_path,
        }
        self.assertEqual(set(rejectors), set(self.required_malformed_package_classes()))

        for package_class in self.required_malformed_package_classes():
            with self.subTest(package_class=package_class):
                rejectors[package_class](root)

    def test_bounded_soak_repeats_startup_recovery_and_cleanup_without_residue(self) -> None:
        cycle_results: list[dict[str, str]] = []
        for cycle in range(2):
            root = self.make_project()
            run_root = self.boot_to_controller(root)
            self.complete_startup_runtime_entry(root)

            lock_path = run_root / "runtime" / "router_daemon.lock"
            lock = read_json(lock_path)
            lock["last_tick_at"] = "2000-01-01T00:00:00Z"
            lock["owner"] = {"pid": 999999999, "process_name": f"missing-shadow-soak-{cycle}"}
            router.write_json(lock_path, lock)
            router.record_external_event(root, "manual_resume_requested")
            self.assertEqual(router.next_action(root)["action_type"], "load_resume_state")
            router.apply_action(root, "load_resume_state")
            stopped = router.stop_router_daemon(root, reason=f"shadow_soak_cleanup_{cycle}")
            final_lock = read_json(lock_path)
            current = read_json(root / ".flowpilot" / "current.json")
            cycle_results.append(
                {
                    "run_id": current["run_id"],
                    "lock_status": final_lock["status"],
                    "stop_ok": str(stopped["ok"]),
                }
            )

        self.assertEqual(len(cycle_results), 2)
        self.assertNotEqual(cycle_results[0]["run_id"], cycle_results[1]["run_id"])
        for result in cycle_results:
            with self.subTest(result=result):
                self.assertEqual(result["stop_ok"], "True")
                self.assertIn(result["lock_status"], {"released", "terminal_stopped"})


if __name__ == "__main__":
    import unittest

    unittest.main()


