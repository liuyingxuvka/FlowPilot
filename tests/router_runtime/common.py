from __future__ import annotations

import json
import hashlib
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock
from pathlib import Path

from .fs_helpers import read_json, unlink_with_windows_retry


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))

import flowpilot_router as router  # noqa: E402
import card_runtime  # noqa: E402
import packet_runtime  # noqa: E402
import role_output_runtime  # noqa: E402
import flowpilot_router_action_handlers_roles as role_action_handlers  # noqa: E402


STARTUP_ANSWERS = {
    "background_collaboration_authorized": True,
    "provenance": "explicit_user_reply",
}

UNSUPPORTED_HEARTBEAT_STARTUP_ANSWERS = {
    **STARTUP_ANSWERS,
    "scheduled_continuation": "allow",
}

USER_REQUEST = {
    "text": "Use FlowPilot to complete the requested project with PM-owned route control.",
    "provenance": "explicit_user_request",
    "source": "activation_turn",
}


class FlowPilotRouterRuntimeTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self._startup_daemon_patch = mock.patch.object(
            router,
            "_spawn_startup_router_daemon_process",
            side_effect=self._fake_startup_daemon_spawn,
        )
        self._startup_daemon_patch.start()
    def tearDown(self) -> None:
        self._startup_daemon_patch.stop()
    def _fake_startup_daemon_spawn(self, project_root: Path, run_root: Path) -> dict:
        result = router.run_router_daemon(
            project_root,
            max_ticks=1,
            observe_only=True,
            release_lock_on_exit=False,
            run_root=run_root,
        )
        return {"pid": 0, "mode": "test_inline_daemon_tick", "result": result}
    def make_project(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="flowpilot-router-"))
    def write_minimal_run(self, root: Path, run_id: str, *, status: str = "running") -> Path:
        run_root = root / ".flowpilot" / "runs" / run_id
        run_root.mkdir(parents=True, exist_ok=True)
        run_root_rel = router.project_relative(root, run_root)
        state = router.new_run_state(run_id, run_root_rel)
        state["status"] = status
        state["daemon_mode_enabled"] = True
        router._copy_runtime_kit_into_run_root(run_root)  # type: ignore[attr-defined]
        router.write_json(run_root / "run.json", {"schema_version": "flowpilot.run.v1", "run_id": run_id})
        router.write_json(router.run_state_path(run_root), state)
        return run_root
    def write_current_focus(self, root: Path, run_root: Path) -> None:
        router.write_json(
            root / ".flowpilot" / "current.json",
            {
                "schema_version": "flowpilot.current.v1",
                "run_id": run_root.name,
                "run_root": router.project_relative(root, run_root),
                "status": "running",
                "updated_at": router.utc_now(),
            },
        )
    def next_and_apply(self, root: Path, payload: dict | None = None) -> dict:
        action = self.next_after_display_sync(root)
        return router.apply_action(root, str(action["action_type"]), self.payload_for_action(action, payload))
    def apply_next_non_card_action(self, root: Path) -> dict:
        action = self.next_after_display_sync(root)
        if action["action_type"] in {"deliver_system_card", "deliver_system_card_bundle"}:
            return {"skipped_relay_action": action["action_type"], "action": action}
        return router.apply_action(root, str(action["action_type"]), self.payload_for_action(action))
    def run_root_for(self, root: Path) -> Path:
        current = read_json(root / ".flowpilot" / "current.json")
        return root / current["run_root"]
    def active_holder_lease_for_packet(self, root: Path, packet_id: str) -> dict:
        run_root = self.run_root_for(root)
        ledger = read_json(run_root / "packet_ledger.json")
        record = next(
            item
            for item in ledger["packets"]
            if isinstance(item, dict) and item.get("packet_id") == packet_id
        )
        self.assertTrue(record["active_holder_lease_issued"])
        return read_json(root / record["active_holder_lease_path"])
    def submit_current_node_result_via_active_holder(
        self,
        root: Path,
        *,
        packet_id: str,
        result_body_text: str = "reviewable result",
    ) -> tuple[str, str]:
        if "Contract Self-Check" not in result_body_text:
            result_body_text = result_body_text.rstrip() + "\n\nContract Self-Check\n\nstatus: pass\n"
        lease = self.active_holder_lease_for_packet(root, packet_id)
        packet_runtime.active_holder_ack(
            root,
            lease_path=lease["lease_path"],
            role=lease["holder_role"],
            agent_id=lease["holder_agent_id"],
            route_version=lease["route_version"],
            frontier_version=lease["frontier_version"],
        )
        envelope = read_json(root / lease["packet_envelope_path"])
        packet_runtime.read_packet_body_for_role(root, envelope, role=lease["holder_role"])
        submission = packet_runtime.active_holder_submit_result(
            root,
            lease_path=lease["lease_path"],
            role=lease["holder_role"],
            agent_id=lease["holder_agent_id"],
            result_body_text=result_body_text,
            next_recipient="project_manager",
            route_version=lease["route_version"],
            frontier_version=lease["frontier_version"],
        )
        self.assertTrue(submission["passed"])
        notice = submission["controller_next_action_notice"]
        self.assertEqual(notice["next_action"], "deliver_result_to_pm_for_disposition")
        return lease["holder_agent_id"], notice["result_envelope_path"]
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
    def pm_package_result_disposition_envelope(
        self,
        root: Path,
        event_name: str,
        *,
        name: str,
        decision: str = "absorbed",
        decision_reason: str = "PM absorbed package results for the formal reviewer gate.",
    ) -> dict:
        run_root = self.run_root_for(root)
        safe_name = name.strip("/").replace("\\", "/")
        return role_output_runtime.submit_output(
            root,
            output_type="pm_package_result_disposition",
            role="project_manager",
            agent_id="agent-project_manager",
            run_id=run_root.name,
            event_name=event_name,
            output_path=run_root / "test_role_outputs" / f"{safe_name}.json",
            body={
                "decided_by_role": "project_manager",
                "decision": decision,
                "decision_reason": decision_reason,
                "residual_risks": [],
            },
        )
    def write_event_envelope(self, root: Path, name: str, envelope: dict) -> tuple[str, str]:
        run_root = self.run_root_for(root)
        safe_name = name.strip("/").replace("\\", "/")
        envelope_path = run_root / "mailbox" / "outbox" / "events" / f"{safe_name}.envelope.json"
        envelope_path.parent.mkdir(parents=True, exist_ok=True)
        envelope_path.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return self.rel(root, envelope_path), hashlib.sha256(envelope_path.read_bytes()).hexdigest()
    def legacy_startup_fact_runtime_envelope(self, root: Path, name: str = "startup/reviewer_startup_fact_report") -> tuple[dict, str, str]:
        run_root = self.run_root_for(root)
        body_path = run_root / "test_role_outputs" / f"{name}.json"
        body_path.parent.mkdir(parents=True, exist_ok=True)
        body_path.write_text(json.dumps(self.legacy_startup_fact_report_body(root), indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
    def submit_legacy_startup_fact_runtime_output_to_ledger(self, root: Path, name: str = "startup/reviewer_startup_fact_report") -> dict:
        run_root = self.run_root_for(root)
        envelope, _, _ = self.legacy_startup_fact_runtime_envelope(root, name)
        ledger_path = run_root / "role_output_ledger.json"
        body_ref = envelope["body_ref"]
        receipt_ref = envelope["runtime_receipt_ref"]
        ledger = read_json(ledger_path) if ledger_path.exists() else {
            "schema_version": role_output_runtime.ROLE_OUTPUT_LEDGER_SCHEMA,
            "run_id": run_root.name,
            "outputs": [],
            "created_at": "2026-05-14T00:00:00Z",
        }
        outputs = ledger.setdefault("outputs", [])
        outputs.append(
            {
                "output_id": "test-startup-fact-report-runtime-receipt",
                "run_id": run_root.name,
                "role": "human_like_reviewer",
                "agent_id": "agent-human_like_reviewer",
                "output_type": "startup_fact_report",
                "output_contract_id": "flowpilot.output_contract.startup_fact_report.v1",
                "body_path": body_ref["path"],
                "body_hash": body_ref["hash"],
                "envelope": envelope,
                "receipt_path": receipt_ref["path"],
                "receipt_hash": receipt_ref["hash"],
                "controller_visibility": "ledger_metadata_only",
                "controller_may_read_body": False,
                "recorded_at": "2026-05-14T00:00:00Z",
            }
        )
        ledger["updated_at"] = "2026-05-14T00:00:00Z"
        ledger_path.write_text(
            json.dumps(ledger, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        return envelope
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
    def model_miss_flowguard_operator_report_body(self) -> dict:
        return {
            "reported_by_role": "flowguard_operator",
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
                self.model_miss_flowguard_operator_report_body(),
            )
            body.update(
                {
                    "flowguard_operator_report_refs": [
                        {
                            "flowguard_operator_role": "flowguard_operator",
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
                    "why_repair_may_start": "FlowGuard operator report generalized the class and PM selected a minimal repair path.",
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
        self.ack_pending_delivered_card(root, "pm.event.reviewer_blocked")
        if not self.flag(root, "pm_model_miss_triage_card_delivered"):
            self.deliver_expected_card(root, "pm.model_miss_triage")
        self.ack_pending_delivered_card(root, "pm.event.reviewer_blocked")
        router.record_external_event(
            root,
            "pm_records_model_miss_triage_decision",
            self.role_decision_envelope(
                root,
                output_name,
                self.model_miss_triage_body(root, decision=decision),
            ),
        )
    def ack_pending_delivered_card(self, root: Path, card_id: str) -> bool:
        run_root = self.run_root_for(root)
        return_ledger_path = run_root / "return_event_ledger.json"
        if not return_ledger_path.exists():
            return False
        return_ledger = read_json(return_ledger_path)
        pending_return = next(
            (
                item
                for item in return_ledger.get("pending_returns", [])
                if isinstance(item, dict) and item.get("card_id") == card_id and item.get("status") == "pending"
            ),
            None,
        )
        if pending_return is None:
            return False
        state = read_json(router.run_state_path(run_root))
        delivery_attempt_id = pending_return.get("delivery_attempt_id")
        delivery = next(
            (
                item
                for item in reversed(state.get("delivered_cards", []))
                if isinstance(item, dict)
                and item.get("card_id") == card_id
                and (not delivery_attempt_id or item.get("delivery_attempt_id") == delivery_attempt_id)
            ),
            None,
        )
        if delivery is None:
            return False
        action = dict(delivery)
        action["action_type"] = "deliver_system_card"
        if not action.get("to_role") and pending_return.get("target_role"):
            action["to_role"] = pending_return["target_role"]
        self.ack_system_card_action(root, action)
        return True
    def flag(self, root: Path, name: str) -> bool:
        run_root = self.run_root_for(root)
        state = read_json(router.run_state_path(run_root))
        return bool(state["flags"].get(name))
    def material_scan_payload(self) -> dict:
        return {
            "packets": [
                {
                    "packet_id": "material-scan-001",
                    "to_role": "worker",
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
                    "to_role": "worker",
                    "body_path": self.rel(root, body_path),
                    "body_hash": hashlib.sha256(body_path.read_bytes()).hexdigest(),
                }
            ]
        }
    def apply_next_packet_action(self, root: Path, expected_action_type: str) -> dict:
        action = self.next_after_display_sync(root)
        while action["action_type"] in {"check_packet_ledger", "open_current_role_agent"}:
            router.apply_action(root, str(action["action_type"]), self.payload_for_action(action))
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
        if "Contract Self-Check" not in result_text:
            result_text = result_text.rstrip() + "\n\nContract Self-Check\n\nstatus: pass\n"
        for record in index["packets"]:
            envelope = packet_runtime.load_envelope(root, record["packet_envelope_path"])
            packet_runtime.read_packet_body_for_role(root, envelope, role=envelope["to_role"])
            agent_id = self.ensure_current_role_agent_for_role(root, str(envelope["to_role"]))
            packet_runtime.write_result(
                root,
                packet_envelope=envelope,
                completed_by_role=envelope["to_role"],
                completed_by_agent_id=str(agent_id),
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
            self.pm_package_result_disposition_envelope(
                root,
                "pm_records_material_scan_result_disposition",
                name="material/pm_material_scan_result_disposition",
                decision=decision,
                decision_reason="PM absorbed material scan results for formal reviewer gate.",
            ),
        )
    def absorb_research_results_with_pm(self, root: Path, index_path: Path, *, decision: str = "absorbed") -> None:
        self.apply_next_packet_action(root, "relay_research_result_to_pm")
        self.open_results_for_pm(root, index_path)
        router.record_external_event(
            root,
            "pm_records_research_result_disposition",
            self.pm_package_result_disposition_envelope(
                root,
                "pm_records_research_result_disposition",
                name="research/pm_research_result_disposition",
                decision=decision,
                decision_reason="PM absorbed research results for formal reviewer gate.",
            ),
        )
    def absorb_current_node_results_with_pm(self, root: Path, result_paths: list[str | Path], *, decision: str = "absorbed") -> None:
        self.apply_until_action(root, "relay_current_node_result_to_pm")
        for result_path in result_paths:
            packet_runtime.read_result_body_for_role(root, read_json(root / result_path), role="project_manager")
        router.record_external_event(
            root,
            "pm_records_current_node_result_disposition",
            self.pm_package_result_disposition_envelope(
                root,
                "pm_records_current_node_result_disposition",
                name="current_node/pm_current_node_result_disposition",
                decision=decision,
                decision_reason="PM absorbed current-node worker result for the formal node-completion gate.",
            ),
        )
    def pm_role_work_request_payload(
        self,
        root: Path,
        *,
        request_id: str = "model-miss-followup-001",
        to_role: str = "flowguard_operator",
        request_kind: str = "model_miss",
        request_mode: str = "blocking",
        output_contract_id: str = "flowpilot.output_contract.flowguard_model_miss_report.v1",
        body_text: str = "Analyze why the FlowGuard model missed this bug class and recommend a minimal repair.",
        supersedes_request_id: str | None = None,
    ) -> dict:
        run_root = self.run_root_for(root)
        body_path = run_root / "test_role_outputs" / "pm_role_work" / f"{request_id}.md"
        body_path.parent.mkdir(parents=True, exist_ok=True)
        body_path.write_text(body_text, encoding="utf-8")
        payload = {
            "requested_by_role": "project_manager",
            "request_id": request_id,
            "to_role": to_role,
            "request_mode": request_mode,
            "request_kind": request_kind,
            "output_contract_id": output_contract_id,
            "packet_body_path": self.rel(root, body_path),
            "packet_body_hash": hashlib.sha256(body_path.read_bytes()).hexdigest(),
        }
        if supersedes_request_id:
            payload["supersedes_request_id"] = supersedes_request_id
        return payload
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
        completed_by_role = str(envelope["to_role"])
        result = packet_runtime.write_result(
            root,
            packet_envelope=envelope,
            completed_by_role=completed_by_role,
            completed_by_agent_id=self.active_agent_id_for_role(root, completed_by_role),
            result_body_text=result_text,
            next_recipient="project_manager",
        )
        return result["result_body_path"].replace("result_body.md", "result_envelope.json")
    def next_after_display_sync(self, root: Path) -> dict:
        action = router.next_action(root)
        while action["action_type"] in {"sync_display_plan", "inject_role_io_protocol"}:
            router.apply_action(root, str(action["action_type"]), self.payload_for_action(action))
            action = router.next_action(root)
        return action
    def router_internal_action_types(self, root: Path) -> list[str]:
        run_root = self.run_root_for(root)
        state = read_json(router.run_state_path(run_root))
        return [
            str(item.get("action_type"))
            for item in state.get("router_internal_mechanical_events", [])
            if isinstance(item, dict)
        ]
    def assert_payload_contract_mentions(self, contract: dict, *fields: str) -> None:
        encoded = json.dumps(contract, sort_keys=True)
        for field in fields:
            self.assertIn(field, encoded)
    def assert_controller_receipt_action_projection(
        self,
        action: dict,
        *,
        receipt_required: bool = True,
        router_pending_apply_required: bool = True,
    ) -> None:
        completion_command = "controller-receipt" if receipt_required else "router-controlled-wait"
        completion_mode = "controller_action_ledger_receipt" if receipt_required else "controller_action_ledger_wait"
        self.assertEqual(action["controller_completion_command"], completion_command)
        self.assertEqual(action["controller_completion_mode"], completion_mode)
        self.assertEqual(action["controller_receipt_required"], receipt_required)
        self.assertEqual(action["router_pending_apply_required"], router_pending_apply_required)
        self.assertFalse(action["apply_required"])
        contract = action["next_step_contract"]
        self.assertEqual(contract["controller_completion_command"], completion_command)
        self.assertEqual(contract["controller_completion_mode"], completion_mode)
        self.assertEqual(contract["controller_receipt_required"], receipt_required)
        self.assertEqual(contract["router_pending_apply_required"], router_pending_apply_required)
        self.assertFalse(contract["apply_required"])
    def assert_controller_receipt_entry_projection(
        self,
        entry: dict,
        *,
        receipt_required: bool = True,
        router_pending_apply_required: bool = True,
    ) -> None:
        completion_command = "controller-receipt" if receipt_required else "router-controlled-wait"
        completion_mode = "controller_action_ledger_receipt" if receipt_required else "controller_action_ledger_wait"
        self.assertEqual(entry["controller_completion_command"], completion_command)
        self.assertEqual(entry["controller_completion_mode"], completion_mode)
        self.assertEqual(entry["controller_receipt_required"], receipt_required)
        self.assertEqual(entry["router_pending_apply_required"], router_pending_apply_required)
        self.assert_controller_receipt_action_projection(
            entry["action"],
            receipt_required=receipt_required,
            router_pending_apply_required=router_pending_apply_required,
        )
    def payload_for_action(self, action: dict, payload: dict | None = None) -> dict:
        payload = dict(payload or {})
        if action.get("action_type") == "open_current_role_agent" and not payload:
            payload.update(self.current_role_agent_payload(action))
        if action.get("requires_user_dialog_display_confirmation"):
            payload["display_confirmation"] = action["payload_template"]["display_confirmation"]
        return payload
    def current_role_agent_payload(self, action: dict) -> dict:
        role = str(action.get("target_role_key") or action.get("to_role") or "")
        contract = action.get("payload_contract") if isinstance(action.get("payload_contract"), dict) else {}
        allowed_values = contract.get("allowed_values") if isinstance(contract.get("allowed_values"), dict) else {}
        run_values = allowed_values.get("current_role_agent_binding.opened_for_run_id")
        run_id = str(run_values[0]) if isinstance(run_values, list) and run_values else "unknown-run"
        return {
            "runtime_role_assistance_capability_status": "available",
            "current_role_agent_binding": {
                "role_key": role,
                "agent_id": f"live-agent-current-{role}",
                "model_policy": "strongest_available",
                "reasoning_effort_policy": "highest_available",
                "binding_open_result": "opened_for_current_packet",
                "opened_for_run_id": run_id,
                "host_liveness_status": "active",
                "liveness_decision": "confirmed_existing_agent",
            },
        }
    def apply_current_role_agent_if_requested(self, root: Path, action: dict | None = None) -> dict:
        action = action or router.run_until_wait(root)
        if action["action_type"] == "open_current_role_agent":
            router.apply_action(root, "open_current_role_agent", self.payload_for_action(action))
            return router.run_until_wait(root)
        return action
    def active_agent_id_for_role(self, root: Path, role: str) -> str:
        run_root = self.run_root_for(root)
        agent_id = router._active_agent_id_for_role(run_root, role)  # type: ignore[attr-defined]
        self.assertIsNotNone(agent_id, f"missing current role binding for {role}")
        return str(agent_id)
    def ensure_current_role_agent_for_role(self, root: Path, role: str) -> str:
        run_root = self.run_root_for(root)
        agent_id = router._active_agent_id_for_role(run_root, role)  # type: ignore[attr-defined]
        if agent_id:
            return str(agent_id)
        state = read_json(router.run_state_path(run_root))
        payload = {
            "runtime_role_assistance_capability_status": "available",
            "current_role_agent_binding": {
                "role_key": role,
                "agent_id": f"live-agent-current-{role}",
                "model_policy": "strongest_available",
                "reasoning_effort_policy": "highest_available",
                "binding_open_result": "opened_for_current_packet",
                "opened_for_run_id": state["run_id"],
                "host_liveness_status": "active",
                "liveness_decision": "confirmed_existing_agent",
            },
        }
        role_action_handlers._write_current_role_agent_binding(router, root, run_root, state, role, payload)
        router.save_run_state(run_root, state)
        return str(router._active_agent_id_for_role(run_root, role))  # type: ignore[attr-defined]
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
        self.assertEqual(summary_record["final_user_report"]["schema_version"], router.FINAL_USER_REPORT_SCHEMA)
        self.assertFalse(summary_record["final_user_report"]["final_report_is_completion_authority"])
        self.assertTrue(summary_record["final_user_report"]["displayed_to_user"])
        self.assertEqual(summary_record["flowpilot_project_url"], router.FLOWPILOT_PROJECT_URL)
        index = read_json(root / ".flowpilot" / "index.json")
        run_entry = next(item for item in index["runs"] if item["run_id"] == read_json(router.run_state_path(run_root))["run_id"])
        self.assertEqual(run_entry["final_summary_path"], self.rel(root, run_root / "final_summary.md"))
        self.assertEqual(run_entry["final_user_report_schema_version"], router.FINAL_USER_REPORT_SCHEMA)
        self.assertFalse(run_entry["final_user_report_is_completion_authority"])
        self.assertEqual(run_entry["flowpilot_project_url"], router.FLOWPILOT_PROJECT_URL)
        return result
    def unsupported_heartbeat_binding_payload(self, root: Path, automation_id: str = "codex-test-heartbeat") -> dict:
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
    def assert_no_startup_heartbeat_action(self, root: Path) -> dict | None:
        action = self.next_after_display_sync(root)
        self.assertNotEqual(action["action_type"], "create_heartbeat_automation")
        return None
    def handle_pending_control_blocker(self, root: Path) -> bool:
        action = self.next_after_display_sync(root)
        if action["action_type"] != "handle_control_blocker":
            return False
        router.apply_action(root, "handle_control_blocker")
        return True
    def deliver_expected_card(self, root: Path, card_id: str) -> dict:
        run_root = self.run_root_for(root)
        pending = read_json(router.run_state_path(run_root)).get("pending_action")
        if isinstance(pending, dict) and pending.get("action_type") == "deliver_system_card" and pending.get("card_id") == card_id:
            self.ack_system_card_action(root, pending)
            return pending
        if (
            isinstance(pending, dict)
            and pending.get("action_type") == "deliver_system_card_bundle"
            and card_id in (pending.get("card_ids") or [])
        ):
            self.ack_system_card_bundle_action(root, pending)
            state = read_json(router.run_state_path(run_root))
            for delivery in reversed(state.get("delivered_cards", [])):
                if isinstance(delivery, dict) and delivery.get("card_id") == card_id:
                    return delivery
            return pending
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
            "inject_role_io_protocol",
            "open_current_role_agent",
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
        agent_id = action.get("target_agent_id") or action.get("waiting_for_agent_id") or self.active_agent_id_for_role(root, role)
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
        agent_id = action.get("target_agent_id") or action.get("waiting_for_agent_id") or self.active_agent_id_for_role(root, role)
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
    def submit_system_card_ack_without_router_next(self, root: Path, action: dict) -> None:
        role = str(action["to_role"])
        agent_id = action.get("target_agent_id") or action.get("waiting_for_agent_id") or self.active_agent_id_for_role(root, role)
        if action["action_type"] == "deliver_system_card_bundle":
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
            return
        self.assertEqual(action["action_type"], "deliver_system_card")
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
    def mark_controller_action_done(self, root: Path, action: dict, payload: dict | None = None) -> None:
        run_root = self.run_root_for(root)
        state = read_json(router.run_state_path(run_root))
        router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        router._write_controller_receipt(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            action_id=action["controller_action_id"],
            status="done",
            payload=payload or {"controller_action_completed": True},
        )
        router.save_run_state(run_root, state)
    def add_current_node_pending_card_return(
        self,
        root: Path,
        *,
        card_id: str = "pm.current_node_loop",
        node_id: str | None = None,
        route_version: int | None = None,
    ) -> dict:
        run_root = self.run_root_for(root)
        frontier = read_json(run_root / "execution_frontier.json")
        node_id = node_id or str(frontier.get("active_node_id") or "node-001")
        route_version = route_version if route_version is not None else int(frontier.get("route_version") or 1)
        ledger_path = run_root / "return_event_ledger.json"
        ledger = read_json(ledger_path)
        pending = {
            "return_kind": "system_card",
            "status": "pending",
            "card_id": card_id,
            "delivery_attempt_id": f"test-pending-{card_id}-{node_id}",
            "card_return_event": f"{card_id.replace('.', '_')}_ack",
            "target_role": "project_manager",
            "expected_return_path": f"runtime/card_returns/test-pending-{card_id}-{node_id}.json",
            "ack_clearance_scope": {
                "schema_version": "flowpilot.system_card_ack_clearance_scope.v1",
                "card_id": card_id,
                "target_role": "project_manager",
                "current_phase": "current_node_loop",
                "card_phase": "current_node_loop",
                "current_node_id": node_id,
                "current_route_id": str(frontier.get("active_route_id") or "route-001"),
                "route_version": route_version,
                "boundary_kind": "node",
                "required_before": [
                    "gate_or_node_boundary_transition",
                    "formal_work_packet_relay_to_target_role",
                ],
                "ack_is_read_receipt_only": True,
                "target_work_completion_evidence_required_separately": True,
            },
        }
        ledger.setdefault("pending_returns", []).append(pending)
        ledger_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return pending
    def set_active_current_node_batch_status(self, root: Path, status: str) -> None:
        run_root = self.run_root_for(root)
        ref = read_json(run_root / "packet_batches" / "active_current_node.json")
        batch_path = root / ref["batch_path"]
        batch = read_json(batch_path)
        batch["status"] = status
        batch_path.write_text(json.dumps(batch, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    def deliver_user_intake_mail(self, root: Path) -> None:
        run_root = self.run_root_for(root)
        state = read_json(router.run_state_path(run_root))
        if state["flags"].get("user_intake_delivered_to_pm"):
            self.assert_startup_user_intake_released_to_pm(root)
            return
        result = self.apply_next_packet_action(root, "deliver_mail")
        self.assertEqual(result["mail_delivery"]["mail_id"], "user_intake")
        self.assert_startup_user_intake_released_to_pm(root)
    def assert_startup_user_intake_held_by_router(self, root: Path) -> None:
        run_root = self.run_root_for(root)
        state = read_json(router.run_state_path(run_root))
        packet_ledger = read_json(run_root / "packet_ledger.json")
        self.assertFalse(state["flags"].get("user_intake_delivered_to_pm", False))
        self.assertEqual(packet_ledger["active_packet_holder"], "router")
        self.assertEqual(packet_ledger["active_packet_status"], "router-held-startup-material")
        record = next(item for item in packet_ledger["packets"] if item["packet_id"] == "user_intake")
        self.assertTrue(record["router_owned_startup_material"])
        self.assertEqual(record["active_packet_holder"], "router")
        self.assertEqual(record["active_packet_status"], "router-held-startup-material")
        self.assertFalse(any(item.get("mail_id") == "user_intake" for item in packet_ledger.get("mail", [])))
        self.assertNotIn("packet_router_release", record)
        self.assertNotIn("router_startup_release", record)
    def assert_startup_user_intake_released_to_pm(self, root: Path) -> None:
        run_root = self.run_root_for(root)
        state = read_json(router.run_state_path(run_root))
        packet_ledger = read_json(run_root / "packet_ledger.json")
        self.assertTrue(state["flags"]["user_intake_delivered_to_pm"])
        self.assertEqual(packet_ledger["active_packet_holder"], "project_manager")
        self.assertEqual(packet_ledger["active_packet_status"], "envelope-relayed")
        record = next(item for item in packet_ledger["packets"] if item["packet_id"] == "user_intake")
        self.assertTrue(record["router_owned_startup_material"])
        self.assertEqual(record["active_packet_holder"], "project_manager")
        self.assertEqual(record["active_packet_status"], "envelope-relayed")
        self.assertNotIn("packet_router_release", record)
        self.assertNotIn("packet_controller_relay", record)
        self.assertEqual(packet_ledger["mail"][0]["mail_id"], "user_intake")
        self.assertEqual(packet_ledger["mail"][0]["delivered_by"], "controller")
    def boot_to_controller(self, root: Path, startup_answers: dict | None = None) -> Path:
        startup_answers = startup_answers or STARTUP_ANSWERS
        while True:
            action = router.next_action(root)
            action_type = str(action["action_type"])
            if action_type == "open_startup_intake_ui":
                router.apply_action(root, action_type, self.startup_intake_payload(root, startup_answers=startup_answers))
            elif action_type == "record_user_request":
                if action.get("requires_payload") == "user_request":
                    router.apply_action(root, action_type, {"user_request": USER_REQUEST})
                else:
                    router.apply_action(root, action_type)
            elif action_type == "load_controller_core":
                router.apply_action(root, action_type, self.payload_for_action(action))
                self.complete_startup_async_controller_rows(root, startup_answers=startup_answers)
                break
            else:
                router.apply_action(root, action_type, self.payload_for_action(action))
        current = read_json(root / ".flowpilot" / "current.json")
        return root / current["run_root"]
    def controller_boundary_recovery_action(self, root: Path) -> tuple[Path, dict, dict]:
        run_root = self.run_root_for(root)
        state = read_json(router.run_state_path(run_root))
        boundary_path = run_root / "startup" / "controller_boundary_confirmation.json"
        if boundary_path.exists():
            boundary_path.unlink()
        flags = state.setdefault("flags", {})
        flags["controller_role_confirmed"] = False
        flags["controller_role_confirmed_from_router_core"] = False
        flags["controller_boundary_confirmation_written"] = False
        flags["controller_boundary_recovery_requested"] = True
        state.pop("controller_boundary_confirmation", None)
        state["pending_action"] = None
        router.save_run_state(run_root, state)
        action = router._next_controller_boundary_confirmation_action(root, state, run_root)  # type: ignore[attr-defined]
        self.assertIsNotNone(action)
        return run_root, state, action
    def boot_to_router_daemon_start(self, root: Path, startup_answers: dict | None = None) -> Path:
        startup_answers = startup_answers or STARTUP_ANSWERS
        while True:
            action = router.next_action(root)
            action_type = str(action["action_type"])
            if action_type == "start_router_daemon":
                return self.run_root_for(root)
            if action_type == "open_startup_intake_ui":
                router.apply_action(root, action_type, self.startup_intake_payload(root, startup_answers=startup_answers))
            elif action_type == "record_user_request":
                if action.get("requires_payload") == "user_request":
                    router.apply_action(root, action_type, {"user_request": USER_REQUEST})
                else:
                    router.apply_action(root, action_type)
            else:
                router.apply_action(root, action_type, self.payload_for_action(action))
    def release_startup_daemon_for_explicit_daemon_test(self, root: Path) -> None:
        try:
            router.stop_router_daemon(root, reason="test_reset_before_explicit_daemon")
        except router.RouterError:
            pass
    def complete_startup_async_controller_rows(self, root: Path, startup_answers: dict | None = None) -> list[str]:
        startup_answers = startup_answers or STARTUP_ANSWERS
        run_root = self.run_root_for(root)
        completed: list[str] = []
        action_dir = run_root / "runtime" / "controller_actions"
        if not action_dir.exists():
            return completed
        for action_path in sorted(action_dir.glob("*.json")):
            entry = read_json(action_path)
            if entry.get("status") in router.CONTROLLER_ACTION_CLOSED_STATUSES and entry.get("router_reconciliation_status") == "reconciled":
                continue
            action_type = entry.get("action_type")
            if action_type not in {"emit_startup_banner"}:
                continue
            action = entry.get("action") if isinstance(entry.get("action"), dict) else {}
            if action_type == "emit_startup_banner":
                payload = self.payload_for_action(action)
            else:
                payload = self.payload_for_action(action)
            router.record_controller_action_receipt(root, action_id=entry["action_id"], status="done", payload=payload)
            completed.append(str(action_type))
        return completed
    def force_current_role_result_wait(self, root: Path, *, waiting_for_role: str = "worker") -> dict:
        run_root = self.run_root_for(root)
        runtime_dir = run_root / "runtime"
        for name in ("controller_actions", "controller_receipts"):
            path = runtime_dir / name
            if path.exists():
                shutil.rmtree(path)
            path.mkdir(parents=True, exist_ok=True)
        ledger_path = runtime_dir / "controller_action_ledger.json"
        if ledger_path.exists():
            ledger_path.unlink()
        state = read_json(router.run_state_path(run_root))
        wait_action = router.make_action(
            action_type="await_role_decision",
            actor="controller",
            label="controller_waits_for_current_role_result",
            summary="Controller waits for a current runtime role result through Router-directed runtime output.",
            to_role=waiting_for_role,
            extra={
                "waiting_for_role": waiting_for_role,
                "allowed_external_events": ["role_work_result_returned"],
                "expected_return_path": "pm_role_work/current_role_result.json",
            },
        )
        state["pending_action"] = wait_action
        state["daemon_mode_enabled"] = True
        lock = router._acquire_router_daemon_lock(root, run_root, state)  # type: ignore[attr-defined]
        router._write_controller_action_entry(root, run_root, state, wait_action)  # type: ignore[attr-defined]
        router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
            current_action=wait_action,
            lock=lock,
        )
        router.save_run_state(run_root, state)
        return wait_action
    def old_utc(self, *, minutes: int) -> str:
        return (
            datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=minutes)
        ).isoformat().replace("+00:00", "Z")
    def startup_intake_payload(
        self,
        root: Path,
        *,
        startup_answers: dict | None = None,
        body_text: str | None = None,
        status: str = "confirmed",
        launch_mode: str = "interactive_native",
        headless: bool = False,
        formal_startup_allowed: bool = True,
    ) -> dict:
        startup_answers = startup_answers or STARTUP_ANSWERS
        bootstrap = self.bootstrap_state(root)
        output_dir = root / ".flowpilot" / "bootstrap" / "startup_intake" / str(bootstrap.get("run_id") or "test-run")
        output_dir.mkdir(parents=True, exist_ok=True)
        receipt_path = output_dir / "startup_intake_receipt.json"
        result_path = output_dir / "startup_intake_result.json"
        recorded_at = "2026-05-13T00:00:00Z"
        if status in {"cancelled", "blocked"}:
            blocked = status == "blocked"
            receipt = {
                "schema_version": router.STARTUP_INTAKE_RECEIPT_SCHEMA,
                "status": status,
                "ui_surface": "native_wpf_startup_intake",
                "launch_mode": launch_mode,
                "headless": headless,
                "formal_startup_allowed": formal_startup_allowed,
                "language": "en",
                "startup_answers": startup_answers,
                "confirmed_by_user": False,
                "cancelled_by_user": not blocked,
                "recorded_at": recorded_at,
            }
            if blocked:
                receipt["block_reason"] = "background_collaboration_required"
            receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            result = {
                "schema_version": router.STARTUP_INTAKE_RESULT_SCHEMA,
                "status": status,
                "launch_mode": launch_mode,
                "headless": headless,
                "formal_startup_allowed": formal_startup_allowed,
                "receipt_path": self.rel(root, receipt_path),
                "controller_visibility": "block_status_only" if blocked else "cancel_status_only",
                "body_text_included": False,
                "recorded_at": recorded_at,
            }
            if blocked:
                result["startup_answers"] = startup_answers
                result["block_reason"] = "background_collaboration_required"
            result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            return {"startup_intake_result": {"result_path": self.rel(root, result_path)}}

        body_path = output_dir / "startup_intake_body.md"
        envelope_path = output_dir / "startup_intake_envelope.json"
        body_path.write_text(body_text or USER_REQUEST["text"], encoding="utf-8")
        body_hash = hashlib.sha256(body_path.read_bytes()).hexdigest()
        receipt = {
            "schema_version": router.STARTUP_INTAKE_RECEIPT_SCHEMA,
            "status": "confirmed",
            "ui_surface": "native_wpf_startup_intake",
            "launch_mode": launch_mode,
            "headless": headless,
            "formal_startup_allowed": formal_startup_allowed,
            "language": "en",
            "startup_answers": startup_answers,
            "confirmed_by_user": True,
            "cancelled_by_user": False,
            "body_path": self.rel(root, body_path),
            "body_hash": body_hash,
            "envelope_path": self.rel(root, envelope_path),
            "body_text_included": False,
            "recorded_at": recorded_at,
        }
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        envelope = {
            "schema_version": router.STARTUP_INTAKE_ENVELOPE_SCHEMA,
            "status": "confirmed",
            "source": "native_wpf_startup_intake",
            "launch_mode": launch_mode,
            "headless": headless,
            "formal_startup_allowed": formal_startup_allowed,
            "language": "en",
            "startup_answers": startup_answers,
            "body_path": self.rel(root, body_path),
            "body_hash": body_hash,
            "receipt_path": self.rel(root, receipt_path),
            "body_visibility": "sealed_pm_only",
            "controller_visibility": "envelope_only",
            "controller_may_read_body": False,
            "body_text_included": False,
            "recorded_at": recorded_at,
        }
        envelope_path.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result = {
            "schema_version": router.STARTUP_INTAKE_RESULT_SCHEMA,
            "status": "confirmed",
            "launch_mode": launch_mode,
            "headless": headless,
            "formal_startup_allowed": formal_startup_allowed,
            "startup_answers": startup_answers,
            "language": "en",
            "receipt_path": self.rel(root, receipt_path),
            "envelope_path": self.rel(root, envelope_path),
            "body_path": self.rel(root, body_path),
            "body_hash": body_hash,
            "controller_visibility": "envelope_only",
            "controller_may_read_body": False,
            "body_text_included": False,
            "recorded_at": recorded_at,
        }
        result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {"startup_intake_result": {"result_path": self.rel(root, result_path)}}
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
                "replacement_opened_after_resume_state_loaded": False,
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
            "runtime_role_assistance_capability_status": "available",
            "liveness_probe_batch_id": batch_id,
            "liveness_probe_mode": "concurrent_batch",
            "all_liveness_probes_started_before_wait": True,
            "rehydrated_role_bindings": records,
        }
    def role_recovery_agent_payload(self, root: Path, action: dict, *, role: str = "worker") -> dict:
        request = next(item for item in action["role_recovery_request"] if item["role_key"] == role)
        transaction = action["role_recovery_transaction"]
        recovered = {
            "role_key": role,
            "old_agent_id": request["old_agent_id"],
            "agent_id": f"recovered-{transaction['transaction_id']}-{role}",
            "model_policy": "strongest_available",
            "reasoning_effort_policy": "highest_available",
            "recovery_result": "targeted_replacement_opened",
            "restore_attempted": True,
            "restore_result": "failed",
            "targeted_replacement_attempted": True,
            "targeted_replacement_result": "success",
            "host_liveness_status": "active",
            "liveness_decision": "opened_replacement_from_current_run_memory",
            "slot_reconciliation_attempted": False,
            "full_role_binding_recovery_attempted": False,
            "rehydrated_for_run_id": transaction["run_id"],
            "memory_context_injected": True,
            "packet_ownership_reconciled": True,
            "role_binding_epoch_advanced": True,
            "superseded_agent_output_quarantined": True,
        }
        if request.get("role_memory_status") == "available":
            recovered.update(
                {
                    "memory_packet_path": request["memory_packet_path"],
                    "memory_packet_hash": request["memory_packet_hash"],
                    "memory_seeded_from_current_run": True,
                }
            )
        else:
            recovered.update(
                {
                    "memory_missing_acknowledged": True,
                    "replacement_seeded_from_common_run_context": True,
                }
            )
        return {
            "runtime_role_assistance_capability_status": "available",
            "recovery_transaction_id": transaction["transaction_id"],
            "trigger_source": transaction["trigger_source"],
            "recovery_scope": transaction["recovery_scope"],
            "target_role_keys": transaction["target_role_keys"],
            "recovered_role_bindings": [recovered],
        }
    def write_worker_recovery_wait_action(
        self,
        root: Path,
        *,
        label: str,
        allowed_event: str = "worker_scan_results_returned",
        extra: dict | None = None,
    ) -> dict:
        run_root = self.run_root_for(root)
        state = read_json(router.run_state_path(run_root))
        action = router.make_action(
            action_type="await_role_decision",
            actor="controller",
            label=label,
            summary=f"Controller waits for worker test output: {label}",
            allowed_reads=[],
            allowed_writes=[],
            to_role="worker",
            extra={"allowed_external_events": [allowed_event], **(extra or {})},
        )
        entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)
        return entry
    def recover_worker_after_liveness_fault(self, root: Path) -> dict:
        router.record_external_event(
            root,
            "controller_reports_role_liveness_fault",
            {
                "role_key": "worker",
                "host_liveness_status": "missing",
                "detected_by": "controller",
            },
        )
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "load_role_recovery_state")
        router.apply_action(root, "load_role_recovery_state")
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "recover_role_bindings")
        router.apply_action(root, "recover_role_bindings", self.role_recovery_agent_payload(root, action, role="worker"))
        return read_json(self.run_root_for(root) / "continuation" / "role_recovery_report.json")
    def bootstrap_state(self, root: Path) -> dict:
        return read_json(router.bootstrap_state_path(root))
    def deliver_startup_fact_check_card(self, root: Path) -> dict:
        raise AssertionError("reviewer.startup_fact_check is not part of the current startup path")
    def deliver_startup_fact_check_card_without_ack(self, root: Path) -> dict:
        raise AssertionError("reviewer.startup_fact_check is not part of the current startup path")
    def deliver_startup_runtime_prompt_cards(self, root: Path) -> None:
        self.deliver_expected_card(root, "pm.core")
        self.deliver_expected_card(root, "pm.output_contract_catalog")
        self.deliver_expected_card(root, "pm.role_work_request")
        self.deliver_expected_card(root, "pm.phase_map")
        self.deliver_expected_card(root, "pm.startup_intake")
    def deliver_initial_pm_cards_and_user_intake(self, root: Path) -> None:
        self.complete_startup_runtime_entry(root)
    def complete_startup_runtime_entry(self, root: Path) -> None:
        run_root = self.run_root_for(root)
        self.deliver_startup_runtime_prompt_cards(root)
        self.assert_startup_user_intake_held_by_router(root)
        self.deliver_user_intake_mail(root)
        self.assert_startup_user_intake_released_to_pm(root)
        self.write_self_interrogation_record(
            root,
            "startup",
            source_path=run_root / "mailbox" / "outbox" / "user_intake.json",
        )
        self.assertTrue((run_root / "display" / "display_surface.json").exists())
    def material_review_source_paths(self, root: Path) -> list[str]:
        run_root = self.run_root_for(root)
        return [
            self.rel(root, run_root / "material" / "pm_material_scan_formal_gate_package.json"),
            self.rel(root, run_root / "material" / "material_artifact_map.json"),
        ]
    def complete_material_flow(self, root: Path, material_understanding_payload: dict | None = None) -> None:
        self.deliver_expected_card(root, "pm.material_scan")

        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        self.apply_next_packet_action(root, "relay_material_scan_packets")
        run_root = self.run_root_for(root)
        material_index_path = run_root / "material" / "material_scan_packets.json"
        self.open_packets_and_write_results(root, material_index_path, result_text="material scan result")
        router.record_external_event(root, "worker_scan_packet_bodies_delivered_after_dispatch")
        router.record_external_event(root, "worker_scan_results_returned")
        self.absorb_material_scan_results_with_pm(root, material_index_path)

        self.deliver_expected_card(root, "reviewer.material_sufficiency")

        router.record_external_event(
            root,
            "reviewer_reports_material_sufficient",
            self.role_report_envelope(
                root,
                "material/reviewer_material_sufficiency",
                {
                    "pm_visible_summary": ["Reviewed material is sufficient for PM planning."],
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": True,
                    "direct_material_sources_checked": True,
                    "packet_matches_checked_sources": True,
                    "pm_ready": True,
                    "checked_source_paths": self.material_review_source_paths(root),
                    "runtime_open_receipt_refs": [],
                    "findings": [],
                    "blockers": [],
                    "pm_suggestion_items": [],
                    "contract_self_check": {"status": "pass"},
                },
            ),
        )
        self.deliver_expected_card(root, "pm.event.reviewer_report")

        self.deliver_expected_card(root, "pm.material_absorb_or_research")

        router.record_external_event(root, "pm_accepts_reviewed_material")
        self.deliver_expected_card(root, "pm.material_understanding")
        router.record_external_event(
            root,
            "pm_writes_material_understanding",
            material_understanding_payload or {"material_summary": "reviewed material accepted"},
        )
    def complete_root_contract_before_child_skill_gates(self, root: Path) -> None:
        run_root = self.run_root_for(root)
        self.deliver_expected_card(root, "pm.product_architecture")
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

        self.deliver_expected_card(root, "flowguard_operator.product_architecture_modelability")
        router.record_external_event(
            root,
            "flowguard_operator_submits_product_behavior_model",
            self.role_report_envelope(
                root,
                "flowguard/product_behavior_model",
                {"reviewed_by_role": "flowguard_operator", "passed": True},
            ),
        )

        self.deliver_expected_card(root, "pm.product_behavior_model_decision")
        router.record_external_event(root, "pm_accepts_product_behavior_model", self.product_behavior_model_decision_body())

        self.deliver_expected_card(root, "reviewer.product_architecture_challenge")
        router.record_external_event(
            root,
            "reviewer_passes_product_architecture",
            self.role_report_envelope(
                root,
                "reviews/product_architecture_challenge",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )
        self.write_self_interrogation_record(
            root,
            "product_architecture",
            source_path=run_root / "product_function_architecture.json",
        )

        self.deliver_expected_card(root, "pm.root_contract")
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

        self.deliver_expected_card(root, "reviewer.root_contract_challenge")
        router.record_external_event(
            root,
            "reviewer_passes_root_acceptance_contract",
            self.role_report_envelope(
                root,
                "reviews/root_contract_challenge",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )

        router.record_external_event(root, "pm_freezes_root_acceptance_contract")
    def complete_product_architecture_and_contract(self, root: Path) -> None:
        self.complete_root_contract_before_child_skill_gates(root)
        self.complete_child_skill_gates(root)
        self.complete_implementation_intent_bridge(root)

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
    def complete_implementation_intent_bridge(self, root: Path) -> None:
        self.deliver_expected_card(root, "pm.implementation_intent")
        router.record_external_event(root, "pm_writes_implementation_intent", self.pm_implementation_intent_body())

        self.deliver_expected_card(root, "flowguard_operator.target_realization_model")
        router.record_external_event(
            root,
            "flowguard_operator_submits_target_realization_model",
            self.role_report_envelope(
                root,
                "flowguard/target_realization_model",
                self.target_realization_model_pass_body(),
            ),
        )

        self.deliver_expected_card(root, "pm.target_realization_model_decision")
        router.record_external_event(
            root,
            "pm_accepts_target_realization_model",
            self.target_realization_model_decision_body(),
        )

        self.deliver_expected_card(root, "reviewer.implementation_intent_challenge")
        router.record_external_event(
            root,
            "reviewer_passes_implementation_intent_challenge",
            self.role_report_envelope(
                root,
                "reviews/implementation_intent_challenge",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )
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
                        "required_approver": "flowguard_operator",
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

        router.record_external_event(root, "pm_approves_child_skill_manifest_for_route")
        self.next_after_display_sync(root)
    def complete_pre_route_gates(self, root: Path) -> None:
        self.complete_startup_runtime_entry(root)
        self.complete_material_flow(root)
        self.complete_product_architecture_and_contract(root)
    def activate_route(self, root: Path, node_id: str = "node-001") -> None:
        router.record_external_event(
            root,
            "pm_activates_reviewed_route",
            {"route_id": "route-001", "active_node_id": node_id, "route_version": 1},
        )
    def complete_route_checks(self, root: Path) -> None:
        self.deliver_expected_card(root, "flowguard_operator.route_process_check")
        router.record_external_event(
            root,
            "flowguard_operator_submits_process_route_model",
            self.role_report_envelope(
                root,
                "flowguard/process_route_model",
                self.route_process_pass_body(),
            ),
        )
        self.deliver_expected_card(root, "pm.process_route_model_decision")
        router.record_external_event(root, "pm_accepts_process_route_model", self.process_route_model_decision_body())
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
            "reviewed_by_role": "flowguard_operator",
            "passed": True,
            "process_viability_verdict": "pass",
            "product_behavior_model_checked": True,
            "target_realization_model_checked": True,
            "route_maps_to_target_realization_model": True,
            "realization_obligations_projected": True,
            "route_can_reach_product_model": True,
            "repair_return_policy_checked": True,
            "serial_execution_model_checked": True,
            "all_effective_nodes_reachable_in_order": True,
            "recursive_child_routes_serialized": True,
        }
    def route_product_pass_body(self) -> dict:
        return {
            "reviewed_by_role": "flowguard_operator",
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
            "pm_model_fit_review": "PM accepted the product-scope FlowGuard model as the product basis.",
            "product_goal_coverage": "The model covers the requested product goal.",
            "unmodeled_or_ambiguous_behavior": [],
            "next_action": "reviewer_product_architecture_challenge",
        }
    def pm_implementation_intent_body(self) -> dict:
        return {
            "written_by_role": "project_manager",
            "implementation_intent_summary": "Realize the accepted product through one practical route without downgrading the user target.",
            "implementation_pathways": [
                {
                    "pathway_id": "impl-001",
                    "summary": "Build a route that turns product behavior into executable work and evidence.",
                }
            ],
            "target_realization_model_request": {
                "requested_model_id": "target-realization-001",
                "expected_path": "flowguard/target_realization_model.json",
            },
            "realization_obligations": [
                {
                    "obligation_id": "realize-001",
                    "summary": "Route must preserve the accepted product behavior and proof floor.",
                }
            ],
            "thin_success_traps": [
                {
                    "trap_id": "thin-001",
                    "summary": "A route can look complete while leaving the product unusable.",
                }
            ],
            "non_downgrade_rules": [
                {
                    "rule_id": "no-downgrade-001",
                    "summary": "Do not replace required product behavior with a weaker planning artifact.",
                }
            ],
            "evidence_gates": [
                {
                    "gate_id": "evidence-001",
                    "summary": "Final closure must prove the product behavior and realization obligation.",
                }
            ],
            "residual_blindspots": [],
            "next_action": "flowguard_operator_target_realization_model",
        }
    def target_realization_model_pass_body(self) -> dict:
        return {
            "reviewed_by_role": "flowguard_operator",
            "passed": True,
            "target_realization_verdict": "pass",
            "pm_implementation_intent_checked": True,
            "product_behavior_model_checked": True,
            "pm_intent_preserved": True,
            "realization_obligations_modeled": True,
            "thin_success_traps_modeled": True,
            "evidence_gates_modeled": True,
            "realization_obligation_ids": ["realize-001"],
            "model_obligations": [{"obligation_id": "realize-001"}],
            "thin_success_traps": [{"trap_id": "thin-001"}],
            "non_downgrade_rules": [{"rule_id": "no-downgrade-001"}],
            "evidence_gates": [{"gate_id": "evidence-001"}],
            "target_state_model": {"states": ["planned", "realized"]},
            "transition_model": {"transitions": ["planned_to_realized"]},
            "conformance_boundary": {"scope": "target realization bridge"},
            "residual_blindspots": [],
        }
    def target_realization_model_decision_body(self) -> dict:
        return {
            "decided_by_role": "project_manager",
            "decision": "accept_target_realization_model",
            "source_paths": [
                "implementation_intent/pm_implementation_intent.json",
                "flowguard/target_realization_model.json",
            ],
            "target_realization_fit_review": "PM accepted the model as preserving implementation intent.",
            "realization_obligation_acceptance": "The realization obligation can guide route drafting.",
            "thin_success_trap_review": "Thin success traps are modeled for later gates.",
            "evidence_gate_review": "Evidence gates are explicit enough for route projection.",
            "non_downgrade_review": "No downgrade rule is hidden.",
            "residual_blindspots": [],
            "next_action": "reviewer_implementation_intent_challenge",
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
            "next_action": "reviewer_route_challenge",
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
        frontier = read_json(self.run_root_for(root) / "execution_frontier.json")
        self.write_self_interrogation_record(
            root,
            "node_entry",
            node_id=str(frontier["active_node_id"]),
            route_version=int(frontier.get("route_version") or 1),
            source_path=self.run_root_for(root)
            / "routes"
            / str(frontier["active_route_id"])
            / "nodes"
            / str(frontier["active_node_id"])
            / "node_acceptance_plan.json",
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
    def legacy_startup_fact_report_body(self, root: Path) -> dict:
        run_root = self.run_root_for(root)
        return {
            "reviewed_by_role": "human_like_reviewer",
            "passed": True,
            "external_fact_review": {
                "reviewed_by_role": "human_like_reviewer",
                "self_attested_ai_claims_accepted_as_proof": False,
                "reviewer_checked_requirement_ids": [],
                "direct_evidence_paths_checked": [],
            },
        }
    def prior_path_context_review(self, root: Path, impact: str = "PM considered current route memory before deciding") -> dict:
        run_root = self.run_root_for(root)
        source_paths = [
            self.rel(root, run_root / "route_memory" / "pm_prior_path_context.json"),
            self.rel(root, run_root / "route_memory" / "route_history_index.json"),
        ]
        material_map_path = run_root / "material" / "material_artifact_map.json"
        if material_map_path.exists():
            source_paths.append(self.rel(root, material_map_path))
        return {
            "prior_path_context_review": {
                "reviewed": True,
                "source_paths": source_paths,
                "material_artifact_map_considered": material_map_path.exists(),
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
            "recovery_option": "same_gate_repair",
            "return_gate": rerun_target,
            "rerun_target": rerun_target,
            "repair_transaction": {
                "plan_kind": "role_reissue",
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
    def write_self_interrogation_record(
        self,
        root: Path,
        scope: str,
        *,
        clean: bool = True,
        node_id: str | None = None,
        route_version: int = 1,
        source_path: Path | None = None,
        record_id: str | None = None,
    ) -> Path:
        run_root = self.run_root_for(root)
        if source_path is None:
            source_path = run_root / "self_interrogation" / "sources" / f"{scope}_source.json"
            source_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.write_text(json.dumps({"scope": scope}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if node_id is None and scope in {"node_entry", "repair", "role_result"}:
            frontier = read_json(run_root / "execution_frontier.json")
            node_id = str(frontier.get("active_node_id") or "node-001")
            route_version = int(frontier.get("route_version") or route_version)
        record_id = record_id or f"{scope}-{node_id or 'run'}-self-check"
        record_path = run_root / "self_interrogation" / f"{record_id}.json"
        finding_id = f"{record_id}-finding-001"
        disposition = {
            "status": "reject_with_reason" if clean else "pending",
            "decided_by_role": "project_manager" if clean else None,
            "decided_at": "2026-05-10T00:00:00Z" if clean else None,
            "reason": "PM reviewed this self-interrogation finding and rejected it for this test route." if clean else None,
            "target_node_or_gate_id": None,
            "suggestion_id": None,
            "artifact_path": None,
            "waiver_authority_role": None,
            "residual_risk_statement": "No residual route impact for this test fixture." if clean else None,
        }
        record = {
            "schema_version": "flowpilot.self_interrogation_record.v1",
            "record_id": record_id,
            "run_id": run_root.name,
            "route_id": "route-001",
            "route_version": route_version,
            "node_id": node_id,
            "scope": scope,
            "owner_role": "project_manager",
            "source_event": f"test_records_{scope}_self_interrogation",
            "source_artifact_path": self.rel(root, source_path),
            "findings": [
                {
                    "finding_id": finding_id,
                    "severity": "hard_blocker",
                    "category": "test_fixture",
                    "summary": "Self-interrogation test fixture finding.",
                    "downstream_obligation": "PM must disposition before the protected gate.",
                    "blocks_current_gate_until_disposition": True,
                    "disposition": disposition,
                }
            ],
            "unresolved_hard_finding_count": 0 if clean else 1,
            "pm_disposition_summary": {
                "status": "complete" if clean else "pending",
                "dispositioned_by_role": "project_manager" if clean else None,
                "summary": "Fixture finding was dispositioned." if clean else "Fixture finding is still pending.",
            },
            "downstream_artifact_paths": [self.rel(root, source_path)] if clean else [],
            "pm_suggestion_ledger_ids": [],
        }
        record_path.parent.mkdir(parents=True, exist_ok=True)
        record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        index_path = run_root / "self_interrogation_index.json"
        index = read_json(index_path) if index_path.exists() else {
            "schema_version": "flowpilot.self_interrogation_index.v1",
            "run_id": run_root.name,
            "records": [],
        }
        records = [item for item in index.get("records", []) if isinstance(item, dict) and item.get("record_id") != record_id]
        records.append(
            {
                "record_id": record_id,
                "scope": scope,
                "route_id": "route-001",
                "route_version": route_version,
                "node_id": node_id,
                "owner_role": "project_manager",
                "record_path": self.rel(root, record_path),
            }
        )
        index["records"] = records
        index["updated_at"] = "2026-05-10T00:00:00Z"
        index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return record_path
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
                "worker_or_flowguard_operator_advisory_only": False,
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
            to_role="worker",
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
        agent_id, result_path = self.submit_current_node_result_via_active_holder(
            root,
            packet_id=packet_id,
            result_body_text="reviewable result",
        )
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
                    "agent_role_map": {agent_id: "worker"},
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
        completed_by_role: str = "worker",
        completed_by_agent_id: str = "agent-worker-1",
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
            to_role="worker",
            node_id="node-001",
            body_text="current node work",
            metadata={"route_version": 1},
        )
        packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
        router.record_external_event(root, "pm_registers_current_node_packet", {"packet_id": packet_id, "packet_envelope_path": packet_path})
        self.apply_until_action(root, "relay_current_node_packet")
        if completed_by_role == "worker":
            completed_by_agent_id, result_path = self.submit_current_node_result_via_active_holder(
                root,
                packet_id=packet_id,
                result_body_text="reviewable result",
            )
        else:
            packet_runtime.read_packet_body_for_role(root, read_json(root / packet_path), role="worker")
            result = packet_runtime.write_result(
                root,
                packet_envelope=read_json(root / packet_path),
                completed_by_role=completed_by_role,
                completed_by_agent_id=completed_by_agent_id,
                result_body_text="reviewable result",
                next_recipient="project_manager",
                strict_role=False,
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
            action = self.next_after_display_sync(root)
            action_type = str(action["action_type"])
            if action_type == "deliver_system_card":
                self.ack_system_card_action(root, action)
            elif action_type == "deliver_system_card_bundle":
                self.ack_system_card_bundle_action(root, action)
            elif action_type == "await_card_return_event":
                self.ack_system_card_action(root, action)
            elif action_type in {
                "check_packet_ledger",
                "open_current_role_agent",
                "confirm_controller_core_boundary",
                "inject_role_io_protocol",
                "write_startup_mechanical_audit",
                "write_display_surface_status",
            }:
                router.apply_action(root, action_type, self.payload_for_action(action))
            else:
                router.apply_action(root, action_type, self.payload_for_action(action))
            if action_type == expected_action_type:
                return action
        raise AssertionError(f"did not apply {expected_action_type} within {max_steps} router steps")


