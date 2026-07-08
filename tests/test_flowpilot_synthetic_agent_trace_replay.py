from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "simulations"))

import flowpilot_defects  # noqa: E402
import packet_runtime  # noqa: E402
import role_output_runtime  # noqa: E402
import flowpilot_router as router  # noqa: E402
import flowpilot_rejection_liveness_matrix_model as rejection_liveness_model  # noqa: E402
import flowpilot_route_authority_singularity_model as route_authority_model  # noqa: E402
from scripts.test_tier import background as test_tier_background  # noqa: E402
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase  # noqa: E402
from tests.flowpilot_route_mutation_contracts import (  # noqa: E402
    ROUTE_MUTATION_CHILD_CONTRACT_SCHEMA,
    RouteMutationContractHarness,
)
from tests.synthetic_agent_trace_replay import (  # noqa: E402
    SyntheticTracePackage,
    read_json,
    run_worker_result_trace,
    start_worker_trace,
)


class FlowPilotSyntheticAgentTraceReplayTests(unittest.TestCase):
    def test_route_authority_fake_ai_matrix_covers_alias_fallback_no_delta_and_feedback(self) -> None:
        expected_failures = {
            route_authority_model.WRONG_ROLE_ROUTE_ACTION: "submitted role does not match current route authority owner",
            route_authority_model.OLD_ALIAS_TRANSLATED: "unsupported old route-action alias was translated",
            route_authority_model.FALLBACK_PROSE_TRANSLATED: "fallback or prose route-action payload was translated",
            route_authority_model.REJECTION_FEEDBACK_MISSING: "route authority rejection feedback missing repair fields",
            route_authority_model.REPEATED_NO_DELTA_ACCEPTED: "repeated no-delta wrong-path submission was accepted",
        }
        hazard_states = route_authority_model.hazard_states()

        for scenario, expected_failure in expected_failures.items():
            with self.subTest(scenario=scenario):
                failures = route_authority_model.route_authority_failures(hazard_states[scenario])
                self.assertIn(expected_failure, failures)

    def test_rejection_liveness_fake_ai_matrix_covers_no_delta_and_corrected_retry(self) -> None:
        retry_cells = [
            cell
            for cell in rejection_liveness_model.REQUIRED_REJECTION_LIVENESS_CELLS
            if cell["defect_class"] in rejection_liveness_model.RETRY_DEFECT_CLASSES
        ]
        families = {cell["family"] for cell in retry_cells}
        defects_by_family = {
            family: {cell["defect_class"] for cell in retry_cells if cell["family"] == family}
            for family in families
        }

        self.assertEqual(families, set(rejection_liveness_model.CONTRACT_FAMILIES))
        for family, defects in defects_by_family.items():
            with self.subTest(family=family):
                self.assertEqual(defects, set(rejection_liveness_model.RETRY_DEFECT_CLASSES))

    def test_happy_path_worker_trace_reaches_pm_disposition(self) -> None:
        package = SyntheticTracePackage(
            name="packet_happy_worker_result",
            evidence_kind="synthetic",
            next_recipient="project_manager",
            expected_outcome="pm_disposition_required",
        )

        replay = run_worker_result_trace(package)

        self.assertEqual(package.evidence_kind, "synthetic")
        self.assertEqual(
            replay.submission["controller_next_action_notice"]["next_action"],  # type: ignore[index]
            "deliver_result_to_pm_for_disposition",
        )
        self.assertFalse(
            replay.submission["controller_next_action_notice"]["controller_may_read_result_body"]  # type: ignore[index]
        )

        record = replay.packet_record()
        self.assertTrue(record["active_holder_ack_recorded"])
        self.assertEqual(record["packet_body_opened_by_role"], "worker")
        self.assertEqual(record["packet_open_work_authority"]["source"], "current_assignment")
        self.assertTrue(record["fast_lane_result_mechanics_passed"])
        self.assertEqual(record["result_envelope"]["next_recipient"], "project_manager")

        replay.relay_result()
        body = replay.open_result_body(role="project_manager")
        self.assertIn("Synthetic worker result", body)

        disposition = replay.pm_disposition()
        self.assertEqual(disposition["output_type"], "pm_package_result_disposition")
        self.assertEqual(disposition["from_role"], "project_manager")
        self.assertEqual(disposition["controller_visibility"], "role_output_envelope_only")
        self.assertFalse(disposition["chat_response_body_allowed"])

    def test_fake_ai_pm_package_trace_catches_same_package_conflicting_decisions(self) -> None:
        replay = run_worker_result_trace(
            SyntheticTracePackage(
                name="fake_ai_conflicting_pm_package_decisions",
                evidence_kind="synthetic",
                next_recipient="project_manager",
            )
        )
        first = replay.pm_disposition(decision="absorbed")
        second = role_output_runtime.submit_output(
            replay.root,
            output_type="pm_package_result_disposition",
            role="project_manager",
            agent_id="agent-project_manager",
            run_id="run-test",
            event_name="pm_records_current_node_result_disposition",
            output_path=replay.run_root
            / "synthetic_trace_outputs"
            / f"{replay.package.name}.pm_disposition.rework.json",
            body={
                "decided_by_role": "project_manager",
                "decision": "rework_requested",
                "decision_reason": "Synthetic fake-AI conflict for the same package generation.",
                "residual_risks": [],
            },
        )
        run_state = read_json(replay.run_root / "state.json")
        first_identity = router._scoped_event_identity(  # type: ignore[attr-defined]
            replay.root,
            replay.run_root,
            run_state,
            "pm_records_current_node_result_disposition",
            first,
        )
        second_identity = router._scoped_event_identity(  # type: ignore[attr-defined]
            replay.root,
            replay.run_root,
            run_state,
            "pm_records_current_node_result_disposition",
            second,
        )
        self.assertEqual(first_identity["dedupe_key"], second_identity["dedupe_key"])  # type: ignore[index]
        self.assertNotEqual(
            first_identity["scope"]["body_hash"],  # type: ignore[index]
            second_identity["scope"]["body_hash"],  # type: ignore[index]
        )

        router._mark_scoped_event_recorded(run_state, first_identity)  # type: ignore[attr-defined]
        with self.assertRaisesRegex(router.RouterError, "conflicts with an already recorded package disposition"):  # type: ignore[attr-defined]
            router._check_scoped_event_conflict(run_state, second_identity)  # type: ignore[attr-defined]

    def test_ack_only_trace_keeps_semantic_work_open(self) -> None:
        replay = start_worker_trace(
            SyntheticTracePackage(
                name="ack_only_not_completion",
                expected_outcome="semantic_work_still_waiting",
            )
        )

        replay.ack()

        ledger = replay.ledger()
        record = replay.packet_record()
        self.assertEqual(ledger["active_packet_holder"], "worker")
        self.assertEqual(ledger["active_packet_status"], "active-holder-acknowledged")
        self.assertTrue(record["active_holder_ack_recorded"])
        self.assertIsNone(record["result_body_hash"])
        self.assertFalse(record["result_body_hash_verified"])
        self.assertFalse((replay.packet_dir / "controller_next_action_notice.json").exists())

    def test_trace_rejects_sealed_body_wrong_identity_and_stale_hash(self) -> None:
        replay = start_worker_trace(SyntheticTracePackage(name="sealed_body_and_identity_guards"))

        with self.assertRaisesRegex(
            packet_runtime.PacketRuntimeError,
            "packet body may only be read by to_role='worker', not 'controller'",
        ):
            packet_runtime.read_packet_body_for_role(
                replay.root,
                replay.packet_envelope,
                role="controller",
            )

        with self.assertRaisesRegex(packet_runtime.PacketRuntimeError, "wrong_role"):
            packet_runtime.active_holder_ack(
                replay.root,
                lease_path=replay.lease["lease_path"],  # type: ignore[index]
                role="human_like_reviewer",
                agent_id="agent-reviewer-1",
                route_version=1,
                frontier_version=1,
            )

        with self.assertRaisesRegex(packet_runtime.PacketRuntimeError, "wrong_agent"):
            packet_runtime.active_holder_ack(
                replay.root,
                lease_path=replay.lease["lease_path"],  # type: ignore[index]
                role="worker",
                agent_id="agent-worker-1-2",
                route_version=1,
                frontier_version=1,
            )

        replay.ack()
        replay.open_packet_body()
        replay.submit_result()
        replay.relay_result()
        replay.tamper_result_body()

        with self.assertRaisesRegex(packet_runtime.PacketRuntimeError, "result body hash mismatch"):
            replay.open_result_body(role="project_manager")

    def test_raw_worker_result_cannot_skip_pm_disposition_to_reviewer_pass(self) -> None:
        replay = run_worker_result_trace(
            SyntheticTracePackage(
                name="raw_worker_result_to_reviewer_blocked",
                next_recipient="project_manager",
                expected_outcome="reviewer_blocks_missing_pm_disposition",
            )
        )

        replay.relay_result(to_role="human_like_reviewer")
        replay.open_result_body(role="human_like_reviewer")

        audit = packet_runtime.validate_for_reviewer(
            replay.root,
            packet_envelope=read_json(replay.packet_envelope_path),
            result_envelope=read_json(replay.result_envelope_path),
            agent_role_map={"agent-worker-1-1": "worker"},
        )
        self.assertTrue(audit["passed"])
        self.assertEqual(audit["blockers"], [])

    def test_fixture_evidence_is_disclosed_but_not_live_completion_evidence(self) -> None:
        replay = start_worker_trace(
            SyntheticTracePackage(
                name="fixture_evidence_cannot_close_live_completion",
                evidence_kind="fixture",
                expected_outcome="fixture_only_disclosed",
            )
        )

        self.assertEqual(replay.package.evidence_kind, "fixture")
        self.assertEqual(flowpilot_defects.main(["--root", str(replay.root), "init"]), 0)
        self.assertEqual(
            flowpilot_defects.main(
                [
                    "--root",
                    str(replay.root),
                    "add-evidence",
                    "--evidence-id",
                    "synthetic-trace-fixture-evidence",
                    "--kind",
                    "trace_replay",
                    "--path",
                    "synthetic-traces/fixture-result.json",
                    "--status",
                    "valid",
                    "--source-kind",
                    "fixture",
                    "--role",
                    "worker",
                    "--reason",
                    "Fixture proves control-flow behavior but not live project completion.",
                ]
            ),
            0,
        )
        self.assertEqual(
            flowpilot_defects.main(
                [
                    "--root",
                    str(replay.root),
                    "pause-snapshot",
                    "--reason",
                    "synthetic_trace_replay",
                    "--next-allowed-action",
                    "continue_current_run",
                    "--automation-checked",
                    "--safe-to-delete",
                    "synthetic trace temp output",
                    "--preserve",
                    "live project evidence",
                    "--must-not-reuse",
                    "fixture evidence as live completion proof",
                    "--summary",
                    "Synthetic trace fixture evidence recorded as non-live evidence.",
                ]
            ),
            0,
        )
        snapshot = json.loads((replay.run_root / "pause_snapshot.json").read_text(encoding="utf-8"))
        self.assertEqual(
            snapshot["evidence_summary"]["fixture_only_evidence_to_disclose"],
            ["synthetic-trace-fixture-evidence"],
        )

    def test_background_progress_only_trace_is_not_pass_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-synthetic-bg-") as tmp_name:
            root = Path(tmp_name)
            paths = test_tier_background.artifact_paths(root, "synthetic_progress_only")
            paths["combined"].parent.mkdir(parents=True, exist_ok=True)
            paths["combined"].write_text("still exploring states\n", encoding="utf-8")

            evidence = test_tier_background.classify_background_artifact(
                root,
                "synthetic_progress_only",
            )

        self.assertEqual(evidence["status"], "progress_only")
        self.assertFalse(evidence["ok"])
        self.assertIn("missing_exit", evidence["reasons"])

    def test_core_deliverable_downgrade_chain_blocks_completion(self) -> None:
        trace_steps = [
            {
                "stage": "pm_route_downgrade",
                "bad_output": "reachable-only route slice replaces the accepted deliverable",
                "required_runtime_path": "route_blocker_or_mutation",
            },
            {
                "stage": "worker_honest_missing_substitute",
                "bad_output": "honest missing deliverable result claims completion without required material",
                "required_runtime_path": "missing_required_information",
            },
            {
                "stage": "reviewer_shallow_pass",
                "bad_output": "reviewer passes deliverable status language without source-intent challenge",
                "required_runtime_path": "reviewer_blocker_repair",
            },
            {
                "stage": "final_ledger_status_only_closure",
                "bad_output": "status-only final ledger row closes an actual deliverable",
                "required_runtime_path": "terminal_repair_or_user_stop",
            },
            {
                "stage": "child_skill_lower_standard_output",
                "bad_output": "weaker child-skill deliverable output closes the parent target",
                "required_runtime_path": "child_skill_gate_blocker",
            },
        ]

        for step in trace_steps:
            with self.subTest(stage=step["stage"]):
                self.assertNotEqual(step["required_runtime_path"], "completion")
                self.assertIn(
                    step["required_runtime_path"],
                    {
                        "route_blocker_or_mutation",
                        "missing_required_information",
                        "reviewer_blocker_repair",
                        "terminal_repair_or_user_stop",
                        "child_skill_gate_blocker",
                    },
                )
                self.assertIn("deliverable", step["bad_output"])
                self.assertFalse(
                    step["bad_output"].endswith("completion accepted"),
                    "core deliverable downgrade traces are blockers, not live completion evidence",
                )


