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
import role_output_runtime_cli  # noqa: E402
import role_output_runtime_contracts  # noqa: E402
import role_output_runtime_controller_boundary  # noqa: E402
import role_output_runtime_envelopes  # noqa: E402
import role_output_runtime_schema  # noqa: E402


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
        run_root = root / ".flowpilot" / "runs" / "run-test"
        shutil.copytree(ASSETS / "runtime_kit", run_root / "runtime_kit", ignore=shutil.ignore_patterns("__pycache__"))
        _write_json(
            root / ".flowpilot" / "current.json",
            {
                "run_id": "run-test",
                "run_root": ".flowpilot/runs/run-test",
            },
        )
        return root

    def read_json(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def test_role_output_owner_modules_expose_direct_external_contracts(self) -> None:
        root = self.make_project()

        skeleton = role_output_runtime_contracts.build_output_skeleton(
            root,
            output_type="pm_resume_decision",
            role="project_manager",
        )
        args = role_output_runtime_cli.parse_args(
            [
                "--root",
                str(root),
                "prepare-output",
                "--output-type",
                "pm_resume_decision",
                "--role",
                "project_manager",
                "--agent-id",
                "agent-pm",
            ]
        )
        constraints = role_output_runtime_schema.controller_boundary_constraints()
        envelope = role_output_runtime_envelopes.runtime_envelope_for_body(
            root,
            output_type="pm_resume_decision",
            body_path="missing.json",
            body_hash="missing",
        )

        self.assertEqual(skeleton["run_id"], "run-test")
        self.assertEqual(args.command, "prepare-output")
        self.assertEqual(args.output_type, "pm_resume_decision")
        self.assertFalse(constraints["controller_may_read_sealed_bodies"])
        self.assertIsNone(envelope)

    def test_missing_project_contract_registry_is_rejected_without_package_fallback(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="flowpilot-role-output-missing-registry-"))
        try:
            with self.assertRaisesRegex(role_output_runtime_schema.RoleOutputRuntimeError, "output contract registry is missing"):
                role_output_runtime_schema.load_contract_registry(root)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_pm_resume_submit_fills_mechanical_fields_and_returns_direct_router_envelope(self) -> None:
        root = self.make_project()
        envelope = role_output_runtime.submit_output(
            root,
            output_type="pm_resume_decision",
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
            router_directed_submission=True,
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
        receipt = role_output_runtime.validate_envelope_runtime_receipt(root, envelope)
        self.assertEqual(receipt["runtime_entrypoint"], "submit_output_to_router")
        self.assertTrue(receipt["local_receipt_written"])
        self.assertTrue(receipt["router_event_recording_required"])
        self.assertFalse(receipt["router_event_recorded"])

        body = self.read_json(root / envelope["body_ref"]["path"])
        self.assertEqual(body["decision_owner"], "project_manager")
        self.assertEqual(body["controller_reminder"]["controller_may_read_sealed_bodies"], False)
        self.assertEqual(body["prior_path_context_review"]["completed_nodes_considered"], [])
        self.assertTrue(body["contract_self_check"]["all_required_fields_present"])
        ledger = self.read_json(root / ".flowpilot" / "runs" / "run-test" / "role_output_ledger.json")
        self.assertEqual(ledger["outputs"][0]["output_type"], "pm_resume_decision")

    def test_registry_backed_output_types_are_preparable(self) -> None:
        root = self.make_project()
        registry = self.read_json(ASSETS / "runtime_kit" / "contracts" / "contract_index.json")
        for contract in registry["contracts"]:
            if contract.get("runtime_channel") != "role_output_runtime":
                continue
            expected_event = contract.get("router_event") if contract.get("router_event_mode") == "fixed" else None
            output_type = contract["output_type"]
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

    def test_direct_router_submission_authority_accepts_fixed_contract_event(self) -> None:
        root = self.make_project()
        authority = role_output_runtime.validate_direct_router_submission_authority(
            root,
            output_type="pm_resume_decision",
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
                output_type="flowguard_operator_model_report",
                role="flowguard_operator",
                agent_id="agent-product-FlowGuard operator-no-event",
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
                output_type="flowguard_operator_model_report",
                role="flowguard_operator",
                agent_id="agent-product-FlowGuard operator-wrong-event",
                event_name="flowguard_operator_product_scope_model_report",
            )

        _write_json(
            root / ".flowpilot" / "runs" / "run-test" / "state.json",
            {
                "pending_action": {
                    "action_type": "await_role_decision",
                    "to_role": "flowguard_operator",
                    "allowed_external_events": [
                        "flowguard_operator_submits_product_behavior_model",
                        "flowguard_operator_blocks_product_behavior_model",
                    ],
                }
            },
        )
        with self.assertRaisesRegex(role_output_runtime.RoleOutputRuntimeError, "not currently allowed"):
            role_output_runtime.validate_direct_router_submission_authority(
                root,
                output_type="flowguard_operator_model_report",
                role="flowguard_operator",
                agent_id="agent-product-FlowGuard operator-unknown-event",
                event_name="flowguard_operator_product_scope_model_report",
            )
        authority = role_output_runtime.validate_direct_router_submission_authority(
            root,
            output_type="flowguard_operator_model_report",
            role="flowguard_operator",
            agent_id="agent-product-FlowGuard operator-current-wait",
            event_name="flowguard_operator_blocks_product_behavior_model",
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
                    "flowguard_operator_model_report",
                    "--role",
                    "flowguard_operator",
                    "--agent-id",
                    "agent-product-FlowGuard operator-cli",
                    "--body-json",
                    "{}",
                ]
            )

        self.assertFalse((root / ".flowpilot" / "runs" / "run-test" / "role_outputs").exists())

    def test_router_validates_runtime_receipt_when_loading_role_output(self) -> None:
        root = self.make_project()
        envelope = role_output_runtime.submit_output(
            root,
            output_type="pm_resume_decision",
            role="project_manager",
            agent_id="agent-pm-002",
            body={
                "decision": "restore_or_replace_roles_from_memory",
                "explicit_recovery_evidence_recorded": False,
                "prior_path_context_review": {
                    "impact_on_decision": "PM selected role restoration after checking current route memory.",
                },
            },
            router_directed_submission=True,
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
                output_type="pm_resume_decision",
                role="project_manager",
                agent_id="agent-pm-003",
                body={
                    "explicit_recovery_evidence_recorded": True,
                    "prior_path_context_review": {
                        "impact_on_decision": "Missing decision should be rejected before the router sees it.",
                    },
                },
                router_directed_submission=True,
            )

    def test_runtime_rejects_wrong_role_and_role_key_agent_id(self) -> None:
        root = self.make_project()
        with self.assertRaisesRegex(role_output_runtime.RoleOutputRuntimeError, "may be submitted only"):
            role_output_runtime.submit_output(
                root,
                output_type="pm_resume_decision",
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

        body = role_output_runtime_controller_boundary.build_controller_boundary_confirmation_body(
            root,
            action_id="controller-action-1",
            source_action_id="router-action-1",
        )
        self.assertEqual(body["controller_action_id"], "controller-action-1")
        self.assertEqual(body["source_action_id"], "router-action-1")
        self.assertEqual(body["boundary_constraints"], role_output_runtime.controller_boundary_constraints())

        direct_envelope = role_output_runtime_controller_boundary.submit_controller_boundary_confirmation(
            root,
            agent_id="agent-controller-boundary-child",
            submit_output=role_output_runtime_envelopes.submit_output,
            action_id="controller-action-child",
            source_action_id="router-action-child",
            output_path=".flowpilot/runs/run-test/startup/controller_boundary_confirmation_child.json",
        )
        direct_body = self.read_json(root / direct_envelope["body_ref"]["path"])
        self.assertEqual(direct_body["controller_action_id"], "controller-action-child")
        self.assertEqual(direct_body["source_action_id"], "router-action-child")

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
            router_directed_submission=True,
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
            output_type="pm_resume_decision",
            role="project_manager",
            agent_id="agent-pm-progress",
        )

        status_path = root / session["controller_status_packet_path"]
        self.assertTrue(status_path.exists())
        self.assertEqual(
            session["body_skeleton"]["_role_output_contract"]["progress_status"]["controller_status_packet_path"],
            session["controller_status_packet_path"],
        )
        self.assertTrue(
            session["body_skeleton"]["_role_output_contract"]["progress_status"]["controller_aside"][
                "authority_boundary"
            ]["does_not_satisfy_wait"]
        )
        status = self.read_json(status_path)
        self.assertEqual(status["status"], "prepared")
        self.assertEqual(status["progress"], 0)
        self.assertTrue(status["progress_written_by_runtime"])
        self.assertFalse(status["controller_may_read_body"])
        self.assertFalse(status["progress_is_decision_evidence"])
        self.assertFalse(status["body_text_persisted_in_status"])
        self.assertFalse(
            status["controller_process_aside_contract"]["authority_boundary"]["router_semantic_inspection_allowed"]
        )

        progress = role_output_runtime.update_output_progress(
            root,
            output_type="pm_resume_decision",
            role="project_manager",
            agent_id="agent-pm-progress",
            progress=40,
            message="Reviewing current route memory.",
            session_path=session["session_path"],
            controller_aside="I prepared the output skeleton and am checking required fields.",
        )
        self.assertEqual(progress["controller_status_packet_path"], session["controller_status_packet_path"])
        self.assertEqual(
            progress["controller_aside"]["text"],
            "I prepared the output skeleton and am checking required fields.",
        )
        self.assertTrue(progress["controller_aside"]["not_formal_evidence"])
        self.assertTrue(progress["controller_aside"]["does_not_create_router_event"])
        status = self.read_json(status_path)
        self.assertEqual(status["status"], "working")
        self.assertEqual(status["progress"], 40)
        self.assertEqual(status["session_id"], session["session_id"])
        self.assertEqual(
            status["controller_aside"]["text"],
            "I prepared the output skeleton and am checking required fields.",
        )

        with self.assertRaisesRegex(role_output_runtime.RoleOutputRuntimeError, "sealed body details"):
            role_output_runtime.update_output_progress(
                root,
                output_type="pm_resume_decision",
                role="project_manager",
                agent_id="agent-pm-progress",
                progress=50,
                message="The sealed body findings are ready.",
                session_path=session["session_path"],
            )

        envelope = role_output_runtime.submit_output(
            root,
            output_type="pm_resume_decision",
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
            controller_aside="Submitted the formal envelope; waiting for Router.",
            router_directed_submission=True,
        )
        self.assertEqual(envelope["controller_status_packet_path"], session["controller_status_packet_path"])
        self.assertEqual(envelope["controller_aside"]["text"], "Submitted the formal envelope; waiting for Router.")
        self.assertTrue(envelope["controller_aside"]["not_decision_or_approval"])
        status = self.read_json(status_path)
        self.assertEqual(status["status"], "submitted")
        self.assertEqual(status["progress"], 999)
        self.assertEqual(status["controller_aside"]["text"], "Submitted the formal envelope; waiting for Router.")
        self.assertTrue(status["local_receipt_written"])
        self.assertTrue(status["router_event_recording_required"])
        self.assertFalse(status["router_event_recorded"])
        self.assertEqual(status["router_handoff_status"], "pending_router_event")

        with self.assertRaisesRegex(role_output_runtime.RoleOutputRuntimeError, "controller_aside"):
            role_output_runtime.update_output_progress(
                root,
                output_type="pm_resume_decision",
                role="project_manager",
                agent_id="agent-pm-progress",
                progress=60,
                message="Still working.",
                session_path=session["session_path"],
                controller_aside="x" * 241,
            )


if __name__ == "__main__":
    unittest.main()
