from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))

import packet_runtime  # noqa: E402


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class FlowPilotOutputContractTests(unittest.TestCase):
    def make_project(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="flowpilot-output-contracts-"))
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

    def test_contract_registry_declares_pm_selection_and_self_check_policy(self) -> None:
        registry_path = ROOT / "skills" / "flowpilot" / "assets" / "runtime_kit" / "contracts" / "contract_index.json"
        registry = self.read_json(registry_path)

        self.assertEqual(registry["schema_version"], "flowpilot.output_contract_registry.v1")
        self.assertTrue(registry["pm_must_select_contract_before_dispatch"])
        self.assertTrue(registry["role_must_self_check_before_return"])
        contract_ids = {item["contract_id"] for item in registry["contracts"]}
        self.assertIn("flowpilot.output_contract.worker_current_node_result.v1", contract_ids)
        self.assertIn("flowpilot.output_contract.material_sufficiency_report.v1", contract_ids)
        self.assertIn("flowpilot.output_contract.terminal_backward_replay_report.v1", contract_ids)
        self.assertIn("flowpilot.output_contract.gate_decision.v1", contract_ids)
        self.assertIn("flowpilot.output_contract.pm_resume_decision.v1", contract_ids)
        self.assertIn("flowpilot.output_contract.pm_parent_segment_decision.v1", contract_ids)
        self.assertIn("flowpilot.output_contract.pm_terminal_closure_decision.v1", contract_ids)
        self.assertIn("flowpilot.output_contract.pm_model_miss_triage_decision.v1", contract_ids)
        self.assertIn("flowpilot.output_contract.flowguard_model_miss_report.v1", contract_ids)
        startup_contract = next(
            item
            for item in registry["contracts"]
            if item["contract_id"] == "flowpilot.output_contract.startup_fact_report.v1"
        )
        self.assertIn(
            "external_fact_review.direct_evidence_paths_checked",
            startup_contract["required_body_fields"],
        )
        gate_contract = next(
            item
            for item in registry["contracts"]
            if item["contract_id"] == "flowpilot.output_contract.gate_decision.v1"
        )
        for field in (
            "gate_decision_version",
            "gate_id",
            "gate_kind",
            "owner_role",
            "risk_type",
            "gate_strength",
            "decision",
            "blocking",
            "required_evidence",
            "evidence_refs",
            "reason",
            "next_action",
            "contract_self_check",
        ):
            self.assertIn(field, gate_contract["required_body_fields"])
        self.assertIn("repair_local", gate_contract["allowed_decision_values"])
        self.assertIn("mutate_route", gate_contract["allowed_decision_values"])
        self.assertIn("semantic_sufficiency_fields_not_router_owned", gate_contract["router_mechanical_validation"])
        resume_contract = next(
            item
            for item in registry["contracts"]
            if item["contract_id"] == "flowpilot.output_contract.pm_resume_decision.v1"
        )
        for field in (
            "decision_owner",
            "decision",
            "explicit_recovery_evidence_recorded",
            "prior_path_context_review.reviewed",
            "prior_path_context_review.source_paths",
            "prior_path_context_review.completed_nodes_considered",
            "prior_path_context_review.superseded_nodes_considered",
            "prior_path_context_review.stale_evidence_considered",
            "prior_path_context_review.prior_blocks_or_experiments_considered",
            "prior_path_context_review.impact_on_decision",
            "prior_path_context_review.controller_summary_used_as_evidence",
            "controller_reminder.controller_only",
            "controller_reminder.controller_may_read_sealed_bodies",
            "controller_reminder.controller_may_infer_from_chat_history",
            "controller_reminder.controller_may_advance_or_close_route",
        ):
            self.assertIn(field, resume_contract["required_body_fields"])
        self.assertIn("continue_current_packet_loop", resume_contract["allowed_decision_values"])
        parent_segment_contract = next(
            item
            for item in registry["contracts"]
            if item["contract_id"] == "flowpilot.output_contract.pm_parent_segment_decision.v1"
        )
        for field in (
            "decision_owner",
            "decision",
            "prior_path_context_review.reviewed",
            "prior_path_context_review.source_paths",
            "prior_path_context_review.completed_nodes_considered",
            "prior_path_context_review.superseded_nodes_considered",
            "prior_path_context_review.stale_evidence_considered",
            "prior_path_context_review.prior_blocks_or_experiments_considered",
            "prior_path_context_review.impact_on_decision",
            "prior_path_context_review.controller_summary_used_as_evidence",
        ):
            self.assertIn(field, parent_segment_contract["required_body_fields"])
        self.assertIn("repair_existing_child", parent_segment_contract["allowed_decision_values"])
        closure_contract = next(
            item
            for item in registry["contracts"]
            if item["contract_id"] == "flowpilot.output_contract.pm_terminal_closure_decision.v1"
        )
        for field in (
            "approved_by_role",
            "decision",
            "prior_path_context_review.reviewed",
            "prior_path_context_review.source_paths",
            "prior_path_context_review.completed_nodes_considered",
            "prior_path_context_review.superseded_nodes_considered",
            "prior_path_context_review.stale_evidence_considered",
            "prior_path_context_review.prior_blocks_or_experiments_considered",
            "prior_path_context_review.impact_on_decision",
            "prior_path_context_review.controller_summary_used_as_evidence",
        ):
            self.assertIn(field, closure_contract["required_body_fields"])
        self.assertIn("approve_terminal_closure", closure_contract["allowed_decision_values"])
        model_miss_contract = next(
            item
            for item in registry["contracts"]
            if item["contract_id"] == "flowpilot.output_contract.pm_model_miss_triage_decision.v1"
        )
        for field in (
            "decided_by_role",
            "decision",
            "defect_or_blocker_id",
            "model_miss_scope",
            "flowguard_capability",
            "same_class_findings_reviewed",
            "repair_recommendation_reviewed",
            "selected_next_action",
            "why_repair_may_start",
            "contract_self_check",
        ):
            self.assertIn(field, model_miss_contract["required_body_fields"])
        self.assertIn("proceed_with_model_backed_repair", model_miss_contract["allowed_decision_values"])
        self.assertIn(
            "model_backed_repair_requires_officer_report_refs",
            model_miss_contract["router_mechanical_validation"],
        )
        officer_model_miss_contract = next(
            item
            for item in registry["contracts"]
            if item["contract_id"] == "flowpilot.output_contract.flowguard_model_miss_report.v1"
        )
        for field in (
            "old_model_miss_reason",
            "bug_class_definition",
            "same_class_findings",
            "candidate_repairs",
            "minimal_sufficient_repair_recommendation",
            "post_repair_model_checks_required",
        ):
            self.assertIn(field, officer_model_miss_contract["required_body_fields"])

    def test_router_delivered_reviewer_cards_include_task_report_contracts(self) -> None:
        startup_card = (
            ROOT
            / "skills"
            / "flowpilot"
            / "assets"
            / "runtime_kit"
            / "cards"
            / "reviewer"
            / "startup_fact_check.md"
        ).read_text(encoding="utf-8")
        material_card = (
            ROOT
            / "skills"
            / "flowpilot"
            / "assets"
            / "runtime_kit"
            / "cards"
            / "reviewer"
            / "material_sufficiency.md"
        ).read_text(encoding="utf-8")

        self.assertIn("## Report Contract For This Task", startup_card)
        self.assertIn("direct_evidence_paths_checked", startup_card)
        self.assertIn("flowpilot.output_contract.startup_fact_report.v1", startup_card)
        self.assertIn("## Report Contract For This Task", material_card)
        self.assertIn("pm_ready", material_card)
        pm_card = (
            ROOT
            / "skills"
            / "flowpilot"
            / "assets"
            / "runtime_kit"
            / "cards"
            / "roles"
            / "project_manager.md"
        ).read_text(encoding="utf-8")
        reviewer_card = (
            ROOT
            / "skills"
            / "flowpilot"
            / "assets"
            / "runtime_kit"
            / "cards"
            / "roles"
            / "human_like_reviewer.md"
        ).read_text(encoding="utf-8")
        self.assertIn("flowpilot.output_contract.gate_decision.v1", pm_card)
        self.assertIn("gate_decision_version", pm_card)
        self.assertIn("role_output_runtime.py", pm_card)
        self.assertIn("flowpilot.output_contract.gate_decision.v1", reviewer_card)
        self.assertIn("semantic reason", reviewer_card)
        self.assertIn("role_output_runtime.py", reviewer_card)
        model_miss_card = (
            ROOT
            / "skills"
            / "flowpilot"
            / "assets"
            / "runtime_kit"
            / "cards"
            / "phases"
            / "pm_model_miss_triage.md"
        ).read_text(encoding="utf-8")
        self.assertIn("flowpilot.output_contract.pm_model_miss_triage_decision.v1", model_miss_card)
        self.assertIn("same_class_findings", model_miss_card)
        self.assertIn("minimal_sufficient_repair_recommendation", model_miss_card)

    def test_pm_packet_repeats_output_contract_in_envelope_body_ledger_and_result(self) -> None:
        root = self.make_project()
        contract = {
            "schema_version": "flowpilot.output_contract.v1",
            "contract_id": "flowpilot.output_contract.worker_current_node_result.v1",
            "selected_by_role": "project_manager",
            "recipient_role": "worker_a",
            "task_family": "worker.current_node",
            "required_result_body_sections": ["Status", "Evidence", "Contract Self-Check"],
            "contract_self_check_required": True,
            "reviewer_must_block_missing_or_failed_check": True,
        }

        envelope = packet_runtime.create_packet(
            root,
            packet_id="packet-001",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="Build the current node slice.",
            output_contract=contract,
        )
        envelope_path = root / ".flowpilot" / "runs" / "run-test" / "packets" / "packet-001" / "packet_envelope.json"
        body_path = envelope_path.with_name("packet_body.md")
        ledger_path = root / ".flowpilot" / "runs" / "run-test" / "packet_ledger.json"

        self.assertEqual(envelope["output_contract_id"], contract["contract_id"])
        self.assertEqual(envelope["output_contract"]["recipient_role"], "worker_a")
        body_text = body_path.read_text(encoding="utf-8")
        self.assertIn("## Output Contract", body_text)
        self.assertIn("## Report Contract For This Task", body_text)
        self.assertIn(contract["contract_id"], body_text)
        self.assertIn("Do not rename fields with synonyms", body_text)
        self.assertIn("Required sealed body sections", body_text)
        self.assertIn("Required return envelope fields", body_text)

        ledger = self.read_json(ledger_path)
        self.assertEqual(ledger["packets"][0]["output_contract_id"], contract["contract_id"])
        self.assertEqual(ledger["packets"][0]["packet_envelope"]["output_contract_id"], contract["contract_id"])

        relayed = packet_runtime.controller_relay_envelope(
            root,
            envelope=envelope,
            envelope_path=envelope_path,
            controller_agent_id="controller",
            received_from_role="project_manager",
            relayed_to_role="worker_a",
        )
        packet_runtime.read_packet_body_for_role(root, relayed, role="worker_a")
        result_body = (
            "finished\n\n"
            "## Contract Self-Check\n\n"
            "- source_output_contract_id: flowpilot.output_contract.worker_current_node_result.v1\n"
            "- self_check_decision: satisfied\n"
        )
        result = packet_runtime.write_result(
            root,
            packet_envelope=relayed,
            completed_by_role="worker_a",
            completed_by_agent_id="worker-a-agent",
            result_body_text=result_body,
            next_recipient="human_like_reviewer",
        )

        self.assertEqual(result["source_output_contract_id"], contract["contract_id"])
        self.assertEqual(result["output_contract"]["contract_id"], contract["contract_id"])
        self.assertTrue(result["contract_self_check"]["completed"])
        self.assertTrue(result["contract_self_check"]["passed"])
        result_path = root / result["result_body_path"]
        self.assertEqual(result["result_body_hash"], hashlib.sha256(result_path.read_bytes()).hexdigest())

    def test_packet_rejects_contract_for_wrong_recipient(self) -> None:
        root = self.make_project()

        with self.assertRaises(packet_runtime.PacketRuntimeError):
            packet_runtime.create_packet(
                root,
                packet_id="packet-001",
                from_role="project_manager",
                to_role="worker_a",
                node_id="node-001",
                body_text="work",
                output_contract={
                    "schema_version": "flowpilot.output_contract.v1",
                    "contract_id": "flowpilot.output_contract.worker_current_node_result.v1",
                    "selected_by_role": "project_manager",
                    "recipient_role": "worker_b",
                },
            )


if __name__ == "__main__":
    unittest.main()
