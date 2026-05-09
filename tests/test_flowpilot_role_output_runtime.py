from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
sys.path.insert(0, str(ASSETS))

import flowpilot_router as router  # noqa: E402
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

    def test_pm_resume_submit_fills_mechanical_fields_and_returns_envelope_only(self) -> None:
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
        self.assertEqual(envelope["body_ref"]["path"], ".flowpilot/runs/run-test/continuation/pm_resume_runtime_body.json")
        self.assertIn("runtime_receipt_ref", envelope)
        self.assertEqual(envelope["controller_visibility"], "role_output_envelope_only")
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


if __name__ == "__main__":
    unittest.main()
