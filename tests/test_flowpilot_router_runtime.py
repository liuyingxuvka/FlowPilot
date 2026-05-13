from __future__ import annotations

import json
import hashlib
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))

import flowpilot_router as router  # noqa: E402
import card_runtime  # noqa: E402
import packet_runtime  # noqa: E402
import role_output_runtime  # noqa: E402


STARTUP_ANSWERS = {
    "background_agents": "allow",
    "scheduled_continuation": "manual",
    "display_surface": "chat",
    "provenance": "explicit_user_reply",
}

HEARTBEAT_STARTUP_ANSWERS = {
    **STARTUP_ANSWERS,
    "scheduled_continuation": "allow",
}

AI_INTERPRETED_STARTUP_ANSWERS = {
    **STARTUP_ANSWERS,
    "provenance": "ai_interpreted_from_explicit_user_reply",
}

USER_REQUEST = {
    "text": "Use FlowPilot to complete the requested project with PM-owned route control.",
    "provenance": "explicit_user_request",
    "source": "activation_turn",
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class FlowPilotRouterRuntimeTests(unittest.TestCase):
    def make_project(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="flowpilot-router-"))

    def next_and_apply(self, root: Path, payload: dict | None = None) -> dict:
        action = self.next_after_display_sync(root)
        return router.apply_action(root, str(action["action_type"]), self.payload_for_action(action, payload))

    def run_root_for(self, root: Path) -> Path:
        current = read_json(root / ".flowpilot" / "current.json")
        return root / current["current_run_root"]

    def seed_child_completion_ledger(self, root: Path, node_id: str, *, route_id: str = "route-001", route_version: int = 1) -> Path:
        run_root = self.run_root_for(root)
        frontier_path = run_root / "execution_frontier.json"
        frontier = read_json(frontier_path)
        completed = [str(item) for item in (frontier.get("completed_nodes") or [])]
        if node_id not in completed:
            completed.append(node_id)
        ledger_path = run_root / "routes" / route_id / "nodes" / node_id / "node_completion_ledger.json"
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        ledger_path.write_text(
            json.dumps(
                {
                    "schema_version": "flowpilot.node_completion_ledger.v1",
                    "run_id": run_root.name,
                    "route_id": route_id,
                    "route_version": route_version,
                    "node_id": node_id,
                    "completed_by_role": "project_manager",
                    "reviewer_result_passed": True,
                    "completion_source_event": "test_seed_completed_child",
                    "parent_backward_replay_completion": False,
                    "completed_nodes_after_update": completed,
                    "next_node_id": None,
                    "flowpilot_completable_work_closed": True,
                    "human_inspection_notes_belong_in_final_report": True,
                    "source_paths": {},
                    "completed_at": "2026-05-12T00:00:00Z",
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        frontier["completed_nodes"] = completed
        frontier["latest_node_completion_ledger_path"] = self.rel(root, ledger_path)
        frontier_path.write_text(json.dumps(frontier, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return ledger_path

    def control_blocker_path(self, root: Path, blocker: dict) -> Path:
        return root / str(blocker["blocker_artifact_path"])

    def role_report_envelope(self, root: Path, name: str, body: dict) -> dict:
        return self.role_output_envelope(root, name, body, path_key="report_path", hash_key="report_hash")

    def role_decision_envelope(self, root: Path, name: str, body: dict) -> dict:
        return self.role_output_envelope(root, name, body, path_key="decision_path", hash_key="decision_hash")

    def role_output_envelope(self, root: Path, name: str, body: dict, *, path_key: str, hash_key: str) -> dict:
        run_root = self.run_root_for(root)
        safe_name = name.strip("/").replace("\\", "/")
        output_path = run_root / "test_role_outputs" / f"{safe_name}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {
            path_key: self.rel(root, output_path),
            hash_key: hashlib.sha256(output_path.read_bytes()).hexdigest(),
            "controller_visibility": "role_output_envelope_only",
        }

    def write_event_envelope(self, root: Path, name: str, envelope: dict) -> tuple[str, str]:
        run_root = self.run_root_for(root)
        safe_name = name.strip("/").replace("\\", "/")
        envelope_path = run_root / "mailbox" / "outbox" / "events" / f"{safe_name}.envelope.json"
        envelope_path.parent.mkdir(parents=True, exist_ok=True)
        envelope_path.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return self.rel(root, envelope_path), hashlib.sha256(envelope_path.read_bytes()).hexdigest()

    def startup_fact_runtime_envelope(self, root: Path, name: str = "startup/reviewer_startup_fact_report") -> tuple[dict, str, str]:
        run_root = self.run_root_for(root)
        body_path = run_root / "test_role_outputs" / f"{name}.json"
        body_path.parent.mkdir(parents=True, exist_ok=True)
        body_path.write_text(json.dumps(self.startup_fact_report_body(root), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        body_ref = {
            "path": self.rel(root, body_path),
            "hash": hashlib.sha256(body_path.read_bytes()).hexdigest(),
            "path_key": "report_path",
            "hash_key": "report_hash",
        }
        receipt = {
            "schema_version": role_output_runtime.ROLE_OUTPUT_RUNTIME_RECEIPT_SCHEMA,
            "runtime_entrypoint": "submit_output",
            "receipt_id": "test-startup-fact-report-runtime-receipt",
            "run_id": run_root.name,
            "role": "human_like_reviewer",
            "agent_id": "agent-human_like_reviewer",
            "output_type": "startup_fact_report",
            "output_contract_id": "flowpilot.output_contract.startup_fact_report.v1",
            "validation_status": "passed",
            "body_path": body_ref["path"],
            "body_hash": body_ref["hash"],
            "controller_visibility": "receipt_metadata_only",
            "controller_may_read_body": False,
            "semantic_sufficiency_reviewed_by_runtime": False,
        }
        receipt_path = run_root / "role_output_runtime" / "receipts" / "startup_fact_report.receipt.json"
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        envelope = {
            "schema_version": role_output_runtime.ROLE_OUTPUT_ENVELOPE_SCHEMA,
            "router_submission_schema": role_output_runtime.ROLE_OUTPUT_DIRECT_ROUTER_SUBMISSION_SCHEMA,
            "body_ref": body_ref,
            "runtime_receipt_ref": {
                "path": self.rel(root, receipt_path),
                "hash": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
            },
            "controller_visibility": "role_output_envelope_only",
            "chat_response_body_allowed": False,
            "delivery_mode": "direct_to_router",
            "submitted_to": "router",
            "controller_handoff_used": False,
            "controller_receives_role_output": False,
            "controller_next_step_source": "router_status_or_notice",
            "event_name": "reviewer_reports_startup_facts",
            "from_role": "human_like_reviewer",
            "to_role": "router",
            "output_type": "startup_fact_report",
            "output_contract_id": "flowpilot.output_contract.startup_fact_report.v1",
            "role_output_runtime_validated": True,
            "runtime_validates_mechanics_only": True,
            "semantic_sufficiency_reviewed_by_runtime": False,
        }
        envelope_path, envelope_hash = self.write_event_envelope(root, name, envelope)
        return envelope, envelope_path, envelope_hash

    def material_scan_event_envelope(self, root: Path, name: str = "material/pm_material_scan") -> tuple[dict, str, str]:
        payload = self.material_scan_file_backed_payload(root)
        envelope = {
            "schema_version": router.EVENT_ENVELOPE_SCHEMA,
            "event": "pm_issues_material_and_capability_scan_packets",
            "from_role": "project_manager",
            "to_role": "controller",
            "controller_visibility": "event_envelope_only",
            "packets": payload["packets"],
        }
        envelope_path, envelope_hash = self.write_event_envelope(root, name, envelope)
        return envelope, envelope_path, envelope_hash

    def model_miss_officer_report_body(self) -> dict:
        return {
            "reported_by_role": "process_flowguard_officer",
            "old_model_miss_reason": "The old model did not represent reviewer-block repair as a model-miss gate.",
            "bug_class_definition": "reviewer blockers that can be generalized into FlowGuard-detectable same-class failures",
            "same_class_findings": [{"finding_id": "same-class-001", "summary": "repair could start before model-miss triage"}],
            "coverage_added": ["model-miss triage precedes repair decision"],
            "candidate_repairs": [{"repair_id": "repair-001", "summary": "add PM model-miss triage gate"}],
            "minimal_sufficient_repair_recommendation": {
                "repair_id": "repair-001",
                "why_minimal": "It inserts one gate before existing repair flow without changing worker execution.",
            },
            "rejected_larger_repairs": [],
            "rejected_smaller_repairs": [],
            "post_repair_model_checks_required": ["run_defect_governance_checks", "run_flowpilot_repair_transaction_checks"],
            "residual_blindspots": [],
            "contract_self_check": {
                "all_required_fields_present": True,
                "exact_field_names_used": True,
                "empty_required_arrays_explicit": True,
            },
        }

    def model_miss_triage_body(self, root: Path, *, decision: str = "proceed_with_model_backed_repair") -> dict:
        run_root = self.run_root_for(root)
        body = {
            "schema_version": "flowpilot.pm_model_miss_triage_decision.v1",
            "run_id": read_json(router.run_state_path(run_root))["run_id"],
            "decided_by_role": "project_manager",
            "decision": decision,
            "defect_or_blocker_id": "review-block-001",
            "reviewer_block_source_path": self.rel(root, router.run_state_path(run_root)),
            "model_miss_scope": {
                "bug_class_definition": "reviewer blockers that should become same-class FlowGuard checks",
                "representative_current_failure": "reviewer blocked current-node result",
                "same_class_search_boundary": ["router repair path"],
            },
            "flowguard_capability": {
                "can_model_bug_class": decision != "out_of_scope_not_modelable",
                "incapability_reason": "external system behavior cannot be modeled" if decision == "out_of_scope_not_modelable" else None,
            },
            "same_class_findings_reviewed": False,
            "repair_recommendation_reviewed": False,
            "selected_next_action": "not authorized yet",
            "why_repair_may_start": "not authorized yet",
            "blockers": [],
            "contract_self_check": {
                "all_required_fields_present": True,
                "exact_field_names_used": True,
                "empty_required_arrays_explicit": True,
            },
        }
        if decision == "proceed_with_model_backed_repair":
            report = self.role_report_envelope(
                root,
                "flowguard/model_miss_report",
                self.model_miss_officer_report_body(),
            )
            body.update(
                {
                    "officer_report_refs": [
                        {
                            "officer_role": "process_flowguard_officer",
                            "report_path": report["report_path"],
                            "report_hash": report["report_hash"],
                        }
                    ],
                    "same_class_findings_reviewed": True,
                    "repair_recommendation_reviewed": True,
                    "candidate_repairs_considered": [{"repair_id": "repair-001"}],
                    "minimal_sufficient_repair_recommendation": {
                        "repair_id": "repair-001",
                        "why_minimal": "One PM gate is enough to close the modeled gap.",
                    },
                    "post_repair_model_checks_required": [
                        "run_defect_governance_checks",
                        "run_flowpilot_repair_transaction_checks",
                    ],
                    "selected_next_action": "enter pm.review_repair with model-backed recommendation",
                    "why_repair_may_start": "Officer report generalized the class and PM selected a minimal repair path.",
                }
            )
        elif decision == "out_of_scope_not_modelable":
            body.update(
                {
                    "selected_next_action": "enter pm.review_repair by non-model route",
                    "why_repair_may_start": "FlowGuard incapability reason was recorded.",
                }
            )
        return body

    def close_model_miss_triage(
        self,
        root: Path,
        *,
        decision: str = "proceed_with_model_backed_repair",
        output_name: str = "decisions/model_miss_valid",
    ) -> None:
        if not self.flag(root, "pm_model_miss_triage_card_delivered"):
            self.deliver_expected_card(root, "pm.model_miss_triage")
        router.record_external_event(
            root,
            "pm_records_model_miss_triage_decision",
            self.role_decision_envelope(
                root,
                output_name,
                self.model_miss_triage_body(root, decision=decision),
            ),
        )

    def flag(self, root: Path, name: str) -> bool:
        run_root = self.run_root_for(root)
        state = read_json(router.run_state_path(run_root))
        return bool(state["flags"].get(name))

    def material_scan_payload(self) -> dict:
        return {
            "packets": [
                {
                    "packet_id": "material-scan-001",
                    "to_role": "worker_a",
                    "body_text": "Inspect the current request, repository state, and available local materials.",
                }
            ]
        }

    def material_scan_file_backed_payload(self, root: Path) -> dict:
        run_root = self.run_root_for(root)
        body_path = run_root / "test_role_outputs" / "material" / "scan_packet_body.md"
        body_path.parent.mkdir(parents=True, exist_ok=True)
        body_path.write_text(
            "Inspect current request, repository state, and available local materials.",
            encoding="utf-8",
        )
        return {
            "packets": [
                {
                    "packet_id": "material-scan-file-backed-001",
                    "to_role": "worker_a",
                    "body_path": self.rel(root, body_path),
                    "body_hash": hashlib.sha256(body_path.read_bytes()).hexdigest(),
                }
            ]
        }

    def apply_next_packet_action(self, root: Path, expected_action_type: str) -> dict:
        action = self.next_after_display_sync(root)
        if action["action_type"] == "check_packet_ledger":
            router.apply_action(root, "check_packet_ledger")
            action = router.next_action(root)
        self.assertEqual(action["action_type"], expected_action_type)
        return router.apply_action(root, expected_action_type)

    def open_packets_and_write_results(
        self,
        root: Path,
        index_path: Path,
        *,
        result_text: str = "worker result",
        next_recipient: str = "project_manager",
    ) -> None:
        index = read_json(index_path)
        for record in index["packets"]:
            envelope = packet_runtime.load_envelope(root, record["packet_envelope_path"])
            packet_runtime.read_packet_body_for_role(root, envelope, role=envelope["to_role"])
            packet_runtime.write_result(
                root,
                packet_envelope=envelope,
                completed_by_role=envelope["to_role"],
                completed_by_agent_id=f"{envelope['to_role']}-agent",
                result_body_text=result_text,
                next_recipient=next_recipient,
            )

    def open_results_for_pm(self, root: Path, index_path: Path) -> None:
        index = read_json(index_path)
        for record in index["packets"]:
            result = packet_runtime.load_envelope(root, record["result_envelope_path"])
            packet_runtime.read_result_body_for_role(root, result, role="project_manager")

    def open_results_for_reviewer(self, root: Path, index_path: Path) -> None:
        index = read_json(index_path)
        for record in index["packets"]:
            result = packet_runtime.load_envelope(root, record["result_envelope_path"])
            packet_runtime.read_result_body_for_role(root, result, role="human_like_reviewer")

    def absorb_material_scan_results_with_pm(self, root: Path, index_path: Path, *, decision: str = "absorbed") -> None:
        self.apply_next_packet_action(root, "relay_material_scan_results_to_pm")
        self.open_results_for_pm(root, index_path)
        router.record_external_event(
            root,
            "pm_records_material_scan_result_disposition",
            {
                "decided_by_role": "project_manager",
                "decision": decision,
                "decision_reason": "PM absorbed material scan results for formal reviewer gate.",
            },
        )

    def absorb_research_results_with_pm(self, root: Path, index_path: Path, *, decision: str = "absorbed") -> None:
        self.apply_next_packet_action(root, "relay_research_result_to_pm")
        self.open_results_for_pm(root, index_path)
        router.record_external_event(
            root,
            "pm_records_research_result_disposition",
            {
                "decided_by_role": "project_manager",
                "decision": decision,
                "decision_reason": "PM absorbed research results for formal reviewer gate.",
            },
        )

    def absorb_current_node_results_with_pm(self, root: Path, result_paths: list[str | Path], *, decision: str = "absorbed") -> None:
        self.apply_until_action(root, "relay_current_node_result_to_pm")
        for result_path in result_paths:
            packet_runtime.read_result_body_for_role(root, read_json(root / result_path), role="project_manager")
        router.record_external_event(
            root,
            "pm_records_current_node_result_disposition",
            {
                "decided_by_role": "project_manager",
                "decision": decision,
                "decision_reason": "PM absorbed current-node worker result for the formal node-completion gate.",
            },
        )

    def pm_role_work_request_payload(
        self,
        root: Path,
        *,
        request_id: str = "model-miss-followup-001",
        to_role: str = "product_flowguard_officer",
        request_kind: str = "model_miss",
        request_mode: str = "blocking",
        output_contract_id: str = "flowpilot.output_contract.flowguard_model_miss_report.v1",
        body_text: str = "Analyze why the FlowGuard model missed this bug class and recommend a minimal repair.",
    ) -> dict:
        run_root = self.run_root_for(root)
        body_path = run_root / "test_role_outputs" / "pm_role_work" / f"{request_id}.md"
        body_path.parent.mkdir(parents=True, exist_ok=True)
        body_path.write_text(body_text, encoding="utf-8")
        return {
            "requested_by_role": "project_manager",
            "request_id": request_id,
            "to_role": to_role,
            "request_mode": request_mode,
            "request_kind": request_kind,
            "output_contract_id": output_contract_id,
            "packet_body_path": self.rel(root, body_path),
            "packet_body_hash": hashlib.sha256(body_path.read_bytes()).hexdigest(),
        }

    def open_role_work_packet_and_write_result(
        self,
        root: Path,
        *,
        request_id: str = "model-miss-followup-001",
        result_text: str = "Status\n\nComplete\n\nFindings\n\nModel miss analyzed.\n\nContract Self-Check\n\nPassed.",
    ) -> str:
        run_root = self.run_root_for(root)
        index = read_json(run_root / "pm_work_requests" / "index.json")
        record = next(item for item in index["requests"] if item["request_id"] == request_id)
        envelope = packet_runtime.load_envelope(root, record["packet_envelope_path"])
        packet_runtime.read_packet_body_for_role(root, envelope, role=envelope["to_role"])
        result = packet_runtime.write_result(
            root,
            packet_envelope=envelope,
            completed_by_role=envelope["to_role"],
            completed_by_agent_id=f"{envelope['to_role']}-agent",
            result_body_text=result_text,
            next_recipient="project_manager",
        )
        return result["result_body_path"].replace("result_body.md", "result_envelope.json")

    def next_after_display_sync(self, root: Path) -> dict:
        action = router.next_action(root)
        while action["action_type"] == "sync_display_plan":
            router.apply_action(root, "sync_display_plan", self.payload_for_action(action))
            action = router.next_action(root)
        return action

    def assert_payload_contract_mentions(self, contract: dict, *fields: str) -> None:
        encoded = json.dumps(contract, sort_keys=True)
        for field in fields:
            self.assertIn(field, encoded)

    def payload_for_action(self, action: dict, payload: dict | None = None) -> dict:
        payload = dict(payload or {})
        if action.get("requires_user_dialog_display_confirmation"):
            payload["display_confirmation"] = action["payload_template"]["display_confirmation"]
        return payload

    def terminal_summary_payload(self, root: Path, action: dict, run_root: Path, *, note: str = "Run ended.") -> dict:
        summary = (
            f"{router.TERMINAL_SUMMARY_ATTRIBUTION}\n\n"
            "# Final Summary\n\n"
            f"- Status: {action['run_lifecycle_status']}\n"
            f"- Note: {note}\n"
        )
        source_paths = [self.rel(root, router.run_state_path(run_root))]
        lifecycle_path = run_root / "lifecycle" / "run_lifecycle.json"
        if lifecycle_path.exists():
            source_paths.append(self.rel(root, lifecycle_path))
        return {
            "summary_markdown": summary,
            "displayed_to_user": True,
            "displayed_summary_sha256": hashlib.sha256(summary.encode("utf-8")).hexdigest(),
            "read_scope_used": router.TERMINAL_SUMMARY_READ_SCOPE,
            "source_paths_reviewed": source_paths,
        }

    def apply_terminal_summary(self, root: Path, action: dict, run_root: Path, *, note: str = "Run ended.") -> dict:
        result = router.apply_action(root, "write_terminal_summary", self.terminal_summary_payload(root, action, run_root, note=note))
        self.assertEqual(result["applied"], "write_terminal_summary")
        self.assertEqual(result["terminal_summary_path"], self.rel(root, run_root / "final_summary.md"))
        summary = (run_root / "final_summary.md").read_text(encoding="utf-8")
        self.assertTrue(summary.startswith(router.TERMINAL_SUMMARY_ATTRIBUTION))
        summary_record = read_json(run_root / "final_summary.json")
        self.assertEqual(summary_record["schema_version"], router.TERMINAL_SUMMARY_SCHEMA)
        self.assertEqual(summary_record["flowpilot_project_url"], router.FLOWPILOT_PROJECT_URL)
        index = read_json(root / ".flowpilot" / "index.json")
        run_entry = next(item for item in index["runs"] if item["run_id"] == read_json(router.run_state_path(run_root))["run_id"])
        self.assertEqual(run_entry["final_summary_path"], self.rel(root, run_root / "final_summary.md"))
        self.assertEqual(run_entry["flowpilot_project_url"], router.FLOWPILOT_PROJECT_URL)
        return result

    def heartbeat_binding_payload(self, root: Path, automation_id: str = "codex-test-heartbeat") -> dict:
        run_root = self.run_root_for(root)
        run_id = read_json(router.run_state_path(run_root))["run_id"]
        return {
            "route_heartbeat_interval_minutes": 1,
            "host_automation_id": automation_id,
            "host_automation_verified": True,
            "host_automation_proof": {
                "source_kind": "host_receipt",
                "run_id": run_id,
                "host_automation_id": automation_id,
                "route_heartbeat_interval_minutes": 1,
                "heartbeat_bound_to_current_run": True,
            },
        }

    def startup_answer_interpretation(self, raw_text: str = "Use background agents, manual resume, and chat route signs.") -> dict:
        return {
            "schema_version": "flowpilot.startup_answer_interpretation.v1",
            "raw_user_reply_text": raw_text,
            "interpreted_by": "controller",
            "interpretation_provenance": "ai_interpreted_from_explicit_user_reply",
            "ambiguity_status": "none",
            "interpreted_answers": {
                "background_agents": AI_INTERPRETED_STARTUP_ANSWERS["background_agents"],
                "scheduled_continuation": AI_INTERPRETED_STARTUP_ANSWERS["scheduled_continuation"],
                "display_surface": AI_INTERPRETED_STARTUP_ANSWERS["display_surface"],
            },
        }

    def apply_startup_heartbeat_if_requested(self, root: Path) -> dict | None:
        action = self.next_after_display_sync(root)
        if action["action_type"] != "create_heartbeat_automation":
            return None
        return router.apply_action(root, "create_heartbeat_automation", self.heartbeat_binding_payload(root))

    def handle_pending_control_blocker(self, root: Path) -> bool:
        action = self.next_after_display_sync(root)
        if action["action_type"] != "handle_control_blocker":
            return False
        router.apply_action(root, "handle_control_blocker")
        return True

    def deliver_expected_card(self, root: Path, card_id: str) -> dict:
        run_root = self.run_root_for(root)
        card_entry = next((entry for entry in router.SYSTEM_CARD_SEQUENCE if entry["card_id"] == card_id), None)
        if card_entry is not None:
            state = read_json(router.run_state_path(run_root))
            if state.get("flags", {}).get(card_entry["flag"]):
                for delivery in reversed(state.get("delivered_cards", [])):
                    if isinstance(delivery, dict) and delivery.get("card_id") == card_id:
                        return delivery
        action = self.next_after_display_sync(root)
        while action["action_type"] in {
            "confirm_controller_core_boundary",
            "check_prompt_manifest",
            "write_startup_mechanical_audit",
            "write_display_surface_status",
        }:
            router.apply_action(root, str(action["action_type"]), self.payload_for_action(action))
            action = self.next_after_display_sync(root)
        if action["action_type"] == "deliver_system_card_bundle":
            self.assertIn(card_id, action["card_ids"])
            self.ack_system_card_bundle_action(root, action)
            state = read_json(router.run_state_path(self.run_root_for(root)))
            for delivery in reversed(state.get("delivered_cards", [])):
                if isinstance(delivery, dict) and delivery.get("card_id") == card_id:
                    return delivery
            return action
        self.assertEqual(action["action_type"], "deliver_system_card")
        self.assertEqual(action["card_id"], card_id)
        self.ack_system_card_action(root, action)
        return action

    def ack_system_card_action(self, root: Path, action: dict) -> None:
        if action.get("action_type") == "deliver_system_card_bundle":
            self.ack_system_card_bundle_action(root, action)
            return
        role = str(action["to_role"])
        agent_id = action.get("target_agent_id") or action.get("waiting_for_agent_id") or f"{role}-agent"
        open_result = card_runtime.open_card(
            root,
            envelope_path=str(action["card_envelope_path"]),
            role=role,
            agent_id=agent_id,
        )
        card_runtime.submit_card_ack(
            root,
            envelope_path=str(action["card_envelope_path"]),
            role=role,
            agent_id=agent_id,
            receipt_paths=[str(open_result["read_receipt_path"])],
        )
        check_action = self.next_after_display_sync(root)
        if check_action["action_type"] == "check_card_return_event":
            self.assertTrue(check_action["apply_required"])
            router.apply_action(root, "check_card_return_event")
            return
        return_ledger = read_json(self.run_root_for(root) / "return_event_ledger.json")
        self.assertTrue(
            any(
                isinstance(item, dict)
                and item.get("delivery_attempt_id") == action.get("delivery_attempt_id")
                and item.get("status") == "resolved"
                for item in return_ledger.get("pending_returns", [])
            )
        )

    def ack_system_card_bundle_action(self, root: Path, action: dict) -> None:
        role = str(action["to_role"])
        agent_id = action.get("target_agent_id") or action.get("waiting_for_agent_id") or f"{role}-agent"
        open_result = card_runtime.open_card_bundle(
            root,
            envelope_path=str(action["card_bundle_envelope_path"]),
            role=role,
            agent_id=agent_id,
        )
        card_runtime.submit_card_bundle_ack(
            root,
            envelope_path=str(action["card_bundle_envelope_path"]),
            role=role,
            agent_id=agent_id,
            receipt_paths=[str(path) for path in open_result["read_receipt_paths"]],
        )
        check_action = self.next_after_display_sync(root)
        if check_action["action_type"] == "check_card_bundle_return_event":
            self.assertTrue(check_action["apply_required"])
            router.apply_action(root, "check_card_bundle_return_event")
            return
        return_ledger = read_json(self.run_root_for(root) / "return_event_ledger.json")
        self.assertTrue(
            any(
                isinstance(item, dict)
                and item.get("return_kind") == "system_card_bundle"
                and item.get("card_bundle_id") == action.get("card_bundle_id")
                and item.get("status") == "resolved"
                for item in return_ledger.get("pending_returns", [])
            )
        )

    def deliver_user_intake_mail(self, root: Path) -> None:
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "check_packet_ledger")
        self.assertEqual(action["next_mail_id"], "user_intake")
        router.apply_action(root, "check_packet_ledger")
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "deliver_mail")
        self.assertEqual(action["mail_id"], "user_intake")
        router.apply_action(root, "deliver_mail")

    def boot_to_controller(self, root: Path, startup_answers: dict | None = None) -> Path:
        startup_answers = startup_answers or STARTUP_ANSWERS
        while True:
            action = router.next_action(root)
            action_type = str(action["action_type"])
            if action_type == "record_startup_answers":
                router.apply_action(root, action_type, {"startup_answers": startup_answers})
            elif action_type == "record_user_request":
                router.apply_action(root, action_type, {"user_request": USER_REQUEST})
            elif action_type == "start_role_slots":
                router.apply_action(root, action_type, self.role_agent_payload(root, startup_answers))
            else:
                router.apply_action(root, action_type, self.payload_for_action(action))
            if action_type == "load_controller_core":
                break
        current = read_json(root / ".flowpilot" / "current.json")
        return root / current["current_run_root"]

    def role_agent_payload(self, root: Path, startup_answers: dict | None = None) -> dict:
        startup_answers = startup_answers or STARTUP_ANSWERS
        if startup_answers.get("background_agents") == "single-agent":
            return {}
        bootstrap = self.bootstrap_state(root)
        run_id = bootstrap["run_id"]
        return {
            "background_agents_capability_status": "available",
            "role_agents": [
                {
                    "role_key": role,
                    "agent_id": f"agent-{run_id}-{role}",
                    "model_policy": "strongest_available",
                    "reasoning_effort_policy": "highest_available",
                    "spawn_result": "spawned_fresh_for_task",
                    "spawned_for_run_id": run_id,
                    "spawned_after_startup_answers": True,
                }
                for role in router.CREW_ROLE_KEYS
            ],
        }

    def resume_role_agent_payload(self, root: Path, action: dict | None = None) -> dict:
        action = action or self.next_after_display_sync(root)
        records = []
        batch_id = action["liveness_probe_batch_id"]
        for request in action["role_rehydration_request"]:
            role = request["role_key"]
            record = {
                "role_key": role,
                "agent_id": f"live-agent-{request['rehydrated_after_resume_tick_id']}-{role}",
                "model_policy": "strongest_available",
                "reasoning_effort_policy": "highest_available",
                "rehydration_result": "live_agent_continuity_confirmed",
                "host_liveness_status": "active",
                "liveness_decision": "confirmed_existing_agent",
                "resume_agent_attempted": True,
                "bounded_wait_result": "completed",
                "bounded_wait_ms": 1000,
                "liveness_probe_batch_id": batch_id,
                "liveness_probe_mode": "concurrent_batch",
                "liveness_probe_started_at": "2026-05-11T00:00:00Z",
                "liveness_probe_completed_at": "2026-05-11T00:00:01Z",
                "wait_agent_timeout_treated_as_active": False,
                "rehydrated_for_run_id": request["rehydrated_for_run_id"],
                "rehydrated_after_resume_tick_id": request["rehydrated_after_resume_tick_id"],
                "rehydrated_after_resume_state_loaded": True,
                "spawned_after_resume_state_loaded": False,
                "core_prompt_path": request["core_prompt_path"],
                "core_prompt_hash": request["core_prompt_hash"],
            }
            if request["role_memory_status"] == "available":
                record.update(
                    {
                        "memory_packet_path": request["memory_packet_path"],
                        "memory_packet_hash": request["memory_packet_hash"],
                        "memory_seeded_from_current_run": True,
                    }
                )
            else:
                record.update(
                    {
                        "memory_missing_acknowledged": True,
                        "replacement_seeded_from_common_run_context": True,
                    }
                )
            if role == "project_manager":
                record["pm_resume_context_delivered"] = True
            records.append(record)
        return {
            "background_agents_capability_status": "available",
            "liveness_probe_batch_id": batch_id,
            "liveness_probe_mode": "concurrent_batch",
            "all_liveness_probes_started_before_wait": True,
            "rehydrated_role_agents": records,
        }

    def role_recovery_agent_payload(self, root: Path, action: dict, *, role: str = "worker_a") -> dict:
        request = next(item for item in action["role_recovery_request"] if item["role_key"] == role)
        transaction = action["role_recovery_transaction"]
        return {
            "background_agents_capability_status": "available",
            "recovery_transaction_id": transaction["transaction_id"],
            "trigger_source": transaction["trigger_source"],
            "recovery_scope": transaction["recovery_scope"],
            "target_role_keys": transaction["target_role_keys"],
            "recovered_role_agents": [
                {
                    "role_key": role,
                    "old_agent_id": request["old_agent_id"],
                    "agent_id": f"recovered-{transaction['transaction_id']}-{role}",
                    "model_policy": "strongest_available",
                    "reasoning_effort_policy": "highest_available",
                    "recovery_result": "targeted_replacement_spawned",
                    "restore_attempted": True,
                    "restore_result": "failed",
                    "targeted_replacement_attempted": True,
                    "targeted_replacement_result": "success",
                    "slot_reconciliation_attempted": False,
                    "full_crew_recycle_attempted": False,
                    "rehydrated_for_run_id": transaction["run_id"],
                    "memory_context_injected": True,
                    "packet_ownership_reconciled": True,
                    "role_binding_epoch_advanced": True,
                    "superseded_agent_output_quarantined": True,
                    "memory_packet_path": request["memory_packet_path"],
                    "memory_packet_hash": request["memory_packet_hash"],
                    "memory_seeded_from_current_run": True,
                }
            ],
        }

    def bootstrap_state(self, root: Path) -> dict:
        return read_json(router.bootstrap_state_path(root))

    def deliver_startup_fact_check_card(self, root: Path) -> dict:
        self.apply_startup_heartbeat_if_requested(root)
        return self.deliver_expected_card(root, "reviewer.startup_fact_check")

    def deliver_initial_pm_cards_and_user_intake(self, root: Path) -> None:
        self.deliver_expected_card(root, "pm.core")
        self.deliver_expected_card(root, "pm.output_contract_catalog")
        self.deliver_expected_card(root, "pm.role_work_request")
        self.deliver_expected_card(root, "pm.phase_map")
        self.deliver_expected_card(root, "pm.startup_intake")
        self.deliver_user_intake_mail(root)

    def complete_startup_activation(self, root: Path) -> None:
        run_root = self.run_root_for(root)
        self.deliver_startup_fact_check_card(root)
        self.deliver_initial_pm_cards_and_user_intake(root)
        router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(
                root,
                "startup/reviewer_startup_fact_report",
                self.startup_fact_report_body(root),
            ),
        )
        self.deliver_expected_card(root, "pm.startup_activation")
        router.record_external_event(
            root,
            "pm_approves_startup_activation",
            self.role_decision_envelope(
                root,
                "startup/pm_startup_activation",
                {"approved_by_role": "project_manager", "decision": "approved"},
            ),
        )
        self.assertTrue((run_root / "display" / "display_surface.json").exists())

    def complete_material_flow(self, root: Path, material_understanding_payload: dict | None = None) -> None:
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        self.deliver_expected_card(root, "pm.material_scan")

        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        self.apply_next_packet_action(root, "relay_material_scan_packets")
        run_root = self.run_root_for(root)
        material_index_path = run_root / "material" / "material_scan_packets.json"
        self.open_packets_and_write_results(root, material_index_path, result_text="material scan result")
        router.record_external_event(root, "worker_scan_packet_bodies_delivered_after_dispatch")
        router.record_external_event(root, "worker_scan_results_returned")
        self.absorb_material_scan_results_with_pm(root, material_index_path)

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        self.deliver_expected_card(root, "reviewer.material_sufficiency")

        router.record_external_event(
            root,
            "reviewer_reports_material_sufficient",
            self.role_report_envelope(
                root,
                "material/reviewer_material_sufficiency",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "direct_material_sources_checked": True,
                    "packet_matches_checked_sources": True,
                    "pm_ready": True,
                },
            ),
        )
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        self.deliver_expected_card(root, "pm.event.reviewer_report")

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        self.deliver_expected_card(root, "pm.material_absorb_or_research")

        router.record_external_event(root, "pm_accepts_reviewed_material")
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        self.deliver_expected_card(root, "pm.material_understanding")
        router.record_external_event(
            root,
            "pm_writes_material_understanding",
            material_understanding_payload or {"material_summary": "reviewed material accepted"},
        )

    def complete_root_contract_before_child_skill_gates(self, root: Path) -> None:
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.product_architecture")
        self.ack_system_card_action(root, action)
        router.record_external_event(
            root,
            "pm_writes_product_function_architecture",
            {
                "user_task_map": [{"task_id": "task-001", "goal": "complete the requested project"}],
                "product_capability_map": [{"capability_id": "cap-001", "behavior": "complete requested work"}],
                "feature_decisions": [{"feature_id": "feature-001", "decision": "must"}],
                "highest_achievable_product_target": {"product_vision": "professional completion"},
                "semantic_fidelity_policy": {"silent_downgrade_forbidden": True},
                "functional_acceptance_matrix": [{"acceptance_id": "root-001"}],
            },
        )

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "product_officer.product_architecture_modelability")
        self.ack_system_card_action(root, action)
        router.record_external_event(
            root,
            "product_officer_submits_product_behavior_model",
            self.role_report_envelope(
                root,
                "flowguard/product_behavior_model",
                {"reviewed_by_role": "product_flowguard_officer", "passed": True},
            ),
        )

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.product_behavior_model_decision")
        self.ack_system_card_action(root, action)
        router.record_external_event(root, "pm_accepts_product_behavior_model", self.product_behavior_model_decision_body())

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "reviewer.product_architecture_challenge")
        self.ack_system_card_action(root, action)
        router.record_external_event(
            root,
            "reviewer_passes_product_architecture",
            self.role_report_envelope(
                root,
                "reviews/product_architecture_challenge",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.root_contract")
        self.ack_system_card_action(root, action)
        router.record_external_event(
            root,
            "pm_writes_root_acceptance_contract",
            {
                "root_requirements": [
                    {
                        "requirement_id": "root-001",
                        "priority": "must",
                        "proof_required": "mixed",
                    }
                ],
                "proof_matrix": [{"requirement_id": "root-001", "expected_final_replay": True}],
                "selected_scenario_ids": ["terminal_complete_state"],
            },
        )

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "reviewer.root_contract_challenge")
        self.ack_system_card_action(root, action)
        router.record_external_event(
            root,
            "reviewer_passes_root_acceptance_contract",
            self.role_report_envelope(
                root,
                "reviews/root_contract_challenge",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "product_officer.root_contract_modelability")
        self.ack_system_card_action(root, action)
        router.record_external_event(
            root,
            "product_officer_passes_root_acceptance_contract_modelability",
            self.role_report_envelope(
                root,
                "flowguard/root_contract_modelability",
                {"reviewed_by_role": "product_flowguard_officer", "passed": True},
            ),
        )
        router.record_external_event(root, "pm_freezes_root_acceptance_contract")

    def complete_product_architecture_and_contract(self, root: Path) -> None:
        self.complete_root_contract_before_child_skill_gates(root)
        self.complete_child_skill_gates(root)

        self.deliver_expected_card(root, "pm.prior_path_context")
        self.deliver_expected_card(root, "pm.route_skeleton")
        router.record_external_event(
            root,
            "pm_writes_route_draft",
            {
                "nodes": [{"node_id": "node-001"}],
                **self.prior_path_context_review(root, "Initial route draft considered the empty current-run route history."),
            },
        )
        self.complete_route_checks(root)

    def complete_child_skill_gates(self, root: Path) -> None:
        selected_skills = [
            {
                "skill_name": "model-first-function-flow",
                "decision": "required",
                "supported_capabilities": ["cap-001"],
                "references_loaded_now": [],
                "references_deferred_with_reason": [],
                "gates": [
                    {
                        "gate_id": "process-model",
                        "required_approver": "process_flowguard_officer",
                        "evidence_required": ["model-check-result"],
                        "controller_can_approve": False,
                    }
                ],
            }
        ]

        if not self.flag(root, "pm_dependency_policy_card_delivered"):
            self.deliver_expected_card(root, "pm.dependency_policy")
        router.record_external_event(
            root,
            "pm_records_dependency_policy",
            {
                "allowed_dependency_actions": ["use_existing_local_skill"],
                "host_level_install_requested": False,
            },
        )
        router.record_external_event(
            root,
            "pm_writes_capabilities_manifest",
            {
                "capabilities": [{"capability_id": "cap-001", "behavior": "model and gate route work"}],
                "capability_to_skill_needs": [{"capability_id": "cap-001", "candidate_skill": "model-first-function-flow"}],
            },
        )

        self.deliver_expected_card(root, "pm.child_skill_selection")
        router.record_external_event(root, "pm_writes_child_skill_selection", {"selected_skills": selected_skills})

        self.deliver_expected_card(root, "pm.child_skill_gate_manifest")
        router.record_external_event(root, "pm_writes_child_skill_gate_manifest", {"selected_skills": selected_skills})

        self.deliver_expected_card(root, "reviewer.child_skill_gate_manifest_review")
        router.record_external_event(
            root,
            "reviewer_passes_child_skill_gate_manifest",
            self.role_report_envelope(
                root,
                "reviews/child_skill_gate_manifest_review",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )

        self.deliver_expected_card(root, "process_officer.child_skill_conformance_model")
        router.record_external_event(
            root,
            "process_officer_passes_child_skill_conformance_model",
            self.role_report_envelope(
                root,
                "flowguard/child_skill_conformance_model",
                {"reviewed_by_role": "process_flowguard_officer", "passed": True},
            ),
        )

        self.deliver_expected_card(root, "product_officer.child_skill_product_fit")
        router.record_external_event(
            root,
            "product_officer_passes_child_skill_product_fit",
            self.role_report_envelope(
                root,
                "flowguard/child_skill_product_fit",
                {"reviewed_by_role": "product_flowguard_officer", "passed": True},
            ),
        )
        router.record_external_event(root, "pm_approves_child_skill_manifest_for_route")
        router.record_external_event(root, "capability_evidence_synced")

    def complete_pre_route_gates(self, root: Path) -> None:
        self.complete_startup_activation(root)
        self.complete_material_flow(root)
        self.complete_product_architecture_and_contract(root)

    def test_controller_route_memory_is_refreshed_and_required_for_pm_route_draft(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        history_path = run_root / "route_memory" / "route_history_index.json"
        context_path = run_root / "route_memory" / "pm_prior_path_context.json"
        self.assertTrue(history_path.exists())
        self.assertTrue(context_path.exists())
        history = read_json(history_path)
        context = read_json(context_path)
        self.assertEqual(history["schema_version"], "flowpilot.route_history_index.v1")
        self.assertEqual(context["schema_version"], "flowpilot.pm_prior_path_context.v1")
        self.assertEqual(history["generated_by"], "controller")
        self.assertFalse(history["sealed_packet_or_result_bodies_read"])
        self.assertFalse(context["controller_decision_authority"])

        self.complete_startup_activation(root)
        self.complete_material_flow(root)
        self.complete_root_contract_before_child_skill_gates(root)
        self.complete_child_skill_gates(root)

        action = self.deliver_expected_card(root, "pm.prior_path_context")
        self.assertTrue(action["pm_prior_path_context_required_for_decision"])
        self.assertEqual(
            action["pm_context_paths"]["pm_prior_path_context"],
            self.rel(root, context_path),
        )

        self.deliver_expected_card(root, "pm.route_skeleton")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_route_draft", {"nodes": [{"node_id": "node-001"}]})

        router.record_external_event(
            root,
            "pm_writes_route_draft",
            {
                "nodes": [{"node_id": "node-001"}],
                **self.prior_path_context_review(root, "Route draft used current Controller route-memory indexes."),
            },
        )
        draft = read_json(run_root / "routes" / "route-001" / "flow.draft.json")
        self.assertEqual(draft["prior_path_context_review"]["source_paths"][0], self.rel(root, context_path))

    def test_pm_route_draft_preserves_role_authored_repair_policy_fields(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.complete_material_flow(root)
        self.complete_root_contract_before_child_skill_gates(root)
        self.complete_child_skill_gates(root)

        self.deliver_expected_card(root, "pm.prior_path_context")
        self.deliver_expected_card(root, "pm.route_skeleton")

        nodes = [{"node_id": "node-001"}]
        repair_policy = {
            "policy_id": "route-001-repair-return-policy-test",
            "branch_table": [
                {
                    "trigger": "reviewer_block",
                    "rejoin_target": "node-001",
                    "rerun_checks": ["process_officer_route_process_check"],
                }
            ],
        }
        router.record_external_event(
            root,
            "pm_writes_route_draft",
            {
                "schema_version": "flowpilot.pm_route_draft_payload.v1",
                "route_id": "route-001",
                "route_version": 4,
                "nodes": nodes,
                "route": {
                    "route_id": "route-001",
                    "route_version": 4,
                    "nodes": nodes,
                    "repair_return_policy": repair_policy,
                },
                "route_repair_return_policy": repair_policy,
                **self.prior_path_context_review(
                    root,
                    "Route draft preserves PM-authored repair-return policy fields.",
                ),
            },
        )

        draft = read_json(run_root / "routes" / "route-001" / "flow.draft.json")
        self.assertEqual(draft["schema_version"], "flowpilot.route_draft.v1")
        self.assertEqual(draft["pm_authored_payload_schema_version"], "flowpilot.pm_route_draft_payload.v1")
        self.assertEqual(draft["route_repair_return_policy"], repair_policy)
        self.assertEqual(draft["route"]["repair_return_policy"], repair_policy)
        self.assertFalse(draft["router_preservation"]["whitelist_rebuild_used"])
        self.assertTrue(draft["router_preservation"]["role_authored_fields_preserved"])

    def test_controller_next_action_reuses_fresh_route_memory(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        history_path = run_root / "route_memory" / "route_history_index.json"
        context_path = run_root / "route_memory" / "pm_prior_path_context.json"
        history_before = read_json(history_path)
        context_before = read_json(context_path)

        action = router.next_action(root)

        self.assertEqual(action["action_type"], "sync_display_plan")
        self.assertEqual(read_json(history_path), history_before)
        self.assertEqual(read_json(context_path), context_before)

    def activate_route(self, root: Path, node_id: str = "node-001") -> None:
        router.record_external_event(
            root,
            "pm_activates_reviewed_route",
            {"route_id": "route-001", "active_node_id": node_id, "route_version": 1},
        )

    def complete_route_checks(self, root: Path) -> None:
        self.deliver_expected_card(root, "process_officer.route_process_check")
        router.record_external_event(
            root,
            "process_officer_submits_process_route_model",
            self.role_report_envelope(
                root,
                "flowguard/process_route_model",
                self.route_process_pass_body(),
            ),
        )
        self.deliver_expected_card(root, "pm.process_route_model_decision")
        router.record_external_event(root, "pm_accepts_process_route_model", self.process_route_model_decision_body())
        self.deliver_expected_card(root, "product_officer.route_product_check")
        router.record_external_event(
            root,
            "product_officer_passes_route_check",
            self.role_report_envelope(
                root,
                "flowguard/route_product_check",
                self.route_product_pass_body(),
            ),
        )
        self.deliver_expected_card(root, "reviewer.route_challenge")
        router.record_external_event(
            root,
            "reviewer_passes_route_check",
            self.role_report_envelope(
                root,
                "reviews/route_challenge",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )

    def route_process_pass_body(self) -> dict:
        return {
            "reviewed_by_role": "process_flowguard_officer",
            "passed": True,
            "process_viability_verdict": "pass",
            "product_behavior_model_checked": True,
            "route_can_reach_product_model": True,
            "repair_return_policy_checked": True,
            "serial_execution_model_checked": True,
            "all_effective_nodes_reachable_in_order": True,
            "recursive_child_routes_serialized": True,
        }

    def route_product_pass_body(self) -> dict:
        return {
            "reviewed_by_role": "product_flowguard_officer",
            "passed": True,
            "route_model_review_verdict": "pass",
            "product_behavior_model_checked": True,
            "route_maps_to_product_behavior_model": True,
        }

    def product_behavior_model_decision_body(self) -> dict:
        return {
            "decided_by_role": "project_manager",
            "decision": "accept_product_behavior_model",
            "source_paths": [
                "product_function_architecture.json",
                "flowguard/product_behavior_model.json",
            ],
            "pm_model_fit_review": "PM accepted the Product FlowGuard model as the product basis.",
            "product_goal_coverage": "The model covers the requested product goal.",
            "unmodeled_or_ambiguous_behavior": [],
            "next_action": "reviewer_product_architecture_challenge",
        }

    def process_route_model_decision_body(self) -> dict:
        return {
            "decided_by_role": "project_manager",
            "decision": "accept_process_route_model",
            "source_paths": [
                "routes/route-001/flow.draft.json",
                "flowguard/process_route_model.json",
            ],
            "serial_execution_line_review": "PM accepted the route as one ordered execution line.",
            "recursive_node_entry_review": "Non-leaf local loops are represented before child execution.",
            "leaf_worker_readiness_review": "Leaves are worker-ready or promoted before dispatch.",
            "parent_and_final_backward_review_policy": "Parent and final backward reviews are required.",
            "model_miss_repair_policy": "Model misses require model update, same-class search, supplemental nodes, and stale gate reruns.",
            "next_action": "product_officer_route_product_check",
        }

    def write_current_node_acceptance_plan(
        self,
        root: Path,
        *,
        active_child_skill_bindings: list[dict] | None = None,
        leaf_readiness_gate: dict | None = None,
    ) -> None:
        self.deliver_expected_card(root, "pm.current_node_loop")
        self.deliver_expected_card(root, "pm.event.node_started")
        self.deliver_expected_card(root, "pm.node_acceptance_plan")
        payload = {
            **self.prior_path_context_review(root, "Node acceptance plan considered route memory and active frontier."),
            "high_standard_recheck": {
                "ideal_outcome": "complete the current node at the highest practical standard",
                "unacceptable_outcomes": ["partial work", "unverified closure", "controller downgrade"],
                "higher_standard_opportunities": ["tighten acceptance evidence before dispatch"],
                "semantic_downgrade_risks": ["treating packet existence as product acceptance"],
                "decision": "proceed",
                "why_current_plan_meets_highest_reasonable_standard": "PM listed node requirements, proof, and direct review gates before work dispatch.",
            },
            "node_requirements": [
                {
                    "requirement_id": "node-001-req",
                    "acceptance_statement": "current node work is complete",
                    "proof_required": "mixed",
                }
            ],
            "experiment_plan": [],
        }
        if active_child_skill_bindings is not None:
            payload["active_child_skill_bindings"] = active_child_skill_bindings
        if leaf_readiness_gate is not None:
            payload["leaf_readiness_gate"] = leaf_readiness_gate
        router.record_external_event(
            root,
            "pm_writes_node_acceptance_plan",
            payload,
        )

    def deliver_current_node_cards(
        self,
        root: Path,
        *,
        active_child_skill_bindings: list[dict] | None = None,
        leaf_readiness_gate: dict | None = None,
    ) -> None:
        self.write_current_node_acceptance_plan(
            root,
            active_child_skill_bindings=active_child_skill_bindings,
            leaf_readiness_gate=leaf_readiness_gate,
        )
        self.deliver_expected_card(root, "reviewer.node_acceptance_plan_review")
        router.record_external_event(
            root,
            "reviewer_passes_node_acceptance_plan",
            self.role_report_envelope(
                root,
                "reviews/node_acceptance_plan_review",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )

    def complete_parent_backward_replay_if_due(self, root: Path) -> None:
        action = router.next_action(root)
        if action["action_type"] == "check_prompt_manifest" and action.get("next_card_id") == "pm.parent_backward_targets":
            router.apply_action(root, "check_prompt_manifest")
            action = router.next_action(root)
        if action.get("card_id") != "pm.parent_backward_targets":
            return
        self.ack_system_card_action(root, action)
        router.record_external_event(root, "pm_builds_parent_backward_targets")
        self.deliver_expected_card(root, "reviewer.parent_backward_replay")
        router.record_external_event(
            root,
            "reviewer_passes_parent_backward_replay",
            self.role_report_envelope(
                root,
                "reviews/parent_backward_replay",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )
        card_action = self.deliver_expected_card(root, "pm.parent_segment_decision")
        self.assert_payload_contract_mentions(
            card_action["payload_contract"],
            "pm_parent_segment_decision_role_output",
            "decision_owner",
            "prior_path_context_review.source_paths",
            "pm_prior_path_context.json",
            "route_history_index.json",
        )
        wait_action = router.next_action(root)
        self.assertEqual(wait_action["action_type"], "await_role_decision")
        self.assertIn("pm_records_parent_segment_decision", wait_action["allowed_external_events"])
        self.assertNotIn(router.PM_ROLE_WORK_REQUEST_EVENT, wait_action["allowed_external_events"])
        self.assertFalse(wait_action["pm_role_work_request_channel_available"])
        self.assertIn("record_parent_segment_decision", wait_action["legal_next_actions"]["legal_action_ids"])
        if "payload_contract" in wait_action:
            self.assert_payload_contract_mentions(
                wait_action["payload_contract"],
                "pm_parent_segment_decision_role_output",
                "repair_existing_child",
                "prior_path_context_review.controller_summary_used_as_evidence",
            )
        router.record_external_event(
            root,
            "pm_records_parent_segment_decision",
            self.role_decision_envelope(
                root,
                "decisions/parent_segment_decision",
                {
                    "decision_owner": "project_manager",
                    "decision": "continue",
                    **self.prior_path_context_review(root, "Parent segment decision considered current route memory."),
                },
            ),
        )

    def complete_evidence_quality_package(self, root: Path) -> None:
        run_root = self.run_root_for(root)
        self.deliver_expected_card(root, "pm.evidence_quality_package")
        router.record_external_event(
            root,
            "pm_records_evidence_quality_package",
            {
                **self.prior_path_context_review(root, "Evidence quality package considered current route memory."),
                "evidence_items": [
                    {
                        "evidence_id": "current-node-reviewed-result",
                        "path": ".flowpilot/current-node-result",
                        "status": "current",
                    }
                ],
                "generated_resources": [],
                "ui_visual_evidence_required": False,
            },
        )
        self.assertTrue((run_root / "evidence" / "evidence_ledger.json").exists())
        self.assertTrue((run_root / "generated_resource_ledger.json").exists())
        self.assertTrue((run_root / "quality" / "quality_package.json").exists())
        self.deliver_expected_card(root, "reviewer.evidence_quality_review")
        router.record_external_event(
            root,
            "reviewer_passes_evidence_quality_package",
            self.role_report_envelope(
                root,
                "reviews/evidence_quality_review",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )

    def complete_final_ledger_and_terminal_replay(self, root: Path) -> None:
        run_root = self.run_root_for(root)
        self.deliver_expected_card(root, "pm.final_ledger")
        router.record_external_event(root, "pm_records_final_route_wide_ledger_clean", self.final_ledger_payload(root))
        final_ledger_path = run_root / "final_route_wide_gate_ledger.json"
        terminal_map_path = run_root / "terminal_human_backward_replay_map.json"
        self.assertTrue(final_ledger_path.exists())
        self.assertTrue(terminal_map_path.exists())
        ledger = read_json(final_ledger_path)
        self.assertEqual(ledger["status"], "clean")
        self.assertFalse(ledger["completion_allowed"])

        self.deliver_expected_card(root, "reviewer.final_backward_replay")
        router.record_external_event(
            root,
            "reviewer_final_backward_replay_passed",
            self.role_report_envelope(
                root,
                "reviews/terminal_backward_replay",
                self.terminal_replay_payload(root),
            ),
        )
        terminal_map = read_json(terminal_map_path)
        ledger = read_json(final_ledger_path)
        self.assertEqual(terminal_map["status"], "passed")
        self.assertTrue(ledger["completion_allowed"])
        projection_path = run_root / "completion" / "task_completion_projection.json"
        self.assertTrue(projection_path.exists())
        projection = read_json(projection_path)
        self.assertEqual(projection["task_status"], "ready_for_pm_terminal_closure")
        self.assertTrue(projection["ui_or_chat_is_display_only"])

    def rel(self, root: Path, path: Path) -> str:
        return str(path.relative_to(root)).replace("\\", "/")

    def startup_fact_report_body(self, root: Path) -> dict:
        run_root = self.run_root_for(root)
        return {
            "reviewed_by_role": "human_like_reviewer",
            "passed": True,
            "external_fact_review": {
                "reviewed_by_role": "human_like_reviewer",
                "self_attested_ai_claims_accepted_as_proof": False,
                "reviewer_checked_requirement_ids": [
                    "live_agent_spawn_freshness",
                    "heartbeat_host_automation_current_run_binding",
                    "cockpit_or_display_fallback_reality",
                ],
                "direct_evidence_paths_checked": [
                    self.rel(root, run_root / "startup_answers.json"),
                    self.rel(root, run_root / "crew_ledger.json"),
                    self.rel(root, run_root / "continuation" / "continuation_binding.json"),
                ],
            },
        }

    def prior_path_context_review(self, root: Path, impact: str = "PM considered current route memory before deciding") -> dict:
        run_root = self.run_root_for(root)
        return {
            "prior_path_context_review": {
                "reviewed": True,
                "source_paths": [
                    self.rel(root, run_root / "route_memory" / "pm_prior_path_context.json"),
                    self.rel(root, run_root / "route_memory" / "route_history_index.json"),
                ],
                "completed_nodes_considered": [],
                "superseded_nodes_considered": [],
                "stale_evidence_considered": [],
                "prior_blocks_or_experiments_considered": [],
                "impact_on_decision": impact,
                "controller_summary_used_as_evidence": False,
            }
        }

    def pm_control_blocker_decision_body(
        self,
        blocker_id: str,
        decision: str = "repair_not_required",
        rerun_target: str = "current_node_reviewer_passes_result",
    ) -> dict:
        return {
            "decided_by_role": "project_manager",
            "blocker_id": blocker_id,
            "decision": decision,
            "prior_path_context_review": {
                "reviewed": True,
                "source_paths": [],
            },
            "repair_action": "PM reviewed the delivered control blocker and recorded the recovery decision.",
            "rerun_target": rerun_target,
            "repair_transaction": {
                "plan_kind": "event_replay",
            },
            "blockers": [],
            "contract_self_check": {
                "all_required_fields_present": True,
                "exact_field_names_used": True,
                "empty_required_arrays_explicit": True,
            },
        }

    def gate_decision_body(
        self,
        root: Path,
        *,
        gate_id: str = "quality-gate-001",
        owner_role: str = "human_like_reviewer",
        gate_kind: str = "quality",
        risk_type: str = "visual_quality",
        gate_strength: str = "hard",
        decision: str = "pass",
        blocking: bool = False,
        next_action: str = "continue",
    ) -> dict:
        run_root = self.run_root_for(root)
        evidence_path = run_root / "test_evidence" / f"{gate_id}.json"
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(
            json.dumps({"gate_id": gate_id, "checked": True}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return {
            "gate_decision_version": "flowpilot.gate_decision.v1",
            "gate_id": gate_id,
            "gate_kind": gate_kind,
            "owner_role": owner_role,
            "risk_type": risk_type,
            "gate_strength": gate_strength,
            "decision": decision,
            "blocking": blocking,
            "required_evidence": ["reviewer-owned walkthrough evidence"],
            "evidence_refs": [
                {
                    "kind": "reviewer_walkthrough",
                    "path": self.rel(root, evidence_path),
                    "hash": hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
                    "summary": "Reviewer checked the gate evidence directly.",
                }
            ],
            "reason": "The gate has direct evidence and can advance without router semantic approval.",
            "next_action": next_action,
            "contract_self_check": {
                "all_required_fields_present": True,
                "exact_field_names_used": True,
                "empty_required_arrays_explicit": True,
            },
        }

    def final_ledger_payload(self, root: Path) -> dict:
        run_root = self.run_root_for(root)
        root_contract_path = self.rel(root, run_root / "root_acceptance_contract.json")
        scenario_pack_path = self.rel(root, run_root / "standard_scenario_pack.json")
        route_flow_path = self.rel(root, run_root / "routes" / "route-001" / "flow.json")
        node_plan_path = self.rel(root, run_root / "routes" / "route-001" / "nodes" / "node-001" / "node_acceptance_plan.json")
        quality_review_path = self.rel(root, run_root / "reviews" / "evidence_quality_review.json")
        return {
            "pm_owned": True,
            **self.prior_path_context_review(root, "PM rebuilt final ledger from current route memory and source-of-truth ledgers."),
            "standard_scenarios_replayed": True,
            "root_contract_replay": [
                {
                    "requirement_id": "root-001",
                    "status": "approved",
                    "evidence_paths": [root_contract_path, scenario_pack_path],
                    "standard_scenarios_replayed": True,
                }
            ],
            "entries": [
                {
                    "entry_id": "route-001:root-contract",
                    "route_version": 1,
                    "node_id": "root",
                    "gate_family": "root_acceptance_contract",
                    "required_approver": "project_manager",
                    "status": "approved",
                    "source_of_truth_paths": [root_contract_path, scenario_pack_path],
                    "evidence_paths": [root_contract_path, scenario_pack_path],
                },
                {
                    "entry_id": "route-001:node-001:acceptance",
                    "route_version": 1,
                    "node_id": "node-001",
                    "gate_family": "node_acceptance",
                    "required_approver": "human_like_reviewer",
                    "status": "approved",
                    "source_of_truth_paths": [route_flow_path, node_plan_path],
                    "evidence_paths": [node_plan_path, quality_review_path],
                },
            ],
            "terminal_replay_segments": [
                {"segment_id": "delivered_product", "source_of_truth_paths": [root_contract_path]},
                {"segment_id": "root_acceptance", "source_of_truth_paths": [root_contract_path, scenario_pack_path]},
                {"segment_id": "leaf:node-001", "source_of_truth_paths": [route_flow_path, node_plan_path]},
            ],
            "pm_segment_decisions": [
                {"segment_id": "delivered_product", "decision": "continue"},
                {"segment_id": "root_acceptance", "decision": "continue"},
                {"segment_id": "leaf:node-001", "decision": "continue"},
            ],
        }

    def write_pm_suggestion_ledger(self, root: Path, entries: list[dict]) -> Path:
        run_root = self.run_root_for(root)
        ledger_path = run_root / "pm_suggestion_ledger.jsonl"
        ledger_path.write_text(
            "\n".join(json.dumps(entry, sort_keys=True) for entry in entries) + "\n",
            encoding="utf-8",
        )
        return ledger_path

    def pm_suggestion_entry(self, root: Path, *, clean: bool) -> dict:
        run_root = self.run_root_for(root)
        disposition = {
            "status": "reject_with_reason" if clean else "pending",
            "decided_by_role": "project_manager",
            "decided_at": "2026-05-10T00:00:00Z" if clean else None,
            "reason": "PM reviewed the nonblocking suggestion and rejected it for this route." if clean else None,
            "target_node_or_gate_id": None,
            "waiver_authority_role": None,
            "route_version_impact": None,
            "stale_evidence_handling": None,
            "repair_or_reissue_target": None,
            "same_review_class_recheck_required": False,
            "flowpilot_skill_improvement_report_path": self.rel(
                root,
                run_root / "flowpilot_skill_improvement_report.json",
            ),
        }
        return {
            "schema_version": "flowpilot.pm_suggestion_item.v1",
            "run_id": run_root.name,
            "route_id": "route-001",
            "route_version": 1,
            "node_id": "node-001",
            "gate_id": "gate-node-001",
            "suggestion_id": "suggestion-001",
            "recorded_at": "2026-05-10T00:00:00Z",
            "source_role": "human_like_reviewer",
            "source_output_ref": {
                "path": self.rel(root, run_root / "reviews" / "terminal_backward_replay.json"),
                "hash": None,
                "sealed_body_content_copied": False,
            },
            "summary": "Reviewer suggested a higher-standard follow-up.",
            "classification": "nonblocking_note" if clean else "current_gate_blocker",
            "authority_basis": {
                "reviewer_minimum_standard_failure": not clean,
                "formal_flowguard_model_gate": False,
                "worker_or_officer_advisory_only": False,
                "reason": "Reviewer finding classification test fixture.",
            },
            "evidence_refs": [],
            "pm_disposition": disposition,
            "closure": {
                "status": "closed" if clean else "open",
                "closed_at": "2026-05-10T00:00:00Z" if clean else None,
                "closure_evidence_refs": [],
                "blocks_current_gate_until_closed": not clean,
            },
        }

    def terminal_replay_payload(self, root: Path) -> dict:
        run_root = self.run_root_for(root)
        terminal_map = read_json(run_root / "terminal_human_backward_replay_map.json")
        segment_reviews = [
            {
                "segment_id": segment["segment_id"],
                "reviewed_by_role": "human_like_reviewer",
                "passed": True,
                "pm_segment_decision": "continue",
            }
            for segment in terminal_map["segments"]
        ]
        return {
            "reviewed_by_role": "human_like_reviewer",
            "passed": True,
            "segment_reviews": segment_reviews,
        }

    def complete_leaf_node_with_reviewed_result(
        self,
        root: Path,
        *,
        packet_id: str = "node-packet-leaf",
        agent_id: str = "agent-worker-leaf",
    ) -> None:
        self.deliver_current_node_cards(root)
        packet = packet_runtime.create_packet(
            root,
            packet_id=packet_id,
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="current node work",
            metadata={"route_version": 1},
        )
        packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
        router.record_external_event(root, "pm_registers_current_node_packet", {"packet_id": packet_id, "packet_envelope_path": packet_path})
        run_root = self.run_root_for(root)
        write_grant_path = run_root / "routes" / "route-001" / "nodes" / "node-001" / "current_node_write_grant.json"
        self.assertTrue(write_grant_path.exists())
        self.assertEqual(read_json(write_grant_path)["packet_id"], packet_id)
        self.apply_until_action(root, "relay_current_node_packet")
        packet_runtime.read_packet_body_for_role(root, read_json(root / packet_path), role="worker_a")
        result = packet_runtime.write_result(
            root,
            packet_envelope=read_json(root / packet_path),
            completed_by_role="worker_a",
            completed_by_agent_id=agent_id,
            result_body_text="reviewable result",
            next_recipient="project_manager",
        )
        result_path = result["result_body_path"].replace("result_body.md", "result_envelope.json")
        router.record_external_event(root, "worker_current_node_result_returned", {"packet_id": packet_id, "result_envelope_path": result_path})
        self.absorb_current_node_results_with_pm(root, [result_path])
        self.deliver_expected_card(root, "reviewer.worker_result_review")
        router.record_external_event(
            root,
            "current_node_reviewer_passes_result",
            self.role_report_envelope(
                root,
                "reviews/current_node_result",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": True,
                    "agent_role_map": {agent_id: "worker_a"},
                },
            ),
        )
        run_root = self.run_root_for(root)
        runtime_audit_path = run_root / "routes" / "route-001" / "nodes" / "node-001" / "reviews" / "current_node_packet_runtime_audit.json"
        self.assertTrue(runtime_audit_path.exists())
        runtime_audit = read_json(runtime_audit_path)
        self.assertTrue(runtime_audit["passed"])
        self.assertEqual(runtime_audit["router_replacement_scope"], "mechanical_only")
        self.assertFalse(runtime_audit["self_attested_ai_claims_accepted_as_proof"])
        runtime_proof = read_json(root / runtime_audit["router_owned_check_proof_path"])
        self.assertEqual(runtime_proof["source_kind"], "packet_runtime_hash")
        self.assertEqual(runtime_proof["reviewer_replacement_scope"], "mechanical_only")
        self.complete_parent_backward_replay_if_due(root)
        router.record_external_event(root, "pm_completes_current_node_from_reviewed_result")
        completion_ledger_path = run_root / "routes" / "route-001" / "nodes" / "node-001" / "node_completion_ledger.json"
        self.assertTrue(completion_ledger_path.exists())
        completion_ledger = read_json(completion_ledger_path)
        self.assertTrue(completion_ledger["flowpilot_completable_work_closed"])
        self.assertTrue(completion_ledger["human_inspection_notes_belong_in_final_report"])

    def prepare_current_node_result_for_review(
        self,
        root: Path,
        *,
        packet_id: str,
        completed_by_role: str = "worker_a",
        completed_by_agent_id: str = "agent-worker-a",
        deliver_review_card: bool = True,
        record_result_return: bool = True,
    ) -> tuple[Path, str, str]:
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.deliver_current_node_cards(root)
        packet = packet_runtime.create_packet(
            root,
            packet_id=packet_id,
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="current node work",
            metadata={"route_version": 1},
        )
        packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
        router.record_external_event(root, "pm_registers_current_node_packet", {"packet_id": packet_id, "packet_envelope_path": packet_path})
        self.apply_until_action(root, "relay_current_node_packet")
        packet_runtime.read_packet_body_for_role(root, read_json(root / packet_path), role="worker_a")
        result = packet_runtime.write_result(
            root,
            packet_envelope=read_json(root / packet_path),
            completed_by_role=completed_by_role,
            completed_by_agent_id=completed_by_agent_id,
            result_body_text="reviewable result",
            next_recipient="project_manager",
            strict_role=completed_by_role == "worker_a",
        )
        result_path = result["result_body_path"].replace("result_body.md", "result_envelope.json")
        if not record_result_return:
            return run_root, packet_path, result_path
        router.record_external_event(root, "worker_current_node_result_returned", {"packet_id": packet_id, "result_envelope_path": result_path})
        self.absorb_current_node_results_with_pm(root, [result_path])
        if deliver_review_card:
            self.deliver_expected_card(root, "reviewer.worker_result_review")
        return run_root, packet_path, result_path

    def apply_until_action(self, root: Path, expected_action_type: str, max_steps: int = 12) -> dict:
        for _ in range(max_steps):
            action = router.next_action(root)
            action_type = str(action["action_type"])
            if action_type == "deliver_system_card":
                self.ack_system_card_action(root, action)
            elif action_type == "await_card_return_event":
                self.ack_system_card_action(root, action)
            else:
                router.apply_action(root, action_type)
            if action_type == expected_action_type:
                return action
        raise AssertionError(f"did not apply {expected_action_type} within {max_steps} router steps")

    def test_reviewer_block_delivers_model_miss_triage_before_review_repair(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-model-miss-gate")

        router.record_external_event(root, "current_node_reviewer_blocks_result")

        card_action = self.deliver_expected_card(root, "pm.model_miss_triage")
        self.assert_payload_contract_mentions(
            card_action["payload_contract"],
            "pm_model_miss_triage_decision_role_output",
            "proceed_with_model_backed_repair",
            "officer_report_refs",
            "minimal_sufficient_repair_recommendation",
        )
        self.assertFalse(self.flag(root, "pm_review_repair_card_delivered"))
        self.deliver_expected_card(root, "pm.event.reviewer_blocked")
        wait_action = router.next_action(root)
        self.assertEqual(wait_action["action_type"], "await_role_decision")
        self.assertIn("pm_records_model_miss_triage_decision", wait_action["allowed_external_events"])
        self.assertIn("pm_registers_role_work_request", wait_action["allowed_external_events"])
        self.assert_payload_contract_mentions(wait_action["payload_contract"], "same_class_findings_reviewed")

    def test_review_block_route_mutation_requires_closed_model_miss_triage(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-model-miss-mutation")
        router.record_external_event(root, "current_node_reviewer_blocks_result")

        with self.assertRaisesRegex(router.RouterError, "model[_-]miss"):
            router.record_external_event(
                root,
                "pm_mutates_route_after_review_block",
                {"repair_node_id": "node-001-repair", "reason": "reviewer_block"},
            )

    def test_stale_review_block_route_mutation_wait_is_recomputed_before_pm_triage(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-model-miss-stale-wait")
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        run_root = self.run_root_for(root)
        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"].get("model_miss_triage_closed"))
        state["pending_action"] = {
            "schema_version": router.SCHEMA_VERSION,
            "action_id": "stale-route-mutation-wait",
            "action_type": "await_role_decision",
            "actor": "controller",
            "label": "controller_waits_for_expected_event_pm_mutates_route_after_review_block",
            "allowed_external_events": ["pm_mutates_route_after_review_block"],
            "allowed_reads": [self.rel(root, router.run_state_path(run_root))],
            "allowed_writes": [self.rel(root, router.run_state_path(run_root))],
        }
        router.save_run_state(run_root, state)

        action = self.deliver_expected_card(root, "pm.model_miss_triage")

        self.assertEqual(action["action_type"], "deliver_system_card")
        self.assertEqual(action["card_id"], "pm.model_miss_triage")
        repaired_state = read_json(router.run_state_path(run_root))
        labels = [entry["label"] for entry in repaired_state["history"]]
        self.assertIn("router_cleared_stale_pending_action", labels)
        pending = repaired_state["pending_action"]
        if pending is not None:
            self.assertEqual(pending["label"], "controller_instructed_to_check_prompt_manifest")
            self.assertEqual(pending["next_card_id"], "pm.event.reviewer_blocked")

    def test_node_acceptance_plan_block_enters_model_miss_repair_path(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.write_current_node_acceptance_plan(root)
        self.deliver_expected_card(root, "reviewer.node_acceptance_plan_review")

        router.record_external_event(
            root,
            "reviewer_blocks_node_acceptance_plan",
            self.role_report_envelope(
                root,
                "reviews/node_acceptance_plan_block",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": False,
                    "blockers": ["acceptance evidence path is not router-authorized"],
                },
            ),
        )

        self.assertTrue(self.flag(root, "node_acceptance_plan_review_blocked"))
        self.deliver_expected_card(root, "pm.model_miss_triage")
        self.close_model_miss_triage(root, output_name="decisions/node_acceptance_model_miss_valid")
        self.deliver_expected_card(root, "pm.review_repair")
        self.deliver_expected_card(root, "pm.event.reviewer_blocked")
        router.record_external_event(
            root,
            "pm_mutates_route_after_review_block",
            {
                "repair_node_id": "node-001-acceptance-repair",
                "repair_return_to_node_id": "node-001",
                "reason": "node_acceptance_plan_review_block",
                **self.prior_path_context_review(root, "Route mutation considered the node acceptance-plan reviewer block."),
            },
        )

        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"]["node_acceptance_plan_review_blocked"])
        frontier = read_json(run_root / "execution_frontier.json")
        self.assertEqual(frontier["status"], "route_mutation_pending_recheck")
        self.assertEqual(frontier["active_node_id"], "node-001")
        self.assertEqual(frontier["pending_route_mutation"]["candidate_node_id"], "node-001-acceptance-repair")

    def test_route_root_node_entry_gap_requires_replanning_not_repair_node(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.deliver_expected_card(root, "pm.prior_path_context")
        self.deliver_expected_card(root, "pm.route_skeleton")
        router.record_external_event(
            root,
            "pm_writes_route_draft",
            {
                "route": {
                    "route_id": "route-001",
                    "route_version": 1,
                    "active_node_id": "route_root",
                    "nodes": [
                        {
                            "node_id": "route_root",
                            "node_kind": "parent",
                            "title": "Route root",
                            "child_node_ids": ["child-001"],
                        },
                        {
                            "node_id": "child-001",
                            "node_kind": "leaf",
                            "parent_node_id": "route_root",
                            "leaf_readiness_gate": {"status": "pass"},
                        },
                    ],
                },
                **self.prior_path_context_review(root, "Parent route draft considered route memory before activation."),
            },
        )
        self.complete_route_checks(root)
        router.record_external_event(root, "pm_activates_reviewed_route", {"route_id": "route-001", "active_node_id": "route_root"})
        self.write_current_node_acceptance_plan(root)
        self.deliver_expected_card(root, "reviewer.node_acceptance_plan_review")
        router.record_external_event(
            root,
            "reviewer_blocks_node_acceptance_plan",
            self.role_report_envelope(
                root,
                "reviews/root_node_acceptance_plan_block",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": False,
                    "blocking_findings": ["route root is still a planning boundary and lacks executable child expansion"],
                },
            ),
        )
        self.close_model_miss_triage(root, output_name="decisions/root_node_entry_gap_triage")

        with self.assertRaisesRegex(router.RouterError, "replanning.*not.*repair node"):
            router.record_external_event(
                root,
                "pm_mutates_route_after_review_block",
                {
                    "repair_node_id": "route_root-repair",
                    "repair_return_to_node_id": "route_root",
                    "reason": "root_node_acceptance_plan_review_block",
                    **self.prior_path_context_review(root, "Root planning gap must be replanned before repair is available."),
                },
            )

        frontier = read_json(run_root / "execution_frontier.json")
        self.assertEqual(frontier["active_node_id"], "route_root")
        self.assertNotEqual(frontier.get("status"), "route_mutation_pending_recheck")

    def test_node_acceptance_plan_block_can_be_revised_on_same_node(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.write_current_node_acceptance_plan(root)
        self.deliver_expected_card(root, "reviewer.node_acceptance_plan_review")

        router.record_external_event(
            root,
            "reviewer_blocks_node_acceptance_plan",
            self.role_report_envelope(
                root,
                "reviews/node_acceptance_plan_block_same_node",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": False,
                    "blocking_findings": ["work_packet_projection is missing a required inherited gate row"],
                    "recommended_resolution": "PM should revise the same node acceptance plan and resubmit it for review.",
                },
            ),
        )
        self.deliver_expected_card(root, "pm.model_miss_triage")
        self.close_model_miss_triage(root, output_name="decisions/node_acceptance_same_node_repair_triage")
        self.deliver_expected_card(root, "pm.review_repair")
        self.deliver_expected_card(root, "pm.event.reviewer_blocked")
        wait_action = router.next_action(root)
        self.assertIn("pm_revises_node_acceptance_plan", wait_action["allowed_external_events"])
        self.assertIn("pm_mutates_route_after_review_block", wait_action["allowed_external_events"])

        router.record_external_event(
            root,
            "pm_revises_node_acceptance_plan",
            {
                **self.prior_path_context_review(root, "PM chose same-node plan repair because the current node can contain the missing gate row."),
                "high_standard_recheck": {
                    "ideal_outcome": "complete the current node at the highest practical standard",
                    "unacceptable_outcomes": ["partial work", "unverified closure", "controller downgrade"],
                    "higher_standard_opportunities": ["tighten inherited gate rows before dispatch"],
                    "semantic_downgrade_risks": ["treating a plan wording repair as a route-level defect"],
                    "decision": "proceed",
                    "why_current_plan_meets_highest_reasonable_standard": "PM revised the current node plan with the missing inherited gate row and kept route structure unchanged.",
                },
                "node_requirements": [
                    {
                        "requirement_id": "node-001-req",
                        "acceptance_statement": "current node work is complete with inherited gate coverage",
                        "proof_required": "mixed",
                    }
                ],
                "experiment_plan": [],
            },
        )

        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"]["node_acceptance_plan_review_blocked"])
        self.assertTrue(state["flags"]["node_acceptance_plan_revised_by_pm"])
        self.assertFalse(state["flags"]["reviewer_node_acceptance_plan_card_delivered"])
        self.deliver_expected_card(root, "reviewer.node_acceptance_plan_review")
        router.record_external_event(
            root,
            "reviewer_passes_node_acceptance_plan",
            self.role_report_envelope(
                root,
                "reviews/node_acceptance_plan_review_recheck",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )

        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["node_acceptance_plan_reviewer_passed"])
        frontier = read_json(run_root / "execution_frontier.json")
        self.assertEqual(frontier["status"], "current_node_loop")
        self.assertFalse(state["flags"].get("route_mutated_by_pm"))
        display_plan = read_json(run_root / "display_plan.json")
        self.assertEqual(display_plan["source_event"], "pm_revises_node_acceptance_plan")
        repair_record = read_json(run_root / "routes" / "route-001" / "nodes" / "node-001" / "repairs" / "node_acceptance_plan_revision.json")
        self.assertTrue(repair_record["stale_blocked_plan_is_context_only"])

    def test_current_node_direct_relay_blocks_missing_output_contract(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.deliver_current_node_cards(root)
        packet = packet_runtime.create_packet(
            root,
            packet_id="node-packet-dispatch-block",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="current node work",
            metadata={"route_version": 1},
        )
        packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
        router.record_external_event(
            root,
            "pm_registers_current_node_packet",
            {"packet_id": "node-packet-dispatch-block", "packet_envelope_path": packet_path},
        )
        envelope_path = root / packet_path
        envelope = read_json(envelope_path)
        envelope.pop("output_contract", None)
        envelope.pop("output_contract_id", None)
        router.write_json(envelope_path, envelope)

        with self.assertRaisesRegex(router.RouterError, "missing_output_contract"):
            self.apply_until_action(root, "relay_current_node_packet")
        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"]["current_node_packet_relayed"])

    def test_model_backed_model_miss_triage_requires_officer_report_refs(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-model-miss-invalid")
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        self.deliver_expected_card(root, "pm.model_miss_triage")

        body = self.model_miss_triage_body(root, decision="proceed_with_model_backed_repair")
        body.pop("officer_report_refs")
        with self.assertRaisesRegex(router.RouterError, "officer_report_refs"):
            router.record_external_event(
                root,
                "pm_records_model_miss_triage_decision",
                self.role_decision_envelope(root, "decisions/model_miss_invalid", body),
            )
        self.assertFalse(self.flag(root, "model_miss_triage_closed"))

    def test_non_authorizing_model_miss_decision_does_not_unlock_review_repair(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-model-miss-request")
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        self.deliver_expected_card(root, "pm.model_miss_triage")

        router.record_external_event(
            root,
            "pm_records_model_miss_triage_decision",
            self.role_decision_envelope(
                root,
                "decisions/model_miss_request",
                self.model_miss_triage_body(root, decision="request_officer_model_miss_analysis"),
            ),
        )

        self.assertFalse(self.flag(root, "model_miss_triage_closed"))
        self.assertFalse(self.flag(root, "pm_review_repair_card_delivered"))
        state = read_json(router.run_state_path(self.run_root_for(root)))
        self.assertTrue(state["flags"]["model_miss_triage_followup_request_pending"])
        self.assertEqual(
            state["model_miss_triage_followup_request"]["required_output_contract_id"],
            "flowpilot.output_contract.flowguard_model_miss_report.v1",
        )
        self.deliver_expected_card(root, "pm.event.reviewer_blocked")
        wait = self.next_after_display_sync(root)
        self.assertEqual(wait["action_type"], "await_role_decision")
        self.assertEqual(wait["allowed_external_events"], ["pm_registers_role_work_request"])

    def test_pm_model_miss_followup_uses_generic_role_work_request_channel(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-role-work-request")
        run_root = self.run_root_for(root)
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        self.deliver_expected_card(root, "pm.model_miss_triage")
        router.record_external_event(
            root,
            "pm_records_model_miss_triage_decision",
            self.role_decision_envelope(
                root,
                "decisions/model_miss_role_work_request",
                self.model_miss_triage_body(root, decision="request_officer_model_miss_analysis"),
            ),
        )
        self.deliver_expected_card(root, "pm.event.reviewer_blocked")

        router.record_external_event(root, "pm_registers_role_work_request", self.pm_role_work_request_payload(root))
        index = read_json(run_root / "pm_work_requests" / "index.json")
        self.assertEqual(index["active_request_id"], "model-miss-followup-001")
        self.assertEqual(index["requests"][0]["to_role"], "product_flowguard_officer")
        self.assertEqual(index["requests"][0]["status"], "open")

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_pm_role_work_request_packet")
        self.assertEqual(action["request_id"], "model-miss-followup-001")
        router.apply_action(root, "relay_pm_role_work_request_packet")

        index = read_json(run_root / "pm_work_requests" / "index.json")
        self.assertEqual(index["requests"][0]["status"], "packet_relayed")
        result_path = self.open_role_work_packet_and_write_result(root)
        router.record_external_event(
            root,
            "role_work_result_returned",
            {
                "request_id": "model-miss-followup-001",
                "packet_id": "pm-role-work-model-miss-followup-001",
                "result_envelope_path": result_path,
            },
        )

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_pm_role_work_result_to_pm")
        router.apply_action(root, "relay_pm_role_work_result_to_pm")
        router.record_external_event(
            root,
            "pm_records_role_work_result_decision",
            {
                "decided_by_role": "project_manager",
                "request_id": "model-miss-followup-001",
                "decision": "absorbed",
                "decision_reason": "PM reviewed the officer model-miss result.",
            },
        )

        index = read_json(run_root / "pm_work_requests" / "index.json")
        self.assertEqual(index["requests"][0]["status"], "absorbed")
        self.assertIsNone(index["active_request_id"])

    def test_gate_targeted_pm_role_work_result_requires_mapped_gate_event(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-gate-targeted-role-work")
        run_root = self.run_root_for(root)
        state_path = router.run_state_path(run_root)
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        self.deliver_expected_card(root, "pm.model_miss_triage")
        router.record_external_event(
            root,
            "pm_records_model_miss_triage_decision",
            self.role_decision_envelope(
                root,
                "decisions/gate_targeted_model_miss_role_work",
                self.model_miss_triage_body(root, decision="request_officer_model_miss_analysis"),
            ),
        )
        self.deliver_expected_card(root, "pm.event.reviewer_blocked")

        request = self.pm_role_work_request_payload(
            root,
            request_id="gate-modelability-followup-001",
            body_text="Assess product architecture modelability and return the result to PM.",
        )
        request["target_gate_id"] = "product_behavior_model"
        router.record_external_event(root, "pm_registers_role_work_request", request)
        index = read_json(run_root / "pm_work_requests" / "index.json")
        self.assertEqual(index["requests"][0]["target_gate_contract"]["gate_id"], "product_behavior_model")

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_pm_role_work_request_packet")
        router.apply_action(root, "relay_pm_role_work_request_packet")

        result_path = self.open_role_work_packet_and_write_result(root, request_id="gate-modelability-followup-001")
        router.record_external_event(
            root,
            "role_work_result_returned",
            {
                "request_id": "gate-modelability-followup-001",
                "packet_id": "pm-role-work-gate-modelability-followup-001",
                "result_envelope_path": result_path,
            },
        )
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_pm_role_work_result_to_pm")
        router.apply_action(root, "relay_pm_role_work_result_to_pm")
        wait = self.next_after_display_sync(root)
        self.assertIn("mapped_gate_event", wait["payload_contract"]["required_fields"])

        with self.assertRaisesRegex(router.RouterError, "mapped_gate_event"):
            router.record_external_event(
                root,
                "pm_records_role_work_result_decision",
                {
                    "decided_by_role": "project_manager",
                    "request_id": "gate-modelability-followup-001",
                    "decision": "absorbed",
                    "decision_reason": "PM reviewed the officer result.",
                },
            )
        router.record_external_event(
            root,
            "pm_records_role_work_result_decision",
            {
                "decided_by_role": "project_manager",
                "request_id": "gate-modelability-followup-001",
                "decision": "absorbed",
                "decision_reason": "PM reviewed the officer result and maps it to the gate pass event.",
                "mapped_gate_event": "product_officer_passes_product_architecture_modelability",
            },
        )

        state = read_json(state_path)
        self.assertTrue(state["flags"]["product_behavior_model_submitted"])
        self.assertTrue(state["flags"]["product_architecture_modelability_passed"])
        self.assertTrue((run_root / "flowguard" / "product_behavior_model.json").exists())
        self.assertTrue((run_root / "flowguard" / "product_architecture_modelability.json").exists())
        self.assertTrue(
            any(
                item.get("event") == "product_officer_passes_product_architecture_modelability"
                and item.get("payload", {}).get("mapped_from_event") == "pm_records_role_work_result_decision"
                for item in state["events"]
                if isinstance(item, dict)
            )
        )

    def test_pm_role_work_batch_waits_for_all_officer_results_before_pm_relay(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-role-work-batch")
        run_root = self.run_root_for(root)
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        self.deliver_expected_card(root, "pm.model_miss_triage")
        router.record_external_event(
            root,
            "pm_records_model_miss_triage_decision",
            self.role_decision_envelope(
                root,
                "decisions/model_miss_role_work_batch",
                self.model_miss_triage_body(root, decision="request_officer_model_miss_analysis"),
            ),
        )
        self.deliver_expected_card(root, "pm.event.reviewer_blocked")

        router.record_external_event(
            root,
            "pm_registers_role_work_request",
            {
                "requested_by_role": "project_manager",
                "batch_id": "pm-model-miss-batch-001",
                "requests": [
                    self.pm_role_work_request_payload(
                        root,
                        request_id="model-miss-product-001",
                        to_role="product_flowguard_officer",
                    ),
                    self.pm_role_work_request_payload(
                        root,
                        request_id="model-miss-process-001",
                        to_role="process_flowguard_officer",
                        body_text="Analyze the missed process invariant and recommend a minimal model repair.",
                    ),
                ],
            },
        )
        index = read_json(run_root / "pm_work_requests" / "index.json")
        self.assertEqual(index["active_batch_id"], "pm-model-miss-batch-001")
        self.assertEqual(index["active_request_ids"], ["model-miss-product-001", "model-miss-process-001"])

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_pm_role_work_request_packet")
        self.assertEqual(sorted(action["packet_ids"]), ["pm-role-work-model-miss-process-001", "pm-role-work-model-miss-product-001"])
        router.apply_action(root, "relay_pm_role_work_request_packet")

        product_result_path = self.open_role_work_packet_and_write_result(root, request_id="model-miss-product-001")
        router.record_external_event(
            root,
            "role_work_result_returned",
            {
                "request_id": "model-miss-product-001",
                "packet_id": "pm-role-work-model-miss-product-001",
                "result_envelope_path": product_result_path,
            },
        )
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertEqual(action["allowed_external_events"], ["role_work_result_returned"])
        self.assertIn("process_flowguard_officer", action["to_role"])

        process_result_path = self.open_role_work_packet_and_write_result(root, request_id="model-miss-process-001")
        router.record_external_event(
            root,
            "role_work_result_returned",
            {
                "request_id": "model-miss-process-001",
                "packet_id": "pm-role-work-model-miss-process-001",
                "result_envelope_path": process_result_path,
            },
        )
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_pm_role_work_result_to_pm")
        self.assertEqual(sorted(action["packet_ids"]), ["pm-role-work-model-miss-process-001", "pm-role-work-model-miss-product-001"])
        router.apply_action(root, "relay_pm_role_work_result_to_pm")
        router.record_external_event(
            root,
            "pm_records_role_work_result_decision",
            {
                "decided_by_role": "project_manager",
                "batch_id": "pm-model-miss-batch-001",
                "decision": "absorbed",
                "decision_reason": "PM reviewed the complete officer batch.",
            },
        )

        index = read_json(run_root / "pm_work_requests" / "index.json")
        self.assertIsNone(index["active_batch_id"])
        self.assertTrue(all(record["status"] == "absorbed" for record in index["requests"]))

    def test_pm_role_work_request_requires_valid_recipient_and_contract(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-role-work-invalid")
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        self.deliver_expected_card(root, "pm.model_miss_triage")
        router.record_external_event(
            root,
            "pm_records_model_miss_triage_decision",
            self.role_decision_envelope(
                root,
                "decisions/model_miss_role_work_invalid",
                self.model_miss_triage_body(root, decision="request_officer_model_miss_analysis"),
            ),
        )

        bad_contract = self.pm_role_work_request_payload(root, request_id="bad-contract")
        bad_contract.pop("output_contract_id")
        with self.assertRaisesRegex(router.RouterError, "output_contract_id"):
            router.record_external_event(root, "pm_registers_role_work_request", bad_contract)

        bad_role = self.pm_role_work_request_payload(root, request_id="bad-role", to_role="controller")
        with self.assertRaisesRegex(router.RouterError, "other than PM or Controller"):
            router.record_external_event(root, "pm_registers_role_work_request", bad_role)

    def test_pm_role_work_request_rejects_current_node_contract_family(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        state["pending_action"] = {
            "action_type": "await_role_decision",
            "to_role": "project_manager",
            "allowed_external_events": ["pm_registers_role_work_request"],
        }
        router.write_json(router.run_state_path(run_root), state)

        bad_contract = self.pm_role_work_request_payload(
            root,
            request_id="bad-current-node-contract",
            to_role="worker_a",
            request_kind="implementation",
            output_contract_id="flowpilot.output_contract.worker_current_node_result.v1",
            body_text="Do a delegated PM repair task.",
        )
        with self.assertRaisesRegex(router.RouterError, "does not match PM role-work process"):
            router.record_external_event(root, "pm_registers_role_work_request", bad_contract)

    def test_strict_pm_role_work_result_rejects_wrong_next_recipient(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-strict-role-work")
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        self.deliver_expected_card(root, "pm.model_miss_triage")
        self.deliver_expected_card(root, "pm.event.reviewer_blocked")
        run_root = self.run_root_for(root)

        router.record_external_event(
            root,
            "pm_registers_role_work_request",
            self.pm_role_work_request_payload(
                root,
                request_id="strict-role-work-001",
                to_role="worker_a",
                request_kind="implementation",
                output_contract_id="flowpilot.output_contract.pm_role_work_result.v1",
                body_text="Do a delegated PM repair task.",
            ),
        )
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_pm_role_work_request_packet")
        router.apply_action(root, "relay_pm_role_work_request_packet")

        index = read_json(run_root / "pm_work_requests" / "index.json")
        record = index["requests"][0]
        envelope = packet_runtime.load_envelope(root, record["packet_envelope_path"])
        packet_runtime.read_packet_body_for_role(root, envelope, role="worker_a")
        result = packet_runtime.write_result(
            root,
            packet_envelope=envelope,
            completed_by_role="worker_a",
            completed_by_agent_id="worker-a-agent",
            result_body_text="Status\n\nComplete\n\nContract Self-Check\n\nPassed.",
            next_recipient="human_like_reviewer",
        )
        result_path = result["result_body_path"].replace("result_body.md", "result_envelope.json")
        with self.assertRaisesRegex(router.RouterError, "next_recipient must match process binding"):
            router.record_external_event(
                root,
                "role_work_result_returned",
                {
                    "request_id": "strict-role-work-001",
                    "packet_id": "pm-role-work-strict-role-work-001",
                    "result_envelope_path": result_path,
                },
            )

    def test_wait_event_producer_binding_rejects_wrong_target_role(self) -> None:
        with self.assertRaisesRegex(router.RouterError, "event producer role"):
            router._validate_wait_event_producer_binding(
                ["current_node_reviewer_passes_result"],
                to_role="project_manager",
                context="test wait",
            )
        router._validate_wait_event_producer_binding(
            ["current_node_reviewer_passes_result"],
            to_role="human_like_reviewer",
            context="test wait",
        )
        self.assertEqual(
            router._control_blocker_followup_target_role(
                ["current_node_reviewer_passes_result"],
                "project_manager",
            ),
            "human_like_reviewer",
        )

    def test_model_backed_model_miss_triage_unlocks_review_repair(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-model-miss-valid")
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        self.deliver_expected_card(root, "pm.model_miss_triage")

        router.record_external_event(
            root,
            "pm_records_model_miss_triage_decision",
            self.role_decision_envelope(
                root,
                "decisions/model_miss_valid",
                self.model_miss_triage_body(root, decision="proceed_with_model_backed_repair"),
            ),
        )

        self.assertTrue(self.flag(root, "model_miss_triage_closed"))
        self.deliver_expected_card(root, "pm.review_repair")

    def test_out_of_scope_model_miss_triage_unlocks_review_repair_with_reason(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-model-miss-out-of-scope")
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        self.deliver_expected_card(root, "pm.model_miss_triage")

        router.record_external_event(
            root,
            "pm_records_model_miss_triage_decision",
            self.role_decision_envelope(
                root,
                "decisions/model_miss_out_of_scope",
                self.model_miss_triage_body(root, decision="out_of_scope_not_modelable"),
            ),
        )

        self.assertTrue(self.flag(root, "model_miss_triage_closed"))
        self.deliver_expected_card(root, "pm.review_repair")

    def test_bootloader_action_requires_pending_router_action(self) -> None:
        root = self.make_project()

        with self.assertRaises(router.RouterError):
            router.apply_action(root, "ask_startup_questions")

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "load_router")
        self.assertEqual(self.next_and_apply(root)["applied"], "load_router")

    def test_run_until_wait_applies_only_safe_startup_action(self) -> None:
        root = self.make_project()
        result = router.run_until_wait(root, new_invocation=True)
        self.assertEqual(result["action_type"], "ask_startup_questions")
        self.assertEqual(result["folded_command"], "run-until-wait")
        self.assertEqual(result["folded_applied_count"], 1)
        self.assertEqual([item["action_type"] for item in result["folded_applied_actions"]], ["load_router"])
        self.assertEqual(result["folded_stop_reason"], "requires_user_host_or_role_boundary")

    def test_run_until_wait_folds_only_internal_bootloader_actions_after_banner(self) -> None:
        root = self.make_project()
        result = router.run_until_wait(root, new_invocation=True)
        router.apply_action(root, "ask_startup_questions")
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "record_startup_answers")
        router.apply_action(root, "record_startup_answers", {"startup_answers": STARTUP_ANSWERS})
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "emit_startup_banner")
        router.apply_action(root, "emit_startup_banner", self.payload_for_action(action))

        result = router.run_until_wait(root)

        self.assertEqual(result["action_type"], "record_user_request")
        self.assertEqual(result["folded_command"], "run-until-wait")
        self.assertEqual(
            [item["action_type"] for item in result["folded_applied_actions"]],
            [
                "create_run_shell",
                "write_current_pointer",
                "update_run_index",
                "copy_runtime_kit",
                "fill_runtime_placeholders",
                "initialize_mailbox",
            ],
        )
        self.assertEqual(result["folded_stop_reason"], "requires_user_host_or_role_boundary")
        bootstrap = self.bootstrap_state(root)
        self.assertTrue(bootstrap["flags"]["run_shell_created"])
        self.assertTrue(bootstrap["flags"]["mailbox_initialized"])
        self.assertFalse(bootstrap["flags"].get("user_request_recorded", False))
        self.assertTrue((root / ".flowpilot" / "current.json").exists())
        self.assertTrue((self.run_root_for(root) / "packet_ledger.json").exists())

    def test_run_until_wait_folds_user_intake_then_stops_before_role_boundary(self) -> None:
        root = self.make_project()
        router.run_until_wait(root, new_invocation=True)
        router.apply_action(root, "ask_startup_questions")
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "record_startup_answers")
        router.apply_action(root, "record_startup_answers", {"startup_answers": STARTUP_ANSWERS})
        action = router.next_action(root)
        router.apply_action(root, "emit_startup_banner", self.payload_for_action(action))
        router.run_until_wait(root)
        router.apply_action(root, "record_user_request", {"user_request": USER_REQUEST})

        result = router.run_until_wait(root)

        self.assertEqual(result["action_type"], "start_role_slots")
        self.assertTrue(result["requires_host_spawn"])
        self.assertEqual(
            [item["action_type"] for item in result["folded_applied_actions"]],
            ["write_user_intake"],
        )
        self.assertEqual(result["folded_stop_reason"], "requires_user_host_or_role_boundary")
        self.assertTrue((self.run_root_for(root) / "mailbox" / "outbox" / "user_intake.json").exists())
        self.assertFalse(self.bootstrap_state(root)["flags"].get("roles_started", False))

    def test_startup_sequence_creates_prompt_isolated_run(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        bootstrap = self.bootstrap_state(root)
        self.assertTrue(bootstrap["router_loaded"])
        self.assertEqual(bootstrap["bootstrap_scope"], "run_scoped")
        self.assertEqual(root / bootstrap["run_root"], run_root)
        self.assertEqual(bootstrap["bootloader_actions"], 13)
        self.assertEqual(bootstrap["router_action_requests"], 13)
        self.assertIsNone(bootstrap["pending_action"])
        self.assertEqual(bootstrap["startup_answers"], STARTUP_ANSWERS)
        self.assertEqual(bootstrap["user_request"], USER_REQUEST)
        self.assertTrue(bootstrap["flags"]["role_core_prompts_injected"])

        self.assertTrue((run_root / "runtime_kit" / "manifest.json").exists())
        self.assertTrue((run_root / "packet_ledger.json").exists())
        self.assertTrue((run_root / "execution_frontier.json").exists())
        self.assertEqual(len(list((run_root / "crew_memory").glob("*.json"))), 6)
        self.assertTrue((run_root / "user_request.json").exists())
        self.assertTrue((run_root / "mailbox" / "outbox" / "user_intake.json").exists())
        self.assertTrue((run_root / "role_core_prompt_delivery.json").exists())
        role_core_delivery = read_json(run_root / "role_core_prompt_delivery.json")
        self.assertEqual(role_core_delivery["delivery_mode"], "same_action_with_role_start")
        self.assertEqual(role_core_delivery["source_action"], "start_role_slots")
        self.assertEqual(set(role_core_delivery["role_card_hashes"]), set(router.ROLE_CARD_KEYS))

        crew = read_json(run_root / "crew_ledger.json")
        self.assertEqual(len(crew["role_slots"]), 6)
        self.assertNotIn("controller", {slot["role_key"] for slot in crew["role_slots"]})
        self.assertEqual({slot["status"] for slot in crew["role_slots"]}, {"live_agent_started"})
        self.assertTrue(all(slot["agent_id"] for slot in crew["role_slots"]))

    def test_display_plan_is_controller_synced_projection_from_pm_plan(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "sync_display_plan")
        self.assertEqual(action["display_kind"], "startup_waiting_state")
        self.assertIn("FlowPilot Startup Status", action["display_text"])
        self.assertEqual(action["payload_template"]["display_confirmation"]["action_type"], "sync_display_plan")
        self.assertEqual(action["payload_template"]["display_confirmation"]["display_kind"], "startup_waiting_state")
        self.assertEqual(
            action["payload_template"]["display_confirmation"]["display_text_sha256"],
            action["display_text_sha256"],
        )
        self.assertEqual(action["native_plan_projection"]["items"][0]["id"], "await_pm_route")
        result = router.apply_action(root, "sync_display_plan", self.payload_for_action(action))
        self.assertEqual(result["host_action"], "replace_visible_plan")
        self.assertEqual(result["display_kind"], "startup_waiting_state")
        waiting_plan = read_json(run_root / "display_plan.json")
        self.assertEqual(waiting_plan["source_role"], "controller")
        self.assertEqual(waiting_plan["route_authority"], "none_until_pm_display_plan")
        waiting_snapshot = read_json(run_root / "route_state_snapshot.json")
        self.assertEqual(waiting_snapshot["schema_version"], "flowpilot.route_state_snapshot.v1")
        self.assertTrue(waiting_snapshot["authority"]["current_pointer_matches_run"])
        self.assertEqual(waiting_snapshot["active_ui_task_catalog"]["active_tasks"][0]["run_id"], waiting_snapshot["run_id"])

        self.complete_pre_route_gates(root)
        route_plan = read_json(run_root / "display_plan.json")
        self.assertNotEqual(route_plan.get("source_event"), "pm_writes_route_draft")
        self.assertNotEqual(route_plan.get("scope"), "route")
        self.assertNotEqual(route_plan["items"][0]["id"], "node-001")
        draft_visibility = read_json(router.run_state_path(run_root))["draft_route_visibility"]
        self.assertFalse(draft_visibility["user_visible"])
        self.assertEqual(draft_visibility["reason"], "draft_routes_are_internal_until_pm_activates_reviewed_flow_json")

        index_path = root / ".flowpilot" / "index.json"
        index = read_json(index_path)
        index["runs"].append({"run_id": "run-stale", "run_root": ".flowpilot/runs/run-stale", "status": "running"})
        index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        self.activate_route(root)
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "sync_display_plan")
        self.assertEqual(action["native_plan_projection"]["items"][0]["status"], "in_progress")
        self.assertEqual(action["display_kind"], "route_map")
        self.assertEqual(action["display_text_format"], "markdown_mermaid")
        self.assertTrue(action["route_sign_display_required"])
        self.assertIn(action["route_sign_source_kind"], {"flow_json", "route_state_snapshot"})
        self.assertNotEqual(action["route_sign_source_kind"], "flow_draft")
        self.assertIn("# FlowPilot Route Sign", action["display_text"])
        self.assertIn("```mermaid", action["display_text"])
        self.assertIn("route=route-001", action["display_text"])
        self.assertIn("class n01 active;", action["display_text"])
        self.assertNotIn("Now: node-001", action["display_text"])
        self.assertNotIn("- node-001 - in_progress", action["display_text"])
        router.apply_action(root, "sync_display_plan", self.payload_for_action(action))
        display_packet = read_json(run_root / "diagrams" / "user-flow-diagram-display.json")
        self.assertTrue(display_packet["canonical_route_available"])
        self.assertEqual(display_packet["display_role"], "canonical_route")
        self.assertFalse(display_packet["is_placeholder"])
        self.assertIsNone(display_packet["replacement_rule"])
        route_sign = (run_root / "diagrams" / "user-flow-diagram.mmd").read_text(encoding="utf-8")
        self.assertIn("route=route-001", route_sign)
        self.assertIn("class n01 active;", route_sign)
        self.assertNotIn("Now: node-001", route_sign)
        self.assertNotIn("route=unknown", route_sign)
        visible_sync = read_json(router.run_state_path(run_root))["visible_plan_sync"]
        self.assertEqual(visible_sync["display_text_format"], "markdown_mermaid")
        self.assertTrue(visible_sync["route_sign_display_required"])
        self.assertEqual(visible_sync["route_sign_node_count"], 1)
        active_snapshot = read_json(run_root / "route_state_snapshot.json")
        self.assertEqual(active_snapshot["route"]["nodes"][0]["id"], "node-001")
        self.assertTrue(active_snapshot["route"]["nodes"][0]["is_active"])
        self.assertEqual(active_snapshot["authority"]["stale_running_index_entries"], [])
        self.assertEqual(active_snapshot["active_ui_task_catalog"]["hidden_non_current_running_index_entries"], [])
        index_after = read_json(index_path)
        stale_entry = next(item for item in index_after["runs"] if item["run_id"] == "run-stale")
        self.assertEqual(stale_entry["status"], "stale_not_current")
        self.assertEqual(stale_entry["stale_reason"], "not_current_pointer")

        self.deliver_current_node_cards(root)
        node_plan = read_json(run_root / "display_plan.json")
        self.assertEqual(node_plan["source_event"], "pm_writes_node_acceptance_plan")
        self.assertEqual(node_plan["current_node"]["checklist"][0]["id"], "node-001-req")

    def test_nonterminal_node_completion_does_not_show_completed_node_as_in_progress(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.complete_material_flow(root)
        self.complete_root_contract_before_child_skill_gates(root)
        self.complete_child_skill_gates(root)
        self.deliver_expected_card(root, "pm.prior_path_context")
        self.deliver_expected_card(root, "pm.route_skeleton")
        router.record_external_event(
            root,
            "pm_writes_route_draft",
            {
                "nodes": [
                    {"node_id": "node-001", "title": "First node"},
                    {"node_id": "node-002", "title": "Second node"},
                ],
                **self.prior_path_context_review(root, "Two-node route draft considered current route memory."),
            },
        )
        self.complete_route_checks(root)
        self.activate_route(root)

        self.complete_leaf_node_with_reviewed_result(root, packet_id="node-packet-nonterminal")

        display_plan = read_json(run_root / "display_plan.json")
        statuses = {item["id"]: item["status"] for item in display_plan["items"]}
        self.assertEqual(statuses["node-001"], "completed")
        self.assertEqual(statuses["node-002"], "in_progress")
        self.assertEqual(list(statuses.values()).count("in_progress"), 1)

    def test_reviewed_route_activation_uses_pm_draft_without_dummy_fallback(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)

        self.activate_route(root)

        flow = read_json(run_root / "routes" / "route-001" / "flow.json")
        self.assertEqual(flow["schema_version"], "flowpilot.route.v1")
        self.assertEqual(flow["source"], "pm_activates_reviewed_route")
        self.assertEqual(flow["nodes"], [{"node_id": "node-001"}])
        self.assertIn("flow.draft.json", flow["activated_from_draft_path"])
        self.assertTrue(flow["activated_from_draft_hash"])
        self.assertNotEqual(flow["nodes"][0].get("title"), "Current node")

    def test_route_check_results_require_router_delivered_check_cards(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.complete_material_flow(root)
        self.complete_root_contract_before_child_skill_gates(root)
        self.complete_child_skill_gates(root)
        self.deliver_expected_card(root, "pm.prior_path_context")
        self.deliver_expected_card(root, "pm.route_skeleton")
        router.record_external_event(
            root,
            "pm_writes_route_draft",
            {
                "nodes": [{"node_id": "node-001"}],
                **self.prior_path_context_review(root, "Route draft considered prior context before route checks."),
            },
        )

        with self.assertRaisesRegex(router.RouterError, "process_officer_route_check_card_delivered"):
            router.record_external_event(
                root,
                "process_officer_passes_route_check",
                self.role_report_envelope(
                    root,
                    "flowguard/route_process_check",
                    self.route_process_pass_body(),
                ),
            )
        self.deliver_expected_card(root, "process_officer.route_process_check")
        router.record_external_event(
            root,
            "process_officer_passes_route_check",
            self.role_report_envelope(
                root,
                "flowguard/route_process_check",
                self.route_process_pass_body(),
            ),
        )

        with self.assertRaisesRegex(router.RouterError, "product_officer_route_check_card_delivered"):
            router.record_external_event(
                root,
                "product_officer_passes_route_check",
                self.role_report_envelope(
                    root,
                    "flowguard/route_product_check",
                    self.route_product_pass_body(),
                ),
            )
        self.deliver_expected_card(root, "pm.process_route_model_decision")
        router.record_external_event(root, "pm_accepts_process_route_model", self.process_route_model_decision_body())
        self.deliver_expected_card(root, "product_officer.route_product_check")
        router.record_external_event(
            root,
            "product_officer_passes_route_check",
            self.role_report_envelope(
                root,
                "flowguard/route_product_check",
                self.route_product_pass_body(),
            ),
        )

        with self.assertRaisesRegex(router.RouterError, "reviewer_route_check_card_delivered"):
            router.record_external_event(
                root,
                "reviewer_passes_route_check",
                self.role_report_envelope(
                    root,
                    "reviews/route_challenge",
                    {"reviewed_by_role": "human_like_reviewer", "passed": True},
                ),
            )
        self.deliver_expected_card(root, "reviewer.route_challenge")
        router.record_external_event(
            root,
            "reviewer_passes_route_check",
            self.role_report_envelope(
                root,
                "reviews/route_challenge",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )

    def test_route_draft_requires_product_behavior_model_report(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.complete_material_flow(root)
        self.complete_root_contract_before_child_skill_gates(root)
        self.complete_child_skill_gates(root)
        (run_root / "flowguard" / "product_behavior_model.json").unlink()
        (run_root / "flowguard" / "product_architecture_modelability.json").unlink()

        self.deliver_expected_card(root, "pm.prior_path_context")
        self.deliver_expected_card(root, "pm.route_skeleton")
        with self.assertRaisesRegex(router.RouterError, "product behavior model report"):
            router.record_external_event(
                root,
                "pm_writes_route_draft",
                {
                    "nodes": [{"node_id": "node-001"}],
                    **self.prior_path_context_review(root, "Route draft attempted without product model."),
                },
            )

    def test_route_check_reports_require_hard_gate_verdict_fields(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.complete_material_flow(root)
        self.complete_root_contract_before_child_skill_gates(root)
        self.complete_child_skill_gates(root)
        self.deliver_expected_card(root, "pm.prior_path_context")
        self.deliver_expected_card(root, "pm.route_skeleton")
        router.record_external_event(
            root,
            "pm_writes_route_draft",
            {
                "nodes": [{"node_id": "node-001"}],
                **self.prior_path_context_review(root, "Route draft considered prior context before route checks."),
            },
        )

        self.deliver_expected_card(root, "process_officer.route_process_check")
        with self.assertRaisesRegex(router.RouterError, "process_viability_verdict=pass"):
            router.record_external_event(
                root,
                "process_officer_passes_route_check",
                self.role_report_envelope(
                    root,
                    "flowguard/route_process_check_missing_verdict",
                    {"reviewed_by_role": "process_flowguard_officer", "passed": True},
                ),
            )

        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.complete_material_flow(root)
        self.complete_root_contract_before_child_skill_gates(root)
        self.complete_child_skill_gates(root)
        self.deliver_expected_card(root, "pm.prior_path_context")
        self.deliver_expected_card(root, "pm.route_skeleton")
        router.record_external_event(
            root,
            "pm_writes_route_draft",
            {
                "nodes": [{"node_id": "node-001"}],
                **self.prior_path_context_review(root, "Route draft considered prior context before route checks."),
            },
        )
        self.deliver_expected_card(root, "process_officer.route_process_check")
        router.record_external_event(
            root,
            "process_officer_passes_route_check",
            self.role_report_envelope(root, "flowguard/route_process_check", self.route_process_pass_body()),
        )

        self.deliver_expected_card(root, "pm.process_route_model_decision")
        router.record_external_event(root, "pm_accepts_process_route_model", self.process_route_model_decision_body())
        self.deliver_expected_card(root, "product_officer.route_product_check")
        with self.assertRaisesRegex(router.RouterError, "route_model_review_verdict=pass"):
            router.record_external_event(
                root,
                "product_officer_passes_route_check",
                self.role_report_envelope(
                    root,
                    "flowguard/route_product_check_missing_verdict",
                    {"reviewed_by_role": "product_flowguard_officer", "passed": True},
                ),
            )

    def test_process_route_repair_required_blocks_activation_and_reopens_pm_route_draft(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.complete_material_flow(root)
        self.complete_root_contract_before_child_skill_gates(root)
        self.complete_child_skill_gates(root)
        self.deliver_expected_card(root, "pm.prior_path_context")
        self.deliver_expected_card(root, "pm.route_skeleton")
        router.record_external_event(
            root,
            "pm_writes_route_draft",
            {
                "nodes": [{"node_id": "node-001"}],
                **self.prior_path_context_review(root, "Route draft considered prior context before process check."),
            },
        )
        self.deliver_expected_card(root, "process_officer.route_process_check")
        router.record_external_event(
            root,
            "process_officer_requires_route_repair",
            self.role_report_envelope(
                root,
                "flowguard/route_process_repair_required",
                {
                    "reviewed_by_role": "process_flowguard_officer",
                    "passed": False,
                    "process_viability_verdict": "repair_required",
                    "product_behavior_model_checked": True,
                    "route_can_reach_product_model": False,
                    "repair_return_policy_checked": False,
                    "recommended_resolution": "PM should redraft route nodes to cover missing product-model recovery path.",
                    "blocking_findings": ["route cannot yet reach modeled recovery state"],
                },
            ),
        )

        with self.assertRaisesRegex(router.RouterError, "reviewer_route_check_passed"):
            router.record_external_event(root, "pm_activates_reviewed_route")
        state = read_json(router.run_state_path(self.run_root_for(root)))
        self.assertFalse(state["flags"]["route_draft_written_by_pm"])
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertIn("pm_writes_route_draft", action["allowed_external_events"])

    def test_route_mutation_requires_topology_and_resets_route_hard_gates(self) -> None:
        root = self.make_project()
        run_root, _packet_path, _result_path = self.prepare_current_node_result_for_review(
            root,
            packet_id="node-packet-route-hard-gate-mutation",
        )
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        self.close_model_miss_triage(root, output_name="decisions/route_hard_gate_mutation_triage")
        with self.assertRaisesRegex(router.RouterError, "topology_strategy"):
            router.record_external_event(
                root,
                "pm_mutates_route_after_review_block",
                {
                    "repair_node_id": "node-001-repair-hard-gate",
                    "reason": "missing_return_target",
                    "stale_evidence": ["node-packet-route-hard-gate-mutation"],
                    **self.prior_path_context_review(root, "Mutation intentionally lacks return target."),
                },
            )

        router.record_external_event(
            root,
            "pm_mutates_route_after_review_block",
            {
                "repair_node_id": "node-001-repair-hard-gate",
                "repair_return_to_node_id": "node-001",
                "reason": "reviewer_block",
                "stale_evidence": ["node-packet-route-hard-gate-mutation"],
                **self.prior_path_context_review(root, "Mutation includes mainline return target."),
            },
        )
        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"]["route_activated_by_pm"])
        self.assertTrue(state["flags"]["route_draft_written_by_pm"])
        self.assertFalse(state["flags"]["process_officer_route_check_passed"])
        mutation = read_json(run_root / "routes" / "route-001" / "mutations.json")["items"][-1]
        self.assertEqual(mutation["repair_return_policy"]["repair_return_to_node_id"], "node-001")
        self.assertEqual(mutation["route_topology"]["topology_strategy"], "return_to_original")

    def test_startup_waits_for_answers_before_banner_or_run_shell(self) -> None:
        root = self.make_project()

        self.assertEqual(self.next_and_apply(root)["applied"], "load_router")
        self.assertEqual(self.next_and_apply(root)["applied"], "ask_startup_questions")

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "record_startup_answers")
        self.assertTrue(action["requires_user"])
        self.assertEqual(action["requires_payload"], "startup_answers")
        self.assertEqual(action["payload_contract"]["schema_version"], "flowpilot.payload_contract.v1")
        self.assertIn("startup_answer_interpretation", " ".join(action["payload_contract"]["optional_fields"]))
        self.assert_payload_contract_mentions(
            action["payload_contract"],
            "startup_answer_interpretation.schema_version",
            "startup_answer_interpretation.raw_user_reply_text",
            "startup_answer_interpretation.interpreted_by",
            "startup_answer_interpretation.interpretation_provenance",
            "startup_answer_interpretation.ambiguity_status",
            "startup_answer_interpretation.interpreted_answers.background_agents",
            "startup_answer_interpretation.interpreted_answers.scheduled_continuation",
            "startup_answer_interpretation.interpreted_answers.display_surface",
            "flowpilot.startup_answer_interpretation.v1",
        )

        with self.assertRaises(router.RouterError):
            router.apply_action(root, "emit_startup_banner")
        with self.assertRaises(router.RouterError):
            router.apply_action(root, "create_run_shell")

        bootstrap = self.bootstrap_state(root)
        self.assertEqual(bootstrap["startup_state"], "awaiting_answers_stopped")
        self.assertEqual(bootstrap["bootstrap_scope"], "run_scoped")
        self.assertTrue(bootstrap["flags"]["startup_state_written_awaiting_answers"])
        self.assertTrue(bootstrap["flags"]["dialog_stopped_for_answers"])
        self.assertIsNone(bootstrap["startup_answers"])
        self.assertIsNotNone(bootstrap["run_id"])
        self.assertTrue((root / ".flowpilot" / "current.json").exists())
        self.assertTrue((root / bootstrap["run_root"] / "bootstrap" / "startup_state.json").exists())
        self.assertFalse((root / bootstrap["run_root"] / "router_state.json").exists())

    def test_startup_banner_action_and_result_are_user_visible(self) -> None:
        root = self.make_project()
        self.assertEqual(self.next_and_apply(root)["applied"], "load_router")
        self.assertEqual(self.next_and_apply(root)["applied"], "ask_startup_questions")
        self.assertEqual(router.next_action(root)["action_type"], "record_startup_answers")
        router.apply_action(root, "record_startup_answers", {"startup_answers": STARTUP_ANSWERS})

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "emit_startup_banner")
        self.assertTrue(action["display_required"])
        self.assertEqual(action["display_text_format"], "plain_text")
        self.assertTrue(action["controller_must_display_text_before_apply"])
        self.assertTrue(action["requires_user_dialog_display_confirmation"])
        self.assertEqual(action["required_render_target"], "user_dialog")
        self.assertEqual(action["requires_payload"], "display_confirmation")
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
        self.assertFalse(action["generated_files_alone_satisfy_chat_display"])
        self.assertIn("user dialog", action["controller_display_rule"])
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

        with self.assertRaisesRegex(router.RouterError, "display_confirmation"):
            router.apply_action(root, "emit_startup_banner")

        result = router.apply_action(root, "emit_startup_banner", self.payload_for_action(action))
        self.assertTrue(result["display_required"])
        self.assertTrue(result["controller_must_display_text_before_apply"])
        self.assertEqual(result["dialog_display_confirmation"]["rendered_to"], "user_dialog")
        self.assertFalse(result["generated_files_alone_satisfy_chat_display"])
        self.assertIn("FlowPilot", result["display_text"])
        self.assertIn("Developer: Yingxu Liu", result["display_text"])
        self.assertIn("Repository: https://github.com/liuyingxuvka/FlowPilot", result["display_text"])
        self.assertIn("Buy the developer a coffee: https://paypal.me/Yingxuliu", result["display_text"])
        self.assertNotIn("████", result["display_text"])
        self.assertNotIn("Formal run mode active.", result["display_text"])
        self.assertNotIn("Route-controlled execution has started.", result["display_text"])
        self.assertNotIn("Packets and ledgers are now in charge.", result["display_text"])
        self.assertNotIn("Startup answers are recorded.", result["display_text"])
        self.assertNotIn("display-only data", result["display_text"])
        self.assertNotIn("flowpilot_router.py", result["display_text"])

    def test_user_intake_requires_explicit_user_request_and_includes_it(self) -> None:
        root = self.make_project()
        while True:
            action = router.next_action(root)
            action_type = str(action["action_type"])
            if action_type == "record_startup_answers":
                router.apply_action(root, action_type, {"startup_answers": STARTUP_ANSWERS})
            elif action_type == "record_user_request":
                break
            else:
                router.apply_action(root, action_type, self.payload_for_action(action))

        inferred_request = {**USER_REQUEST, "provenance": "inferred_by_assistant"}
        with self.assertRaisesRegex(router.RouterError, "provenance=explicit_user_request"):
            router.apply_action(root, "record_user_request", {"user_request": inferred_request})

        router.apply_action(root, "record_user_request", {"user_request": USER_REQUEST})
        self.assertEqual(router.next_action(root)["action_type"], "write_user_intake")
        router.apply_action(root, "write_user_intake")

        run_root = root / self.bootstrap_state(root)["run_root"]
        body = (run_root / "packets" / "user_intake" / "packet_body.md").read_text(encoding="utf-8")
        body_payload = json.loads(body[body.index("{") :])
        self.assertEqual(body_payload["user_request"], USER_REQUEST)
        self.assertEqual(body_payload["startup_answers"], STARTUP_ANSWERS)
        self.assertTrue((run_root / "user_request.json").exists())

    def test_background_agents_allow_requires_six_fresh_live_agent_records(self) -> None:
        root = self.make_project()
        while True:
            action = router.next_action(root)
            action_type = str(action["action_type"])
            if action_type == "record_startup_answers":
                router.apply_action(root, action_type, {"startup_answers": STARTUP_ANSWERS})
            elif action_type == "record_user_request":
                router.apply_action(root, action_type, {"user_request": USER_REQUEST})
            elif action_type == "start_role_slots":
                break
            else:
                router.apply_action(root, action_type, self.payload_for_action(action))

        self.assertTrue(action["requires_host_spawn"])
        self.assertEqual(action["payload_contract"]["name"], "role_slots_startup_receipt")
        self.assert_payload_contract_mentions(
            action["payload_contract"],
            "role_agents[].role_key",
            "role_agents[].agent_id",
            "role_agents[].model_policy",
            "role_agents[].reasoning_effort_policy",
            "role_agents[].spawned_for_run_id",
            "role_agents[].spawned_after_startup_answers",
            "role_agents[].host_spawn_receipt.source_kind",
            "exactly one non-duplicate role agent record",
        )
        self.assertEqual(action["background_role_agent_model_policy"]["model_policy"], "strongest_available")
        self.assertEqual(
            action["background_role_agent_model_policy"]["reasoning_effort_policy"],
            "highest_available",
        )
        self.assertFalse(action["background_role_agent_model_policy"]["inherit_foreground_model_allowed"])
        self.assertEqual(
            {item["model_policy"] for item in action["role_spawn_request"]},
            {"strongest_available"},
        )
        self.assertEqual(
            {item["reasoning_effort_policy"] for item in action["role_spawn_request"]},
            {"highest_available"},
        )
        self.assertEqual(len(action["role_spawn_request"]), 6)
        with self.assertRaisesRegex(router.RouterError, "role_agents"):
            router.apply_action(root, "start_role_slots")

        payload = self.role_agent_payload(root)
        payload["role_agents"] = payload["role_agents"][:-1]
        with self.assertRaisesRegex(router.RouterError, "missing live role agent records"):
            router.apply_action(root, "start_role_slots", payload)

        payload = self.role_agent_payload(root)
        payload["role_agents"][0]["spawned_for_run_id"] = "run-old"
        with self.assertRaisesRegex(router.RouterError, "spawned_for_run_id"):
            router.apply_action(root, "start_role_slots", payload)

        router.apply_action(root, "start_role_slots", self.role_agent_payload(root))
        run_root = root / self.bootstrap_state(root)["run_root"]
        crew = read_json(run_root / "crew_ledger.json")
        self.assertEqual({slot["status"] for slot in crew["role_slots"]}, {"live_agent_started"})
        self.assertEqual({slot["spawn_result"] for slot in crew["role_slots"]}, {"spawned_fresh_for_task"})
        self.assertEqual({slot["model_policy"] for slot in crew["role_slots"]}, {"strongest_available"})
        self.assertEqual({slot["reasoning_effort_policy"] for slot in crew["role_slots"]}, {"highest_available"})
        role_io = read_json(run_root / "role_io_protocol_ledger.json")
        self.assertEqual(role_io["schema_version"], "flowpilot.role_io_protocol_ledger.v1")
        self.assertEqual(len(role_io["injection_receipts"]), 6)
        self.assertEqual({item["lifecycle_phase"] for item in role_io["injection_receipts"]}, {"fresh_spawn"})
        self.assertTrue(all((root / item["receipt_path"]).exists() for item in role_io["injection_receipts"]))

    def test_single_agent_answer_records_authorized_role_continuity_without_live_agents(self) -> None:
        root = self.make_project()
        answers = {**STARTUP_ANSWERS, "background_agents": "single-agent"}
        run_root = self.boot_to_controller(root, startup_answers=answers)
        crew = read_json(run_root / "crew_ledger.json")
        self.assertEqual({slot["status"] for slot in crew["role_slots"]}, {"single_agent_continuity_authorized"})
        self.assertEqual({slot["agent_id"] for slot in crew["role_slots"]}, {None})

    def test_startup_answer_resume_normalizes_old_stop_boundary_state(self) -> None:
        root = self.make_project()
        self.assertEqual(self.next_and_apply(root)["applied"], "load_router")
        self.assertEqual(self.next_and_apply(root)["applied"], "ask_startup_questions")

        state_path = router.bootstrap_state_path(root)
        bootstrap = read_json(state_path)
        bootstrap["flags"]["startup_state_written_awaiting_answers"] = False
        bootstrap["flags"]["dialog_stopped_for_answers"] = False
        bootstrap["startup_state"] = "asking_questions"
        bootstrap["pending_action"] = {
            "action_type": "stop_for_startup_answers",
            "label": "dialog_stopped_for_startup_answers",
        }
        state_path.write_text(json.dumps(bootstrap, indent=2, sort_keys=True), encoding="utf-8")

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "record_startup_answers")
        router.apply_action(root, "record_startup_answers", {"startup_answers": STARTUP_ANSWERS})
        self.assertEqual(router.next_action(root)["action_type"], "emit_startup_banner")

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
                        "background_agents": "allow",
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
                    "current_run_id": "run-old-stopped",
                    "current_run_root": ".flowpilot/runs/run-old-stopped",
                    "status": "stopped_by_user",
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        action = router.next_action(root, new_invocation=True)
        self.assertEqual(action["action_type"], "load_router")
        current = read_json(root / ".flowpilot" / "current.json")
        self.assertNotEqual(current["current_run_id"], "run-old-stopped")
        self.assertIn("/bootstrap/startup_state.json", current["startup_bootstrap_path"])
        bootstrap = self.bootstrap_state(root)
        self.assertEqual(bootstrap["bootstrap_scope"], "run_scoped")
        self.assertIsNone(bootstrap["startup_answers"])
        self.assertFalse(bootstrap["flags"]["startup_answers_recorded"])
        self.assertEqual(action["allowed_reads"], [current["startup_bootstrap_path"]])

    def test_record_startup_answers_rejects_naked_inferred_or_invalid_values(self) -> None:
        root = self.make_project()
        self.assertEqual(self.next_and_apply(root)["applied"], "load_router")
        self.assertEqual(self.next_and_apply(root)["applied"], "ask_startup_questions")
        self.assertEqual(router.next_action(root)["action_type"], "record_startup_answers")

        naked_answers = {key: value for key, value in STARTUP_ANSWERS.items() if key != "provenance"}
        with self.assertRaisesRegex(router.RouterError, "provenance=explicit_user_reply"):
            router.apply_action(root, "record_startup_answers", {"startup_answers": naked_answers})

        inferred_answers = {**STARTUP_ANSWERS, "provenance": "inferred_by_assistant"}
        with self.assertRaisesRegex(router.RouterError, "provenance=explicit_user_reply"):
            router.apply_action(root, "record_startup_answers", {"startup_answers": inferred_answers})

        prose_answers = {
            **STARTUP_ANSWERS,
            "background_agents": "No additional background subagents because the assistant inferred a default.",
        }
        with self.assertRaisesRegex(router.RouterError, "background_agents"):
            router.apply_action(root, "record_startup_answers", {"startup_answers": prose_answers})

        extra_answers = {**STARTUP_ANSWERS, "objective": "assistant-filled task summary"}
        with self.assertRaisesRegex(router.RouterError, "unsupported fields"):
            router.apply_action(root, "record_startup_answers", {"startup_answers": extra_answers})

        router.apply_action(root, "record_startup_answers", {"startup_answers": STARTUP_ANSWERS})
        bootstrap = self.bootstrap_state(root)
        self.assertEqual(bootstrap["startup_answers"], STARTUP_ANSWERS)

    def test_record_startup_answers_accepts_ai_interpretation_with_reviewer_receipt(self) -> None:
        root = self.make_project()
        self.assertEqual(self.next_and_apply(root)["applied"], "load_router")
        self.assertEqual(self.next_and_apply(root)["applied"], "ask_startup_questions")
        self.assertEqual(router.next_action(root)["action_type"], "record_startup_answers")

        with self.assertRaisesRegex(router.RouterError, "startup_answer_interpretation"):
            router.apply_action(root, "record_startup_answers", {"startup_answers": AI_INTERPRETED_STARTUP_ANSWERS})

        ambiguous_receipt = {**self.startup_answer_interpretation(), "ambiguity_status": "ambiguous"}
        with self.assertRaisesRegex(router.RouterError, "ambiguous startup answers"):
            router.apply_action(
                root,
                "record_startup_answers",
                {
                    "startup_answers": AI_INTERPRETED_STARTUP_ANSWERS,
                    "startup_answer_interpretation": ambiguous_receipt,
                },
            )

        router.apply_action(
            root,
            "record_startup_answers",
            {
                "startup_answers": AI_INTERPRETED_STARTUP_ANSWERS,
                "startup_answer_interpretation": self.startup_answer_interpretation(),
            },
        )
        bootstrap = self.bootstrap_state(root)
        self.assertEqual(bootstrap["startup_answers"], AI_INTERPRETED_STARTUP_ANSWERS)
        self.assertEqual(bootstrap["startup_answer_interpretation"]["raw_user_reply_text"], "Use background agents, manual resume, and chat route signs.")

        while router.next_action(root)["action_type"] != "record_user_request":
            action = router.next_action(root)
            router.apply_action(root, str(action["action_type"]), self.payload_for_action(action))
        run_root = self.run_root_for(root)
        startup_answers = read_json(run_root / "startup_answers.json")
        self.assertTrue(startup_answers["startup_answer_interpretation_path"].endswith("startup_answer_interpretation.json"))
        receipt = read_json(root / startup_answers["startup_answer_interpretation_path"])
        self.assertEqual(receipt["interpreted_answers"]["display_surface"], "chat")

    def test_cli_accepts_json_after_subcommand(self) -> None:
        parsed = router.parse_args(["--root", "C:/tmp/project", "next", "--json"])
        self.assertEqual(parsed.command, "next")
        self.assertTrue(parsed.json)

        parsed = router.parse_args(
            ["--root", "C:/tmp/project", "run-until-wait", "--new-invocation", "--json"]
        )
        self.assertEqual(parsed.command, "run-until-wait")
        self.assertTrue(parsed.new_invocation)
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

        parsed = router.parse_args(["--root", "C:/tmp/project", "reconcile-run", "--json"])
        self.assertEqual(parsed.command, "reconcile-run")
        self.assertTrue(parsed.json)

    def test_retired_high_risk_fold_commands_are_not_cli_commands(self) -> None:
        for command in (
            "deliver-card-bundle-checked",
            "relay-checked",
            "prepare-startup-fact-check",
            "record-role-output-checked",
        ):
            with self.assertRaises(SystemExit):
                with contextlib.redirect_stderr(io.StringIO()):
                    router.parse_args(["--root", "C:/tmp/project", command, "--json"])

    def test_role_output_envelope_writes_body_and_keeps_controller_visible_payload_sealed(self) -> None:
        root = self.make_project()
        envelope = router.write_role_output_envelope(
            root,
            output_path="role_outputs/route_process_check.json",
            body={"reviewed_by_role": "process_flowguard_officer", "passed": True},
            event_name="process_officer_passes_route_check",
            from_role="process_flowguard_officer",
        )

        self.assertEqual(envelope["schema_version"], "flowpilot.role_output_envelope.v1")
        self.assertEqual(envelope["controller_visibility"], "role_output_envelope_only")
        self.assertFalse(envelope["chat_response_body_allowed"])
        self.assertNotIn("passed", envelope)
        loaded = router._load_file_backed_role_payload(root, envelope)
        self.assertTrue(loaded["passed"])
        self.assertEqual(loaded["_role_output_envelope"]["body_path_key"], "report_path")

    def test_role_output_envelope_hash_survives_same_path_envelope_rewrite(self) -> None:
        root = self.make_project()
        body_path = root / "role_outputs" / "same_path_report.json"
        body = {"reviewed_by_role": "human_like_reviewer", "passed": True}
        router.write_json(body_path, body)
        raw_hash = hashlib.sha256(body_path.read_bytes()).hexdigest()

        loaded = router._load_file_backed_role_payload(
            root,
            {
                "report_path": self.rel(root, body_path),
                "report_hash": raw_hash,
                "controller_visibility": "role_output_envelope_only",
            },
        )
        router.write_json(body_path, loaded)

        reloaded = router._load_file_backed_role_payload(
            root,
            {
                "report_path": self.rel(root, body_path),
                "report_hash": raw_hash,
                "controller_visibility": "role_output_envelope_only",
            },
        )
        self.assertTrue(reloaded["passed"])
        self.assertEqual(
            reloaded["_role_output_envelope"]["body_hash"],
            loaded["_role_output_envelope"]["body_hash"],
        )

    def test_pm_material_understanding_accepts_file_backed_memo_payload(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        self.complete_material_flow(
            root,
            self.role_output_envelope(
                root,
                "pm/material_understanding",
                {
                    "material_summary": "file backed material understanding",
                    "route_consequences": ["continue route construction"],
                },
                path_key="memo_path",
                hash_key="memo_hash",
            ),
        )

        memo = read_json(run_root / "pm_material_understanding.json")
        self.assertEqual(memo["material_summary"], "file backed material understanding")
        self.assertEqual(memo["route_consequences"], ["continue route construction"])
        self.assertEqual(memo["_role_output_envelope"]["body_path_key"], "memo_path")
        self.assertTrue((run_root / "material" / "pm_material_understanding_payload.json").exists())

    def test_phase_card_delivery_context_includes_required_upstream_sources(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.complete_material_flow(root)

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "deliver_system_card")
        self.assertEqual(action["card_id"], "pm.product_architecture")
        context = action["delivery_context"]
        self.assertEqual(context["current_stage"]["current_phase"], "product_architecture")
        source_values = set(context["source_paths"].values())
        self.assertIn(f"{run_root.relative_to(root).as_posix()}/pm_material_understanding.json", source_values)
        self.assertIn(f"{run_root.relative_to(root).as_posix()}/material/pm_material_understanding_payload.json", source_values)

        self.ack_system_card_action(root, action)
        router.record_external_event(
            root,
            "pm_writes_product_function_architecture",
            {
                "user_task_map": [{"task_id": "task-001", "goal": "complete the requested project"}],
                "product_capability_map": [{"capability_id": "cap-001", "behavior": "complete requested work"}],
                "feature_decisions": [{"feature_id": "feature-001", "decision": "must"}],
                "highest_achievable_product_target": {"product_vision": "professional completion"},
                "semantic_fidelity_policy": {"silent_downgrade_forbidden": True},
                "functional_acceptance_matrix": [{"acceptance_id": "root-001"}],
            },
        )
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "product_officer.product_architecture_modelability")
        context = action["delivery_context"]
        self.assertEqual(context["current_stage"]["current_phase"], "product_architecture")
        self.assertIn(
            f"{run_root.relative_to(root).as_posix()}/product_function_architecture.json",
            set(context["source_paths"].values()),
        )

    def test_system_card_delivery_requires_manifest_check(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        first = self.next_after_display_sync(root)
        self.assertEqual(first["action_type"], "confirm_controller_core_boundary")
        self.assertEqual(first["next_step_contract"]["recipient_role"], "controller")
        router.apply_action(root, "confirm_controller_core_boundary")

        first = self.next_after_display_sync(root)
        self.assertEqual(first["action_type"], "write_startup_mechanical_audit")
        router.apply_action(root, "write_startup_mechanical_audit")

        first = self.next_after_display_sync(root)
        self.assertEqual(first["action_type"], "write_display_surface_status")
        router.apply_action(root, "write_display_surface_status", self.payload_for_action(first))

        first = self.next_after_display_sync(root)
        self.assertEqual(first["action_type"], "check_prompt_manifest")
        self.assertEqual(first["next_card_id"], "reviewer.startup_fact_check")
        self.assertTrue(first["next_step_contract"]["controller_has_explicit_next"])
        self.assertEqual(first["next_step_contract"]["recipient_role"], "human_like_reviewer")
        router.apply_action(root, "check_prompt_manifest")

        second = self.next_after_display_sync(root)
        self.assertEqual(second["action_type"], "deliver_system_card")
        self.assertEqual(second["card_id"], "reviewer.startup_fact_check")
        self.assertEqual(second["next_step_contract"]["recipient_role"], "human_like_reviewer")
        self.assertEqual(second["from"], "system")
        self.assertEqual(second["issued_by"], "router")
        self.assertEqual(second["delivered_by"], "controller")
        self.assertEqual(second["resource_lifecycle"], "committed_artifact")
        self.assertTrue(second["artifact_committed"])
        self.assertTrue(second["artifact_exists"])
        self.assertTrue(second["artifact_hash_verified"])
        self.assertTrue(second["ledger_recorded"])
        self.assertTrue(second["return_wait_recorded"])
        self.assertTrue(second["relay_allowed"])
        self.assertFalse(second["apply_required"])
        self.assertEqual(second["card_return_event"], "reviewer_card_ack")
        self.assertNotIn("return_event", second)
        self.assertEqual(second["card_checkin_instruction"]["command_name"], "receive-card")
        self.assertEqual(second["card_checkin_instruction"]["card_return_event"], "reviewer_card_ack")
        self.assertEqual(second["card_checkin_instruction"]["ack_submission_mode"], "direct_to_router")
        self.assertFalse(second["card_checkin_instruction"]["controller_ack_handoff_allowed"])
        self.assertEqual(second["ack_submission_mode"], "direct_to_router")
        self.assertFalse(second["controller_ack_handoff_allowed"])
        self.assertTrue(second["direct_router_ack_token_hash"])
        self.assertTrue(second["card_checkin_instruction"]["do_not_handwrite_ack"])
        self.assertIn("--envelope-path", second["card_checkin_instruction"]["command"])
        self.assertTrue(second["auto_committed_by_router"])
        self.assertEqual(second["next_step_contract"]["resource_lifecycle"], "committed_artifact")
        self.assertTrue(second["next_step_contract"]["artifact_committed"])
        self.assertTrue(second["next_step_contract"]["relay_allowed"])
        self.assertFalse(second["next_step_contract"]["apply_required"])
        self.assertTrue((root / second["card_envelope_path"]).exists())
        envelope = read_json(root / second["card_envelope_path"])
        self.assertEqual(envelope["card_return_event"], "reviewer_card_ack")
        self.assertEqual(envelope["card_checkin_instruction"]["command_name"], "receive-card")
        self.assertEqual(envelope["direct_router_ack_token"]["submission_mode"], "direct_to_router")
        self.assertFalse(envelope["direct_router_ack_token"]["controller_ack_handoff_allowed"])
        self.assertNotIn("return_event", envelope)
        pre_apply_state = read_json(run_root / "router_state.json")
        pre_apply_prompt_ledger = read_json(run_root / "prompt_delivery_ledger.json")
        self.assertEqual(pre_apply_state["prompt_deliveries"], 1)
        self.assertEqual(pre_apply_prompt_ledger["deliveries"][0]["card_id"], "reviewer.startup_fact_check")
        context = second["delivery_context"]
        self.assertEqual(context["schema_version"], "flowpilot.live_card_context.v1")
        self.assertEqual(context["run_id"], run_root.name)
        self.assertEqual(context["card_id"], "reviewer.startup_fact_check")
        self.assertEqual(context["to_role"], "human_like_reviewer")
        self.assertEqual(context["current_task"]["user_request_path"], f"{run_root.relative_to(root).as_posix()}/user_request.json")
        self.assertFalse(context["current_task"]["controller_summary_is_task_authority"])
        self.assertIn("current_phase", context["current_stage"])
        self.assertIn("current_node_id", context["current_stage"])
        self.assertEqual(context["source_paths"]["execution_frontier"], f"{run_root.relative_to(root).as_posix()}/execution_frontier.json")
        self.assertEqual(context["source_paths"]["prompt_delivery_ledger"], f"{run_root.relative_to(root).as_posix()}/prompt_delivery_ledger.json")
        self.assertEqual(context["source_paths"]["display_surface"], f"{run_root.relative_to(root).as_posix()}/display/display_surface.json")
        self.assertTrue(second["reviewer_has_direct_display_evidence"])

        state = read_json(run_root / "router_state.json")
        prompt_ledger = read_json(run_root / "prompt_delivery_ledger.json")
        self.assertTrue(state["flags"]["reviewer_startup_fact_check_card_delivered"])
        self.assertEqual(state["manifest_checks"], 1)
        self.assertEqual(state["prompt_deliveries"], 1)
        self.assertEqual(state["delivered_cards"][0]["card_id"], "reviewer.startup_fact_check")
        self.assertEqual(state["delivered_cards"][0]["delivery_context"]["card_id"], "reviewer.startup_fact_check")
        self.assertEqual(prompt_ledger["deliveries"][0]["delivery_context"]["card_id"], "reviewer.startup_fact_check")
        self.assertEqual(second["delivery_mode"], "envelope_only_v2")
        self.assertEqual(second["controller_visibility"], "system_card_envelope_only")
        self.assertFalse(second["sealed_body_reads_allowed"])
        self.assertNotIn(second["body_path"], second["allowed_reads"])
        self.assertEqual(second["role_io_protocol_hash"], read_json(run_root / "role_io_protocol_ledger.json")["protocol_hash"])
        self.assertTrue((root / second["role_io_protocol_receipt_path"]).exists())
        self.assertTrue((root / second["card_envelope_path"]).exists())
        card_ledger = read_json(run_root / "card_ledger.json")
        return_ledger = read_json(run_root / "return_event_ledger.json")
        self.assertEqual(card_ledger["deliveries"][0]["card_id"], "reviewer.startup_fact_check")
        self.assertEqual(card_ledger["deliveries"][0]["role_io_protocol_receipt_hash"], second["role_io_protocol_receipt_hash"])
        self.assertEqual(return_ledger["pending_returns"][0]["card_return_event"], "reviewer_card_ack")
        self.assertNotIn("return_event", return_ledger["pending_returns"][0])

        with self.assertRaisesRegex(router.RouterError, "relay-only"):
            router.apply_action(root, "deliver_system_card")
        relay_action = self.next_after_display_sync(root)
        self.assertEqual(relay_action["action_type"], "deliver_system_card")
        self.assertEqual(relay_action["card_envelope_path"], second["card_envelope_path"])
        self.assertTrue(relay_action["relay_allowed"])
        with self.assertRaisesRegex(router.RouterError, "unresolved card return"):
            router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        with self.assertRaisesRegex(router.RouterError, "legacy record-event ACK path is disabled"):
            router.record_external_event(root, "reviewer_card_ack")

        open_result = card_runtime.open_card(
            root,
            envelope_path=str(second["card_envelope_path"]),
            role="human_like_reviewer",
            agent_id=str(second["target_agent_id"]),
        )
        card_runtime.submit_card_ack(
            root,
            envelope_path=str(second["card_envelope_path"]),
            role="human_like_reviewer",
            agent_id=str(second["target_agent_id"]),
            receipt_paths=[str(open_result["read_receipt_path"])],
        )
        with self.assertRaisesRegex(router.RouterError, "legacy record-event ACK path is disabled"):
            router.record_external_event(root, "reviewer_card_ack")
        next_action = self.next_after_display_sync(root)
        self.assertNotEqual(next_action["action_type"], "check_card_return_event")
        return_ledger = read_json(run_root / "return_event_ledger.json")
        self.assertEqual(return_ledger["pending_returns"][0]["status"], "resolved")

    def test_committed_system_card_relay_can_resolve_without_apply_roundtrip(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "confirm_controller_core_boundary")
        router.apply_action(root, "confirm_controller_core_boundary")

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "write_startup_mechanical_audit")
        router.apply_action(root, "write_startup_mechanical_audit")

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "write_display_surface_status")
        router.apply_action(root, "write_display_surface_status", self.payload_for_action(action))

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "check_prompt_manifest")
        router.apply_action(root, "check_prompt_manifest")

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "deliver_system_card")
        self.assertEqual(action["card_id"], "reviewer.startup_fact_check")
        self.assertTrue(action["artifact_committed"])
        self.assertTrue(action["relay_allowed"])
        self.assertFalse(action["apply_required"])
        self.assertEqual(action["card_return_event"], "reviewer_card_ack")

        open_result = card_runtime.open_card(
            root,
            envelope_path=str(action["card_envelope_path"]),
            role="human_like_reviewer",
            agent_id=str(action["target_agent_id"]),
        )
        card_runtime.submit_card_ack(
            root,
            envelope_path=str(action["card_envelope_path"]),
            role="human_like_reviewer",
            agent_id=str(action["target_agent_id"]),
            receipt_paths=[str(open_result["read_receipt_path"])],
        )

        next_action = self.next_after_display_sync(root)
        return_ledger = read_json(run_root / "return_event_ledger.json")
        self.assertEqual(return_ledger["pending_returns"][0]["status"], "resolved")
        self.assertNotEqual(next_action["action_type"], "check_card_return_event")

        duplicate_open = card_runtime.open_card(
            root,
            envelope_path=str(action["card_envelope_path"]),
            role="human_like_reviewer",
            agent_id=str(action["target_agent_id"]),
        )
        card_runtime.submit_card_ack(
            root,
            envelope_path=str(action["card_envelope_path"]),
            role="human_like_reviewer",
            agent_id=str(action["target_agent_id"]),
            receipt_paths=[str(duplicate_open["read_receipt_path"])],
        )
        return_ledger = read_json(run_root / "return_event_ledger.json")
        self.assertEqual(return_ledger["pending_returns"][0]["status"], "resolved")
        self.assertEqual(return_ledger["pending_returns"][0]["terminal_replay_ack"]["count"], 1)
        self.assertIsNone(
            router._pending_card_return_blocker_for_event(
                run_root,
                run_root.name,
                "pm_issues_material_and_capability_scan_packets",
            )
        )

    def test_initial_pm_system_cards_are_delivered_as_same_role_bundle(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        self.deliver_startup_fact_check_card(root)

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "check_prompt_manifest")
        self.assertTrue(action["bundle_candidate"])
        expected_card_ids = [
            "pm.core",
            "pm.output_contract_catalog",
            "pm.role_work_request",
            "pm.phase_map",
            "pm.startup_intake",
        ]
        self.assertEqual(action["bundle_card_ids"], expected_card_ids)
        router.apply_action(root, "check_prompt_manifest")

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "deliver_system_card_bundle")
        self.assertEqual(action["card_ids"], expected_card_ids)
        self.assertEqual(action["to_role"], "project_manager")
        self.assertEqual(action["controller_visibility"], "system_card_bundle_envelope_only")
        self.assertTrue(action["artifact_committed"])
        self.assertTrue(action["relay_allowed"])
        self.assertFalse(action["apply_required"])
        self.assertEqual(action["card_checkin_instruction"]["command_name"], "receive-card-bundle")
        self.assertEqual(action["card_checkin_instruction"]["card_return_event"], "pm_card_bundle_ack")
        self.assertTrue((root / action["card_bundle_envelope_path"]).exists())
        envelope = read_json(root / action["card_bundle_envelope_path"])
        self.assertEqual(envelope["schema_version"], card_runtime.CARD_BUNDLE_ENVELOPE_SCHEMA)
        self.assertEqual(envelope["card_ids"], expected_card_ids)
        self.assertEqual(envelope["card_return_event"], "pm_card_bundle_ack")
        self.assertEqual(envelope["card_checkin_instruction"]["command_name"], "receive-card-bundle")
        self.assertEqual(len(envelope["cards"]), 5)

        self.ack_system_card_bundle_action(root, action)

        state = read_json(run_root / "router_state.json")
        for card_id in expected_card_ids:
            entry = next(entry for entry in router.SYSTEM_CARD_SEQUENCE if entry["card_id"] == card_id)
            self.assertTrue(state["flags"][entry["flag"]])
        self.assertEqual(state["prompt_deliveries"], 6)
        return_ledger = read_json(run_root / "return_event_ledger.json")
        bundle_records = [
            item for item in return_ledger["pending_returns"]
            if isinstance(item, dict) and item.get("return_kind") == "system_card_bundle"
        ]
        self.assertEqual(bundle_records[0]["status"], "resolved")
        next_action = self.next_after_display_sync(root)
        self.assertEqual(next_action["action_type"], "check_packet_ledger")
        self.assertEqual(next_action["next_mail_id"], "user_intake")

    def test_incomplete_system_card_bundle_ack_waits_for_missing_receipts_then_recovers(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        self.deliver_startup_fact_check_card(root)
        manifest_action = self.next_after_display_sync(root)
        self.assertEqual(manifest_action["action_type"], "check_prompt_manifest")
        router.apply_action(root, "check_prompt_manifest")
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "deliver_system_card_bundle")
        role = str(action["to_role"])
        agent_id = str(action["target_agent_id"])
        opened = card_runtime.open_card_bundle(
            root,
            envelope_path=str(action["card_bundle_envelope_path"]),
            role=role,
            agent_id=agent_id,
        )
        envelope_path = root / action["card_bundle_envelope_path"]
        envelope = read_json(envelope_path)
        first_three_receipts = opened["read_receipt_paths"][:-1]
        receipt_refs = []
        for receipt_path in first_three_receipts:
            receipt = read_json(root / receipt_path)
            receipt_refs.append(
                {
                    "receipt_path": receipt_path,
                    "receipt_hash": receipt["receipt_hash"],
                    "card_id": receipt["card_id"],
                    "delivery_id": receipt["delivery_id"],
                    "delivery_attempt_id": receipt["delivery_attempt_id"],
                    "card_hash": receipt["card_hash"],
                    "opened_at": receipt["opened_at"],
                }
            )
        incomplete_ack = {
            "schema_version": card_runtime.CARD_BUNDLE_ACK_ENVELOPE_SCHEMA,
            "run_id": envelope["run_id"],
            "resume_tick_id": envelope["resume_tick_id"],
            "role_key": role,
            "agent_id": agent_id,
            "card_return_event": envelope["card_return_event"],
            "status": "acknowledged",
            "card_bundle_id": envelope["bundle_id"],
            "card_bundle_envelope_path": action["card_bundle_envelope_path"],
            "card_bundle_envelope_hash": card_runtime.stable_json_hash(envelope),
            "ack_delivery_mode": "direct_to_router",
            "submitted_to": "router",
            "controller_ack_handoff_used": False,
            "direct_router_ack_token": envelope["direct_router_ack_token"],
            "direct_router_ack_token_hash": envelope["direct_router_ack_token_hash"],
            "acknowledged_bundle": envelope["bundle_id"],
            "acknowledged_envelopes": [envelope["bundle_id"]],
            "member_card_ids": envelope["card_ids"][:-1],
            "receipt_refs": receipt_refs,
            "body_visibility": "ack_envelope_only",
            "contains_card_body": False,
            "runtime_validates_mechanics_only": True,
            "semantic_understanding_validated": False,
            "returned_at": card_runtime.utc_now(),
        }
        incomplete_ack["ack_hash"] = card_runtime.stable_json_hash(incomplete_ack)
        router.write_json(root / action["expected_return_path"], incomplete_ack)

        wait_action = self.next_after_display_sync(root)
        return_ledger = read_json(run_root / "return_event_ledger.json")
        bundle_pending = [
            item for item in return_ledger["pending_returns"]
            if isinstance(item, dict) and item.get("return_kind") == "system_card_bundle"
        ][0]
        self.assertEqual(bundle_pending["status"], "bundle_ack_incomplete")
        self.assertEqual(bundle_pending["missing_card_ids"], [opened["cards"][-1]["card_id"]])
        self.assertEqual(wait_action["action_type"], "await_card_bundle_return_event")
        self.assertTrue(wait_action["bundle_ack_incomplete"])
        self.assertEqual(wait_action["missing_card_ids"], [opened["cards"][-1]["card_id"]])

        card_runtime.submit_card_bundle_ack(
            root,
            envelope_path=str(action["card_bundle_envelope_path"]),
            role=role,
            agent_id=agent_id,
            receipt_paths=[str(path) for path in opened["read_receipt_paths"]],
        )
        next_action = self.next_after_display_sync(root)
        return_ledger = read_json(run_root / "return_event_ledger.json")
        bundle_pending = [
            item for item in return_ledger["pending_returns"]
            if isinstance(item, dict) and item.get("return_kind") == "system_card_bundle"
        ][0]
        self.assertEqual(bundle_pending["status"], "resolved")
        self.assertEqual(next_action["action_type"], "check_packet_ledger")

    def test_user_intake_mail_requires_packet_ledger_check_after_pm_cards(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        self.deliver_startup_fact_check_card(root)
        self.deliver_expected_card(root, "pm.core")
        self.deliver_expected_card(root, "pm.output_contract_catalog")
        self.deliver_expected_card(root, "pm.role_work_request")
        self.deliver_expected_card(root, "pm.phase_map")
        self.deliver_expected_card(root, "pm.startup_intake")

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "check_packet_ledger")
        self.assertEqual(action["next_mail_id"], "user_intake")
        router.apply_action(root, "check_packet_ledger")

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "deliver_mail")
        self.assertEqual(action["mail_id"], "user_intake")
        router.apply_action(root, "deliver_mail")

        state = read_json(run_root / "router_state.json")
        packet_ledger = read_json(run_root / "packet_ledger.json")
        self.assertTrue(state["flags"]["user_intake_delivered_to_pm"])
        self.assertEqual(state["ledger_checks"], 1)
        self.assertEqual(state["mail_deliveries"], 1)
        self.assertEqual(packet_ledger["mail"][0]["mail_id"], "user_intake")
        self.assertEqual(packet_ledger["schema_version"], packet_runtime.PACKET_LEDGER_SCHEMA)

    def test_startup_activation_requires_reviewer_facts_before_work(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.deliver_startup_fact_check_card(root)
        self.deliver_initial_pm_cards_and_user_intake(root)

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_issues_material_and_capability_scan_packets")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_activates_reviewed_route")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_approves_startup_activation", {"decision": "approved"})

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_first_decision_resets_controller")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "controller_role_confirmed_from_pm_reset")
        boundary = read_json(run_root / "startup" / "controller_boundary_confirmation.json")
        self.assertEqual(boundary["event"], "controller_role_confirmed_from_router_core")
        self.assertFalse(boundary["sealed_body_reads_allowed"])

        self.assertTrue((run_root / "display" / "display_surface.json").exists())
        startup_audit = read_json(run_root / "startup" / "startup_mechanical_audit.json")
        self.assertTrue(startup_audit["mechanical_checks_passed"])
        self.assertFalse(startup_audit["self_attested_ai_claims_accepted_as_proof"])
        self.assertEqual(startup_audit["router_replacement_scope"], "mechanical_only")
        proof_path = root / startup_audit["router_owned_check_proof_path"]
        self.assertTrue(proof_path.exists())
        proof = read_json(proof_path)
        self.assertEqual(proof["source_kind"], "router_computed")
        self.assertFalse(proof["self_attested_ai_claims_accepted_as_proof"])

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "reviewer_reports_startup_facts", {"passed": True})
        with self.assertRaisesRegex(router.RouterError, "file-backed body path"):
            router.record_external_event(
                root,
                "reviewer_reports_startup_facts",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            )
        self.assertTrue(self.handle_pending_control_blocker(root))
        router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(
                root,
                "startup/reviewer_startup_fact_report",
                self.startup_fact_report_body(root),
            ),
        )
        self.assertTrue((run_root / "startup" / "startup_fact_report.json").exists())
        fact_report = read_json(run_root / "startup" / "startup_fact_report.json")
        self.assertEqual(fact_report["startup_mechanical_audit_hash"], hashlib.sha256((run_root / "startup" / "startup_mechanical_audit.json").read_bytes()).hexdigest())
        self.assertNotIn("router_mechanical_audit_hash", fact_report["external_fact_review"])

        self.deliver_expected_card(root, "pm.startup_activation")

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_approves_startup_activation", {"decision": "blocked"})
        with self.assertRaisesRegex(router.RouterError, "file-backed body path"):
            router.record_external_event(root, "pm_approves_startup_activation", {"decision": "approved"})
        self.assertTrue(self.handle_pending_control_blocker(root))
        router.record_external_event(
            root,
            "pm_approves_startup_activation",
            self.role_decision_envelope(
                root,
                "startup/pm_startup_activation",
                {"approved_by_role": "project_manager", "decision": "approved"},
            ),
        )

        self.assertTrue((run_root / "startup" / "startup_activation.json").exists())
        self.assertTrue((run_root / "display" / "display_surface.json").exists())
        self.assertTrue((run_root / "diagrams" / "current_route_sign.md").exists())
        self.assertTrue((run_root / "diagrams" / "user-flow-diagram.md").exists())
        self.assertTrue((run_root / "diagrams" / "user-flow-diagram.mmd").exists())
        route_sign_markdown = (run_root / "diagrams" / "current_route_sign.md").read_text(encoding="utf-8")
        self.assertIn("```mermaid", route_sign_markdown)
        self.assertNotIn("Display gate:", route_sign_markdown)
        self.assertNotIn("Chat evidence:", route_sign_markdown)
        display_surface = read_json(run_root / "display" / "display_surface.json")
        self.assertTrue(display_surface["chat_displayed_by_controller"])
        self.assertEqual(display_surface["selected_surface"], "chat_route_sign")
        self.assertFalse(display_surface["generated_files_alone_satisfy_chat_display"])

        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["pm_material_packets_issued"])

    def test_reviewer_startup_findings_go_to_pm_without_control_blocker(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.deliver_startup_fact_check_card(root)
        self.deliver_initial_pm_cards_and_user_intake(root)

        block_body = self.startup_fact_report_body(root)
        block_body.update(
            {
                "passed": False,
                "checks": {"startup_user_answer_authenticity": False},
                "blockers": ["startup_user_answer_authenticity"],
            }
        )
        router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(
                root,
                "startup/reviewer_startup_fact_block",
                block_body,
            ),
        )
        report = read_json(run_root / "startup" / "startup_fact_report.json")
        self.assertFalse(report["passed"])
        self.assertEqual(report["status"], "findings")
        self.assertTrue(report["requires_pm_startup_decision"])
        self.assertFalse(report["reviewer_directly_blocks_route"])
        state = read_json(router.run_state_path(run_root))
        self.assertIsNone(state["active_control_blocker"])

        self.deliver_expected_card(root, "pm.startup_activation")
        with self.assertRaisesRegex(router.RouterError, "accepts_startup_findings_with_reason"):
            router.record_external_event(
                root,
                "pm_approves_startup_activation",
                self.role_decision_envelope(
                    root,
                    "startup/pm_startup_activation_after_block",
                    {"approved_by_role": "project_manager", "decision": "approved"},
                ),
            )

        router.record_external_event(
            root,
            "pm_declares_startup_protocol_dead_end",
            self.role_decision_envelope(
                root,
                "startup/pm_startup_protocol_dead_end",
                {
                    "declared_by_role": "project_manager",
                    "decision": "protocol_dead_end",
                    "no_legal_repair_path": True,
                    "why_no_existing_path_applies": "No startup repair event can safely represent this synthetic test block.",
                    "attempted_legal_paths": ["pm_requests_startup_repair", "reviewer_reports_startup_facts"],
                    "unsafe_to_continue_reason": "PM cannot open startup from a blocking reviewer report.",
                    "resume_conditions": ["Add or select a legal startup repair path, then restart startup fact review."],
                },
            ),
        )
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "write_terminal_summary")
        self.assertEqual(action["read_scope"], router.TERMINAL_SUMMARY_READ_SCOPE)
        self.assertIn(f"{self.rel(root, run_root)}/**", action["allowed_reads"])
        self.assertEqual(action["run_lifecycle_status"], "protocol_dead_end")
        self.apply_terminal_summary(root, action, run_root, note="Startup protocol dead end.")
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "run_lifecycle_terminal")
        self.assertEqual(action["run_lifecycle_status"], "protocol_dead_end")
        lifecycle = read_json(run_root / "lifecycle" / "run_lifecycle.json")
        self.assertEqual(lifecycle["status"], "protocol_dead_end")
        dead_end = read_json(run_root / "lifecycle" / "startup_protocol_dead_end.json")
        self.assertTrue(dead_end["effects"]["cancel_or_suspend_pending_mail"])
        self.assertFalse(dead_end["effects"]["heartbeat_should_stop"])
        self.assertTrue(dead_end["effects"]["heartbeat_should_remain_for_resume_or_user_decision"])

    def test_pm_can_approve_startup_findings_with_file_backed_decision(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.deliver_startup_fact_check_card(root)
        self.deliver_initial_pm_cards_and_user_intake(root)

        findings_body = self.startup_fact_report_body(root)
        findings_body.update(
            {
                "passed": False,
                "checks": {"startup_user_answer_authenticity": False},
                "blockers": ["startup_user_answer_authenticity"],
            }
        )
        router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(root, "startup/reviewer_startup_fact_findings", findings_body),
        )
        self.deliver_expected_card(root, "pm.startup_activation")

        router.record_external_event(
            root,
            "pm_approves_startup_activation",
            self.role_decision_envelope(
                root,
                "startup/pm_startup_activation_findings_decision",
                {
                    "approved_by_role": "project_manager",
                    "decision": "approved",
                    "reviewed_report_path": self.rel(root, run_root / "startup" / "startup_fact_report.json"),
                    "accepts_startup_findings_with_reason": True,
                    "startup_findings_decision": "unreviewable_requirement_demoted",
                    "startup_findings_decision_reason": "The router task contract is the startup-answer authority; original chat authenticity is not independently reviewable by this role.",
                    "demoted_unreviewable_requirement_ids": ["startup_user_answer_authenticity"],
                },
            ),
        )
        activation = read_json(run_root / "startup" / "startup_activation.json")
        self.assertEqual(activation["approval_basis"], "pm_file_backed_findings_decision")
        self.assertEqual(
            activation["pm_findings_decision"]["startup_findings_decision"],
            "unreviewable_requirement_demoted",
        )

    def test_pm_startup_repair_request_resets_fact_review_cycle(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.deliver_startup_fact_check_card(root)
        self.deliver_initial_pm_cards_and_user_intake(root)

        block_body = self.startup_fact_report_body(root)
        block_body.update(
            {
                "passed": False,
                "checks": {"startup_user_answer_authenticity": False},
                "blockers": ["startup_user_answer_authenticity"],
            }
        )
        router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(root, "startup/reviewer_startup_fact_block", block_body),
        )
        self.deliver_expected_card(root, "pm.startup_activation")

        router.record_external_event(
            root,
            "pm_requests_startup_repair",
            self.role_decision_envelope(
                root,
                "startup/pm_startup_repair_request",
                {
                    "decided_by_role": "project_manager",
                    "decision": "startup_repair_requested",
                    "repair_target_kind": "system",
                    "target_role_or_system": "flowpilot_router",
                    "repair_action": "rewrite_startup_mechanical_audit_and_reissue_reviewer_fact_check",
                    "blocked_report_path": self.rel(root, run_root / "startup" / "startup_fact_report.json"),
                    "resume_event": "reviewer_reports_startup_facts",
                    "resume_condition": "Router rewrites the audit and reviewer files a fresh startup fact report.",
                },
            ),
        )
        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"]["startup_fact_reported"])
        self.assertFalse(state["flags"]["reviewer_startup_fact_check_card_delivered"])
        self.assertFalse(state["flags"]["pm_startup_activation_card_delivered"])
        self.assertTrue((run_root / "startup" / "startup_repair_request.json").exists())

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "write_startup_mechanical_audit")
        router.apply_action(root, "write_startup_mechanical_audit")
        self.deliver_expected_card(root, "reviewer.startup_fact_check")

    def test_pm_startup_repair_request_can_repeat_for_new_blocking_report(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.deliver_startup_fact_check_card(root)
        self.deliver_initial_pm_cards_and_user_intake(root)

        def submit_blocking_report(name: str, blocker: str) -> None:
            block_body = self.startup_fact_report_body(root)
            block_body.update(
                {
                    "passed": False,
                    "checks": {blocker: False},
                    "blockers": [blocker],
                }
            )
            router.record_external_event(
                root,
                "reviewer_reports_startup_facts",
                self.role_report_envelope(root, f"startup/{name}", block_body),
            )

        def repair_decision(name: str, action: str) -> dict:
            return self.role_decision_envelope(
                root,
                f"startup/{name}",
                {
                    "decided_by_role": "project_manager",
                    "decision": "startup_repair_requested",
                    "repair_target_kind": "system",
                    "target_role_or_system": "flowpilot_router",
                    "repair_action": action,
                    "blocked_report_path": self.rel(root, run_root / "startup" / "startup_fact_report.json"),
                    "resume_event": "reviewer_reports_startup_facts",
                    "resume_condition": "Router repair is complete and reviewer writes a fresh startup fact report.",
                },
            )

        submit_blocking_report("reviewer_startup_fact_block_1", "startup_user_answer_authenticity")
        self.deliver_expected_card(root, "pm.startup_activation")
        first_decision = repair_decision(
            "pm_startup_repair_request_1",
            "rewrite_startup_mechanical_audit_and_reissue_reviewer_fact_check",
        )
        first_result = router.record_external_event(root, "pm_requests_startup_repair", first_decision)
        self.assertNotIn("already_recorded", first_result)
        state = read_json(router.run_state_path(run_root))
        self.assertEqual(state["startup_repair_request"]["startup_repair_cycle"], 1)

        self.deliver_expected_card(root, "reviewer.startup_fact_check")
        submit_blocking_report("reviewer_startup_fact_block_2", "cockpit_or_display_fallback_reality")
        self.deliver_expected_card(root, "pm.startup_activation")

        with self.assertRaisesRegex(router.RouterError, "repeats the previous PM decision"):
            router.record_external_event(root, "pm_requests_startup_repair", first_decision)

        second_result = router.record_external_event(
            root,
            "pm_requests_startup_repair",
            repair_decision(
                "pm_startup_repair_request_2",
                "write_display_surface_receipt_and_reissue_reviewer_fact_check",
            ),
        )
        self.assertNotIn("already_recorded", second_result)
        state = read_json(router.run_state_path(run_root))
        self.assertEqual(state["startup_repair_request"]["startup_repair_cycle"], 2)
        ledger = read_json(run_root / "startup" / "startup_repair_requests.json")
        self.assertEqual(ledger["latest_cycle"], 2)
        self.assertEqual(len(ledger["entries"]), 2)

    def test_cockpit_requested_startup_display_records_chat_fallback_mermaid(self) -> None:
        root = self.make_project()
        cockpit_answers = {**STARTUP_ANSWERS, "display_surface": "cockpit"}
        run_root = self.boot_to_controller(root, cockpit_answers)

        self.complete_startup_activation(root)

        display_surface = read_json(run_root / "display" / "display_surface.json")
        self.assertEqual(display_surface["requested_display_surface"], "cockpit")
        self.assertEqual(display_surface["selected_surface"], "chat_route_sign_fallback")
        self.assertEqual(display_surface["cockpit_status"], "not_started_in_router_runtime")
        self.assertTrue(display_surface["cockpit_probe_required_for_requested_cockpit"])
        self.assertTrue(display_surface["reviewer_fallback_check_required_for_requested_cockpit"])
        self.assertTrue(display_surface["fallback_is_display_only_not_product_ui_completion"])
        self.assertIn("user-flow-diagram.md", display_surface["standard_route_sign_markdown_path"])
        display_packet = read_json(run_root / "diagrams" / "user-flow-diagram-display.json")
        self.assertFalse(display_packet["canonical_route_available"])
        self.assertEqual(display_packet["display_role"], "startup_placeholder")
        self.assertTrue(display_packet["is_placeholder"])
        self.assertEqual(display_packet["replacement_rule"], "replace_when_canonical_route_available")
        route_sign_markdown = (run_root / "diagrams" / "current_route_sign.md").read_text(encoding="utf-8")
        self.assertIn("```mermaid", route_sign_markdown)
        self.assertNotIn("Display gate:", route_sign_markdown)
        self.assertNotIn("Chat evidence:", route_sign_markdown)

    def test_user_stop_or_cancel_makes_run_terminal_and_blocks_next_work(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        pending_before_stop = self.next_after_display_sync(root)
        self.assertIn(
            pending_before_stop["action_type"],
            {"confirm_controller_core_boundary", "check_prompt_manifest", "create_heartbeat_automation", "deliver_system_card"},
        )

        router.record_external_event(root, "user_requests_run_stop", {"reason": "user asked to stop"})
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "write_terminal_summary")
        self.assertEqual(action["run_lifecycle_status"], "stopped_by_user")
        self.assertFalse(action["controller_may_continue_route_work"])
        self.assertTrue(action["controller_may_read_all_current_run_files"])
        self.apply_terminal_summary(root, action, run_root, note="User asked to stop.")
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "run_lifecycle_terminal")
        self.assertEqual(action["run_lifecycle_status"], "stopped_by_user")
        self.assertFalse(action["controller_may_continue_route_work"])
        result = router.apply_action(root, "run_lifecycle_terminal")
        self.assertTrue(result["terminal"])

        state = read_json(router.run_state_path(run_root))
        self.assertEqual(state["status"], "stopped_by_user")
        self.assertTrue(state["flags"]["run_stopped_by_user"])
        self.assertTrue((run_root / "lifecycle" / "run_lifecycle.json").exists())
        lifecycle = read_json(run_root / "lifecycle" / "run_lifecycle.json")
        self.assertEqual(lifecycle["reconciliation"]["status"], "stopped_by_user")
        self.assertTrue((run_root / "lifecycle" / "terminal_reconciliation.json").exists())
        continuation = read_json(run_root / "continuation" / "continuation_binding.json")
        self.assertFalse(continuation["heartbeat_active"])
        self.assertIn(continuation["host_automation_cleanup_status"], {"inactive_verified", "missing_verified"})
        crew = read_json(run_root / "crew_ledger.json")
        self.assertTrue(all(slot["status"] == "stopped_with_run" for slot in crew["role_slots"]))
        packet_ledger = read_json(run_root / "packet_ledger.json")
        self.assertEqual(packet_ledger["active_packet_status"], "stopped_by_user")
        frontier = read_json(run_root / "execution_frontier.json")
        self.assertEqual(frontier["status"], "stopped_by_user")
        self.assertTrue(frontier["terminal"])
        snapshot = read_json(run_root / "route_state_snapshot.json")
        self.assertEqual(snapshot["state"]["status"], "stopped_by_user")
        self.assertTrue(snapshot["state"]["flags"]["run_stopped_by_user"])
        self.assertEqual(snapshot["frontier"]["status"], "stopped_by_user")
        self.assertEqual(snapshot["packet_ledger"]["active_packet_status"], "stopped_by_user")
        self.assertEqual(snapshot["active_ui_task_catalog"]["active_tasks"], [])
        current = read_json(root / ".flowpilot" / "current.json")
        self.assertEqual(current["status"], "stopped_by_user")

        result = router.record_external_event(root, "user_requests_run_cancel", {"reason": "user switched to cancel"})
        self.assertTrue(result["ok"])
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "write_terminal_summary")
        self.assertEqual(action["run_lifecycle_status"], "cancelled_by_user")

    def test_terminal_summary_payload_requires_attribution_display_and_run_root_sources(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        router.record_external_event(root, "user_requests_run_stop", {"reason": "user asked to stop"})
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "write_terminal_summary")

        bad_summary = "Final Summary\n\nNo FlowPilot attribution.\n"
        with self.assertRaisesRegex(router.RouterError, "GitHub attribution"):
            router.apply_controller_action(
                root,
                "write_terminal_summary",
                {
                    "summary_markdown": bad_summary,
                    "displayed_to_user": True,
                    "displayed_summary_sha256": hashlib.sha256(bad_summary.encode("utf-8")).hexdigest(),
                    "read_scope_used": router.TERMINAL_SUMMARY_READ_SCOPE,
                },
            )

        good = self.terminal_summary_payload(root, action, run_root, note="User asked to stop.")
        with self.assertRaisesRegex(router.RouterError, "current run root"):
            router.apply_controller_action(root, "write_terminal_summary", {**good, "source_paths_reviewed": ["outside.json"]})

        with self.assertRaisesRegex(router.RouterError, "displayed_to_user=true"):
            router.apply_controller_action(root, "write_terminal_summary", {**good, "displayed_to_user": False})

        self.apply_terminal_summary(root, action, run_root, note="User asked to stop.")

    def test_startup_fact_report_accepts_file_backed_envelope_only_payload(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.deliver_startup_fact_check_card(root)
        self.deliver_initial_pm_cards_and_user_intake(root)

        report_body = self.startup_fact_report_body(root)
        report_text = json.dumps(report_body, indent=2, sort_keys=True)
        private_report = run_root / "startup" / "reviewer_private_startup_fact_report.json"
        private_report.parent.mkdir(parents=True, exist_ok=True)
        private_report.write_text(report_text, encoding="utf-8")
        report_hash = hashlib.sha256(private_report.read_bytes()).hexdigest()
        report_path = str(private_report.relative_to(root))

        with self.assertRaisesRegex(router.RouterError, "leaked role body fields"):
            router.record_external_event(
                root,
                "reviewer_reports_startup_facts",
                {
                    "report_path": report_path,
                    "report_hash": report_hash,
                    "controller_visibility": "role_output_envelope_only",
                    "blockers": [],
                },
            )

        router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            {
                "report_path": report_path,
                "report_hash": report_hash,
                "controller_visibility": "role_output_envelope_only",
            },
        )

        canonical_report = read_json(run_root / "startup" / "startup_fact_report.json")
        self.assertEqual(
            canonical_report["_role_output_envelope"]["controller_visibility"],
            "role_output_envelope_only",
        )
        self.assertFalse(canonical_report["_role_output_envelope"]["chat_response_body_allowed"])

    def test_record_event_accepts_runtime_envelope_ref_for_startup_fact_report(self) -> None:
        for mode in ("payload_ref", "cli_ref", "full_envelope"):
            with self.subTest(mode=mode):
                root = self.make_project()
                run_root = self.boot_to_controller(root)
                self.deliver_startup_fact_check_card(root)
                self.deliver_initial_pm_cards_and_user_intake(root)
                envelope, envelope_path, envelope_hash = self.startup_fact_runtime_envelope(root)

                if mode == "payload_ref":
                    result = router.record_external_event(
                        root,
                        "reviewer_reports_startup_facts",
                        {"event_envelope_ref": {"path": envelope_path, "hash": envelope_hash}},
                    )
                elif mode == "cli_ref":
                    parsed = router.parse_args(
                        [
                            "--root",
                            str(root),
                            "record-event",
                            "--event",
                            "reviewer_reports_startup_facts",
                            "--envelope-path",
                            envelope_path,
                            "--envelope-hash",
                            envelope_hash,
                        ]
                    )
                    self.assertEqual(parsed.envelope_path, envelope_path)
                    self.assertEqual(parsed.envelope_hash, envelope_hash)
                    result = router.record_external_event(
                        root,
                        "reviewer_reports_startup_facts",
                        envelope_path=envelope_path,
                        envelope_hash=envelope_hash,
                    )
                else:
                    result = router.record_external_event(root, "reviewer_reports_startup_facts", envelope)

                self.assertTrue(result["ok"])
                canonical_report = read_json(run_root / "startup" / "startup_fact_report.json")
                source_envelope = canonical_report["_role_output_envelope"]
                self.assertEqual(source_envelope["role_output_runtime_receipt_path"], envelope["runtime_receipt_ref"]["path"])
                self.assertTrue(source_envelope["role_output_runtime_validated"])
                self.assertFalse(source_envelope["chat_response_body_allowed"])
                self.assertNotIn("runtime_receipt_path", source_envelope)

    def test_record_event_rejects_bad_event_envelope_refs_before_payload_reconstruction(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.deliver_startup_fact_check_card(root)
        self.deliver_initial_pm_cards_and_user_intake(root)
        envelope, envelope_path, envelope_hash = self.startup_fact_runtime_envelope(root)

        with self.assertRaisesRegex(router.RouterError, "hash mismatch"):
            router.record_external_event(
                root,
                "reviewer_reports_startup_facts",
                {"event_envelope_ref": {"path": envelope_path, "hash": "0" * 64}},
            )

        missing_ref = {"event_envelope_ref": {"path": ".flowpilot/runs/missing/events/nope.envelope.json", "hash": envelope_hash}}
        with self.assertRaisesRegex(router.RouterError, "file is missing"):
            router.record_external_event(root, "reviewer_reports_startup_facts", missing_ref)

        outside_path = root.parent / f"{root.name}-outside-event.envelope.json"
        outside_path.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self.addCleanup(lambda: outside_path.unlink(missing_ok=True))
        with self.assertRaisesRegex(router.RouterError, "outside project root"):
            router.record_external_event(
                root,
                "reviewer_reports_startup_facts",
                {
                    "event_envelope_ref": {
                        "path": str(outside_path),
                        "hash": hashlib.sha256(outside_path.read_bytes()).hexdigest(),
                    }
                },
            )

        bad_schema = dict(envelope)
        bad_schema["schema_version"] = "flowpilot.untrusted_event_envelope.v0"
        bad_schema_path, bad_schema_hash = self.write_event_envelope(root, "startup/bad_schema", bad_schema)
        with self.assertRaisesRegex(router.RouterError, "schema_version"):
            router.record_external_event(
                root,
                "reviewer_reports_startup_facts",
                {"event_envelope_ref": {"path": bad_schema_path, "hash": bad_schema_hash}},
            )

        bad_event = dict(envelope)
        bad_event["event_name"] = "pm_issues_material_and_capability_scan_packets"
        bad_event_path, bad_event_hash = self.write_event_envelope(root, "startup/bad_event", bad_event)
        with self.assertRaisesRegex(router.RouterError, "event mismatch"):
            router.record_external_event(
                root,
                "reviewer_reports_startup_facts",
                {"event_envelope_ref": {"path": bad_event_path, "hash": bad_event_hash}},
            )

        bad_role = dict(envelope)
        bad_role["from_role"] = "project_manager"
        bad_role_path, bad_role_hash = self.write_event_envelope(root, "startup/bad_role", bad_role)
        with self.assertRaisesRegex(router.RouterError, "from_role mismatch"):
            router.record_external_event(
                root,
                "reviewer_reports_startup_facts",
                {"event_envelope_ref": {"path": bad_role_path, "hash": bad_role_hash}},
            )

        bad_visibility = dict(envelope)
        bad_visibility["controller_visibility"] = "sealed_body_visible"
        bad_visibility_path, bad_visibility_hash = self.write_event_envelope(root, "startup/bad_visibility", bad_visibility)
        with self.assertRaisesRegex(router.RouterError, "controller_visibility"):
            router.record_external_event(
                root,
                "reviewer_reports_startup_facts",
                {"event_envelope_ref": {"path": bad_visibility_path, "hash": bad_visibility_hash}},
            )

        leaked = dict(envelope)
        leaked["recommendations"] = ["inline body content that belongs in the sealed report body"]
        leaked_path, leaked_hash = self.write_event_envelope(root, "startup/leaked_body", leaked)
        with self.assertRaisesRegex(router.RouterError, "leaked role body fields"):
            router.record_external_event(
                root,
                "reviewer_reports_startup_facts",
                {"event_envelope_ref": {"path": leaked_path, "hash": leaked_hash}},
            )

    def test_record_event_rejects_envelope_outside_current_wait(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        envelope, envelope_path, envelope_hash = self.startup_fact_runtime_envelope(root)
        self.assertEqual(envelope["event_name"], "reviewer_reports_startup_facts")

        with self.assertRaisesRegex(router.RouterError, "not currently allowed"):
            router.record_external_event(
                root,
                "reviewer_reports_startup_facts",
                {"event_envelope_ref": {"path": envelope_path, "hash": envelope_hash}},
            )

    def test_startup_fact_report_rejects_canonical_submission_alias(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.deliver_startup_fact_check_card(root)
        self.deliver_initial_pm_cards_and_user_intake(root)

        canonical_report = run_root / "startup" / "startup_fact_report.json"
        canonical_report.write_text(
            json.dumps(self.startup_fact_report_body(root), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        report_hash = hashlib.sha256(canonical_report.read_bytes()).hexdigest()

        with self.assertRaisesRegex(router.RouterError, "canonical startup_fact_report.json"):
            router.record_external_event(
                root,
                "reviewer_reports_startup_facts",
                {
                    "report_path": self.rel(root, canonical_report),
                    "report_hash": report_hash,
                    "controller_visibility": "role_output_envelope_only",
                },
            )

    def test_router_owned_check_proof_rejects_self_attested_and_stale_audit(self) -> None:
        root = self.make_project()
        run_root = root / ".flowpilot" / "runs" / "run-proof"
        audit_path = run_root / "proof" / "audit.json"
        router.write_json(audit_path, {"schema_version": "test.audit.v1", "run_id": "run-proof", "passed": True})

        with self.assertRaisesRegex(router.RouterError, "unsupported router-owned proof source"):
            router._write_router_owned_check_proof(
                root,
                run_root,
                check_name="unit_proof_check",
                audit_path=audit_path,
                source_kind="self_attested_ai",
                evidence_paths=[audit_path],
            )

        router._write_router_owned_check_proof(
            root,
            run_root,
            check_name="unit_proof_check",
            audit_path=audit_path,
            source_kind="router_computed",
            evidence_paths=[audit_path],
        )
        proof = router._validate_router_owned_check_proof(
            root,
            run_root,
            check_name="unit_proof_check",
            audit_path=audit_path,
        )
        self.assertFalse(proof["self_attested_ai_claims_accepted_as_proof"])

        router.write_json(audit_path, {"schema_version": "test.audit.v1", "run_id": "run-proof", "passed": False})
        with self.assertRaisesRegex(router.RouterError, "audit hash is stale"):
            router._validate_router_owned_check_proof(
                root,
                run_root,
                check_name="unit_proof_check",
                audit_path=audit_path,
            )

    def test_material_acceptance_requires_reviewer_sufficiency_and_pm_absorb_card(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_accepts_reviewed_material")

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.material_scan")
        self.ack_system_card_action(root, action)
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "worker_scan_results_returned")

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "worker_scan_packet_bodies_delivered_after_dispatch")
        self.apply_next_packet_action(root, "relay_material_scan_packets")
        material_index_path = run_root / "material" / "material_scan_packets.json"
        self.open_packets_and_write_results(root, material_index_path, result_text="insufficient material scan result")
        router.record_external_event(root, "worker_scan_packet_bodies_delivered_after_dispatch")
        router.record_external_event(root, "worker_scan_results_returned")

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "reviewer_reports_material_sufficient")
        self.absorb_material_scan_results_with_pm(root, material_index_path)

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "reviewer.material_sufficiency")
        self.ack_system_card_action(root, action)
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "reviewer_reports_material_insufficient")
        router.record_external_event(
            root,
            "reviewer_reports_material_insufficient",
            self.role_report_envelope(
                root,
                "material/reviewer_material_insufficient",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "direct_material_sources_checked": True,
                    "packet_matches_checked_sources": True,
                    "pm_ready": False,
                    "blockers": ["missing authoritative source"],
                },
            ),
        )

        self.deliver_expected_card(root, "pm.event.reviewer_report")
        self.deliver_expected_card(root, "pm.material_absorb_or_research")

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_accepts_reviewed_material")
        router.record_external_event(root, "pm_requests_research_after_material_insufficient")
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["pm_research_requested"])

    def test_material_scan_accepts_file_backed_packet_body_and_updates_frontier(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(
            root,
            "pm_issues_material_and_capability_scan_packets",
            self.material_scan_file_backed_payload(root),
        )

        frontier = read_json(run_root / "execution_frontier.json")
        self.assertEqual(frontier["status"], "material_scan")
        self.assertIsNone(frontier["active_node_id"])
        material_index = read_json(run_root / "material" / "material_scan_packets.json")
        packet = packet_runtime.load_envelope(root, material_index["packets"][0]["packet_envelope_path"])
        self.assertEqual(packet["packet_type"], "material_scan")
        self.assertFalse(packet["is_current_node"])
        self.assertEqual(packet["expected_result_body_path"], material_index["packets"][0]["result_body_path"])
        self.assertEqual(packet["write_target_path"], material_index["packets"][0]["result_body_path"])
        self.assertEqual(packet["result_write_target"]["result_body_path"], material_index["packets"][0]["result_body_path"])
        self.assertEqual(packet["output_contract"]["expected_result_body_path"], material_index["packets"][0]["result_body_path"])
        packet_body = (root / packet["body_path"]).read_text(encoding="utf-8")
        self.assertIn(material_index["packets"][0]["result_body_path"], packet_body)

    def test_record_event_accepts_material_scan_envelope_ref_with_packets(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.deliver_expected_card(root, "pm.material_scan")
        envelope, envelope_path, envelope_hash = self.material_scan_event_envelope(root)

        result = router.record_external_event(
            root,
            "pm_issues_material_and_capability_scan_packets",
            {"event_envelope_ref": {"path": envelope_path, "hash": envelope_hash}},
        )

        self.assertTrue(result["ok"])
        material_index = read_json(run_root / "material" / "material_scan_packets.json")
        self.assertEqual(material_index["written_by_role"], "project_manager")
        self.assertEqual(material_index["packets"][0]["packet_id"], envelope["packets"][0]["packet_id"])
        self.assertTrue((root / material_index["packets"][0]["packet_envelope_path"]).exists())

    def test_record_event_rejects_manual_material_scan_payload_with_hidden_packets(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.deliver_expected_card(root, "pm.material_scan")
        payload = {"event_envelope": self.material_scan_event_envelope(root)[0]}

        with self.assertRaisesRegex(router.RouterError, "payload\\.packets"):
            router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", payload)

    def test_material_scan_packet_and_result_relays_combine_ledger_check(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())

        state_before = read_json(router.run_state_path(run_root))
        ledger_checks_before = int(state_before.get("ledger_checks", 0))
        ledger_requests_before = int(state_before.get("ledger_check_requests", 0))
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "relay_material_scan_packets")
        self.assertTrue(action["combined_ledger_check_and_relay"])
        self.assertTrue(action["ledger_check_receipt_required"])
        self.assertFalse(action["sealed_body_reads_allowed"])

        router.apply_action(root, "relay_material_scan_packets")

        state_after_packets = read_json(router.run_state_path(run_root))
        self.assertEqual(state_after_packets["ledger_checks"], ledger_checks_before + 1)
        self.assertEqual(state_after_packets["ledger_check_requests"], ledger_requests_before + 1)
        self.assertFalse(state_after_packets.get("ledger_check_requested"))
        self.assertTrue(state_after_packets["flags"]["material_scan_packets_relayed"])

        material_index_path = run_root / "material" / "material_scan_packets.json"
        self.open_packets_and_write_results(root, material_index_path, result_text="material scan result")
        router.record_external_event(root, "worker_scan_packet_bodies_delivered_after_dispatch")
        router.record_external_event(root, "worker_scan_results_returned")

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "relay_material_scan_results_to_pm")
        self.assertTrue(action["combined_ledger_check_and_relay"])
        self.assertTrue(action["ledger_check_receipt_required"])
        self.assertFalse(action["sealed_body_reads_allowed"])

        router.apply_action(root, "relay_material_scan_results_to_pm")

        state_after_results = read_json(router.run_state_path(run_root))
        self.assertEqual(state_after_results["ledger_checks"], ledger_checks_before + 2)
        self.assertEqual(state_after_results["ledger_check_requests"], ledger_requests_before + 2)
        self.assertFalse(state_after_results.get("ledger_check_requested"))
        self.assertTrue(state_after_results["flags"]["material_scan_results_relayed_to_pm"])

        index = read_json(material_index_path)
        relayed_result = packet_runtime.load_envelope(root, index["packets"][0]["result_envelope_path"])
        self.assertEqual(relayed_result["controller_relay"]["relayed_to_role"], "project_manager")
        self.assertFalse(relayed_result["controller_relay"]["body_was_read_by_controller"])

    def test_material_scan_packet_body_event_requires_packet_ledger_open_receipt(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        self.apply_next_packet_action(root, "relay_material_scan_packets")
        material_index_path = run_root / "material" / "material_scan_packets.json"
        index = read_json(material_index_path)
        envelope = packet_runtime.load_envelope(root, index["packets"][0]["packet_envelope_path"])
        packet_runtime.read_packet_body_for_role(root, envelope, role=envelope["to_role"])

        ledger_path = run_root / "packet_ledger.json"
        ledger = read_json(ledger_path)
        packet_record = next(record for record in ledger["packets"] if record.get("packet_id") == envelope["packet_id"])
        packet_record.pop("packet_body_opened_by_role", None)
        packet_record["packet_body_opened_after_controller_relay_check"] = False
        router.write_json(ledger_path, ledger)

        with self.assertRaisesRegex(router.RouterError, "ledger open receipt") as raised:
            router.record_external_event(root, "worker_scan_packet_bodies_delivered_after_dispatch")
        blocker = raised.exception.control_blocker
        self.assertEqual(blocker["handling_lane"], "control_plane_reissue")
        self.assertEqual(blocker["target_role"], "worker_a")
        self.assertEqual(blocker["responsible_role_for_reissue"], "worker_a")
        self.assertFalse(blocker["pm_decision_required"])

    def test_material_scan_results_event_requires_result_ledger_absorption(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        self.apply_next_packet_action(root, "relay_material_scan_packets")
        material_index_path = run_root / "material" / "material_scan_packets.json"
        self.open_packets_and_write_results(root, material_index_path, result_text="material scan result")
        router.record_external_event(root, "worker_scan_packet_bodies_delivered_after_dispatch")

        ledger_path = run_root / "packet_ledger.json"
        ledger = read_json(ledger_path)
        index = read_json(material_index_path)
        packet_id = index["packets"][0]["packet_id"]
        packet_record = next(record for record in ledger["packets"] if record.get("packet_id") == packet_id)
        packet_record["result_body_hash"] = "stale-result-hash"
        router.write_json(ledger_path, ledger)

        with self.assertRaisesRegex(router.RouterError, "packet_ledger_missing_result_absorption") as raised:
            router.record_external_event(root, "worker_scan_results_returned")
        blocker = raised.exception.control_blocker
        self.assertEqual(blocker["handling_lane"], "control_plane_reissue")
        self.assertEqual(blocker["target_role"], "worker_a")
        self.assertEqual(blocker["responsible_role_for_reissue"], "worker_a")
        self.assertFalse(blocker["pm_decision_required"])

    def test_material_scan_direct_relay_blocks_body_hash_mismatch(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        material_index = read_json(run_root / "material" / "material_scan_packets.json")
        envelope = read_json(root / material_index["packets"][0]["packet_envelope_path"])
        body_path = root / envelope["body_path"]
        body_path.write_text(body_path.read_text(encoding="utf-8") + "\nTampered after packet creation.\n", encoding="utf-8")

        with self.assertRaisesRegex(router.RouterError, "body_hash_mismatch"):
            self.apply_next_packet_action(root, "relay_material_scan_packets")

    def test_material_scan_direct_relay_blocks_missing_output_contract(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        material_index = read_json(run_root / "material" / "material_scan_packets.json")
        envelope_path = root / material_index["packets"][0]["packet_envelope_path"]
        envelope = read_json(envelope_path)
        envelope.pop("output_contract", None)
        envelope.pop("output_contract_id", None)
        router.write_json(envelope_path, envelope)

        with self.assertRaisesRegex(router.RouterError, "missing_output_contract"):
            self.apply_next_packet_action(root, "relay_material_scan_packets")

    def test_research_required_blocks_product_architecture_until_absorbed(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        self.apply_next_packet_action(root, "relay_material_scan_packets")
        material_index_path = run_root / "material" / "material_scan_packets.json"
        self.open_packets_and_write_results(root, material_index_path, result_text="research needed")
        router.record_external_event(root, "worker_scan_packet_bodies_delivered_after_dispatch")
        router.record_external_event(root, "worker_scan_results_returned")
        self.absorb_material_scan_results_with_pm(root, material_index_path)
        self.deliver_expected_card(root, "reviewer.material_sufficiency")
        router.record_external_event(
            root,
            "reviewer_reports_material_insufficient",
            self.role_report_envelope(
                root,
                "material/reviewer_material_insufficient",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "direct_material_sources_checked": True,
                    "packet_matches_checked_sources": True,
                    "pm_ready": False,
                },
            ),
        )
        self.deliver_expected_card(root, "pm.event.reviewer_report")
        self.deliver_expected_card(root, "pm.material_absorb_or_research")
        router.record_external_event(root, "pm_requests_research_after_material_insufficient")

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_material_understanding")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_product_function_architecture")

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.research_package")
        self.ack_system_card_action(root, action)
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_research_package", {})
        router.record_external_event(
            root,
            "pm_writes_research_package",
            {
                "decision_question": "which source is authoritative?",
                "allowed_source_types": [
                    "current_repository_files",
                    "bounded_local_read_only_experiments",
                ],
                "host_capability_decision": "local_sources_first",
                "worker_owner": "worker_a",
                "stop_conditions": ["Do not edit production code."],
            },
        )
        router.record_external_event(root, "research_capability_decision_recorded", {})
        research_package = read_json(run_root / "research" / "research_package.json")
        self.assertEqual(research_package["allowed_source_types"], ["current_repository_files", "bounded_local_read_only_experiments"])
        research_decision = read_json(run_root / "research" / "research_capability_decision.json")
        self.assertEqual(research_decision["allowed_sources"], research_package["allowed_source_types"])
        self.assertEqual(research_decision["stop_conditions"], ["Do not edit production code."])
        research_index = read_json(run_root / "research" / "research_packet.json")
        self.assertIn("packet_body_path", research_index)
        self.assertIn("packet_body_hash", research_index)
        self.assertIn("body_path", research_index["packets"][0])
        research_packet_body = (root / research_index["packet_body_path"]).read_text(encoding="utf-8")
        self.assertIn("current_repository_files", research_packet_body)
        self.assertIn("Do not edit production code.", research_packet_body)

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "worker.research_report")
        self.ack_system_card_action(root, action)
        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "worker_research_report_returned",
                {"completed_by_role": "worker_a", "answers_decision_question": True},
            )
        state_before_research_relay = read_json(router.run_state_path(run_root))
        ledger_checks_before_research = int(state_before_research_relay.get("ledger_checks", 0))
        ledger_requests_before_research = int(state_before_research_relay.get("ledger_check_requests", 0))
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "relay_research_packet")
        self.assertTrue(action["combined_ledger_check_and_relay"])
        self.assertTrue(action["ledger_check_receipt_required"])
        self.assertFalse(action["sealed_body_reads_allowed"])
        router.apply_action(root, "relay_research_packet")
        state_after_research_packet = read_json(router.run_state_path(run_root))
        self.assertEqual(state_after_research_packet["ledger_checks"], ledger_checks_before_research + 1)
        self.assertEqual(state_after_research_packet["ledger_check_requests"], ledger_requests_before_research + 1)
        self.assertFalse(state_after_research_packet.get("ledger_check_requested"))

        research_index_path = run_root / "research" / "research_packet.json"
        self.open_packets_and_write_results(root, research_index_path, result_text="research report result")
        router.record_external_event(
            root,
            "worker_research_report_returned",
            {"completed_by_role": "worker_a", "answers_decision_question": True},
        )
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "relay_research_result_to_pm")
        self.assertTrue(action["combined_ledger_check_and_relay"])
        self.assertTrue(action["ledger_check_receipt_required"])
        self.assertFalse(action["sealed_body_reads_allowed"])
        router.apply_action(root, "relay_research_result_to_pm")
        state_after_research_result = read_json(router.run_state_path(run_root))
        self.assertEqual(state_after_research_result["ledger_checks"], ledger_checks_before_research + 2)
        self.assertEqual(state_after_research_result["ledger_check_requests"], ledger_requests_before_research + 2)
        self.assertFalse(state_after_research_result.get("ledger_check_requested"))
        self.open_results_for_pm(root, research_index_path)
        router.record_external_event(
            root,
            "pm_records_research_result_disposition",
            {
                "decided_by_role": "project_manager",
                "decision": "absorbed",
                "decision_reason": "PM absorbed research results for reviewer direct-source gate.",
            },
        )

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "reviewer.research_direct_source_check")
        self.ack_system_card_action(root, action)
        router.record_external_event(
            root,
            "reviewer_passes_research_direct_source_check",
            self.role_report_envelope(
                root,
                "research/reviewer_direct_source_check",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.research_absorb_or_mutate")
        self.ack_system_card_action(root, action)
        router.record_external_event(root, "pm_absorbs_reviewed_research")

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.material_understanding")
        self.ack_system_card_action(root, action)
        router.record_external_event(root, "pm_writes_material_understanding", {"material_summary": "research absorbed"})
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["research_result_absorbed_by_pm"])
        self.assertTrue(state["flags"]["material_accepted_by_pm"])
        self.assertTrue((run_root / "pm_material_understanding.json").exists())

    def test_product_architecture_and_root_contract_gate_route_skeleton(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.complete_material_flow(root)

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_activates_reviewed_route")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_product_function_architecture")

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.product_architecture")
        self.ack_system_card_action(root, action)
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_product_function_architecture", {"user_task_map": []})
        router.record_external_event(
            root,
            "pm_writes_product_function_architecture",
            {
                "user_task_map": [{"task_id": "task-001", "goal": "ship FlowPilot"}],
                "product_capability_map": [{"capability_id": "cap-001", "behavior": "ship FlowPilot"}],
                "feature_decisions": [{"feature_id": "feature-001", "decision": "must"}],
                "highest_achievable_product_target": {"product_vision": "complete FlowPilot route control"},
                "semantic_fidelity_policy": {"silent_downgrade_forbidden": True},
                "functional_acceptance_matrix": [{"acceptance_id": "root-001"}],
            },
        )
        self.assertTrue((run_root / "product_function_architecture.json").exists())

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_root_acceptance_contract", {"root_requirements": [{"requirement_id": "root-001"}]})

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "product_officer.product_architecture_modelability")
        self.ack_system_card_action(root, action)
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "product_officer_passes_product_architecture_modelability", {"passed": True})
        self.assertTrue(self.handle_pending_control_blocker(root))
        router.record_external_event(
            root,
            "product_officer_passes_product_architecture_modelability",
            self.role_report_envelope(
                root,
                "flowguard/product_architecture_modelability",
                {"reviewed_by_role": "product_flowguard_officer", "passed": True},
            ),
        )

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.product_behavior_model_decision")
        self.ack_system_card_action(root, action)
        router.record_external_event(root, "pm_accepts_product_behavior_model", self.product_behavior_model_decision_body())

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "reviewer.product_architecture_challenge")
        self.ack_system_card_action(root, action)
        router.record_external_event(
            root,
            "reviewer_passes_product_architecture",
            self.role_report_envelope(
                root,
                "reviews/product_architecture_challenge",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.root_contract")
        self.ack_system_card_action(root, action)
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_root_acceptance_contract", {"root_requirements": []})
        router.record_external_event(
            root,
            "pm_writes_root_acceptance_contract",
            {
                "root_requirements": [
                    {
                        "requirement_id": "root-001",
                        "priority": "must",
                        "proof_required": "mixed",
                    }
                ],
                "proof_matrix": [{"requirement_id": "root-001", "expected_final_replay": True}],
                "selected_scenario_ids": ["terminal_complete_state"],
            },
        )
        self.assertTrue((run_root / "root_acceptance_contract.json").exists())
        self.assertTrue((run_root / "standard_scenario_pack.json").exists())
        self.assertTrue((run_root / "contract.md").exists())

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_activates_reviewed_route")

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "reviewer.root_contract_challenge")
        self.ack_system_card_action(root, action)
        router.record_external_event(
            root,
            "reviewer_passes_root_acceptance_contract",
            self.role_report_envelope(
                root,
                "reviews/root_contract_challenge",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "product_officer.root_contract_modelability")
        self.ack_system_card_action(root, action)
        router.record_external_event(
            root,
            "product_officer_passes_root_acceptance_contract_modelability",
            self.role_report_envelope(
                root,
                "flowguard/root_contract_modelability",
                {"reviewed_by_role": "product_flowguard_officer", "passed": True},
            ),
        )
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_activates_reviewed_route")
        router.record_external_event(root, "pm_freezes_root_acceptance_contract")

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.dependency_policy")
        self.ack_system_card_action(root, action)
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_route_draft", {"nodes": [{"node_id": "node-001"}]})
        self.complete_child_skill_gates(root)

        self.deliver_expected_card(root, "pm.prior_path_context")
        self.deliver_expected_card(root, "pm.route_skeleton")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_activates_reviewed_route")
        router.record_external_event(
            root,
            "pm_writes_route_draft",
            {
                "nodes": [{"node_id": "node-001"}],
                **self.prior_path_context_review(root, "Route draft considered prior path context before activation."),
            },
        )
        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "process_officer_passes_route_check",
                self.role_report_envelope(
                    root,
                    "flowguard/route_process_check",
                    self.route_process_pass_body(),
                ),
            )
        self.complete_route_checks(root)
        router.record_external_event(root, "pm_activates_reviewed_route")

    def test_legacy_product_officer_model_report_does_not_close_modelability_gate(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.complete_material_flow(root)

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.product_architecture")
        self.ack_system_card_action(root, action)
        router.record_external_event(
            root,
            "pm_writes_product_function_architecture",
            {
                "user_task_map": [{"task_id": "task-001", "goal": "ship FlowPilot"}],
                "product_capability_map": [{"capability_id": "cap-001", "behavior": "ship FlowPilot"}],
                "feature_decisions": [{"feature_id": "feature-001", "decision": "must"}],
                "highest_achievable_product_target": {"product_vision": "complete FlowPilot route control"},
                "semantic_fidelity_policy": {"silent_downgrade_forbidden": True},
                "functional_acceptance_matrix": [{"acceptance_id": "root-001"}],
            },
        )

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "product_officer.product_architecture_modelability")
        self.assertEqual(action["gate_contract"]["gate_id"], "product_behavior_model")
        self.ack_system_card_action(root, action)
        wait = self.next_after_display_sync(root)
        self.assertEqual(wait["action_type"], "await_role_decision")
        self.assertEqual(wait["gate_contract"]["gate_id"], "product_behavior_model")
        self.assertIn("product_officer_passes_product_architecture_modelability", wait["allowed_external_events"])
        self.assertIn("product_officer_blocks_product_architecture_modelability", wait["allowed_external_events"])
        self.assertNotIn("product_officer_model_report", wait["allowed_external_events"])

        router.record_external_event(root, "product_officer_model_report", {"legacy_status": "received"})
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["legacy_product_officer_model_report_received"])
        self.assertFalse(state["flags"]["product_architecture_modelability_passed"])

        wait = self.next_after_display_sync(root)
        self.assertEqual(wait["action_type"], "await_role_decision")
        self.assertIn("product_officer_passes_product_architecture_modelability", wait["allowed_external_events"])
        self.assertNotIn("product_officer_model_report", wait["allowed_external_events"])

        router.record_external_event(
            root,
            "product_officer_passes_product_architecture_modelability",
            self.role_report_envelope(
                root,
                "flowguard/product_architecture_modelability",
                {"reviewed_by_role": "product_flowguard_officer", "passed": True},
            ),
        )
        action = self.deliver_expected_card(root, "pm.product_behavior_model_decision")
        self.assertEqual(action["card_id"], "pm.product_behavior_model_decision")

    def test_process_route_model_canonical_event_writes_compatibility_alias(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.complete_material_flow(root)
        self.complete_root_contract_before_child_skill_gates(root)
        self.complete_child_skill_gates(root)
        self.deliver_expected_card(root, "pm.prior_path_context")
        self.deliver_expected_card(root, "pm.route_skeleton")
        router.record_external_event(
            root,
            "pm_writes_route_draft",
            {
                "nodes": [{"node_id": "node-001"}],
                **self.prior_path_context_review(root, "Route draft considered prior context before process model."),
            },
        )

        action = self.deliver_expected_card(root, "process_officer.route_process_check")
        self.assertEqual(action["gate_contract"]["gate_id"], "process_route_model")
        wait = self.next_after_display_sync(root)
        self.assertEqual(wait["action_type"], "await_role_decision")
        self.assertEqual(wait["gate_contract"]["gate_id"], "process_route_model")
        self.assertIn("process_officer_submits_process_route_model", wait["allowed_external_events"])
        self.assertIn("process_officer_passes_route_check", wait["allowed_external_events"])

        router.record_external_event(
            root,
            "process_officer_submits_process_route_model",
            self.role_report_envelope(root, "flowguard/process_route_model", self.route_process_pass_body()),
        )
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["process_route_model_submitted"])
        self.assertTrue(state["flags"]["process_officer_route_check_passed"])
        self.assertTrue((run_root / "flowguard" / "process_route_model.json").exists())
        self.assertTrue((run_root / "flowguard" / "route_process_check.json").exists())

        action = self.deliver_expected_card(root, "pm.process_route_model_decision")
        self.assertEqual(action["card_id"], "pm.process_route_model_decision")

    def test_route_activation_rejects_active_node_missing_from_reviewed_route(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.deliver_expected_card(root, "pm.prior_path_context")
        self.deliver_expected_card(root, "pm.route_skeleton")
        router.record_external_event(
            root,
            "pm_writes_route_draft",
            {
                "nodes": [{"node_id": "node-001"}],
                **self.prior_path_context_review(root, "Route draft considered prior path context before activation."),
            },
        )
        self.complete_route_checks(root)

        with self.assertRaisesRegex(router.RouterError, "active route node is missing"):
            router.record_external_event(root, "pm_activates_reviewed_route", {"active_node_id": "missing-node"})

    def test_child_skill_gates_block_raw_inventory_and_controller_approval(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.complete_material_flow(root)
        self.complete_root_contract_before_child_skill_gates(root)

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.dependency_policy")
        self.ack_system_card_action(root, action)
        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "pm_records_dependency_policy",
                {
                    "host_level_install_requested": True,
                    "explicit_user_approval_recorded": False,
                },
            )
        router.record_external_event(root, "pm_records_dependency_policy", {"allowed_dependency_actions": ["use_existing_local_skill"]})

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_capabilities_manifest", {"raw_inventory_is_authority": True})
        router.record_external_event(
            root,
            "pm_writes_capabilities_manifest",
            {"capabilities": [{"capability_id": "cap-001", "behavior": "route capability"}]},
        )

        self.deliver_expected_card(root, "pm.child_skill_selection")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_child_skill_selection", {"raw_inventory_used_as_authority": True})
        controller_selected_skill = [
            {
                "skill_name": "bad-controller-approved-skill",
                "decision": "required",
                "gates": [{"gate_id": "bad", "required_approver": "controller", "controller_can_approve": True}],
            }
        ]
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_child_skill_selection", {"selected_skills": controller_selected_skill})
        safe_selected_skill = [
            {
                "skill_name": "model-first-function-flow",
                "decision": "required",
                "supported_capabilities": ["cap-001"],
                "gates": [
                    {
                        "gate_id": "process-model",
                        "required_approver": "process_flowguard_officer",
                        "controller_can_approve": False,
                    }
                ],
            }
        ]
        router.record_external_event(root, "pm_writes_child_skill_selection", {"selected_skills": safe_selected_skill})

        self.deliver_expected_card(root, "pm.child_skill_gate_manifest")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_child_skill_gate_manifest", {"selected_skills": controller_selected_skill})

        router.record_external_event(root, "pm_writes_child_skill_gate_manifest", {"selected_skills": safe_selected_skill})
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_approves_child_skill_manifest_for_route")

        self.deliver_expected_card(root, "reviewer.child_skill_gate_manifest_review")
        router.record_external_event(
            root,
            "reviewer_passes_child_skill_gate_manifest",
            self.role_report_envelope(
                root,
                "reviews/child_skill_gate_manifest_review",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )
        manifest_after_review = read_json(run_root / "child_skill_gate_manifest.json")
        self.assertTrue(manifest_after_review["approval"]["reviewer_passed"])
        self.assertFalse(manifest_after_review["approval"]["pm_approved_for_route"])
        self.deliver_expected_card(root, "process_officer.child_skill_conformance_model")
        router.record_external_event(
            root,
            "process_officer_passes_child_skill_conformance_model",
            self.role_report_envelope(
                root,
                "flowguard/child_skill_conformance_model",
                {"reviewed_by_role": "process_flowguard_officer", "passed": True},
            ),
        )
        self.deliver_expected_card(root, "product_officer.child_skill_product_fit")
        router.record_external_event(
            root,
            "product_officer_passes_child_skill_product_fit",
            self.role_report_envelope(
                root,
                "flowguard/child_skill_product_fit",
                {"reviewed_by_role": "product_flowguard_officer", "passed": True},
            ),
        )
        router.record_external_event(root, "pm_approves_child_skill_manifest_for_route")
        router.record_external_event(root, "capability_evidence_synced")
        self.assertTrue((run_root / "capabilities" / "capability_sync.json").exists())

    def test_reviewer_and_officer_gate_event_groups_have_non_pass_outcomes(self) -> None:
        pass_markers = ("passes", "passed", "approves", "allows", "sufficient")
        non_pass_markers = ("blocks", "blocked", "insufficient", "requires_repair", "requests_repair", "protocol_dead_end")
        groups: dict[str, list[str]] = {}
        for event_name, meta in router.EXTERNAL_EVENTS.items():
            if meta.get("legacy"):
                continue
            required_flag = str(meta.get("requires_flag") or "")
            if not required_flag:
                continue
            role_events = groups.setdefault(required_flag, [])
            if event_name.startswith(("reviewer_", "current_node_reviewer_", "process_officer_", "product_officer_")):
                role_events.append(event_name)

        pass_only: dict[str, list[str]] = {}
        for required_flag, event_names in groups.items():
            if required_flag == "reviewer_startup_fact_check_card_delivered":
                continue
            classes = {
                "non_pass" if any(marker in event_name for marker in non_pass_markers)
                else "pass" if any(marker in event_name for marker in pass_markers)
                else "other"
                for event_name in event_names
            }
            if "pass" in classes and "non_pass" not in classes:
                pass_only[required_flag] = sorted(event_names)

        self.assertEqual(pass_only, {})

    def test_gate_outcome_block_specs_are_registered_and_reset_stale_passes(self) -> None:
        self.assertTrue(router.GATE_OUTCOME_BLOCK_EVENT_SPECS)
        for event_name, spec in router.GATE_OUTCOME_BLOCK_EVENT_SPECS.items():
            self.assertIn(event_name, router.EXTERNAL_EVENTS)
            self.assertIn(event_name, router.GATE_OUTCOME_BLOCK_EVENTS)
            self.assertTrue(spec.get("checked_paths"))
            reset_flags = tuple(spec.get("reset_flags") or ())
            self.assertTrue(reset_flags)
            self.assertNotIn(router.EXTERNAL_EVENTS[event_name]["flag"], reset_flags)

        for event_name, clear_flags in router.GATE_OUTCOME_PASS_CLEAR_FLAGS.items():
            self.assertIn(event_name, router.EXTERNAL_EVENTS)
            self.assertTrue(clear_flags)

    def test_child_skill_gate_manifest_block_records_repair_without_approval(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.complete_material_flow(root)
        self.complete_root_contract_before_child_skill_gates(root)

        selected_skills = [
            {
                "skill_name": "model-first-function-flow",
                "decision": "required",
                "supported_capabilities": ["cap-001"],
                "gates": [
                    {
                        "gate_id": "process-model",
                        "required_approver": "process_flowguard_officer",
                        "controller_can_approve": False,
                    }
                ],
            }
        ]
        self.deliver_expected_card(root, "pm.dependency_policy")
        router.record_external_event(root, "pm_records_dependency_policy", {"allowed_dependency_actions": ["use_existing_local_skill"]})
        router.record_external_event(
            root,
            "pm_writes_capabilities_manifest",
            {"capabilities": [{"capability_id": "cap-001", "behavior": "model and gate route work"}]},
        )
        self.deliver_expected_card(root, "pm.child_skill_selection")
        router.record_external_event(root, "pm_writes_child_skill_selection", {"selected_skills": selected_skills})
        self.deliver_expected_card(root, "pm.child_skill_gate_manifest")
        router.record_external_event(root, "pm_writes_child_skill_gate_manifest", {"selected_skills": selected_skills})

        self.deliver_expected_card(root, "reviewer.child_skill_gate_manifest_review")
        router.record_external_event(
            root,
            "reviewer_blocks_child_skill_gate_manifest",
            self.role_report_envelope(
                root,
                "reviews/child_skill_gate_manifest_block",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": False,
                    "blocking_findings": ["selected skills lack compiled standard contracts"],
                    "repair_recommendation": "PM must rewrite manifest with per-gate mappings before rerun.",
                },
            ),
        )

        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["child_skill_manifest_reviewer_blocked"])
        self.assertFalse(state["flags"]["child_skill_manifest_reviewer_passed"])
        self.assertFalse(state["flags"]["child_skill_gate_manifest_written"])
        self.assertFalse(state["flags"]["child_skill_process_officer_passed"])
        self.assertFalse(state["flags"]["child_skill_product_officer_passed"])
        self.assertFalse(state["flags"]["child_skill_manifest_pm_approved_for_route"])
        self.assertTrue((run_root / "reviews" / "child_skill_gate_manifest_block.json").exists())

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertIn("pm_writes_child_skill_gate_manifest", action["allowed_external_events"])

    def test_child_skill_gate_manifest_repair_pass_clears_active_gate_block(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.complete_material_flow(root)
        self.complete_root_contract_before_child_skill_gates(root)

        selected_skills = [
            {
                "skill_name": "model-first-function-flow",
                "decision": "required",
                "supported_capabilities": ["cap-001"],
                "gates": [
                    {
                        "gate_id": "process-model",
                        "required_approver": "process_flowguard_officer",
                        "evidence_required": ["model-check-result"],
                        "controller_can_approve": False,
                    }
                ],
            }
        ]
        self.deliver_expected_card(root, "pm.dependency_policy")
        router.record_external_event(root, "pm_records_dependency_policy", {"allowed_dependency_actions": ["use_existing_local_skill"]})
        router.record_external_event(
            root,
            "pm_writes_capabilities_manifest",
            {"capabilities": [{"capability_id": "cap-001", "behavior": "model and gate route work"}]},
        )
        self.deliver_expected_card(root, "pm.child_skill_selection")
        router.record_external_event(root, "pm_writes_child_skill_selection", {"selected_skills": selected_skills})
        self.deliver_expected_card(root, "pm.child_skill_gate_manifest")
        router.record_external_event(root, "pm_writes_child_skill_gate_manifest", {"selected_skills": selected_skills})

        self.deliver_expected_card(root, "reviewer.child_skill_gate_manifest_review")
        router.record_external_event(
            root,
            "reviewer_blocks_child_skill_gate_manifest",
            self.role_report_envelope(
                root,
                "reviews/child_skill_gate_manifest_block",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": False,
                    "blocking_findings": ["selected skills lack compiled standard contracts"],
                    "repair_recommendation": "PM must rewrite manifest with per-gate mappings before rerun.",
                },
            ),
        )

        state = read_json(router.run_state_path(run_root))
        self.assertEqual(state["active_gate_outcome_block"]["event"], "reviewer_blocks_child_skill_gate_manifest")

        router.record_external_event(root, "pm_writes_child_skill_gate_manifest", {"selected_skills": selected_skills})
        self.deliver_expected_card(root, "reviewer.child_skill_gate_manifest_review")
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertIn("reviewer_passes_child_skill_gate_manifest", action["allowed_external_events"])
        self.assertIn("reviewer_blocks_child_skill_gate_manifest", action["allowed_external_events"])

        router.record_external_event(
            root,
            "reviewer_passes_child_skill_gate_manifest",
            self.role_report_envelope(
                root,
                "reviews/child_skill_gate_manifest_review_repaired",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )

        state = read_json(router.run_state_path(run_root))
        self.assertIsNone(state.get("active_gate_outcome_block"))
        self.assertFalse(state["flags"]["child_skill_manifest_reviewer_blocked"])
        self.assertTrue(state["flags"]["child_skill_manifest_reviewer_passed"])
        manifest = read_json(run_root / "child_skill_gate_manifest.json")
        self.assertTrue(manifest["approval"]["reviewer_passed"])

    def test_control_blocker_reviewer_followup_rejects_pm_origin(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.complete_material_flow(root)
        self.complete_root_contract_before_child_skill_gates(root)

        selected_skills = [
            {
                "skill_name": "model-first-function-flow",
                "decision": "required",
                "supported_capabilities": ["cap-001"],
                "gates": [
                    {
                        "gate_id": "process-model",
                        "required_approver": "process_flowguard_officer",
                        "evidence_required": ["model-check-result"],
                        "controller_can_approve": False,
                    }
                ],
            }
        ]
        self.deliver_expected_card(root, "pm.dependency_policy")
        router.record_external_event(root, "pm_records_dependency_policy", {"allowed_dependency_actions": ["use_existing_local_skill"]})
        router.record_external_event(
            root,
            "pm_writes_capabilities_manifest",
            {"capabilities": [{"capability_id": "cap-001", "behavior": "model and gate route work"}]},
        )
        self.deliver_expected_card(root, "pm.child_skill_selection")
        router.record_external_event(root, "pm_writes_child_skill_selection", {"selected_skills": selected_skills})
        self.deliver_expected_card(root, "pm.child_skill_gate_manifest")
        router.record_external_event(root, "pm_writes_child_skill_gate_manifest", {"selected_skills": selected_skills})
        self.deliver_expected_card(root, "reviewer.child_skill_gate_manifest_review")

        state = read_json(router.run_state_path(run_root))
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="Controller has no legal next action while reviewer gate result is waiting",
            action_type="controller_no_legal_next_action",
            payload={"path": self.rel(root, router.run_state_path(run_root)), "role": "controller"},
        )
        self.assertTrue(self.handle_pending_control_blocker(root))
        router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(
                root,
                "control_blocks/pm_repair_to_reviewer_gate_followup",
                self.pm_control_blocker_decision_body(
                    blocker["blocker_id"],
                    decision="repair_completed",
                    rerun_target="reviewer_passes_child_skill_gate_manifest",
                ),
            ),
        )

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertIn("reviewer_passes_child_skill_gate_manifest", action["allowed_external_events"])
        report = self.role_report_envelope(
            root,
            "reviews/child_skill_gate_manifest_review_pm_impersonation",
            {"reviewed_by_role": "human_like_reviewer", "passed": True},
        )
        pm_origin_envelope = {
            "schema_version": router.EVENT_ENVELOPE_SCHEMA,
            "event": "reviewer_passes_child_skill_gate_manifest",
            "from_role": "project_manager",
            "to_role": "controller",
            "controller_visibility": "event_envelope_only",
            **report,
        }
        with self.assertRaisesRegex(router.RouterError, "from_role mismatch"):
            router.record_external_event(root, "reviewer_passes_child_skill_gate_manifest", pm_origin_envelope)

    def test_resume_reentry_loads_state_before_resume_cards(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        router.record_external_event(root, "heartbeat_or_manual_resume_requested")

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
        self.assertEqual(action["action_type"], "rehydrate_role_agents")
        self.assertFalse(action["requires_host_spawn"])
        self.assertTrue(action["requires_host_role_rehydration"])
        self.assertTrue(action["spawn_required_only_for_replacements"])
        self.assertTrue(action["reuse_live_agents_when_active"])
        self.assertEqual(action["payload_contract"]["name"], "resume_role_rehydration_receipt")
        self.assert_payload_contract_mentions(
            action["payload_contract"],
            "rehydrated_role_agents[].role_key",
            "rehydrated_role_agents[].agent_id",
            "rehydrated_role_agents[].model_policy",
            "rehydrated_role_agents[].reasoning_effort_policy",
            "rehydrated_role_agents[].rehydrated_for_run_id",
            "rehydrated_role_agents[].rehydrated_after_resume_tick_id",
            "rehydrated_role_agents[].rehydrated_after_resume_state_loaded",
            "rehydrated_role_agents[].core_prompt_path",
            "rehydrated_role_agents[].core_prompt_hash",
            "rehydrated_role_agents[].host_liveness_status",
            "rehydrated_role_agents[].liveness_decision",
            "rehydrated_role_agents[].resume_agent_attempted",
            "rehydrated_role_agents[].bounded_wait_result",
            "rehydrated_role_agents[].bounded_wait_ms",
            "rehydrated_role_agents[].liveness_probe_batch_id",
            "rehydrated_role_agents[].liveness_probe_mode",
            "rehydrated_role_agents[].liveness_probe_started_at",
            "rehydrated_role_agents[].liveness_probe_completed_at",
            "rehydrated_role_agents[].wait_agent_timeout_treated_as_active",
            "rehydrated_role_agents[].memory_packet_path",
            "rehydrated_role_agents[].memory_packet_hash",
            "rehydrated_role_agents[].memory_missing_acknowledged",
            "rehydrated_role_agents[].replacement_seeded_from_common_run_context",
            "rehydrated_role_agents[].pm_resume_context_delivered",
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
        self.assertEqual(action["spawn_policy"], "reuse_confirmed_live_agents_spawn_only_missing_cancelled_completed_unknown_or_timeout")
        self.assertTrue(action["liveness_preflight_required"])
        self.assertTrue(action["liveness_preflight_policy"]["concurrent_probe_required"])
        self.assertTrue(action["liveness_preflight_policy"]["start_all_probes_before_waiting"])
        self.assertEqual(action["liveness_preflight_policy"]["probe_mode"], "concurrent_batch")
        self.assertEqual(action["liveness_preflight_policy"]["liveness_probe_batch_id"], action["liveness_probe_batch_id"])
        self.assertFalse(action["liveness_preflight_policy"]["timeout_unknown_is_active"])
        self.assertEqual(action["liveness_preflight_policy"]["roles_to_check"], list(router.CREW_ROLE_KEYS))
        self.assertEqual(len(action["role_rehydration_request"]), 6)
        pm_request = next(item for item in action["role_rehydration_request"] if item["role_key"] == "project_manager")
        self.assertTrue(pm_request["pm_resume_context_required"])
        self.assertIn("pm_prior_path_context", pm_request["pm_resume_context_paths"])
        with self.assertRaisesRegex(router.RouterError, "background_agents_capability_status"):
            router.apply_action(root, "rehydrate_role_agents")
        payload = self.resume_role_agent_payload(root, action)
        payload["rehydrated_role_agents"] = payload["rehydrated_role_agents"][:-1]
        with self.assertRaisesRegex(router.RouterError, "missing rehydrated live role agent records"):
            router.apply_action(root, "rehydrate_role_agents", payload)
        action = router.next_action(root)
        payload = self.resume_role_agent_payload(root, action)
        payload["rehydrated_role_agents"][0]["memory_packet_hash"] = "bad"
        with self.assertRaisesRegex(router.RouterError, "memory packet hash mismatch"):
            router.apply_action(root, "rehydrate_role_agents", payload)
        action = router.next_action(root)
        payload = self.resume_role_agent_payload(root, action)
        payload["rehydrated_role_agents"][0].update(
            {
                "rehydration_result": "live_agent_continuity_confirmed",
                "host_liveness_status": "timeout_unknown",
                "liveness_decision": "confirmed_existing_agent",
                "bounded_wait_result": "timeout_unknown",
                "wait_agent_timeout_treated_as_active": True,
            }
        )
        with self.assertRaisesRegex(router.RouterError, "timeout_unknown|wait_agent_timeout_treated_as_active"):
            router.apply_action(root, "rehydrate_role_agents", payload)
        action = router.next_action(root)
        payload = self.resume_role_agent_payload(root, action)
        payload["rehydrated_role_agents"][0]["liveness_probe_mode"] = "serial"
        with self.assertRaisesRegex(router.RouterError, "concurrent liveness probe mode"):
            router.apply_action(root, "rehydrate_role_agents", payload)
        action = router.next_action(root)
        payload = self.resume_role_agent_payload(root, action)
        payload["all_liveness_probes_started_before_wait"] = False
        with self.assertRaisesRegex(router.RouterError, "all_liveness_probes_started_before_wait"):
            router.apply_action(root, "rehydrate_role_agents", payload)
        action = router.next_action(root)
        payload = self.resume_role_agent_payload(root, action)
        payload["rehydrated_role_agents"][0].update(
            {
                "rehydration_result": "rehydrated_from_current_run_memory",
                "host_liveness_status": "active",
                "liveness_decision": "spawned_replacement_from_current_run_memory",
                "spawned_after_resume_state_loaded": True,
            }
        )
        with self.assertRaisesRegex(router.RouterError, "active host liveness must use live_agent_continuity_confirmed"):
            router.apply_action(root, "rehydrate_role_agents", payload)
        action = router.next_action(root)
        payload = self.resume_role_agent_payload(root, action)
        replaced_role = payload["rehydrated_role_agents"][0]["role_key"]
        payload["rehydrated_role_agents"][0].update(
            {
                "agent_id": f"replacement-agent-{replaced_role}",
                "rehydration_result": "rehydrated_from_current_run_memory",
                "host_liveness_status": "missing",
                "liveness_decision": "spawned_replacement_from_current_run_memory",
                "bounded_wait_result": "not_waited",
                "bounded_wait_ms": 0,
                "spawned_after_resume_state_loaded": True,
            }
        )
        router.apply_action(root, "rehydrate_role_agents", payload)
        rehydration = read_json(run_root / "continuation" / "crew_rehydration_report.json")
        self.assertEqual(rehydration["liveness_preflight"]["replacement_role_keys"], [replaced_role])
        self.assertEqual(rehydration["liveness_preflight"]["decision"], "roles_ready_after_replacement")

        router.record_external_event(root, "heartbeat_or_manual_resume_requested")
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "load_resume_state")
        router.apply_action(root, "load_resume_state")
        action = router.next_action(root)
        router.apply_action(root, "rehydrate_role_agents", self.resume_role_agent_payload(root, action))
        rehydration = read_json(run_root / "continuation" / "crew_rehydration_report.json")
        self.assertTrue(rehydration["all_six_roles_ready"])
        self.assertEqual(rehydration["liveness_preflight"]["roles_checked"], list(router.CREW_ROLE_KEYS))
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
        self.assertEqual(len(resume_receipts), 6)
        self.assertEqual({item["lifecycle_phase"] for item in resume_receipts}, {"heartbeat_rehydration"})

        self.deliver_expected_card(root, "controller.resume_reentry")
        self.deliver_expected_card(root, "pm.crew_rehydration_freshness")
        card_action = self.deliver_expected_card(root, "pm.resume_decision")
        self.assert_payload_contract_mentions(
            card_action["payload_contract"],
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
        )
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertEqual(action["label"], "controller_waits_for_pm_resume_decision")
        self.assert_payload_contract_mentions(
            action["payload_contract"],
            "pm_resume_decision_role_output",
            "decision_owner",
            "prior_path_context_review.source_paths",
            self.rel(root, run_root / "route_memory" / "pm_prior_path_context.json"),
            self.rel(root, run_root / "route_memory" / "route_history_index.json"),
        )
        progress_status = action["role_output_progress_status"]
        progress_status_path = progress_status["controller_status_packet_path"]
        self.assertIn(progress_status_path, action["allowed_reads"])
        self.assertIn(self.rel(root, run_root / "role_output_status"), progress_status_path)
        self.assertNotIn(self.rel(root, run_root / "continuation"), action["allowed_reads"])
        self.assertTrue(progress_status["default_progress_required"])
        self.assertEqual(progress_status["controller_visibility"], "metadata_only")
        self.assertFalse(progress_status["progress_is_decision_evidence"])
        self.assertEqual(
            action["payload_contract"]["progress_status"]["controller_status_packet_path"],
            progress_status_path,
        )
        self.assertIn("flowpilot_runtime.py progress-output", action["payload_contract"]["structural_requirements"][-1])

        with self.assertRaisesRegex(router.RouterError, "file-backed body path"):
            router.record_external_event(root, "pm_resume_recovery_decision_returned", {"decision": "continue_current_packet_loop"})
        with self.assertRaisesRegex(router.RouterError, "decision_owner=project_manager"):
            router.record_external_event(
                root,
                "pm_resume_recovery_decision_returned",
                self.role_decision_envelope(
                    root,
                    "continuation/pm_resume_decision_missing_owner",
                    {
                        "decision": "continue_current_packet_loop",
                        **self.prior_path_context_review(root, "Bad resume decision missing owner"),
                        "controller_reminder": {
                            "controller_only": True,
                            "controller_may_read_sealed_bodies": False,
                            "controller_may_infer_from_chat_history": False,
                            "controller_may_advance_or_close_route": False,
                        },
                    },
                ),
            )
        with self.assertRaisesRegex(router.RouterError, "prior_path_context_review.reviewed=true"):
            bad_review = self.prior_path_context_review(root, "Bad resume decision missing reviewed=true")
            bad_review["prior_path_context_review"].pop("reviewed")
            router.record_external_event(
                root,
                "pm_resume_recovery_decision_returned",
                self.role_decision_envelope(
                    root,
                    "continuation/pm_resume_decision_missing_reviewed",
                    {
                        "decision_owner": "project_manager",
                        "decision": "continue_current_packet_loop",
                        **bad_review,
                        "controller_reminder": {
                            "controller_only": True,
                            "controller_may_read_sealed_bodies": False,
                            "controller_may_infer_from_chat_history": False,
                            "controller_may_advance_or_close_route": False,
                        },
                    },
                ),
            )
        with self.assertRaisesRegex(router.RouterError, "current pm_prior_path_context.json"):
            bad_sources = self.prior_path_context_review(root, "Bad resume decision missing current PM context path")
            bad_sources["prior_path_context_review"]["source_paths"] = [
                self.rel(root, run_root / "route_memory" / "route_history_index.json")
            ]
            router.record_external_event(
                root,
                "pm_resume_recovery_decision_returned",
                self.role_decision_envelope(
                    root,
                    "continuation/pm_resume_decision_missing_pm_context_path",
                    {
                        "decision_owner": "project_manager",
                        "decision": "continue_current_packet_loop",
                        **bad_sources,
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
                "continuation/pm_resume_decision",
                {
                    "decision_owner": "project_manager",
                    "decision": "continue_current_packet_loop",
                    **self.prior_path_context_review(root, "PM resume decision considered current route memory."),
                    "controller_reminder": {
                        "controller_only": True,
                        "controller_may_read_sealed_bodies": False,
                        "controller_may_infer_from_chat_history": False,
                        "controller_may_advance_or_close_route": False,
                    },
                },
            ),
        )
        self.assertTrue((run_root / "continuation" / "pm_resume_decision.json").exists())
        decision = read_json(run_root / "continuation" / "pm_resume_decision.json")
        self.assertEqual(
            decision["source_paths"]["crew_rehydration_report"],
            self.rel(root, run_root / "continuation" / "crew_rehydration_report.json"),
        )

    def test_resume_reentry_preempts_active_control_blocker_until_pm_decision(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
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

        router.record_external_event(root, "heartbeat_or_manual_resume_requested")

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "load_resume_state")
        router.apply_action(root, "load_resume_state")
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "rehydrate_role_agents")
        router.apply_action(root, "rehydrate_role_agents", self.resume_role_agent_payload(root, action))

        self.deliver_expected_card(root, "controller.resume_reentry")
        self.deliver_expected_card(root, "pm.crew_rehydration_freshness")
        self.deliver_expected_card(root, "pm.resume_decision")
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertEqual(action["label"], "controller_waits_for_pm_resume_decision")

        router.record_external_event(
            root,
            "pm_resume_recovery_decision_returned",
            self.role_decision_envelope(
                root,
                "continuation/pm_resume_decision_with_deferred_blocker",
                {
                    "decision_owner": "project_manager",
                    "decision": "continue_current_packet_loop",
                    "explicit_recovery_evidence_recorded": True,
                    **self.prior_path_context_review(root, "PM resumes after current-run state and roles were rehydrated."),
                    "controller_reminder": {
                        "controller_only": True,
                        "controller_may_read_sealed_bodies": False,
                        "controller_may_infer_from_chat_history": False,
                        "controller_may_advance_or_close_route": False,
                    },
                },
            ),
        )
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "handle_control_blocker")
        self.assertEqual(action["blocker_id"], blocker["blocker_id"])

    def test_mid_run_role_liveness_fault_uses_unified_recovery_before_normal_work(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        state = read_json(router.run_state_path(run_root))
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="Controller has a deferred blocker while worker_a is missing",
            action_type="controller_no_legal_next_action",
            payload={"path": self.rel(root, router.run_state_path(run_root)), "role": "controller"},
        )

        result = router.record_external_event(
            root,
            "controller_reports_role_liveness_fault",
            {
                "role_key": "worker_a",
                "host_liveness_status": "missing",
                "detected_by": "controller",
            },
        )

        self.assertTrue(result["role_recovery_requested"])
        transaction = result["role_recovery_transaction"]
        self.assertEqual(transaction["trigger_source"], "mid_run_liveness_fault")
        self.assertEqual(transaction["target_role_keys"], ["worker_a"])

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "load_role_recovery_state")
        self.assertEqual(action["recovery_priority"], "preempt_normal_work")
        router.apply_action(root, "load_role_recovery_state")

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "recover_role_agents")
        self.assertEqual(action["target_role_keys"], ["worker_a"])
        self.assertIn("restore_old_agent", action["recovery_ladder"])
        self.assertIn("full_crew_recycle", action["recovery_ladder"])
        self.assertFalse(action["normal_waits_allowed_before_recovery"])
        router.apply_action(root, "recover_role_agents", self.role_recovery_agent_payload(root, action, role="worker_a"))

        report = read_json(run_root / "continuation" / "role_recovery_report.json")
        self.assertEqual(report["schema_version"], "flowpilot.role_recovery_report.v1")
        self.assertTrue(report["all_six_roles_ready"])
        self.assertTrue(report["pm_decision_required_before_normal_work"])
        self.assertEqual(report["role_records"][0]["recovery_result"], "targeted_replacement_spawned")
        crew = read_json(run_root / "crew_ledger.json")
        worker_slot = next(slot for slot in crew["role_slots"] if slot["role_key"] == "worker_a")
        self.assertEqual(worker_slot["last_role_recovery_result"], "targeted_replacement_spawned")
        self.assertTrue(worker_slot["superseded_agent_output_quarantined"])

        self.deliver_expected_card(root, "controller.resume_reentry")
        self.deliver_expected_card(root, "pm.crew_rehydration_freshness")
        self.deliver_expected_card(root, "pm.resume_decision")
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertEqual(action["label"], "controller_waits_for_pm_resume_decision")

        router.record_external_event(
            root,
            "pm_resume_recovery_decision_returned",
            self.role_decision_envelope(
                root,
                "continuation/pm_resume_decision_after_role_recovery",
                {
                    "decision_owner": "project_manager",
                    "decision": "continue_current_packet_loop",
                    "explicit_recovery_evidence_recorded": True,
                    **self.prior_path_context_review(root, "PM reviewed the role recovery report before continuing."),
                    "controller_reminder": {
                        "controller_only": True,
                        "controller_may_read_sealed_bodies": False,
                        "controller_may_infer_from_chat_history": False,
                        "controller_may_advance_or_close_route": False,
                    },
                },
            ),
        )
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "handle_control_blocker")
        self.assertEqual(action["blocker_id"], blocker["blocker_id"])

    def test_resume_ambiguous_state_blocks_continue_without_recovery_evidence(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        (run_root / "crew_memory" / "worker_b.json").unlink()

        router.record_external_event(root, "heartbeat_or_manual_resume_requested")
        self.assertEqual(self.next_after_display_sync(root)["action_type"], "load_resume_state")
        router.apply_action(root, "load_resume_state")
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "rehydrate_role_agents")
        self.assertEqual(action["memory_missing_role_keys"], ["worker_b"])
        router.apply_action(root, "rehydrate_role_agents", self.resume_role_agent_payload(root, action))
        self.deliver_expected_card(root, "controller.resume_reentry")
        self.deliver_expected_card(root, "pm.crew_rehydration_freshness")
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

    def test_heartbeat_alive_status_still_enters_router_resume_path(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)

        result = router.record_external_event(
            root,
            "heartbeat_or_manual_resume_requested",
            {"source": "heartbeat", "work_chain_status": "alive"},
        )

        self.assertTrue(result["resume_requested"])
        self.assertTrue(result["heartbeat_tick"]["router_reentry_required"])
        self.assertFalse(result["heartbeat_tick"]["self_keepalive_allowed"])
        self.assertEqual(result["heartbeat_tick"]["work_chain_status_trust"], "diagnostic_only")
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "load_resume_state")

    def test_heartbeat_startup_records_one_minute_active_binding_for_resume_reentry(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root, startup_answers=HEARTBEAT_STARTUP_ANSWERS)
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "create_heartbeat_automation")
        self.assertTrue(action["requires_host_automation"])
        self.assertEqual(action["automation_update_request"]["kind"], "heartbeat")
        self.assertNotIn("otherwise keep the run alive", action["automation_update_request"]["prompt"])
        self.assertIn("Every heartbeat wake must record heartbeat_or_manual_resume_requested", action["automation_update_request"]["prompt"])
        self.assertEqual(action["automation_update_request"]["rrule"], "FREQ=MINUTELY;INTERVAL=1")
        self.assertEqual(action["expected_payload"]["route_heartbeat_interval_minutes"], 1)
        self.assertTrue(action["proof_required_before_apply"])
        self.assertEqual(action["payload_contract"]["allowed_values"]["route_heartbeat_interval_minutes"], [1])
        self.assertEqual(action["payload_contract"]["allowed_values"]["host_automation_verified"], [True])
        self.assertEqual(action["payload_contract"]["allowed_values"]["host_automation_proof.heartbeat_bound_to_current_run"], [True])
        with self.assertRaisesRegex(router.RouterError, "host_automation_proof"):
            router.apply_action(
                root,
                "create_heartbeat_automation",
                {
                    "route_heartbeat_interval_minutes": 1,
                    "host_automation_id": "codex-test-heartbeat",
                    "host_automation_verified": True,
                },
            )
        router.apply_action(root, "create_heartbeat_automation", self.heartbeat_binding_payload(root))
        self.complete_startup_activation(root)

        binding_path = run_root / "continuation" / "continuation_binding.json"
        self.assertTrue(binding_path.exists())
        binding = read_json(binding_path)
        self.assertEqual(binding["run_id"], read_json(run_root / "router_state.json")["run_id"])
        self.assertEqual(binding["mode"], "scheduled_heartbeat")
        self.assertEqual(binding["route_heartbeat_interval_minutes"], 1)
        self.assertTrue(binding["heartbeat_active"])
        self.assertEqual(binding["host_automation_id"], "codex-test-heartbeat")
        self.assertTrue(binding["host_automation_verified"])
        self.assertEqual(binding["host_automation_proof"]["source_kind"], "host_receipt")

        router.record_external_event(root, "heartbeat_or_manual_resume_requested", {"source": "heartbeat", "work_chain_status": "broken_or_unknown"})
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "load_resume_state")
        self.assertEqual(
            action["resume_next_recipient_from_packet_ledger"]["controller_next_action"],
            "relay_packet_envelope_to_recorded_recipient",
        )
        self.assertEqual(action["resume_next_recipient_from_packet_ledger"]["next_recipient_role"], "project_manager")
        router.apply_action(root, "load_resume_state")
        resume_evidence = read_json(run_root / "continuation" / "resume_reentry.json")
        self.assertIn("continuation_binding", resume_evidence["loaded_paths"])
        self.assertEqual(resume_evidence["loaded_paths"]["continuation_binding"], self.rel(root, binding_path))
        self.assertEqual(resume_evidence["resume_next_recipient_from_packet_ledger"]["source"], "packet_ledger")

    def test_current_node_packet_relay_uses_router_direct_dispatch(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)

        packet = packet_runtime.create_packet(
            root,
            packet_id="node-packet-without-plan",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="current node work",
            metadata={"route_version": 1},
        )
        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "pm_registers_current_node_packet",
                {
                    "packet_id": "node-packet-without-plan",
                    "packet_envelope_path": packet["body_path"].replace("packet_body.md", "packet_envelope.json"),
                },
            )

        self.deliver_current_node_cards(root)

        packet = packet_runtime.create_packet(
            root,
            packet_id="node-packet-001",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="current node work",
            metadata={"route_version": 1},
        )
        router.record_external_event(
            root,
            "pm_registers_current_node_packet",
            {"packet_id": "node-packet-001", "packet_envelope_path": packet["body_path"].replace("packet_body.md", "packet_envelope.json")},
        )
        resume_next = router._derive_resume_next_recipient_from_packet_ledger(self.run_root_for(root))
        self.assertEqual(resume_next["controller_next_action"], "relay_packet_envelope_to_recorded_recipient")
        self.assertEqual(resume_next["next_recipient_role"], "worker_a")

        run_root = self.run_root_for(root)
        state_before = read_json(router.run_state_path(run_root))
        ledger_checks_before = int(state_before.get("ledger_checks", 0))
        ledger_requests_before = int(state_before.get("ledger_check_requests", 0))
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "relay_current_node_packet")
        self.assertTrue(action["combined_ledger_check_and_relay"])
        self.assertTrue(action["ledger_check_receipt_required"])
        self.assertFalse(action["sealed_body_reads_allowed"])
        router.apply_action(root, "relay_current_node_packet")

        state_after = read_json(router.run_state_path(run_root))
        self.assertEqual(state_after["ledger_checks"], ledger_checks_before + 1)
        self.assertEqual(state_after["ledger_check_requests"], ledger_requests_before + 1)
        self.assertFalse(state_after.get("ledger_check_requested"))
        envelope = read_json(root / packet["body_path"].replace("packet_body.md", "packet_envelope.json"))
        self.assertEqual(envelope["controller_relay"]["relayed_to_role"], "worker_a")
        self.assertFalse(envelope["controller_relay"]["body_was_read_by_controller"])

    def test_current_node_parallel_batch_waits_for_all_results_before_review(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.deliver_current_node_cards(root)

        packet_paths: dict[str, str] = {}
        for packet_id, role in (("node-batch-worker-a", "worker_a"), ("node-batch-worker-b", "worker_b")):
            packet = packet_runtime.create_packet(
                root,
                packet_id=packet_id,
                from_role="project_manager",
                to_role=role,
                node_id="node-001",
                body_text=f"current node work for {role}",
                metadata={"route_version": 1},
            )
            packet_paths[packet_id] = packet["body_path"].replace("packet_body.md", "packet_envelope.json")

        router.record_external_event(
            root,
            "pm_registers_current_node_packet",
            {
                "batch_id": "node-parallel-batch-001",
                "packets": [
                    {"packet_id": packet_id, "packet_envelope_path": packet_path}
                    for packet_id, packet_path in packet_paths.items()
                ],
            },
        )
        run_root = self.run_root_for(root)
        batch_index = read_json(run_root / "routes" / "route-001" / "nodes" / "node-001" / "current_node_packet_batch.json")
        self.assertEqual(batch_index["batch_id"], "node-parallel-batch-001")
        self.assertEqual(len(batch_index["packets"]), 2)

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_current_node_packet")
        self.assertEqual(sorted(action["packet_ids"]), ["node-batch-worker-a", "node-batch-worker-b"])
        router.apply_action(root, "relay_current_node_packet")

        results: dict[str, str] = {}
        packet_a = read_json(root / packet_paths["node-batch-worker-a"])
        packet_runtime.read_packet_body_for_role(root, packet_a, role="worker_a")
        result_a = packet_runtime.write_result(
            root,
            packet_envelope=packet_a,
            completed_by_role="worker_a",
            completed_by_agent_id="agent-worker-a",
            result_body_text="worker a result",
            next_recipient="project_manager",
        )
        results["node-batch-worker-a"] = result_a["result_body_path"].replace("result_body.md", "result_envelope.json")
        router.record_external_event(
            root,
            "worker_current_node_result_returned",
            {"packet_id": "node-batch-worker-a", "result_envelope_path": results["node-batch-worker-a"]},
        )
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertEqual(action["allowed_external_events"], ["worker_current_node_result_returned"])
        self.assertIn("worker_b", action["to_role"])

        packet_b = read_json(root / packet_paths["node-batch-worker-b"])
        packet_runtime.read_packet_body_for_role(root, packet_b, role="worker_b")
        result_b = packet_runtime.write_result(
            root,
            packet_envelope=packet_b,
            completed_by_role="worker_b",
            completed_by_agent_id="agent-worker-b",
            result_body_text="worker b result",
            next_recipient="project_manager",
        )
        results["node-batch-worker-b"] = result_b["result_body_path"].replace("result_body.md", "result_envelope.json")
        router.record_external_event(
            root,
            "worker_current_node_result_returned",
            {"packet_id": "node-batch-worker-b", "result_envelope_path": results["node-batch-worker-b"]},
        )
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_current_node_result_to_pm")
        self.assertEqual(sorted(action["packet_ids"]), ["node-batch-worker-a", "node-batch-worker-b"])
        router.apply_action(root, "relay_current_node_result_to_pm")

        for result_path in results.values():
            packet_runtime.read_result_body_for_role(root, read_json(root / result_path), role="project_manager")
        router.record_external_event(
            root,
            "pm_records_current_node_result_disposition",
            {
                "decided_by_role": "project_manager",
                "decision": "absorbed",
                "decision_reason": "PM absorbed parallel worker results for the formal node-completion gate.",
            },
        )
        self.deliver_expected_card(root, "reviewer.worker_result_review")
        router.record_external_event(
            root,
            "current_node_reviewer_passes_result",
            self.role_report_envelope(
                root,
                "reviews/current_node_parallel_result",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": True,
                    "agent_role_map": {"agent-worker-a": "worker_a", "agent-worker-b": "worker_b"},
                },
            ),
        )
        runtime_audit = read_json(
            run_root / "routes" / "route-001" / "nodes" / "node-001" / "reviews" / "current_node_packet_runtime_audit.json"
        )
        self.assertTrue(runtime_audit["passed"])
        self.assertEqual(runtime_audit["batch_id"], "node-parallel-batch-001")
        self.assertEqual(runtime_audit["packet_count"], 2)
        self.assertEqual(sorted(runtime_audit["reviewed_packet_ids"]), ["node-batch-worker-a", "node-batch-worker-b"])

    def test_current_node_worker_packet_requires_active_child_skill_binding_projection(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)

        active_bindings = [
            {
                "binding_id": "frontend-design:node-001:implementation",
                "source_skill": "frontend-design",
                "source_path": "skills/frontend-design/SKILL.md",
                "referenced_paths": ["skills/frontend-design/references/ui.md"],
                "applies_to_this_node": True,
                "node_slice_scope": "current node UI implementation",
                "applies_to_packet_ids": ["node-packet-bound"],
                "must_open_source_skill": True,
                "selected_standard_ids": ["frontend-design.verify.rendered-qa"],
                "stricter_than_pm_packet": True,
                "precedence_rule": "PM packet is the minimum floor; stricter child-skill requirements apply.",
                "result_evidence_required": True,
                "reviewer_check_required": True,
            }
        ]
        self.deliver_current_node_cards(root, active_child_skill_bindings=active_bindings)
        run_root = self.run_root_for(root)
        plan = read_json(run_root / "routes" / "route-001" / "nodes" / "node-001" / "node_acceptance_plan.json")
        self.assertEqual(plan["active_child_skill_bindings"], active_bindings)

        packet = packet_runtime.create_packet(
            root,
            packet_id="node-packet-missing-binding",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="current node work",
            metadata={"route_version": 1},
        )
        packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
        with self.assertRaisesRegex(router.RouterError, "active child skill bindings"):
            router.record_external_event(
                root,
                "pm_registers_current_node_packet",
                {"packet_id": "node-packet-missing-binding", "packet_envelope_path": packet_path},
            )

        packet = packet_runtime.create_packet(
            root,
            packet_id="node-packet-bound",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="current node work",
            metadata={
                "route_version": 1,
                "active_child_skill_bindings": active_bindings,
                "child_skill_use_instruction_written": True,
                "active_child_skill_source_paths_allowed": [
                    "skills/frontend-design/SKILL.md",
                    "skills/frontend-design/references/ui.md",
                ],
            },
        )
        packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
        router.record_external_event(
            root,
            "pm_registers_current_node_packet",
            {"packet_id": "node-packet-bound", "packet_envelope_path": packet_path},
        )
        grant = read_json(run_root / "routes" / "route-001" / "nodes" / "node-001" / "current_node_write_grant.json")
        self.assertTrue(grant["active_child_skill_bindings_declared"])
        self.assertEqual(
            grant["active_child_skill_source_paths"],
            [
                "skills/frontend-design/SKILL.md",
                "skills/frontend-design/references/ui.md",
            ],
        )

    def test_current_node_completion_requires_reviewer_passed_packet_audit(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.deliver_current_node_cards(root)

        packet = packet_runtime.create_packet(
            root,
            packet_id="node-packet-002",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="current node work",
            metadata={"route_version": 1},
        )
        packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
        router.record_external_event(root, "pm_registers_current_node_packet", {"packet_id": "node-packet-002", "packet_envelope_path": packet_path})
        self.apply_until_action(root, "relay_current_node_packet")

        relayed_packet = read_json(root / packet_path)
        packet_runtime.read_packet_body_for_role(root, relayed_packet, role="worker_a")
        result = packet_runtime.write_result(
            root,
            packet_envelope=read_json(root / packet_path),
            completed_by_role="worker_a",
            completed_by_agent_id="agent-worker-a-1",
            result_body_text="reviewable result",
            next_recipient="project_manager",
        )
        result_path = result["result_body_path"].replace("result_body.md", "result_envelope.json")

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_completes_current_node_from_reviewed_result")

        router.record_external_event(root, "worker_current_node_result_returned", {"packet_id": "node-packet-002", "result_envelope_path": result_path})
        self.absorb_current_node_results_with_pm(root, [result_path])
        self.deliver_expected_card(root, "reviewer.worker_result_review")

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_completes_current_node_from_reviewed_result")

        router.record_external_event(
            root,
            "current_node_reviewer_passes_result",
            self.role_report_envelope(
                root,
                "reviews/current_node_result_agent_a_1",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": True,
                    "agent_role_map": {"agent-worker-a-1": "worker_a"},
                },
            ),
        )
        self.complete_parent_backward_replay_if_due(root)
        router.record_external_event(root, "pm_completes_current_node_from_reviewed_result")

        current = read_json(root / ".flowpilot" / "current.json")
        run_root = root / current["current_run_root"]
        frontier = read_json(root / current["current_run_root"] / "execution_frontier.json")
        self.assertEqual(frontier["status"], "node_completed_by_pm")
        self.assertIn("node-001", frontier["completed_nodes"])

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_records_final_route_wide_ledger_clean")
        self.complete_evidence_quality_package(root)
        self.complete_final_ledger_and_terminal_replay(root)
        self.deliver_expected_card(root, "pm.closure")

    def test_node_completion_idempotency_is_scoped_to_active_node(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        router.record_external_event(
            root,
            "pm_activates_reviewed_route",
            {
                "route_id": "route-001",
                "active_node_id": "node-001",
                "route_version": 1,
                "route": {
                    "schema_version": "flowpilot.route.v1",
                    "route_id": "route-001",
                    "route_version": 1,
                    "active_node_id": "node-001",
                    "nodes": [
                        {"node_id": "node-001", "status": "active", "title": "First node"},
                        {"node_id": "node-002", "status": "pending", "title": "Second node"},
                    ],
                },
            },
        )

        def complete_active_node(node_id: str, packet_id: str, agent_id: str) -> dict:
            self.deliver_current_node_cards(root)
            packet = packet_runtime.create_packet(
                root,
                packet_id=packet_id,
                from_role="project_manager",
                to_role="worker_a",
                node_id=node_id,
                body_text=f"{node_id} work",
                metadata={"route_version": 1},
            )
            packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
            router.record_external_event(root, "pm_registers_current_node_packet", {"packet_id": packet_id, "packet_envelope_path": packet_path})
            self.apply_until_action(root, "relay_current_node_packet")
            packet_runtime.read_packet_body_for_role(root, read_json(root / packet_path), role="worker_a")
            result = packet_runtime.write_result(
                root,
                packet_envelope=read_json(root / packet_path),
                completed_by_role="worker_a",
                completed_by_agent_id=agent_id,
                result_body_text=f"{node_id} result",
                next_recipient="project_manager",
            )
            result_path = result["result_body_path"].replace("result_body.md", "result_envelope.json")
            router.record_external_event(root, "worker_current_node_result_returned", {"packet_id": packet_id, "result_envelope_path": result_path})
            self.absorb_current_node_results_with_pm(root, [result_path])
            self.deliver_expected_card(root, "reviewer.worker_result_review")
            router.record_external_event(
                root,
                "current_node_reviewer_passes_result",
                self.role_report_envelope(
                    root,
                    f"reviews/current_node_result_{node_id}",
                    {
                        "reviewed_by_role": "human_like_reviewer",
                        "passed": True,
                        "agent_role_map": {agent_id: "worker_a"},
                    },
                ),
            )
            self.complete_parent_backward_replay_if_due(root)
            return router.record_external_event(root, "pm_completes_current_node_from_reviewed_result", {"node_id": node_id})

        first_result = complete_active_node("node-001", "node-packet-first", "agent-worker-first")
        self.assertNotIn("already_recorded", first_result)
        first_ledger_path = run_root / "routes" / "route-001" / "nodes" / "node-001" / "node_completion_ledger.json"
        self.assertTrue(first_ledger_path.exists())
        frontier = read_json(run_root / "execution_frontier.json")
        self.assertEqual(frontier["active_node_id"], "node-002")
        self.assertIn("node-001", frontier["completed_nodes"])
        self.assertFalse(read_json(router.run_state_path(run_root))["flags"]["node_completed_by_pm"])

        stale_state = read_json(router.run_state_path(run_root))
        stale_state["flags"]["node_completed_by_pm"] = True
        stale_state["flags"]["node_completion_ledger_updated"] = False
        router.run_state_path(run_root).write_text(json.dumps(stale_state, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        second_result = complete_active_node("node-002", "node-packet-second", "agent-worker-second")
        self.assertNotIn("already_recorded", second_result)
        second_ledger_path = run_root / "routes" / "route-001" / "nodes" / "node-002" / "node_completion_ledger.json"
        self.assertTrue(second_ledger_path.exists())
        frontier = read_json(run_root / "execution_frontier.json")
        self.assertEqual(frontier["active_node_id"], "node-002")
        self.assertEqual(frontier["status"], "node_completed_by_pm")
        self.assertIn("node-002", frontier["completed_nodes"])

    def test_current_node_result_relay_combines_ledger_check_with_relay(self) -> None:
        root = self.make_project()
        run_root, _packet_path, result_path = self.prepare_current_node_result_for_review(
            root,
            packet_id="node-packet-combined-result-relay",
            deliver_review_card=False,
            record_result_return=False,
        )
        state_before = read_json(router.run_state_path(run_root))
        ledger_checks_before = int(state_before.get("ledger_checks", 0))
        ledger_requests_before = int(state_before.get("ledger_check_requests", 0))

        router.record_external_event(
            root,
            "worker_current_node_result_returned",
            {
                "packet_id": "node-packet-combined-result-relay",
                "result_envelope_path": result_path,
            },
        )
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "relay_current_node_result_to_pm")
        self.assertTrue(action["combined_ledger_check_and_relay"])
        self.assertTrue(action["ledger_check_receipt_required"])
        self.assertFalse(action["sealed_body_reads_allowed"])
        self.assertTrue(any(path.endswith("packet_ledger.json") for path in action["allowed_reads"]))
        self.assertTrue(any(path.endswith("packet_ledger.json") for path in action["allowed_writes"]))

        router.apply_action(root, "relay_current_node_result_to_pm")

        state_after = read_json(router.run_state_path(run_root))
        self.assertEqual(state_after["ledger_checks"], ledger_checks_before + 1)
        self.assertEqual(state_after["ledger_check_requests"], ledger_requests_before + 1)
        self.assertFalse(state_after.get("ledger_check_requested"))
        self.assertTrue(state_after["flags"]["current_node_result_relayed_to_pm"])

        relayed_result = packet_runtime.load_envelope(root, result_path)
        self.assertEqual(relayed_result["controller_relay"]["relayed_to_role"], "project_manager")
        self.assertFalse(relayed_result["controller_relay"]["body_was_read_by_controller"])

    def test_current_node_packet_and_result_accept_safe_envelope_aliases(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.deliver_current_node_cards(root)

        packet = packet_runtime.create_packet(
            root,
            packet_id="node-packet-aliases",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="current node work",
            metadata={"route_version": 1},
        )
        packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
        packet_file = root / packet_path
        packet_envelope = read_json(packet_file)
        packet_envelope["packet_body_path"] = packet_envelope.pop("body_path")
        packet_envelope["packet_body_hash"] = packet_envelope.pop("body_hash")
        packet_file.write_text(json.dumps(packet_envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        router.record_external_event(root, "pm_registers_current_node_packet", {"packet_id": "node-packet-aliases", "packet_envelope_path": packet_path})
        self.apply_until_action(root, "relay_current_node_packet")
        relayed_packet = packet_runtime.load_envelope(root, packet_path)
        self.assertIn("body_path", relayed_packet)
        packet_runtime.read_packet_body_for_role(root, relayed_packet, role="worker_a")

        result = packet_runtime.write_result(
            root,
            packet_envelope=relayed_packet,
            completed_by_role="worker_a",
            completed_by_agent_id="agent-worker-aliases",
            result_body_text="reviewable result",
            next_recipient="project_manager",
        )
        result_path = result["result_body_path"].replace("result_body.md", "result_envelope.json")
        result_file = root / result_path
        result_envelope = read_json(result_file)
        result_envelope["body_path"] = result_envelope.pop("result_body_path")
        result_envelope["body_hash"] = result_envelope.pop("result_body_hash")
        result_envelope["to_role"] = result_envelope.pop("next_recipient")
        result_file.write_text(json.dumps(result_envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        router.record_external_event(root, "worker_current_node_result_returned", {"packet_id": "node-packet-aliases", "result_envelope_path": result_path})
        self.absorb_current_node_results_with_pm(root, [result_path])
        self.deliver_expected_card(root, "reviewer.worker_result_review")
        relayed_result = packet_runtime.load_envelope(root, result_path)
        self.assertIn("result_body_path", relayed_result)
        self.assertEqual(relayed_result["next_recipient"], "project_manager")

        router.record_external_event(
            root,
            "current_node_reviewer_passes_result",
            self.role_report_envelope(
                root,
                "reviews/current_node_result_aliases",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": True,
                    "agent_role_map": {"agent-worker-aliases": "worker_a"},
                },
            ),
        )

    def test_current_node_result_decision_requires_review_card_after_result_relay(self) -> None:
        root = self.make_project()
        _, _, result_path = self.prepare_current_node_result_for_review(
            root,
            packet_id="node-packet-review-card-required",
            deliver_review_card=False,
        )

        with self.assertRaisesRegex(router.RouterError, "reviewer_worker_result_card_delivered"):
            router.record_external_event(
                root,
                "current_node_reviewer_passes_result",
                self.role_report_envelope(
                    root,
                    "reviews/current_node_result_before_card",
                    {
                        "reviewed_by_role": "human_like_reviewer",
                        "passed": True,
                        "agent_role_map": {"agent-worker-a": "worker_a"},
                    },
                ),
            )
        with self.assertRaisesRegex(router.RouterError, "reviewer_worker_result_card_delivered"):
            router.record_external_event(root, "current_node_reviewer_blocks_result")

        self.deliver_expected_card(root, "reviewer.worker_result_review")
        router.record_external_event(
            root,
            "current_node_reviewer_passes_result",
            self.role_report_envelope(
                root,
                "reviews/current_node_result_after_card",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": True,
                    "agent_role_map": {"agent-worker-a": "worker_a"},
                },
            ),
        )

    def test_no_legal_next_action_materializes_pm_decision_control_blocker(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)

        for flag in list(state["flags"]):
            state["flags"][flag] = True
        for terminal_flag in (
            "run_cancelled_by_user",
            "run_stopped_by_user",
            "startup_protocol_dead_end_declared",
            "resume_reentry_requested",
        ):
            state["flags"][terminal_flag] = False
        state["status"] = "controller_ready"
        state["phase"] = "route_loop"
        state["pending_action"] = None
        state["active_control_blocker"] = None
        state["latest_control_blocker_path"] = None
        state["control_blockers"] = []
        state["resolved_control_blockers"] = []
        route_memory = run_root / "route_memory"
        route_memory.mkdir(parents=True, exist_ok=True)
        router.write_json(route_memory / "route_history_index.json", {"schema_version": "test", "routes": []})
        router.write_json(route_memory / "pm_prior_path_context.json", {"schema_version": "test", "reviewed": True})
        router._write_startup_mechanical_audit(root, run_root, state, {})  # type: ignore[attr-defined]
        router.write_json(state_path, state)

        action = self.next_after_display_sync(root)

        self.assertEqual(action["action_type"], "handle_control_blocker")
        self.assertEqual(action["to_role"], "project_manager")
        self.assertEqual(action["handling_lane"], "pm_repair_decision_required")
        self.assertTrue(action["pm_decision_required"])
        self.assertFalse(action["sealed_body_reads_allowed"])
        state = read_json(state_path)
        blocker = state["active_control_blocker"]
        self.assertEqual(blocker["delivery_status"], "pending")
        blocker_path = self.control_blocker_path(root, blocker)
        self.assertTrue(blocker_path.exists())
        saved = read_json(blocker_path)
        self.assertEqual(saved["source"], "router_no_legal_next_action")
        self.assertEqual(saved["originating_action_type"], "controller_no_legal_next_action")
        self.assertEqual(saved["target_role"], "project_manager")
        self.assertTrue(saved["pm_decision_required"])
        self.assertEqual(saved["allowed_resolution_events"], ["pm_records_control_blocker_repair_decision"])
        self.assertIn("advance route state", " ".join(saved["controller_forbidden_actions"]))
        self.assertTrue((root / saved["sealed_repair_packet_path"]).exists())

    def test_router_hard_rejection_returns_control_plane_reissue_action(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-control-reissue")

        with self.assertRaises(router.RouterError) as raised:
            router.record_external_event(
                root,
                "current_node_reviewer_passes_result",
                self.role_report_envelope(
                    root,
                    "reviews/current_node_result_missing_passed",
                    {
                        "reviewed_by_role": "human_like_reviewer",
                        "agent_role_map": {"agent-worker-a": "worker_a"},
                    },
                ),
            )

        blocker = raised.exception.control_blocker
        self.assertIsInstance(blocker, dict)
        self.assertEqual(blocker["handling_lane"], "control_plane_reissue")
        self.assertEqual(blocker["target_role"], "human_like_reviewer")
        blocker_path = self.control_blocker_path(root, blocker)
        self.assertTrue(blocker_path.exists())
        saved = read_json(blocker_path)
        self.assertIn("same-role reissue", saved["controller_instruction"])
        self.assertNotIn("error_message", saved)
        self.assertNotIn("source_paths", saved)
        sealed_packet = root / saved["sealed_repair_packet_path"]
        self.assertTrue(sealed_packet.exists())
        self.assertEqual(read_json(sealed_packet)["target_role"], "human_like_reviewer")
        self.assertFalse(saved["pm_decision_required"])
        self.assertEqual(saved["skill_observation_reminder"]["suggested_kind"], "controller_compensation")

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "handle_control_blocker")
        self.assertEqual(action["to_role"], "human_like_reviewer")
        self.assertEqual(action["next_step_contract"]["recipient_role"], "human_like_reviewer")
        self.assertFalse(action["next_step_contract"]["sealed_body_reads_allowed"])
        self.assertEqual(action["handling_lane"], "control_plane_reissue")
        self.assertIn("sealed_repair_packet_path", action)
        self.assertNotIn("controller_delivery_body", action)
        self.assertIn("sealed", " ".join(action["controller_forbidden_actions"]))
        self.assertTrue(action["skill_observation_reminder"]["should_consider_recording"])
        router.apply_action(root, "handle_control_blocker")

        delivered = read_json(blocker_path)
        self.assertEqual(delivered["delivery_status"], "delivered")
        self.assertEqual(delivered["delivered_to_role"], "human_like_reviewer")

        router.record_external_event(
            root,
            "current_node_reviewer_passes_result",
            self.role_report_envelope(
                root,
                "reviews/current_node_result_reissued",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": True,
                    "agent_role_map": {"agent-worker-a": "worker_a"},
                },
            ),
        )
        state = read_json(router.run_state_path(router.active_run_root(root)))  # type: ignore[arg-type]
        self.assertIsNone(state["active_control_blocker"])

    def test_already_recorded_event_can_resolve_delivered_control_blocker(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-control-reissue-race")

        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "current_node_reviewer_passes_result",
                self.role_report_envelope(
                    root,
                    "reviews/current_node_result_missing_passed_race",
                    {
                        "reviewed_by_role": "human_like_reviewer",
                        "agent_role_map": {"agent-worker-a": "worker_a"},
                    },
                ),
            )

        reissued_payload = self.role_report_envelope(
            root,
            "reviews/current_node_result_reissued_before_blocker_delivery",
            {
                "reviewed_by_role": "human_like_reviewer",
                "passed": True,
                "agent_role_map": {"agent-worker-a": "worker_a"},
            },
        )
        router.record_external_event(root, "current_node_reviewer_passes_result", reissued_payload)

        state = read_json(router.run_state_path(router.active_run_root(root)))  # type: ignore[arg-type]
        self.assertEqual(state["active_control_blocker"]["delivery_status"], "pending")

        router.next_action(root)
        router.apply_action(root, "handle_control_blocker")
        state = read_json(router.run_state_path(router.active_run_root(root)))  # type: ignore[arg-type]
        self.assertEqual(state["active_control_blocker"]["delivery_status"], "delivered")

        result = router.record_external_event(root, "current_node_reviewer_passes_result", reissued_payload)

        self.assertTrue(result["already_recorded"])
        self.assertTrue(result["control_blocker_resolved"])
        state = read_json(router.run_state_path(router.active_run_root(root)))  # type: ignore[arg-type]
        self.assertIsNone(state["active_control_blocker"])
        self.assertIsNone(state["latest_control_blocker_path"])
        self.assertEqual(len(state["resolved_control_blockers"]), 1)

    def test_already_recorded_event_does_not_resolve_pm_required_control_blocker(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)
        state["flags"]["continuation_binding_recorded"] = True
        state["events"].append(
            {
                "event": "host_records_heartbeat_binding",
                "summary": "Host recorded the active run heartbeat/manual-resume binding before startup fact review.",
                "payload": {},
                "recorded_at": "2026-05-05T00:00:00Z",
            }
        )
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="envelope payload leaked role body fields to Controller: passed",
            event="host_records_heartbeat_binding",
            payload={"from_role": "host", "passed": True},
        )
        self.assertEqual(blocker["handling_lane"], "fatal_protocol_violation")

        self.assertTrue(self.handle_pending_control_blocker(root))
        result = router.record_external_event(root, "host_records_heartbeat_binding")

        self.assertTrue(result["already_recorded"])
        self.assertNotIn("control_blocker_resolved", result)
        state = read_json(state_path)
        self.assertEqual(state["active_control_blocker"]["blocker_id"], blocker["blocker_id"])
        self.assertEqual(state["active_control_blocker"]["delivery_status"], "delivered")
        self.assertEqual(state["latest_control_blocker_path"], blocker["blocker_artifact_path"])

    def test_already_recorded_event_resolves_fatal_control_blocker_after_pm_repair_decision(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)
        state["flags"]["continuation_binding_recorded"] = True
        state["events"].append(
            {
                "event": "host_records_heartbeat_binding",
                "summary": "Host recorded the active run heartbeat/manual-resume binding before startup fact review.",
                "payload": {},
                "recorded_at": "2026-05-05T00:00:00Z",
            }
        )
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="envelope payload leaked role body fields to Controller: passed",
            event="host_records_heartbeat_binding",
            payload={"from_role": "host", "passed": True},
        )
        self.assertEqual(blocker["handling_lane"], "fatal_protocol_violation")

        self.assertTrue(self.handle_pending_control_blocker(root))
        router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(
                root,
                "control_blocks/fatal_pm_repair_decision",
                self.pm_control_blocker_decision_body(
                    blocker["blocker_id"],
                    rerun_target="host_records_heartbeat_binding",
                ),
            ),
        )

        state = read_json(state_path)
        self.assertEqual(state["active_control_blocker"]["blocker_id"], blocker["blocker_id"])
        self.assertEqual(state["active_control_blocker"]["pm_repair_decision_status"], "recorded")
        self.assertIn("host_records_heartbeat_binding", state["active_control_blocker"]["allowed_resolution_events"])

        result = router.record_external_event(root, "host_records_heartbeat_binding")

        self.assertTrue(result["already_recorded"])
        self.assertTrue(result["control_blocker_resolved"])
        state = read_json(state_path)
        self.assertIsNone(state["active_control_blocker"])
        self.assertIsNone(state["latest_control_blocker_path"])
        self.assertEqual(len(state["resolved_control_blockers"]), 1)

    def test_router_packet_audit_rejection_routes_pm_repair_decision(self) -> None:
        root = self.make_project()
        _run_root, _packet_path, result_path = self.prepare_current_node_result_for_review(
            root,
            packet_id="node-packet-wrong-role",
            completed_by_role="worker_b",
            completed_by_agent_id="agent-worker-b",
            record_result_return=False,
        )

        with self.assertRaises(router.RouterError) as raised:
            router.record_external_event(
                root,
                "worker_current_node_result_returned",
                {"packet_id": "node-packet-wrong-role", "result_envelope_path": result_path},
            )

        blocker = raised.exception.control_blocker
        self.assertIsInstance(blocker, dict)
        self.assertEqual(blocker["handling_lane"], "pm_repair_decision_required")
        self.assertEqual(blocker["target_role"], "project_manager")
        self.assertTrue(blocker["pm_decision_required"])
        saved = read_json(self.control_blocker_path(root, blocker))
        self.assertIn("project_manager", saved["controller_instruction"])
        self.assertIn("contact the worker directly", " ".join(saved["controller_forbidden_actions"]))
        self.assertNotIn("error_message", saved)
        self.assertTrue((root / saved["sealed_repair_packet_path"]).exists())

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "handle_control_blocker")
        self.assertEqual(action["to_role"], "project_manager")
        self.assertEqual(action["handling_lane"], "pm_repair_decision_required")
        self.assertNotIn("controller_delivery_body", action)
        router.apply_action(root, "handle_control_blocker")

        router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(
                root,
                "control_blocks/wrong_role_pm_repair_decision",
                self.pm_control_blocker_decision_body(blocker["blocker_id"], rerun_target="worker_current_node_result_returned"),
            ),
        )
        state = read_json(router.run_state_path(router.active_run_root(root)))  # type: ignore[arg-type]
        self.assertEqual(state["active_control_blocker"]["blocker_id"], blocker["blocker_id"])
        self.assertEqual(state["active_control_blocker"]["pm_repair_decision_status"], "recorded")
        self.assertIn("worker_current_node_result_returned", state["active_control_blocker"]["allowed_resolution_events"])
        self.assertIn("repair_transaction_id", state["active_control_blocker"])
        self.assertEqual(
            set(state["active_control_blocker"]["repair_outcome_table"]),
            {"success", "blocker", "protocol_blocker"},
        )
        self.assertTrue((self.run_root_for(root) / "control_blocks" / f"{blocker['blocker_id']}.pm_repair_decision.json").exists())
        transaction_path = root / state["active_control_blocker"]["repair_transaction_path"]
        self.assertTrue(transaction_path.exists())
        transaction = read_json(transaction_path)
        self.assertEqual(transaction["status"], "committed")
        self.assertEqual(transaction["plan_kind"], "event_replay")

    def test_pm_repair_transaction_commits_material_reissue_generation(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        state = read_json(router.run_state_path(run_root))
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="Controller has no legal next action after material dispatch repair request",
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
                    "packet_id": "material-scan-001-r1",
                    "replacement_for": "material-scan-001",
                    "to_role": "worker_a",
                    "body_text": "Reissued material scan packet with a committed repair generation.",
                }
            ],
        }
        router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(root, "control_blocks/material_reissue_pm_repair_decision", decision),
        )

        state = read_json(router.run_state_path(run_root))
        active = state["active_control_blocker"]
        self.assertEqual(active["blocker_id"], blocker["blocker_id"])
        self.assertEqual(
            set(active["allowed_resolution_events"]),
            {
                "router_direct_material_scan_dispatch_recheck_passed",
                "router_direct_material_scan_dispatch_recheck_blocked",
                "router_protocol_blocker_material_scan_dispatch_recheck",
            },
        )
        transaction = read_json(root / active["repair_transaction_path"])
        self.assertEqual(transaction["plan_kind"], "packet_reissue")
        self.assertEqual(transaction["status"], "committed")
        self.assertEqual(transaction["generation_commit"]["packet_count"], 1)
        material_index = read_json(run_root / "material" / "material_scan_packets.json")
        self.assertEqual(material_index["current_generation_id"], transaction["packet_generation_id"])
        self.assertEqual(material_index["packets"][0]["packet_id"], "material-scan-001-r1")
        self.assertIn("result_body_path", material_index["packets"][0])
        self.assertEqual(
            material_index["packets"][0]["result_write_target"]["result_body_path"],
            material_index["packets"][0]["result_body_path"],
        )
        packet_envelope = read_json(root / material_index["packets"][0]["packet_envelope_path"])
        self.assertEqual(packet_envelope["result_body_path"], material_index["packets"][0]["result_body_path"])
        packet_body = (root / packet_envelope["body_path"]).read_text(encoding="utf-8")
        self.assertIn('"recipient_role": "worker_a"', packet_body)
        self.assertIn('"required_result_envelope_fields"', packet_body)
        self.assertTrue((run_root / "packets" / "material-scan-001-r1" / "packet_envelope.json").exists())
        ledger = read_json(run_root / "packet_ledger.json")
        self.assertTrue(any(record.get("packet_id") == "material-scan-001-r1" for record in ledger["packets"]))

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertEqual(set(action["allowed_external_events"]), set(active["allowed_resolution_events"]))
        router.record_external_event(root, "router_direct_material_scan_dispatch_recheck_passed")
        state = read_json(router.run_state_path(run_root))
        self.assertIsNone(state["active_control_blocker"])
        self.assertIsNone(state["active_repair_transaction"])
        self.assertFalse(state["flags"]["material_scan_dispatch_recheck_blocked"])
        self.assertFalse(state["flags"]["material_scan_dispatch_recheck_protocol_blocked"])
        transaction = read_json(run_root / "control_blocks" / "repair_transactions" / f"{transaction['transaction_id']}.json")
        self.assertEqual(transaction["status"], "complete")
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_material_scan_packets")

    def test_material_scan_mechanical_agent_id_gap_reissues_to_worker(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        self.apply_next_packet_action(root, "relay_material_scan_packets")
        material_index_path = run_root / "material" / "material_scan_packets.json"
        material_index = read_json(material_index_path)
        for record in material_index["packets"]:
            envelope = packet_runtime.load_envelope(root, record["packet_envelope_path"])
            packet_runtime.read_packet_body_for_role(root, envelope, role=envelope["to_role"])
            packet_runtime.write_result(
                root,
                packet_envelope=envelope,
                completed_by_role=envelope["to_role"],
                completed_by_agent_id=envelope["to_role"],
                result_body_text="material scan result with role-name agent id",
                next_recipient="project_manager",
            )
        router.record_external_event(root, "worker_scan_packet_bodies_delivered_after_dispatch")
        with self.assertRaises(router.RouterError) as raised:
            router.record_external_event(root, "worker_scan_results_returned")

        blocker = raised.exception.control_blocker
        self.assertIsInstance(blocker, dict)
        self.assertEqual(blocker["handling_lane"], "control_plane_reissue")
        self.assertEqual(blocker["target_role"], "worker_a")
        self.assertEqual(blocker["responsible_role_for_reissue"], "worker_a")
        self.assertFalse(blocker["pm_decision_required"])
        self.assertIn("completed_agent_id_is_role_key_not_agent_id", str(raised.exception))
        self.assertTrue(self.handle_pending_control_blocker(root))
        state = read_json(router.run_state_path(run_root))
        self.assertIsNone(state["active_repair_transaction"])
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertEqual(action["to_role"], "worker_a")
        self.assertIn("worker_scan_results_returned", action["allowed_external_events"])

        material_index = read_json(material_index_path)
        for record in material_index["packets"]:
            envelope = packet_runtime.load_envelope(root, record["packet_envelope_path"])
            packet_runtime.write_result(
                root,
                packet_envelope=envelope,
                completed_by_role=envelope["to_role"],
                completed_by_agent_id=f"agent-fixed-{envelope['to_role']}",
                result_body_text="material scan result with corrected agent id",
                next_recipient="project_manager",
            )
        router.record_external_event(root, "worker_scan_results_returned")

        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["worker_scan_results_returned"])
        self.assertIsNone(state["active_control_blocker"])
        self.assertIsNone(state["active_repair_transaction"])
        self.assertIsNone(state["pending_action"])
        self.assertFalse(state["flags"]["material_scan_dispatch_recheck_blocked"])
        self.assertFalse(state["flags"]["material_scan_dispatch_recheck_protocol_blocked"])
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_material_scan_results_to_pm")

    def test_repair_transaction_recheck_blocker_registers_followup_blocker(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        state = read_json(router.run_state_path(run_root))
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="Controller has no legal next action after material dispatch repair request",
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
                    "packet_id": "material-scan-001-r1",
                    "replacement_for": "material-scan-001",
                    "to_role": "worker_a",
                    "body_text": "Reissued material scan packet with a committed repair generation.",
                }
            ],
        }
        router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(root, "control_blocks/material_reissue_pm_repair_decision_block", decision),
        )

        router.record_external_event(
            root,
            "router_direct_material_scan_dispatch_recheck_blocked",
            self.role_report_envelope(
                root,
                "control_blocks/material_reissue_recheck_block",
                {
                    "checked_by_role": "controller",
                    "dispatch_allowed": False,
                    "blockers": ["replacement packet generation needs PM repair"],
                },
            ),
        )

        state = read_json(router.run_state_path(run_root))
        active = state["active_control_blocker"]
        self.assertNotEqual(active["blocker_id"], blocker["blocker_id"])
        self.assertEqual(active["handling_lane"], "pm_repair_decision_required")
        self.assertIsNone(state["active_repair_transaction"])
        original = read_json(self.control_blocker_path(root, blocker))
        self.assertEqual(original["resolution_status"], "repair_transaction_blocker")
        tx_index = read_json(run_root / "control_blocks" / "repair_transactions" / "repair_transaction_index.json")
        self.assertIsNone(tx_index["active_transaction"])
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "handle_control_blocker")

    def test_repair_transaction_protocol_blocker_registers_followup_blocker(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        state = read_json(router.run_state_path(run_root))
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="Controller has no legal next action after material dispatch repair request",
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
                    "packet_id": "material-scan-001-r1",
                    "replacement_for": "material-scan-001",
                    "to_role": "worker_a",
                    "body_text": "Reissued material scan packet with a committed repair generation.",
                }
            ],
        }
        router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(root, "control_blocks/material_reissue_pm_repair_decision_blocked", decision),
        )

        router.record_external_event(
            root,
            "router_protocol_blocker_material_scan_dispatch_recheck",
            self.role_report_envelope(
                root,
                "control_blocks/material_reissue_protocol_blocker",
                {
                    "checked_by_role": "controller",
                    "blockers": ["replacement packet generation is not reviewable"],
                    "source_paths": [],
                    "contract_self_check": {
                        "all_required_fields_present": True,
                        "exact_field_names_used": True,
                    },
                },
            ),
        )

        state = read_json(router.run_state_path(run_root))
        active = state["active_control_blocker"]
        self.assertNotEqual(active["blocker_id"], blocker["blocker_id"])
        self.assertEqual(active["handling_lane"], "pm_repair_decision_required")
        self.assertIsNone(state["active_repair_transaction"])
        original = read_json(self.control_blocker_path(root, blocker))
        self.assertEqual(original["resolution_status"], "repair_transaction_protocol_blocker")
        tx_index = read_json(run_root / "control_blocks" / "repair_transactions" / "repair_transaction_index.json")
        self.assertIsNone(tx_index["active_transaction"])
        transaction_path = root / tx_index["transactions"][0]["path"]
        transaction = read_json(transaction_path)
        self.assertEqual(transaction["status"], "blocked")
        self.assertEqual(transaction["followup_blocker_id"], active["blocker_id"])
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "handle_control_blocker")

    def test_pm_repair_decision_rejects_unregistered_rerun_target_before_wait_write(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        state["flags"]["pm_route_skeleton_card_delivered"] = True
        router.save_run_state(run_root, state)
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="packet group reviewer audit failed: PM must repair route draft handoff",
            event="reviewer_reports_material_sufficient",
            payload={"report_path": ".flowpilot/runs/test/reviews/material.json"},
        )
        self.assertTrue(self.handle_pending_control_blocker(root))

        with self.assertRaisesRegex(router.RouterError, "rerun_target must name a registered external event"):
            router.record_external_event(
                root,
                "pm_records_control_blocker_repair_decision",
                self.role_decision_envelope(
                    root,
                    "control_blocks/invalid_pm_repair_decision",
                    self.pm_control_blocker_decision_body(
                        blocker["blocker_id"],
                        rerun_target="router_selects_next_legal_action_after_pm_records_control_blocker_repair_decision",
                    ),
                ),
            )

        original = read_json(self.control_blocker_path(root, blocker))
        self.assertNotEqual(
            original.get("allowed_resolution_events"),
            ["router_selects_next_legal_action_after_pm_records_control_blocker_repair_decision"],
        )
        self.assertNotIn("pm_repair_rerun_target", original)

    def test_delivered_control_blocker_with_legacy_invalid_wait_falls_back_to_pm_repair_decision(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="packet group reviewer audit failed: legacy bad control wait",
            event="reviewer_reports_material_sufficient",
            payload={"report_path": ".flowpilot/runs/test/reviews/legacy.json"},
        )
        self.assertTrue(self.handle_pending_control_blocker(root))
        artifact_path = self.control_blocker_path(root, blocker)
        artifact = read_json(artifact_path)
        artifact["pm_repair_decision_status"] = "recorded"
        artifact["pm_repair_rerun_target"] = "router_selects_next_legal_action_after_pm_records_control_blocker_repair_decision"
        artifact["allowed_resolution_events"] = [
            "router_selects_next_legal_action_after_pm_records_control_blocker_repair_decision"
        ]
        router.write_json(artifact_path, artifact)

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertEqual(action["allowed_external_events"], ["pm_records_control_blocker_repair_decision"])
        self.assertEqual(
            action["event_contract_issue"]["fallback"],
            "pm_must_resubmit_control_blocker_repair_decision",
        )

    def test_pm_repair_decision_accepts_registered_rerun_target_and_waits_for_it(self) -> None:
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
            source="test",
            error_message="packet group reviewer audit failed: route draft needs PM reissue",
            event="reviewer_reports_material_sufficient",
            payload={"report_path": ".flowpilot/runs/test/reviews/route-draft.json"},
        )
        self.assertTrue(self.handle_pending_control_blocker(root))
        router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(
                root,
                "control_blocks/valid_route_draft_pm_repair_decision",
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

    def test_pm_repair_decision_rejects_registered_but_not_receivable_rerun_target(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="packet group reviewer audit failed: route draft needs PM reissue",
            event="reviewer_reports_material_sufficient",
            payload={"report_path": ".flowpilot/runs/test/reviews/route-draft-not-ready.json"},
        )
        self.assertTrue(self.handle_pending_control_blocker(root))

        with self.assertRaisesRegex(router.RouterError, "pm_writes_route_draft: event requires unsatisfied flag"):
            router.record_external_event(
                root,
                "pm_records_control_blocker_repair_decision",
                self.role_decision_envelope(
                    root,
                    "control_blocks/not_receivable_route_draft_pm_repair_decision",
                    self.pm_control_blocker_decision_body(blocker["blocker_id"], rerun_target="pm_writes_route_draft"),
                ),
            )

        original = read_json(self.control_blocker_path(root, blocker))
        self.assertNotIn("pm_repair_rerun_target", original)

    def test_pm_repair_decision_rejects_parent_repair_targeting_current_node_packet(self) -> None:
        root = self.make_project()
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
                        {"node_id": "child-001", "status": "planned", "title": "Child node"},
                    ],
                },
            },
        )
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)
        state["flags"]["node_acceptance_plan_reviewer_passed"] = True
        router.save_run_state(run_root, state)
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="parent backward replay repair cannot jump to leaf current-node packet registration",
            event="pm_records_parent_segment_decision",
            payload={"decision_path": ".flowpilot/runs/test/decisions/parent.json"},
        )
        self.assertTrue(self.handle_pending_control_blocker(root))

        with self.assertRaisesRegex(router.RouterError, "pm_registers_current_node_packet: event is incompatible with parent/module active node"):
            router.record_external_event(
                root,
                "pm_records_control_blocker_repair_decision",
                self.role_decision_envelope(
                    root,
                    "control_blocks/parent_bad_rerun_pm_repair_decision",
                    self.pm_control_blocker_decision_body(
                        blocker["blocker_id"],
                        rerun_target="pm_registers_current_node_packet",
                    ),
                ),
            )

        original = read_json(self.control_blocker_path(root, blocker))
        self.assertNotIn("pm_repair_rerun_target", original)

    def test_pm_repair_decision_can_repeat_for_new_control_blocker(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)
        state["flags"]["reviewer_material_sufficiency_card_delivered"] = True
        router.save_run_state(run_root, state)
        first = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="packet group reviewer audit failed: first reviewer audit issue",
            event="reviewer_reports_material_sufficient",
            payload={"report_path": ".flowpilot/runs/test/reviews/first.json"},
        )
        self.assertEqual(first["handling_lane"], "pm_repair_decision_required")
        self.assertTrue(self.handle_pending_control_blocker(root))
        router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(
                root,
                "control_blocks/first_pm_repair_decision",
                self.pm_control_blocker_decision_body(first["blocker_id"], rerun_target="reviewer_reports_material_sufficient"),
            ),
        )

        state = read_json(state_path)
        self.assertEqual(state["active_control_blocker"]["blocker_id"], first["blocker_id"])
        self.assertEqual(state["active_control_blocker"]["pm_repair_decision_status"], "recorded")
        second = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="packet group reviewer audit failed: second reviewer audit issue",
            event="reviewer_reports_material_sufficient",
            payload={"report_path": ".flowpilot/runs/test/reviews/second.json"},
        )
        self.assertEqual(second["handling_lane"], "pm_repair_decision_required")
        self.assertTrue(self.handle_pending_control_blocker(root))
        result = router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(
                root,
                "control_blocks/second_pm_repair_decision",
                self.pm_control_blocker_decision_body(second["blocker_id"], rerun_target="reviewer_reports_material_sufficient"),
            ),
        )

        self.assertNotIn("already_recorded", result)
        state = read_json(state_path)
        self.assertEqual(state["active_control_blocker"]["blocker_id"], second["blocker_id"])
        self.assertEqual(state["active_control_blocker"]["pm_repair_decision_status"], "recorded")
        self.assertTrue((run_root / "control_blocks" / f"{second['blocker_id']}.pm_repair_decision.json").exists())

    def test_missing_open_receipt_control_blocker_routes_to_same_reviewer_reissue(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))

        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="packet group reviewer audit failed: ['result_body_not_opened_by_reviewer_or_pm_after_relay_check']",
            event="reviewer_reports_material_insufficient",
            payload={"report_path": ".flowpilot/runs/test/material/reviewer.json"},
        )

        self.assertEqual(blocker["handling_lane"], "control_plane_reissue")
        self.assertEqual(blocker["target_role"], "human_like_reviewer")
        self.assertFalse(blocker["pm_decision_required"])
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "handle_control_blocker")
        self.assertEqual(action["to_role"], "human_like_reviewer")

    def test_current_node_result_requires_write_grant(self) -> None:
        root = self.make_project()
        run_root, _packet_path, result_path = self.prepare_current_node_result_for_review(
            root,
            packet_id="node-packet-write-grant-required",
            record_result_return=False,
        )
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)
        state["flags"]["current_node_write_grant_issued"] = False
        grant_path = run_root / "routes" / "route-001" / "nodes" / "node-001" / "current_node_write_grant.json"
        self.assertTrue(grant_path.exists())
        grant_path.unlink()
        router.write_json(state_path, state)

        with self.assertRaisesRegex(router.RouterError, "current-node write grant"):
            router.record_external_event(
                root,
                "worker_current_node_result_returned",
                {
                    "packet_id": "node-packet-write-grant-required",
                    "result_envelope_path": result_path,
                },
            )

    def test_node_acceptance_plan_requires_pm_high_standard_recheck(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.deliver_expected_card(root, "pm.current_node_loop")
        self.deliver_expected_card(root, "pm.event.node_started")
        self.deliver_expected_card(root, "pm.node_acceptance_plan")

        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "pm_writes_node_acceptance_plan",
                {
                    "node_requirements": [
                        {
                            "requirement_id": "node-001-req",
                            "acceptance_statement": "current node work is complete",
                            "proof_required": "mixed",
                        }
                    ],
                    "experiment_plan": [],
                },
            )

    def test_validate_artifact_reports_node_acceptance_missing_fields_together(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        plan_path = root / ".flowpilot" / "partial_node_acceptance_plan.json"
        plan_path.write_text(
            json.dumps(
                {
                    "schema_version": "flowpilot.node_acceptance_plan.v1",
                    "run_id": "run-test",
                    "route_id": "route-001",
                    "route_version": 1,
                    "node_id": "node-001",
                    "node_requirements": [{"requirement_id": "req-001"}],
                    "experiment_plan": [],
                    "high_standard_recheck": {"decision": "proceed"},
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        result = router.validate_artifact(root, "node_acceptance_plan", self.rel(root, plan_path))
        fields = {issue["field"] for issue in result["errors"]}

        self.assertFalse(result["ok"])
        self.assertEqual(result["next_action"], "repair_node_acceptance_plan")
        self.assertIn("prior_path_context_review", fields)
        self.assertIn("prior_path_context_review.source_paths", fields)
        self.assertIn("high_standard_recheck.ideal_outcome", fields)
        self.assertIn("high_standard_recheck.why_current_plan_meets_highest_reasonable_standard", fields)

    def test_gate_decision_event_records_ledger_and_state(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        body = self.gate_decision_body(root)
        router.record_external_event(
            root,
            "role_records_gate_decision",
            self.role_decision_envelope(root, "gate_decisions/quality_gate_001", body),
        )

        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["gate_decision_recorded"])
        self.assertEqual(len(state["gate_decisions"]), 1)
        self.assertEqual(state["gate_decisions"][0]["gate_id"], "quality-gate-001")
        self.assertEqual(state["gate_decisions"][0]["decision"], "pass")
        decision_record = read_json(root / state["gate_decisions"][0]["decision_path"])
        self.assertEqual(decision_record["schema_version"], "flowpilot.gate_decision_record.v1")
        self.assertEqual(decision_record["gate_decision"]["owner_role"], "human_like_reviewer")
        ledger = read_json(run_root / "gate_decisions" / "gate_decision_ledger.json")
        self.assertEqual(ledger["gate_decision_count"], 1)

    def test_gate_decision_same_identity_replay_is_already_recorded(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        envelope = self.role_decision_envelope(
            root,
            "gate_decisions/replayed_quality_gate",
            self.gate_decision_body(root, gate_id="replayed-quality-gate"),
        )

        router.record_external_event(root, "role_records_gate_decision", envelope)
        state = read_json(router.run_state_path(run_root))
        record_path = root / state["gate_decisions"][0]["decision_path"]
        first_recorded_at = read_json(record_path)["recorded_at"]

        replay = router.record_external_event(root, "role_records_gate_decision", envelope)

        self.assertTrue(replay["already_recorded"])
        self.assertEqual(read_json(record_path)["recorded_at"], first_recorded_at)
        state = read_json(router.run_state_path(run_root))
        self.assertEqual(len(state["gate_decisions"]), 1)
        processed = state["external_event_idempotency"]["processed"]["role_records_gate_decision"]
        self.assertEqual(len(processed), 1)

    def test_gate_decision_rejects_mechanical_contradictions(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        body = self.gate_decision_body(root, blocking=True)

        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "role_records_gate_decision",
                self.role_decision_envelope(root, "gate_decisions/contradictory_pass", body),
            )

    def test_validate_artifact_reports_gate_decision_issues_together(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        bad = self.gate_decision_body(root)
        bad.pop("reason")
        bad["owner_role"] = "controller"
        bad["blocking"] = True
        gate_path = root / ".flowpilot" / "bad_gate_decision.json"
        gate_path.write_text(json.dumps(bad, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        result = router.validate_artifact(root, "gate_decision", self.rel(root, gate_path))
        fields = {issue["field"] for issue in result["errors"]}

        self.assertFalse(result["ok"])
        self.assertEqual(result["next_action"], "repair_gate_decision")
        self.assertIn("reason", fields)
        self.assertIn("owner_role", fields)
        self.assertIn("blocking", fields)

    def test_evidence_quality_package_blocks_stale_and_missing_visual_evidence(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.deliver_current_node_cards(root)

        packet = packet_runtime.create_packet(
            root,
            packet_id="node-packet-quality",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="current node work",
            metadata={"route_version": 1},
        )
        packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
        router.record_external_event(root, "pm_registers_current_node_packet", {"packet_id": "node-packet-quality", "packet_envelope_path": packet_path})
        self.apply_until_action(root, "relay_current_node_packet")
        relayed_packet = read_json(root / packet_path)
        packet_runtime.read_packet_body_for_role(root, relayed_packet, role="worker_a")
        result = packet_runtime.write_result(
            root,
            packet_envelope=read_json(root / packet_path),
            completed_by_role="worker_a",
            completed_by_agent_id="agent-worker-quality",
            result_body_text="reviewable result",
            next_recipient="project_manager",
        )
        result_path = result["result_body_path"].replace("result_body.md", "result_envelope.json")
        router.record_external_event(root, "worker_current_node_result_returned", {"packet_id": "node-packet-quality", "result_envelope_path": result_path})
        self.absorb_current_node_results_with_pm(root, [result_path])
        self.deliver_expected_card(root, "reviewer.worker_result_review")
        router.record_external_event(
            root,
            "current_node_reviewer_passes_result",
            self.role_report_envelope(
                root,
                "reviews/current_node_result_quality",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": True,
                    "agent_role_map": {"agent-worker-quality": "worker_a"},
                },
            ),
        )
        router.record_external_event(root, "pm_completes_current_node_from_reviewed_result")

        self.deliver_expected_card(root, "pm.evidence_quality_package")
        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "pm_records_evidence_quality_package",
                {"evidence_items": [{"evidence_id": "stale", "status": "stale"}]},
            )
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_records_evidence_quality_package", {"ui_visual_evidence_required": True})
        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "pm_records_evidence_quality_package",
                {
                    "ui_visual_evidence_required": True,
                    "ui_visual_evidence": {"screenshot_paths": ["ui.png"], "old_assets_reused": True},
                },
            )

        router.record_external_event(
            root,
            "pm_records_evidence_quality_package",
            {
                **self.prior_path_context_review(root, "Evidence quality package considered visual evidence and route memory."),
                "evidence_items": [{"evidence_id": "reviewed-result", "status": "current"}],
                "generated_resources": [{"resource_id": "diagram-1", "disposition": "qa_evidence"}],
                "ui_visual_evidence_required": True,
                "ui_visual_evidence": {"screenshot_paths": ["screenshots/current-ui.png"], "old_assets_reused": False},
            },
        )
        self.deliver_expected_card(root, "reviewer.evidence_quality_review")
        router.record_external_event(
            root,
            "reviewer_passes_evidence_quality_package",
            self.role_report_envelope(
                root,
                "reviews/evidence_quality_review",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )
        self.deliver_expected_card(root, "pm.final_ledger")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_records_final_route_wide_ledger_clean", {"unresolved_count": 1})
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "reviewer_final_backward_replay_passed", {"reviewed_by_role": "human_like_reviewer", "passed": True})
        router.record_external_event(root, "pm_records_final_route_wide_ledger_clean", self.final_ledger_payload(root))
        self.deliver_expected_card(root, "reviewer.final_backward_replay")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "reviewer_final_backward_replay_passed", {"reviewed_by_role": "project_manager", "passed": True})
        router.record_external_event(
            root,
            "reviewer_final_backward_replay_passed",
            self.role_report_envelope(
                root,
                "reviews/terminal_backward_replay",
                self.terminal_replay_payload(root),
            ),
        )

    def test_route_mutation_and_final_ledger_have_required_preconditions(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_mutates_route_after_review_block")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_records_final_route_wide_ledger_clean")

        self.activate_route(root)
        self.deliver_current_node_cards(root)
        packet = packet_runtime.create_packet(
            root,
            packet_id="node-packet-003",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="current node work",
            metadata={"route_version": 1},
        )
        packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
        router.record_external_event(root, "pm_registers_current_node_packet", {"packet_id": "node-packet-003", "packet_envelope_path": packet_path})
        self.apply_until_action(root, "relay_current_node_packet")
        relayed_packet = read_json(root / packet_path)
        packet_runtime.read_packet_body_for_role(root, relayed_packet, role="worker_a")
        result = packet_runtime.write_result(
            root,
            packet_envelope=read_json(root / packet_path),
            completed_by_role="worker_a",
            completed_by_agent_id="agent-worker-a-2",
            result_body_text="blocked result",
            next_recipient="project_manager",
        )
        result_path = result["result_body_path"].replace("result_body.md", "result_envelope.json")
        router.record_external_event(root, "worker_current_node_result_returned", {"packet_id": "node-packet-003", "result_envelope_path": result_path})
        self.absorb_current_node_results_with_pm(root, [result_path])
        self.deliver_expected_card(root, "reviewer.worker_result_review")
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        self.close_model_miss_triage(root, output_name="decisions/route_mutation_model_miss_valid")
        router.record_external_event(
            root,
            "pm_mutates_route_after_review_block",
            {
                "repair_node_id": "node-001-repair",
                "repair_return_to_node_id": "node-001",
                "reason": "reviewer_block",
                "stale_evidence": ["node-packet-003"],
                **self.prior_path_context_review(root, "Route mutation considered blocked node result and stale evidence."),
            },
        )

        current = read_json(root / ".flowpilot" / "current.json")
        run_root = root / current["current_run_root"]
        frontier = read_json(root / current["current_run_root"] / "execution_frontier.json")
        self.assertEqual(frontier["status"], "route_mutation_pending_recheck")
        self.assertEqual(frontier["active_node_id"], "node-001")
        self.assertEqual(frontier["pending_route_mutation"]["candidate_node_id"], "node-001-repair")
        self.assertEqual(frontier["pending_route_mutation"]["candidate_route_version"], 2)
        self.assertEqual(read_json(run_root / "routes" / "route-001" / "flow.json")["active_node_id"], "node-001")
        draft = read_json(run_root / "routes" / "route-001" / "flow.draft.json")
        self.assertEqual(draft["candidate_activation_status"], "pending_route_recheck")
        self.assertEqual(draft["route_topology"]["topology_strategy"], "return_to_original")
        self.assertIn("node-001-repair", {node.get("node_id") for node in draft["nodes"]})
        self.assertTrue(self.flag(root, "route_draft_written_by_pm"))

        self.complete_route_checks(root)
        router.record_external_event(
            root,
            "pm_activates_reviewed_route",
            {"route_id": "route-001", "active_node_id": "node-001-repair"},
        )
        frontier = read_json(root / current["current_run_root"] / "execution_frontier.json")
        self.assertEqual(frontier["status"], "current_node_loop")
        self.assertEqual(frontier["active_node_id"], "node-001-repair")
        self.assertEqual(frontier["route_version"], 2)

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "reviewer_final_backward_replay_passed")

    def test_route_mutation_new_repair_transaction_is_not_swallowed_by_old_flag(self) -> None:
        root = self.make_project()
        run_root, _packet_path, _result_path = self.prepare_current_node_result_for_review(
            root,
            packet_id="node-packet-scoped-route-mutation",
        )
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        self.close_model_miss_triage(root, output_name="decisions/scoped_route_mutation_first_triage")
        first_payload = {
            "repair_node_id": "node-001-repair-v2",
            "repair_return_to_node_id": "node-001",
            "route_version": 2,
            "reason": "first_reviewer_block",
            "stale_evidence": ["node-packet-scoped-route-mutation"],
            **self.prior_path_context_review(root, "First route mutation considered the reviewer block."),
        }
        first = router.record_external_event(root, "pm_mutates_route_after_review_block", first_payload)
        self.assertNotIn("already_recorded", first)
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)
        self.assertTrue(state["flags"]["route_mutated_by_pm"])
        self.assertFalse(state["flags"]["node_review_blocked"])
        first_replay = router.record_external_event(root, "pm_mutates_route_after_review_block", first_payload)
        self.assertTrue(first_replay["already_recorded"])
        mutations = read_json(run_root / "routes" / "route-001" / "mutations.json")
        self.assertEqual([item["route_version"] for item in mutations["items"]], [2])

        blocker_path = run_root / "control_blocks" / "control-blocker-scoped-route-mutation.json"
        blocker_rel = self.rel(root, blocker_path)
        blocker = {
            "schema_version": router.CONTROL_BLOCKER_SCHEMA,
            "blocker_id": "control-blocker-scoped-route-mutation",
            "run_id": run_root.name,
            "handling_lane": "pm_repair_decision_required",
            "delivery_status": "delivered",
            "blocker_artifact_path": blocker_rel,
            "target_role": "project_manager",
            "pm_decision_required": True,
            "pm_repair_decision_status": "recorded",
            "repair_transaction_id": "repair-tx-scoped-route-mutation",
            "allowed_resolution_events": ["pm_mutates_route_after_review_block"],
            "created_at": "2026-05-10T00:00:00Z",
        }
        blocker_path.parent.mkdir(parents=True, exist_ok=True)
        blocker_path.write_text(json.dumps(blocker, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        state["active_control_blocker"] = dict(blocker)
        state["latest_control_blocker_path"] = blocker_rel
        state["control_blockers"] = [dict(blocker)]
        state["flags"]["node_review_blocked"] = True
        state["flags"]["model_miss_triage_closed"] = True
        router.save_run_state(run_root, state)

        second = router.record_external_event(
            root,
            "pm_mutates_route_after_review_block",
            {
                "control_blocker_id": "control-blocker-scoped-route-mutation",
                "repair_transaction_id": "repair-tx-scoped-route-mutation",
                "repair_node_id": "node-001-repair-v3",
                "repair_return_to_node_id": "node-001-repair-v2",
                "route_version": 3,
                "reason": "second_control_blocker_repair",
                "stale_evidence": ["node-packet-scoped-route-mutation-v2"],
                **self.prior_path_context_review(root, "Second route mutation considered a later control blocker."),
            },
        )

        self.assertNotIn("already_recorded", second)
        state = read_json(state_path)
        self.assertIsNone(state["active_control_blocker"])
        mutations = read_json(run_root / "routes" / "route-001" / "mutations.json")
        self.assertEqual([item["route_version"] for item in mutations["items"]], [2, 3])
        frontier = read_json(run_root / "execution_frontier.json")
        self.assertEqual(frontier["route_version"], 1)
        self.assertEqual(frontier["active_node_id"], "node-001")
        self.assertEqual(frontier["status"], "route_mutation_pending_recheck")
        self.assertEqual(frontier["pending_route_mutation"]["candidate_node_id"], "node-001-repair-v3")
        self.assertEqual(frontier["pending_route_mutation"]["candidate_route_version"], 3)
        processed = state["external_event_idempotency"]["processed"]["pm_mutates_route_after_review_block"]
        self.assertEqual(len(processed), 2)

    def test_route_mutation_supersede_strategy_does_not_require_return_to_original(self) -> None:
        root = self.make_project()
        run_root, _packet_path, _result_path = self.prepare_current_node_result_for_review(
            root,
            packet_id="node-packet-supersede-route-mutation",
        )
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        self.close_model_miss_triage(root, output_name="decisions/supersede_route_mutation_triage")

        router.record_external_event(
            root,
            "pm_mutates_route_after_review_block",
            {
                "repair_node_id": "node-001-v2",
                "topology_strategy": "supersede_original",
                "superseded_nodes": ["node-001"],
                "reason": "replace invalid original node",
                "stale_evidence": ["node-packet-supersede-route-mutation"],
                **self.prior_path_context_review(root, "Supersede route mutation considered the blocked original node."),
            },
        )

        frontier = read_json(run_root / "execution_frontier.json")
        self.assertEqual(frontier["status"], "route_mutation_pending_recheck")
        self.assertEqual(frontier["active_node_id"], "node-001")
        self.assertEqual(frontier["pending_route_mutation"]["candidate_node_id"], "node-001-v2")
        draft = read_json(run_root / "routes" / "route-001" / "flow.draft.json")
        old_node = next(node for node in draft["nodes"] if node.get("node_id") == "node-001")
        replacement = next(node for node in draft["nodes"] if node.get("node_id") == "node-001-v2")
        self.assertEqual(old_node["status"], "superseded")
        self.assertEqual(replacement["topology_strategy"], "supersede_original")
        self.assertIsNone(replacement["repair_return_to_node_id"])

        self.complete_route_checks(root)
        router.record_external_event(root, "pm_activates_reviewed_route", {"route_id": "route-001", "active_node_id": "node-001-v2"})
        frontier = read_json(run_root / "execution_frontier.json")
        self.assertEqual(frontier["active_node_id"], "node-001-v2")
        self.assertEqual(frontier["route_version"], 2)
        active_route = read_json(run_root / "routes" / "route-001" / "flow.json")
        active_old_node = next(node for node in active_route["nodes"] if node.get("node_id") == "node-001")
        self.assertEqual(active_old_node["status"], "superseded")

    def test_parent_backward_targets_require_current_child_completion_ledgers(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
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
        self.deliver_current_node_cards(root)
        state_path = router.run_state_path(self.run_root_for(root))
        state = read_json(state_path)
        state["flags"]["pm_parent_backward_targets_card_delivered"] = True
        router.save_run_state(self.run_root_for(root), state)
        with self.assertRaisesRegex(router.RouterError, "requires legal route action build_parent_backward_targets"):
            router.record_external_event(root, "pm_builds_parent_backward_targets")

    def test_parent_node_requires_backward_replay_before_completion(self) -> None:
        root = self.make_project()
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
        packet = packet_runtime.create_packet(
            root,
            packet_id="parent-node-packet",
            from_role="project_manager",
            to_role="worker_a",
            node_id="parent-001",
            body_text="parent node work",
            metadata={"route_version": 1},
        )
        packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_registers_current_node_packet", {"packet_id": "parent-node-packet", "packet_envelope_path": packet_path})

        self.complete_parent_backward_replay_if_due(root)
        router.record_external_event(root, "pm_completes_parent_node_from_backward_replay")
        frontier = read_json(run_root / "execution_frontier.json")
        self.assertIn("parent-001", frontier["completed_nodes"])
        self.assertTrue((run_root / "routes" / "route-001" / "nodes" / "parent-001" / "parent_backward_replay.json").exists())

    def test_parent_backward_non_continue_decision_mutates_route_and_requires_rerun(self) -> None:
        root = self.make_project()
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
                "reviews/parent_backward_replay_noncontinue",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )
        self.deliver_expected_card(root, "pm.parent_segment_decision")
        router.record_external_event(
            root,
            "pm_records_parent_segment_decision",
            self.role_decision_envelope(
                root,
                "decisions/parent_segment_repair_decision",
                {
                    "decision_owner": "project_manager",
                    "decision": "repair_existing_child",
                    "repair_return_to_node_id": "parent-001",
                    **self.prior_path_context_review(root, "Parent segment repair decision considered prior route memory and replay evidence."),
                },
            ),
        )

        frontier = read_json(run_root / "execution_frontier.json")
        self.assertEqual(frontier["status"], "route_mutation_pending_recheck")
        self.assertEqual(frontier["active_node_id"], "parent-001")
        self.assertNotEqual(frontier["pending_route_mutation"]["candidate_node_id"], "parent-001")
        decision = read_json(run_root / "routes" / "route-001" / "nodes" / "parent-001" / "pm_parent_segment_decision.json")
        self.assertTrue(decision["same_parent_replay_rerun_required"])

    def test_unready_leaf_cannot_receive_current_node_packet(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        router.record_external_event(
            root,
            "pm_activates_reviewed_route",
            {
                "route_id": "route-001",
                "active_node_id": "leaf-001",
                "route_version": 1,
                "route": {
                    "schema_version": "flowpilot.route.v1",
                    "route_id": "route-001",
                    "route_version": 1,
                    "active_node_id": "leaf-001",
                    "nodes": [
                        {
                            "node_id": "leaf-001",
                            "node_kind": "leaf",
                            "status": "active",
                            "title": "Unready leaf",
                        }
                    ],
                },
            },
        )
        self.deliver_current_node_cards(
            root,
            leaf_readiness_gate={
                "status": "fail",
                "single_outcome": False,
                "worker_executable_without_replanning": False,
                "proof_defined": False,
                "dependency_boundary_defined": True,
                "failure_isolation_defined": True,
                "over_decomposition_checked": True,
            },
        )
        packet = packet_runtime.create_packet(
            root,
            packet_id="unready-leaf-packet",
            from_role="project_manager",
            to_role="worker_a",
            node_id="leaf-001",
            body_text="unready leaf work",
            metadata={"route_version": 1},
        )
        packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_registers_current_node_packet", {"packet_id": "unready-leaf-packet", "packet_envelope_path": packet_path})

    def test_controller_boundary_confirmation_records_envelope_only_event(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "confirm_controller_core_boundary")
        result = router.apply_action(root, "confirm_controller_core_boundary")

        self.assertTrue(result["ok"])
        state = read_json(router.run_state_path(router.active_run_root(root)))  # type: ignore[arg-type]
        self.assertTrue(state["flags"]["controller_role_confirmed"])
        self.assertEqual(state["events"][0]["event"], "controller_role_confirmed_from_router_core")
        self.assertIn("path", state["events"][0]["payload"])
        self.assertIn("sha256", state["events"][0]["payload"])

    def test_material_insufficient_event_records_insufficient_state(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_startup_activation(root)
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        self.apply_next_packet_action(root, "relay_material_scan_packets")
        run_root = self.run_root_for(root)
        material_index_path = run_root / "material" / "material_scan_packets.json"
        self.open_packets_and_write_results(root, material_index_path, result_text="insufficient material")
        router.record_external_event(root, "worker_scan_packet_bodies_delivered_after_dispatch")
        router.record_external_event(root, "worker_scan_results_returned")
        self.absorb_material_scan_results_with_pm(root, material_index_path)
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        self.deliver_expected_card(root, "reviewer.material_sufficiency")

        router.record_external_event(
            root,
            "reviewer_reports_material_insufficient",
            self.role_report_envelope(
                root,
                "material/reviewer_material_insufficient",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "direct_material_sources_checked": True,
                    "packet_matches_checked_sources": True,
                    "pm_ready": False,
                },
            ),
        )

        state = read_json(router.run_state_path(router.active_run_root(root)))  # type: ignore[arg-type]
        self.assertTrue(state["flags"]["material_review_insufficient"])
        self.assertEqual(state["material_review"], "insufficient")

    def test_final_ledger_rejects_missing_source_of_truth_entries_and_contract_replay(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id="node-packet-final-ledger-preconditions")
        self.complete_evidence_quality_package(root)
        self.deliver_expected_card(root, "pm.final_ledger")

        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "pm_records_final_route_wide_ledger_clean",
                {
                    "pm_owned": True,
                    "entries": [
                        {
                            "entry_id": "route-001:node-001",
                            "node_id": "node-001",
                            "gate_family": "human_review",
                            "required_approver": "human_like_reviewer",
                            "status": "approved",
                            "evidence_paths": [".flowpilot/current-node-result"],
                        }
                    ],
                },
            )

    def test_terminal_replay_requires_reviewed_segments_and_pm_segment_decisions(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id="node-packet-terminal-segments")
        self.complete_evidence_quality_package(root)
        self.deliver_expected_card(root, "pm.final_ledger")
        router.record_external_event(root, "pm_records_final_route_wide_ledger_clean", self.final_ledger_payload(root))
        self.deliver_expected_card(root, "reviewer.final_backward_replay")

        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "reviewer_final_backward_replay_passed",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            )

    def test_final_ledger_records_frozen_contract_replay_source_paths(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id="node-packet-final-ledger-sources")
        self.complete_evidence_quality_package(root)
        router.record_external_event(
            root,
            "role_records_gate_decision",
            self.role_decision_envelope(
                root,
                "gate_decisions/final_quality_gate",
                self.gate_decision_body(root, gate_id="final-quality-gate"),
            ),
        )
        self.deliver_expected_card(root, "pm.final_ledger")
        router.record_external_event(root, "pm_records_final_route_wide_ledger_clean", self.final_ledger_payload(root))

        ledger = read_json(run_root / "final_route_wide_gate_ledger.json")
        self.assertEqual(ledger["root_contract_replay"][0]["requirement_id"], "root-001")
        self.assertIn(self.rel(root, run_root / "root_acceptance_contract.json"), ledger["root_contract_replay"][0]["evidence_paths"])
        self.assertEqual(ledger["source_paths"]["root_acceptance_contract"], self.rel(root, run_root / "root_acceptance_contract.json"))
        gate_families = {entry["gate_family"] for entry in ledger["entries"]}
        self.assertIn("root_acceptance", gate_families)
        self.assertIn("route_node", gate_families)
        self.assertIn("child_skill_gate", gate_families)
        self.assertIn("evidence_integrity", gate_families)
        self.assertEqual(ledger["counts"]["gate_decision_count"], 1)
        self.assertEqual(ledger["gate_decisions"][0]["gate_id"], "final-quality-gate")
        self.assertEqual(ledger["source_paths"]["gate_decision_ledger"], self.rel(root, run_root / "gate_decisions" / "gate_decision_ledger.json"))

    def test_closure_lifecycle_blocks_when_ledgers_are_dirty_after_terminal_replay(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id="node-packet-dirty-closure")
        self.complete_evidence_quality_package(root)
        self.complete_final_ledger_and_terminal_replay(root)

        evidence_ledger_path = run_root / "evidence" / "evidence_ledger.json"
        evidence_ledger = read_json(evidence_ledger_path)
        evidence_ledger["unresolved_count"] = 1
        evidence_ledger_path.write_text(json.dumps(evidence_ledger, indent=2, sort_keys=True), encoding="utf-8")

        action = router.next_action(root)
        card_id = action.get("next_card_id") or action.get("card_id")
        self.assertNotEqual(card_id, "pm.closure")

    def test_pm_terminal_closure_uses_file_backed_contract_and_prior_context(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id="node-packet-terminal-closure")
        self.complete_evidence_quality_package(root)
        self.complete_final_ledger_and_terminal_replay(root)

        card_action = self.deliver_expected_card(root, "pm.closure")
        self.assert_payload_contract_mentions(
            card_action["payload_contract"],
            "pm_terminal_closure_decision_role_output",
            "approved_by_role",
            "approve_terminal_closure",
            "prior_path_context_review.source_paths",
            "pm_prior_path_context.json",
            "route_history_index.json",
        )
        wait_action = router.next_action(root)
        self.assertEqual(wait_action["action_type"], "await_role_decision")
        self.assert_payload_contract_mentions(
            wait_action["payload_contract"],
            "pm_terminal_closure_decision_role_output",
            "current_ledgers_clean",
            "pm_suggestion_ledger_clean",
            "prior_path_context_review.controller_summary_used_as_evidence",
        )

        result = router.record_external_event(
            root,
            "pm_approves_terminal_closure",
            self.role_decision_envelope(
                root,
                "closure/pm_terminal_closure_decision",
                {
                    "approved_by_role": "project_manager",
                    "decision": "approve_terminal_closure",
                    **self.prior_path_context_review(root, "Terminal closure considered clean final ledger and current route memory."),
                    "final_report": {"status": "complete"},
                },
            ),
        )
        self.assertTrue(result["ok"])
        closure = read_json(run_root / "closure" / "terminal_closure_suite.json")
        self.assertEqual(closure["decision"], "approve_terminal_closure")
        self.assertEqual(closure["prior_path_context_review"]["reviewed"], True)
        self.assertEqual(closure["status"], "closed")
        frontier = read_json(run_root / "execution_frontier.json")
        self.assertEqual(frontier["status"], "closed")
        state = read_json(router.run_state_path(run_root))
        self.assertEqual(state["status"], "closed")
        self.assertTrue(state["flags"]["terminal_closure_approved"])
        lifecycle = read_json(run_root / "lifecycle" / "run_lifecycle.json")
        self.assertEqual(lifecycle["status"], "closed")
        snapshot = read_json(run_root / "route_state_snapshot.json")
        completed_nodes = {node["id"]: node for node in snapshot["route"]["nodes"] if node["id"] in frontier["completed_nodes"]}
        self.assertTrue(completed_nodes)
        self.assertTrue(all(node["status"] == "completed" for node in completed_nodes.values()))
        self.assertTrue(
            all(
                item["status"] == "completed"
                for node in completed_nodes.values()
                for item in node["checklist"]
            )
        )
        self.assertEqual(snapshot["active_ui_task_catalog"]["active_tasks"], [])

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "write_terminal_summary")
        self.assertEqual(action["run_lifecycle_status"], "closed")
        self.assertEqual(action["required_attribution_line"], router.TERMINAL_SUMMARY_ATTRIBUTION)
        self.apply_terminal_summary(root, action, run_root, note="PM approved terminal closure.")
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "run_lifecycle_terminal")
        self.assertEqual(action["run_lifecycle_status"], "closed")

    def test_final_ledger_rejects_dirty_pm_suggestion_ledger(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id="node-packet-suggestion-ledger")
        self.complete_evidence_quality_package(root)
        self.write_pm_suggestion_ledger(root, [self.pm_suggestion_entry(root, clean=False)])

        self.deliver_expected_card(root, "pm.final_ledger")
        with self.assertRaisesRegex(router.RouterError, "clean PM suggestion ledger"):
            router.record_external_event(root, "pm_records_final_route_wide_ledger_clean", self.final_ledger_payload(root))

    def test_dirty_pm_suggestion_ledger_invalidates_terminal_closure_card(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id="node-packet-suggestion-closure")
        self.complete_evidence_quality_package(root)
        self.write_pm_suggestion_ledger(root, [self.pm_suggestion_entry(root, clean=True)])
        self.complete_final_ledger_and_terminal_replay(root)
        self.write_pm_suggestion_ledger(root, [self.pm_suggestion_entry(root, clean=False)])

        action = router.next_action(root)
        card_id = action.get("next_card_id") or action.get("card_id")
        self.assertNotEqual(card_id, "pm.closure")
        self.assertEqual(card_id, "pm.evidence_quality_package")

    def test_reconcile_recovers_legacy_terminal_closure_state(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id="node-packet-legacy-terminal-closure")
        self.complete_evidence_quality_package(root)
        self.complete_final_ledger_and_terminal_replay(root)
        self.deliver_expected_card(root, "pm.closure")
        router.record_external_event(
            root,
            "pm_approves_terminal_closure",
            self.role_decision_envelope(
                root,
                "closure/pm_legacy_terminal_closure_decision",
                {
                    "approved_by_role": "project_manager",
                    "decision": "approve_terminal_closure",
                    **self.prior_path_context_review(root, "Terminal closure considered clean final ledger and current route memory."),
                    "final_report": {"status": "complete"},
                },
            ),
        )
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)
        state["status"] = "active"
        state["phase"] = "route_execution"
        state["flags"].pop("terminal_closure_approved", None)
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="router_no_legal_next_action",
            error_message="Controller has no legal next action after legacy terminal closure.",
            action_type="controller_no_legal_next_action",
            payload={"path": self.rel(root, state_path), "role": "controller"},
        )
        state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (run_root / "lifecycle" / "run_lifecycle.json").unlink()

        result = router.reconcile_current_run(root)
        self.assertTrue(result["repaired"]["terminal_closure_status_recovered"])
        self.assertTrue(result["repaired"]["terminal_lifecycle"])
        self.assertTrue(result["repaired"]["terminal_lifecycle_record_written"])
        lifecycle = read_json(run_root / "lifecycle" / "run_lifecycle.json")
        self.assertEqual(lifecycle["status"], "closed")
        self.assertEqual(lifecycle["request_event"], "reconcile_current_run")
        state = read_json(state_path)
        self.assertEqual(state["status"], "closed")
        self.assertIsNone(state["active_control_blocker"])
        blocker_record = read_json(self.control_blocker_path(root, blocker))
        self.assertEqual(blocker_record["resolution_status"], "superseded_by_terminal_lifecycle")
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "write_terminal_summary")
        self.assertEqual(action["run_lifecycle_status"], "closed")
        self.apply_terminal_summary(root, action, run_root, note="Reconciled legacy terminal closure.")
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "run_lifecycle_terminal")
        self.assertEqual(action["run_lifecycle_status"], "closed")

    def test_manifest_references_existing_system_cards(self) -> None:
        manifest = read_json(ROOT / "skills" / "flowpilot" / "assets" / "runtime_kit" / "manifest.json")
        kit_root = ROOT / "skills" / "flowpilot" / "assets" / "runtime_kit"
        card_ids = set()

        for card in manifest["cards"]:
            card_ids.add(card["id"])
            self.assertEqual(card["source"], "system")
            self.assertEqual(card["issued_by"], "router")
            self.assertTrue((kit_root / card["path"]).exists(), card["path"])

        self.assertIn("pm.core", card_ids)
        self.assertIn("pm.final_ledger", card_ids)
        self.assertIn("pm.evidence_quality_package", card_ids)
        self.assertIn("reviewer.evidence_quality_review", card_ids)
        self.assertIn("reviewer.final_backward_replay", card_ids)
        self.assertIn("controller.resume_reentry", card_ids)
        self.assertIn("pm.crew_rehydration_freshness", card_ids)
        self.assertIn("pm.resume_decision", card_ids)
        self.assertIn("pm.role_work_request", card_ids)
        self.assertIn("pm.material_understanding", card_ids)
        self.assertIn("pm.research_package", card_ids)
        self.assertIn("pm.product_architecture", card_ids)
        self.assertIn("pm.root_contract", card_ids)
        self.assertIn("reviewer.research_direct_source_check", card_ids)
        self.assertIn("product_officer.root_contract_modelability", card_ids)
        self.assertIn("reviewer.worker_result_review", card_ids)

    def test_reviewer_block_events_are_registered_in_external_taxonomy(self) -> None:
        self.assertEqual(router.EXTERNAL_EVENTS["reviewer_blocks_current_node_dispatch"]["flag"], "current_node_dispatch_blocked")
        self.assertEqual(router.EXTERNAL_EVENTS["reviewer_blocks_node_acceptance_plan"]["flag"], "node_acceptance_plan_review_blocked")
        self.assertTrue(router.EXTERNAL_EVENTS["product_officer_model_report"]["legacy"])

    def test_model_miss_review_block_flags_stay_in_sync(self) -> None:
        expected_flags = set(router.MODEL_MISS_REVIEW_BLOCK_FLAGS)
        event_flags = {
            router.EXTERNAL_EVENTS[event_name]["flag"]
            for event_name in router.MODEL_MISS_REVIEW_BLOCK_EVENTS
        }
        card_flags_by_id = {
            entry["card_id"]: set(entry.get("requires_any_flag", []))
            for entry in router.SYSTEM_CARD_SEQUENCE
            if entry.get("card_id") in {"pm.model_miss_triage", "pm.review_repair", "pm.event.reviewer_blocked"}
        }
        repair_writer_flags = set(router.MODEL_MISS_ROUTE_MUTATION_BLOCK_FLAGS) | set(
            router.MODEL_MISS_MATERIAL_DISPATCH_REPAIR_FLAGS
        )

        self.assertEqual(event_flags, expected_flags)
        self.assertEqual(repair_writer_flags, expected_flags)
        self.assertEqual(set(card_flags_by_id), {"pm.model_miss_triage", "pm.review_repair", "pm.event.reviewer_blocked"})
        for card_flags in card_flags_by_id.values():
            self.assertEqual(card_flags, expected_flags)

    def test_skill_entrypoint_remains_small_router_launcher(self) -> None:
        skill_text = (ROOT / "skills" / "flowpilot" / "SKILL.md").read_text(encoding="utf-8")
        line_count = len(skill_text.splitlines())

        self.assertLess(line_count, 120)
        self.assertIn("flowpilot_router.py", skill_text)
        self.assertIn("Do not read FlowPilot reference files", skill_text)
        self.assertNotIn("Final Route-Wide Gate Ledger", skill_text)


if __name__ == "__main__":
    unittest.main()
