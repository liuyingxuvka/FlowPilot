from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase


class StartupBootstrapRuntimeTests(FlowPilotRouterRuntimeTestBase):
    def test_run_until_wait_applies_only_safe_startup_action(self) -> None:
        root = self.make_project()
        result = router.run_until_wait(root, new_invocation=True)
        self.assertEqual(result["action_type"], "open_startup_intake_ui")
        self.assertEqual(result["folded_command"], "run-until-wait")
        self.assertEqual(result["folded_applied_count"], 5)
        self.assertEqual(
            [item["action_type"] for item in result["folded_applied_actions"]],
            ["load_router", "create_run_shell", "write_current_pointer", "update_run_index", "start_router_daemon"],
        )
        self.assertTrue(result["startup_daemon_scheduled"])
        self.assertTrue(result["scheduled_by_router_daemon"])
        self.assertEqual(result["scope_kind"], "startup")
        self.assertEqual(result["controller_table_contract"], "simple_work_board")
        self.assertTrue(result["controller_action_id"])
        self.assertTrue(result["router_scheduler_row_id"])
        self.assertEqual(result["folded_stop_reason"], "requires_user_host_or_role_boundary")
        run_state = read_json(router.run_state_path(self.run_root_for(root)))
        self.assertTrue(run_state["flags"]["formal_router_daemon_started"])
        self.assertFalse(run_state["flags"]["controller_core_loaded"])
    def test_unsupported_scheduled_continuation_startup_answer_is_rejected(self) -> None:
        root = self.make_project()
        router.run_until_wait(root, new_invocation=True)
        with self.assertRaisesRegex(router.RouterError, "unsupported fields: scheduled_continuation"):
            router.apply_action(
                root,
                "open_startup_intake_ui",
                self.startup_intake_payload(root, startup_answers=UNSUPPORTED_HEARTBEAT_STARTUP_ANSWERS),
            )

    def test_manual_startup_writes_current_resume_binding_after_controller_core(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root, startup_answers=STARTUP_ANSWERS)
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["formal_router_daemon_started"])
        self.assertTrue(state["flags"]["controller_core_loaded"])
        continuation = read_json(run_root / "continuation" / "continuation_binding.json")
        self.assertEqual(continuation["mode"], "manual_resume")
        self.assertTrue(continuation["manual_resume_required"])
        self.assertTrue(continuation["manual_resume_binding_active"])
        self.assertFalse(continuation["host_automation_supported"])
        self.assertNotIn("host_heartbeat_supported", continuation)
        self.assertNotIn("heartbeat_active", continuation)
        self.assertNotIn("host_automation_verified", continuation)
    def test_formal_startup_starts_router_daemon_before_controller_core(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_router_daemon_start(root)

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "start_router_daemon")
        self.assertTrue(action["startup_readiness_contract"]["failure_blocks_controller_core"])
        result = router.apply_action(root, "start_router_daemon")
        self.assertTrue(result["router_daemon_ready"])
        self.assertFalse(result["attached_existing_daemon"])

        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["daemon_mode_enabled"])
        self.assertTrue(state["flags"]["formal_router_daemon_started"])
        self.assertEqual(read_json(run_root / "runtime" / "router_daemon.lock")["status"], "active")
        self.assertEqual(read_json(run_root / "runtime" / "router_daemon_status.json")["tick_interval_seconds"], 1)
        self.assertEqual(
            read_json(run_root / "runtime" / "controller_action_ledger.json")["schema_version"],
            router.CONTROLLER_ACTION_LEDGER_SCHEMA,
        )

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "open_startup_intake_ui")
        self.assertTrue(action["startup_daemon_scheduled"])
        self.assertTrue(action["scheduled_by_router_daemon"])
        entry = read_json(run_root / "runtime" / "controller_actions" / f"{action['controller_action_id']}.json")
        self.assertEqual(entry["action_type"], "open_startup_intake_ui")
        self.assertEqual(entry["scope_kind"], "startup")
        self.assertIn("Router daemon status", entry["action"]["plain_instruction"])
        self.assertIn("Controller action ledger", entry["action"]["plain_instruction"])
        self.assertNotIn("apply this pending action", entry["action"]["plain_instruction"])
        self.assertNotIn("apply its confirmed or cancelled result", entry["action"]["summary"])
        scheduler = read_json(run_root / "runtime" / "router_scheduler_ledger.json")
        row = next(item for item in scheduler["rows"] if item["row_id"] == action["router_scheduler_row_id"])
        self.assertEqual(row["scope_kind"], "startup")
        self.assertEqual(row["barrier_kind"], "external_barrier")
        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"]["controller_core_loaded"])
    def test_startup_daemon_defers_banner_and_queues_next_boot_row(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_router_daemon_start(root)
        router.apply_action(root, "start_router_daemon")

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "open_startup_intake_ui")
        router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "load_controller_core")
        bootstrap = self.bootstrap_state(root)
        self.assertEqual(bootstrap["pending_action"]["action_type"], "load_controller_core")
        self.assertTrue(bootstrap["flags"]["deterministic_bootstrap_seed_completed"])
        self.assertTrue((run_root / "bootstrap" / "deterministic_bootstrap_seed_evidence.json").exists())

        controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        banner_rows = [item for item in controller_ledger["actions"] if item.get("action_type") == "emit_startup_banner"]
        self.assertEqual(len(banner_rows), 0)
        startup_types = [item.get("action_type") for item in controller_ledger["actions"] if item.get("scope_kind") == "startup"]
        self.assertNotIn("emit_startup_banner", startup_types)
        self.assertNotIn("start_role_slots", startup_types)
        self.assertNotIn("create_heartbeat_automation", startup_types)
        self.assertNotIn("fill_runtime_placeholders", startup_types)
        self.assertNotIn("initialize_mailbox", startup_types)
        self.assertNotIn("record_user_request", startup_types)
        self.assertNotIn("write_user_intake", startup_types)
        self.assertFalse(bootstrap["flags"].get("banner_emitted", False))

        router.apply_action(root, "load_controller_core")
        controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        banner_rows = [item for item in controller_ledger["actions"] if item.get("action_type") == "emit_startup_banner"]
        self.assertEqual(len(banner_rows), 1)
        banner_record = read_json(run_root / "runtime" / "controller_actions" / f"{banner_rows[0]['action_id']}.json")
        self.assertEqual(banner_record["status"], "pending")
        self.assertEqual(banner_record["action"]["router_scheduler_progress_class"], "parallel_obligation")
    def test_deterministic_bootstrap_seed_failure_does_not_create_pm_blocker(self) -> None:
        root = self.make_project()
        self.boot_to_router_daemon_start(root)
        router.apply_action(root, "start_router_daemon")

        with mock.patch.object(
            router,
            "_initialize_mailbox_foundation",
            side_effect=router.RouterError("seed mailbox failed"),
        ):
            with self.assertRaisesRegex(router.RouterError, "seed mailbox failed"):
                router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))

        run_root = self.run_root_for(root)
        control_blocks = run_root / "control_blocks"
        self.assertFalse(control_blocks.exists() and list(control_blocks.glob("*.json")))
    def test_deterministic_bootstrap_seed_replay_uses_existing_evidence(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_router_daemon_start(root)
        router.apply_action(root, "start_router_daemon")
        router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))

        return_ledger_path = run_root / "return_event_ledger.json"
        return_ledger = read_json(return_ledger_path)
        return_ledger["pending_returns"].append({"return_id": "existing-return", "source": "test"})
        router.write_json(return_ledger_path, return_ledger)

        proof = router._run_deterministic_startup_bootstrap_seed(root, self.bootstrap_state(root))  # type: ignore[attr-defined]

        self.assertTrue(proof["completed"])
        refreshed_return_ledger = read_json(return_ledger_path)
        self.assertEqual(
            [item["return_id"] for item in refreshed_return_ledger["pending_returns"]],
            ["existing-return"],
        )
    def test_startup_seed_writes_portable_flowguard_capability_snapshot(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_router_daemon_start(root)
        router.apply_action(root, "start_router_daemon")
        router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))

        snapshot_path = run_root / "flowguard" / "capability_snapshot.json"
        self.assertTrue(snapshot_path.exists())
        snapshot = read_json(snapshot_path)
        self.assertEqual(snapshot["generated_by_role_key"], "router")
        self.assertTrue(snapshot["policy"]["flowguard_is_required_foundation"])
        self.assertFalse(snapshot["policy"]["ordinary_child_skill"])
        self.assertFalse(snapshot["portable_resolution"]["hardcoded_user_path_required"])
        self.assertEqual(snapshot["portable_resolution"]["generator"], "flowpilot_router_startup_seed")
        self.assertIn("python_executable", snapshot["flowguard_import"])
        self.assertTrue(snapshot["pm_summary"]["must_read_before_product_modeling"])
        self.assertTrue(snapshot["pm_summary"]["final_ledger_must_close_all_model_families"])

        proof = read_json(run_root / "bootstrap" / "deterministic_bootstrap_seed_evidence.json")
        self.assertTrue(proof["required_flags"]["flowguard_capability_snapshot_written"])
        self.assertIn("flowguard_capability_snapshot", proof["artifacts"])
        bootstrap = self.bootstrap_state(root)
        self.assertTrue(bootstrap["flags"]["flowguard_capability_snapshot_written"])
        self.assertEqual(
            bootstrap["flowguard_capability_snapshot_path"],
            self.rel(root, snapshot_path),
        )
    def test_flowguard_snapshot_discovers_codex_home_flowguard_skills(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-test")
        fake_codex = Path(tempfile.mkdtemp(prefix="flowpilot-codex-home-"))
        fake_skill = fake_codex / "skills" / "flowguard-ui-flow-structure"
        fake_skill.mkdir(parents=True, exist_ok=True)
        (fake_skill / "SKILL.md").write_text(
            "---\nname: flowguard-ui-flow-structure\n---\n\n# FlowGuard UI\n",
            encoding="utf-8",
        )

        state = {"run_id": "run-test", "flags": {}}
        with mock.patch.dict(os.environ, {"CODEX_HOME": str(fake_codex)}):
            summary = router._write_flowguard_capability_snapshot(root, run_root, state)  # type: ignore[attr-defined]

        snapshot = read_json(root / summary["path"])
        routes = {item["skill_name"]: item for item in snapshot["skill_routes"]}
        self.assertIn("flowguard-ui-flow-structure", routes)
        self.assertIn("ui_interaction", routes["flowguard-ui-flow-structure"]["model_family_fit"])
        self.assertFalse(snapshot["portable_resolution"]["hardcoded_user_path_required"])
        self.assertIn(str((fake_codex / "skills").resolve()), snapshot["portable_resolution"]["search_roots"])
        self.assertEqual(state["flowguard_capability_snapshot_path"], self.rel(root, run_root / "flowguard" / "capability_snapshot.json"))
    def test_startup_daemon_bootloader_completion_uses_receipt_owner(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_router_daemon_start(root)
        router.apply_action(root, "start_router_daemon")
        router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))

        controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        intake_row = next(item for item in controller_ledger["actions"] if item.get("action_type") == "open_startup_intake_ui")
        action_path = run_root / "runtime" / "controller_actions" / f"{intake_row['action_id']}.json"
        entry = read_json(action_path)
        reconciliation = entry["router_reconciliation"]

        self.assertEqual(entry["router_reconciliation_status"], "reconciled")
        self.assertEqual(reconciliation["source"], "startup_bootloader_controller_receipt")
        self.assertNotEqual(reconciliation["source"], "startup_daemon_bootloader_postcondition")
        scheduler = read_json(run_root / "runtime" / "router_scheduler_ledger.json")
        scheduler_row = next(item for item in scheduler["rows"] if item.get("row_id") == intake_row["router_scheduler_row_id"])
        self.assertEqual(scheduler_row["router_state"], "reconciled")
        self.assertEqual(scheduler_row["reconciliation"]["source"], "startup_bootloader_controller_receipt")
    def test_load_controller_core_receipt_reconciles_startup_postcondition(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_router_daemon_start(root)
        router.apply_action(root, "start_router_daemon")
        router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "load_controller_core")

        state = read_json(router.run_state_path(run_root))
        router._write_controller_receipt(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            action_id=action["controller_action_id"],
            status="done",
            payload={"controller_action_completed": True},
        )
        state = read_json(router.run_state_path(run_root))
        result = router._reconcile_scheduled_controller_action_receipts(root, run_root, state)  # type: ignore[attr-defined]

        self.assertTrue(result["changed"])
        self.assertEqual(result["blocked"], 0)
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["controller_core_loaded"])
        self.assertEqual(state["status"], "controller_ready")
        self.assertFalse(state.get("active_control_blocker"))
    def test_startup_reconciliation_resolves_stale_blocker_and_supersedes_pm_row(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_router_daemon_start(root)
        router.apply_action(root, "start_router_daemon")
        router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "load_controller_core")

        state = read_json(router.run_state_path(run_root))
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="controller_action_receipt_missing_router_postcondition",
            error_message=(
                "Controller action load_controller_core was marked done, but Router could not "
                "apply its required postcondition before reconciliation."
            ),
            action_type="load_controller_core",
            payload={
                "controller_action_id": action["controller_action_id"],
                "router_scheduler_row_id": action["router_scheduler_row_id"],
                "postcondition": "controller_core_loaded",
                "direct_retry_attempts_used": 2,
                "direct_retry_budget": 2,
            },
        )
        self.assertEqual(blocker["policy_row_id"], "mechanical_control_plane_reissue")
        self.assertTrue(blocker["direct_retry_budget_exhausted"])
        state = read_json(router.run_state_path(run_root))
        stale_pm_action = router._next_control_blocker_action(root, state, run_root)  # type: ignore[attr-defined]
        self.assertIsNotNone(stale_pm_action)
        self.assertEqual(stale_pm_action["action_type"], "handle_control_blocker")
        self.assertEqual(stale_pm_action["to_role"], "project_manager")
        stale_pm_action = router._prepare_router_scheduled_action(root, run_root, state, stale_pm_action)  # type: ignore[attr-defined]
        stale_pm_entry = router._write_controller_action_entry(root, run_root, state, stale_pm_action)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)

        router.apply_action(root, "load_controller_core")

        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state.get("active_control_blocker"))
        blocker_record = read_json(self.control_blocker_path(root, blocker))
        self.assertEqual(blocker_record["resolution_status"], "resolved_by_startup_reconciliation")
        self.assertEqual(blocker_record["resolved_by_controller_action_id"], action["controller_action_id"])
        stale_pm_entry = read_json(router._controller_action_path(run_root, stale_pm_entry["action_id"]))  # type: ignore[attr-defined]
        self.assertEqual(stale_pm_entry["status"], "superseded")
        self.assertEqual(
            stale_pm_entry["router_reconciliation_status"],
            "superseded_by_resolved_control_blocker",
        )
        self.assertNotEqual((self.bootstrap_state(root).get("pending_action") or {}).get("action_type"), "handle_control_blocker")
    def test_startup_missing_router_postcondition_retries_before_pm_blocker(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_router_daemon_start(root)
        router.apply_action(root, "start_router_daemon")
        router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "load_controller_core")

        status_path = run_root / "runtime" / "router_daemon_status.json"
        status = read_json(status_path)
        status["daemon_mode_enabled"] = False
        router.write_json(status_path, status)

        state = read_json(router.run_state_path(run_root))
        router._write_controller_receipt(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            action_id=action["controller_action_id"],
            status="done",
            payload={"controller_action_completed": True},
        )

        for expected_attempt in (1, 2):
            state = read_json(router.run_state_path(run_root))
            result = router._reconcile_scheduled_controller_action_receipts(root, run_root, state)  # type: ignore[attr-defined]
            self.assertTrue(result["changed"])
            self.assertEqual(result["blocked"], 0)
            state = read_json(router.run_state_path(run_root))
            entry = read_json(router._controller_action_path(run_root, action["controller_action_id"]))  # type: ignore[attr-defined]
            self.assertEqual(entry["router_reconciliation_status"], "retry_pending")
            self.assertEqual(entry["postcondition_reconciliation_attempts"], expected_attempt)
            self.assertEqual(entry["max_postcondition_reconciliation_attempts"], 2)
            self.assertFalse(entry["postcondition_reconciliation_exhausted"])
            self.assertFalse(state.get("active_control_blocker"))

        state = read_json(router.run_state_path(run_root))
        result = router._reconcile_scheduled_controller_action_receipts(root, run_root, state)  # type: ignore[attr-defined]
        self.assertTrue(result["changed"])
        self.assertEqual(result["blocked"], 1)
        state = read_json(router.run_state_path(run_root))
        blocker = state["active_control_blocker"]
        self.assertEqual(blocker["handling_lane"], "pm_repair_decision_required")
        self.assertEqual(blocker["policy_row_id"], "mechanical_control_plane_reissue")
        self.assertEqual(blocker["target_role"], "project_manager")
        self.assertEqual(blocker["direct_retry_budget"], 2)
        self.assertEqual(blocker["direct_retry_attempts_used"], 2)
        self.assertTrue(blocker["direct_retry_budget_exhausted"])
    def test_startup_daemon_queues_controller_core_without_legacy_role_or_automation_wait(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_router_daemon_start(root, startup_answers=STARTUP_ANSWERS)
        router.apply_action(root, "start_router_daemon")
        router.apply_action(
            root,
            "open_startup_intake_ui",
            self.startup_intake_payload(root, startup_answers=STARTUP_ANSWERS),
        )

        while True:
            action = router.next_action(root)
            action_type = str(action["action_type"])
            if action_type == "load_controller_core":
                break
            self.assertNotIn(action_type, {"emit_startup_banner", "start_role_slots", "create_heartbeat_automation"})
            if action_type == "record_user_request":
                router.apply_action(root, action_type)
            else:
                router.apply_action(root, action_type, self.payload_for_action(action))

        controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        startup_types = [item.get("action_type") for item in controller_ledger["actions"] if item.get("scope_kind") == "startup"]
        self.assertEqual(startup_types.count("emit_startup_banner"), 0)
        self.assertEqual(startup_types.count("start_role_slots"), 0)
        self.assertEqual(startup_types.count("create_heartbeat_automation"), 0)
        self.assertNotIn("inject_role_core_prompts", startup_types)
        self.assertEqual(self.bootstrap_state(root)["pending_action"]["action_type"], "load_controller_core")

        router.apply_action(root, "load_controller_core", self.payload_for_action(action))
        controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        startup_types = [item.get("action_type") for item in controller_ledger["actions"] if item.get("scope_kind") == "startup"]
        self.assertEqual(startup_types.count("emit_startup_banner"), 1)
        self.assertEqual(startup_types.count("start_role_slots"), 0)
        self.assertEqual(startup_types.count("create_heartbeat_automation"), 0)
        state = read_json(router.run_state_path(run_root))
        blockers = router._startup_pre_review_reconciliation_blockers(root, run_root, state)  # type: ignore[attr-defined]
        blocker_kinds = [item["kind"] for item in blockers]
        self.assertIn("pending_startup_controller_row", blocker_kinds)
        self.assertIn("missing_startup_flag", blocker_kinds)
    def test_startup_async_receipts_update_bootstrap_flags_and_scheduler_rows(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_router_daemon_start(root, startup_answers=STARTUP_ANSWERS)
        router.apply_action(root, "start_router_daemon")
        router.apply_action(
            root,
            "open_startup_intake_ui",
            self.startup_intake_payload(root, startup_answers=STARTUP_ANSWERS),
        )
        while True:
            action = router.next_action(root)
            if action["action_type"] == "load_controller_core":
                break
            payload = {} if action["action_type"] == "record_user_request" else self.payload_for_action(action)
            router.apply_action(root, str(action["action_type"]), payload)

        router.apply_action(root, "load_controller_core", self.payload_for_action(action))
        completed = self.complete_startup_async_controller_rows(root, startup_answers=STARTUP_ANSWERS)
        self.assertEqual(set(completed), {"emit_startup_banner"})

        bootstrap = self.bootstrap_state(root)
        self.assertTrue(bootstrap["flags"]["banner_emitted"])
        self.assertFalse(bootstrap["flags"].get("roles_started", False))
        self.assertFalse(bootstrap["flags"].get("role_core_prompts_injected", False))
        self.assertFalse(bootstrap["flags"].get("continuation_binding_recorded", False))
        scheduler = read_json(run_root / "runtime" / "router_scheduler_ledger.json")
        async_rows = [
            item
            for item in scheduler["rows"]
            if item.get("action_type") in {"emit_startup_banner", "start_role_slots", "create_heartbeat_automation"}
        ]
        self.assertEqual(len(async_rows), 1)
        self.assertTrue(all(item["router_state"] == "reconciled" for item in async_rows))
    def test_formal_startup_daemon_failure_blocks_controller_core(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_router_daemon_start(root)

        with mock.patch.object(router, "_spawn_startup_router_daemon_process", side_effect=router.RouterError("daemon launch failed")):
            with self.assertRaisesRegex(router.RouterError, "daemon launch failed"):
                router.apply_action(root, "start_router_daemon")

        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"]["controller_core_loaded"])
        self.assertTrue(state["flags"]["router_daemon_start_failed"])
        self.assertEqual(router.next_action(root)["action_type"], "start_router_daemon")
    def test_formal_startup_attaches_same_run_live_daemon_without_duplicate_spawn(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_router_daemon_start(root)
        router.run_router_daemon(root, max_ticks=1, observe_only=True, release_lock_on_exit=False)

        with mock.patch.object(
            router,
            "_spawn_startup_router_daemon_process",
            side_effect=AssertionError("startup should attach to the existing daemon"),
        ):
            result = router.apply_action(root, "start_router_daemon")

        self.assertTrue(result["router_daemon_ready"])
        self.assertTrue(result["attached_existing_daemon"])
        self.assertEqual(read_json(run_root / "runtime" / "router_daemon.lock")["status"], "active")
    def test_router_daemon_queues_visible_startup_rows_after_internal_audit(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "write_display_surface_status")

        result = router.run_router_daemon(root, max_ticks=1, release_lock_on_exit=True)

        tick = result["ticks"][0]
        self.assertGreaterEqual(tick["queued_count"], 1)
        queued_types = [item["action_type"] for item in tick["queued_actions"]]
        self.assertNotIn("write_startup_mechanical_audit", queued_types)
        self.assertIn("write_display_surface_status", queued_types)
        self.assertIn("write_startup_mechanical_audit", self.router_internal_action_types(root))
        self.assertIn(tick["queue_stop_reason"], {"barrier", "passive_wait_status"})
        scheduler = read_json(run_root / "runtime" / "router_scheduler_ledger.json")
        self.assertEqual(scheduler["schema_version"], router.ROUTER_SCHEDULER_LEDGER_SCHEMA)
        self.assertTrue(scheduler["router_is_only_scheduler_writer"])
        controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        startup_rows = [item for item in controller_ledger["actions"] if item.get("scope_kind") == "startup"]
        self.assertGreaterEqual(len(startup_rows), 1)
        self.assertNotIn("write_startup_mechanical_audit", [item.get("action_type") for item in startup_rows])
        for row in startup_rows:
            record = read_json(run_root / "runtime" / "controller_actions" / f"{row['action_id']}.json")
            self.assertEqual(record["dependencies"], [])
            self.assertTrue(record["router_scheduler_row_id"])
    def test_startup_obligations_are_not_global_scheduler_barriers(self) -> None:
        root = self.make_project()
        run_root = root / "run"
        run_root.mkdir(parents=True)
        run_state = {"run_id": "test-run"}

        cases = (
            (
                "emit_startup_banner",
                "parallel_obligation",
                {"card_id": "startup_banner", "requires_user_dialog_display_confirmation": True},
            ),
            (
                "write_display_surface_status",
                "parallel_obligation",
                {"requires_user_dialog_display_confirmation": True},
            ),
        )

        for action_type, progress_class, extra in cases:
            with self.subTest(action_type=action_type):
                action = router.make_action(
                    action_type=action_type,
                    actor="bootloader" if action_type != "write_display_surface_status" else "controller",
                    label=f"test_{action_type}",
                    summary=f"Test scheduler classification for {action_type}.",
                    extra=extra,
                )
                prepared = router._prepare_router_scheduled_action(root, run_root, run_state, action)  # type: ignore[attr-defined]
                self.assertEqual(prepared["scope_kind"], "startup")
                self.assertEqual(prepared["router_scheduler_progress_class"], progress_class)
                self.assertEqual(prepared["router_scheduler_barrier_kind"], "none")
                self.assertTrue(router._router_daemon_can_continue_after_enqueued_action(prepared))  # type: ignore[attr-defined]
    def test_startup_bootloader_already_reconciled_backfills_scheduler_row(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        bootstrap = self.bootstrap_state(root)
        controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        row = next(item for item in controller_ledger["actions"] if item.get("action_type") == "emit_startup_banner")
        action_path = run_root / "runtime" / "controller_actions" / f"{row['action_id']}.json"
        action_record = read_json(action_path)

        scheduler_path = run_root / "runtime" / "router_scheduler_ledger.json"
        scheduler = read_json(scheduler_path)
        scheduler_row = next(item for item in scheduler["rows"] if item.get("row_id") == row["router_scheduler_row_id"])
        scheduler_row["router_state"] = "receipt_done"
        scheduler_row.pop("reconciled_at", None)
        router.write_json(scheduler_path, scheduler)

        result = router._complete_startup_daemon_bootloader_row(  # type: ignore[attr-defined]
            root,
            bootstrap,
            action_record["action"],
            applied_action_type="emit_startup_banner",
        )

        self.assertTrue(result["already_reconciled"])
        self.assertTrue(result["scheduler_backfill"]["changed"])
        refreshed_scheduler = read_json(scheduler_path)
        refreshed_row = next(
            item for item in refreshed_scheduler["rows"] if item.get("row_id") == row["router_scheduler_row_id"]
        )
        self.assertEqual(refreshed_row["router_state"], "reconciled")
        self.assertEqual(
            refreshed_row["reconciliation"]["scheduler_backfill_source"],
            "startup_bootloader_already_reconciled_scheduler_backfill",
        )
    def test_startup_bootloader_receipt_updates_bootstrap_and_scheduler_row(self) -> None:
        root = self.make_project()
        router.run_until_wait(root, new_invocation=True)
        router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))
        load_action = router.run_until_wait(root)
        self.assertEqual(load_action["action_type"], "load_controller_core")
        router.apply_action(root, "load_controller_core", self.payload_for_action(load_action))
        run_root = self.run_root_for(root)
        controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        banner_row = next(item for item in controller_ledger["actions"] if item["action_type"] == "emit_startup_banner")
        action_id = banner_row["action_id"]
        action_record = read_json(run_root / "runtime" / "controller_actions" / f"{action_id}.json")
        action = action_record["action"]
        row_id = action["router_scheduler_row_id"]

        result = router.record_controller_action_receipt(
            root,
            action_id=action_id,
            status="done",
            payload=self.payload_for_action(action),
        )

        self.assertTrue(result["ok"])
        bootstrap = self.bootstrap_state(root)
        self.assertTrue(bootstrap["flags"]["banner_emitted"])
        self.assertNotEqual((bootstrap.get("pending_action") or {}).get("controller_action_id"), action_id)
        action_record = read_json(run_root / "runtime" / "controller_actions" / f"{action_id}.json")
        self.assertEqual(action_record["router_reconciliation_status"], "reconciled")
        scheduler = read_json(run_root / "runtime" / "router_scheduler_ledger.json")
        row = next(item for item in scheduler["rows"] if item["row_id"] == row_id)
        self.assertEqual(row["router_state"], "reconciled")
        self.assertNotEqual((self.bootstrap_state(root).get("pending_action") or {}).get("action_type"), "emit_startup_banner")
    def test_startup_intake_controller_receipt_folds_native_ui_result(self) -> None:
        root = self.make_project()
        action = router.run_until_wait(root, new_invocation=True)
        self.assertEqual(action["action_type"], "open_startup_intake_ui")
        run_root = self.run_root_for(root)
        controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        intake_row = next(item for item in controller_ledger["actions"] if item["action_type"] == "open_startup_intake_ui")
        action_id = intake_row["action_id"]
        row_id = intake_row["router_scheduler_row_id"]

        result = router.record_controller_action_receipt(
            root,
            action_id=action_id,
            status="done",
            payload=self.startup_intake_payload(root),
        )

        self.assertTrue(result["ok"])
        bootstrap = self.bootstrap_state(root)
        self.assertEqual(bootstrap["startup_state"], "answers_complete")
        self.assertEqual(bootstrap["startup_answers"], STARTUP_ANSWERS)
        self.assertIsNone(bootstrap.get("pending_action"))
        self.assertTrue(bootstrap["flags"]["startup_intake_ui_completed"])
        self.assertTrue(bootstrap["flags"]["startup_intake_result_recorded"])
        self.assertTrue(bootstrap["flags"]["startup_intake_body_boundary_enforced"])
        self.assertTrue(bootstrap["flags"]["startup_answers_recorded"])
        self.assertTrue((run_root / "startup_answers.json").exists())

        run_state = read_json(router.run_state_path(run_root))
        self.assertTrue(run_state["flags"]["startup_intake_ui_completed"])
        self.assertTrue(run_state["flags"]["startup_intake_result_recorded"])
        self.assertTrue(run_state["flags"]["startup_intake_body_boundary_enforced"])
        self.assertTrue(run_state["flags"]["startup_answers_recorded"])
        action_record = read_json(run_root / "runtime" / "controller_actions" / f"{action_id}.json")
        self.assertEqual(action_record["router_reconciliation_status"], "reconciled")
        self.assertEqual(action_record["router_reconciliation"]["source"], "startup_bootloader_controller_receipt")
        self.assertEqual(action_record["router_reconciliation"]["action_type"], "open_startup_intake_ui")
        scheduler = read_json(run_root / "runtime" / "router_scheduler_ledger.json")
        row = next(item for item in scheduler["rows"] if item["row_id"] == row_id)
        self.assertEqual(row["router_state"], "reconciled")
        self.assertEqual(row["reconciliation"]["source"], "startup_bootloader_controller_receipt")
        control_blocks = run_root / "control_blocks"
        self.assertFalse(control_blocks.exists() and list(control_blocks.glob("*.json")))

        next_action = router.run_until_wait(root)
        self.assertEqual(next_action["action_type"], "load_controller_core")

    def test_startup_seed_projection_prevents_reissued_answer_row_after_stale_daemon_snapshot(self) -> None:
        root = self.make_project()
        router.run_until_wait(root, new_invocation=True)
        run_root = self.run_root_for(root)
        router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))
        completed = self.bootstrap_state(root)
        self.assertTrue(completed["flags"]["deterministic_bootstrap_seed_completed"])
        self.assertTrue((run_root / "bootstrap" / "deterministic_bootstrap_seed_evidence.json").exists())

        stale = json.loads(json.dumps(completed))
        stale["startup_answers"] = None
        stale["startup_state"] = "awaiting_answers_stopped"
        for flag in (
            "startup_answers_recorded",
            "deterministic_bootstrap_seed_completed",
            "placeholders_filled",
            "mailbox_initialized",
            "user_request_recorded",
            "user_intake_ready",
            "flowguard_capability_snapshot_written",
        ):
            stale["flags"][flag] = False
        stale["pending_action"] = None
        router.write_json(router.bootstrap_state_path(root), stale)

        run_state = read_json(router.run_state_path(run_root))
        schedule = router._startup_daemon_schedule_bootloader_action(  # type: ignore[attr-defined]
            root,
            run_root,
            run_state,
            source="test_stale_startup_seed_projection",
        )

        self.assertTrue(schedule["scheduled"])
        self.assertEqual(schedule["action"]["action_type"], "load_controller_core")
        queued = [item["action_type"] for item in schedule["queued_actions"]]
        self.assertEqual(queued, ["load_controller_core"])
        bootstrap = self.bootstrap_state(root)
        self.assertEqual(bootstrap["startup_answers"], STARTUP_ANSWERS)
        self.assertTrue(bootstrap["flags"]["startup_answers_recorded"])
        self.assertTrue(bootstrap["flags"]["deterministic_bootstrap_seed_completed"])
        self.assertFalse(bootstrap["flags"].get("current_background_collaboration_opened", False))
        control_blocks = run_root / "control_blocks"
        self.assertFalse(control_blocks.exists() and list(control_blocks.glob("*.json")))
    def test_startup_review_join_checks_bootstrap_banner_and_role_flags(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        bootstrap = self.bootstrap_state(root)
        bootstrap["flags"]["banner_emitted"] = False
        router.write_json(router.bootstrap_state_path(root), bootstrap)

        blockers = router._startup_pre_review_reconciliation_blockers(root, run_root, state)  # type: ignore[attr-defined]
        missing_flags = {
            blocker.get("flag")
            for blocker in blockers
            if blocker.get("kind") == "missing_startup_bootstrap_flag"
        }
        self.assertIn("banner_emitted", missing_flags)
        self.assertNotIn("roles_started", missing_flags)
    def test_startup_rejects_legacy_reviewer_event_before_pm_work(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.deliver_startup_runtime_prompt_cards(root)

        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "reviewer_reports_startup_facts",
                self.role_report_envelope(
                    root,
                    "startup/legacy_reviewer_report_before_pm_work",
                    self.legacy_startup_fact_report_body(root),
                ),
            )

        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"].get("startup_fact_reported", False))
        self.assertFalse((run_root / "startup" / "startup_fact_report.json").exists())

    def test_startup_rejects_legacy_startup_fact_role_output_ledger(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        self.submit_legacy_startup_fact_runtime_output_to_ledger(root)

        before = read_json(router.run_state_path(run_root))
        self.assertFalse(before["flags"].get("startup_fact_reported", False))
        router.run_router_daemon(root, max_ticks=1, release_lock_on_exit=True)

        after = read_json(router.run_state_path(run_root))
        self.assertFalse(after["flags"].get("startup_fact_reported", False))
        self.assertFalse((run_root / "startup" / "startup_fact_report.json").exists())
        self.assertFalse(any(
            isinstance(item, dict) and item.get("event") == "reviewer_reports_startup_facts"
            for item in after.get("events", [])
        ))
    def test_startup_intake_cancel_is_terminal_after_daemon_first_shell(self) -> None:
        root = self.make_project()
        router.run_until_wait(root, new_invocation=True)
        payload = self.startup_intake_payload(root, status="cancelled")
        result = router.apply_action(root, "open_startup_intake_ui", payload)
        self.assertEqual(result["startup_intake"]["status"], "cancelled")
        bootstrap = self.bootstrap_state(root)
        self.assertEqual(bootstrap["status"], "startup_cancelled")
        self.assertEqual(bootstrap["startup_state"], "startup_cancelled")
        self.assertTrue(bootstrap["flags"]["run_shell_created"])
        self.assertTrue(bootstrap["flags"]["router_daemon_started"])
        self.assertTrue((root / bootstrap["run_root"] / "run.json").exists())
        self.assertTrue((root / bootstrap["run_root"] / "router_state.json").exists())
        run_state = read_json(router.run_state_path(self.run_root_for(root)))
        self.assertFalse(run_state["flags"]["controller_core_loaded"])
        self.assertFalse(bootstrap["flags"].get("roles_started", False))
        self.assertFalse(run_state["flags"]["continuation_binding_recorded"])
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "startup_cancelled")
        self.assertTrue(action["terminal"])

    def test_startup_intake_background_ack_disabled_blocks_startup(self) -> None:
        root = self.make_project()
        router.run_until_wait(root, new_invocation=True)
        answers = {**STARTUP_ANSWERS, "background_collaboration_authorized": False}
        payload = self.startup_intake_payload(root, startup_answers=answers, status="blocked")
        result = router.apply_action(root, "open_startup_intake_ui", payload)
        self.assertEqual(result["startup_intake"]["status"], "blocked")
        self.assertEqual(result["startup_intake"]["block_reason"], "background_collaboration_required")
        bootstrap = self.bootstrap_state(root)
        self.assertEqual(bootstrap["status"], "startup_blocked")
        self.assertEqual(bootstrap["startup_state"], "startup_blocked")
        self.assertFalse(bootstrap["flags"]["controller_core_loaded"])
        self.assertFalse(bootstrap["flags"].get("roles_started", False))
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "startup_blocked")
        self.assertTrue(action["terminal"])

    def test_startup_intake_rejects_confirmed_background_ack_disabled(self) -> None:
        root = self.make_project()
        router.run_until_wait(root, new_invocation=True)
        answers = {**STARTUP_ANSWERS, "background_collaboration_authorized": False}
        payload = self.startup_intake_payload(root, startup_answers=answers)
        with self.assertRaisesRegex(router.RouterError, "background_collaboration_authorized=true"):
            router.apply_action(root, "open_startup_intake_ui", payload)

    def test_startup_does_not_schedule_background_role_prewarm_action(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_router_daemon_start(root)
        router.apply_action(root, "start_router_daemon")
        router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))

        seen_actions: list[str] = []
        while True:
            action = router.next_action(root)
            action_type = action["action_type"]
            if action_type == "load_controller_core":
                break
            seen_actions.append(action_type)
            self.assertNotEqual(action_type, "bind_background_role_agents")
            router.apply_action(root, action_type, self.payload_for_action(action))

        self.assertNotIn("bind_background_role_agents", seen_actions)
        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"].get("background_role_agents_bound", False))
        self.assertFalse(state["flags"].get("current_background_collaboration_opened", False))
        self.assertFalse((run_root / "role_binding_ledger.json").exists())

    def test_startup_intake_rejects_body_hash_mismatch(self) -> None:
        root = self.make_project()
        router.run_until_wait(root, new_invocation=True)
        payload = self.startup_intake_payload(root)
        result_path = root / payload["startup_intake_result"]["result_path"]
        result = read_json(result_path)
        (root / result["body_path"]).write_text("changed after receipt", encoding="utf-8")
        with self.assertRaisesRegex(router.RouterError, "body hash mismatch"):
            router.apply_action(root, "open_startup_intake_ui", payload)
    def test_startup_intake_rejects_body_text_in_controller_payload(self) -> None:
        root = self.make_project()
        router.run_until_wait(root, new_invocation=True)
        payload = self.startup_intake_payload(root)
        result_path = root / payload["startup_intake_result"]["result_path"]
        result = read_json(result_path)
        result["body_text"] = USER_REQUEST["text"]
        result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(router.RouterError, "forbidden body text fields"):
            router.apply_action(root, "open_startup_intake_ui", payload)
    def test_startup_intake_rejects_headless_confirmed_result(self) -> None:
        root = self.make_project()
        router.run_until_wait(root, new_invocation=True)
        payload = self.startup_intake_payload(
            root,
            launch_mode="headless",
            headless=True,
            formal_startup_allowed=False,
        )
        with self.assertRaisesRegex(router.RouterError, "native interactive startup intake UI"):
            router.apply_action(root, "open_startup_intake_ui", payload)
    def test_startup_sequence_creates_prompt_isolated_run(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        bootstrap = self.bootstrap_state(root)
        self.assertTrue(bootstrap["router_loaded"])
        self.assertEqual(bootstrap["bootstrap_scope"], "run_scoped")
        self.assertEqual(root / bootstrap["run_root"], run_root)
        self.assertGreaterEqual(bootstrap["bootloader_actions"], 6)
        self.assertGreaterEqual(bootstrap["router_action_requests"], 7)
        self.assertIsNone(bootstrap["pending_action"])
        self.assertEqual(bootstrap["startup_answers"], STARTUP_ANSWERS)
        self.assertEqual(bootstrap["user_request"]["schema_version"], router.USER_REQUEST_REF_SCHEMA)
        self.assertFalse(bootstrap["user_request"]["controller_may_read_body"])
        self.assertFalse(bootstrap["flags"].get("role_core_prompts_injected", False))
        self.assertTrue(bootstrap["flags"]["router_daemon_started"])

        self.assertTrue((run_root / "runtime_kit" / "manifest.json").exists())
        self.assertTrue((run_root / "packet_ledger.json").exists())
        self.assertTrue((run_root / "execution_frontier.json").exists())
        role_memory_files = sorted((run_root / "role_binding_memory").glob("*.json"))
        self.assertEqual(role_memory_files, [])
        self.assertFalse((run_root / "role_binding_ledger.json").exists())
        self.assertTrue((run_root / "user_request.json").exists())
        user_request_record = read_json(run_root / "user_request.json")
        self.assertNotIn(USER_REQUEST["text"], json.dumps(user_request_record))
        self.assertEqual(user_request_record["source"], "startup_intake_ui")
        self.assertTrue((run_root / "startup_intake" / "startup_intake_record.json").exists())
        self.assertTrue((run_root / "mailbox" / "outbox" / "user_intake.json").exists())
        self.assertFalse((run_root / "role_core_prompt_delivery.json").exists())

        controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        startup_rows = {
            row["action_type"]: row
            for row in controller_ledger["actions"]
            if row.get("scope_kind") == "startup"
        }
        self.assertEqual(
            {
                "emit_startup_banner",
                "load_controller_core",
                "open_startup_intake_ui",
            },
            set(startup_rows),
        )
        self.assertEqual(
            {row["router_reconciliation_status"] for row in startup_rows.values()},
            {"reconciled"},
        )
    def test_startup_waits_for_answers_before_banner_or_controller(self) -> None:
        root = self.make_project()

        action = router.run_until_wait(root, new_invocation=True)
        self.assertEqual(action["action_type"], "open_startup_intake_ui")
        self.assertTrue(action["apply_required"])
        self.assertTrue(action["next_step_contract"]["apply_required"])
        self.assertNotIn("controller_completion_command", action)
        self.assertNotIn("router_pending_apply_required", action)
        self.assertTrue(action["requires_host_automation"])
        self.assertEqual(action["requires_payload"], "startup_intake_result")
        self.assertEqual(action["payload_contract"]["schema_version"], "flowpilot.payload_contract.v1")
        self.assertEqual(action["payload_contract"]["payload_key"], "startup_intake_result")
        self.assertIn("flowpilot_startup_intake.ps1", action["startup_intake_ui"]["launcher_path"])
        self.assertTrue(action["startup_intake_ui"]["body_text_is_never_router_payload"])
        self.assertIn("background driver status", action["plain_instruction"])
        self.assertIn("Controller action ledger", action["plain_instruction"])
        self.assertNotIn("apply this pending action", action["plain_instruction"])
        self.assertNotIn("apply its confirmed or cancelled result", action["summary"])

        with self.assertRaises(router.RouterError):
            router.apply_action(root, "emit_startup_banner")
        with self.assertRaises(router.RouterError):
            router.apply_action(root, "load_controller_core")

        bootstrap = self.bootstrap_state(root)
        self.assertEqual(bootstrap["startup_state"], "none")
        self.assertEqual(bootstrap["bootstrap_scope"], "run_scoped")
        self.assertFalse(bootstrap["flags"].get("startup_intake_result_recorded", False))
        self.assertFalse(bootstrap["flags"].get("startup_intake_body_boundary_enforced", False))
        self.assertIsNone(bootstrap["startup_answers"])
        self.assertIsNotNone(bootstrap["run_id"])
        self.assertTrue(bootstrap["flags"]["run_shell_created"])
        self.assertTrue(bootstrap["flags"]["router_daemon_started"])
        self.assertFalse(bootstrap["flags"]["controller_core_loaded"])
        self.assertFalse(bootstrap["flags"].get("roles_started", False))
        self.assertTrue((root / ".flowpilot" / "current.json").exists())
        self.assertTrue((root / bootstrap["run_root"] / "bootstrap" / "startup_state.json").exists())
        self.assertTrue((root / bootstrap["run_root"] / "router_state.json").exists())
    def test_startup_banner_action_and_result_are_user_visible(self) -> None:
        root = self.make_project()
        action = router.run_until_wait(root, new_invocation=True)
        self.assertEqual(action["action_type"], "open_startup_intake_ui")
        router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))

        run_root = self.run_root_for(root)
        controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        self.assertFalse(any(row["action_type"] == "emit_startup_banner" for row in controller_ledger["actions"]))
        action = router.run_until_wait(root)
        self.assertEqual(action["action_type"], "load_controller_core")
        router.apply_action(root, "load_controller_core", self.payload_for_action(action))
        controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        banner_row = next(row for row in controller_ledger["actions"] if row["action_type"] == "emit_startup_banner")
        self.assertEqual(banner_row["status"], "pending")
        entry = read_json(run_root / "runtime" / "controller_actions" / f"{banner_row['action_id']}.json")
        action = entry["action"]
        self.assertEqual(action["action_type"], "emit_startup_banner")
        self.assert_controller_receipt_action_projection(action)
        self.assertTrue(action["display_required"])
        self.assertEqual(action["display_text_format"], "plain_text")
        self.assertFalse(action["controller_must_display_text_before_apply"])
        self.assertTrue(action["controller_must_display_text_before_receipt"])
        self.assertTrue(action["requires_user_dialog_display_confirmation"])
        self.assertEqual(action["required_render_target"], "user_dialog")
        self.assertEqual(action["requires_payload"], "display_confirmation")
        self.assertTrue(action["controller_user_reporting_policy"]["plain_language_required"])
        self.assertTrue(action["controller_user_reporting_policy"]["speak_only_when_user_value"])
        self.assertIn(
            "routine_process_asides",
            action["controller_user_reporting_policy"]["silent_by_default_for"],
        )
        self.assertIn(
            "explicit_user_status_request",
            action["controller_user_reporting_policy"]["report_when"],
        )
        self.assertEqual(
            action["next_step_contract"]["controller_user_reporting_policy"],
            action["controller_user_reporting_policy"],
        )
        self.assertEqual(
            action["payload_template"],
            {
                "display_confirmation": {
                    "action_type": "emit_startup_banner",
                    "display_kind": "startup_banner",
                    "display_text_sha256": action["display_text_sha256"],
                    "provenance": "controller_user_dialog_render",
                    "rendered_to": "user_dialog",
                }
            },
        )
        self.assertIn("display_text exactly", action["payload_template_rule"])
        self.assertIn("Controller receipt", action["payload_template_rule"])
        self.assertNotIn("apply the action", action["payload_template_rule"])
        self.assertFalse(action["generated_files_alone_satisfy_chat_display"])
        self.assertIn("user dialog", action["controller_display_rule"])
        self.assertIn("Controller receipt", action["controller_display_rule"])
        self.assertNotIn("before applying", action["controller_display_rule"])
        self.assertIn("```text", action["display_text"])
        self.assertIn("FlowPilot", action["display_text"])
        self.assertIn("Developer: Yingxu Liu", action["display_text"])
        self.assertIn("Repository: https://github.com/liuyingxuvka/FlowPilot", action["display_text"])
        self.assertIn("Buy the developer a coffee: https://paypal.me/Yingxuliu", action["display_text"])
        self.assertNotIn("████", action["display_text"])
        self.assertNotIn("FLOWPILOT_IDENTITY_BOUNDARY_V1", action["display_text"])
        self.assertNotIn("Formal run mode active.", action["display_text"])
        self.assertNotIn("Route-controlled execution has started.", action["display_text"])
        self.assertNotIn("Packets and ledgers are now in charge.", action["display_text"])
        self.assertNotIn("Startup answers are recorded.", action["display_text"])
        self.assertNotIn("display-only data", action["display_text"])
        self.assertNotIn("flowpilot_router.py", action["display_text"])
        self.assertNotIn(action["controller_user_reporting_policy"]["reminder"], action["display_text"])

        router.record_controller_action_receipt(
            root,
            action_id=banner_row["action_id"],
            status="done",
            payload=self.payload_for_action(action),
        )
        entry = read_json(run_root / "runtime" / "controller_actions" / f"{banner_row['action_id']}.json")
        self.assertEqual(entry["status"], "done")
        self.assertEqual(entry["router_reconciliation_status"], "reconciled")
    def test_user_intake_from_startup_ui_is_router_owned_and_sealed_from_controller(self) -> None:
        root = self.make_project()
        router.run_until_wait(root, new_invocation=True)
        router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))
        result = router.run_until_wait(root)
        self.assertEqual(result["action_type"], "load_controller_core")

        run_root = root / self.bootstrap_state(root)["run_root"]
        user_request_record = read_json(run_root / "user_request.json")
        self.assertNotIn(USER_REQUEST["text"], json.dumps(user_request_record))
        self.assertFalse(user_request_record["controller_may_read_body"])
        self.assertEqual(user_request_record["user_request_ref"]["schema_version"], router.USER_REQUEST_REF_SCHEMA)
        packet_envelope = read_json(run_root / "mailbox" / "outbox" / "user_intake.json")
        self.assertEqual(packet_envelope["body_visibility"], packet_runtime.SEALED_BODY_VISIBILITY)
        self.assertFalse(packet_envelope["body_access"]["controller_can_read_body"])
        packet_ledger = read_json(run_root / "packet_ledger.json")
        record = next(item for item in packet_ledger["packets"] if item["packet_id"] == "user_intake")
        self.assertEqual(packet_ledger["active_packet_holder"], "router")
        self.assertEqual(packet_ledger["active_packet_status"], "router-held-startup-material")
        self.assertEqual(record["active_packet_holder"], "router")
        self.assertEqual(record["active_packet_status"], "router-held-startup-material")
        self.assertTrue(record["router_owned_startup_material"])
        self.assertEqual(record["packet_envelope"]["to_role"], "project_manager")
        body = (run_root / "packets" / "user_intake" / "packet_body.md").read_text(encoding="utf-8")
        self.assertIn(USER_REQUEST["text"], body)
        self.assertIn("startup_intake_record_path", body)
        self.assertIn("pm_startup_repair_request", body)
    def test_new_invocation_creates_fresh_run_scoped_bootstrap_over_stale_state(self) -> None:
        root = self.make_project()
        old_run_root = root / ".flowpilot" / "runs" / "run-old-stopped"
        old_run_root.mkdir(parents=True, exist_ok=True)
        (root / ".flowpilot" / "bootstrap").mkdir(parents=True, exist_ok=True)
        (root / ".flowpilot" / "bootstrap" / "startup_state.json").write_text(
            json.dumps(
                {
                    "schema_version": "flowpilot.bootstrap_state.v1",
                    "status": "running",
                    "startup_state": "answers_complete",
                    "startup_answers": {
                        "runtime_role_assistances": "allow",
                        "scheduled_continuation": "allow",
                        "display_surface": "cockpit",
                    },
                    "flags": {"startup_answers_recorded": True},
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        (root / ".flowpilot" / "current.json").write_text(
            json.dumps(
                {
                    "schema_version": "flowpilot.current.v1",
                    "run_id": "run-old-stopped",
                    "run_root": ".flowpilot/runs/run-old-stopped",
                    "status": "stopped_by_user",
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        action = router.next_action(root, new_invocation=True)
        self.assertEqual(action["action_type"], "load_router")
        current = read_json(root / ".flowpilot" / "current.json")
        self.assertNotEqual(current["run_id"], "run-old-stopped")
        self.assertIn("/bootstrap/startup_state.json", current["startup_bootstrap_path"])
        bootstrap = self.bootstrap_state(root)
        self.assertEqual(bootstrap["bootstrap_scope"], "run_scoped")
        self.assertIsNone(bootstrap["startup_answers"])
        self.assertFalse(bootstrap["flags"].get("startup_answers_recorded", False))
        self.assertEqual(action["allowed_reads"], [current["startup_bootstrap_path"]])
    def test_startup_current_path_releases_user_intake_without_startup_role_gate(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        self.deliver_startup_runtime_prompt_cards(root)
        self.assert_startup_user_intake_held_by_router(root)
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["startup_mechanical_audit_written"])
        self.assertTrue(state["flags"]["startup_display_status_written"])
        self.assertFalse(state["flags"].get("startup_fact_reported", False))
        self.assertFalse(state["flags"].get("startup_activation_approved", False))
        self.assertFalse((run_root / "startup" / "startup_fact_report.json").exists())
        self.assertFalse((run_root / "startup" / "startup_activation.json").exists())

        self.deliver_user_intake_mail(root)
        self.assert_startup_user_intake_released_to_pm(root)
        self.deliver_expected_card(root, "pm.product_architecture")

        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["user_intake_delivered_to_pm"])
        self.assertFalse(state["flags"].get("startup_fact_reported", False))
        self.assertFalse(state["flags"].get("startup_activation_approved", False))

    def test_startup_old_role_gate_events_are_unsupported(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.deliver_startup_runtime_prompt_cards(root)

        old_events = {
            "reviewer_reports_startup_facts": self.role_report_envelope(
                root,
                "startup/legacy_reviewer_startup_fact_report",
                self.legacy_startup_fact_report_body(root),
            ),
            "pm_approves_startup_activation": self.role_decision_envelope(
                root,
                "startup/legacy_pm_startup_activation",
                {"approved_by_role": "project_manager", "decision": "approved"},
            ),
            "pm_requests_startup_repair": self.role_decision_envelope(
                root,
                "startup/legacy_pm_startup_repair_request",
                {"decided_by_role": "project_manager", "decision": "startup_repair_requested"},
            ),
            "pm_declares_startup_protocol_dead_end": self.role_decision_envelope(
                root,
                "startup/legacy_pm_startup_protocol_dead_end",
                {"declared_by_role": "project_manager", "decision": "protocol_dead_end"},
            ),
        }
        for event, payload in old_events.items():
            with self.subTest(event=event):
                with self.assertRaises(router.RouterError):
                    router.record_external_event(root, event, payload)

        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"].get("startup_fact_reported", False))
        self.assertFalse(state["flags"].get("startup_activation_approved", False))
        self.assertFalse((run_root / "startup" / "startup_fact_report.json").exists())
        self.assertFalse((run_root / "startup" / "startup_activation.json").exists())
        self.assertFalse((run_root / "startup" / "startup_repair_request.json").exists())

    def test_daemon_ignores_old_startup_role_flags_from_bootstrap(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-startup-role-fold")
        bootstrap_path = run_root / "bootstrap" / "startup_state.json"
        router.write_json(
            bootstrap_path,
            {
                "schema_version": "flowpilot.startup_state.v1",
                "run_id": run_root.name,
                "run_root": router.project_relative(root, run_root),
                "flags": {
                    "roles_started": True,
                    "role_core_prompts_injected": True,
                },
            },
        )
        state = read_json(router.run_state_path(run_root))

        result = router._fold_stable_startup_role_flags_from_bootstrap(root, run_root, state)  # type: ignore[attr-defined]

        self.assertFalse(result["changed"])
        self.assertTrue(result["ignored_old_startup_role_flags"])
        self.assertFalse(state["flags"].get("roles_started", False))
        self.assertFalse(state["flags"].get("role_core_prompts_injected", False))
    def test_partial_old_startup_role_flags_are_ignored_without_settlement_wait(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-startup-role-partial")
        bootstrap_path = run_root / "bootstrap" / "startup_state.json"
        router.write_json(
            bootstrap_path,
            {
                "schema_version": "flowpilot.startup_state.v1",
                "run_id": run_root.name,
                "run_root": router.project_relative(root, run_root),
                "flags": {
                    "roles_started": True,
                    "role_core_prompts_injected": False,
                },
            },
        )
        state = read_json(router.run_state_path(run_root))

        result = router._fold_stable_startup_role_flags_from_bootstrap(root, run_root, state)  # type: ignore[attr-defined]

        self.assertFalse(result["changed"])
        self.assertTrue(result["ignored_old_startup_role_flags"])
        self.assertFalse(state["flags"].get("roles_started", False))
        self.assertFalse(state["flags"].get("role_core_prompts_injected", False))
    def test_cockpit_startup_answer_is_rejected_as_legacy_option(self) -> None:
        root = self.make_project()
        cockpit_answers = {**STARTUP_ANSWERS, "display_surface": "cockpit"}
        router.run_until_wait(root, new_invocation=True)

        with self.assertRaisesRegex(router.RouterError, "unsupported fields: display_surface"):
            router.apply_action(
                root,
                "open_startup_intake_ui",
                self.startup_intake_payload(root, startup_answers=cockpit_answers),
            )
    def test_old_startup_role_output_contracts_are_absent(self) -> None:
        self.assertNotIn("startup_fact_report", role_output_runtime.SUPPORTED_OUTPUT_TYPES)
        self.assertNotIn("pm_startup_activation_approval", role_output_runtime.SUPPORTED_OUTPUT_TYPES)
        contract_index = read_json(ROOT / "skills" / "flowpilot" / "assets" / "runtime_kit" / "contracts" / "contract_index.json")
        contract_ids = {item.get("contract_id") for item in contract_index.get("contracts", []) if isinstance(item, dict)}
        self.assertNotIn("flowpilot.output_contract.startup_fact_report.v1", contract_ids)
        self.assertNotIn("flowpilot.output_contract.pm_startup_activation_approval.v1", contract_ids)
    def test_manual_startup_records_current_resume_binding_for_resume_reentry(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root, startup_answers=STARTUP_ANSWERS)
        action = self.next_after_display_sync(root)
        self.assertNotEqual(action["action_type"], "create_heartbeat_automation")
        self.assertEqual(action["action_type"], "write_display_surface_status")
        self.complete_startup_runtime_entry(root)

        binding_path = run_root / "continuation" / "continuation_binding.json"
        self.assertTrue(binding_path.exists())
        binding = read_json(binding_path)
        self.assertEqual(binding["run_id"], read_json(run_root / "router_state.json")["run_id"])
        self.assertEqual(binding["mode"], "manual_resume")
        self.assertTrue(binding["manual_resume_required"])
        self.assertTrue(binding["manual_resume_binding_active"])
        self.assertFalse(binding["host_automation_supported"])
        self.assertNotIn("route_heartbeat_interval_minutes", binding)
        self.assertNotIn("heartbeat_active", binding)
        self.assertNotIn("host_automation_id", binding)
        self.assertNotIn("host_automation_verified", binding)

        router.record_external_event(root, "manual_resume_requested", {"source": "manual_resume", "work_chain_status": "broken_or_unknown"})
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "load_resume_state")
        self.assertEqual(
            action["resume_next_recipient_from_packet_ledger"]["controller_next_action"],
            "wait_for_recorded_packet_holder_result",
        )
        self.assertEqual(action["resume_next_recipient_from_packet_ledger"]["next_recipient_role"], "project_manager")
        router.apply_action(root, "load_resume_state")
        resume_evidence = read_json(run_root / "continuation" / "resume_reentry.json")
        self.assertIn("continuation_binding", resume_evidence["loaded_paths"])
        self.assertEqual(resume_evidence["loaded_paths"]["continuation_binding"], self.rel(root, binding_path))
        self.assertEqual(resume_evidence["resume_next_recipient_from_packet_ledger"]["source"], "packet_ledger")
    def test_reconciled_startup_display_receipt_replays_missing_flag(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "write_display_surface_status")
        state = read_json(router.run_state_path(run_root))
        entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        router.record_controller_action_receipt(
            root,
            action_id=entry["action_id"],
            status="done",
            payload=self.payload_for_action(action),
        )
        state = read_json(router.run_state_path(run_root))
        router._reconcile_scheduled_controller_action_receipts(root, run_root, state)  # type: ignore[attr-defined]
        self.assertTrue(read_json(router.run_state_path(run_root))["flags"]["startup_display_status_written"])

        state = read_json(router.run_state_path(run_root))
        state["flags"]["startup_display_status_written"] = False
        state["pending_action"] = None
        router.save_run_state(run_root, state)
        display_entry = next(
            item
            for item in (
                read_json(path)
                for path in sorted((run_root / "runtime" / "controller_actions").glob("*.json"))
            )
            if item.get("action_type") == "write_display_surface_status"
        )
        self.assertEqual(display_entry["status"], "done")
        self.assertEqual(display_entry["router_reconciliation_status"], "reconciled")

        result = router._reconcile_scheduled_controller_action_receipts(root, run_root, state)  # type: ignore[attr-defined]

        self.assertTrue(result["changed"])
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["startup_display_status_written"])
        refreshed_entry = read_json(run_root / "runtime" / "controller_actions" / f"{display_entry['action_id']}.json")
        self.assertEqual(
            refreshed_entry["router_reconciliation"]["postcondition_replay_source"],
            "already_reconciled_controller_action_postcondition_drift_replay",
        )
        self.assertTrue(any(
            item.get("label") == "router_replayed_reconciled_controller_postcondition"
            for item in state.get("history", [])
        ))
    def test_reconciled_startup_display_action_is_not_requeued_after_flag_drift(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "write_display_surface_status")
        state = read_json(router.run_state_path(run_root))
        entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        router.record_controller_action_receipt(
            root,
            action_id=entry["action_id"],
            status="done",
            payload=self.payload_for_action(action),
        )
        state = read_json(router.run_state_path(run_root))
        router._reconcile_scheduled_controller_action_receipts(root, run_root, state)  # type: ignore[attr-defined]

        state = read_json(router.run_state_path(run_root))
        state["flags"]["startup_display_status_written"] = False
        state["pending_action"] = None
        router.save_run_state(run_root, state)

        self.assertIsNone(router._next_startup_display_action(root, state, run_root))  # type: ignore[attr-defined]
        next_action = router.next_action(root)

        self.assertNotEqual(next_action["action_type"], "write_display_surface_status")
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["startup_display_status_written"])
    def test_reconciled_startup_display_missing_receipt_retries_without_requeue(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "write_display_surface_status")
        state = read_json(router.run_state_path(run_root))
        entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        router.record_controller_action_receipt(
            root,
            action_id=entry["action_id"],
            status="done",
            payload=self.payload_for_action(action),
        )
        state = read_json(router.run_state_path(run_root))
        router._reconcile_scheduled_controller_action_receipts(root, run_root, state)  # type: ignore[attr-defined]

        receipt_path = run_root / "runtime" / "controller_receipts" / f"{entry['action_id']}.json"
        receipt_path.unlink()
        state = read_json(router.run_state_path(run_root))
        state["flags"]["startup_display_status_written"] = False
        stale_pending = dict(action)
        stale_pending["controller_action_id"] = entry["action_id"]
        stale_pending["router_scheduler_row_id"] = entry["router_scheduler_row_id"]
        state["pending_action"] = stale_pending
        router.save_run_state(run_root, state)

        result = router._reconcile_scheduled_controller_action_receipts(root, run_root, state)  # type: ignore[attr-defined]

        self.assertTrue(result["changed"])
        refreshed_entry = read_json(run_root / "runtime" / "controller_actions" / f"{entry['action_id']}.json")
        self.assertEqual(refreshed_entry["router_reconciliation_status"], "retry_pending")
        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"]["startup_display_status_written"])
        self.assertIsNone(state["pending_action"])
        self.assertTrue(any(
            item.get("label") == "router_cleared_resolved_controller_pending_projection"
            for item in state.get("history", [])
        ))
        self.assertIsNone(router._next_startup_display_action(root, state, run_root))  # type: ignore[attr-defined]
    def test_startup_reconciliation_wait_does_not_hide_router_local_obligation(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        flags = state.setdefault("flags", {})
        flags["controller_role_confirmed"] = True
        flags["startup_mechanical_audit_written"] = False
        state.pop("startup_mechanical_audit", None)
        blockers = router._startup_pre_review_reconciliation_blockers(root, run_root, state)  # type: ignore[attr-defined]
        wait = router._current_scope_pre_review_reconciliation_action(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            blockers=blockers,
            review_trigger="pm.startup_intake",
        )
        state["pending_action"] = wait
        router.save_run_state(run_root, state)

        action = router.next_action(root)

        self.assertNotEqual(action["action_type"], "await_current_scope_reconciliation")
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["startup_mechanical_audit_written"])
        self.assertTrue(any(
            item.get("label") == "router_local_obligation_preempted_passive_reconciliation_wait"
            for item in state.get("history", [])
        ))
    def test_startup_reconciliation_wait_does_not_block_itself(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        flags = state.setdefault("flags", {})
        for flag in (
            "banner_emitted",
            "controller_role_confirmed",
            "startup_mechanical_audit_written",
            "startup_display_status_written",
            "continuation_binding_recorded",
            *router._startup_pre_review_card_flags(),  # type: ignore[attr-defined]
        ):
            flags[flag] = True
        state.pop("active_control_blocker", None)
        bootstrap = self.bootstrap_state(root)
        bootstrap.setdefault("flags", {})["banner_emitted"] = True
        router.write_json(router.bootstrap_state_path(root), bootstrap)
        return_ledger_path = run_root / "return_event_ledger.json"
        if return_ledger_path.exists():
            return_ledger = read_json(return_ledger_path)
            return_ledger["pending_returns"] = []
            router.write_json(return_ledger_path, return_ledger)
        action_dir = run_root / "runtime" / "controller_actions"
        if action_dir.exists():
            for action_path in sorted(action_dir.glob("*.json")):
                entry = read_json(action_path)
                if entry.get("schema_version") != router.CONTROLLER_ACTION_SCHEMA:
                    continue
                entry["status"] = "done"
                entry["router_reconciliation_status"] = "reconciled"
                entry["router_reconciled_at"] = router.utc_now()
                router.write_json(action_path, entry)
        router.save_run_state(run_root, state)

        wait = router._current_scope_pre_review_reconciliation_action(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            blockers=[{"kind": "test_reconciled_startup_blocker", "scope_kind": "startup"}],
            review_trigger="pm.startup_intake",
        )
        state["pending_action"] = wait
        entry = router._write_controller_action_entry(root, run_root, state, wait)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)
        self.assertFalse(entry["controller_receipt_required"])
        self.assertEqual(entry["controller_projection_kind"], "passive_wait_status")

        state = read_json(router.run_state_path(run_root))
        blockers = router._startup_pre_review_reconciliation_blockers(root, run_root, state)  # type: ignore[attr-defined]
        self.assertEqual(blockers, [])
        self.assertFalse(router._current_scope_reconciliation_wait_still_blocked(root, run_root, state, wait))  # type: ignore[attr-defined]

        action = router.next_action(root)

        self.assertNotEqual(action["action_type"], "await_current_scope_reconciliation")
        state = read_json(router.run_state_path(run_root))
        labels = [item.get("label") for item in state.get("history", []) if isinstance(item, dict)]
        self.assertTrue(
            {
                "router_rechecks_after_current_scope_reconciliation_cleared",
                "router_superseded_resolved_current_scope_wait",
            }
            & set(labels)
        )
    def test_startup_pre_review_uses_closure_kernel_for_resolved_rows(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        flags = state.setdefault("flags", {})
        for flag in (
            "banner_emitted",
            "controller_role_confirmed",
            "startup_mechanical_audit_written",
            "startup_display_status_written",
            "continuation_binding_recorded",
            *router._startup_pre_review_card_flags(),  # type: ignore[attr-defined]
        ):
            flags[flag] = True
        state.pop("active_control_blocker", None)
        bootstrap = self.bootstrap_state(root)
        bootstrap.setdefault("flags", {})["banner_emitted"] = True
        router.write_json(router.bootstrap_state_path(root), bootstrap)
        return_ledger_path = run_root / "return_event_ledger.json"
        if return_ledger_path.exists():
            return_ledger = read_json(return_ledger_path)
            return_ledger["pending_returns"] = []
            router.write_json(return_ledger_path, return_ledger)
        resolved_action_id = None
        action_dir = run_root / "runtime" / "controller_actions"
        if action_dir.exists():
            for action_path in sorted(action_dir.glob("*.json")):
                entry = read_json(action_path)
                if entry.get("schema_version") != router.CONTROLLER_ACTION_SCHEMA:
                    continue
                entry["status"] = "done"
                entry["router_reconciliation_status"] = "reconciled"
                entry["router_reconciled_at"] = router.utc_now()
                if resolved_action_id is None and router._controller_action_is_ordinary_work_row(entry):  # type: ignore[attr-defined]
                    entry["status"] = "resolved"
                    resolved_action_id = entry.get("action_id")
                router.write_json(action_path, entry)
        self.assertIsNotNone(resolved_action_id)
        router.save_run_state(run_root, state)

        blockers = router._startup_pre_review_reconciliation_blockers(root, run_root, state)  # type: ignore[attr-defined]

        self.assertEqual(
            [item for item in blockers if item.get("kind") == "pending_startup_controller_row"],
            [],
        )