class FlowPilotSyntheticExceptionTraceReplayTests(FlowPilotRouterRuntimeTestBase):
    def test_control_blocker_reissue_retry_budget_escalates_to_pm_fake_reviewer_package(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        blockers: list[dict] = []
        for attempt in range(3):
            state = read_json(router.run_state_path(run_root))
            blocker = router._write_control_blocker(  # type: ignore[attr-defined]
                root,
                run_root,
                state,
                source="synthetic_trace",
                error_message="current-node reviewer pass must explicitly pass",
                event="current_node_reviewer_passes_result",
                payload={
                    "report_path": f".flowpilot/runs/test/reviews/synthetic-missing-passed-budget-{attempt}.json",
                    "synthetic_trace_package": "control_blocker_reissue_then_pm_escalation",
                },
            )
            self.assertIsInstance(blocker, dict)
            blockers.append(blocker)
            if attempt < 2:
                self.assertEqual(blocker["handling_lane"], "control_plane_reissue")
                self.assertEqual(blocker["target_role"], "human_like_reviewer")
                self.assertEqual(blocker["direct_retry_attempts_used"], attempt)
                self.assertFalse(blocker["direct_retry_budget_exhausted"])
            else:
                self.assertEqual(blocker["handling_lane"], "pm_repair_decision_required")
                self.assertEqual(blocker["target_role"], "project_manager")
                self.assertEqual(blocker["policy_row_id"], "mechanical_control_plane_reissue")
                self.assertEqual(blocker["direct_retry_attempts_used"], 2)
                self.assertTrue(blocker["direct_retry_budget_exhausted"])
                self.assertEqual(blocker["allowed_resolution_events"], ["pm_records_control_blocker_repair_decision"])

        state = read_json(router.run_state_path(router.active_run_root(root)))  # type: ignore[arg-type]
        attempts = state["blocker_repair_attempts"][blockers[-1]["attempt_key"]]
        self.assertTrue(attempts["direct_retry_budget_exhausted"])
        self.assertEqual(attempts["latest_target_role"], "project_manager")

    def test_pm_repair_decision_accepts_registered_target_fake_pm_package(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)
        state["flags"]["pm_route_skeleton_card_delivered"] = True
        router.save_run_state(run_root, state)
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="synthetic_trace",
            error_message="fake PM package repairs route draft handoff",
            event="reviewer_reports_material_sufficient",
            payload={"report_path": ".flowpilot/runs/test/reviews/synthetic-route-draft.json"},
        )
        self.assertTrue(self.handle_pending_control_blocker(root))

        router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(
                root,
                "synthetic/control_blocks/valid_route_draft_pm_repair_decision",
                self.pm_control_blocker_decision_body(blocker["blocker_id"], rerun_target="pm_writes_route_draft"),
            ),
        )

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertEqual(
            set(action["allowed_external_events"]),
            {
                "pm_writes_route_draft",
                "pm_records_control_blocker_followup_blocker",
                "pm_records_control_blocker_protocol_blocker",
            },
        )

    def test_pm_repair_decision_rejects_invalid_targets_fake_pm_package(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        state["flags"]["pm_route_skeleton_card_delivered"] = True
        router.save_run_state(run_root, state)
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="synthetic_trace",
            error_message="fake PM package tries invalid repair target",
            event="reviewer_reports_material_sufficient",
            payload={"report_path": ".flowpilot/runs/test/reviews/synthetic-invalid-target.json"},
        )
        self.assertTrue(self.handle_pending_control_blocker(root))

        with self.assertRaisesRegex(router.RouterError, "rerun_target must name a registered external event"):
            router.record_external_event(
                root,
                "pm_records_control_blocker_repair_decision",
                self.role_decision_envelope(
                    root,
                    "synthetic/control_blocks/unregistered_pm_repair_decision",
                    self.pm_control_blocker_decision_body(
                        blocker["blocker_id"],
                        rerun_target="router_selects_next_legal_action_after_pm_records_control_blocker_repair_decision",
                    ),
                ),
            )
        original = read_json(self.control_blocker_path(root, blocker))
        self.assertNotIn("pm_repair_rerun_target", original)

        stale_root = self.make_project()
        stale_run_root = self.boot_to_controller(stale_root)
        stale_state = read_json(router.run_state_path(stale_run_root))
        stale_blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            stale_root,
            stale_run_root,
            stale_state,
            source="synthetic_trace",
            error_message="fake PM package points to a registered target that is not receivable yet",
            event="reviewer_reports_material_sufficient",
            payload={"report_path": ".flowpilot/runs/test/reviews/synthetic-not-receivable.json"},
        )
        self.assertTrue(self.handle_pending_control_blocker(stale_root))
        with self.assertRaisesRegex(router.RouterError, "pm_writes_route_draft: event requires unsatisfied flag"):
            router.record_external_event(
                stale_root,
                "pm_records_control_blocker_repair_decision",
                self.role_decision_envelope(
                    stale_root,
                    "synthetic/control_blocks/not_receivable_pm_repair_decision",
                    self.pm_control_blocker_decision_body(stale_blocker["blocker_id"], rerun_target="pm_writes_route_draft"),
                ),
            )

    def test_fatal_control_blocker_rejects_pm_ordinary_waiver_fake_package(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        state["flags"]["continuation_binding_recorded"] = True
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="synthetic_trace",
            error_message="envelope payload leaked role body fields to Controller: passed",
            event="host_records_manual_resume_binding",
            payload={"from_role": "host", "passed": True},
        )
        self.assertEqual(blocker["policy_row_id"], "fatal_protocol_violation")
        self.assertTrue(blocker["hard_stop_conditions"])
        self.assertTrue(self.handle_pending_control_blocker(root))

        body = self.pm_control_blocker_decision_body(
            blocker["blocker_id"],
            rerun_target="host_records_manual_resume_binding",
        )
        body["recovery_option"] = "allowed_waiver"
        body["return_gate"] = "host_records_manual_resume_binding"
        with self.assertRaisesRegex(router.RouterError, "not allowed by blocker policy"):
            router.record_external_event(
                root,
                "pm_records_control_blocker_repair_decision",
                self.role_decision_envelope(root, "synthetic/control_blocks/fatal_pm_waiver_rejected", body),
            )

    def test_resume_active_blocker_and_ambiguous_state_preempt_fake_package(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_runtime_entry(root)
        state = read_json(router.run_state_path(run_root))
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="synthetic_trace",
            error_message="Controller has no legal next action while fake package resumes",
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
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "handle_control_blocker")
        self.assertEqual(action["blocker_id"], blocker["blocker_id"])
        self.assertFalse((run_root / "continuation" / "pm_resume_decision.json").exists())

        ambiguous_root = self.make_project()
        ambiguous_run_root = self.boot_to_controller(ambiguous_root)
        self.ensure_current_role_agent_for_role(ambiguous_root, "worker")
        (ambiguous_run_root / "role_binding_memory" / "worker.json").unlink()
        router.record_external_event(ambiguous_root, "manual_resume_requested")
        action = self.next_after_display_sync(ambiguous_root)
        self.assertEqual(action["action_type"], "load_resume_state")
        router.apply_action(ambiguous_root, "load_resume_state")
        action = self.next_after_display_sync(ambiguous_root)
        self.assertEqual(action["action_type"], "rehydrate_role_bindings")
        self.assertEqual(action["memory_missing_role_keys"], ["worker"])
        router.apply_action(ambiguous_root, "rehydrate_role_bindings", self.resume_role_agent_payload(ambiguous_root, action))
        self.deliver_expected_card(ambiguous_root, "controller.resume_reentry")
        self.deliver_expected_card(ambiguous_root, "pm.role_binding_recovery_freshness")
        self.deliver_expected_card(ambiguous_root, "pm.resume_decision")

        with self.assertRaises(router.RouterError):
            router.record_external_event(
                ambiguous_root,
                "pm_resume_recovery_decision_returned",
                self.role_decision_envelope(
                    ambiguous_root,
                    "synthetic/continuation/pm_resume_decision_continue_ambiguous",
                    {
                        "decision_owner": "project_manager",
                        "decision": "continue_current_packet_loop",
                        **self.prior_path_context_review(
                            ambiguous_root,
                            "PM resume decision considered ambiguous current route memory.",
                        ),
                        "controller_reminder": {
                            "controller_only": True,
                            "controller_may_read_sealed_bodies": False,
                            "controller_may_infer_from_chat_history": False,
                            "controller_may_advance_or_close_route": False,
                        },
                    },
                ),
            )

    def _prepare_route_authority_parent_segment_wait(self, root: Path) -> Path:
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        router.record_external_event(
            root,
            "pm_activates_reviewed_route",
            {
                "route_id": "route-001",
                "active_node_id": "parent-001",
                "route_version": 1,
                "route": {
                    "schema_version": "flowpilot.route.v1",
                    "route_id": "route-001",
                    "route_version": 1,
                    "active_node_id": "parent-001",
                    "nodes": [
                        {
                            "node_id": "parent-001",
                            "status": "active",
                            "title": "Parent node",
                            "child_node_ids": ["child-001"],
                        },
                        {"node_id": "child-001", "status": "completed", "title": "Child node"},
                    ],
                },
            },
        )
        self.seed_child_completion_ledger(root, "child-001")
        self.deliver_current_node_cards(root)
        self.deliver_expected_card(root, "pm.parent_backward_targets")
        router.record_external_event(root, "pm_builds_parent_backward_targets")
        self.deliver_expected_card(root, "reviewer.parent_backward_replay")
        router.record_external_event(
            root,
            "reviewer_passes_parent_backward_replay",
            self.role_report_envelope(
                root,
                "synthetic/route_authority/parent_backward_replay",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )
        self.deliver_expected_card(root, "pm.parent_segment_decision")
        wait_action = router.next_action(root)
        self.assertEqual(wait_action["action_type"], "await_role_decision")
        self.assertIn("pm_records_parent_segment_decision", wait_action["allowed_external_events"])
        self.assertEqual(wait_action["legal_next_actions"]["current_owner"], "project_manager")
        self.assertEqual(
            wait_action["legal_next_actions"]["required_repair_command"],
            "submit_pm_parent_segment_decision",
        )
        return run_root

    def test_route_authority_wrong_path_rejection_guides_corrected_retry_fake_package(self) -> None:
        root = self.make_project()
        run_root = self._prepare_route_authority_parent_segment_wait(root)

        with self.assertRaisesRegex(router.RouterError, "rejected by route authority") as raised:
            router.record_external_event(root, "pm_completes_parent_node_from_backward_replay")

        blocker = raised.exception.control_blocker
        rejection = blocker["route_authority_rejection"]
        self.assertEqual(rejection["rejection_kind"], "wrong_path")
        self.assertEqual(rejection["rejected_action_id"], "complete_parent_node")
        self.assertEqual(rejection["legal_action_ids"], ["record_parent_segment_decision"])
        self.assertEqual(rejection["required_repair_command"], "submit_pm_parent_segment_decision")
        self.assertFalse(rejection["fallback_or_alias_translation_allowed"])

        router.record_external_event(
            root,
            "pm_records_parent_segment_decision",
            self.role_decision_envelope(
                root,
                "synthetic/route_authority/corrected_parent_segment_decision",
                {
                    "decision_owner": "project_manager",
                    "decision": "continue",
                    **self.prior_path_context_review(
                        root,
                        "Corrected retry used submit_pm_parent_segment_decision after route-authority feedback.",
                    ),
                },
            ),
        )

        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["parent_segment_decision_recorded"])
        self.assertEqual(state["flags"].get("last_route_authority_rejected_action"), None)

    def test_route_mutation_stale_sibling_proof_fake_package(self) -> None:
        contract_harness = RouteMutationContractHarness(methodName="runTest")
        root = contract_harness.make_project()
        run_root, contract = contract_harness.seed_route_mutation_child_contract(
            root,
            route_shape="sibling",
            packet_id="synthetic-node-packet-sibling-replacement",
        )
        self.assertEqual(contract["schema_version"], ROUTE_MUTATION_CHILD_CONTRACT_SCHEMA)
        self.assertIn("deliver_current_node_cards", contract["forbidden_parent_helpers"])

        with self.assertRaisesRegex(router.RouterError, "affected_sibling_nodes"):
            router.record_external_event(
                root,
                "pm_mutates_route_after_review_block",
                {
                    "repair_node_id": "node-002-v2",
                    "topology_strategy": "sibling_branch_replacement",
                    "repair_of_node_id": "node-002",
                    "replay_scope_node_id": "route-root",
                    "stale_evidence": ["node-002-old-proof"],
                    **self.prior_path_context_review(root, "Invalid sibling replacement intentionally lacks affected sibling list."),
                },
            )

        router.record_external_event(
            root,
            "pm_mutates_route_after_review_block",
            {
                "repair_node_id": "node-002-v2",
                "topology_strategy": "sibling_branch_replacement",
                "repair_of_node_id": "node-002",
                "affected_sibling_nodes": ["node-002"],
                "replay_scope_node_id": "route-root",
                "reason": "replace invalid sibling branch",
                "stale_evidence": ["node-002-old-proof"],
                **self.prior_path_context_review(root, "Sibling branch replacement considered stale sibling proof and replay scope."),
            },
        )

        frontier = read_json(run_root / "execution_frontier.json")
        self.assertEqual(frontier["status"], "route_mutation_pending_recheck")
        stale_ledger = read_json(run_root / "evidence" / "stale_evidence_ledger.json")
        self.assertIn("node-002-old-proof", {item["evidence_id"] for item in stale_ledger["items"]})
        packet_ledger = read_json(run_root / "packet_ledger.json")
        self.assertEqual(packet_ledger["active_packet_status"], "superseded")
        self.assertEqual(packet_ledger["route_mutation_packet_disposition"]["topology_strategy"], "sibling_branch_replacement")

    def test_pm_package_disposition_envelope_authority_fake_package(self) -> None:
        replay = run_worker_result_trace(
            SyntheticTracePackage(
                name="pm_package_disposition_envelope_authority",
                next_recipient="project_manager",
            )
        )
        disposition = replay.pm_disposition()
        self.assertEqual(disposition["output_type"], "pm_package_result_disposition")
        self.assertEqual(disposition["from_role"], "project_manager")
        self.assertEqual(disposition["controller_visibility"], "role_output_envelope_only")
        self.assertFalse(disposition["chat_response_body_allowed"])

        with self.assertRaisesRegex(role_output_runtime.RoleOutputRuntimeError, "may be submitted only"):
            role_output_runtime.submit_output(
                replay.root,
                output_type="pm_package_result_disposition",
                role="controller",
                agent_id="agent-controller",
                body={
                    "decided_by_role": "controller",
                    "decision": "absorbed",
                    "decision_reason": "Controller cannot submit PM package disposition.",
                },
            )

    def test_controller_boundary_repair_budget_escalates_fake_package(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)

        run_root, state, action = self.controller_boundary_recovery_action(root)
        entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        state["pending_action"] = action
        router._write_controller_receipt(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            action_id=entry["action_id"],
            status="done",
            payload={"controller_action_completed": True},
        )
        router.save_run_state(run_root, state)
        repair_1 = self.next_after_display_sync(root)
        router.record_controller_action_receipt(
            root,
            action_id=repair_1["controller_action_id"],
            status="done",
            payload={"controller_action_completed": True},
        )
        repair_2 = read_json(router.run_state_path(run_root))["pending_action"]
        self.assertEqual(repair_2["action_type"], "complete_missing_controller_deliverable")
        self.assertEqual(repair_2["repair_attempt"], 2)

        router.record_controller_action_receipt(
            root,
            action_id=repair_2["controller_action_id"],
            status="done",
            payload={"controller_action_completed": True},
        )

        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state.get("active_control_blocker"))
        original = read_json(router._controller_action_path(run_root, entry["action_id"]))  # type: ignore[attr-defined]
        self.assertEqual(original["status"], "blocked")
        self.assertEqual(original["deliverable_repair_failed_receipts"], 2)

    def test_material_repair_generation_blocks_stale_flags_fake_package(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_runtime_entry(root)

        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        state = read_json(router.run_state_path(run_root))
        generation = router._commit_material_scan_repair_generation(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            transaction_id="synthetic-repair-tx-active-generation",
            packet_generation_id="synthetic-repair-tx-active-generation-gen-001",
            packet_specs=[
                {"packet_id": "synthetic-material-repair-worker", "to_role": "worker", "body_text": "Repair generation packet"},
            ],
        )
        state["flags"]["material_scan_packets_relayed"] = True
        state["flags"]["worker_packets_delivered"] = True
        state["flags"]["worker_scan_results_returned"] = True
        state["flags"]["material_scan_results_relayed_to_pm"] = True
        state["flags"]["material_scan_result_disposition_recorded"] = True
        router.save_run_state(run_root, state)
        self.ensure_current_role_agent_for_role(root, "worker")

        action = self.next_after_display_sync(root)

        self.assertEqual(action["action_type"], "relay_material_scan_packets")
        self.assertEqual(set(action["packet_ids"]), {packet["packet_id"] for packet in generation["packets"]})
        batch = router._active_parallel_packet_batch(run_root, "material_scan")  # type: ignore[attr-defined]
        self.assertEqual(batch["counts"]["relayed"], 0)
        self.assertEqual(batch["counts"]["results_returned"], 0)

    def test_dirty_terminal_ledgers_block_completion_fake_package(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id="synthetic-node-packet-dirty-ledger")
        self.complete_evidence_quality_package(root)
        self.write_pm_suggestion_ledger(root, [self.pm_suggestion_entry(root, clean=False)])

        self.deliver_expected_card(root, "pm.final_ledger")
        with self.assertRaisesRegex(router.RouterError, "clean PM suggestion ledger"):
            router.record_external_event(root, "pm_records_final_route_wide_ledger_clean", self.final_ledger_payload(root))

    def test_system_story_valid_repair_envelope_bad_content_is_rejected(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        state["flags"]["pm_route_skeleton_card_delivered"] = True
        router.save_run_state(run_root, state)
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="systemic_synthetic_trace",
            error_message="valid envelope carries a PM repair decision missing self-check content",
            event="reviewer_reports_material_sufficient",
            payload={"report_path": ".flowpilot/runs/test/reviews/systemic-valid-envelope-bad-content.json"},
        )
        self.assertTrue(self.handle_pending_control_blocker(root))
        body = self.pm_control_blocker_decision_body(blocker["blocker_id"], rerun_target="pm_writes_route_draft")
        body.pop("contract_self_check")

        with self.assertRaisesRegex(router.RouterError, "requires contract_self_check"):
            router.record_external_event(
                root,
                "pm_records_control_blocker_repair_decision",
                self.role_decision_envelope(root, "systemic/bad_pm_repair_content", body),
            )
        saved = read_json(router.run_state_path(run_root))
        self.assertEqual(saved["active_control_blocker"]["blocker_id"], blocker["blocker_id"])

    def test_system_story_stacked_blockers_preempt_and_preserve_dirty_ledger(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="systemic_synthetic_trace",
            error_message="active blocker must preempt dirty ledger story",
            action_type="controller_no_legal_next_action",
            payload={"path": self.rel(root, router.run_state_path(run_root)), "role": "controller"},
        )
        self.write_pm_suggestion_ledger(root, [self.pm_suggestion_entry(root, clean=False)])

        action = self.next_after_display_sync(root)

        self.assertEqual(action["action_type"], "handle_control_blocker")
        self.assertEqual(action["blocker_id"], blocker["blocker_id"])
        router.apply_action(root, "handle_control_blocker")
        ledger_text = (run_root / "pm_suggestion_ledger.jsonl").read_text(encoding="utf-8")
        self.assertIn('"closure": {"blocks_current_gate_until_closed": true', ledger_text)

    def test_system_story_failed_pm_repair_loop_registers_followup_blocker(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_runtime_entry(root)
        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        state = read_json(router.run_state_path(run_root))
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="systemic_synthetic_trace",
            error_message="PM repair loop still has invalid material dispatch evidence",
            action_type="controller_no_legal_next_action",
            payload={"path": self.rel(root, router.run_state_path(run_root)), "role": "controller"},
        )
        self.assertTrue(self.handle_pending_control_blocker(root))
        decision = self.pm_control_blocker_decision_body(
            blocker["blocker_id"],
            decision="repair_completed",
            rerun_target="router_direct_material_scan_dispatch_recheck_passed",
        )
        decision["repair_transaction"] = {
            "plan_kind": "packet_reissue",
            "replacement_packets": [
                {
                    "packet_id": "systemic-material-scan-r1",
                    "replacement_for": "material-scan-001",
                    "to_role": "worker",
                    "body_text": "Systemic replay replacement packet with still-blocked dispatch evidence.",
                }
            ],
        }
        router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(root, "systemic/pm_repair_loop_decision", decision),
        )

        router.record_external_event(
            root,
            "router_direct_material_scan_dispatch_recheck_blocked",
            self.role_report_envelope(
                root,
                "systemic/pm_repair_loop_recheck_blocked",
                {
                    "checked_by_role": "controller",
                    "dispatch_allowed": False,
                    "blockers": ["replacement packet still lacks valid dispatch evidence"],
                },
            ),
        )

        state = read_json(router.run_state_path(run_root))
        active = state["active_control_blocker"]
        self.assertNotEqual(active["blocker_id"], blocker["blocker_id"])
        self.assertEqual(active["handling_lane"], "pm_repair_decision_required")
        tx_index = read_json(run_root / "control_blocks" / "repair_transactions" / "repair_transaction_index.json")
        self.assertIsNone(tx_index["active_transaction"])

    def test_system_story_stale_run_state_save_cannot_clear_active_blocker(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        stale_state, _ = router.load_run_state_from_run_root(root, run_root)
        state = read_json(router.run_state_path(run_root))
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="systemic_synthetic_trace",
            error_message="foreground control blocker written after stale state load",
            action_type="controller_no_legal_next_action",
            payload={"path": self.rel(root, router.run_state_path(run_root)), "role": "controller"},
        )

        router.save_run_state(run_root, stale_state)

        saved = read_json(router.run_state_path(run_root))
        self.assertEqual(saved["active_control_blocker"]["blocker_id"], blocker["blocker_id"])
        self.assertEqual(saved["latest_control_blocker_path"], blocker["blocker_artifact_path"])
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "handle_control_blocker")

    def test_system_story_parallel_run_stop_does_not_touch_peer_authority(self) -> None:
        root = self.make_project()
        run_a = self.write_minimal_run(root, "run-a")
        run_b = self.write_minimal_run(root, "run-b")
        self.write_current_focus(root, run_b)
        state_a = read_json(router.run_state_path(run_a))
        state_b = read_json(router.run_state_path(run_b))
        router._acquire_router_daemon_lock(root, run_a, state_a)  # type: ignore[attr-defined]
        router._acquire_router_daemon_lock(root, run_b, state_b)  # type: ignore[attr-defined]

        stopped = router.stop_router_daemon(root, reason="systemic_peer_stop", run_root=run_a)

        self.assertEqual(stopped["run_id"], "run-a")
        current = read_json(root / ".flowpilot" / "current.json")
        self.assertEqual(current.get("run_id"), "run-b")
        self.assertEqual(read_json(run_a / "runtime" / "router_daemon.lock")["status"], "released")
        self.assertEqual(read_json(run_b / "runtime" / "router_daemon.lock")["status"], "active")
        self.assertFalse(read_json(router.run_state_path(run_a))["daemon_mode_enabled"])
        self.assertTrue(read_json(router.run_state_path(run_b))["daemon_mode_enabled"])

    def test_system_story_terminal_total_gate_rejects_multiple_dirty_sources(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id="systemic-node-packet-total-gate")
        self.complete_evidence_quality_package(root)
        self.complete_final_ledger_and_terminal_replay(root)
        self.deliver_expected_card(root, "pm.closure")
        self.write_pm_suggestion_ledger(root, [self.pm_suggestion_entry(root, clean=False)])
        self.write_self_interrogation_record(root, "terminal", clean=False)
        defect_ledger_path = run_root / "defects" / "defect_ledger.json"
        router.write_json(
            defect_ledger_path,
            {
                "schema_version": "flowpilot.defect_ledger.v1",
                "run_id": run_root.name,
                "route_id": "route-001",
                "route_version": 1,
                "pm_owned": True,
                "status": "active",
                "counts": {
                    "total": 1,
                    "open": 1,
                    "blocker_open": 1,
                    "fixed_pending_recheck": 0,
                    "closed": 0,
                    "deferred": 0,
                },
                "defects": [
                    {
                        "defect_id": "systemic-terminal-defect",
                        "severity": "blocker",
                        "status": "open",
                        "pm_triage": {"recheck_role_class": "human_like_reviewer"},
                        "recheck_paths": [],
                    }
                ],
            },
        )

        with self.assertRaisesRegex(router.RouterError, "defect_ledger|PM suggestion ledger|self_interrogation"):
            router.record_external_event(
                root,
                "pm_approves_terminal_closure",
                self.role_decision_envelope(
                    root,
                    "systemic/terminal_total_gate_dirty_sources",
                    self.pm_terminal_closure_body(root, "Terminal closure attempted with multiple dirty sources."),
                ),
            )
        state = read_json(router.run_state_path(run_root))
        self.assertNotEqual(state["status"], "closed")


if __name__ == "__main__":
    unittest.main()
