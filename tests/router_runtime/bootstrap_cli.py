from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase


class BootstrapCliRuntimeTests(FlowPilotRouterRuntimeTestBase):
    def test_start_command_creates_fresh_run_when_current_is_running(self) -> None:
        root = self.make_project()
        old_run_root = self.write_minimal_run(root, "run-old-running", status="controller_ready")
        self.write_current_focus(root, old_run_root)
        old_state_before = read_json(router.run_state_path(old_run_root))

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = router.main(["--root", str(root), "start", "--json"])

        self.assertEqual(exit_code, 0)
        result = json.loads(stdout.getvalue())
        current = read_json(root / ".flowpilot" / "current.json")
        self.assertNotEqual(current["current_run_id"], "run-old-running")
        self.assertIn("create_run_shell", [item["action_type"] for item in result["folded_applied_actions"]])
        self.assertTrue((root / current["current_run_root"] / "run.json").exists())
        self.assertEqual(read_json(router.run_state_path(old_run_root)), old_state_before)
        self.assertFalse((old_run_root / "runtime" / "controller_action_ledger.json").exists())
    def test_new_invocation_preserves_multiple_parallel_running_runs(self) -> None:
        root = self.make_project()
        run_a = self.write_minimal_run(root, "run-a", status="controller_ready")
        run_b = self.write_minimal_run(root, "run-b", status="controller_ready")
        self.write_current_focus(root, run_b)
        router.write_json(
            root / ".flowpilot" / "index.json",
            {
                "schema_version": "flowpilot.index.v1",
                "runs": [
                    {"run_id": "run-a", "run_root": ".flowpilot/runs/run-a", "status": "running"},
                    {"run_id": "run-b", "run_root": ".flowpilot/runs/run-b", "status": "running"},
                ],
                "current_run_id": "run-b",
                "updated_at": router.utc_now(),
            },
        )
        state_a_before = read_json(router.run_state_path(run_a))
        state_b_before = read_json(router.run_state_path(run_b))

        result = router.run_until_wait(root, new_invocation=True)

        current = read_json(root / ".flowpilot" / "current.json")
        self.assertNotIn(current["current_run_id"], {"run-a", "run-b"})
        self.assertIn("create_run_shell", [item["action_type"] for item in result["folded_applied_actions"]])
        self.assertTrue((root / current["current_run_root"] / "run.json").exists())
        self.assertEqual(read_json(router.run_state_path(run_a)), state_a_before)
        self.assertEqual(read_json(router.run_state_path(run_b)), state_b_before)
        index = read_json(root / ".flowpilot" / "index.json")
        run_ids = {item["run_id"] for item in index["runs"]}
        self.assertTrue({"run-a", "run-b", current["current_run_id"]}.issubset(run_ids))
        self.assertEqual(next(item for item in index["runs"] if item["run_id"] == "run-a")["status"], "running")
        self.assertEqual(next(item for item in index["runs"] if item["run_id"] == "run-b")["status"], "running")
    def test_cli_accepts_json_after_subcommand(self) -> None:
        parsed = router.parse_args(["--root", "C:/tmp/project", "next", "--json"])
        self.assertEqual(parsed.command, "next")
        self.assertTrue(parsed.json)

        parsed = router.parse_args(
            ["--root", "C:/tmp/project", "run-until-wait", "--new-invocation", "--json"]
        )
        self.assertEqual(parsed.command, "run-until-wait")
        self.assertTrue(parsed.new_invocation)
        self.assertTrue(parsed.json)

        parsed = router.parse_args(["--root", "C:/tmp/project", "start", "--json"])
        self.assertEqual(parsed.command, "start")
        self.assertTrue(parsed.json)

        parsed = router.parse_args(
            ["--root", "C:/tmp/project", "apply", "--action-type", "load_router", "--json"]
        )
        self.assertEqual(parsed.command, "apply")
        self.assertEqual(parsed.action_type, "load_router")
        self.assertTrue(parsed.json)

        parsed = router.parse_args(
            ["--root", "C:/tmp/project", "record-event", "--event", "pm_first_decision_resets_controller", "--json"]
        )
        self.assertEqual(parsed.command, "record-event")
        self.assertEqual(parsed.event, "pm_first_decision_resets_controller")
        self.assertTrue(parsed.json)

        parsed = router.parse_args(
            [
                "--root",
                "C:/tmp/project",
                "role-output-envelope",
                "--output-path",
                "role_outputs/sample.json",
                "--json",
            ]
        )
        self.assertEqual(parsed.command, "role-output-envelope")
        self.assertTrue(parsed.json)

        parsed = router.parse_args(
            [
                "--root",
                "C:/tmp/project",
                "validate-artifact",
                "--type",
                "role_output_envelope",
                "--path",
                "role_outputs/sample.json",
                "--json",
            ]
        )
        self.assertEqual(parsed.command, "validate-artifact")
        self.assertTrue(parsed.json)

        parsed = router.parse_args(["--root", "C:/tmp/project", "state", "--json"])
        self.assertEqual(parsed.command, "state")
        self.assertTrue(parsed.json)

        parsed = router.parse_args(["--root", "C:/tmp/project", "reconcile-run", "--json"])
        self.assertEqual(parsed.command, "reconcile-run")
        self.assertTrue(parsed.json)
    def test_retired_high_risk_fold_commands_are_not_cli_commands(self) -> None:
        for command in (
            "deliver-card-bundle-checked",
            "relay-checked",
            "prepare-startup-fact-check",
            "record-role-output-checked",
        ):
            with self.assertRaises(SystemExit):
                with contextlib.redirect_stderr(io.StringIO()):
                    router.parse_args(["--root", "C:/tmp/project", command, "--json"])
    def test_skill_entrypoint_remains_small_router_launcher(self) -> None:
        skill_text = (ROOT / "skills" / "flowpilot" / "SKILL.md").read_text(encoding="utf-8")
        line_count = len(skill_text.splitlines())

        self.assertLess(line_count, 120)
        self.assertIn("flowpilot_router.py", skill_text)
        self.assertIn("Do not read FlowPilot reference files", skill_text)
        self.assertNotIn("Final Route-Wide Gate Ledger", skill_text)
