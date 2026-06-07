from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase


class ResumeRuntimeTests(FlowPilotRouterRuntimeTestBase):
    def test_resume_reentry_loads_state_before_resume_cards(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_runtime_entry(root)

        router.record_external_event(root, "manual_resume_requested")

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "load_resume_state")
        self.assertFalse(action["sealed_body_reads_allowed"])
        self.assertFalse(action["chat_history_progress_inference_allowed"])
        router.apply_action(root, "load_resume_state")

        resume_evidence = read_json(run_root / "continuation" / "resume_reentry.json")
        self.assertTrue(resume_evidence["stable_launcher"])
        self.assertTrue(resume_evidence["controller_only"])
        self.assertFalse(resume_evidence["controller_may_read_packet_body"])
        self.assertFalse(resume_evidence["controller_may_read_result_body"])
        self.assertFalse(resume_evidence["controller_may_infer_route_progress_from_chat_history"])
        self.assertEqual(resume_evidence["missing_paths"], [])
        self.assertTrue(resume_evidence["wake_recorded_to_router"])
        self.assertTrue(resume_evidence["visible_plan_restore_required"])
        self.assertTrue(resume_evidence["visible_plan_restored_from_run"])
        self.assertIn("display_plan_projection", resume_evidence)
        self.assertTrue(resume_evidence["role_rehydration_required"])
        self.assertFalse(resume_evidence["roles_restored_or_replaced"])

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "rehydrate_role_bindings")
        self.assertTrue(action["background_collaboration_authorized"])
        self.assertFalse(action["requires_host_role_binding"])
        self.assertTrue(action["requires_host_role_rehydration"])
        self.assertTrue(action["new_binding_required_only_for_replacements"])
        self.assertTrue(action["reuse_live_agents_when_active"])
        self.assertEqual(action["payload_contract"]["name"], "resume_role_rehydration_receipt")
        self.assert_payload_contract_mentions(
            action["payload_contract"],
            "rehydrated_role_bindings[].role_key",
            "rehydrated_role_bindings[].agent_id",
            "rehydrated_role_bindings[].model_policy",
            "rehydrated_role_bindings[].reasoning_effort_policy",
            "rehydrated_role_bindings[].rehydrated_for_run_id",
            "rehydrated_role_bindings[].rehydrated_after_resume_tick_id",
            "rehydrated_role_bindings[].rehydrated_after_resume_state_loaded",
            "rehydrated_role_bindings[].core_prompt_path",
            "rehydrated_role_bindings[].core_prompt_hash",
            "rehydrated_role_bindings[].host_liveness_status",
            "rehydrated_role_bindings[].liveness_decision",
            "rehydrated_role_bindings[].resume_agent_attempted",
            "rehydrated_role_bindings[].bounded_wait_result",
            "rehydrated_role_bindings[].bounded_wait_ms",
            "rehydrated_role_bindings[].liveness_probe_batch_id",
            "rehydrated_role_bindings[].liveness_probe_mode",
            "rehydrated_role_bindings[].liveness_probe_started_at",
            "rehydrated_role_bindings[].liveness_probe_completed_at",
            "rehydrated_role_bindings[].wait_agent_timeout_treated_as_active",
            "rehydrated_role_bindings[].memory_packet_path",
            "rehydrated_role_bindings[].memory_packet_hash",
            "rehydrated_role_bindings[].memory_missing_acknowledged",
            "rehydrated_role_bindings[].replacement_seeded_from_common_run_context",
            "rehydrated_role_bindings[].pm_resume_context_delivered",
        )
        self.assertEqual(action["background_role_agent_model_policy"]["model_policy"], "strongest_available")
        self.assertEqual(
            action["background_role_agent_model_policy"]["reasoning_effort_policy"],
            "highest_available",
        )
        self.assertFalse(action["background_role_agent_model_policy"]["inherit_foreground_model_allowed"])
        self.assertEqual(
            {item["model_policy"] for item in action["role_rehydration_request"]},
            {"strongest_available"},
        )
        self.assertEqual(
            {item["reasoning_effort_policy"] for item in action["role_rehydration_request"]},
            {"highest_available"},
        )
        self.assertEqual(action["role_binding_open_policy"], "reuse_confirmed_live_agents_spawn_only_missing_cancelled_completed_unknown_or_timeout")
        self.assertTrue(action["liveness_preflight_required"])
        self.assertTrue(action["liveness_preflight_policy"]["concurrent_probe_required"])
        self.assertTrue(action["liveness_preflight_policy"]["start_all_probes_before_waiting"])
        self.assertEqual(action["liveness_preflight_policy"]["probe_mode"], "concurrent_batch")
        self.assertEqual(action["liveness_preflight_policy"]["liveness_probe_batch_id"], action["liveness_probe_batch_id"])
        self.assertFalse(action["liveness_preflight_policy"]["timeout_unknown_is_active"])
        target_roles = action["role_keys"]
        self.assertEqual(action["liveness_preflight_policy"]["roles_to_check"], target_roles)
        self.assertEqual(
            {item["role_key"] for item in action["role_rehydration_request"]},
            set(target_roles),
        )
        self.assertEqual(len(action["role_rehydration_request"]), len(target_roles))
        pm_request = next(item for item in action["role_rehydration_request"] if item["role_key"] == "project_manager")
        self.assertTrue(pm_request["pm_resume_context_required"])
        self.assertIn("pm_prior_path_context", pm_request["pm_resume_context_paths"])
        with self.assertRaisesRegex(router.RouterError, "runtime_role_assistance_capability_status"):
            router.apply_action(root, "rehydrate_role_bindings")
        payload = self.resume_role_agent_payload(root, action)
        payload["role_bindings"] = payload.pop("rehydrated_role_bindings")
        with self.assertRaisesRegex(router.RouterError, "old role_bindings aliases"):
            router.apply_action(root, "rehydrate_role_bindings", payload)
        payload = self.resume_role_agent_payload(root, action)
        state = read_json(router.run_state_path(run_root))
        state["startup_answers"]["background_collaboration_authorized"] = False
        router.save_run_state(run_root, state)
        with self.assertRaisesRegex(router.RouterError, "background_collaboration_authorized=true"):
            router.apply_action(root, "rehydrate_role_bindings", payload)
        state["startup_answers"]["background_collaboration_authorized"] = True
        router.save_run_state(run_root, state)
        payload = self.resume_role_agent_payload(root, action)
        payload["rehydrated_role_bindings"] = payload["rehydrated_role_bindings"][:-1]
        with self.assertRaisesRegex(router.RouterError, "missing rehydrated live role binding records"):
            router.apply_action(root, "rehydrate_role_bindings", payload)
        action = router.next_action(root)
        payload = self.resume_role_agent_payload(root, action)
        payload["rehydrated_role_bindings"][0]["memory_packet_hash"] = "bad"
        with self.assertRaisesRegex(router.RouterError, "memory packet hash mismatch"):
            router.apply_action(root, "rehydrate_role_bindings", payload)
        action = router.next_action(root)
        payload = self.resume_role_agent_payload(root, action)
        payload["rehydrated_role_bindings"][0].update(
            {
                "rehydration_result": "live_agent_continuity_confirmed",
                "host_liveness_status": "timeout_unknown",
                "liveness_decision": "confirmed_existing_agent",
                "bounded_wait_result": "timeout_unknown",
                "wait_agent_timeout_treated_as_active": True,
            }
        )
        with self.assertRaisesRegex(router.RouterError, "timeout_unknown|wait_agent_timeout_treated_as_active"):
            router.apply_action(root, "rehydrate_role_bindings", payload)
        action = router.next_action(root)
        payload = self.resume_role_agent_payload(root, action)
        payload["rehydrated_role_bindings"][0]["liveness_probe_mode"] = "serial"
        with self.assertRaisesRegex(router.RouterError, "concurrent liveness probe mode"):
            router.apply_action(root, "rehydrate_role_bindings", payload)
        action = router.next_action(root)
        payload = self.resume_role_agent_payload(root, action)
        payload["all_liveness_probes_started_before_wait"] = False
        with self.assertRaisesRegex(router.RouterError, "all_liveness_probes_started_before_wait"):
            router.apply_action(root, "rehydrate_role_bindings", payload)
        action = router.next_action(root)
        payload = self.resume_role_agent_payload(root, action)
        payload["rehydrated_role_bindings"][0].update(
            {
                "rehydration_result": "rehydrated_from_current_run_memory",
                "host_liveness_status": "active",
                "liveness_decision": "opened_replacement_from_current_run_memory",
                "replacement_opened_after_resume_state_loaded": True,
            }
        )
        with self.assertRaisesRegex(router.RouterError, "active host liveness must use live_agent_continuity_confirmed"):
            router.apply_action(root, "rehydrate_role_bindings", payload)

        action = router.next_action(root)
        payload = self.resume_role_agent_payload(root, action)
        replaced_role = payload["rehydrated_role_bindings"][0]["role_key"]
        payload["rehydrated_role_bindings"][0].update(
            {
                "agent_id": f"replacement-agent-{replaced_role}",
                "rehydration_result": "rehydrated_from_current_run_memory",
                "host_liveness_status": "missing",
                "liveness_decision": "opened_replacement_from_current_run_memory",
                "bounded_wait_result": "not_waited",
                "bounded_wait_ms": 0,
                "replacement_opened_after_resume_state_loaded": True,
            }
        )
        router.apply_action(root, "rehydrate_role_bindings", payload)
        rehydration = read_json(run_root / "continuation" / "role_binding_recovery_report.json")
        self.assertEqual(rehydration["liveness_preflight"]["replacement_role_keys"], [replaced_role])
        self.assertEqual(rehydration["liveness_preflight"]["decision"], "roles_ready_after_replacement")
        self.assertTrue(rehydration["required_role_bindings_ready"])
        self.assertEqual(rehydration["liveness_preflight"]["roles_checked"], target_roles)
        self.assertFalse(rehydration["liveness_preflight"]["wait_agent_timeout_treated_as_active"])
        self.assertEqual(rehydration["liveness_preflight"]["probe_mode"], "concurrent_batch")
        self.assertTrue(rehydration["liveness_preflight"]["all_liveness_probes_started_before_wait"])
        self.assertTrue(rehydration["current_run_memory_complete"])
        self.assertTrue(rehydration["pm_memory_rehydrated"])
        role_io = read_json(run_root / "role_io_protocol_ledger.json")
        resume_tick_id = rehydration["resume_tick_id"]
        resume_receipts = [
            item
            for item in role_io["injection_receipts"]
            if item["resume_tick_id"] == resume_tick_id
        ]
        self.assertEqual({item["role_key"] for item in resume_receipts}, set(target_roles))
        self.assertEqual(len(resume_receipts), len(target_roles))
        receipt_phase_by_role = {item["role_key"]: item["lifecycle_phase"] for item in resume_receipts}
        self.assertEqual(receipt_phase_by_role[replaced_role], "missing_agent_replacement")
        unchanged_phases = {phase for role, phase in receipt_phase_by_role.items() if role != replaced_role}
        if unchanged_phases:
            self.assertEqual(unchanged_phases, {"manual_resume_rehydration"})

        state = read_json(router.run_state_path(run_root))
        self.assertFalse((run_root / "continuation" / "role_recovery_report.json").exists())
        self.assertTrue(state["flags"]["role_binding_recovery_report_written"])
        self.assertTrue(state["flags"]["resume_role_bindings_rehydrated"])
        self.assertTrue(state["flags"]["resume_roles_restored"])
        self.assertFalse(state["flags"]["role_recovery_report_written"])
        self.assertFalse(state["flags"]["role_recovery_obligation_replay_completed"])
        self.assertFalse(state["flags"]["role_recovery_pm_escalation_required"])
        self.assertFalse(state["flags"]["pm_resume_recovery_decision_returned"])

        controller_card = self.deliver_expected_card(root, "controller.resume_reentry")
        self.assertEqual(controller_card["to_role"], "controller")
        self.assertEqual(controller_card["target_agent_id"], router.CONTROLLER_RUNTIME_HELPER_AGENT_ID)
        action = router.next_action(root)
        while action.get("action_type") in {"open_current_role_agent", "inject_role_io_protocol"}:
            router.apply_action(root, str(action["action_type"]), self.payload_for_action(action))
            action = self.next_after_display_sync(root)
        self.assertEqual(action.get("action_type"), "deliver_system_card")
        self.assertEqual(action.get("card_id"), "pm.role_binding_recovery_freshness")
        self.assertNotEqual(action.get("card_id"), "pm.resume_decision")
        self.assertNotEqual(action.get("label"), "controller_waits_for_pm_resume_decision")
        self.assertFalse((run_root / "continuation" / "pm_resume_decision.json").exists())

    def test_load_resume_state_controller_receipt_replays_router_state_handler(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_runtime_entry(root)

        router.record_external_event(root, "manual_resume_requested")
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "load_resume_state")

        state = read_json(router.run_state_path(run_root))
        entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)

        result = router.record_controller_action_receipt(
            root,
            action_id=entry["action_id"],
            status="done",
            payload={},
        )

        self.assertTrue(result["ok"])
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["resume_state_loaded"])
        resume_evidence = read_json(run_root / "continuation" / "resume_reentry.json")
        self.assertTrue(resume_evidence["wake_recorded_to_router"])
        refreshed = read_json(router._controller_action_path(run_root, entry["action_id"]))  # type: ignore[attr-defined]
        self.assertEqual(refreshed["router_reconciliation_status"], "reconciled")
        self.assertEqual(
            refreshed["router_reconciliation"]["source"],
            "router_owned_state_replay_receipt",
        )
        self.assertEqual(refreshed["router_reconciliation"]["action_type"], "load_resume_state")

    def test_resume_reentry_attaches_to_live_router_daemon_and_ledger(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_runtime_entry(root)
        router._refresh_router_daemon_lock(root, run_root)  # type: ignore[attr-defined]

        try:
            router.record_external_event(root, "manual_resume_requested")
            action = router.next_action(root)
            self.assertEqual(action["action_type"], "load_resume_state")
            recovery = action["router_daemon_resume_recovery"]
            self.assertTrue(recovery["router_daemon_lock_live"])
            self.assertEqual(recovery["decision"], "attach_controller_to_live_daemon")
            self.assertFalse(recovery["work_chain_liveness_claimed"])
            self.assertEqual(recovery["liveness_authority"], "current_daemon_lock_process_and_controller_action_ledger")
            self.assertTrue(recovery["old_route_state_liveness_rejected"])
            self.assertTrue(recovery["wait_agent_timeout_liveness_rejected"])
            self.assertIn(self.rel(root, run_root / "runtime" / "router_daemon_status.json"), action["allowed_reads"])
            self.assertIn(self.rel(root, run_root / "runtime" / "controller_action_ledger.json"), action["allowed_reads"])

            router.apply_action(root, "load_resume_state")
            resume_evidence = read_json(run_root / "continuation" / "resume_reentry.json")
            self.assertTrue(resume_evidence["router_daemon_liveness_checked"])
            self.assertFalse(resume_evidence["router_daemon_restarted_if_dead"])
            self.assertTrue(resume_evidence["controller_action_ledger_loaded"])
            self.assertTrue(resume_evidence["controller_action_ledger_rescanned"])
        finally:
            router.stop_router_daemon(root, reason="test_cleanup")
    def test_resume_reentry_attaches_to_live_owner_after_delayed_daemon_patrol(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_runtime_entry(root)
        lock_path = run_root / "runtime" / "router_daemon.lock"
        lock = read_json(lock_path)
        lock["last_tick_at"] = "2000-01-01T00:00:00Z"
        router.write_json(lock_path, lock)

        router.record_external_event(root, "manual_resume_requested")
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "load_resume_state")
        recovery = action["router_daemon_resume_recovery"]
        self.assertFalse(recovery["router_daemon_lock_live"])
        self.assertTrue(recovery["router_daemon_owner_process_live"])
        self.assertTrue(recovery["router_daemon_active_owner_live"])
        self.assertEqual(recovery["daemon_patrol"]["status"], "check_liveness")
        self.assertEqual(recovery["decision"], "attach_controller_to_live_daemon")
        self.assertFalse(recovery["work_chain_liveness_claimed"])
        self.assertTrue(recovery["old_route_state_liveness_rejected"])
        self.assertTrue(recovery["wait_agent_timeout_liveness_rejected"])

        router.apply_action(root, "load_resume_state")
        resume_evidence = read_json(run_root / "continuation" / "resume_reentry.json")
        self.assertTrue(resume_evidence["router_daemon_liveness_checked"])
        self.assertFalse(resume_evidence["router_daemon_restarted_if_dead"])
        self.assertTrue(resume_evidence["controller_action_ledger_loaded"])
        router.stop_router_daemon(root, reason="test_cleanup")
    def test_resume_reentry_marks_dead_daemon_for_restart_after_liveness_check(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_runtime_entry(root)
        lock_path = run_root / "runtime" / "router_daemon.lock"
        lock = read_json(lock_path)
        lock["last_tick_at"] = "2000-01-01T00:00:00Z"
        lock["owner"] = {"pid": 999999999, "process_name": "missing-test-daemon"}
        router.write_json(lock_path, lock)

        router.record_external_event(root, "manual_resume_requested")
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "load_resume_state")
        recovery = action["router_daemon_resume_recovery"]
        self.assertFalse(recovery["router_daemon_lock_live"])
        self.assertFalse(recovery["router_daemon_owner_process_live"])
        self.assertFalse(recovery["router_daemon_active_owner_live"])
        self.assertEqual(recovery["daemon_patrol"]["status"], "check_liveness")
        self.assertEqual(recovery["decision"], "restart_router_daemon_from_current_state")
        self.assertFalse(recovery["work_chain_liveness_claimed"])
        self.assertTrue(recovery["wait_agent_timeout_liveness_rejected"])

        router.apply_action(root, "load_resume_state")
        resume_evidence = read_json(run_root / "continuation" / "resume_reentry.json")
        self.assertTrue(resume_evidence["router_daemon_liveness_checked"])
        self.assertTrue(resume_evidence["router_daemon_restarted_if_dead"])
        self.assertTrue(resume_evidence["controller_action_ledger_loaded"])
    def test_resume_reentry_preempts_active_control_blocker_until_replay_or_pm_decision(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_runtime_entry(root)
        state = read_json(router.run_state_path(run_root))
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="Controller has no legal next action while resume is sleeping",
            action_type="controller_no_legal_next_action",
            payload={"path": self.rel(root, router.run_state_path(run_root)), "role": "controller"},
        )

        router.record_external_event(root, "manual_resume_requested")

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "load_resume_state")
        router.apply_action(root, "load_resume_state")
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "rehydrate_role_bindings")
        router.apply_action(root, "rehydrate_role_bindings", self.resume_role_agent_payload(root, action))

        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["role_recovery_obligation_replay_completed"])
        self.assertFalse(state["flags"]["role_recovery_pm_escalation_required"])
        self.assertTrue(state["flags"]["pm_resume_recovery_decision_returned"])
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "handle_control_blocker")
        self.assertEqual(action["blocker_id"], blocker["blocker_id"])
        self.assertFalse((run_root / "continuation" / "pm_resume_decision.json").exists())
    def test_mid_run_role_liveness_fault_uses_unified_recovery_before_normal_work(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_runtime_entry(root)
        state = read_json(router.run_state_path(run_root))
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="Controller has a deferred blocker while worker is missing",
            action_type="controller_no_legal_next_action",
            payload={"path": self.rel(root, router.run_state_path(run_root)), "role": "controller"},
        )

        result = router.record_external_event(
            root,
            "controller_reports_role_liveness_fault",
            {
                "role_key": "worker",
                "host_liveness_status": "missing",
                "detected_by": "controller",
            },
        )

        self.assertTrue(result["role_recovery_requested"])
        transaction = result["role_recovery_transaction"]
        self.assertEqual(transaction["trigger_source"], "mid_run_liveness_fault")
        self.assertEqual(transaction["target_role_keys"], ["worker"])

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "load_role_recovery_state")
        self.assertEqual(action["recovery_priority"], "preempt_normal_work")
        router.apply_action(root, "load_role_recovery_state")

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "recover_role_bindings")
        self.assertEqual(action["target_role_keys"], ["worker"])
        self.assertTrue(action["background_collaboration_authorized"])
        self.assertIn("restore_old_agent", action["recovery_ladder"])
        self.assertIn("full_role_binding_recovery", action["recovery_ladder"])
        self.assertFalse(action["normal_waits_allowed_before_recovery"])
        payload = self.role_recovery_agent_payload(root, action, role="worker")
        legacy_payload = self.role_recovery_agent_payload(root, action, role="worker")
        legacy_payload["role_bindings"] = legacy_payload.pop("recovered_role_bindings")
        with self.assertRaisesRegex(router.RouterError, "old role_bindings aliases"):
            router.apply_action(root, "recover_role_bindings", legacy_payload)
        state = read_json(router.run_state_path(run_root))
        state["startup_answers"]["background_collaboration_authorized"] = False
        router.save_run_state(run_root, state)
        with self.assertRaisesRegex(router.RouterError, "background_collaboration_authorized=true"):
            router.apply_action(root, "recover_role_bindings", payload)
        state["startup_answers"]["background_collaboration_authorized"] = True
        router.save_run_state(run_root, state)
        router.apply_action(root, "recover_role_bindings", payload)

        report = read_json(run_root / "continuation" / "role_recovery_report.json")
        self.assertEqual(report["schema_version"], "flowpilot.role_recovery_report.v1")
        self.assertTrue(report["required_role_bindings_ready"])
        self.assertFalse(report["pm_decision_required_before_normal_work"])
        self.assertTrue(report["mechanical_obligation_replay_completed"])
        replay = read_json(root / report["role_recovery_obligation_replay_path"])
        self.assertEqual(replay["schema_version"], "flowpilot.role_recovery_obligation_replay.v1")
        self.assertFalse(replay["pm_escalation_required"])
        self.assertEqual(report["role_records"][0]["recovery_result"], "targeted_replacement_opened")
        role_binding = read_json(run_root / "role_binding_ledger.json")
        worker_slot = next(slot for slot in role_binding["role_slots"] if slot["role_key"] == "worker")
        self.assertEqual(worker_slot["last_role_recovery_result"], "targeted_replacement_opened")
        self.assertTrue(worker_slot["superseded_agent_output_quarantined"])

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "handle_control_blocker")
        self.assertEqual(action["blocker_id"], blocker["blocker_id"])
    def test_blocked_role_recovery_receipt_reclaims_existing_report(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_runtime_entry(root)

        report = self.recover_worker_after_liveness_fault(root)
        self.assertTrue(report["required_role_bindings_ready"])

        state = read_json(router.run_state_path(run_root))
        action = router.make_action(
            action_type="recover_role_bindings",
            actor="controller",
            label="host_recovers_role_bindings_before_normal_work_stale_projection",
            summary="Stale daemon row for a recovery action whose report already exists.",
            allowed_reads=[],
            allowed_writes=[],
            extra={"postcondition": "role_recovery_roles_restored"},
        )
        entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)
        action_path = run_root / "runtime" / "controller_actions" / f"{entry['action_id']}.json"
        entry["status"] = "done"
        entry["router_reconciliation_status"] = "blocked"
        entry["router_reconciliation_blocker"] = {"reason": "stale_role_recovery_projection"}
        entry.pop("router_reconciled_at", None)
        entry.pop("router_reconciliation", None)
        router.write_json(action_path, entry)

        state = read_json(router.run_state_path(run_root))
        state["flags"]["role_recovery_roles_restored"] = False
        state["flags"]["resume_roles_restored"] = False
        router.save_run_state(run_root, state)
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            read_json(router.run_state_path(run_root)),
            source=router.CONTROLLER_POSTCONDITION_MISSING_BLOCKER_SOURCE,
            error_message=(
                "Controller action recover_role_bindings was marked done, but Router could not "
                "apply its required postcondition before reconciliation."
            ),
            action_type="recover_role_bindings",
            payload={
                "controller_action_id": entry["action_id"],
                "router_scheduler_row_id": entry.get("router_scheduler_row_id"),
                "postcondition": "role_recovery_roles_restored",
                "direct_retry_attempts_used": 2,
                "direct_retry_budget": 2,
            },
        )

        state = read_json(router.run_state_path(run_root))
        result = router._reconcile_scheduled_controller_action_receipts(root, run_root, state)  # type: ignore[attr-defined]

        self.assertTrue(result["changed"])
        self.assertEqual(result["blocked"], 0)
        refreshed = read_json(action_path)
        self.assertEqual(refreshed["router_reconciliation_status"], "reconciled")
        self.assertTrue(refreshed["router_reconciliation_recovered_from_blocked_state"])
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["role_recovery_roles_restored"])
        self.assertTrue(state["flags"]["resume_roles_restored"])
        self.assertTrue(state["flags"]["role_recovery_obligation_replay_completed"])
        blocker_record = read_json(self.control_blocker_path(root, blocker))
        self.assertEqual(blocker_record["resolution_status"], "resolved_by_controller_action_reconciliation")

    def test_stale_role_recovery_report_is_not_reclaimed_for_new_transaction(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_runtime_entry(root)

        first_report = self.recover_worker_after_liveness_fault(root)
        self.assertTrue(first_report["required_role_bindings_ready"])
        first_transaction_id = first_report["transaction_id"]

        result = router.record_external_event(
            root,
            "controller_reports_role_liveness_fault",
            {
                "role_key": "project_manager",
                "host_liveness_status": "missing",
                "detected_by": "controller",
            },
        )
        self.assertTrue(result["role_recovery_requested"])
        self.assertNotEqual(result["role_recovery_transaction"]["transaction_id"], first_transaction_id)

        state = read_json(router.run_state_path(run_root))
        reclaim = router._reclaim_role_recovery_postcondition_from_report(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test_new_transaction_must_not_reclaim_old_report",
        )

        self.assertFalse(reclaim["applied"])
        self.assertEqual(reclaim["reason"], "role_recovery_report_not_ready")

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "load_role_recovery_state")
        self.assertEqual(action["role_recovery_transaction"]["target_role_keys"], ["project_manager"])

    def test_active_agent_lookup_rejects_unknown_recovered_liveness(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_runtime_entry(root)

        role_binding = read_json(run_root / "role_binding_ledger.json")
        pm_slot = next(slot for slot in role_binding["role_slots"] if slot["role_key"] == "project_manager")
        pm_slot.update(
            {
                "status": "live_agent_recovered",
                "agent_id": "recovered-pm-unknown",
                "host_liveness_status": "unknown",
                "liveness_decision": "opened_replacement_from_current_run_memory",
            }
        )
        router.write_json(run_root / "role_binding_ledger.json", role_binding)

        self.assertIsNone(router._active_agent_id_for_role(run_root, "project_manager"))  # type: ignore[attr-defined]
    def test_load_resume_state_does_not_downgrade_existing_role_recovery_report(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_runtime_entry(root)

        report = self.recover_worker_after_liveness_fault(root)
        self.assertFalse(report["pm_decision_required_before_normal_work"])

        state = read_json(router.run_state_path(run_root))
        state["flags"]["resume_reentry_requested"] = True
        state["flags"]["resume_state_loaded"] = False
        state["flags"]["resume_roles_restored"] = False
        state["flags"]["resume_role_bindings_rehydrated"] = False
        state["flags"]["role_binding_recovery_report_written"] = False
        state["flags"]["pm_resume_recovery_decision_returned"] = False
        state["flags"]["role_recovery_roles_restored"] = False
        state["flags"]["role_recovery_obligation_replay_completed"] = False
        state["pending_action"] = None
        router.save_run_state(run_root, state)

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "load_resume_state")
        router.apply_action(root, "load_resume_state")

        resume = read_json(run_root / "continuation" / "resume_reentry.json")
        self.assertTrue(resume["roles_restored_or_replaced"])
        self.assertFalse(resume["role_rehydration_required"])
        self.assertTrue(resume["role_recovery_report_reclaimed"])
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["resume_roles_restored"])
        self.assertTrue(state["flags"]["role_recovery_roles_restored"])
        self.assertTrue(state["flags"]["role_recovery_obligation_replay_completed"])
        self.assertTrue(state["flags"]["pm_resume_recovery_decision_returned"])
    def test_incomplete_stateful_rehydrate_receipt_becomes_control_blocker(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        state["flags"]["controller_role_confirmed"] = True
        state["flags"]["controller_boundary_confirmation_written"] = True
        state["flags"]["resume_reentry_requested"] = True
        state["flags"]["resume_state_loaded"] = True
        state["flags"]["resume_roles_restored"] = False
        action = router.make_action(
            action_type="rehydrate_role_bindings",
            actor="controller",
            label="host_rehydrates_resume_roles_before_pm_decision",
            summary="Test rehydrate action with incomplete receipt.",
            extra={"postcondition": "resume_roles_restored"},
        )
        state["pending_action"] = action
        entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)
        router.record_controller_action_receipt(
            root,
            action_id=entry["action_id"],
            status="done",
            payload={"roles_rehydrated": 6},
        )

        next_action = self.next_after_display_sync(root)

        self.assertEqual(next_action["action_type"], "handle_control_blocker")
        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"]["resume_roles_restored"])
        self.assertEqual(state["active_control_blocker"]["originating_action_type"], "rehydrate_role_bindings")
        self.assertNotEqual((state.get("pending_action") or {}).get("action_type"), "rehydrate_role_bindings")

    def test_done_rehydrate_receipt_reclaims_existing_current_run_report_before_blocker(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_runtime_entry(root)
        router.record_external_event(root, "manual_resume_requested")
        self.assertEqual(self.next_after_display_sync(root)["action_type"], "load_resume_state")
        router.apply_action(root, "load_resume_state")
        original_action = self.next_after_display_sync(root)
        self.assertEqual(original_action["action_type"], "rehydrate_role_bindings")
        router.apply_action(root, "rehydrate_role_bindings", self.resume_role_agent_payload(root, original_action))
        report = read_json(run_root / "continuation" / "role_binding_recovery_report.json")
        self.assertTrue(report["required_role_bindings_ready"])
        self.assertTrue(report["current_run_memory_complete"])

        state = read_json(router.run_state_path(run_root))
        state["flags"]["resume_roles_restored"] = False
        state["flags"]["resume_role_bindings_rehydrated"] = False
        state["flags"]["role_binding_recovery_report_written"] = False
        stale_action = router.make_action(
            action_type="rehydrate_role_bindings",
            actor="controller",
            label="host_rehydrates_resume_roles_before_pm_decision_stale_projection",
            summary="Stale projection whose current-run role binding report already exists.",
            extra={"postcondition": "resume_roles_restored"},
        )
        state["pending_action"] = stale_action
        entry = router._write_controller_action_entry(root, run_root, state, stale_action)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)
        router.record_controller_action_receipt(
            root,
            action_id=entry["action_id"],
            status="done",
            payload={"roles_rehydrated": 6},
        )

        next_action = self.next_after_display_sync(root)

        self.assertNotEqual(next_action["action_type"], "handle_control_blocker")
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["resume_roles_restored"])
        self.assertTrue(state["flags"]["resume_role_bindings_rehydrated"])
        self.assertTrue(state["flags"]["role_binding_recovery_report_written"])
        self.assertIsNone(state.get("active_control_blocker"))
        refreshed = read_json(run_root / "runtime" / "controller_actions" / f"{entry['action_id']}.json")
        self.assertEqual(refreshed["router_reconciliation_status"], "reconciled")
        self.assertEqual(
            refreshed["router_reconciliation"]["source"],
            "controller_receipt_resume_rehydration_report_reclaim",
        )

    def test_role_no_output_report_reissues_same_work_before_role_recovery(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        wait_action = self.force_current_role_result_wait(root)

        result = router.record_external_event(
            root,
            "controller_reports_role_no_output",
            {
                "role_key": "human_like_reviewer",
                "liveness_probe_result": "completed_without_expected_event",
                "current_controller_action_id": wait_action["controller_action_id"],
                "router_scheduler_row_id": wait_action["router_scheduler_row_id"],
            },
        )

        self.assertTrue(result["ok"])
        self.assertTrue(result["role_no_output_reissue_created"])
        self.assertFalse(result["role_recovery_requested"])
        self.assertEqual(result["role_no_output_reissue_attempt"], 1)
        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"]["role_recovery_requested"])
        self.assertTrue(state["flags"]["role_no_output_reissue_recorded"])
        pending = state["pending_action"]
        self.assertEqual(pending["action_type"], "await_role_decision")
        self.assertIn("_no_output_reissue_001", pending["label"])
        self.assertEqual(pending["replacement_reason"], "role_no_output_missing_expected_event")
        self.assertEqual(pending["role_no_output_reissue_attempt"], 1)
        original = read_json(run_root / "runtime" / "controller_actions" / f"{wait_action['controller_action_id']}.json")
        self.assertEqual(original["status"], "superseded")
        self.assertEqual(original["superseded_by_controller_action_id"], result["replacement_controller_action_id"])
        replacement = read_json(run_root / "runtime" / "controller_actions" / f"{result['replacement_controller_action_id']}.json")
        self.assertEqual(replacement["status"], "waiting")
        self.assertEqual(replacement["replacement_reason"], "role_no_output_missing_expected_event")
        self.assertEqual(replacement["replaces_controller_action_id"], wait_action["controller_action_id"])
    def test_completed_liveness_fault_no_output_redirects_to_reissue_not_recovery(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        wait_action = self.force_current_role_result_wait(root)

        result = router.record_external_event(
            root,
            "controller_reports_role_liveness_fault",
            {
                "role_key": "human_like_reviewer",
                "host_liveness_status": "completed",
                "current_controller_action_id": wait_action["controller_action_id"],
            },
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["event"], "controller_reports_role_no_output")
        self.assertEqual(result["source_event"], "controller_reports_role_liveness_fault")
        self.assertTrue(result["role_no_output_reissue_created"])
        self.assertFalse(result["role_recovery_requested"])
        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"]["role_recovery_requested"])
        self.assertTrue(state["flags"]["role_no_output_reissue_recorded"])
        self.assertIn("_no_output_reissue_001", state["pending_action"]["label"])
    def test_role_no_output_escalates_to_pm_after_two_reissues(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        wait_action = self.force_current_role_result_wait(root)

        first = router.record_external_event(
            root,
            "controller_reports_role_no_output",
            {
                "role_key": "human_like_reviewer",
                "liveness_probe_result": "completed_without_expected_event",
                "current_controller_action_id": wait_action["controller_action_id"],
            },
        )
        second = router.record_external_event(
            root,
            "controller_reports_role_no_output",
            {
                "role_key": "human_like_reviewer",
                "liveness_probe_result": "completed_without_expected_event",
                "current_controller_action_id": first["replacement_controller_action_id"],
            },
        )
        third = router.record_external_event(
            root,
            "controller_reports_role_no_output",
            {
                "role_key": "human_like_reviewer",
                "liveness_probe_result": "completed_without_expected_event",
                "current_controller_action_id": second["replacement_controller_action_id"],
            },
        )

        self.assertTrue(first["role_no_output_reissue_created"])
        self.assertEqual(second["role_no_output_reissue_attempt"], 2)
        self.assertFalse(third["role_no_output_reissue_created"])
        self.assertTrue(third["pm_escalation_required"])
        self.assertIn("control_blocker_id", third)
        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"]["role_recovery_requested"])
        self.assertTrue(state["flags"]["role_no_output_pm_escalation_required"])
        self.assertEqual(state["active_control_blocker"]["originating_event"], "controller_reports_role_no_output")
    def test_resume_rehydration_settles_existing_output_without_pm(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_runtime_entry(root)
        original = self.write_worker_recovery_wait_action(root, label="resume_waits_for_worker_existing_output")
        state = read_json(router.run_state_path(run_root))
        state.setdefault("events", []).append(
            {
                "event": "worker_scan_results_returned",
                "summary": "Worker output already reached Router before manual resume replay.",
                "payload": {"result_envelope_path": self.rel(root, run_root / "test_role_outputs" / "resume-existing.json")},
                "recorded_at": router.utc_now(),
            }
        )
        router.save_run_state(run_root, state)

        router.record_external_event(root, "manual_resume_requested")
        self.assertEqual(self.next_after_display_sync(root)["action_type"], "load_resume_state")
        router.apply_action(root, "load_resume_state")
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "rehydrate_role_bindings")
        router.apply_action(root, "rehydrate_role_bindings", self.resume_role_agent_payload(root, action))

        report = read_json(run_root / "continuation" / "role_recovery_report.json")
        replay = read_json(root / report["role_recovery_obligation_replay_path"])
        self.assertEqual(replay["settled_existing_count"], 1)
        self.assertEqual(replay["replacement_count"], 0)
        self.assertEqual(replay["outcomes"][0]["outcome"], "settled_existing_output")
        original_after = read_json(run_root / "runtime" / "controller_actions" / f"{original['action_id']}.json")
        self.assertEqual(original_after["status"], "done")
        self.assertFalse(report["pm_decision_required_before_normal_work"])
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["pm_resume_recovery_decision_returned"])
        self.assertFalse((run_root / "continuation" / "pm_resume_decision.json").exists())
    def test_resume_rehydration_reissues_missing_obligations_before_pm(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_runtime_entry(root)
        original = self.write_worker_recovery_wait_action(root, label="resume_waits_for_worker_missing_output")

        router.record_external_event(root, "manual_resume_requested")
        self.assertEqual(self.next_after_display_sync(root)["action_type"], "load_resume_state")
        router.apply_action(root, "load_resume_state")
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "rehydrate_role_bindings")
        router.apply_action(root, "rehydrate_role_bindings", self.resume_role_agent_payload(root, action))

        report = read_json(run_root / "continuation" / "role_recovery_report.json")
        replay = read_json(root / report["role_recovery_obligation_replay_path"])
        self.assertEqual(replay["replacement_count"], 1)
        self.assertEqual(replay["settled_existing_count"], 0)
        self.assertFalse(report["pm_decision_required_before_normal_work"])
        original_after = read_json(run_root / "runtime" / "controller_actions" / f"{original['action_id']}.json")
        self.assertEqual(original_after["status"], "superseded")
        replacement_id = replay["replacement_order"][0]["replacement_controller_action_id"]
        replacement = read_json(run_root / "runtime" / "controller_actions" / f"{replacement_id}.json")
        self.assertEqual(replacement["status"], "waiting")
        self.assertEqual(replacement["replaces_controller_action_id"], original["action_id"])
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["pm_resume_recovery_decision_returned"])
        self.assertEqual(state["pending_action"]["controller_action_id"], replacement_id)
        self.assertFalse((run_root / "continuation" / "pm_resume_decision.json").exists())
    def test_role_recovery_settles_existing_output_without_replay_or_pm(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_runtime_entry(root)
        original = self.write_worker_recovery_wait_action(root, label="controller_waits_for_worker_existing_output")
        state = read_json(router.run_state_path(run_root))
        state.setdefault("events", []).append(
            {
                "event": "worker_scan_results_returned",
                "summary": "Worker output already reached Router before recovery replay.",
                "payload": {"result_envelope_path": self.rel(root, run_root / "test_role_outputs" / "existing.json")},
                "recorded_at": router.utc_now(),
            }
        )
        router.save_run_state(run_root, state)

        report = self.recover_worker_after_liveness_fault(root)
        replay = read_json(root / report["role_recovery_obligation_replay_path"])
        self.assertEqual(replay["settled_existing_count"], 1)
        self.assertEqual(replay["replacement_count"], 0)
        self.assertEqual(replay["outcomes"][0]["outcome"], "settled_existing_output")
        original_after = read_json(run_root / "runtime" / "controller_actions" / f"{original['action_id']}.json")
        self.assertEqual(original_after["status"], "done")
        self.assertEqual(original_after["completion_source"], "role_recovery_obligation_replay")
        self.assertFalse(report["pm_decision_required_before_normal_work"])
    def test_role_recovery_settles_existing_ack_without_replay_or_pm(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_runtime_entry(root)
        ack_path = run_root / "runtime" / "card_returns" / "worker-existing.ack.json"
        envelope_path = run_root / "runtime" / "card_envelopes" / "worker-existing.envelope.json"
        ack_path.parent.mkdir(parents=True, exist_ok=True)
        envelope_path.parent.mkdir(parents=True, exist_ok=True)
        ack_path.write_text(json.dumps({"status": "acknowledged"}, indent=2) + "\n", encoding="utf-8")
        envelope_path.write_text(json.dumps({"status": "delivered"}, indent=2) + "\n", encoding="utf-8")
        ack_rel = self.rel(root, ack_path)
        envelope_rel = self.rel(root, envelope_path)
        state = read_json(router.run_state_path(run_root))
        action = router.make_action(
            action_type="await_card_return_event",
            actor="controller",
            label="controller_waits_for_worker_existing_ack",
            summary="Controller waits for worker card ACK before recovery.",
            allowed_reads=[envelope_rel],
            allowed_writes=[],
            to_role="worker",
            extra={
                "delivery_attempt_id": "worker-existing-delivery",
                "card_id": "worker.research_report",
                "card_return_event": "worker_existing_card_ack",
                "expected_return_path": ack_rel,
                "card_envelope_path": envelope_rel,
                "artifact_committed": True,
                "relay_allowed": True,
            },
        )
        original = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        return_ledger_path = run_root / "return_event_ledger.json"
        return_ledger = read_json(return_ledger_path)
        return_ledger.setdefault("pending_returns", []).append(
            {
                "return_kind": "system_card",
                "status": "pending",
                "card_id": "worker.research_report",
                "delivery_attempt_id": "worker-existing-delivery",
                "card_return_event": "worker_existing_card_ack",
                "target_role": "worker",
                "expected_return_path": ack_rel,
                "card_envelope_path": envelope_rel,
            }
        )
        return_ledger_path.write_text(json.dumps(return_ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        router.save_run_state(run_root, state)

        with mock.patch.object(
            router.card_runtime,
            "validate_card_ack",
            return_value={"ack_path": ack_rel, "ack_hash": "valid-existing-ack", "receipt_ref_count": 1},
        ):
            report = self.recover_worker_after_liveness_fault(root)

        replay = read_json(root / report["role_recovery_obligation_replay_path"])
        self.assertEqual(replay["settled_existing_count"], 1)
        self.assertEqual(replay["replacement_count"], 0)
        self.assertEqual(replay["outcomes"][0]["outcome"], "settled_existing_ack")
        original_after = read_json(run_root / "runtime" / "controller_actions" / f"{original['action_id']}.json")
        self.assertEqual(original_after["status"], "done")
        self.assertEqual(original_after["completion_source"], "role_recovery_obligation_replay")
        self.assertFalse(report["pm_decision_required_before_normal_work"])
    def test_role_recovery_reissues_missing_obligations_in_original_order(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_runtime_entry(root)
        first = self.write_worker_recovery_wait_action(root, label="controller_waits_for_worker_output_first")
        second = self.write_worker_recovery_wait_action(root, label="controller_waits_for_worker_output_second")

        report = self.recover_worker_after_liveness_fault(root)
        replay = read_json(root / report["role_recovery_obligation_replay_path"])
        self.assertEqual(replay["replacement_count"], 2)
        self.assertEqual([item["original_order"] for item in replay["replacement_order"]], [1, 2])

        first_after = read_json(run_root / "runtime" / "controller_actions" / f"{first['action_id']}.json")
        second_after = read_json(run_root / "runtime" / "controller_actions" / f"{second['action_id']}.json")
        self.assertEqual(first_after["status"], "superseded")
        self.assertEqual(second_after["status"], "superseded")
        replacement_ids = [item["replacement_controller_action_id"] for item in replay["replacement_order"]]
        replacements = [read_json(run_root / "runtime" / "controller_actions" / f"{action_id}.json") for action_id in replacement_ids]
        self.assertEqual([entry["original_order"] for entry in replacements], [1, 2])
        self.assertEqual([entry["replaces_controller_action_id"] for entry in replacements], [first["action_id"], second["action_id"]])
        self.assertTrue(all(entry["status"] == "waiting" for entry in replacements))
        self.assertTrue(all(entry["replacement_reason"] == "role_recovered_missing_or_invalid_output" for entry in replacements))
        state = read_json(router.run_state_path(run_root))
        self.assertEqual(state["pending_action"]["controller_action_id"], replacements[0]["action_id"])
        self.assertFalse(report["pm_decision_required_before_normal_work"])
    def test_resume_ambiguous_state_blocks_continue_without_recovery_evidence(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.ensure_current_role_agent_for_role(root, "worker")
        (run_root / "role_binding_memory" / "worker.json").unlink()

        router.record_external_event(root, "manual_resume_requested")
        self.assertEqual(self.next_after_display_sync(root)["action_type"], "load_resume_state")
        router.apply_action(root, "load_resume_state")
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "rehydrate_role_bindings")
        self.assertEqual(action["memory_missing_role_keys"], ["worker"])
        router.apply_action(root, "rehydrate_role_bindings", self.resume_role_agent_payload(root, action))
        self.deliver_expected_card(root, "controller.resume_reentry")
        self.deliver_expected_card(root, "pm.role_binding_recovery_freshness")
        self.deliver_expected_card(root, "pm.resume_decision")

        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "pm_resume_recovery_decision_returned",
                self.role_decision_envelope(
                    root,
                    "continuation/pm_resume_decision_continue_ambiguous",
                    {
                        "decision_owner": "project_manager",
                        "decision": "continue_current_packet_loop",
                        **self.prior_path_context_review(root, "PM resume decision considered ambiguous current route memory."),
                        "controller_reminder": {
                        "controller_only": True,
                        "controller_may_read_sealed_bodies": False,
                        "controller_may_infer_from_chat_history": False,
                        "controller_may_advance_or_close_route": False,
                        },
                    },
                ),
            )
        router.record_external_event(
            root,
            "pm_resume_recovery_decision_returned",
            self.role_decision_envelope(
                root,
                "continuation/pm_resume_decision_restore",
                {
                    "decision_owner": "project_manager",
                    "decision": "restore_or_replace_roles_from_memory",
                    **self.prior_path_context_review(root, "PM chose role restoration from current route memory and resume evidence."),
                    "controller_reminder": {
                        "controller_only": True,
                        "controller_may_read_sealed_bodies": False,
                        "controller_may_infer_from_chat_history": False,
                        "controller_may_advance_or_close_route": False,
                    },
                },
            ),
        )
        decision = read_json(run_root / "continuation" / "pm_resume_decision.json")
        self.assertTrue(decision["resume_ambiguous"])
        self.assertEqual(decision["decision"], "restore_or_replace_roles_from_memory")
    def test_manual_resume_alive_status_enters_router_resume_path(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)

        result = router.record_external_event(
            root,
            "manual_resume_requested",
            {"source": "manual_resume", "work_chain_status": "alive"},
        )

        self.assertTrue(result["resume_requested"])
        self.assertTrue(result["manual_resume_tick"]["router_reentry_required"])
        self.assertFalse(result["manual_resume_tick"]["self_keepalive_allowed"])
        self.assertEqual(result["manual_resume_tick"]["work_chain_status_trust"], "diagnostic_only")
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "load_resume_state")

    def test_legacy_heartbeat_resume_event_is_rejected(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)

        with self.assertRaisesRegex(router.RouterError, "unknown external event: heartbeat_or_manual_resume_requested"):
            router.record_external_event(
                root,
                "heartbeat_or_manual_resume_requested",
                {"source": "heartbeat", "work_chain_status": "alive"},
            )


