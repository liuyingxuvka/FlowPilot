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
        self.assertNotEqual(current["run_id"], "run-old-running")
        self.assertIn("create_run_shell", [item["action_type"] for item in result["folded_applied_actions"]])
        self.assertTrue((root / current["run_root"] / "run.json").exists())
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
        self.assertNotIn(current["run_id"], {"run-a", "run-b"})
        self.assertIn("create_run_shell", [item["action_type"] for item in result["folded_applied_actions"]])
        self.assertTrue((root / current["run_root"] / "run.json").exists())
        self.assertEqual(read_json(router.run_state_path(run_a)), state_a_before)
        self.assertEqual(read_json(router.run_state_path(run_b)), state_b_before)
        index = read_json(root / ".flowpilot" / "index.json")
        run_ids = {item["run_id"] for item in index["runs"]}
        self.assertTrue({"run-a", "run-b", current["run_id"]}.issubset(run_ids))
        self.assertEqual(next(item for item in index["runs"] if item["run_id"] == "run-a")["status"], "running")
        self.assertEqual(next(item for item in index["runs"] if item["run_id"] == "run-b")["status"], "running")

    def test_active_ui_catalog_exposes_parallel_run_targets_and_stale_residue(self) -> None:
        root = self.make_project()
        run_a = self.write_minimal_run(root, "run-a", status="controller_ready")
        self.write_minimal_run(root, "run-b", status="controller_ready")
        self.write_minimal_run(root, "run-old", status="stopped_by_user")
        self.write_current_focus(root, run_a)
        router.write_json(
            root / ".flowpilot" / "index.json",
            {
                "schema_version": "flowpilot.index.v1",
                "runs": [
                    {"run_id": "run-a", "run_root": ".flowpilot/runs/run-a", "status": "running"},
                    {"run_id": "run-b", "run_root": ".flowpilot/runs/run-b", "status": "running"},
                    {"run_id": "run-old", "run_root": ".flowpilot/runs/run-old", "status": "stopped_by_user"},
                ],
                "current_run_id": "run-a",
                "updated_at": router.utc_now(),
            },
        )
        state_a = read_json(router.run_state_path(run_a))

        catalog = router._active_ui_task_catalog(root, run_a, state_a)  # type: ignore[attr-defined]

        self.assertEqual(catalog["authority"], "explicit_active_set")
        self.assertEqual(catalog["scope_kind"], "parallel_runs")
        self.assertFalse(catalog["global_main_required"])
        self.assertTrue(catalog["operation_target_required"])
        self.assertEqual(catalog["operation_targets"]["current_focus"], "run:run-a")
        self.assertEqual(
            sorted(catalog["operation_targets"]["all_active"]["run_ids"]),
            ["run-a", "run-b"],
        )
        self.assertEqual(
            {item["run_id"]: item["target_id"] for item in catalog["active_tasks"]},
            {"run-a": "run:run-a", "run-b": "run:run-b"},
        )
        self.assertEqual([item["run_id"] for item in catalog["background_active_tasks"]], ["run-b"])
        self.assertEqual(
            [(item["run_id"], item["stale_residue"], item["operation_target_allowed"]) for item in catalog["stale_residue_tasks"]],
            [("run-old", True, False)],
        )

    def test_active_ui_catalog_keeps_block_scoped_agents_under_parent_flow_block(self) -> None:
        root = self.make_project()
        run_a = self.write_minimal_run(root, "run-a", status="controller_ready")
        self.write_current_focus(root, run_a)
        router.write_json(
            root / ".flowpilot" / "index.json",
            {
                "schema_version": "flowpilot.index.v1",
                "runs": [{"run_id": "run-a", "run_root": ".flowpilot/runs/run-a", "status": "running"}],
                "current_run_id": "run-a",
                "updated_at": router.utc_now(),
            },
        )
        state_a = read_json(router.run_state_path(run_a))
        state_a["active_flow_block_agents"] = [
            {
                "flow_block_id": "run-a",
                "agent_role": "worker",
                "result_target_id": "run:run-a",
                "status": "running",
            },
            {
                "flow_block_id": "run-a",
                "agent_role": "reviewer",
                "result_target_id": "run:run-a",
                "status": "waiting",
            },
        ]

        catalog = router._active_ui_task_catalog(root, run_a, state_a)  # type: ignore[attr-defined]

        self.assertEqual(catalog["scope_kind"], "block_scoped_agents")
        self.assertEqual(catalog["active_tasks"][0]["flow_block_id"], "run-a")
        self.assertEqual(catalog["active_tasks"][0]["target_id"], "run:run-a")
        self.assertEqual(
            {agent["agent_role"]: agent["result_target_id"] for agent in catalog["block_scoped_agents"]},
            {"worker": "run:run-a", "reviewer": "run:run-a"},
        )
    def test_cli_accepts_json_after_subcommand(self) -> None:
        parsed = router.parse_args(["--root", "C:/tmp/project", "next", "--json"])
        self.assertEqual(parsed.command, "next")
        self.assertTrue(parsed.json)

        parsed = router.parse_args(["--root", "C:/tmp/project", "run-until-wait", "--json"])
        self.assertEqual(parsed.command, "run-until-wait")
        self.assertTrue(parsed.json)

        with self.assertRaises(SystemExit):
            router.parse_args(["--root", "C:/tmp/project", "run-until-wait", "--new-invocation", "--json"])
        with self.assertRaises(SystemExit):
            router.parse_args(["--root", "C:/tmp/project", "next", "--new-invocation", "--json"])

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
        self.assertFalse(parsed.full)

        parsed = router.parse_args(["--root", "C:/tmp/project", "state", "--full", "--json"])
        self.assertEqual(parsed.command, "state")
        self.assertTrue(parsed.full)

        parsed = router.parse_args(["--root", "C:/tmp/project", "reconcile-run", "--json"])
        self.assertEqual(parsed.command, "reconcile-run")
        self.assertTrue(parsed.json)

    def test_state_command_compacts_controller_ledger_by_default(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-compact-state", status="controller_ready")
        self.write_current_focus(root, run_root)
        state = read_json(router.run_state_path(run_root))
        action = router.make_action(
            action_type="load_resume_state",
            actor="controller",
            label="controller_loads_resume_state",
            summary="Large row that should not be dumped by default.",
        )
        router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = router.main(["--root", str(root), "state", "--json"])
        payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0, payload)
        self.assertTrue(payload["compact"])
        self.assertIn("counts", payload["controller_action_ledger"])
        self.assertNotIn("actions", payload["controller_action_ledger"])

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = router.main(["--root", str(root), "state", "--full", "--json"])
        full_payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0, full_payload)
        self.assertFalse(full_payload["compact"])
        self.assertIn("actions", full_payload["controller_action_ledger"])
    def test_unsupported_high_risk_fold_commands_are_not_cli_commands(self) -> None:
        for command in (
            "deliver-card-bundle-checked",
            "relay-checked",
            "prepare-startup-fact-check",
            "record-role-output-checked",
        ):
            with self.assertRaises(SystemExit):
                with contextlib.redirect_stderr(io.StringIO()):
                    router.parse_args(["--root", "C:/tmp/project", command, "--json"])
    def test_skill_entrypoint_remains_small_flowpilot_new_launcher(self) -> None:
        skill_text = (ROOT / "skills" / "flowpilot" / "SKILL.md").read_text(encoding="utf-8")
        line_count = len(skill_text.splitlines())

        self.assertLess(line_count, 120)
        self.assertIn("flowpilot_new.py", skill_text)
        self.assertIn("Do not read FlowPilot reference files", skill_text)
        self.assertNotIn("Final Route-Wide Gate Ledger", skill_text)
