from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase

import flowpilot_router_action_providers  # noqa: E402
import flowpilot_router_role_output_bridge_events as role_output_bridge_events  # noqa: E402


class RoleOutputReconciliationTests(FlowPilotRouterRuntimeTestBase):
    def _seed_material_sources(self, root: Path, run_root: Path) -> list[str]:
        package_path = run_root / "material" / "pm_material_scan_formal_gate_package.json"
        artifact_map_path = run_root / "material" / "material_artifact_map.json"
        router.write_json(package_path, {"schema_version": "test.material_package.v1", "ok": True})
        router.write_json(artifact_map_path, {"schema_version": "test.material_artifact_map.v1", "ok": True})
        return [self.rel(root, package_path), self.rel(root, artifact_map_path)]

    def _seed_resolved_material_review_wait(self, root: Path, run_root: Path) -> tuple[dict, dict]:
        state = read_json(router.run_state_path(run_root))
        state.setdefault("flags", {})["reviewer_material_sufficiency_card_delivered"] = True
        wait_action = router.make_action(
            action_type="await_role_decision",
            actor="controller",
            label="controller_waits_for_material_sufficiency",
            summary="Wait for material sufficiency review.",
            to_role="human_like_reviewer",
            extra={
                "allowed_external_events": ["reviewer_reports_material_insufficient"],
                "payload_contract": {
                    "required_object": "role_output_body",
                    "expected_return_envelope": "role_output_envelope",
                    "expected_output_type": "material_sufficiency_report",
                    "expected_output_contract_id": "flowpilot.output_contract.material_sufficiency_report.v1",
                },
                "started_at": "2026-05-20T00:00:00Z",
            },
        )
        entry = router._write_controller_action_entry(root, run_root, state, wait_action)  # type: ignore[attr-defined]
        wait_action["controller_action_id"] = entry["action_id"]
        wait_action["router_scheduler_row_id"] = entry["router_scheduler_row_id"]
        state["pending_action"] = wait_action
        router.save_run_state(run_root, state)

        action_path = run_root / "runtime" / "controller_actions" / f"{entry['action_id']}.json"
        action_record = read_json(action_path)
        action_record["status"] = "done"
        action_record["completed_at"] = router.utc_now()
        action_record["completion_source"] = "test_resolved_wait_before_router_event"
        action_record["router_reconciliation_status"] = "reconciled"
        action_record["router_reconciled_at"] = router.utc_now()
        action_record["router_reconciliation"] = {
            "source": "test_resolved_wait_before_router_event",
            "event": "reviewer_reports_material_insufficient",
        }
        router.write_json(action_path, action_record)
        router._update_router_scheduler_row(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            row_id=entry["router_scheduler_row_id"],
            router_state="reconciled",
            reconciliation={"source": "test_resolved_wait_before_router_event"},
        )
        router._rebuild_controller_action_ledger(root, run_root, state)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)
        return wait_action, entry

    def _submit_material_insufficient_role_output(self, root: Path, run_root: Path) -> dict:
        return role_output_runtime.submit_output(
            root,
            output_type="material_sufficiency_report",
            role="human_like_reviewer",
            agent_id="agent-human_like_reviewer",
            run_id=run_root.name,
            event_name="reviewer_reports_material_insufficient",
            output_path=run_root / "test_role_outputs" / "material" / "reviewer_material_insufficient.json",
            body={
                "reviewed_by_role": "human_like_reviewer",
                "direct_material_sources_checked": True,
                "packet_matches_checked_sources": True,
                "pm_ready": False,
                "checked_source_paths": self._seed_material_sources(root, run_root),
                "runtime_open_receipt_refs": [],
                "findings": [{"finding_id": "missing-context", "summary": "Material is insufficient for execution."}],
                "blockers": [{"blocker_id": "missing-context", "summary": "More source material is required."}],
                "residual_risks": [],
                "pm_suggestion_items": [],
                "independent_challenge": {
                    "scope_restatement": "Review whether the material package is sufficient for execution.",
                    "explicit_and_implicit_commitments": [],
                    "failure_hypotheses": [],
                    "challenge_actions": [],
                    "blocking_findings": [],
                    "non_blocking_findings": [],
                    "pass_or_block": "block",
                    "reroute_request": [],
                    "challenge_waivers": [],
                },
            },
        )

    def _seed_package_disposition_conflict_replay(
        self,
        root: Path,
        run_root: Path,
        *,
        event: str = "pm_records_material_scan_result_disposition",
        owner: str,
    ) -> dict:
        event_slug = event.replace("pm_records_", "").replace("_result_disposition", "")
        self.pm_package_result_disposition_envelope(
            root,
            event,
            name=f"{event_slug}/{owner}/pm_package_result_disposition_first",
            decision="absorbed",
            decision_reason="PM absorbed the current package result batch.",
        )
        self.pm_package_result_disposition_envelope(
            root,
            event,
            name=f"{event_slug}/{owner}/pm_package_result_disposition_conflict",
            decision="rework_requested",
            decision_reason="A stale conflicting PM disposition was still replayable.",
        )
        ledger_records = role_output_bridge_events._role_output_ledger_outputs(router, run_root)
        first_record = next(
            record
            for record in ledger_records
            if "pm_package_result_disposition_first" in str(record)
        )

        state = read_json(router.run_state_path(run_root))
        payload = role_output_bridge_events._role_output_body_payload_from_record(
            router,
            root,
            first_record,
            first_record["envelope"],
        )
        identity = router._scoped_event_identity(root, run_root, state, event, payload)  # type: ignore[attr-defined]
        router._mark_scoped_event_recorded(state, identity)  # type: ignore[attr-defined]
        flags = state.setdefault("flags", {})
        required_flag = router.EXTERNAL_EVENTS[event].get("requires_flag")
        if required_flag:
            flags[required_flag] = True
        flags[router.EXTERNAL_EVENTS[event]["flag"]] = True
        if owner == "control_blocker":
            allowed_events = [router.PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT]
        elif owner == "pm_repair":
            flags["pm_control_blocker_repair_decision_recorded"] = True
            allowed_events = [
                "router_direct_material_scan_dispatch_recheck_passed",
                "router_direct_material_scan_dispatch_recheck_blocked",
                "router_protocol_blocker_material_scan_dispatch_recheck",
            ]
        else:
            raise AssertionError(f"unknown owner: {owner}")
        state.setdefault("events", []).append(
            {
                "event": event,
                "recorded_at": router.utc_now(),
                "source": "test_existing_package_disposition",
                "dedupe_key": identity["dedupe_key"],
            }
        )
        state["pending_action"] = router.make_action(
            action_type="await_role_decision",
            actor="controller",
            label=f"controller_waits_for_{event_slug}_{owner}_resolution",
            summary="Wait for the existing control-plane owner to resolve package disposition conflict.",
            to_role="project_manager",
            extra={
                "allowed_external_events": allowed_events,
                "started_at": "2026-05-20T00:00:00Z",
            },
        )
        if owner == "control_blocker":
            state["active_control_blocker"] = {
                "blocker_id": "control-blocker-1",
                "originating_event": event,
                "handling_lane": "pm_repair_decision_required",
                "target_role": "project_manager",
                "pm_decision_required": True,
                "delivery_status": "delivered",
            }
        elif owner == "pm_repair":
            state["active_repair_transaction"] = {
                "transaction_id": "repair-tx-1",
                "blocker_id": "control-blocker-1",
                "status": "committed",
                "originating_event": event,
            }
        router.save_run_state(run_root, state)
        return state

    def test_material_role_output_event_reconciles_router_state_and_clears_stale_pending(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-material-role-output-reconcile")
        self.write_current_focus(root, run_root)
        wait_action, _entry = self._seed_resolved_material_review_wait(root, run_root)
        self._submit_material_insufficient_role_output(root, run_root)
        before = read_json(router.run_state_path(run_root))
        self.assertFalse(before["flags"].get("material_review_insufficient"))
        self.assertEqual((before.get("pending_action") or {}).get("controller_action_id"), wait_action["controller_action_id"])

        result = router._reconcile_durable_wait_evidence(root, run_root, before)  # type: ignore[attr-defined]
        router.save_run_state(run_root, before)

        self.assertTrue(result["direct_role_output_reconciliation"]["changed"])
        after = read_json(router.run_state_path(run_root))
        self.assertTrue(after["flags"]["material_review_insufficient"])
        self.assertEqual(after["material_review"], "insufficient")
        self.assertIsNone(after.get("pending_action"))
        if (run_root / "material" / "material_sufficiency_report.json").exists():
            report = read_json(run_root / "material" / "material_sufficiency_report.json")
            self.assertFalse(report["sufficient"])
        events = [
            item
            for item in after["events"]
            if isinstance(item, dict) and item.get("event") == "reviewer_reports_material_insufficient"
        ]
        self.assertEqual(len(events), 1)

        replay = router._reconcile_durable_wait_evidence(root, run_root, after)  # type: ignore[attr-defined]
        self.assertFalse(replay["direct_role_output_reconciliation"]["changed"])
        replay_events = [
            item
            for item in after["events"]
            if isinstance(item, dict) and item.get("event") == "reviewer_reports_material_insufficient"
        ]
        self.assertEqual(len(replay_events), 1)

    def test_repair_owned_package_disposition_conflict_replay_is_quarantined_without_daemon_error(self) -> None:
        events = (
            "pm_records_material_scan_result_disposition",
            "pm_records_research_result_disposition",
            "pm_records_current_node_result_disposition",
        )
        for event in events:
            event_slug = event.replace("pm_records_", "").replace("_result_disposition", "")
            for owner in ("control_blocker", "pm_repair"):
                with self.subTest(event=event, owner=owner):
                    root = self.make_project()
                    run_root = self.write_minimal_run(root, f"run-package-conflict-replay-{event_slug}-{owner}")
                    self.write_current_focus(root, run_root)
                    state = self._seed_package_disposition_conflict_replay(root, run_root, event=event, owner=owner)

                    result = router._reconcile_durable_wait_evidence(root, run_root, state)  # type: ignore[attr-defined]
                    router.save_run_state(run_root, state)

                    direct_reconcile = result["direct_role_output_reconciliation"]
                    self.assertTrue(direct_reconcile["changed"])
                    self.assertEqual(direct_reconcile["repair_owned_conflicts"], 1)
                    self.assertEqual(direct_reconcile["reconciled"], 0)
                    after = read_json(router.run_state_path(run_root))
                    package_events = [
                        item
                        for item in after["events"]
                        if isinstance(item, dict) and item.get("event") == event
                    ]
                    self.assertEqual(len(package_events), 1)
                    self.assertEqual(
                        (after.get("pending_action") or {}).get("label"),
                        f"controller_waits_for_{event_slug}_{owner}_resolution",
                    )
                    quarantine_rows = after.get("role_output_replay_quarantine", [])
                    self.assertEqual(len(quarantine_rows), 1)
                    self.assertEqual(quarantine_rows[0]["event"], event)
                    self.assertEqual(quarantine_rows[0]["status"], "quarantined_audit_only")
                    quarantine_path = run_root / "runtime" / "role_output_replay_quarantine.jsonl"
                    self.assertTrue(quarantine_path.exists())
                    self.assertTrue(
                        any(
                            item.get("label") == "router_skipped_repair_owned_package_disposition_conflict_replay"
                            for item in after.get("history", [])
                            if isinstance(item, dict)
                        )
                    )

                    replay = router._reconcile_durable_wait_evidence(root, run_root, after)  # type: ignore[attr-defined]
                    self.assertFalse(replay["direct_role_output_reconciliation"]["changed"])
                    self.assertEqual(replay["direct_role_output_reconciliation"]["repair_owned_conflicts"], 1)

    def test_repair_owned_package_disposition_conflict_replay_is_seen_before_required_flag(self) -> None:
        for owner in ("control_blocker", "pm_repair"):
            with self.subTest(owner=owner):
                root = self.make_project()
                run_root = self.write_minimal_run(root, f"run-package-conflict-replay-missing-required-flag-{owner}")
                self.write_current_focus(root, run_root)
                state = self._seed_package_disposition_conflict_replay(root, run_root, owner=owner)
                required_flag = router.EXTERNAL_EVENTS["pm_records_material_scan_result_disposition"]["requires_flag"]
                state["flags"].pop(required_flag, None)
                router.save_run_state(run_root, state)

                result = router._reconcile_durable_wait_evidence(root, run_root, state)  # type: ignore[attr-defined]
                router.save_run_state(run_root, state)

                direct_reconcile = result["direct_role_output_reconciliation"]
                self.assertTrue(direct_reconcile["changed"])
                self.assertEqual(direct_reconcile["repair_owned_conflicts"], 1)
                self.assertEqual(direct_reconcile["reconciled"], 0)
                after = read_json(router.run_state_path(run_root))
                package_events = [
                    item
                    for item in after["events"]
                    if isinstance(item, dict) and item.get("event") == "pm_records_material_scan_result_disposition"
                ]
                self.assertEqual(len(package_events), 1)
                self.assertEqual(
                    (after.get("pending_action") or {}).get("label"),
                    f"controller_waits_for_material_scan_{owner}_resolution",
                )
                self.assertTrue(
                    any(
                        item.get("label") == "router_skipped_repair_owned_package_disposition_conflict_replay"
                        for item in after.get("history", [])
                        if isinstance(item, dict)
                    )
                )

    def test_daemon_tick_quarantines_repair_owned_package_conflict_without_erasing_wait(self) -> None:
        for owner in ("control_blocker", "pm_repair"):
            with self.subTest(owner=owner):
                root = self.make_project()
                run_root = self.write_minimal_run(root, f"run-package-conflict-daemon-replay-{owner}")
                self.write_current_focus(root, run_root)
                self.release_startup_daemon_for_explicit_daemon_test(root)
                state = read_json(router.run_state_path(run_root))
                sync_action = router._next_display_plan_action(root, state, run_root)  # type: ignore[attr-defined]
                if sync_action is not None:
                    router._apply_sync_display_plan_state(root, run_root, state, sync_action, {})  # type: ignore[attr-defined]
                    router.save_run_state(run_root, state)
                self._seed_package_disposition_conflict_replay(root, run_root, owner=owner)

                result = router.run_router_daemon(root, max_ticks=1, release_lock_on_exit=True)

                self.assertTrue(result["ok"])
                status = read_json(run_root / "runtime" / "router_daemon_status.json")
                self.assertNotEqual(status["lifecycle_status"], "daemon_error")
                after = read_json(router.run_state_path(run_root))
                self.assertEqual(
                    (after.get("pending_action") or {}).get("label"),
                    f"controller_waits_for_material_scan_{owner}_resolution",
                )
                self.assertEqual(len(after.get("role_output_replay_quarantine", [])), 1)
                package_events = [
                    item
                    for item in after["events"]
                    if isinstance(item, dict) and item.get("event") == "pm_records_material_scan_result_disposition"
                ]
                self.assertEqual(len(package_events), 1)

    def test_resolved_wait_cannot_drive_current_work_or_wait_reminder(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-resolved-wait-current-work")
        self.write_current_focus(root, run_root)
        wait_action, entry = self._seed_resolved_material_review_wait(root, run_root)
        state = read_json(router.run_state_path(run_root))
        self.assertEqual((state.get("pending_action") or {}).get("controller_action_id"), entry["action_id"])

        daemon_status = router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
        )
        self.assertNotEqual(daemon_status["current_work"]["source"], "pending_action")

        provider_result = flowpilot_router_action_providers.pending_action_provider(
            router,
            root,
            state,
            run_root,
            router_internal_depth=0,
            compute_again=lambda _root, _state, _run_root, _depth: {},
        )
        self.assertIsNone(provider_result)
        self.assertIsNone(state.get("pending_action"))
        ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        reminder_rows = [
            item
            for item in ledger.get("actions", [])
            if isinstance(item, dict) and item.get("action_type") == router.WAIT_TARGET_REMINDER_ACTION_TYPE
        ]
        self.assertEqual(reminder_rows, [])
        self.assertEqual(wait_action["controller_action_id"], entry["action_id"])
