from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
sys.path.insert(0, str(ASSETS))

import flowpilot_router as router  # noqa: E402
import flowpilot_runtime  # noqa: E402
import role_output_runtime  # noqa: E402


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class FlowPilotRoleOutputRuntimeTests(unittest.TestCase):
    def make_project(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="flowpilot-role-output-runtime-"))
        registry_src = ASSETS / "runtime_kit" / "contracts" / "contract_index.json"
        registry_dst = root / "skills" / "flowpilot" / "assets" / "runtime_kit" / "contracts" / "contract_index.json"
        registry_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(registry_src, registry_dst)
        catalog_src = ASSETS / "runtime_kit" / "quality_pack_catalog.json"
        catalog_dst = root / "skills" / "flowpilot" / "assets" / "runtime_kit" / "quality_pack_catalog.json"
        shutil.copyfile(catalog_src, catalog_dst)
        _write_json(
            root / ".flowpilot" / "current.json",
            {
                "current_run_id": "run-test",
                "current_run_root": ".flowpilot/runs/run-test",
            },
        )
        return root

    def read_json(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def test_pm_resume_submit_fills_mechanical_fields_and_returns_direct_router_envelope(self) -> None:
        root = self.make_project()
        envelope = role_output_runtime.submit_output(
            root,
            output_type="pm_resume_recovery_decision",
            role="project_manager",
            agent_id="agent-pm-001",
            body={
                "decision": "continue_current_packet_loop",
                "explicit_recovery_evidence_recorded": True,
                "prior_path_context_review": {
                    "impact_on_decision": "PM checked current route memory and found no stale or superseded path.",
                },
            },
            output_path=".flowpilot/runs/run-test/continuation/pm_resume_runtime_body.json",
        )

        self.assertEqual(envelope["schema_version"], role_output_runtime.ROLE_OUTPUT_ENVELOPE_SCHEMA)
        self.assertEqual(
            envelope["router_submission_schema"],
            role_output_runtime.ROLE_OUTPUT_DIRECT_ROUTER_SUBMISSION_SCHEMA,
        )
        self.assertEqual(envelope["body_ref"]["path"], ".flowpilot/runs/run-test/continuation/pm_resume_runtime_body.json")
        self.assertIn("runtime_receipt_ref", envelope)
        self.assertEqual(envelope["controller_visibility"], "role_output_envelope_only")
        self.assertEqual(envelope["delivery_mode"], "direct_to_router")
        self.assertEqual(envelope["submitted_to"], "router")
        self.assertEqual(envelope["to_role"], "router")
        self.assertFalse(envelope["controller_handoff_used"])
        self.assertFalse(envelope["controller_receives_role_output"])
        self.assertFalse(envelope["chat_response_body_allowed"])
        self.assertNotIn("decision_path", envelope)
        self.assertNotIn("decision_hash", envelope)
        self.assertNotIn("decision", envelope)
        self.assertNotIn("evidence", envelope)
        self.assertTrue(envelope["role_output_runtime_validated"])

        body = self.read_json(root / envelope["body_ref"]["path"])
        self.assertEqual(body["decision_owner"], "project_manager")
        self.assertEqual(body["controller_reminder"]["controller_may_read_sealed_bodies"], False)
        self.assertEqual(body["prior_path_context_review"]["completed_nodes_considered"], [])
        self.assertTrue(body["contract_self_check"]["all_required_fields_present"])
        ledger = self.read_json(root / ".flowpilot" / "runs" / "run-test" / "role_output_ledger.json")
        self.assertEqual(ledger["outputs"][0]["output_type"], "pm_resume_recovery_decision")

    def test_registry_backed_output_types_are_preparable(self) -> None:
        root = self.make_project()
        registry = self.read_json(ASSETS / "runtime_kit" / "contracts" / "contract_index.json")
        for contract in registry["contracts"]:
            if contract.get("runtime_channel") != "role_output_runtime":
                continue
            output_types = [contract["output_type"], *contract.get("output_type_aliases", [])]
            expected_event = contract.get("router_event") if contract.get("router_event_mode") == "fixed" else None
            for output_type in output_types:
                session = role_output_runtime.prepare_output_session(
                    root,
                    output_type=output_type,
                    role=contract["recipient_roles"][0],
                    agent_id=f"agent-{output_type}",
                )
                self.assertEqual(session["output_type"], output_type)
                self.assertEqual(session["output_contract_id"], contract["contract_id"])
                self.assertEqual(session["event_name"], expected_event)
                self.assertEqual(session["path_key"], contract["path_key"])
                self.assertEqual(session["hash_key"], contract["hash_key"])

    def test_startup_activation_approval_is_registry_bound_runtime_output(self) -> None:
        root = self.make_project()
        envelope = role_output_runtime.submit_output(
            root,
            output_type="pm_startup_activation_approval",
            role="project_manager",
            agent_id="agent-pm-startup",
            body={"decision": "approved"},
        )

        self.assertEqual(envelope["event_name"], "pm_approves_startup_activation")
        self.assertEqual(
            envelope["output_contract_id"],
            "flowpilot.output_contract.pm_startup_activation_approval.v1",
        )
        body = self.read_json(root / envelope["body_ref"]["path"])
        self.assertEqual(body["schema_version"], "flowpilot.pm_startup_activation_approval.v1")
        self.assertEqual(body["approved_by_role"], "project_manager")
        self.assertEqual(body["decision"], "approved")

    def test_direct_router_submission_authority_accepts_fixed_contract_event(self) -> None:
        root = self.make_project()
        authority = role_output_runtime.validate_direct_router_submission_authority(
            root,
            output_type="pm_resume_recovery_decision",
            role="project_manager",
            agent_id="agent-pm-fixed-authority",
        )

        self.assertTrue(authority["ok"])
        self.assertEqual(authority["authority_source"], "fixed_contract_event")
        self.assertEqual(authority["event_name"], "pm_resume_recovery_decision_returned")

    def test_router_supplied_direct_submission_requires_current_wait_authority(self) -> None:
        root = self.make_project()
        with self.assertRaisesRegex(role_output_runtime.RoleOutputRuntimeError, "Router-supplied event"):
            role_output_runtime.validate_direct_router_submission_authority(
                root,
                output_type="officer_model_report",
                role="product_flowguard_officer",
                agent_id="agent-product-officer-no-event",
            )

        _write_json(
            root / ".flowpilot" / "runs" / "run-test" / "state.json",
            {
                "pending_action": {
                    "action_type": "await_role_decision",
                    "to_role": "project_manager",
                    "allowed_external_events": ["pm_registers_role_work_request"],
                }
            },
        )
        with self.assertRaisesRegex(role_output_runtime.RoleOutputRuntimeError, "not currently allowed"):
            role_output_runtime.validate_direct_router_submission_authority(
                root,
                output_type="officer_model_report",
                role="product_flowguard_officer",
                agent_id="agent-product-officer-wrong-event",
                event_name="product_officer_model_report",
            )

        _write_json(
            root / ".flowpilot" / "runs" / "run-test" / "state.json",
            {
                "pending_action": {
                    "action_type": "await_role_decision",
                    "to_role": "product_flowguard_officer",
                    "allowed_external_events": [
                        "product_officer_passes_product_architecture_modelability",
                        "product_officer_blocks_product_architecture_modelability",
                    ],
                }
            },
        )
        with self.assertRaisesRegex(role_output_runtime.RoleOutputRuntimeError, "not currently allowed"):
            role_output_runtime.validate_direct_router_submission_authority(
                root,
                output_type="officer_model_report",
                role="product_flowguard_officer",
                agent_id="agent-product-officer-legacy-event",
                event_name="product_officer_model_report",
            )
        authority = role_output_runtime.validate_direct_router_submission_authority(
            root,
            output_type="officer_model_report",
            role="product_flowguard_officer",
            agent_id="agent-product-officer-current-wait",
            event_name="product_officer_blocks_product_architecture_modelability",
        )
        self.assertTrue(authority["ok"])
        self.assertEqual(authority["authority_source"], "current_router_wait")

    def test_cli_submit_output_to_router_blocks_router_supplied_output_without_current_wait(self) -> None:
        root = self.make_project()
        with self.assertRaisesRegex(role_output_runtime.RoleOutputRuntimeError, "Router-supplied event"):
            flowpilot_runtime.main(
                [
                    "--root",
                    str(root),
                    "submit-output-to-router",
                    "--output-type",
                    "officer_model_report",
                    "--role",
                    "product_flowguard_officer",
                    "--agent-id",
                    "agent-product-officer-cli",
                    "--body-json",
                    "{}",
                ]
            )

        self.assertFalse((root / ".flowpilot" / "runs" / "run-test" / "role_outputs").exists())

    def test_cli_submit_output_to_router_returns_next_action_for_control_blocker(self) -> None:
        root = self.make_project()
        blocker = {
            "blocker_id": "control-blocker-test",
            "handling_lane": "pm_repair_decision_required",
            "target_role": "project_manager",
        }
        next_action = {
            "action_type": "handle_control_blocker",
            "to_role": "project_manager",
            "blocker_id": "control-blocker-test",
        }
        envelope = {
            "schema_version": role_output_runtime.ROLE_OUTPUT_ENVELOPE_SCHEMA,
            "event_name": "reviewer_reports_startup_facts",
            "body_ref": {"path": ".flowpilot/runs/run-test/reviews/startup_fact_report.json", "hash": "abc"},
        }

        with (
            mock.patch.object(
                flowpilot_runtime.role_output_runtime,
                "validate_direct_router_submission_authority",
                return_value={"ok": True, "authority_source": "current_router_wait"},
            ),
            mock.patch.object(flowpilot_runtime.role_output_runtime, "submit_output", return_value=envelope),
            mock.patch.object(
                flowpilot_runtime.flowpilot_router,
                "record_external_event",
                side_effect=router.RouterError("event blocked", control_blocker=blocker),
            ),
            mock.patch.object(flowpilot_runtime.flowpilot_router, "next_action", return_value=next_action),
            mock.patch("builtins.print") as printed,
        ):
            exit_code = flowpilot_runtime.main(
                [
                    "--root",
                    str(root),
                    "submit-output-to-router",
                    "--output-type",
                    "startup_fact_report",
                    "--role",
                    "human_like_reviewer",
                    "--agent-id",
                    "agent-reviewer-cli",
                    "--body-json",
                    "{}",
                    "--event-name",
                    "reviewer_reports_startup_facts",
                ]
            )

        self.assertEqual(exit_code, 0)
        payload = json.loads(printed.call_args.args[0])
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["blocked"])
        self.assertEqual(payload["event"], "reviewer_reports_startup_facts")
        self.assertEqual(payload["control_blocker"]["blocker_id"], "control-blocker-test")
        self.assertEqual(payload["next_action"]["action_type"], "handle_control_blocker")
        self.assertEqual(payload["next_action_source"], "router")

    def test_cli_submit_output_to_router_preserves_plain_router_errors(self) -> None:
        root = self.make_project()
        envelope = {
            "schema_version": role_output_runtime.ROLE_OUTPUT_ENVELOPE_SCHEMA,
            "event_name": "reviewer_reports_startup_facts",
            "body_ref": {"path": ".flowpilot/runs/run-test/reviews/startup_fact_report.json", "hash": "abc"},
        }

        with (
            mock.patch.object(
                flowpilot_runtime.role_output_runtime,
                "validate_direct_router_submission_authority",
                return_value={"ok": True, "authority_source": "current_router_wait"},
            ),
            mock.patch.object(flowpilot_runtime.role_output_runtime, "submit_output", return_value=envelope),
            mock.patch.object(
                flowpilot_runtime.flowpilot_router,
                "record_external_event",
                side_effect=router.RouterError("plain router error"),
            ),
        ):
            with self.assertRaisesRegex(router.RouterError, "plain router error"):
                flowpilot_runtime.main(
                    [
                        "--root",
                        str(root),
                        "submit-output-to-router",
                        "--output-type",
                        "startup_fact_report",
                        "--role",
                        "human_like_reviewer",
                        "--agent-id",
                        "agent-reviewer-cli",
                        "--body-json",
                        "{}",
                        "--event-name",
                        "reviewer_reports_startup_facts",
                    ]
                )

    def test_router_validates_runtime_receipt_when_loading_role_output(self) -> None:
        root = self.make_project()
        envelope = role_output_runtime.submit_output(
            root,
            output_type="pm_resume_recovery_decision",
            role="project_manager",
            agent_id="agent-pm-002",
            body={
                "decision": "restore_or_replace_roles_from_memory",
                "explicit_recovery_evidence_recorded": False,
                "prior_path_context_review": {
                    "impact_on_decision": "PM selected role restoration after checking current route memory.",
                },
            },
        )

        loaded = router._load_file_backed_role_payload(root, envelope)  # type: ignore[attr-defined]

        self.assertEqual(loaded["decision_owner"], "project_manager")
        self.assertTrue(loaded["_role_output_envelope"]["role_output_runtime_validated"])
        self.assertEqual(
            loaded["_role_output_envelope"]["output_contract_id"],
            "flowpilot.output_contract.pm_resume_decision.v1",
        )

        envelope_path = root / ".flowpilot" / "runs" / "run-test" / "continuation" / "pm_resume_runtime_envelope.json"
        _write_json(envelope_path, envelope)
        artifact_validation = router.validate_artifact(
            root,
            "role_output_envelope",
            ".flowpilot/runs/run-test/continuation/pm_resume_runtime_envelope.json",
        )
        self.assertTrue(artifact_validation["ok"], artifact_validation)

    def test_runtime_rejects_missing_role_authored_required_choice(self) -> None:
        root = self.make_project()
        with self.assertRaisesRegex(role_output_runtime.RoleOutputRuntimeError, "decision"):
            role_output_runtime.submit_output(
                root,
                output_type="pm_resume_recovery_decision",
                role="project_manager",
                agent_id="agent-pm-003",
                body={
                    "explicit_recovery_evidence_recorded": True,
                    "prior_path_context_review": {
                        "impact_on_decision": "Missing decision should be rejected before the router sees it.",
                    },
                },
            )

    def test_runtime_rejects_wrong_role_and_role_key_agent_id(self) -> None:
        root = self.make_project()
        with self.assertRaisesRegex(role_output_runtime.RoleOutputRuntimeError, "may be submitted only"):
            role_output_runtime.submit_output(
                root,
                output_type="pm_resume_recovery_decision",
                role="controller",
                agent_id="agent-controller-001",
                body={"decision": "continue_current_packet_loop"},
            )
        with self.assertRaisesRegex(role_output_runtime.RoleOutputRuntimeError, "not a role key"):
            role_output_runtime.prepare_output_session(
                root,
                output_type="gate_decision",
                role="human_like_reviewer",
                agent_id="human_like_reviewer",
            )

    def test_controller_boundary_confirmation_is_controller_scoped_runtime_output(self) -> None:
        root = self.make_project()
        envelope = role_output_runtime.submit_output(
            root,
            output_type="controller_boundary_confirmation",
            role="controller",
            agent_id="agent-controller-runtime",
            body={
                "event": "controller_role_confirmed_from_router_core",
                "confirmed_by_role": "controller",
                "confirmation_source": "router_delivered_controller_core",
                "controller_core_card_id": "controller.core",
                "controller_core_path": ".flowpilot/runs/run-test/runtime_kit/cards/roles/controller.md",
                "controller_core_sha256": "0" * 64,
                "manifest_path": ".flowpilot/runs/run-test/runtime_kit/manifest.json",
                "manifest_sha256": "1" * 64,
                "controller_policy": {"relay_and_record_only": True},
                "controller_policy_sha256": "2" * 64,
                "boundary_constraints": {
                    "controller_may_read_sealed_bodies": False,
                    "controller_may_approve_gate": False,
                    "controller_may_mutate_route": False,
                },
                "sealed_body_reads_allowed": False,
                "router_owned_confirmation": True,
                "confirmed_at": "2026-05-15T00:00:00Z",
            },
            output_path=".flowpilot/runs/run-test/startup/controller_boundary_confirmation.json",
        )

        self.assertEqual(envelope["from_role"], "controller")
        self.assertEqual(envelope["output_type"], "controller_boundary_confirmation")
        self.assertEqual(
            envelope["output_contract_id"],
            "flowpilot.output_contract.controller_boundary_confirmation.v1",
        )
        self.assertEqual(envelope["body_ref"]["path_key"], "confirmation_path")
        self.assertEqual(envelope["body_ref"]["hash_key"], "confirmation_hash")
        self.assertNotIn("event_name", envelope)
        body = self.read_json(root / envelope["body_ref"]["path"])
        self.assertEqual(body["confirmed_by_role"], "controller")
        self.assertEqual(body["_role_output_contract"]["contract_id"], envelope["output_contract_id"])

        with self.assertRaisesRegex(role_output_runtime.RoleOutputRuntimeError, "may be submitted only"):
            role_output_runtime.submit_output(
                root,
                output_type="controller_boundary_confirmation",
                role="project_manager",
                agent_id="agent-pm-not-controller",
                body={},
            )

    def test_controller_boundary_helper_writes_runtime_body_receipt_and_ledger(self) -> None:
        root = self.make_project()
        run_root = root / ".flowpilot" / "runs" / "run-test"
        controller_card = run_root / "runtime_kit" / "cards" / "roles" / "controller.md"
        controller_card.parent.mkdir(parents=True, exist_ok=True)
        controller_card.write_text("Controller core card\n", encoding="utf-8")
        _write_json(
            run_root / "runtime_kit" / "manifest.json",
            {
                "schema_version": "flowpilot.prompt_manifest.v1",
                "controller_policy": {"relay_and_record_only": True},
                "cards": [
                    {
                        "id": "controller.core",
                        "audience": "controller",
                        "kind": "role_core",
                        "path": "cards/roles/controller.md",
                    }
                ],
            },
        )

        envelope = role_output_runtime.submit_controller_boundary_confirmation(
            root,
            agent_id="agent-controller-boundary-helper",
            action_id="controller-action-1",
            source_action_id="router-action-1",
        )
        body_path = root / envelope["body_ref"]["path"]
        body_hash = role_output_runtime._sha256_file(body_path)  # type: ignore[attr-defined]
        recovered = role_output_runtime.runtime_envelope_for_body(
            root,
            output_type="controller_boundary_confirmation",
            body_path=body_path,
            body_hash=body_hash,
        )

        self.assertEqual(recovered, envelope)
        body = self.read_json(body_path)
        self.assertEqual(body["controller_action_id"], "controller-action-1")
        self.assertEqual(body["source_action_id"], "router-action-1")
        self.assertEqual(body["boundary_constraints"], role_output_runtime.controller_boundary_constraints())

    def test_gate_decision_runtime_keeps_owner_role_mechanical_and_not_semantic(self) -> None:
        root = self.make_project()
        evidence_path = root / ".flowpilot" / "runs" / "run-test" / "evidence" / "gate.json"
        _write_json(evidence_path, {"checked": True})
        envelope = role_output_runtime.submit_output(
            root,
            output_type="gate_decision",
            role="human_like_reviewer",
            agent_id="agent-reviewer-001",
            body={
                "gate_id": "quality-gate-001",
                "gate_kind": "quality",
                "risk_type": "visual_quality",
                "gate_strength": "hard",
                "decision": "pass",
                "blocking": False,
                "required_evidence": ["reviewer walkthrough"],
                "evidence_refs": [
                    {
                        "kind": "file",
                        "path": ".flowpilot/runs/run-test/evidence/gate.json",
                        "hash": role_output_runtime._sha256_file(evidence_path),  # type: ignore[attr-defined]
                        "summary": "Reviewer checked the evidence file.",
                    }
                ],
                "reason": "The reviewer has direct evidence for the gate decision.",
                "next_action": "continue",
            },
        )

        body = self.read_json(root / envelope["body_ref"]["path"])
        self.assertEqual(body["owner_role"], "human_like_reviewer")
        self.assertFalse(envelope["semantic_sufficiency_reviewed_by_runtime"])
        self.assertTrue(body["contract_self_check"]["runtime_mechanical_validation_passed"])

    def test_quality_pack_checks_are_generic_and_route_declared(self) -> None:
        root = self.make_project()
        _write_json(
            root / ".flowpilot" / "runs" / "run-test" / "quality" / "attached_quality_packs.json",
            {
                "quality_packs": [
                    {"pack_id": "ui_visual_interaction_quality_pack"},
                    {"pack_id": "localization_quality_pack"},
                ]
            },
        )
        session = role_output_runtime.prepare_output_session(
            root,
            output_type="reviewer_review_report",
            role="human_like_reviewer",
            agent_id="agent-reviewer-quality",
        )
        skeleton = session["body_skeleton"]
        self.assertEqual(
            [row["pack_id"] for row in skeleton["quality_pack_checks"]],
            ["ui_visual_interaction_quality_pack", "localization_quality_pack"],
        )
        self.assertEqual(skeleton["pm_suggestion_items"], [])
        envelope = role_output_runtime.submit_output(
            root,
            output_type="reviewer_review_report",
            role="human_like_reviewer",
            agent_id="agent-reviewer-quality",
            body={
                "passed": True,
                "review_summary": "Reviewer checked the declared generic quality-pack rows.",
                "direct_evidence_paths_checked": [],
                "findings": [],
                "blockers": [],
                "residual_risks": [],
                "quality_pack_checks": [
                    {
                        "pack_id": "ui_visual_interaction_quality_pack",
                        "status": "satisfied",
                        "evidence_refs": [],
                        "blockers": [],
                        "waivers": [],
                    },
                    {
                        "pack_id": "localization_quality_pack",
                        "status": "not_applicable",
                        "evidence_refs": [],
                        "blockers": [],
                        "waivers": [],
                    },
                ],
                "independent_challenge": {
                    "scope_restatement": "Generic quality-pack response structure only.",
                    "explicit_and_implicit_commitments": [],
                    "failure_hypotheses": [],
                    "challenge_actions": [],
                    "blocking_findings": [],
                    "non_blocking_findings": [],
                    "pass_or_block": "pass",
                    "reroute_request": [],
                    "challenge_waivers": [],
                },
            },
        )
        body = self.read_json(root / envelope["body_ref"]["path"])
        self.assertEqual(len(body["quality_pack_checks"]), 2)
        self.assertEqual(body["pm_suggestion_items"], [])

        with self.assertRaisesRegex(role_output_runtime.RoleOutputRuntimeError, "quality_pack_checks"):
            role_output_runtime.submit_output(
                root,
                output_type="reviewer_review_report",
                role="human_like_reviewer",
                agent_id="agent-reviewer-quality-2",
                body={
                    "passed": True,
                    "review_summary": "Missing declared quality pack rows should fail.",
                    "direct_evidence_paths_checked": [],
                    "findings": [],
                    "blockers": [],
                    "residual_risks": [],
                    "independent_challenge": {
                        "scope_restatement": "Missing pack rows.",
                        "explicit_and_implicit_commitments": [],
                        "failure_hypotheses": [],
                        "challenge_actions": [],
                        "blocking_findings": [],
                        "non_blocking_findings": [],
                        "pass_or_block": "pass",
                        "reroute_request": [],
                        "challenge_waivers": [],
                    },
                },
            )

    def test_role_output_progress_status_is_default_runtime_written_metadata(self) -> None:
        root = self.make_project()
        session = role_output_runtime.prepare_output_session(
            root,
            output_type="pm_resume_recovery_decision",
            role="project_manager",
            agent_id="agent-pm-progress",
        )

        status_path = root / session["controller_status_packet_path"]
        self.assertTrue(status_path.exists())
        self.assertEqual(
            session["body_skeleton"]["_role_output_contract"]["progress_status"]["controller_status_packet_path"],
            session["controller_status_packet_path"],
        )
        status = self.read_json(status_path)
        self.assertEqual(status["status"], "prepared")
        self.assertEqual(status["progress"], 0)
        self.assertTrue(status["progress_written_by_runtime"])
        self.assertFalse(status["controller_may_read_body"])
        self.assertFalse(status["progress_is_decision_evidence"])
        self.assertFalse(status["body_text_persisted_in_status"])

        progress = role_output_runtime.update_output_progress(
            root,
            output_type="pm_resume_recovery_decision",
            role="project_manager",
            agent_id="agent-pm-progress",
            progress=40,
            message="Reviewing current route memory.",
            session_path=session["session_path"],
        )
        self.assertEqual(progress["controller_status_packet_path"], session["controller_status_packet_path"])
        status = self.read_json(status_path)
        self.assertEqual(status["status"], "working")
        self.assertEqual(status["progress"], 40)
        self.assertEqual(status["session_id"], session["session_id"])

        with self.assertRaisesRegex(role_output_runtime.RoleOutputRuntimeError, "sealed body details"):
            role_output_runtime.update_output_progress(
                root,
                output_type="pm_resume_recovery_decision",
                role="project_manager",
                agent_id="agent-pm-progress",
                progress=50,
                message="The sealed body findings are ready.",
                session_path=session["session_path"],
            )

        envelope = role_output_runtime.submit_output(
            root,
            output_type="pm_resume_recovery_decision",
            role="project_manager",
            agent_id="agent-pm-progress",
            session_path=session["session_path"],
            body={
                "decision": "continue_current_packet_loop",
                "explicit_recovery_evidence_recorded": True,
                "prior_path_context_review": {
                    "impact_on_decision": "PM checked current route memory before resuming.",
                },
            },
        )
        self.assertEqual(envelope["controller_status_packet_path"], session["controller_status_packet_path"])
        status = self.read_json(status_path)
        self.assertEqual(status["status"], "submitted")
        self.assertEqual(status["progress"], 999)


if __name__ == "__main__":
    unittest.main()
