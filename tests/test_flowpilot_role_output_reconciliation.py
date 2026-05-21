from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase

import flowpilot_router_action_providers  # noqa: E402


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
