from __future__ import annotations

import json
import hashlib
import contextlib
import io
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock
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
        router.write_json(run_root / "run.json", {"schema_version": "flowpilot.run.v1", "run_id": run_id})
        router.write_json(router.run_state_path(run_root), state)
        return run_root

    def write_current_focus(self, root: Path, run_root: Path) -> None:
        router.write_json(
            root / ".flowpilot" / "current.json",
            {
                "schema_version": "flowpilot.current.v1",
                "current_run_id": run_root.name,
                "current_run_root": router.project_relative(root, run_root),
                "status": "running",
                "updated_at": router.utc_now(),
            },
        )

    def test_startup_intake_powershell_sources_with_non_ascii_use_utf8_bom(self) -> None:
        scripts = (
            ROOT / "skills" / "flowpilot" / "assets" / "ui" / "startup_intake" / "flowpilot_startup_intake.ps1",
            ROOT / "docs" / "ui" / "startup_intake_desktop_preview" / "flowpilot_startup_intake.ps1",
        )
        for script in scripts:
            with self.subTest(script=script.relative_to(ROOT).as_posix()):
                data = script.read_bytes()
                self.assertTrue(any(byte >= 0x80 for byte in data), "test requires non-ASCII script source")
                self.assertTrue(data.startswith(b"\xef\xbb\xbf"), "non-ASCII .ps1 source must be UTF-8 BOM for Windows PowerShell 5.1")

    def test_startup_intake_ui_writes_utf8_without_bom(self) -> None:
        if sys.platform != "win32" or shutil.which("powershell") is None:
            self.skipTest("startup intake WPF smoke requires Windows PowerShell")
        root = self.make_project()
        output_dir = root / "startup-intake-output"
        script = ROOT / "skills" / "flowpilot" / "assets" / "ui" / "startup_intake" / "flowpilot_startup_intake.ps1"
        result = subprocess.run(
            [
                "powershell",
                "-STA",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
                "-OutputDir",
                str(output_dir),
                "-HeadlessConfirmText",
                "Check startup intake encoding",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        for name in (
            "startup_intake_result.json",
            "startup_intake_receipt.json",
            "startup_intake_envelope.json",
            "startup_intake_body.md",
        ):
            data = (output_dir / name).read_bytes()
            self.assertFalse(data.startswith(b"\xef\xbb\xbf"), name)
        for name in (
            "startup_intake_result.json",
            "startup_intake_receipt.json",
            "startup_intake_envelope.json",
        ):
            self.assertEqual((output_dir / name).read_bytes()[:1], b"{", name)
        result_payload = json.loads((output_dir / "startup_intake_result.json").read_text(encoding="utf-8"))
        self.assertEqual(result_payload["launch_mode"], "headless")
        self.assertTrue(result_payload["headless"])
        self.assertFalse(result_payload["formal_startup_allowed"])

    def test_startup_intake_ui_runs_from_installed_skill_without_repo_assets(self) -> None:
        if sys.platform != "win32" or shutil.which("powershell") is None:
            self.skipTest("startup intake WPF smoke requires Windows PowerShell")
        root = self.make_project()
        install_root = root / "skills-install" / "flowpilot"
        shutil.copytree(ROOT / "skills" / "flowpilot", install_root)
        output_dir = root / "startup-intake-output"
        script = install_root / "assets" / "ui" / "startup_intake" / "flowpilot_startup_intake.ps1"

        result = subprocess.run(
            [
                "powershell",
                "-STA",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
                "-OutputDir",
                str(output_dir),
                "-HeadlessConfirmText",
                "Check startup intake installed skill asset lookup",
            ],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=60,
        )

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertTrue((output_dir / "startup_intake_result.json").is_file())

    def test_router_accepts_utf8_bom_json_control_artifact(self) -> None:
        root = self.make_project()
        path = root / "bom.json"
        path.write_bytes(b"\xef\xbb\xbf" + json.dumps({"ok": True}).encode("utf-8"))
        self.assertEqual(router.read_json(path), {"ok": True})

    def test_startup_intake_body_bom_is_not_injected_into_pm_packet_body(self) -> None:
        root = self.make_project()
        body_path = root / "startup_intake_body.md"
        body_path.write_bytes(b"\xef\xbb\xbfBuild with the existing requirements.")
        body_hash = packet_runtime.sha256_file(body_path)
        body = router._build_user_intake_body_from_ref(
            root,
            {
                "body_path": self.rel(root, body_path),
                "body_hash": body_hash,
                "startup_intake_record_path": "startup_intake/startup_intake_record.json",
                "startup_intake_receipt_path": "startup_intake/startup_intake_receipt.json",
                "startup_intake_envelope_path": "startup_intake/startup_intake_envelope.json",
            },
            STARTUP_ANSWERS,
        )
        self.assertIn("Build with the existing requirements.", body)
        self.assertNotIn("\ufeff", body)

    def test_next_effective_node_returns_parent_before_sibling_module_after_last_child(self) -> None:
        route = {
            "route_id": "route-001",
            "nodes": [
                {
                    "node_id": "route-root",
                    "title": "Root",
                    "node_kind": "root",
                    "children": [
                        {
                            "node_id": "module-a",
                            "title": "Module A",
                            "node_kind": "module",
                            "children": [
                                {"node_id": "leaf-a1", "title": "A1", "node_kind": "leaf"},
                                {"node_id": "leaf-a2", "title": "A2", "node_kind": "leaf"},
                            ],
                        },
                        {
                            "node_id": "module-b",
                            "title": "Module B",
                            "node_kind": "module",
                            "children": [
                                {"node_id": "leaf-b1", "title": "B1", "node_kind": "leaf"},
                            ],
                        },
                    ],
                }
            ],
        }

        next_node_id = router._next_effective_node_id(
            route,
            {},
            ["leaf-a1", "leaf-a2"],
            "leaf-a2",
        )
        self.assertEqual(next_node_id, "module-a")

        next_node_after_parent_review = router._next_effective_node_id(
            route,
            {},
            ["leaf-a1", "leaf-a2", "module-a"],
            "module-a",
        )
        self.assertEqual(next_node_after_parent_review, "leaf-b1")

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
        return root / current["current_run_root"]

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

    def submit_startup_fact_runtime_output_to_ledger(self, root: Path, name: str = "startup/reviewer_startup_fact_report") -> dict:
        run_root = self.run_root_for(root)
        envelope, _, _ = self.startup_fact_runtime_envelope(root, name)
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

    def submit_system_card_ack_without_router_next(self, root: Path, action: dict) -> None:
        role = str(action["to_role"])
        agent_id = action.get("target_agent_id") or action.get("waiting_for_agent_id") or f"{role}-agent"
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
        self.assert_startup_user_intake_released_to_pm(root)

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
        self.assertEqual(record["packet_router_release"]["relayed_to_role"], "project_manager")
        self.assertTrue(record["packet_router_release"]["delivered_by_router"])
        self.assertEqual(packet_ledger["mail"][0]["mail_id"], "user_intake")
        self.assertEqual(packet_ledger["mail"][0]["delivered_by"], "router")
        action_dir = run_root / "runtime" / "controller_actions"
        controller_action_types = [
            read_json(path).get("action_type")
            for path in sorted(action_dir.glob("*.json"))
        ] if action_dir.exists() else []
        self.assertNotIn("deliver_mail", controller_action_types)

    def boot_to_controller(self, root: Path, startup_answers: dict | None = None) -> Path:
        startup_answers = startup_answers or STARTUP_ANSWERS
        while True:
            action = router.next_action(root)
            action_type = str(action["action_type"])
            if action_type == "open_startup_intake_ui":
                router.apply_action(root, action_type, self.startup_intake_payload(root, startup_answers=startup_answers))
            elif action_type == "record_startup_answers":
                router.apply_action(root, action_type, {"startup_answers": startup_answers})
            elif action_type == "record_user_request":
                if action.get("requires_payload") == "user_request":
                    router.apply_action(root, action_type, {"user_request": USER_REQUEST})
                else:
                    router.apply_action(root, action_type)
            elif action_type == "start_role_slots":
                router.apply_action(root, action_type, self.role_agent_payload(root, startup_answers))
            elif action_type == "create_heartbeat_automation":
                router.apply_action(root, action_type, self.heartbeat_binding_payload(root))
            elif action_type == "load_controller_core":
                router.apply_action(root, action_type, self.payload_for_action(action))
                self.complete_startup_async_controller_rows(root, startup_answers=startup_answers)
                break
            else:
                router.apply_action(root, action_type, self.payload_for_action(action))
        current = read_json(root / ".flowpilot" / "current.json")
        return root / current["current_run_root"]

    def legacy_controller_boundary_action(self, root: Path) -> tuple[Path, dict, dict]:
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
            elif action_type == "record_startup_answers":
                router.apply_action(root, action_type, {"startup_answers": startup_answers})
            elif action_type == "record_user_request":
                if action.get("requires_payload") == "user_request":
                    router.apply_action(root, action_type, {"user_request": USER_REQUEST})
                else:
                    router.apply_action(root, action_type)
            elif action_type == "start_role_slots":
                router.apply_action(root, action_type, self.role_agent_payload(root, startup_answers))
            elif action_type == "create_heartbeat_automation":
                router.apply_action(root, action_type, self.heartbeat_binding_payload(root))
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
            if action_type not in {"emit_startup_banner", "start_role_slots", "create_heartbeat_automation"}:
                continue
            action = entry.get("action") if isinstance(entry.get("action"), dict) else {}
            if action_type == "emit_startup_banner":
                payload = self.payload_for_action(action)
            elif action_type == "start_role_slots":
                payload = self.role_agent_payload(root, startup_answers)
            else:
                payload = self.heartbeat_binding_payload(root)
            router.record_controller_action_receipt(root, action_id=entry["action_id"], status="done", payload=payload)
            completed.append(str(action_type))
        return completed

    def force_startup_fact_role_wait(self, root: Path) -> dict:
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
            label="controller_waits_for_reviewer_startup_facts",
            summary="Controller waits for reviewer startup fact report through Router-directed runtime output.",
            to_role="human_like_reviewer",
            extra={
                "waiting_for_role": "human_like_reviewer",
                "allowed_external_events": ["reviewer_reports_startup_facts"],
                "expected_return_path": "startup/startup_fact_report.json",
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
        if status == "cancelled":
            receipt = {
                "schema_version": router.STARTUP_INTAKE_RECEIPT_SCHEMA,
                "status": "cancelled",
                "ui_surface": "native_wpf_startup_intake",
                "launch_mode": launch_mode,
                "headless": headless,
                "formal_startup_allowed": formal_startup_allowed,
                "language": "en",
                "startup_answers": startup_answers,
                "confirmed_by_user": False,
                "cancelled_by_user": True,
                "recorded_at": recorded_at,
            }
            receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            result = {
                "schema_version": router.STARTUP_INTAKE_RESULT_SCHEMA,
                "status": "cancelled",
                "launch_mode": launch_mode,
                "headless": headless,
                "formal_startup_allowed": formal_startup_allowed,
                "receipt_path": self.rel(root, receipt_path),
                "controller_visibility": "cancel_status_only",
                "body_text_included": False,
                "recorded_at": recorded_at,
            }
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

    def enter_legacy_startup_answer_boundary(self, root: Path) -> None:
        state_path = router.bootstrap_state_path(root)
        bootstrap = read_json(state_path)
        bootstrap["pending_action"] = {
            "action_type": "ask_startup_questions",
            "label": "legacy_startup_questions_asked_from_router",
        }
        state_path.write_text(json.dumps(bootstrap, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self.assertEqual(router.apply_action(root, "ask_startup_questions")["applied"], "ask_startup_questions")
        bootstrap = read_json(state_path)
        bootstrap["pending_action"] = {
            "action_type": "record_startup_answers",
            "label": "legacy_startup_answers_recorded_by_router",
            "requires_payload": "startup_answers",
        }
        state_path.write_text(json.dumps(bootstrap, indent=2, sort_keys=True) + "\n", encoding="utf-8")

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
            summary=f"Controller waits for worker_a test output: {label}",
            allowed_reads=[],
            allowed_writes=[],
            to_role="worker_a",
            extra={"allowed_external_events": [allowed_event], **(extra or {})},
        )
        entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)
        return entry

    def recover_worker_a_after_liveness_fault(self, root: Path) -> dict:
        router.record_external_event(
            root,
            "controller_reports_role_liveness_fault",
            {
                "role_key": "worker_a",
                "host_liveness_status": "missing",
                "detected_by": "controller",
            },
        )
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "load_role_recovery_state")
        router.apply_action(root, "load_role_recovery_state")
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "recover_role_agents")
        router.apply_action(root, "recover_role_agents", self.role_recovery_agent_payload(root, action, role="worker_a"))
        return read_json(self.run_root_for(root) / "continuation" / "role_recovery_report.json")

    def bootstrap_state(self, root: Path) -> dict:
        return read_json(router.bootstrap_state_path(root))

    def deliver_startup_fact_check_card(self, root: Path) -> dict:
        self.apply_startup_heartbeat_if_requested(root)
        self.complete_startup_pre_review_join(root)
        return self.deliver_expected_card(root, "reviewer.startup_fact_check")

    def deliver_startup_fact_check_card_without_ack(self, root: Path) -> dict:
        self.apply_startup_heartbeat_if_requested(root)
        self.complete_startup_pre_review_join(root)
        action = self.next_after_display_sync(root)
        while action["action_type"] in {
            "confirm_controller_core_boundary",
            "check_prompt_manifest",
            "write_startup_mechanical_audit",
            "write_display_surface_status",
        }:
            router.apply_action(root, str(action["action_type"]), self.payload_for_action(action))
            action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "deliver_system_card")
        self.assertEqual(action["card_id"], "reviewer.startup_fact_check")
        return action

    def complete_startup_pre_review_join(self, root: Path) -> None:
        self.deliver_expected_card(root, "pm.core")
        self.deliver_expected_card(root, "pm.output_contract_catalog")
        self.deliver_expected_card(root, "pm.role_work_request")
        self.deliver_expected_card(root, "pm.phase_map")
        self.deliver_expected_card(root, "pm.startup_intake")

    def deliver_initial_pm_cards_and_user_intake(self, root: Path) -> None:
        self.complete_startup_pre_review_join(root)
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
        self.write_self_interrogation_record(
            root,
            "startup",
            source_path=run_root / "test_role_outputs" / "startup" / "pm_startup_activation.json",
        )
        self.assertTrue((run_root / "display" / "display_surface.json").exists())

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
                    "reviewed_by_role": "human_like_reviewer",
                    "direct_material_sources_checked": True,
                    "packet_matches_checked_sources": True,
                    "pm_ready": True,
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

        self.deliver_expected_card(root, "product_officer.product_architecture_modelability")
        router.record_external_event(
            root,
            "product_officer_submits_product_behavior_model",
            self.role_report_envelope(
                root,
                "flowguard/product_behavior_model",
                {"reviewed_by_role": "product_flowguard_officer", "passed": True},
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
        if completed_by_role == "worker_a":
            completed_by_agent_id, result_path = self.submit_current_node_result_via_active_holder(
                root,
                packet_id=packet_id,
                result_body_text="reviewable result",
            )
        else:
            packet_runtime.read_packet_body_for_role(root, read_json(root / packet_path), role="worker_a")
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
            self.assertNotEqual(pending.get("action_type"), "check_prompt_manifest")
            if pending.get("action_type") == "deliver_system_card":
                self.assertEqual(pending["card_id"], "pm.event.reviewer_blocked")

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

    def test_pm_role_work_existing_result_reconciles_before_wait(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-role-work-reconcile")
        run_root = self.run_root_for(root)
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        self.deliver_expected_card(root, "pm.model_miss_triage")
        router.record_external_event(
            root,
            "pm_records_model_miss_triage_decision",
            self.role_decision_envelope(
                root,
                "decisions/model_miss_role_work_reconcile",
                self.model_miss_triage_body(root, decision="request_officer_model_miss_analysis"),
            ),
        )
        self.deliver_expected_card(root, "pm.event.reviewer_blocked")

        router.record_external_event(root, "pm_registers_role_work_request", self.pm_role_work_request_payload(root))
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_pm_role_work_request_packet")
        router.apply_action(root, "relay_pm_role_work_request_packet")
        index_after_relay = read_json(run_root / "pm_work_requests" / "index.json")
        packet_id = index_after_relay["requests"][0]["packet_id"]
        lease = self.active_holder_lease_for_packet(root, packet_id)
        self.assertEqual(lease["holder_role"], "product_flowguard_officer")

        self.open_role_work_packet_and_write_result(root)
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_pm_role_work_result_to_pm")

        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["pm_role_work_result_returned"])
        self.assertTrue(
            any(
                item.get("event") == "role_work_result_returned"
                and item.get("reconciled_by_router") is True
                for item in state["events"]
                if isinstance(item, dict)
            )
        )
        index = read_json(run_root / "pm_work_requests" / "index.json")
        self.assertEqual(index["requests"][0]["status"], "result_returned")

    def test_advisory_pm_role_work_wait_is_marked_nonblocking(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-role-work-advisory")
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        self.deliver_expected_card(root, "pm.model_miss_triage")
        router.record_external_event(
            root,
            "pm_records_model_miss_triage_decision",
            self.role_decision_envelope(
                root,
                "decisions/model_miss_role_work_advisory",
                self.model_miss_triage_body(root, decision="request_officer_model_miss_analysis"),
            ),
        )
        self.deliver_expected_card(root, "pm.event.reviewer_blocked")

        router.record_external_event(
            root,
            "pm_registers_role_work_request",
            self.pm_role_work_request_payload(
                root,
                request_id="model-miss-advisory-001",
                request_mode="advisory",
            ),
        )
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_pm_role_work_request_packet")
        router.apply_action(root, "relay_pm_role_work_request_packet")

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertEqual(action["allowed_external_events"], ["role_work_result_returned"])
        self.assertTrue(action["nonblocking_wait"])
        self.assertEqual(action["dependency_class"], "advisory")

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
        self.assertEqual(result["action_type"], "open_startup_intake_ui")
        self.assertEqual(result["folded_command"], "run-until-wait")
        self.assertEqual(result["folded_applied_count"], 5)
        self.assertEqual(
            [item["action_type"] for item in result["folded_applied_actions"]],
            ["load_router", "create_run_shell", "write_current_pointer", "update_run_index", "start_router_daemon"],
        )
        self.assertTrue(result["startup_daemon_scheduled"])
        self.assertTrue(result["scheduled_by_router_daemon"])
        self.assertEqual(result["scope_kind"], "startup")
        self.assertEqual(result["controller_table_contract"], "simple_work_board")
        self.assertTrue(result["controller_action_id"])
        self.assertTrue(result["router_scheduler_row_id"])
        self.assertEqual(result["folded_stop_reason"], "requires_user_host_or_role_boundary")
        run_state = read_json(router.run_state_path(self.run_root_for(root)))
        self.assertTrue(run_state["flags"]["formal_router_daemon_started"])
        self.assertFalse(run_state["flags"]["controller_core_loaded"])

    def test_run_until_wait_folds_only_internal_bootloader_actions_after_banner(self) -> None:
        root = self.make_project()
        router.run_until_wait(root, new_invocation=True)
        router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))

        result = router.run_until_wait(root)

        self.assertEqual(result["action_type"], "load_controller_core")
        self.assertEqual(result["folded_command"], "run-until-wait")
        self.assertEqual([item["action_type"] for item in result["folded_applied_actions"]], [])
        self.assertEqual(result["folded_stop_reason"], "requires_user_host_or_role_boundary")
        bootstrap = self.bootstrap_state(root)
        self.assertTrue(bootstrap["flags"]["run_shell_created"])
        self.assertTrue(bootstrap["flags"]["router_daemon_started"])
        self.assertTrue(bootstrap["flags"]["mailbox_initialized"])
        self.assertTrue(bootstrap["flags"].get("user_request_recorded", False))
        self.assertTrue(bootstrap["flags"].get("deterministic_bootstrap_seed_completed", False))
        self.assertFalse(bootstrap["flags"].get("banner_emitted", False))
        self.assertFalse(bootstrap["flags"].get("roles_started", False))
        self.assertTrue((root / ".flowpilot" / "current.json").exists())
        run_root = self.run_root_for(root)
        self.assertTrue((run_root / "packet_ledger.json").exists())
        self.assertTrue((run_root / "bootstrap" / "deterministic_bootstrap_seed_evidence.json").exists())
        controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        startup_types = [item.get("action_type") for item in controller_ledger["actions"] if item.get("scope_kind") == "startup"]
        self.assertIn("load_controller_core", startup_types)
        self.assertNotIn("emit_startup_banner", startup_types)
        self.assertNotIn("start_role_slots", startup_types)
        self.assertNotIn("fill_runtime_placeholders", startup_types)
        self.assertNotIn("initialize_mailbox", startup_types)
        self.assertNotIn("record_user_request", startup_types)
        self.assertNotIn("write_user_intake", startup_types)

    def test_run_until_wait_folds_user_intake_then_stops_before_role_boundary(self) -> None:
        root = self.make_project()
        router.run_until_wait(root, new_invocation=True)
        router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))

        result = router.run_until_wait(root)

        self.assertEqual(result["action_type"], "load_controller_core")
        self.assertEqual([item["action_type"] for item in result["folded_applied_actions"]], [])
        self.assertEqual(result["folded_stop_reason"], "requires_user_host_or_role_boundary")
        self.assertTrue((self.run_root_for(root) / "mailbox" / "outbox" / "user_intake.json").exists())
        self.assertTrue(
            (self.run_root_for(root) / "bootstrap" / "deterministic_bootstrap_seed_evidence.json").exists()
        )
        self.assertFalse(self.bootstrap_state(root)["flags"].get("roles_started", False))

    def test_scheduled_startup_heartbeat_is_queued_after_controller_core(self) -> None:
        root = self.make_project()
        router.run_until_wait(root, new_invocation=True)
        router.apply_action(
            root,
            "open_startup_intake_ui",
            self.startup_intake_payload(root, startup_answers=HEARTBEAT_STARTUP_ANSWERS),
        )
        action = router.run_until_wait(root)
        self.assertEqual(action["action_type"], "load_controller_core")

        run_root = self.run_root_for(root)
        run_state = read_json(router.run_state_path(run_root))
        self.assertFalse(run_state["flags"]["controller_core_loaded"])
        self.assertFalse(run_state["flags"]["continuation_binding_recorded"])
        controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        self.assertFalse(any(item.get("action_type") == "create_heartbeat_automation" for item in controller_ledger["actions"]))
        router.apply_action(root, "load_controller_core", self.payload_for_action(action))
        run_state = read_json(router.run_state_path(run_root))
        self.assertTrue(run_state["flags"]["controller_core_loaded"])
        self.assertFalse(run_state["flags"]["continuation_binding_recorded"])
        controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        heartbeat_row = next(item for item in controller_ledger["actions"] if item.get("action_type") == "create_heartbeat_automation")
        heartbeat_action = read_json(run_root / "runtime" / "controller_actions" / f"{heartbeat_row['action_id']}.json")["action"]
        self.assertEqual(heartbeat_action["actor"], "bootloader")
        self.assertEqual(heartbeat_action["postcondition"], "continuation_binding_recorded")
        self.assertTrue(heartbeat_action["requires_host_automation"])
        self.assertEqual(heartbeat_action["router_scheduler_progress_class"], "parallel_obligation")
        self.assertEqual(heartbeat_action["automation_update_request"]["kind"], "heartbeat")
        self.assertNotIn("otherwise keep the run alive", heartbeat_action["automation_update_request"]["prompt"])
        self.assertIn("Every heartbeat wake must record heartbeat_or_manual_resume_requested", heartbeat_action["automation_update_request"]["prompt"])
        self.assertIn("Router consumes local prompt-manifest checks internally", heartbeat_action["automation_update_request"]["prompt"])
        self.assertIn("stop only at a real role, user, host, payload, packet, or await_role_decision boundary", heartbeat_action["automation_update_request"]["prompt"])
        self.assertEqual(heartbeat_action["automation_update_request"]["rrule"], "FREQ=MINUTELY;INTERVAL=1")
        self.assertEqual(heartbeat_action["expected_payload"]["route_heartbeat_interval_minutes"], 1)
        self.assert_controller_receipt_action_projection(heartbeat_action)
        self.assertTrue(heartbeat_action["proof_required_before_controller_receipt"])
        self.assertFalse(heartbeat_action.get("proof_required_before_apply", False))
        self.assertEqual(heartbeat_action["payload_contract"]["allowed_values"]["route_heartbeat_interval_minutes"], [1])
        self.assertEqual(heartbeat_action["payload_contract"]["allowed_values"]["host_automation_verified"], [True])
        self.assertEqual(heartbeat_action["payload_contract"]["allowed_values"]["host_automation_proof.heartbeat_bound_to_current_run"], [True])

        self.complete_startup_async_controller_rows(root, startup_answers=HEARTBEAT_STARTUP_ANSWERS)
        self.assertTrue(action["startup_daemon_scheduled"])
        self.assertTrue(action["scheduled_by_router_daemon"])
        run_state = read_json(router.run_state_path(run_root))
        self.assertTrue(run_state["flags"]["controller_core_loaded"])
        self.assertTrue(run_state["flags"]["formal_router_daemon_started"])
        continuation = read_json(run_root / "continuation" / "continuation_binding.json")
        self.assertEqual(continuation["mode"], "scheduled_heartbeat")
        self.assertTrue(continuation["heartbeat_active"])

    def test_manual_startup_skips_heartbeat_after_controller_core(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root, startup_answers=STARTUP_ANSWERS)
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["formal_router_daemon_started"])
        self.assertTrue(state["flags"]["controller_core_loaded"])
        continuation = read_json(run_root / "continuation" / "continuation_binding.json")
        self.assertEqual(continuation["mode"], "manual_resume")
        self.assertFalse(continuation["heartbeat_active"])
        self.assertFalse(continuation["host_automation_verified"])

    def test_formal_startup_starts_router_daemon_before_controller_core(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_router_daemon_start(root)

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "start_router_daemon")
        self.assertTrue(action["startup_readiness_contract"]["failure_blocks_controller_core"])
        result = router.apply_action(root, "start_router_daemon")
        self.assertTrue(result["router_daemon_ready"])
        self.assertFalse(result["attached_existing_daemon"])

        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["daemon_mode_enabled"])
        self.assertTrue(state["flags"]["formal_router_daemon_started"])
        self.assertEqual(read_json(run_root / "runtime" / "router_daemon.lock")["status"], "active")
        self.assertEqual(read_json(run_root / "runtime" / "router_daemon_status.json")["tick_interval_seconds"], 1)
        self.assertEqual(
            read_json(run_root / "runtime" / "controller_action_ledger.json")["schema_version"],
            router.CONTROLLER_ACTION_LEDGER_SCHEMA,
        )

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "open_startup_intake_ui")
        self.assertTrue(action["startup_daemon_scheduled"])
        self.assertTrue(action["scheduled_by_router_daemon"])
        entry = read_json(run_root / "runtime" / "controller_actions" / f"{action['controller_action_id']}.json")
        self.assertEqual(entry["action_type"], "open_startup_intake_ui")
        self.assertEqual(entry["scope_kind"], "startup")
        self.assertIn("Router daemon status", entry["action"]["plain_instruction"])
        self.assertIn("Controller action ledger", entry["action"]["plain_instruction"])
        self.assertNotIn("apply this pending action", entry["action"]["plain_instruction"])
        self.assertNotIn("apply its confirmed or cancelled result", entry["action"]["summary"])
        scheduler = read_json(run_root / "runtime" / "router_scheduler_ledger.json")
        row = next(item for item in scheduler["rows"] if item["row_id"] == action["router_scheduler_row_id"])
        self.assertEqual(row["scope_kind"], "startup")
        self.assertEqual(row["barrier_kind"], "external_barrier")
        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"]["controller_core_loaded"])

    def test_startup_daemon_defers_banner_and_queues_next_boot_row(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_router_daemon_start(root)
        router.apply_action(root, "start_router_daemon")

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "open_startup_intake_ui")
        router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "load_controller_core")
        bootstrap = self.bootstrap_state(root)
        self.assertEqual(bootstrap["pending_action"]["action_type"], "load_controller_core")
        self.assertTrue(bootstrap["flags"]["deterministic_bootstrap_seed_completed"])
        self.assertTrue((run_root / "bootstrap" / "deterministic_bootstrap_seed_evidence.json").exists())

        controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        banner_rows = [item for item in controller_ledger["actions"] if item.get("action_type") == "emit_startup_banner"]
        self.assertEqual(len(banner_rows), 0)
        startup_types = [item.get("action_type") for item in controller_ledger["actions"] if item.get("scope_kind") == "startup"]
        self.assertNotIn("emit_startup_banner", startup_types)
        self.assertNotIn("start_role_slots", startup_types)
        self.assertNotIn("create_heartbeat_automation", startup_types)
        self.assertNotIn("fill_runtime_placeholders", startup_types)
        self.assertNotIn("initialize_mailbox", startup_types)
        self.assertNotIn("record_user_request", startup_types)
        self.assertNotIn("write_user_intake", startup_types)
        self.assertFalse(bootstrap["flags"].get("banner_emitted", False))

        router.apply_action(root, "load_controller_core")
        controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        banner_rows = [item for item in controller_ledger["actions"] if item.get("action_type") == "emit_startup_banner"]
        self.assertEqual(len(banner_rows), 1)
        banner_record = read_json(run_root / "runtime" / "controller_actions" / f"{banner_rows[0]['action_id']}.json")
        self.assertEqual(banner_record["status"], "pending")
        self.assertEqual(banner_record["action"]["router_scheduler_progress_class"], "parallel_obligation")

    def test_deterministic_bootstrap_seed_failure_does_not_create_pm_blocker(self) -> None:
        root = self.make_project()
        self.boot_to_router_daemon_start(root)
        router.apply_action(root, "start_router_daemon")

        with mock.patch.object(
            router,
            "_initialize_mailbox_foundation",
            side_effect=router.RouterError("seed mailbox failed"),
        ):
            with self.assertRaisesRegex(router.RouterError, "seed mailbox failed"):
                router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))

        run_root = self.run_root_for(root)
        control_blocks = run_root / "control_blocks"
        self.assertFalse(control_blocks.exists() and list(control_blocks.glob("*.json")))

    def test_deterministic_bootstrap_seed_replay_uses_existing_evidence(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_router_daemon_start(root)
        router.apply_action(root, "start_router_daemon")
        router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))

        return_ledger_path = run_root / "return_event_ledger.json"
        return_ledger = read_json(return_ledger_path)
        return_ledger["pending_returns"].append({"return_id": "existing-return", "source": "test"})
        router.write_json(return_ledger_path, return_ledger)

        proof = router._run_deterministic_startup_bootstrap_seed(root, self.bootstrap_state(root))  # type: ignore[attr-defined]

        self.assertTrue(proof["completed"])
        refreshed_return_ledger = read_json(return_ledger_path)
        self.assertEqual(
            [item["return_id"] for item in refreshed_return_ledger["pending_returns"]],
            ["existing-return"],
        )

    def test_reconciled_scheduler_row_receipt_replay_does_not_create_pm_blocker(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_router_daemon_start(root)
        router.apply_action(root, "start_router_daemon")
        router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "load_controller_core")
        router.apply_action(root, "load_controller_core")

        controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        load_core_row = next(item for item in controller_ledger["actions"] if item.get("action_type") == "load_controller_core")
        action_path = run_root / "runtime" / "controller_actions" / f"{load_core_row['action_id']}.json"
        entry = read_json(action_path)
        self.assert_controller_receipt_entry_projection(entry)
        entry.pop("router_reconciliation_status", None)
        entry.pop("router_reconciled_at", None)
        entry.pop("router_reconciliation", None)
        router.write_json(action_path, entry)

        run_state = read_json(router.run_state_path(run_root))
        result = router._reconcile_scheduled_controller_action_receipts(root, run_root, run_state)  # type: ignore[attr-defined]

        self.assertTrue(result["changed"])
        self.assertEqual(result["blocked"], 0)
        refreshed = read_json(action_path)
        self.assertEqual(refreshed["router_reconciliation_status"], "reconciled")
        control_blocks = run_root / "control_blocks"
        self.assertFalse(control_blocks.exists() and list(control_blocks.glob("*.json")))

    def test_startup_daemon_bootloader_completion_uses_receipt_owner(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_router_daemon_start(root)
        router.apply_action(root, "start_router_daemon")
        router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))

        controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        intake_row = next(item for item in controller_ledger["actions"] if item.get("action_type") == "open_startup_intake_ui")
        action_path = run_root / "runtime" / "controller_actions" / f"{intake_row['action_id']}.json"
        entry = read_json(action_path)
        reconciliation = entry["router_reconciliation"]

        self.assertEqual(entry["router_reconciliation_status"], "reconciled")
        self.assertEqual(reconciliation["source"], "startup_bootloader_controller_receipt")
        self.assertNotEqual(reconciliation["source"], "startup_daemon_bootloader_postcondition")
        scheduler = read_json(run_root / "runtime" / "router_scheduler_ledger.json")
        scheduler_row = next(item for item in scheduler["rows"] if item.get("row_id") == intake_row["router_scheduler_row_id"])
        self.assertEqual(scheduler_row["router_state"], "reconciled")
        self.assertEqual(scheduler_row["reconciliation"]["source"], "startup_bootloader_controller_receipt")

    def test_legacy_startup_daemon_postcondition_owner_canonicalizes_to_receipt_owner(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_router_daemon_start(root)
        router.apply_action(root, "start_router_daemon")
        router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))

        controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        intake_row = next(item for item in controller_ledger["actions"] if item.get("action_type") == "open_startup_intake_ui")
        action_path = run_root / "runtime" / "controller_actions" / f"{intake_row['action_id']}.json"
        entry = read_json(action_path)
        entry["router_reconciliation"]["source"] = "startup_daemon_bootloader_postcondition"
        entry["router_pending_apply_required"] = True
        entry["action"]["router_pending_apply_required"] = True
        router.write_json(action_path, entry)
        scheduler_path = run_root / "runtime" / "router_scheduler_ledger.json"
        scheduler = read_json(scheduler_path)
        scheduler_row = next(item for item in scheduler["rows"] if item.get("row_id") == intake_row["router_scheduler_row_id"])
        scheduler_row["reconciliation"]["source"] = "startup_daemon_bootloader_postcondition"
        router.write_json(scheduler_path, scheduler)

        state = read_json(router.run_state_path(run_root))
        result = router._reconcile_scheduled_controller_action_receipts(root, run_root, state)  # type: ignore[attr-defined]

        self.assertTrue(result["changed"])
        refreshed = read_json(action_path)
        self.assertEqual(refreshed["router_reconciliation"]["source"], "startup_bootloader_controller_receipt")
        self.assertEqual(
            refreshed["router_reconciliation"]["canonicalized_from"],
            "startup_daemon_bootloader_postcondition",
        )
        self.assertFalse(refreshed["router_pending_apply_required"])
        scheduler = read_json(scheduler_path)
        scheduler_row = next(item for item in scheduler["rows"] if item.get("row_id") == intake_row["router_scheduler_row_id"])
        self.assertEqual(scheduler_row["reconciliation"]["source"], "startup_bootloader_controller_receipt")

    def test_load_controller_core_receipt_reconciles_startup_postcondition(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_router_daemon_start(root)
        router.apply_action(root, "start_router_daemon")
        router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "load_controller_core")

        state = read_json(router.run_state_path(run_root))
        router._write_controller_receipt(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            action_id=action["controller_action_id"],
            status="done",
            payload={"controller_action_completed": True},
        )
        state = read_json(router.run_state_path(run_root))
        result = router._reconcile_scheduled_controller_action_receipts(root, run_root, state)  # type: ignore[attr-defined]

        self.assertTrue(result["changed"])
        self.assertEqual(result["blocked"], 0)
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["controller_core_loaded"])
        self.assertEqual(state["status"], "controller_ready")
        self.assertFalse(state.get("active_control_blocker"))

    def test_startup_reconciliation_resolves_stale_blocker_and_supersedes_pm_row(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_router_daemon_start(root)
        router.apply_action(root, "start_router_daemon")
        router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "load_controller_core")

        state = read_json(router.run_state_path(run_root))
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="controller_action_receipt_missing_router_postcondition",
            error_message=(
                "Controller action load_controller_core was marked done, but Router could not "
                "apply its required postcondition before reconciliation."
            ),
            action_type="load_controller_core",
            payload={
                "controller_action_id": action["controller_action_id"],
                "router_scheduler_row_id": action["router_scheduler_row_id"],
                "postcondition": "controller_core_loaded",
                "direct_retry_attempts_used": 2,
                "direct_retry_budget": 2,
            },
        )
        self.assertEqual(blocker["policy_row_id"], "mechanical_control_plane_reissue")
        self.assertTrue(blocker["direct_retry_budget_exhausted"])
        state = read_json(router.run_state_path(run_root))
        stale_pm_action = router._next_control_blocker_action(root, state, run_root)  # type: ignore[attr-defined]
        self.assertIsNotNone(stale_pm_action)
        self.assertEqual(stale_pm_action["action_type"], "handle_control_blocker")
        self.assertEqual(stale_pm_action["to_role"], "project_manager")
        stale_pm_action = router._prepare_router_scheduled_action(root, run_root, state, stale_pm_action)  # type: ignore[attr-defined]
        stale_pm_entry = router._write_controller_action_entry(root, run_root, state, stale_pm_action)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)

        router.apply_action(root, "load_controller_core")

        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state.get("active_control_blocker"))
        blocker_record = read_json(self.control_blocker_path(root, blocker))
        self.assertEqual(blocker_record["resolution_status"], "resolved_by_startup_reconciliation")
        self.assertEqual(blocker_record["resolved_by_controller_action_id"], action["controller_action_id"])
        stale_pm_entry = read_json(router._controller_action_path(run_root, stale_pm_entry["action_id"]))  # type: ignore[attr-defined]
        self.assertEqual(stale_pm_entry["status"], "superseded")
        self.assertEqual(
            stale_pm_entry["router_reconciliation_status"],
            "superseded_by_resolved_control_blocker",
        )
        self.assertNotEqual((self.bootstrap_state(root).get("pending_action") or {}).get("action_type"), "handle_control_blocker")

    def test_startup_missing_router_postcondition_retries_before_pm_blocker(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_router_daemon_start(root)
        router.apply_action(root, "start_router_daemon")
        router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "load_controller_core")

        status_path = run_root / "runtime" / "router_daemon_status.json"
        status = read_json(status_path)
        status["daemon_mode_enabled"] = False
        router.write_json(status_path, status)

        state = read_json(router.run_state_path(run_root))
        router._write_controller_receipt(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            action_id=action["controller_action_id"],
            status="done",
            payload={"controller_action_completed": True},
        )

        for expected_attempt in (1, 2):
            state = read_json(router.run_state_path(run_root))
            result = router._reconcile_scheduled_controller_action_receipts(root, run_root, state)  # type: ignore[attr-defined]
            self.assertTrue(result["changed"])
            self.assertEqual(result["blocked"], 0)
            state = read_json(router.run_state_path(run_root))
            entry = read_json(router._controller_action_path(run_root, action["controller_action_id"]))  # type: ignore[attr-defined]
            self.assertEqual(entry["router_reconciliation_status"], "retry_pending")
            self.assertEqual(entry["postcondition_reconciliation_attempts"], expected_attempt)
            self.assertEqual(entry["max_postcondition_reconciliation_attempts"], 2)
            self.assertFalse(entry["postcondition_reconciliation_exhausted"])
            self.assertFalse(state.get("active_control_blocker"))

        state = read_json(router.run_state_path(run_root))
        result = router._reconcile_scheduled_controller_action_receipts(root, run_root, state)  # type: ignore[attr-defined]
        self.assertTrue(result["changed"])
        self.assertEqual(result["blocked"], 1)
        state = read_json(router.run_state_path(run_root))
        blocker = state["active_control_blocker"]
        self.assertEqual(blocker["handling_lane"], "pm_repair_decision_required")
        self.assertEqual(blocker["policy_row_id"], "mechanical_control_plane_reissue")
        self.assertEqual(blocker["target_role"], "project_manager")
        self.assertEqual(blocker["direct_retry_budget"], 2)
        self.assertEqual(blocker["direct_retry_attempts_used"], 2)
        self.assertTrue(blocker["direct_retry_budget_exhausted"])

    def test_startup_daemon_queues_role_heartbeat_and_controller_core_without_role_wait(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_router_daemon_start(root, startup_answers=HEARTBEAT_STARTUP_ANSWERS)
        router.apply_action(root, "start_router_daemon")
        router.apply_action(
            root,
            "open_startup_intake_ui",
            self.startup_intake_payload(root, startup_answers=HEARTBEAT_STARTUP_ANSWERS),
        )

        while True:
            action = router.next_action(root)
            action_type = str(action["action_type"])
            if action_type == "load_controller_core":
                break
            self.assertNotIn(action_type, {"emit_startup_banner", "start_role_slots", "create_heartbeat_automation"})
            if action_type == "record_user_request":
                router.apply_action(root, action_type)
            else:
                router.apply_action(root, action_type, self.payload_for_action(action))

        controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        startup_types = [item.get("action_type") for item in controller_ledger["actions"] if item.get("scope_kind") == "startup"]
        self.assertEqual(startup_types.count("emit_startup_banner"), 0)
        self.assertEqual(startup_types.count("start_role_slots"), 0)
        self.assertEqual(startup_types.count("create_heartbeat_automation"), 0)
        self.assertNotIn("inject_role_core_prompts", startup_types)
        self.assertEqual(self.bootstrap_state(root)["pending_action"]["action_type"], "load_controller_core")

        router.apply_action(root, "load_controller_core", self.payload_for_action(action))
        controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        startup_types = [item.get("action_type") for item in controller_ledger["actions"] if item.get("scope_kind") == "startup"]
        self.assertEqual(startup_types.count("emit_startup_banner"), 1)
        self.assertEqual(startup_types.count("start_role_slots"), 1)
        self.assertEqual(startup_types.count("create_heartbeat_automation"), 1)
        state = read_json(router.run_state_path(run_root))
        blockers = router._startup_pre_review_reconciliation_blockers(root, run_root, state)  # type: ignore[attr-defined]
        blocker_kinds = [item["kind"] for item in blockers]
        self.assertIn("pending_startup_controller_row", blocker_kinds)
        self.assertIn("missing_startup_flag", blocker_kinds)

    def test_startup_async_receipts_update_bootstrap_flags_and_scheduler_rows(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_router_daemon_start(root, startup_answers=HEARTBEAT_STARTUP_ANSWERS)
        router.apply_action(root, "start_router_daemon")
        router.apply_action(
            root,
            "open_startup_intake_ui",
            self.startup_intake_payload(root, startup_answers=HEARTBEAT_STARTUP_ANSWERS),
        )
        while True:
            action = router.next_action(root)
            if action["action_type"] == "load_controller_core":
                break
            payload = {} if action["action_type"] == "record_user_request" else self.payload_for_action(action)
            router.apply_action(root, str(action["action_type"]), payload)

        router.apply_action(root, "load_controller_core", self.payload_for_action(action))
        completed = self.complete_startup_async_controller_rows(root, startup_answers=HEARTBEAT_STARTUP_ANSWERS)
        self.assertEqual(set(completed), {"emit_startup_banner", "start_role_slots", "create_heartbeat_automation"})

        bootstrap = self.bootstrap_state(root)
        self.assertTrue(bootstrap["flags"]["banner_emitted"])
        self.assertTrue(bootstrap["flags"]["roles_started"])
        self.assertTrue(bootstrap["flags"]["role_core_prompts_injected"])
        self.assertTrue(bootstrap["flags"]["continuation_binding_recorded"])
        scheduler = read_json(run_root / "runtime" / "router_scheduler_ledger.json")
        async_rows = [
            item
            for item in scheduler["rows"]
            if item.get("action_type") in {"emit_startup_banner", "start_role_slots", "create_heartbeat_automation"}
        ]
        self.assertEqual(len(async_rows), 3)
        self.assertTrue(all(item["router_state"] == "reconciled" for item in async_rows))

    def test_formal_startup_daemon_failure_blocks_controller_core(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_router_daemon_start(root)

        with mock.patch.object(router, "_spawn_startup_router_daemon_process", side_effect=router.RouterError("daemon launch failed")):
            with self.assertRaisesRegex(router.RouterError, "daemon launch failed"):
                router.apply_action(root, "start_router_daemon")

        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"]["controller_core_loaded"])
        self.assertTrue(state["flags"]["router_daemon_start_failed"])
        self.assertEqual(router.next_action(root)["action_type"], "start_router_daemon")

    def test_formal_startup_attaches_same_run_live_daemon_without_duplicate_spawn(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_router_daemon_start(root)
        router.run_router_daemon(root, max_ticks=1, observe_only=True, release_lock_on_exit=False)

        with mock.patch.object(
            router,
            "_spawn_startup_router_daemon_process",
            side_effect=AssertionError("startup should attach to the existing daemon"),
        ):
            result = router.apply_action(root, "start_router_daemon")

        self.assertTrue(result["router_daemon_ready"])
        self.assertTrue(result["attached_existing_daemon"])
        self.assertEqual(read_json(run_root / "runtime" / "router_daemon.lock")["status"], "active")

    def test_run_until_wait_reaches_card_boundary_after_router_internal_manifest_check(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root, startup_answers=HEARTBEAT_STARTUP_ANSWERS)
        while True:
            action = self.next_after_display_sync(root)
            if action["action_type"] in {"deliver_system_card", "deliver_system_card_bundle"}:
                break
            if action["action_type"] == "create_heartbeat_automation":
                router.apply_action(root, "create_heartbeat_automation", self.heartbeat_binding_payload(root))
                continue
            if action["action_type"] in {
                "confirm_controller_core_boundary",
                "write_startup_mechanical_audit",
                "write_display_surface_status",
            }:
                router.apply_action(root, str(action["action_type"]), self.payload_for_action(action))
                continue
            self.fail(f"unexpected action before card boundary: {action['action_type']}")

        self.assertIn("check_prompt_manifest", self.router_internal_action_types(root))

        state = read_json(router.run_state_path(run_root))
        self.assertIn(state["pending_action"]["action_type"], {"deliver_system_card", "deliver_system_card_bundle"})

        result = router.run_until_wait(root)

        self.assertIn(result["action_type"], {"deliver_system_card", "deliver_system_card_bundle"})
        self.assertEqual(result["folded_applied_actions"], [])
        self.assertEqual(result["folded_stop_reason"], "requires_user_host_or_role_boundary")

    def test_router_daemon_observation_initializes_lock_status_and_ledger(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)

        result = router.run_router_daemon(root, max_ticks=1, observe_only=True, release_lock_on_exit=False)

        self.assertTrue(result["ok"])
        self.assertEqual(result["tick_interval_seconds"], 1)
        lock = read_json(run_root / "runtime" / "router_daemon.lock")
        status = read_json(run_root / "runtime" / "router_daemon_status.json")
        ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        self.assertEqual(lock["schema_version"], router.ROUTER_DAEMON_LOCK_SCHEMA)
        self.assertEqual(lock["status"], "active")
        self.assertEqual(status["schema_version"], router.ROUTER_DAEMON_STATUS_SCHEMA)
        self.assertTrue(status["daemon_mode_enabled"])
        self.assertEqual(status["tick_interval_seconds"], 1)
        self.assertNotIn("router_ownership_ledger", status)
        self.assertFalse(status["router_internal_ownership_ledger_visible_to_controller"])
        self.assertTrue((run_root / "runtime" / "router_ownership_ledger.json").exists())
        self.assertEqual(ledger["schema_version"], router.CONTROLLER_ACTION_LEDGER_SCHEMA)
        self.assertLess(list(ledger).index("controller_table_prompt"), list(ledger).index("actions"))
        prompt = ledger["controller_table_prompt"]
        self.assertEqual(prompt["language"], "en")
        self.assertEqual(prompt["row_processing_order"], "top_to_bottom")
        self.assertTrue(prompt["foreground_controller_must_remain_attached_while_flowpilot_running"])
        self.assertFalse(prompt["sealed_body_reads_allowed"])
        self.assertIn("Work from top to bottom", prompt["text"])
        self.assertIn("As long as FlowPilot is still running", prompt["text"])
        self.assertIn("continuous monitoring duty, not a finishable checklist item", prompt["text"])
        self.assertIn("return to top-to-bottom row processing", prompt["text"])

        with self.assertRaisesRegex(router.RouterError, "already active"):
            router.run_router_daemon(root, max_ticks=1, observe_only=True)
        stopped = router.stop_router_daemon(root, reason="test_cleanup")
        self.assertEqual(stopped["lock_status"], "released")

    def test_router_daemon_tick_stays_bound_when_current_focus_changes(self) -> None:
        root = self.make_project()
        run_a = self.write_minimal_run(root, "run-a")
        run_b = self.write_minimal_run(root, "run-b")
        self.write_current_focus(root, run_a)
        state_a = read_json(router.run_state_path(run_a))
        router._acquire_router_daemon_lock(root, run_a, state_a)  # type: ignore[attr-defined]

        self.write_current_focus(root, run_b)
        tick = router._router_daemon_tick(root, run_a, state_a, observe_only=True)  # type: ignore[attr-defined]

        self.assertEqual(tick["observe_only"], True)
        self.assertEqual(read_json(router.run_state_path(run_a))["run_id"], "run-a")
        self.assertEqual(read_json(router.run_state_path(run_b))["run_id"], "run-b")
        status_a = read_json(run_a / "runtime" / "router_daemon_status.json")
        self.assertEqual(status_a["run_id"], "run-a")
        self.assertEqual(status_a["run_root"], ".flowpilot/runs/run-a")
        self.assertFalse((run_b / "runtime" / "controller_action_ledger.json").exists())

    def test_router_daemon_stop_targets_one_parallel_run(self) -> None:
        root = self.make_project()
        run_a = self.write_minimal_run(root, "run-a")
        run_b = self.write_minimal_run(root, "run-b")
        self.write_current_focus(root, run_b)
        state_a = read_json(router.run_state_path(run_a))
        state_b = read_json(router.run_state_path(run_b))
        router._acquire_router_daemon_lock(root, run_a, state_a)  # type: ignore[attr-defined]
        router._acquire_router_daemon_lock(root, run_b, state_b)  # type: ignore[attr-defined]

        stopped = router.stop_router_daemon(root, reason="test_stop_a", run_root=run_a)

        self.assertEqual(stopped["run_id"], "run-a")
        self.assertEqual(read_json(run_a / "runtime" / "router_daemon.lock")["status"], "released")
        self.assertEqual(read_json(run_b / "runtime" / "router_daemon.lock")["status"], "active")
        self.assertFalse(read_json(router.run_state_path(run_a))["daemon_mode_enabled"])
        self.assertTrue(read_json(router.run_state_path(run_b))["daemon_mode_enabled"])

    def test_router_daemon_refresh_does_not_reactivate_released_lock(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-a")
        state = read_json(router.run_state_path(run_root))
        router._acquire_router_daemon_lock(root, run_root, state)  # type: ignore[attr-defined]
        router._release_router_daemon_lock(root, run_root, reason="test_release", status="released")  # type: ignore[attr-defined]

        refreshed = router._refresh_router_daemon_lock(root, run_root)  # type: ignore[attr-defined]

        self.assertEqual(refreshed["status"], "released")
        self.assertEqual(read_json(run_root / "runtime" / "router_daemon.lock")["status"], "released")

    def test_controller_action_summary_separates_done_history_from_active_work(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-a")
        ledger_path = run_root / "runtime" / "controller_action_ledger.json"
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        router.write_json(
            ledger_path,
            {
                "schema_version": router.CONTROLLER_ACTION_LEDGER_SCHEMA,
                "run_id": "run-a",
                "run_root": ".flowpilot/runs/run-a",
                "updated_at": router.utc_now(),
                "actions": [{"action_id": "action-1", "action_type": "open_startup_intake_ui", "status": "done"}],
            },
        )

        summary = router._controller_action_ledger_summary(run_root)  # type: ignore[attr-defined]

        self.assertEqual(summary["history_done_count"], 1)
        self.assertEqual(summary["active_work_count"], 0)
        self.assertEqual(summary["pending_action_ids"], [])
        self.assertEqual(summary["waiting_action_ids"], [])

    def test_passive_wait_projection_is_not_ordinary_controller_work(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)

        self.force_startup_fact_role_wait(root)

        ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        ordinary_types = [item.get("action_type") for item in ledger["actions"]]
        passive_types = [item.get("action_type") for item in ledger["passive_waits"]]
        self.assertNotIn("await_role_decision", ordinary_types)
        self.assertIn("await_role_decision", passive_types)
        self.assertTrue(ledger["controller_actions_are_executable_only"])
        self.assertTrue(ledger["passive_waits_projected_via_status_not_work_board"])
        summary = router._controller_action_ledger_summary(run_root)  # type: ignore[attr-defined]
        self.assertEqual(summary["passive_wait_count"], 1)
        self.assertEqual(summary["active_work_count"], 0)

    def test_all_passive_wait_types_are_status_projections_not_work_rows(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        passive_actions = [
            router.make_action(
                action_type="await_role_decision",
                actor="controller",
                label="test_wait_role",
                summary="Wait for role output.",
                to_role="project_manager",
                extra={"allowed_external_events": ["pm_resume_recovery_decision_returned"]},
            ),
            router.make_action(
                action_type="await_card_return_event",
                actor="controller",
                label="test_wait_card",
                summary="Wait for card ACK.",
                to_role="project_manager",
                extra={"expected_return_path": "runtime/card_returns/test-card.json"},
            ),
            router.make_action(
                action_type="await_card_bundle_return_event",
                actor="controller",
                label="test_wait_bundle",
                summary="Wait for bundled card ACK.",
                to_role="project_manager",
                extra={"expected_return_path": "runtime/card_returns/test-bundle.json"},
            ),
            router.make_action(
                action_type="await_current_scope_reconciliation",
                actor="controller",
                label="test_wait_scope_reconciliation",
                summary="Wait for local reconciliation.",
                to_role="controller",
                extra={"scope_kind": "current_node", "scope_id": "node-001", "blockers": [{"kind": "test"}]},
            ),
        ]

        for action in passive_actions:
            router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)

        ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        ordinary_types = [item.get("action_type") for item in ledger["actions"]]
        passive_types = [item.get("action_type") for item in ledger["passive_waits"]]
        for action_type in router.PASSIVE_WAIT_STATUS_ACTION_TYPES:
            self.assertNotIn(action_type, ordinary_types)
            self.assertIn(action_type, passive_types)
        self.assertEqual(ledger["passive_wait_count"], len(router.PASSIVE_WAIT_STATUS_ACTION_TYPES))

    def test_current_work_uses_packet_holder_when_pending_wait_is_empty(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-current-work-packet")
        state = read_json(router.run_state_path(run_root))
        state["pending_action"] = None
        router.save_run_state(run_root, state)
        router.write_json(
            run_root / "packet_ledger.json",
            {
                "schema_version": router.PACKET_LEDGER_SCHEMA,
                "run_id": "run-current-work-packet",
                "active_packet_id": "user_intake",
                "active_packet_status": "packet-body-opened-by-recipient",
                "active_packet_holder": "project_manager",
                "packets": [
                    {
                        "packet_id": "user_intake",
                        "active_packet_status": "packet-body-opened-by-recipient",
                        "active_packet_holder": "project_manager",
                    }
                ],
                "mail": [],
                "updated_at": router.utc_now(),
            },
        )

        daemon_status = router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
        )
        router._write_current_status_summary(run_root, state)  # type: ignore[attr-defined]
        status_summary = read_json(run_root / "display" / "current_status_summary.json")
        snapshot = router._build_foreground_controller_standby_snapshot(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            started_at=router.utc_now(),
            start_monotonic=time.monotonic(),
            poll_count=0,
            max_seconds=0,
            poll_seconds=0.1,
        )

        self.assertIsNone(daemon_status["current_wait"]["waiting_for_role"])
        self.assertEqual(daemon_status["current_work"]["owner_kind"], "role")
        self.assertEqual(daemon_status["current_work"]["owner_key"], "project_manager")
        self.assertEqual(daemon_status["current_work"]["source"], "packet_ledger")
        self.assertEqual(status_summary["current_work"]["owner_key"], "project_manager")
        self.assertEqual(status_summary["current_work"]["packet_id"], "user_intake")
        self.assertEqual(snapshot["current_work"]["owner_key"], "project_manager")

    def test_current_work_uses_passive_reconciliation_owner_when_pending_wait_is_empty(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-current-work-passive")
        state = read_json(router.run_state_path(run_root))
        state["pending_action"] = None
        passive_action = router.make_action(
            action_type="await_current_scope_reconciliation",
            actor="controller",
            label="controller_reconciles_current_scope",
            summary="Reconcile current scope before continuing.",
            to_role="controller",
            extra={"scope_kind": "startup", "scope_id": "startup", "blockers": [{"kind": "test"}]},
        )
        router._write_controller_action_entry(root, run_root, state, passive_action)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)

        daemon_status = router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
        )
        router._write_current_status_summary(run_root, state)  # type: ignore[attr-defined]
        status_summary = read_json(run_root / "display" / "current_status_summary.json")

        self.assertIsNone(daemon_status["current_wait"]["waiting_for_role"])
        self.assertEqual(daemon_status["current_work"]["owner_kind"], "controller")
        self.assertEqual(daemon_status["current_work"]["owner_key"], "controller")
        self.assertEqual(daemon_status["current_work"]["source"], "controller_action_ledger.passive_waits")
        self.assertIn("Reconcile current scope", daemon_status["current_work"]["task_label"])
        self.assertEqual(status_summary["current_work"]["owner_key"], "controller")
        self.assertEqual(status_summary["current_work"]["source"], "controller_action_ledger.passive_waits")

    def test_router_daemon_tick_writes_controller_action_ledger_and_receipt_reconciles(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)

        result = router.run_router_daemon(root, max_ticks=1, release_lock_on_exit=True)

        self.assertEqual(result["tick_count"], 1)
        action_id = result["ticks"][0]["controller_action_id"]
        self.assertTrue(action_id)
        action_record = read_json(run_root / "runtime" / "controller_actions" / f"{action_id}.json")
        self.assertEqual(action_record["schema_version"], router.CONTROLLER_ACTION_SCHEMA)
        self.assertIn(action_record["status"], {"pending", "waiting"})
        receipt_result = router.record_controller_action_receipt(
            root,
            action_id=action_id,
            status="done",
            payload={"test_receipt": True},
        )
        self.assertTrue(receipt_result["ok"])
        action_record = read_json(run_root / "runtime" / "controller_actions" / f"{action_id}.json")
        self.assertEqual(action_record["status"], "done")
        ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        self.assertGreaterEqual(ledger["counts"]["done"], 1)

    def test_router_daemon_queues_visible_startup_rows_after_internal_audit(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "write_display_surface_status")

        result = router.run_router_daemon(root, max_ticks=1, release_lock_on_exit=True)

        tick = result["ticks"][0]
        self.assertGreaterEqual(tick["queued_count"], 1)
        queued_types = [item["action_type"] for item in tick["queued_actions"]]
        self.assertNotIn("write_startup_mechanical_audit", queued_types)
        self.assertIn("write_display_surface_status", queued_types)
        self.assertIn("write_startup_mechanical_audit", self.router_internal_action_types(root))
        self.assertIn(tick["queue_stop_reason"], {"barrier", "passive_wait_status"})
        scheduler = read_json(run_root / "runtime" / "router_scheduler_ledger.json")
        self.assertEqual(scheduler["schema_version"], router.ROUTER_SCHEDULER_LEDGER_SCHEMA)
        self.assertTrue(scheduler["router_is_only_scheduler_writer"])
        controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        startup_rows = [item for item in controller_ledger["actions"] if item.get("scope_kind") == "startup"]
        self.assertGreaterEqual(len(startup_rows), 1)
        self.assertNotIn("write_startup_mechanical_audit", [item.get("action_type") for item in startup_rows])
        for row in startup_rows:
            record = read_json(run_root / "runtime" / "controller_actions" / f"{row['action_id']}.json")
            self.assertEqual(record["dependencies"], [])
            self.assertTrue(record["router_scheduler_row_id"])

    def test_router_daemon_immediately_continues_after_queue_budget_stop(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        calls: list[int] = []

        def fake_queue(project_root: Path, run_root: Path, run_state: dict) -> dict:
            del project_root, run_root, run_state
            calls.append(1)
            return {
                "queued_count": router.ROUTER_DAEMON_MAX_QUEUE_ACTIONS_PER_TICK if len(calls) == 1 else 0,
                "queued_actions": [],
                "stop_reason": "max_actions_per_tick" if len(calls) == 1 else "no_action",
                "current_action": None,
            }

        with (
            mock.patch.object(router, "_router_daemon_fill_action_queue", side_effect=fake_queue),
            mock.patch.object(router.time, "sleep") as sleep_mock,
        ):
            result = router.run_router_daemon(root, max_ticks=2, release_lock_on_exit=True)

        self.assertEqual(result["tick_count"], 2)
        self.assertEqual(len(calls), 2)
        sleep_mock.assert_not_called()

    def test_router_daemon_sleeps_after_real_queue_wait(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)

        def fake_queue(project_root: Path, run_root: Path, run_state: dict) -> dict:
            del project_root, run_root, run_state
            return {
                "queued_count": 1,
                "queued_actions": [],
                "stop_reason": "barrier",
                "current_action": None,
            }

        with (
            mock.patch.object(router, "_router_daemon_fill_action_queue", side_effect=fake_queue),
            mock.patch.object(router.time, "sleep") as sleep_mock,
        ):
            result = router.run_router_daemon(root, max_ticks=2, release_lock_on_exit=True)

        self.assertEqual(result["tick_count"], 2)
        sleep_mock.assert_called_once_with(router.ROUTER_DAEMON_TICK_SECONDS)

    def test_startup_obligations_are_not_global_scheduler_barriers(self) -> None:
        root = self.make_project()
        run_root = root / "run"
        run_root.mkdir(parents=True)
        run_state = {"run_id": "test-run"}

        cases = (
            (
                "emit_startup_banner",
                "parallel_obligation",
                {"card_id": "startup_banner", "requires_user_dialog_display_confirmation": True},
            ),
            (
                "create_heartbeat_automation",
                "parallel_obligation",
                {"requires_host_automation": True},
            ),
            (
                "write_display_surface_status",
                "parallel_obligation",
                {"requires_user_dialog_display_confirmation": True},
            ),
            (
                "start_role_slots",
                "local_dependency",
                {"requires_host_spawn": True},
            ),
        )

        for action_type, progress_class, extra in cases:
            with self.subTest(action_type=action_type):
                action = router.make_action(
                    action_type=action_type,
                    actor="bootloader" if action_type != "write_display_surface_status" else "controller",
                    label=f"test_{action_type}",
                    summary=f"Test scheduler classification for {action_type}.",
                    extra=extra,
                )
                prepared = router._prepare_router_scheduled_action(root, run_root, run_state, action)  # type: ignore[attr-defined]
                self.assertEqual(prepared["scope_kind"], "startup")
                self.assertEqual(prepared["router_scheduler_progress_class"], progress_class)
                self.assertEqual(prepared["router_scheduler_barrier_kind"], "none")
                self.assertTrue(router._router_daemon_can_continue_after_enqueued_action(prepared))  # type: ignore[attr-defined]

    def test_true_barriers_still_stop_scheduler_queueing(self) -> None:
        root = self.make_project()
        run_root = root / "run"
        run_root.mkdir(parents=True)
        run_state = {"run_id": "test-run"}

        cases = (
            (
                "open_startup_intake_ui",
                {"requires_host_automation": True, "requires_payload": "startup_intake_result"},
            ),
            (
                "record_startup_answers",
                {"requires_user": True, "requires_payload": "startup_answers"},
            ),
            (
                "await_card_return_event",
                {"expected_return_path": "mailbox/outbox/card_acks/test.ack.json"},
            ),
        )

        for action_type, extra in cases:
            with self.subTest(action_type=action_type):
                action = router.make_action(
                    action_type=action_type,
                    actor="bootloader" if action_type != "await_card_return_event" else "controller",
                    label=f"test_{action_type}",
                    summary=f"Test true scheduler barrier for {action_type}.",
                    extra=extra,
                )
                prepared = router._prepare_router_scheduled_action(root, run_root, run_state, action)  # type: ignore[attr-defined]
                self.assertEqual(prepared["router_scheduler_progress_class"], "true_barrier")
                self.assertNotEqual(prepared["router_scheduler_barrier_kind"], "none")
                self.assertFalse(router._router_daemon_can_continue_after_enqueued_action(prepared))  # type: ignore[attr-defined]

    def test_reconciled_scheduler_row_is_not_downgraded_by_later_receipt_sync(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        action = router.make_action(
            action_type="write_display_surface_status",
            actor="controller",
            label="test_reconciled_scheduler_row",
            summary="Test scheduler reconciliation monotonicity.",
            extra={"postcondition": "startup_display_status_written"},
        )
        entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        row_id = entry["router_scheduler_row_id"]
        router._update_router_scheduler_row(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            row_id=row_id,
            router_state="reconciled",
            reconciliation={"source": "test_reconciliation"},
        )
        router._update_router_scheduler_row(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            row_id=row_id,
            router_state="receipt_done",
            reconciliation={"source": "late_receipt_sync"},
        )

        scheduler = read_json(run_root / "runtime" / "router_scheduler_ledger.json")
        row = next(item for item in scheduler["rows"] if item["row_id"] == row_id)
        self.assertEqual(row["router_state"], "reconciled")
        self.assertEqual(row["reconciliation"]["source"], "test_reconciliation")
        self.assertEqual(row["reconciliation"]["latest_receipt_sync"]["source"], "late_receipt_sync")

    def test_startup_bootloader_receipt_updates_bootstrap_and_scheduler_row(self) -> None:
        root = self.make_project()
        router.run_until_wait(root, new_invocation=True)
        router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))
        load_action = router.run_until_wait(root)
        self.assertEqual(load_action["action_type"], "load_controller_core")
        router.apply_action(root, "load_controller_core", self.payload_for_action(load_action))
        run_root = self.run_root_for(root)
        controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        banner_row = next(item for item in controller_ledger["actions"] if item["action_type"] == "emit_startup_banner")
        action_id = banner_row["action_id"]
        action_record = read_json(run_root / "runtime" / "controller_actions" / f"{action_id}.json")
        action = action_record["action"]
        row_id = action["router_scheduler_row_id"]

        result = router.record_controller_action_receipt(
            root,
            action_id=action_id,
            status="done",
            payload=self.payload_for_action(action),
        )

        self.assertTrue(result["ok"])
        bootstrap = self.bootstrap_state(root)
        self.assertTrue(bootstrap["flags"]["banner_emitted"])
        self.assertNotEqual((bootstrap.get("pending_action") or {}).get("controller_action_id"), action_id)
        action_record = read_json(run_root / "runtime" / "controller_actions" / f"{action_id}.json")
        self.assertEqual(action_record["router_reconciliation_status"], "reconciled")
        scheduler = read_json(run_root / "runtime" / "router_scheduler_ledger.json")
        row = next(item for item in scheduler["rows"] if item["row_id"] == row_id)
        self.assertEqual(row["router_state"], "reconciled")
        self.assertNotEqual((self.bootstrap_state(root).get("pending_action") or {}).get("action_type"), "emit_startup_banner")

    def test_startup_review_join_checks_bootstrap_banner_and_role_flags(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        bootstrap = self.bootstrap_state(root)
        bootstrap["flags"]["banner_emitted"] = False
        bootstrap["flags"]["roles_started"] = False
        router.write_json(router.bootstrap_state_path(root), bootstrap)

        blockers = router._startup_pre_review_reconciliation_blockers(root, run_root, state)  # type: ignore[attr-defined]
        missing_flags = {
            blocker.get("flag")
            for blocker in blockers
            if blocker.get("kind") == "missing_startup_bootstrap_flag"
        }
        self.assertIn("banner_emitted", missing_flags)
        self.assertIn("roles_started", missing_flags)

    def test_runtime_ledgers_remain_valid_json_after_repeated_daemon_writes(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)

        for _ in range(3):
            result = router.run_router_daemon(root, max_ticks=1, release_lock_on_exit=True)
            self.assertEqual(result["tick_count"], 1)
            for path in (
                run_root / "runtime" / "router_scheduler_ledger.json",
                run_root / "runtime" / "controller_action_ledger.json",
                run_root / "runtime" / "router_daemon_status.json",
                run_root / "runtime" / "router_daemon.lock",
            ):
                payload = read_json(path)
                self.assertIsInstance(payload, dict)

    def test_router_daemon_corrupted_scheduler_ledger_writes_error_status(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        scheduler_path = run_root / "runtime" / "router_scheduler_ledger.json"
        scheduler_path.write_text(
            '{"schema_version": "flowpilot.router_scheduler_ledger.v1"}\nBROKEN',
            encoding="utf-8",
        )

        with self.assertRaises(router.RouterLedgerCorruptionError):
            router.run_router_daemon(root, max_ticks=1, release_lock_on_exit=True)

        lock = read_json(run_root / "runtime" / "router_daemon.lock")
        status = read_json(run_root / "runtime" / "router_daemon_status.json")
        self.assertEqual(lock["status"], "error")
        self.assertEqual(status["lifecycle_status"], "daemon_error")
        self.assertFalse(status["daemon_live"])
        self.assertEqual(status["error"]["type"], "RouterLedgerCorruptionError")
        self.assertFalse(status["router_scheduler_ledger"]["valid_json"])

    def test_router_daemon_waits_on_fresh_scheduler_write_lock_before_error(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        state = read_json(router.run_state_path(run_root))
        scheduler_path = run_root / "runtime" / "router_scheduler_ledger.json"
        scheduler_path.write_text(
            '{"schema_version": "flowpilot.router_scheduler_ledger.v1"}\nBROKEN',
            encoding="utf-8",
        )
        write_lock = router._json_write_lock_path(scheduler_path)  # type: ignore[attr-defined]
        write_lock.write_text(
            json.dumps(
                {
                    "schema_version": "flowpilot.runtime_json_write_lock.v1",
                    "path": str(scheduler_path),
                    "pid": 0,
                    "created_at": router.utc_now(),
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        def finish_write() -> None:
            time.sleep(0.05)
            ledger = router._empty_router_scheduler_ledger(root, run_root, state)  # type: ignore[attr-defined]
            scheduler_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            write_lock.unlink()

        thread = threading.Thread(target=finish_write, daemon=True)
        thread.start()
        result = router.run_router_daemon(root, max_ticks=2, observe_only=True, release_lock_on_exit=True)
        thread.join(timeout=1.0)

        self.assertEqual(result["tick_count"], 2)
        self.assertTrue(result["ticks"][0]["deferred"])
        self.assertEqual(result["ticks"][0]["defer_reason"], "runtime_ledger_write_in_progress")
        self.assertFalse(result["ticks"][1].get("deferred", False))
        self.assertEqual(read_json(scheduler_path)["schema_version"], router.ROUTER_SCHEDULER_LEDGER_SCHEMA)

    def test_foreground_next_waits_on_fresh_controller_action_write_lock(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        action_path = sorted((run_root / "runtime" / "controller_actions").glob("*.json"))[0]
        original_entry = read_json(action_path)
        action_path.write_text(
            '{"schema_version": "flowpilot.controller_action.v1"}\nBROKEN',
            encoding="utf-8",
        )
        write_lock = router._json_write_lock_path(action_path)  # type: ignore[attr-defined]
        write_lock.write_text(
            json.dumps(
                {
                    "schema_version": "flowpilot.runtime_json_write_lock.v1",
                    "path": str(action_path),
                    "pid": 0,
                    "created_at": router.utc_now(),
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        def finish_write() -> None:
            time.sleep(0.05)
            action_path.write_text(json.dumps(original_entry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            write_lock.unlink()

        thread = threading.Thread(target=finish_write, daemon=True)
        thread.start()
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = router.main(["--root", str(root), "next", "--json"])
        thread.join(timeout=1.0)

        self.assertEqual(exit_code, 0, stdout.getvalue())
        result = json.loads(stdout.getvalue())
        self.assertTrue(result["runtime_write_settlement"]["waited"])
        self.assertEqual(result["runtime_write_settlement"]["command"], "next")
        self.assertGreaterEqual(result["runtime_write_settlement"]["wait_count"], 1)
        self.assertEqual(read_json(action_path)["schema_version"], router.CONTROLLER_ACTION_SCHEMA)

    def test_router_daemon_status_not_active_after_error_lock_or_missing_pid(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        state = read_json(router.run_state_path(run_root))
        base_lock = {
            "schema_version": router.ROUTER_DAEMON_LOCK_SCHEMA,
            "run_id": state.get("run_id"),
            "run_root": router.project_relative(root, run_root),
            "created_at": router.utc_now(),
            "last_tick_at": router.utc_now(),
            "tick_interval_seconds": router.ROUTER_DAEMON_TICK_SECONDS,
            "stale_after_seconds": router.ROUTER_DAEMON_LOCK_STALE_SECONDS,
            "owner": router._router_daemon_owner(),  # type: ignore[attr-defined]
        }

        error_status = router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
            lock={**base_lock, "status": "error"},
        )
        self.assertEqual(error_status["lifecycle_status"], "daemon_error")
        self.assertFalse(error_status["lock"]["live"])

        missing_pid_status = router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
            lock={
                **base_lock,
                "status": "active",
                "owner": {"pid": 999999999, "process_name": "missing-test-daemon"},
            },
        )
        self.assertEqual(missing_pid_status["lifecycle_status"], "daemon_stale_or_missing")
        self.assertFalse(missing_pid_status["lock"]["process_live"])
        self.assertFalse(missing_pid_status["daemon_live"])

    def test_startup_reviewer_event_uses_current_scope_reconciliation(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        self.apply_startup_heartbeat_if_requested(root)
        action = self.next_after_display_sync(root)
        while action["action_type"] in {
            "confirm_controller_core_boundary",
            "check_prompt_manifest",
            "write_startup_mechanical_audit",
            "write_display_surface_status",
        }:
            router.apply_action(root, str(action["action_type"]), self.payload_for_action(action))
            action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "deliver_system_card_bundle")
        self.mark_controller_action_done(root, action, {"delivery_relayed": True})

        result = router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(
                root,
                "startup/reviewer_report_before_startup_scope_clean",
                self.startup_fact_report_body(root),
            ),
        )

        self.assertFalse(result["ok"])
        self.assertTrue(result["current_scope_reconciliation_blocked"])
        self.assertEqual(result["scope_kind"], "startup")
        self.assertEqual(result["next_required_action"]["action_type"], "await_current_scope_reconciliation")
        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"]["startup_fact_reported"])

    def test_controller_boundary_done_receipt_reclaims_router_postcondition(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        run_root, state, action = self.legacy_controller_boundary_action(root)
        self.assertEqual(action["action_type"], "confirm_controller_core_boundary")
        entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        router._write_controller_boundary_confirmation(root, run_root, state)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)

        receipt = router.record_controller_action_receipt(
            root,
            action_id=entry["action_id"],
            status="done",
            payload={"controller_action_completed": True},
        )

        self.assertTrue(receipt["ok"])
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["controller_role_confirmed"])
        self.assertTrue(state["flags"]["controller_boundary_confirmation_written"])
        self.assertTrue((run_root / "startup" / "controller_boundary_confirmation.json").exists())
        action_record = read_json(run_root / "runtime" / "controller_actions" / f"{entry['action_id']}.json")
        self.assertEqual(action_record["router_reconciliation_status"], "reconciled")

    def test_controller_boundary_projection_reclaims_stale_flags_without_pending_action(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        run_root, state, action = self.legacy_controller_boundary_action(root)
        self.assertEqual(action["action_type"], "confirm_controller_core_boundary")
        entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        router._write_controller_boundary_confirmation(root, run_root, state)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)

        receipt = router.record_controller_action_receipt(
            root,
            action_id=entry["action_id"],
            status="done",
            payload={"controller_action_completed": True},
        )
        self.assertTrue(receipt["ok"])

        state = read_json(router.run_state_path(run_root))
        state["flags"]["controller_role_confirmed"] = False
        state["flags"]["controller_role_confirmed_from_router_core"] = False
        state["flags"]["controller_boundary_confirmation_written"] = False
        state["pending_action"] = None
        state.pop("controller_boundary_confirmation", None)
        router.save_run_state(run_root, state)

        next_action = self.next_after_display_sync(root)

        self.assertNotEqual(next_action["action_type"], "confirm_controller_core_boundary")
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["controller_role_confirmed"])
        self.assertTrue(state["flags"]["controller_role_confirmed_from_router_core"])
        self.assertTrue(state["flags"]["controller_boundary_confirmation_written"])
        self.assertNotEqual((state.get("pending_action") or {}).get("action_type"), "confirm_controller_core_boundary")
        labels = [item["label"] for item in state["history"] if isinstance(item, dict)]
        self.assertIn("router_reconciled_controller_boundary_projection", labels)
        action_record = read_json(run_root / "runtime" / "controller_actions" / f"{entry['action_id']}.json")
        self.assertEqual(action_record["router_reconciliation_status"], "reconciled")
        scheduler = read_json(run_root / "runtime" / "router_scheduler_ledger.json")
        row = next(item for item in scheduler["rows"] if item["row_id"] == action_record["router_scheduler_row_id"])
        self.assertEqual(row["router_state"], "reconciled")

    def test_sync_display_plan_done_receipt_updates_router_fact_before_next_action(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)

        result = router.run_router_daemon(root, max_ticks=1, release_lock_on_exit=True)
        action_id = result["ticks"][0]["controller_action_id"]
        action_record = read_json(run_root / "runtime" / "controller_actions" / f"{action_id}.json")
        self.assertEqual(action_record["action_type"], "sync_display_plan")
        self.assert_controller_receipt_entry_projection(action_record)

        router.record_controller_action_receipt(
            root,
            action_id=action_id,
            status="done",
            payload={"completed_by_test_controller": True},
        )

        next_action = router.next_action(root)

        self.assertNotEqual(next_action["action_type"], "sync_display_plan")
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["visible_plan_synced"])
        self.assertIn("visible_plan_sync", state)
        self.assertEqual(state["visible_plan_sync"]["host_action"], "replace_visible_plan")
        self.assertNotEqual((state.get("pending_action") or {}).get("controller_action_id"), action_id)
        labels = [item["label"] for item in state["history"] if isinstance(item, dict)]
        self.assertIn("router_reconciled_pending_controller_action_receipt", labels)

    def test_controller_action_ledger_handles_multiple_receipts_and_duplicates(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))

        first_action = router.make_action(
            action_type="check_prompt_manifest",
            actor="controller",
            label="test_multi_action_first",
            summary="Test first ledger action.",
        )
        second_action = router.make_action(
            action_type="write_startup_mechanical_audit",
            actor="controller",
            label="test_multi_action_second",
            summary="Test dependent ledger action.",
            extra={"dependencies": ["test_multi_action_first"]},
        )
        blocked_action = router.make_action(
            action_type="write_display_surface_status",
            actor="controller",
            label="test_multi_action_blocked",
            summary="Test blocked ledger action.",
        )
        first = router._write_controller_action_entry(root, run_root, state, first_action)  # type: ignore[attr-defined]
        second = router._write_controller_action_entry(root, run_root, state, second_action)  # type: ignore[attr-defined]
        blocked = router._write_controller_action_entry(root, run_root, state, blocked_action)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)

        ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        baseline_done = int(ledger["counts"].get("done") or 0)
        baseline_blocked = int(ledger["counts"].get("blocked") or 0)
        self.assertEqual(ledger["counts"]["pending"], 3)
        second_record = read_json(run_root / "runtime" / "controller_actions" / f"{second['action_id']}.json")
        self.assertEqual(second_record["dependencies"], [])
        scheduler = read_json(run_root / "runtime" / "router_scheduler_ledger.json")
        second_row = next(row for row in scheduler["rows"] if row["controller_action_id"] == second["action_id"])
        self.assertEqual(second_row["dependencies"], ["test_multi_action_first"])
        self.assertTrue(second_row["router_only_dependency_metadata"])

        router.record_controller_action_receipt(root, action_id=first["action_id"], status="done")
        router.record_controller_action_receipt(root, action_id=first["action_id"], status="done")
        router.record_controller_action_receipt(root, action_id=second["action_id"], status="done")
        router.record_controller_action_receipt(
            root,
            action_id=blocked["action_id"],
            status="blocked",
            payload={"reason": "test-blocked"},
        )

        ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        self.assertEqual(ledger["counts"]["done"], baseline_done + 2)
        self.assertEqual(ledger["counts"]["blocked"], baseline_blocked + 1)
        first_record = read_json(run_root / "runtime" / "controller_actions" / f"{first['action_id']}.json")
        blocked_record = read_json(run_root / "runtime" / "controller_actions" / f"{blocked['action_id']}.json")
        self.assertEqual(first_record["status"], "done")
        self.assertEqual(blocked_record["status"], "blocked")
        self.assertEqual(blocked_record["blocked_payload"], {"reason": "test-blocked"})

    def test_completed_pending_controller_action_receipt_is_not_returned_again(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        action = router.make_action(
            action_type="test_metadata_only_host_action",
            actor="controller",
            label="test_metadata_only_host_action",
            summary="Test metadata-only action already completed by Controller.",
        )
        state["pending_action"] = action
        entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)
        router.record_controller_action_receipt(
            root,
            action_id=entry["action_id"],
            status="done",
            payload={"completed_by_test": True},
        )

        next_action = self.next_after_display_sync(root)

        self.assertNotEqual(next_action["action_type"], "test_metadata_only_host_action")
        state = read_json(router.run_state_path(run_root))
        self.assertNotEqual((state.get("pending_action") or {}).get("controller_action_id"), entry["action_id"])
        labels = [item["label"] for item in state["history"] if isinstance(item, dict)]
        self.assertIn("router_reconciled_pending_controller_action_receipt", labels)

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
            action_type="rehydrate_role_agents",
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
        self.assertEqual(state["active_control_blocker"]["originating_action_type"], "rehydrate_role_agents")
        self.assertNotEqual((state.get("pending_action") or {}).get("action_type"), "rehydrate_role_agents")

    def test_startup_fact_role_output_ledger_is_reconciled_by_router_tick(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        self.deliver_startup_fact_check_card(root)
        wait_action = self.force_startup_fact_role_wait(root)
        self.assertEqual(wait_action["action_type"], "await_role_decision")
        router.stop_router_daemon(root, reason="test_release_before_role_output_reconciliation")

        self.submit_startup_fact_runtime_output_to_ledger(root)
        before = read_json(router.run_state_path(run_root))
        self.assertFalse(before["flags"]["startup_fact_reported"])

        router.run_router_daemon(root, max_ticks=1, release_lock_on_exit=True)

        after = read_json(router.run_state_path(run_root))
        self.assertTrue(after["flags"]["startup_fact_reported"])
        self.assertTrue((run_root / "startup" / "startup_fact_report.json").exists())
        events = [item for item in after["events"] if isinstance(item, dict) and item.get("event") == "reviewer_reports_startup_facts"]
        self.assertEqual(len(events), 1)
        self.assertNotEqual((after.get("pending_action") or {}).get("label"), wait_action["label"])

    def test_recorded_external_event_closes_matching_wait_action_row(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.deliver_startup_fact_check_card(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        wait_action = self.force_startup_fact_role_wait(root)

        result = router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(
                root,
                "startup/reviewer_startup_fact_report_wait_closure",
                self.startup_fact_report_body(root),
            ),
        )

        self.assertTrue(result["ok"])
        self.assertTrue(result["wait_closure"]["changed"])
        state = read_json(router.run_state_path(run_root))
        action_id = wait_action["controller_action_id"]
        action_record = read_json(run_root / "runtime" / "controller_actions" / f"{action_id}.json")
        self.assertEqual(action_record["status"], "done")
        self.assertEqual(action_record["completion_source"], "router_external_event_reconciliation")
        self.assertEqual(action_record["satisfied_by_external_event"], "reviewer_reports_startup_facts")
        self.assertFalse(action_record["controller_receipt_required"])
        self.assert_controller_receipt_entry_projection(
            action_record,
            receipt_required=False,
            router_pending_apply_required=False,
        )
        ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        waiting_ids = [item["action_id"] for item in ledger["actions"] if item["status"] == "waiting"]
        self.assertNotIn(action_id, waiting_ids)
        self.assertNotEqual((state.get("pending_action") or {}).get("controller_action_id"), action_id)

    def test_already_recorded_external_event_closes_stale_wait_action_row(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.deliver_startup_fact_check_card(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        payload = self.role_report_envelope(
            root,
            "startup/reviewer_startup_fact_report_already_recorded_wait_closure",
            self.startup_fact_report_body(root),
        )
        first = router.record_external_event(root, "reviewer_reports_startup_facts", payload)
        self.assertTrue(first["ok"])

        state = read_json(router.run_state_path(run_root))
        stale_wait = router.make_action(
            action_type="await_role_decision",
            actor="controller",
            label="test_stale_wait_for_already_recorded_startup_facts",
            summary="Test stale wait row that should be closed by replayed event evidence.",
            to_role="human_like_reviewer",
            extra={
                "waiting_for_role": "human_like_reviewer",
                "allowed_external_events": ["reviewer_reports_startup_facts"],
            },
        )
        state["pending_action"] = stale_wait
        entry = router._write_controller_action_entry(root, run_root, state, stale_wait)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)

        replay = router.record_external_event(root, "reviewer_reports_startup_facts", payload)

        self.assertTrue(replay["already_recorded"])
        self.assertTrue(replay["wait_closure"]["changed"])
        action_record = read_json(run_root / "runtime" / "controller_actions" / f"{entry['action_id']}.json")
        self.assertEqual(action_record["status"], "done")
        self.assertEqual(action_record["completion_source"], "router_external_event_reconciliation")
        self.assertEqual(action_record["satisfied_by_external_event"], "reviewer_reports_startup_facts")
        state = read_json(router.run_state_path(run_root))
        self.assertNotEqual((state.get("pending_action") or {}).get("controller_action_id"), entry["action_id"])

    def test_startup_fact_canonical_artifact_drift_syncs_flag_once(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.deliver_startup_fact_check_card(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        wait_action = self.force_startup_fact_role_wait(root)
        envelope = self.submit_startup_fact_runtime_output_to_ledger(root)
        state = read_json(router.run_state_path(run_root))
        router._write_startup_fact_report(root, run_root, state, envelope)  # type: ignore[attr-defined]
        state["flags"]["startup_fact_reported"] = False
        state["events"] = [
            item
            for item in state["events"]
            if not isinstance(item, dict) or item.get("event") != "reviewer_reports_startup_facts"
        ]
        state["pending_action"] = wait_action
        router.save_run_state(run_root, state)

        router.next_action(root)
        router.next_action(root)

        after = read_json(router.run_state_path(run_root))
        self.assertTrue(after["flags"]["startup_fact_reported"])
        events = [item for item in after["events"] if isinstance(item, dict) and item.get("event") == "reviewer_reports_startup_facts"]
        self.assertEqual(len(events), 1)

    def test_foreground_controller_standby_waits_on_live_daemon_role_wait(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        wait_action = self.force_startup_fact_role_wait(root)
        self.assertEqual(wait_action["action_type"], "await_role_decision")
        self.assertIn("reviewer_reports_startup_facts", wait_action["allowed_external_events"])

        standby = router.foreground_controller_standby(root, max_seconds=0, poll_seconds=0.01, bounded_diagnostic=True)

        self.assertEqual(standby["schema_version"], router.FOREGROUND_CONTROLLER_STANDBY_SCHEMA)
        self.assertEqual(standby["standby_state"], "timeout_still_waiting")
        self.assertTrue(standby["controller_must_continue_standby"])
        self.assertTrue(standby["router_daemon"]["daemon_live"])
        self.assertEqual(standby["current_wait"]["waiting_for_role"], "human_like_reviewer")
        self.assertEqual(standby["normal_router_progress_source"], "router_daemon_status_and_controller_action_ledger")
        self.assertTrue(standby["standby_does_not_drive_router_progress"])
        self.assertFalse(standby["sealed_body_reads_allowed"])
        self.assertFalse(standby["foreground_exit_allowed"])
        self.assertFalse(standby["controller_stop_allowed"])
        self.assertEqual(standby["foreground_required_mode"], "watch_router_daemon")
        self.assertFalse(standby["controller_must_process_pending_action_before_exit"])
        self.assertFalse(standby["controller_must_process_wait_target_before_exit"])
        self.assertEqual(standby["current_wait"]["wait_class"], "report_result")
        self.assertTrue(standby["current_wait"]["liveness_probe"]["required"])
        self.assertTrue(standby["current_wait"]["liveness_probe"]["current_liveness_is_not_cached_authority"])
        self.assertNotIn("role_alive", standby["current_wait"])
        self.assertTrue(standby["exit_policy"]["live_daemon_wait_requires_standby"])
        self.assertTrue(standby["bounded_diagnostic"])
        self.assertTrue(standby["bounded_timeout_is_diagnostic_only"])
        standby_task = standby["continuous_standby_task"]
        self.assertEqual(standby_task["task_kind"], "continuous_controller_standby")
        self.assertEqual(standby_task["codex_plan_sync"]["plan_status"], "in_progress")
        self.assertFalse(standby_task["foreground_close_allowed_while_flowpilot_running"])
        self.assertTrue(standby_task["new_controller_work_requires_ledger_update_and_top_down_reentry"])
        self.assertIn("continuous monitoring duty", standby_task["codex_plan_sync"]["plan_item"])
        self.assertIn("return to top-to-bottom row processing", standby_task["codex_plan_sync"]["plan_item"])
        self.assertIn("timeout_still_waiting", standby_task["do_not_mark_complete_on"])
        self.assertEqual(standby_task["current_wait"]["waiting_for_role"], "human_like_reviewer")
        run_root = self.run_root_for(root)
        ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        standby_rows = [
            item
            for item in ledger["actions"]
            if item.get("action_type") == router.CONTINUOUS_CONTROLLER_STANDBY_ACTION_TYPE
        ]
        self.assertEqual(len(standby_rows), 1)
        standby_entry = read_json(root / standby_rows[0]["action_path"])
        self.assertEqual(standby_entry["status"], "waiting")
        self.assertTrue(standby_entry["action"]["codex_plan_sync"]["required"])
        self.assertTrue(
            standby_entry["action"]["codex_plan_sync"]["new_controller_work_returns_to_top_down_processing"]
        )

    def test_foreground_controller_standby_materializes_report_reminder_with_liveness_probe(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        self.force_startup_fact_role_wait(root)
        state = read_json(router.run_state_path(run_root))
        state["pending_action"]["created_at"] = self.old_utc(minutes=11)
        lock = router._refresh_router_daemon_lock(root, run_root)  # type: ignore[attr-defined]
        router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
            current_action=state["pending_action"],
            lock=lock,
        )
        router.save_run_state(run_root, state)

        standby = router.foreground_controller_standby(root, max_seconds=5, poll_seconds=0.01)

        self.assertEqual(standby["standby_state"], "controller_action_ready")
        self.assertEqual(standby["foreground_required_mode"], "process_controller_action")
        self.assertFalse(standby["controller_must_process_wait_target_before_exit"])
        self.assertTrue(standby["current_wait"]["reminder"]["due"])
        self.assertTrue(standby["current_wait"]["liveness_probe"]["due"])
        self.assertTrue(standby["current_wait"]["liveness_probe"]["required"])
        self.assertTrue(standby["current_wait"]["liveness_probe"]["current_liveness_is_not_cached_authority"])
        materialized = standby["materialized_wait_target_controller_action"]
        self.assertEqual(materialized["action_type"], router.WAIT_TARGET_REMINDER_ACTION_TYPE)
        action_record = read_json(run_root / "runtime" / "controller_actions" / f"{materialized['controller_action_id']}.json")
        reminder_action = action_record["action"]
        self.assertEqual(reminder_action["target_role"], "human_like_reviewer")
        self.assertEqual(reminder_action["wait_class"], "report_result")
        self.assertTrue(reminder_action["fresh_liveness_probe_required"])
        self.assertTrue(reminder_action["controller_must_use_router_authored_text"])
        self.assertFalse(reminder_action["sealed_body_reads_allowed"])

        receipt = router.record_controller_action_receipt(
            root,
            action_id=materialized["controller_action_id"],
            status="done",
            payload={
                "target_role": "human_like_reviewer",
                "delivered_to_role": "human_like_reviewer",
                "reminder_text_sha256": reminder_action["reminder_text_sha256"],
                "sealed_body_reads": False,
                "liveness_probe": {"checked_at": router.utc_now(), "result": "working"},
            },
        )
        self.assertTrue(receipt["ok"])
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["pending_action"]["last_wait_reminder_at"])
        self.assertEqual(state["pending_action"]["last_liveness_probe"]["result"], "working")
        action_record = read_json(run_root / "runtime" / "controller_actions" / f"{materialized['controller_action_id']}.json")
        self.assertEqual(action_record["status"], "done")

    def test_foreground_controller_standby_default_waits_past_timeout_until_action(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        self.force_startup_fact_role_wait(root)
        result: dict[str, object] = {}

        def run_standby() -> None:
            try:
                result["standby"] = router.foreground_controller_standby(root, max_seconds=0, poll_seconds=0.01)
            except BaseException as exc:  # pragma: no cover - failure relay from thread
                result["error"] = exc

        thread = threading.Thread(target=run_standby, daemon=True)
        thread.start()
        time.sleep(0.05)
        self.assertNotIn("standby", result)

        state = read_json(router.run_state_path(run_root))
        ready_action = router.make_action(
            action_type="sync_display_plan",
            actor="controller",
            label="controller_syncs_display_plan_from_test",
            summary="Controller syncs visible display plan from test.",
        )
        router._write_controller_action_entry(root, run_root, state, ready_action)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)
        thread.join(timeout=1.0)

        self.assertNotIn("error", result)
        self.assertFalse(thread.is_alive())
        standby = result["standby"]
        self.assertIsInstance(standby, dict)
        self.assertEqual(standby["standby_state"], "controller_action_ready")
        self.assertIn(ready_action["controller_action_id"], standby["controller_action_ledger"]["pending_action_ids"])

    def test_foreground_controller_standby_returns_no_output_reissue_required(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        self.force_startup_fact_role_wait(root)
        state = read_json(router.run_state_path(run_root))
        state["pending_action"]["created_at"] = self.old_utc(minutes=11)
        state["pending_action"]["last_liveness_probe"] = {
            "checked_at": router.utc_now(),
            "result": "completed_without_expected_event",
            "evidence_path": "runtime/liveness/reviewer-completed-no-output.json",
        }
        lock = router._refresh_router_daemon_lock(root, run_root)  # type: ignore[attr-defined]
        router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
            current_action=state["pending_action"],
            lock=lock,
        )
        router.save_run_state(run_root, state)

        standby = router.foreground_controller_standby(root, max_seconds=5, poll_seconds=0.01)

        self.assertEqual(standby["standby_state"], "wait_target_reissue_required")
        self.assertEqual(standby["foreground_required_mode"], "record_wait_target_no_output_reissue")
        self.assertTrue(standby["current_wait"]["reissue"]["required"])
        self.assertEqual(standby["current_wait"]["reissue"]["event"], "controller_reports_role_no_output")
        self.assertFalse(standby["current_wait"]["blocker"]["required"])
        self.assertEqual(
            standby["current_wait"]["reissue"]["record_event_payload"]["role_key"],
            "human_like_reviewer",
        )
        self.assertEqual(
            standby["current_wait"]["liveness_probe"]["last_result"],
            "completed_without_expected_event",
        )

    def test_foreground_controller_standby_returns_lost_role_blocker_required(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        self.force_startup_fact_role_wait(root)
        state = read_json(router.run_state_path(run_root))
        state["pending_action"]["created_at"] = self.old_utc(minutes=11)
        state["pending_action"]["last_liveness_probe"] = {
            "checked_at": router.utc_now(),
            "result": "unresponsive",
            "evidence_path": "runtime/liveness/reviewer-unresponsive.json",
        }
        lock = router._refresh_router_daemon_lock(root, run_root)  # type: ignore[attr-defined]
        router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
            current_action=state["pending_action"],
            lock=lock,
        )
        router.save_run_state(run_root, state)

        standby = router.foreground_controller_standby(root, max_seconds=5, poll_seconds=0.01)

        self.assertEqual(standby["standby_state"], "wait_target_blocker_required")
        self.assertEqual(standby["foreground_required_mode"], "record_wait_target_blocker")
        self.assertTrue(standby["current_wait"]["blocker"]["required"])
        self.assertEqual(standby["current_wait"]["blocker"]["event"], "controller_reports_role_liveness_fault")
        self.assertEqual(standby["current_wait"]["blocker"]["record_event_payload"]["role_key"], "human_like_reviewer")
        self.assertEqual(standby["current_wait"]["liveness_probe"]["last_result"], "unresponsive")

    def test_foreground_controller_standby_returns_ack_reminder_and_blocker_due(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        runtime_dir = run_root / "runtime"
        for name in ("controller_actions", "controller_receipts"):
            path = runtime_dir / name
            if path.exists():
                shutil.rmtree(path)
            path.mkdir(parents=True, exist_ok=True)
        state = read_json(router.run_state_path(run_root))
        ack_action = router.make_action(
            action_type="await_card_return_event",
            actor="controller",
            label="controller_waits_for_pm_card_ack",
            summary="Controller waits for PM card ACK.",
            to_role="project_manager",
            extra={
                "waiting_for_role": "project_manager",
                "expected_return_path": "mailbox/outbox/card_acks/pm_core.ack.json",
            },
        )
        state["pending_action"] = ack_action
        state["daemon_mode_enabled"] = True
        return_ledger_path = run_root / "return_event_ledger.json"
        return_ledger = read_json(return_ledger_path)
        return_ledger.setdefault("pending_returns", []).append(
            {
                "return_id": "pm-core-ack",
                "return_kind": "system_card",
                "status": "awaiting_return",
                "target_role": "project_manager",
                "card_return_event": "pm_card_ack",
                "expected_return_path": "mailbox/outbox/card_acks/pm_core.ack.json",
            }
        )
        router.write_json(return_ledger_path, return_ledger)
        router._write_controller_action_entry(root, run_root, state, ack_action)  # type: ignore[attr-defined]
        state["pending_action"]["created_at"] = self.old_utc(minutes=4)
        lock = router._acquire_router_daemon_lock(root, run_root, state)  # type: ignore[attr-defined]
        router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
            current_action=state["pending_action"],
            lock=lock,
        )
        router.save_run_state(run_root, state)

        reminder = router.foreground_controller_standby(root, max_seconds=5, poll_seconds=0.01)

        self.assertEqual(reminder["standby_state"], "controller_action_ready")
        self.assertEqual(reminder["current_wait"]["wait_class"], "ack")
        self.assertTrue(reminder["current_wait"]["reminder"]["due"])
        self.assertFalse(reminder["current_wait"]["blocker"]["required"])
        materialized = reminder["materialized_wait_target_controller_action"]
        self.assertEqual(materialized["action_type"], router.WAIT_TARGET_REMINDER_ACTION_TYPE)
        action_record = read_json(run_root / "runtime" / "controller_actions" / f"{materialized['controller_action_id']}.json")
        reminder_action = action_record["action"]
        self.assertEqual(reminder_action["target_role"], "project_manager")
        self.assertEqual(reminder_action["wait_class"], "ack")
        self.assertFalse(reminder_action["fresh_liveness_probe_required"])

        router.record_controller_action_receipt(
            root,
            action_id=materialized["controller_action_id"],
            status="done",
            payload={
                "target_role": "project_manager",
                "delivered_to_role": "project_manager",
                "reminder_text_sha256": reminder_action["reminder_text_sha256"],
                "sealed_body_reads": False,
            },
        )
        return_ledger = read_json(return_ledger_path)
        self.assertEqual(return_ledger["pending_returns"][0]["status"], "reminded")
        self.assertTrue(return_ledger["pending_returns"][0]["last_wait_reminder_at"])

        state = read_json(router.run_state_path(run_root))
        state["pending_action"]["created_at"] = self.old_utc(minutes=11)
        state["pending_action"]["last_wait_reminder_at"] = self.old_utc(minutes=11)
        lock = router._refresh_router_daemon_lock(root, run_root)  # type: ignore[attr-defined]
        router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
            current_action=state["pending_action"],
            lock=lock,
        )
        router.save_run_state(run_root, state)

        blocker = router.foreground_controller_standby(root, max_seconds=5, poll_seconds=0.01)

        self.assertEqual(blocker["standby_state"], "wait_target_blocker_required")
        self.assertTrue(blocker["current_wait"]["blocker"]["required"])
        self.assertEqual(blocker["current_wait"]["blocker"]["reason"], "ack_missing_after_ten_minutes")

    def test_foreground_controller_standby_self_audits_controller_local_wait(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        runtime_dir = run_root / "runtime"
        for name in ("controller_actions", "controller_receipts"):
            path = runtime_dir / name
            if path.exists():
                shutil.rmtree(path)
            path.mkdir(parents=True, exist_ok=True)
        router.write_json(  # type: ignore[attr-defined]
            runtime_dir / "controller_action_ledger.json",
            {
                "schema_version": router.CONTROLLER_ACTION_LEDGER_SCHEMA,
                "run_id": run_root.name,
                "run_root": self.rel(root, run_root),
                "updated_at": router.utc_now(),
                "actions": [],
                "counts": {"pending": 0, "in_progress": 0, "done": 0, "blocked": 0, "waiting": 0, "skipped": 0, "total": 0},
            },
        )
        state = read_json(router.run_state_path(run_root))
        local_action = router.make_action(
            action_type="sync_display_plan",
            actor="controller",
            label="controller_syncs_display_plan",
            summary="Controller syncs local display plan.",
        )
        state["pending_action"] = local_action
        state["daemon_mode_enabled"] = True
        lock = router._acquire_router_daemon_lock(root, run_root, state)  # type: ignore[attr-defined]
        router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
            current_action=local_action,
            lock=lock,
        )
        router.save_run_state(run_root, state)

        standby = router.foreground_controller_standby(root, max_seconds=5, poll_seconds=0.01)

        self.assertEqual(standby["standby_state"], "wait_target_check_due")
        self.assertEqual(standby["current_wait"]["wait_class"], "controller_local_action")
        self.assertTrue(standby["current_wait"]["controller_local_self_audit"]["required"])
        self.assertFalse(standby["current_wait"]["controller_local_self_audit"]["reminder_allowed"])

    def test_foreground_controller_standby_keeps_alive_when_daemon_has_no_ready_action(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        runtime_dir = run_root / "runtime"
        for name in ("controller_actions", "controller_receipts"):
            path = runtime_dir / name
            if path.exists():
                shutil.rmtree(path)
            path.mkdir(parents=True, exist_ok=True)
        state = read_json(router.run_state_path(run_root))
        state["pending_action"] = None
        state["daemon_mode_enabled"] = True
        router._rebuild_controller_action_ledger(root, run_root, state)  # type: ignore[attr-defined]
        lock = router._refresh_router_daemon_lock(root, run_root)  # type: ignore[attr-defined]
        router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
            current_action=None,
            lock=lock,
        )
        router.save_run_state(run_root, state)

        standby = router.foreground_controller_standby(root, max_seconds=0, poll_seconds=0.01, bounded_diagnostic=True)

        self.assertEqual(standby["standby_state"], "timeout_still_waiting")
        self.assertTrue(standby["controller_must_continue_standby"])
        self.assertFalse(standby["controller_must_process_pending_action_before_exit"])
        self.assertFalse(standby["foreground_exit_allowed"])
        self.assertFalse(standby["controller_stop_allowed"])
        self.assertEqual(standby["foreground_required_mode"], "watch_router_daemon")
        self.assertEqual(standby["controller_action_ledger"]["pending_action_ids"], [])
        self.assertTrue(standby["exit_policy"]["live_daemon_wait_requires_standby"])
        standby_task = standby["continuous_standby_task"]
        self.assertEqual(standby_task["task_kind"], "continuous_controller_standby")
        self.assertTrue(standby_task["codex_plan_sync"]["required"])
        self.assertEqual(standby_task["codex_plan_sync"]["plan_status"], "in_progress")
        self.assertFalse(standby_task["foreground_close_allowed_while_flowpilot_running"])
        self.assertTrue(standby_task["new_controller_work_requires_ledger_update_and_top_down_reentry"])
        self.assertIn("continuous monitoring duty", standby_task["codex_plan_sync"]["plan_item"])
        self.assertIn("no_new_controller_action_yet", standby_task["do_not_mark_complete_on"])
        self.assertEqual(
            standby_task["required_command"],
            "python skills\\flowpilot\\assets\\flowpilot_router.py --root . --json controller-patrol-timer --seconds 10",
        )
        self.assertIn("continue_patrol", standby_task["do_not_mark_complete_on"])
        self.assertIn("wait for the next output", standby_task["loop_rule"])
        self.assertEqual(standby_task["completion_allowed_only_when"], "terminal_return_and_controller_stop_allowed_true")

    def test_controller_patrol_timer_continue_patrol_restarts_and_waits(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        runtime_dir = run_root / "runtime"
        for name in ("controller_actions", "controller_receipts"):
            path = runtime_dir / name
            if path.exists():
                shutil.rmtree(path)
            path.mkdir(parents=True, exist_ok=True)
        state = read_json(router.run_state_path(run_root))
        state["pending_action"] = None
        state["daemon_mode_enabled"] = True
        router._rebuild_controller_action_ledger(root, run_root, state)  # type: ignore[attr-defined]
        lock = router._refresh_router_daemon_lock(root, run_root)  # type: ignore[attr-defined]
        router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
            current_action=None,
            lock=lock,
        )
        router.save_run_state(run_root, state)

        result = router.controller_patrol_timer(root, seconds=0)

        self.assertEqual(result["schema_version"], router.CONTROLLER_PATROL_TIMER_SCHEMA)
        self.assertEqual(result["patrol_result"], "continue_patrol")
        self.assertEqual(result["foreground_required_mode"], "watch_router_daemon")
        self.assertIn("prevent Controller from accidentally exiting", result["anti_exit_reminder"])
        self.assertIn("Immediately rerun next_command and wait", result["controller_instruction"])
        self.assertIn("Starting or restarting the command is not completion", result["controller_instruction"])
        self.assertEqual(
            result["next_command"],
            "python skills\\flowpilot\\assets\\flowpilot_router.py --root . --json controller-patrol-timer --seconds 0",
        )
        self.assertEqual(
            result["standby_status_after_rerun"],
            "continuous_controller_standby remains in_progress until the next command output",
        )
        self.assertFalse(result["command_start_is_completion"])
        self.assertFalse(result["command_restart_is_completion"])
        self.assertEqual(result["monitor_source"], "existing_router_daemon_monitor")

    def test_controller_patrol_timer_requests_liveness_check_after_delayed_daemon_heartbeat(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        runtime_dir = run_root / "runtime"
        for name in ("controller_actions", "controller_receipts"):
            path = runtime_dir / name
            if path.exists():
                shutil.rmtree(path)
            path.mkdir(parents=True, exist_ok=True)
        state = read_json(router.run_state_path(run_root))
        state["pending_action"] = None
        state["daemon_mode_enabled"] = True
        router._rebuild_controller_action_ledger(root, run_root, state)  # type: ignore[attr-defined]
        lock = router._refresh_router_daemon_lock(root, run_root)  # type: ignore[attr-defined]
        lock["last_tick_at"] = self.old_utc(minutes=1)
        router.write_json(run_root / "runtime" / "router_daemon.lock", lock)
        router._write_router_daemon_status(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            lifecycle_status="daemon_active",
            current_action=None,
            lock=lock,
        )
        router.save_run_state(run_root, state)

        result = router.controller_patrol_timer(root, seconds=0)

        self.assertEqual(result["patrol_result"], "check_liveness")
        self.assertEqual(result["foreground_required_mode"], "check_liveness")
        self.assertIn("If the daemon is alive, stay attached", result["controller_instruction"])
        router_daemon = result["standby_snapshot"]["router_daemon"]
        self.assertEqual(router_daemon["heartbeat_status"], "check_liveness")
        self.assertGreater(router_daemon["heartbeat_age_seconds"], router.ROUTER_DAEMON_HEARTBEAT_CHECK_SECONDS)
        self.assertFalse(router_daemon["monitor_can_decide_recovery"])
        self.assertTrue(router_daemon["controller_liveness_check_required"])

    def test_foreground_controller_standby_wakes_on_controller_action_ledger(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        result = router.run_router_daemon(root, max_ticks=1, release_lock_on_exit=False)
        action_id = result["ticks"][0]["controller_action_id"]
        self.assertTrue(action_id)

        standby = router.foreground_controller_standby(root, max_seconds=5, poll_seconds=0.01)

        self.assertEqual(standby["standby_state"], "controller_action_ready")
        self.assertIn(action_id, standby["controller_action_ledger"]["pending_action_ids"])
        self.assertFalse(standby["controller_must_continue_standby"])
        self.assertTrue(standby["controller_must_process_pending_action_before_exit"])
        self.assertFalse(standby["foreground_exit_allowed"])
        self.assertFalse(standby["controller_stop_allowed"])
        self.assertEqual(standby["foreground_required_mode"], "process_controller_action")
        self.assertTrue(standby["exit_policy"]["controller_action_ready_blocks_foreground_exit"])

    def test_controller_patrol_timer_wakes_on_controller_action_ledger(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        result = router.run_router_daemon(root, max_ticks=1, release_lock_on_exit=False)
        action_id = result["ticks"][0]["controller_action_id"]

        patrol = router.controller_patrol_timer(root, seconds=0)

        self.assertEqual(patrol["patrol_result"], "new_controller_work")
        self.assertEqual(patrol["foreground_required_mode"], "process_controller_action")
        self.assertIn("process ready Controller rows", patrol["controller_instruction"])
        self.assertIn(action_id, patrol["standby_snapshot"]["controller_action_ledger"]["pending_action_ids"])

    def test_controller_patrol_timer_allows_terminal_return_only_when_stopped(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        state["status"] = "completed"
        state["pending_action"] = None
        state["daemon_mode_enabled"] = True
        router.save_run_state(run_root, state)

        patrol = router.controller_patrol_timer(root, seconds=0)

        self.assertEqual(patrol["patrol_result"], "terminal_return")
        self.assertTrue(patrol["controller_stop_allowed"])
        self.assertEqual(patrol["completion_allowed_only_when"], "terminal_return_and_controller_stop_allowed_true")

    def test_foreground_controller_standby_requests_liveness_check_on_stale_or_missing_daemon(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        router.stop_router_daemon(root, reason="test_standby_missing_daemon")

        standby = router.foreground_controller_standby(root, max_seconds=5, poll_seconds=0.01)

        self.assertEqual(standby["standby_state"], "daemon_liveness_check_required")
        self.assertFalse(standby["router_daemon"]["daemon_live"])
        self.assertFalse(standby["controller_must_continue_standby"])
        self.assertFalse(standby["foreground_exit_allowed"])
        self.assertFalse(standby["controller_stop_allowed"])
        self.assertTrue(standby["foreground_turn_return_allowed"])
        self.assertEqual(standby["foreground_required_mode"], "check_liveness")
        self.assertEqual(standby["router_daemon"]["heartbeat_status"], "check_liveness")
        self.assertFalse(standby["router_daemon"]["monitor_can_decide_recovery"])

    def test_foreground_controller_standby_does_not_compute_router_next(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        wait_action = self.force_startup_fact_role_wait(root)
        self.assertEqual(wait_action["action_type"], "await_role_decision")

        with mock.patch.object(router, "compute_controller_action", side_effect=AssertionError("standby must not drive Router")):
            standby = router.foreground_controller_standby(root, max_seconds=0, poll_seconds=0.01, bounded_diagnostic=True)

        self.assertEqual(standby["standby_state"], "timeout_still_waiting")
        self.assertEqual(standby["diagnostic_router_reentry_commands"], ["next", "run-until-wait"])

    def test_router_daemon_tick_consumes_card_ack_without_manual_next(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        while True:
            action = self.next_after_display_sync(root)
            if action["action_type"] in {
                "confirm_controller_core_boundary",
                "check_prompt_manifest",
                "write_startup_mechanical_audit",
                "write_display_surface_status",
            }:
                router.apply_action(root, str(action["action_type"]), self.payload_for_action(action))
                continue
            self.assertIn(action["action_type"], {"deliver_system_card", "deliver_system_card_bundle"})
            break

        self.submit_system_card_ack_without_router_next(root, action)
        before = read_json(router.run_state_path(run_root))
        self.assertEqual(before["pending_action"]["action_type"], action["action_type"])

        result = router.run_router_daemon(root, max_ticks=1, release_lock_on_exit=True)

        self.assertEqual(result["tick_count"], 1)
        after = read_json(router.run_state_path(run_root))
        labels = [item["label"] for item in after["history"] if isinstance(item, dict)]
        self.assertTrue(
            {
                "router_auto_consumed_card_return_ack",
                "router_return_settlement_cleared_pending_card_bundle_wait",
            }
            & set(labels)
        )
        self.assertNotEqual((after.get("pending_action") or {}).get("action_id"), action.get("action_id"))

    def test_router_daemon_invalid_card_ack_variants_do_not_advance(self) -> None:
        variants = {
            "wrong_role": lambda ack: ack.update({"role_key": "project_manager"}),
            "wrong_hash": lambda ack: ack.update({"card_envelope_hash": "0" * 64}),
        }
        for variant, mutate in variants.items():
            with self.subTest(variant=variant):
                root = self.make_project()
                run_root = self.boot_to_controller(root)
                self.release_startup_daemon_for_explicit_daemon_test(root)
                action = self.deliver_startup_fact_check_card_without_ack(root)
                open_result = card_runtime.open_card(
                    root,
                    envelope_path=str(action["card_envelope_path"]),
                    role=str(action["to_role"]),
                    agent_id=str(action["target_agent_id"]),
                )
                card_runtime.submit_card_ack(
                    root,
                    envelope_path=str(action["card_envelope_path"]),
                    role=str(action["to_role"]),
                    agent_id=str(action["target_agent_id"]),
                    receipt_paths=[str(open_result["read_receipt_path"])],
                )
                ack_path = root / action["expected_return_path"]
                ack = read_json(ack_path)
                mutate(ack)
                ack["ack_hash"] = card_runtime.stable_json_hash(ack)
                router.write_json(ack_path, ack)

                result = router.run_router_daemon(root, max_ticks=1, release_lock_on_exit=True)

                self.assertEqual(result["ticks"][0]["action_type"], "check_card_return_event")
                state = read_json(router.run_state_path(run_root))
                self.assertFalse(state["flags"]["startup_fact_reported"])
                self.assertEqual(state["pending_action"]["action_type"], "check_card_return_event")
                labels = [item["label"] for item in state["history"] if isinstance(item, dict)]
                self.assertIn("router_deferred_invalid_card_ack_to_explicit_check", labels)
                return_ledger = read_json(run_root / "return_event_ledger.json")
                self.assertNotEqual(return_ledger["pending_returns"][0].get("status"), "resolved")

    def test_router_daemon_incomplete_bundle_ack_waits_without_advancing(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        self.apply_startup_heartbeat_if_requested(root)
        action = self.next_after_display_sync(root)
        while action["action_type"] in {
            "confirm_controller_core_boundary",
            "write_startup_mechanical_audit",
            "write_display_surface_status",
        }:
            router.apply_action(root, str(action["action_type"]), self.payload_for_action(action))
            action = self.next_after_display_sync(root)
        self.assertIn("check_prompt_manifest", self.router_internal_action_types(root))
        self.assertEqual(action["action_type"], "deliver_system_card_bundle")

        role = str(action["to_role"])
        agent_id = str(action["target_agent_id"])
        opened = card_runtime.open_card_bundle(
            root,
            envelope_path=str(action["card_bundle_envelope_path"]),
            role=role,
            agent_id=agent_id,
        )
        envelope = read_json(root / action["card_bundle_envelope_path"])
        receipt_refs = []
        for receipt_path in opened["read_receipt_paths"][:-1]:
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

        result = router.run_router_daemon(root, max_ticks=1, release_lock_on_exit=True)

        self.assertEqual(result["ticks"][0]["action_type"], "await_card_bundle_return_event")
        state = read_json(router.run_state_path(run_root))
        self.assertEqual(state["pending_action"]["action_type"], "await_card_bundle_return_event")
        self.assertTrue(state["pending_action"]["bundle_ack_incomplete"])
        self.assertEqual(state["pending_action"]["missing_card_ids"], [opened["cards"][-1]["card_id"]])
        return_ledger = read_json(run_root / "return_event_ledger.json")
        bundle_pending = [
            item
            for item in return_ledger["pending_returns"]
            if isinstance(item, dict) and item.get("return_kind") == "system_card_bundle"
        ][0]
        self.assertEqual(bundle_pending["status"], "bundle_ack_incomplete")

    def test_router_daemon_duplicate_stale_card_ack_is_idempotent(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        action = self.deliver_startup_fact_check_card_without_ack(root)
        self.submit_system_card_ack_without_router_next(root, action)

        router.run_router_daemon(root, max_ticks=1, release_lock_on_exit=True)
        router.run_router_daemon(root, max_ticks=1, release_lock_on_exit=True)

        return_ledger = read_json(run_root / "return_event_ledger.json")
        completed = [
            item
            for item in return_ledger["completed_returns"]
            if item.get("delivery_attempt_id") == action["delivery_attempt_id"]
        ]
        self.assertEqual(len(completed), 1)

    def test_startup_intake_cancel_is_terminal_after_daemon_first_shell(self) -> None:
        root = self.make_project()
        router.run_until_wait(root, new_invocation=True)
        payload = self.startup_intake_payload(root, status="cancelled")
        result = router.apply_action(root, "open_startup_intake_ui", payload)
        self.assertEqual(result["startup_intake"]["status"], "cancelled")
        bootstrap = self.bootstrap_state(root)
        self.assertEqual(bootstrap["status"], "startup_cancelled")
        self.assertEqual(bootstrap["startup_state"], "startup_cancelled")
        self.assertTrue(bootstrap["flags"]["run_shell_created"])
        self.assertTrue(bootstrap["flags"]["router_daemon_started"])
        self.assertTrue((root / bootstrap["run_root"] / "run.json").exists())
        self.assertTrue((root / bootstrap["run_root"] / "router_state.json").exists())
        run_state = read_json(router.run_state_path(self.run_root_for(root)))
        self.assertFalse(run_state["flags"]["controller_core_loaded"])
        self.assertFalse(bootstrap["flags"]["roles_started"])
        self.assertFalse(run_state["flags"]["continuation_binding_recorded"])
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "startup_cancelled")
        self.assertTrue(action["terminal"])

    def test_startup_intake_rejects_body_hash_mismatch(self) -> None:
        root = self.make_project()
        router.run_until_wait(root, new_invocation=True)
        payload = self.startup_intake_payload(root)
        result_path = root / payload["startup_intake_result"]["result_path"]
        result = read_json(result_path)
        (root / result["body_path"]).write_text("changed after receipt", encoding="utf-8")
        with self.assertRaisesRegex(router.RouterError, "body hash mismatch"):
            router.apply_action(root, "open_startup_intake_ui", payload)

    def test_startup_intake_rejects_body_text_in_controller_payload(self) -> None:
        root = self.make_project()
        router.run_until_wait(root, new_invocation=True)
        payload = self.startup_intake_payload(root)
        result_path = root / payload["startup_intake_result"]["result_path"]
        result = read_json(result_path)
        result["body_text"] = USER_REQUEST["text"]
        result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(router.RouterError, "forbidden body text fields"):
            router.apply_action(root, "open_startup_intake_ui", payload)

    def test_startup_intake_rejects_headless_confirmed_result(self) -> None:
        root = self.make_project()
        router.run_until_wait(root, new_invocation=True)
        payload = self.startup_intake_payload(
            root,
            launch_mode="headless",
            headless=True,
            formal_startup_allowed=False,
        )
        with self.assertRaisesRegex(router.RouterError, "native interactive startup intake UI"):
            router.apply_action(root, "open_startup_intake_ui", payload)

    def test_startup_sequence_creates_prompt_isolated_run(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        bootstrap = self.bootstrap_state(root)
        self.assertTrue(bootstrap["router_loaded"])
        self.assertEqual(bootstrap["bootstrap_scope"], "run_scoped")
        self.assertEqual(root / bootstrap["run_root"], run_root)
        self.assertGreaterEqual(bootstrap["bootloader_actions"], 6)
        self.assertGreaterEqual(bootstrap["router_action_requests"], 8)
        self.assertIsNone(bootstrap["pending_action"])
        self.assertEqual(bootstrap["startup_answers"], STARTUP_ANSWERS)
        self.assertEqual(bootstrap["user_request"]["schema_version"], router.USER_REQUEST_REF_SCHEMA)
        self.assertFalse(bootstrap["user_request"]["controller_may_read_body"])
        self.assertTrue(bootstrap["flags"]["role_core_prompts_injected"])
        self.assertTrue(bootstrap["flags"]["router_daemon_started"])

        self.assertTrue((run_root / "runtime_kit" / "manifest.json").exists())
        self.assertTrue((run_root / "packet_ledger.json").exists())
        self.assertTrue((run_root / "execution_frontier.json").exists())
        self.assertEqual(len(list((run_root / "crew_memory").glob("*.json"))), 6)
        self.assertTrue((run_root / "user_request.json").exists())
        user_request_record = read_json(run_root / "user_request.json")
        self.assertNotIn(USER_REQUEST["text"], json.dumps(user_request_record))
        self.assertEqual(user_request_record["source"], "startup_intake_ui")
        self.assertTrue((run_root / "startup_intake" / "startup_intake_record.json").exists())
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

        controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        startup_rows = {
            row["action_type"]: row
            for row in controller_ledger["actions"]
            if row.get("scope_kind") == "startup"
        }
        self.assertEqual(
            {"emit_startup_banner", "load_controller_core", "start_role_slots", "open_startup_intake_ui"},
            set(startup_rows),
        )
        self.assertEqual(
            {row["router_reconciliation_status"] for row in startup_rows.values()},
            {"reconciled"},
        )

    def test_display_plan_is_controller_synced_projection_from_pm_plan(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "sync_display_plan")
        self.assertEqual(action["display_kind"], "startup_waiting_state")
        self.assertIsNone(action.get("postcondition"))
        self.assertIsNone(action["next_step_contract"]["postcondition"])
        self.assertFalse(action["display_required"])
        self.assertFalse(action["requires_user_dialog_display_confirmation"])
        self.assertTrue(action["user_visible_display_suppressed"])
        self.assertEqual(action["internal_display_reason"], "waiting_for_pm_route_before_canonical_route")
        self.assertIn("internal waiting-for-PM-route placeholder", action["summary"])
        self.assertIn("no user-dialog route map is required", action["summary"])
        self.assertNotIn("Display the route map in the user dialog", action["summary"])
        self.assertNotIn("display_text", action)
        self.assertNotIn("payload_template", action)
        policy = action["controller_user_reporting_policy"]
        self.assertEqual(policy["schema_version"], router.CONTROLLER_USER_REPORTING_POLICY_SCHEMA)
        self.assertTrue(policy["plain_language_required"])
        self.assertIn("plain language", policy["reminder"])
        self.assertEqual(action["next_step_contract"]["controller_user_reporting_policy"], policy)
        self.assertEqual(action["native_plan_projection"]["items"][0]["id"], "await_pm_route")
        result = router.apply_action(root, "sync_display_plan", self.payload_for_action(action))
        self.assertEqual(result["host_action"], "replace_visible_plan")
        self.assertEqual(result["display_kind"], "startup_waiting_state")
        self.assertFalse(result["display_required"])
        self.assertTrue(result["user_visible_display_suppressed"])
        self.assertNotIn("display_text", result)
        self.assertNotIn("user_dialog_display_confirmation", result)
        self.assertFalse((run_root / "display" / "user_dialog_display_ledger.json").exists())
        waiting_plan = read_json(run_root / "display_plan.json")
        self.assertEqual(waiting_plan["source_role"], "controller")
        self.assertEqual(waiting_plan["route_authority"], "none_until_pm_display_plan")
        visible_sync = read_json(router.run_state_path(run_root))["visible_plan_sync"]
        self.assertFalse(visible_sync["display_required"])
        self.assertTrue(visible_sync["user_visible_display_suppressed"])
        self.assertNotIn("user_dialog_display_confirmation", visible_sync)
        self.assertTrue(read_json(router.run_state_path(run_root))["flags"]["visible_plan_synced"])
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
        self.assertIsNone(action.get("postcondition"))
        self.assertIsNone(action["next_step_contract"]["postcondition"])
        self.assertEqual(action["native_plan_projection"]["items"][0]["status"], "in_progress")
        self.assertEqual(action["display_kind"], "route_map")
        self.assertEqual(action["display_text_format"], "markdown_mermaid")
        self.assertTrue(action["route_sign_display_required"])
        self.assertIn(action["route_sign_source_kind"], {"flow_json", "route_state_snapshot"})
        self.assertNotEqual(action["route_sign_source_kind"], "flow_draft")
        self.assertIn("Display the canonical FlowPilot Route Sign", action["summary"])
        self.assertIn("committed route state", action["summary"])
        self.assertIn("# FlowPilot Route Sign", action["display_text"])
        self.assertIn("```mermaid", action["display_text"])
        self.assertIn("route=route-001", action["display_text"])
        self.assertIn("class n01 active;", action["display_text"])
        self.assertNotIn("Now: node-001", action["display_text"])
        self.assertNotIn("- node-001 - in_progress", action["display_text"])
        self.assertNotIn(action["controller_user_reporting_policy"]["reminder"], action["display_text"])
        self.assertTrue(action["current_status_summary_exists"])
        self.assertTrue(action["router_daemon_status_exists"])
        self.assertEqual(action["user_visible_status_source"]["status_summary_source"], "current_status_summary")
        self.assertEqual(action["user_visible_status_source"]["daemon_status_source"], "router_daemon_status")
        self.assertTrue(action["user_visible_status_source"]["controller_must_show_status_from_current_status_summary"])
        self.assertEqual(
            action["next_step_contract"]["controller_user_reporting_policy"],
            action["controller_user_reporting_policy"],
        )
        status_summary = read_json(run_root / "display" / "current_status_summary.json")
        progress = status_summary["progress_summary"]
        self.assertEqual(progress["schema_version"], "flowpilot.progress_summary.v1")
        self.assertEqual(progress["state"], status_summary["state_kind"])
        self.assertEqual(progress["level_count"], 1)
        self.assertEqual(progress["overall_total_nodes"], 1)
        self.assertEqual(progress["overall_completed_nodes"], 0)
        self.assertEqual(progress["levels"][0]["level"], 1)
        self.assertEqual(progress["levels"][0]["total_nodes"], 1)
        self.assertEqual(progress["levels"][0]["completed_nodes"], 0)
        self.assertEqual(progress["levels"][0]["current_index"], 1)
        self.assertEqual(progress["levels"][0]["current_node_id"], "node-001")
        self.assertTrue(progress["metadata_only"])
        self.assertTrue(progress["sealed_body_fields_excluded"])
        self.assertTrue(progress["diagnostic_paths_excluded"])
        self.assertTrue(progress["hash_fields_excluded"])
        self.assertTrue(progress["elapsed_seconds"] is None or progress["elapsed_seconds"] >= 0)
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
        self.assertTrue(read_json(router.run_state_path(run_root))["flags"]["visible_plan_synced"])
        active_snapshot = read_json(run_root / "route_state_snapshot.json")
        self.assertEqual(active_snapshot["route"]["nodes"][0]["id"], "node-001")
        self.assertTrue(active_snapshot["route"]["nodes"][0]["is_active"])
        self.assertEqual(active_snapshot["authority"]["stale_running_index_entries"], [])
        self.assertEqual(
            active_snapshot["authority"]["background_running_index_entries"],
            [{"focus_selected": False, "run_id": "run-stale", "run_root": ".flowpilot/runs/run-stale", "status": "running"}],
        )
        self.assertEqual(active_snapshot["active_ui_task_catalog"]["hidden_non_current_running_index_entries"], [])
        self.assertEqual(
            [item["run_id"] for item in active_snapshot["active_ui_task_catalog"]["background_active_tasks"]],
            ["run-stale"],
        )
        index_after = read_json(index_path)
        stale_entry = next(item for item in index_after["runs"] if item["run_id"] == "run-stale")
        self.assertEqual(stale_entry["status"], "running")
        self.assertNotIn("stale_reason", stale_entry)

        self.deliver_current_node_cards(root)
        node_plan = read_json(run_root / "display_plan.json")
        self.assertEqual(node_plan["source_event"], "pm_writes_node_acceptance_plan")
        self.assertEqual(node_plan["current_node"]["checklist"][0]["id"], "node-001-req")

    def test_run_until_wait_folds_nonblocking_display_sync(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        first = router.next_action(root)
        self.assertEqual(first["action_type"], "sync_display_plan")
        self.assertFalse(first["requires_user_dialog_display_confirmation"])
        self.assertIsNone(first.get("postcondition"))

        result = router.run_until_wait(root, max_steps=3)

        self.assertEqual(result["folded_command"], "run-until-wait")
        self.assertGreaterEqual(result["folded_applied_count"], 1)
        self.assertEqual(result["folded_applied_actions"][0]["action_type"], "sync_display_plan")
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["visible_plan_synced"])
        self.assertIn("visible_plan_sync", state)

    def test_progress_summary_counts_nested_active_path(self) -> None:
        root = self.make_project()
        run_root = root / ".flowpilot" / "runs" / "run-progress"
        run_root.mkdir(parents=True)
        route = {
            "route_id": "route-progress",
            "nodes": [
                {
                    "node_id": "route-root",
                    "node_kind": "root",
                    "depth": 0,
                    "child_node_ids": ["parent-done", "parent-current"],
                },
                {"node_id": "parent-done", "title": "Finished parent", "status": "completed"},
                {
                    "node_id": "parent-current",
                    "title": "Current parent",
                    "child_node_ids": ["child-done", "child-current"],
                },
                {
                    "node_id": "child-done",
                    "parent_node_id": "parent-current",
                    "title": "Finished child",
                    "status": "completed",
                },
                {
                    "node_id": "child-current",
                    "parent_node_id": "parent-current",
                    "title": "Current child",
                    "child_node_ids": ["leaf-done", "leaf-current"],
                },
                {
                    "node_id": "leaf-done",
                    "parent_node_id": "child-current",
                    "title": "Finished leaf",
                    "status": "completed",
                },
                {"node_id": "leaf-current", "parent_node_id": "child-current", "title": "Current leaf"},
            ],
        }
        progress = router._build_progress_summary(  # type: ignore[attr-defined]
            run_root,
            {"run_id": "run-progress"},
            route=route,
            frontier={"completed_nodes": ["parent-done", "child-done", "leaf-done"]},
            active_node_id="leaf-current",
            state_kind="running",
        )

        self.assertEqual(progress["level_count"], 3)
        self.assertEqual(progress["overall_total_nodes"], 6)
        self.assertEqual(progress["overall_completed_nodes"], 3)
        self.assertEqual([level["current_index"] for level in progress["levels"]], [2, 2, 2])
        self.assertEqual([level["total_nodes"] for level in progress["levels"]], [2, 2, 2])
        self.assertEqual([level["completed_nodes"] for level in progress["levels"]], [1, 1, 1])
        self.assertEqual([level["current_label"] for level in progress["levels"]], [
            "Current parent",
            "Current child",
            "Current leaf",
        ])
        self.assertIsNone(progress["elapsed_seconds"])
        self.assertTrue(progress["metadata_only"])
        self.assertTrue(progress["sealed_body_fields_excluded"])
        self.assertTrue(progress["diagnostic_paths_excluded"])

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
        with self.assertRaisesRegex(router.RouterError, "product_behavior_model_checked=true"):
            router.record_external_event(
                root,
                "process_officer_passes_route_check",
                self.role_report_envelope(
                    root,
                    "flowguard/route_process_check_missing_product_coverage",
                    {
                        "reviewed_by_role": "process_flowguard_officer",
                        "passed": True,
                        "process_viability_verdict": "pass",
                        "repair_return_policy_checked": True,
                        "serial_execution_model_checked": True,
                        "all_effective_nodes_reachable_in_order": True,
                        "recursive_child_routes_serialized": True,
                    },
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

    def test_startup_waits_for_answers_before_banner_or_controller(self) -> None:
        root = self.make_project()

        action = router.run_until_wait(root, new_invocation=True)
        self.assertEqual(action["action_type"], "open_startup_intake_ui")
        self.assertTrue(action["apply_required"])
        self.assertTrue(action["next_step_contract"]["apply_required"])
        self.assertNotIn("controller_completion_command", action)
        self.assertNotIn("router_pending_apply_required", action)
        self.assertTrue(action["requires_host_automation"])
        self.assertEqual(action["requires_payload"], "startup_intake_result")
        self.assertEqual(action["payload_contract"]["schema_version"], "flowpilot.payload_contract.v1")
        self.assertEqual(action["payload_contract"]["payload_key"], "startup_intake_result")
        self.assertIn("flowpilot_startup_intake.ps1", action["startup_intake_ui"]["launcher_path"])
        self.assertTrue(action["startup_intake_ui"]["body_text_is_never_router_payload"])
        self.assertIn("Router daemon status", action["plain_instruction"])
        self.assertIn("Controller action ledger", action["plain_instruction"])
        self.assertNotIn("apply this pending action", action["plain_instruction"])
        self.assertNotIn("apply its confirmed or cancelled result", action["summary"])

        with self.assertRaises(router.RouterError):
            router.apply_action(root, "emit_startup_banner")
        with self.assertRaises(router.RouterError):
            router.apply_action(root, "load_controller_core")

        bootstrap = self.bootstrap_state(root)
        self.assertEqual(bootstrap["startup_state"], "none")
        self.assertEqual(bootstrap["bootstrap_scope"], "run_scoped")
        self.assertFalse(bootstrap["flags"]["startup_state_written_awaiting_answers"])
        self.assertFalse(bootstrap["flags"]["dialog_stopped_for_answers"])
        self.assertIsNone(bootstrap["startup_answers"])
        self.assertIsNotNone(bootstrap["run_id"])
        self.assertTrue(bootstrap["flags"]["run_shell_created"])
        self.assertTrue(bootstrap["flags"]["router_daemon_started"])
        self.assertFalse(bootstrap["flags"]["controller_core_loaded"])
        self.assertFalse(bootstrap["flags"]["roles_started"])
        self.assertTrue((root / ".flowpilot" / "current.json").exists())
        self.assertTrue((root / bootstrap["run_root"] / "bootstrap" / "startup_state.json").exists())
        self.assertTrue((root / bootstrap["run_root"] / "router_state.json").exists())

    def test_startup_banner_action_and_result_are_user_visible(self) -> None:
        root = self.make_project()
        action = router.run_until_wait(root, new_invocation=True)
        self.assertEqual(action["action_type"], "open_startup_intake_ui")
        router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))

        run_root = self.run_root_for(root)
        controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        self.assertFalse(any(row["action_type"] == "emit_startup_banner" for row in controller_ledger["actions"]))
        action = router.run_until_wait(root)
        self.assertEqual(action["action_type"], "load_controller_core")
        router.apply_action(root, "load_controller_core", self.payload_for_action(action))
        controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
        banner_row = next(row for row in controller_ledger["actions"] if row["action_type"] == "emit_startup_banner")
        self.assertEqual(banner_row["status"], "pending")
        entry = read_json(run_root / "runtime" / "controller_actions" / f"{banner_row['action_id']}.json")
        action = entry["action"]
        self.assertEqual(action["action_type"], "emit_startup_banner")
        self.assert_controller_receipt_action_projection(action)
        self.assertTrue(action["display_required"])
        self.assertEqual(action["display_text_format"], "plain_text")
        self.assertFalse(action["controller_must_display_text_before_apply"])
        self.assertTrue(action["controller_must_display_text_before_receipt"])
        self.assertTrue(action["requires_user_dialog_display_confirmation"])
        self.assertEqual(action["required_render_target"], "user_dialog")
        self.assertEqual(action["requires_payload"], "display_confirmation")
        self.assertTrue(action["controller_user_reporting_policy"]["plain_language_required"])
        self.assertEqual(
            action["next_step_contract"]["controller_user_reporting_policy"],
            action["controller_user_reporting_policy"],
        )
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
        self.assertIn("Controller receipt", action["payload_template_rule"])
        self.assertNotIn("apply the action", action["payload_template_rule"])
        self.assertFalse(action["generated_files_alone_satisfy_chat_display"])
        self.assertIn("user dialog", action["controller_display_rule"])
        self.assertIn("Controller receipt", action["controller_display_rule"])
        self.assertNotIn("before applying", action["controller_display_rule"])
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
        self.assertNotIn(action["controller_user_reporting_policy"]["reminder"], action["display_text"])

        router.record_controller_action_receipt(
            root,
            action_id=banner_row["action_id"],
            status="done",
            payload=self.payload_for_action(action),
        )
        entry = read_json(run_root / "runtime" / "controller_actions" / f"{banner_row['action_id']}.json")
        self.assertEqual(entry["status"], "done")
        self.assertEqual(entry["router_reconciliation_status"], "reconciled")

    def test_user_intake_from_startup_ui_is_router_owned_and_sealed_from_controller(self) -> None:
        root = self.make_project()
        router.run_until_wait(root, new_invocation=True)
        router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))
        result = router.run_until_wait(root)
        self.assertEqual(result["action_type"], "load_controller_core")

        run_root = root / self.bootstrap_state(root)["run_root"]
        user_request_record = read_json(run_root / "user_request.json")
        self.assertNotIn(USER_REQUEST["text"], json.dumps(user_request_record))
        self.assertFalse(user_request_record["controller_may_read_body"])
        self.assertEqual(user_request_record["user_request_ref"]["schema_version"], router.USER_REQUEST_REF_SCHEMA)
        packet_envelope = read_json(run_root / "mailbox" / "outbox" / "user_intake.json")
        self.assertEqual(packet_envelope["body_visibility"], packet_runtime.SEALED_BODY_VISIBILITY)
        self.assertFalse(packet_envelope["body_access"]["controller_can_read_body"])
        packet_ledger = read_json(run_root / "packet_ledger.json")
        record = next(item for item in packet_ledger["packets"] if item["packet_id"] == "user_intake")
        self.assertEqual(packet_ledger["active_packet_holder"], "router")
        self.assertEqual(packet_ledger["active_packet_status"], "router-held-startup-material")
        self.assertEqual(record["active_packet_holder"], "router")
        self.assertEqual(record["active_packet_status"], "router-held-startup-material")
        self.assertTrue(record["router_owned_startup_material"])
        self.assertEqual(record["packet_envelope"]["to_role"], "project_manager")
        body = (run_root / "packets" / "user_intake" / "packet_body.md").read_text(encoding="utf-8")
        self.assertIn(USER_REQUEST["text"], body)
        self.assertIn("startup_intake_record_path", body)

    def test_background_agents_allow_requires_six_fresh_live_agent_records(self) -> None:
        def scheduled_role_slots_action() -> tuple[Path, Path, dict, dict]:
            root = self.make_project()
            router.run_until_wait(root, new_invocation=True)
            router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))
            result = router.run_until_wait(root)
            self.assertEqual(result["action_type"], "load_controller_core")
            run_root = self.run_root_for(root)
            controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
            row = next(item for item in controller_ledger["actions"] if item.get("action_type") == "start_role_slots")
            entry = read_json(run_root / "runtime" / "controller_actions" / f"{row['action_id']}.json")
            return root, run_root, entry["action"], row

        root, run_root, action, row = scheduled_role_slots_action()

        self.assert_controller_receipt_action_projection(action)
        self.assertTrue(action["requires_host_spawn"])
        self.assertEqual(action["payload_contract"]["name"], "role_slots_startup_receipt")
        self.assertEqual(action["spawn_policy"], "spawn_all_six_fresh_current_task_agents_before_controller_receipt")
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

        def assert_role_slots_receipt_blocked(payload_factory, expected_text: str) -> None:
            blocked_root, blocked_run_root, _, blocked_row = scheduled_role_slots_action()
            payload = payload_factory(blocked_root)
            router.record_controller_action_receipt(
                blocked_root,
                action_id=blocked_row["action_id"],
                status="done",
                payload=payload,
            )
            entry = read_json(blocked_run_root / "runtime" / "controller_actions" / f"{blocked_row['action_id']}.json")
            self.assertEqual(entry["router_reconciliation_status"], "blocked")
            self.assertIn(expected_text, json.dumps(entry["router_reconciliation_blocker"], sort_keys=True))

        assert_role_slots_receipt_blocked(lambda _: None, "role_agents")

        def missing_role_payload(blocked_root: Path) -> dict:
            payload = self.role_agent_payload(blocked_root)
            payload["role_agents"] = payload["role_agents"][:-1]
            return payload

        assert_role_slots_receipt_blocked(missing_role_payload, "missing live role agent records")

        def stale_run_payload(blocked_root: Path) -> dict:
            payload = self.role_agent_payload(blocked_root)
            payload["role_agents"][0]["spawned_for_run_id"] = "run-old"
            return payload

        assert_role_slots_receipt_blocked(stale_run_payload, "spawned_for_run_id")

        router.record_controller_action_receipt(
            root,
            action_id=row["action_id"],
            status="done",
            payload=self.role_agent_payload(root),
        )
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

    def test_legacy_startup_answer_boundary_records_answers(self) -> None:
        root = self.make_project()
        self.assertEqual(self.next_and_apply(root)["applied"], "load_router")

        self.enter_legacy_startup_answer_boundary(root)
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "record_startup_answers")
        router.apply_action(root, "record_startup_answers", {"startup_answers": STARTUP_ANSWERS})
        bootstrap = self.bootstrap_state(root)
        self.assertEqual(bootstrap["startup_answers"], STARTUP_ANSWERS)
        self.assertEqual(bootstrap["startup_state"], "answers_complete")
        self.assertEqual(router.next_action(root)["action_type"], "create_run_shell")

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

    def test_start_command_creates_fresh_run_when_current_is_running(self) -> None:
        root = self.make_project()
        old_run_root = self.write_minimal_run(root, "run-old-running", status="controller_ready")
        self.write_current_focus(root, old_run_root)
        old_state_before = read_json(router.run_state_path(old_run_root))

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = router.main(["--root", str(root), "start", "--json"])

        self.assertEqual(exit_code, 0)
        result = json.loads(stdout.getvalue())
        current = read_json(root / ".flowpilot" / "current.json")
        self.assertNotEqual(current["current_run_id"], "run-old-running")
        self.assertIn("create_run_shell", [item["action_type"] for item in result["folded_applied_actions"]])
        self.assertTrue((root / current["current_run_root"] / "run.json").exists())
        self.assertEqual(read_json(router.run_state_path(old_run_root)), old_state_before)
        self.assertFalse((old_run_root / "runtime" / "controller_action_ledger.json").exists())

    def test_new_invocation_preserves_multiple_parallel_running_runs(self) -> None:
        root = self.make_project()
        run_a = self.write_minimal_run(root, "run-a", status="controller_ready")
        run_b = self.write_minimal_run(root, "run-b", status="controller_ready")
        self.write_current_focus(root, run_b)
        router.write_json(
            root / ".flowpilot" / "index.json",
            {
                "schema_version": "flowpilot.index.v1",
                "runs": [
                    {"run_id": "run-a", "run_root": ".flowpilot/runs/run-a", "status": "running"},
                    {"run_id": "run-b", "run_root": ".flowpilot/runs/run-b", "status": "running"},
                ],
                "current_run_id": "run-b",
                "updated_at": router.utc_now(),
            },
        )
        state_a_before = read_json(router.run_state_path(run_a))
        state_b_before = read_json(router.run_state_path(run_b))

        result = router.run_until_wait(root, new_invocation=True)

        current = read_json(root / ".flowpilot" / "current.json")
        self.assertNotIn(current["current_run_id"], {"run-a", "run-b"})
        self.assertIn("create_run_shell", [item["action_type"] for item in result["folded_applied_actions"]])
        self.assertTrue((root / current["current_run_root"] / "run.json").exists())
        self.assertEqual(read_json(router.run_state_path(run_a)), state_a_before)
        self.assertEqual(read_json(router.run_state_path(run_b)), state_b_before)
        index = read_json(root / ".flowpilot" / "index.json")
        run_ids = {item["run_id"] for item in index["runs"]}
        self.assertTrue({"run-a", "run-b", current["current_run_id"]}.issubset(run_ids))
        self.assertEqual(next(item for item in index["runs"] if item["run_id"] == "run-a")["status"], "running")
        self.assertEqual(next(item for item in index["runs"] if item["run_id"] == "run-b")["status"], "running")

    def test_record_startup_answers_rejects_naked_inferred_or_invalid_values(self) -> None:
        root = self.make_project()
        self.assertEqual(self.next_and_apply(root)["applied"], "load_router")
        self.enter_legacy_startup_answer_boundary(root)
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
        self.enter_legacy_startup_answer_boundary(root)
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

        parsed = router.parse_args(["--root", "C:/tmp/project", "start", "--json"])
        self.assertEqual(parsed.command, "start")
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

        self.apply_next_non_card_action(root)
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
        self.apply_next_non_card_action(root)
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "product_officer.product_architecture_modelability")
        context = action["delivery_context"]
        self.assertEqual(context["current_stage"]["current_phase"], "product_architecture")
        self.assertIn(
            f"{run_root.relative_to(root).as_posix()}/product_function_architecture.json",
            set(context["source_paths"].values()),
        )

    def test_system_card_delivery_uses_router_internal_manifest_check(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        first = self.next_after_display_sync(root)
        self.assertEqual(first["action_type"], "write_display_surface_status")
        self.assertEqual(first["next_step_contract"]["recipient_role"], "controller")
        startup_state = read_json(run_root / "router_state.json")
        self.assertTrue(startup_state["flags"]["startup_mechanical_audit_written"])
        self.assertIn(
            "write_startup_mechanical_audit",
            [item["action_type"] for item in startup_state.get("router_internal_mechanical_events", [])],
        )
        router.apply_action(root, "write_display_surface_status", self.payload_for_action(first))

        self.complete_startup_pre_review_join(root)
        pre_reviewer_state = read_json(run_root / "router_state.json")
        pre_reviewer_delivery_count = int(pre_reviewer_state["prompt_deliveries"])
        pre_reviewer_manifest_checks = int(pre_reviewer_state["manifest_checks"])
        self.assertIn(
            "check_prompt_manifest",
            [item["action_type"] for item in pre_reviewer_state.get("router_internal_mechanical_events", [])],
        )

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
        self.assertTrue(second["controller_after_relay_policy"]["router_ready_preempts_foreground_wait"])
        self.assertFalse(second["controller_after_relay_policy"]["foreground_wait_agent_allowed"])
        self.assertFalse(second["controller_after_relay_policy"]["foreground_role_chat_wait_allowed"])
        self.assertTrue(second["next_step_contract"]["router_ready_preempts_foreground_wait"])
        self.assertTrue(second["next_step_contract"]["controller_must_scan_daemon_before_foreground_role_wait"])
        self.assertEqual(second["next_step_contract"]["normal_router_progress_source"], "router_daemon_status_and_controller_action_ledger")
        self.assertFalse(second["next_step_contract"]["foreground_wait_agent_allowed"])
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
        self.assertEqual(pre_apply_state["prompt_deliveries"], pre_reviewer_delivery_count)
        self.assertEqual(pre_apply_prompt_ledger["deliveries"][-1]["card_id"], "reviewer.startup_fact_check")
        context = second["delivery_context"]
        self.assertEqual(context["schema_version"], "flowpilot.live_card_context.v1")
        self.assertEqual(context["run_id"], run_root.name)
        self.assertEqual(context["card_id"], "reviewer.startup_fact_check")
        self.assertEqual(context["to_role"], "human_like_reviewer")
        self.assertEqual(context["current_task"]["user_request_path"], f"{run_root.relative_to(root).as_posix()}/user_request.json")
        self.assertEqual(
            context["current_task"]["startup_intake_record_path"],
            f"{run_root.relative_to(root).as_posix()}/startup_intake/startup_intake_record.json",
        )
        self.assertEqual(context["current_task"]["reviewer_live_review_source"], "startup_intake_record")
        self.assertFalse(context["current_task"]["controller_summary_is_task_authority"])
        self.assertIn("current_phase", context["current_stage"])
        self.assertIn("current_node_id", context["current_stage"])
        self.assertEqual(context["source_paths"]["execution_frontier"], f"{run_root.relative_to(root).as_posix()}/execution_frontier.json")
        self.assertEqual(context["source_paths"]["prompt_delivery_ledger"], f"{run_root.relative_to(root).as_posix()}/prompt_delivery_ledger.json")
        self.assertEqual(context["source_paths"]["display_surface"], f"{run_root.relative_to(root).as_posix()}/display/display_surface.json")
        self.assertEqual(
            context["source_paths"]["startup_intake_record_path"],
            f"{run_root.relative_to(root).as_posix()}/startup_intake/startup_intake_record.json",
        )
        self.assertTrue(second["reviewer_has_direct_display_evidence"])

        state = read_json(run_root / "router_state.json")
        prompt_ledger = read_json(run_root / "prompt_delivery_ledger.json")
        self.assertTrue(state["flags"]["reviewer_startup_fact_check_card_delivered"])
        self.assertEqual(state["manifest_checks"], pre_reviewer_manifest_checks)
        self.assertEqual(state["prompt_deliveries"], pre_reviewer_delivery_count)
        action_dir = run_root / "runtime" / "controller_actions"
        controller_action_types = [
            read_json(path).get("action_type")
            for path in sorted(action_dir.glob("*.json"))
        ] if action_dir.exists() else []
        self.assertNotIn("check_prompt_manifest", controller_action_types)
        self.assertNotIn("write_startup_mechanical_audit", controller_action_types)
        self.assertEqual(state["delivered_cards"][-1]["card_id"], "reviewer.startup_fact_check")
        self.assertEqual(state["delivered_cards"][-1]["delivery_context"]["card_id"], "reviewer.startup_fact_check")
        self.assertEqual(prompt_ledger["deliveries"][-1]["delivery_context"]["card_id"], "reviewer.startup_fact_check")
        self.assertEqual(second["delivery_mode"], "envelope_only_v2")
        self.assertEqual(second["controller_visibility"], "system_card_envelope_only")
        self.assertFalse(second["sealed_body_reads_allowed"])
        self.assertNotIn(second["body_path"], second["allowed_reads"])
        self.assertEqual(second["role_io_protocol_hash"], read_json(run_root / "role_io_protocol_ledger.json")["protocol_hash"])
        self.assertTrue((root / second["role_io_protocol_receipt_path"]).exists())
        self.assertTrue((root / second["card_envelope_path"]).exists())
        card_ledger = read_json(run_root / "card_ledger.json")
        return_ledger = read_json(run_root / "return_event_ledger.json")
        self.assertEqual(card_ledger["deliveries"][-1]["card_id"], "reviewer.startup_fact_check")
        self.assertEqual(card_ledger["deliveries"][-1]["role_io_protocol_receipt_hash"], second["role_io_protocol_receipt_hash"])
        reviewer_pending = [
            item
            for item in return_ledger["pending_returns"]
            if item.get("delivery_attempt_id") == second.get("delivery_attempt_id")
        ][0]
        self.assertEqual(reviewer_pending["card_return_event"], "reviewer_card_ack")
        self.assertNotIn("return_event", reviewer_pending)

        with self.assertRaisesRegex(router.RouterError, "relay-only"):
            router.apply_action(root, "deliver_system_card")
        relay_action = self.next_after_display_sync(root)
        self.assertEqual(relay_action["action_type"], "deliver_system_card")
        self.assertEqual(relay_action["card_envelope_path"], second["card_envelope_path"])
        self.assertTrue(relay_action["relay_allowed"])
        self.assertTrue(relay_action["controller_after_relay_policy"]["router_ready_preempts_foreground_wait"])
        self.assertFalse(relay_action["controller_after_relay_policy"]["foreground_role_chat_wait_allowed"])
        blocked_report = router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(
                root,
                "startup/reviewer_startup_fact_report_before_card_ack",
                self.startup_fact_report_body(root),
            ),
        )
        self.assertFalse(blocked_report["ok"])
        self.assertTrue(blocked_report["report_quarantined"])
        self.assertTrue(blocked_report["recoverable"])
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
        reviewer_pending = [
            item
            for item in return_ledger["pending_returns"]
            if item.get("delivery_attempt_id") == second.get("delivery_attempt_id")
        ][0]
        self.assertEqual(reviewer_pending["status"], "resolved")

    def test_committed_system_card_relay_can_resolve_without_apply_roundtrip(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "write_display_surface_status")
        self.assertIn("write_startup_mechanical_audit", self.router_internal_action_types(root))
        router.apply_action(root, "write_display_surface_status", self.payload_for_action(action))

        self.complete_startup_pre_review_join(root)

        action = self.next_after_display_sync(root)
        self.assertIn("check_prompt_manifest", self.router_internal_action_types(root))
        self.assertEqual(action["action_type"], "deliver_system_card")
        self.assertEqual(action["card_id"], "reviewer.startup_fact_check")
        self.assertTrue(action["artifact_committed"])
        self.assertTrue(action["relay_allowed"])
        self.assertTrue(action["controller_after_relay_policy"]["router_ready_preempts_foreground_wait"])
        self.assertEqual(action["controller_after_relay_policy"]["allowed_router_reentry_commands"], [])
        self.assertEqual(action["controller_after_relay_policy"]["diagnostic_router_reentry_commands"], ["next", "run-until-wait"])
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
        reviewer_pending = [
            item
            for item in return_ledger["pending_returns"]
            if item.get("delivery_attempt_id") == action.get("delivery_attempt_id")
        ][0]
        self.assertEqual(reviewer_pending["status"], "resolved")
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
        reviewer_pending = [
            item
            for item in return_ledger["pending_returns"]
            if item.get("delivery_attempt_id") == action.get("delivery_attempt_id")
        ][0]
        self.assertEqual(reviewer_pending["status"], "resolved")
        self.assertEqual(reviewer_pending["terminal_replay_ack"]["count"], 1)
        self.assertIsNone(
            router._pending_card_return_blocker_for_event(
                run_root,
                run_root.name,
                "pm_issues_material_and_capability_scan_packets",
                read_json(router.run_state_path(run_root)),
            )
        )

    def test_record_external_event_preconsumes_valid_card_ack_before_blocking(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        action = self.deliver_startup_fact_check_card_without_ack(root)
        open_result = card_runtime.open_card(
            root,
            envelope_path=str(action["card_envelope_path"]),
            role=str(action["to_role"]),
            agent_id=str(action["target_agent_id"]),
        )
        card_runtime.submit_card_ack(
            root,
            envelope_path=str(action["card_envelope_path"]),
            role=str(action["to_role"]),
            agent_id=str(action["target_agent_id"]),
            receipt_paths=[str(open_result["read_receipt_path"])],
        )

        result = router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(
                root,
                "startup/reviewer_startup_fact_report",
                self.startup_fact_report_body(root),
            ),
        )

        self.assertTrue(result["ok"])
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["startup_fact_reported"])
        self.assertIn(
            "router_pre_consumed_card_return_ack_before_external_event",
            [item.get("label") for item in state["history"] if isinstance(item, dict)],
        )
        return_ledger = read_json(run_root / "return_event_ledger.json")
        pending = return_ledger["pending_returns"][0]
        self.assertEqual(pending["status"], "resolved")
        completed = [
            item for item in return_ledger["completed_returns"]
            if item.get("delivery_attempt_id") == action.get("delivery_attempt_id")
        ]
        self.assertEqual(len(completed), 1)

    def test_reviewer_startup_report_preconsumes_pre_review_pm_bundle_ack(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        self.apply_startup_heartbeat_if_requested(root)
        action = self.next_after_display_sync(root)
        while action["action_type"] in {
            "confirm_controller_core_boundary",
            "check_prompt_manifest",
            "write_startup_mechanical_audit",
            "write_display_surface_status",
        }:
            router.apply_action(root, str(action["action_type"]), self.payload_for_action(action))
            action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "deliver_system_card_bundle")
        self.assertIn("pm.core", action["card_ids"])

        opened = card_runtime.open_card_bundle(
            root,
            envelope_path=str(action["card_bundle_envelope_path"]),
            role=str(action["to_role"]),
            agent_id=str(action["target_agent_id"]),
        )
        card_runtime.submit_card_bundle_ack(
            root,
            envelope_path=str(action["card_bundle_envelope_path"]),
            role=str(action["to_role"]),
            agent_id=str(action["target_agent_id"]),
            receipt_paths=[str(path) for path in opened["read_receipt_paths"]],
        )
        self.deliver_expected_card(root, "reviewer.startup_fact_check")

        envelope = self.role_report_envelope(
            root,
            "startup/reviewer_startup_fact_report",
            self.startup_fact_report_body(root),
        )
        result = router.record_external_event(root, "reviewer_reports_startup_facts", envelope)
        self.assertTrue(result["ok"])

        return_ledger = read_json(run_root / "return_event_ledger.json")
        bundle_completed = [
            item for item in return_ledger["completed_returns"]
            if item.get("return_kind") == "system_card_bundle"
            and item.get("card_bundle_id") == action.get("card_bundle_id")
        ]
        self.assertEqual(len(bundle_completed), 1)
        bundle_pending = [
            item for item in return_ledger["pending_returns"]
            if item.get("return_kind") == "system_card_bundle"
            and item.get("card_bundle_id") == action.get("card_bundle_id")
        ][0]
        self.assertIn(bundle_pending["status"], {"returned", "resolved"})
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["startup_fact_reported"])

        duplicate = router.record_external_event(root, "reviewer_reports_startup_facts", envelope)
        self.assertTrue(duplicate["already_recorded"])
        return_ledger = read_json(run_root / "return_event_ledger.json")
        bundle_completed = [
            item for item in return_ledger["completed_returns"]
            if item.get("return_kind") == "system_card_bundle"
            and item.get("card_bundle_id") == action.get("card_bundle_id")
        ]
        self.assertEqual(len(bundle_completed), 1)

    def test_startup_pre_review_ack_join_blocks_reviewer_card(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        self.apply_startup_heartbeat_if_requested(root)
        action = self.next_after_display_sync(root)
        while action["action_type"] in {
            "confirm_controller_core_boundary",
            "check_prompt_manifest",
            "write_startup_mechanical_audit",
            "write_display_surface_status",
        }:
            router.apply_action(root, str(action["action_type"]), self.payload_for_action(action))
            action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "deliver_system_card_bundle")
        self.assertIn("pm.core", action["card_ids"])
        self.mark_controller_action_done(root, action, {"delivery_relayed": True})

        next_action = self.next_after_display_sync(root)
        self.assertEqual(next_action["action_type"], "await_card_bundle_return_event")
        self.assertEqual(next_action["ack_clearance_reason"], "current_scope_pre_review_reconciliation")
        self.assertEqual(next_action["scope_kind"], "startup")

        return_ledger = read_json(run_root / "return_event_ledger.json")
        pm_pending = [
            item
            for item in return_ledger["pending_returns"]
            if item.get("return_kind") == "system_card_bundle"
            and "pm.core" in item.get("card_ids", [])
        ]
        self.assertEqual(len(pm_pending), 1)
        self.assertEqual(pm_pending[0]["status"], "pending")
        self.assertNotEqual(next_action.get("card_id"), "reviewer.startup_fact_check")

    def test_pm_startup_activation_uses_existing_same_role_card_ack_blocker(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        self.deliver_startup_fact_check_card(root)
        self.deliver_initial_pm_cards_and_user_intake(root)
        report = router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(
                root,
                "startup/reviewer_startup_fact_report_with_pm_ack_pending",
                self.startup_fact_report_body(root),
            ),
        )
        self.assertTrue(report["ok"])

        action = self.next_after_display_sync(root)
        if action["action_type"] == "check_prompt_manifest":
            self.assertEqual(action["next_card_id"], "pm.startup_activation")
            router.apply_action(root, "check_prompt_manifest")
            action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "deliver_system_card")
        self.assertEqual(action["card_id"], "pm.startup_activation")
        self.mark_controller_action_done(root, action, {"delivery_relayed": True})

        result = router.record_external_event(
            root,
            "pm_approves_startup_activation",
            self.role_decision_envelope(
                root,
                "startup/pm_startup_activation_before_card_ack",
                {"approved_by_role": "project_manager", "decision": "approved"},
            ),
        )

        self.assertFalse(result["ok"])
        self.assertTrue(result["report_quarantined"])
        self.assertTrue(result["recoverable"])
        self.assertEqual(result["next_required_action"]["action_type"], "await_card_return_event")
        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"]["startup_activation_approved"])
        self.assertEqual(state["pending_action"]["ack_clearance_reason"], "router_progress")
        self.assertEqual(state["pending_action"]["card_id"], "pm.startup_activation")

    def test_record_external_event_quarantines_missing_same_role_ack_report(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        action = self.deliver_startup_fact_check_card_without_ack(root)
        result = router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(
                root,
                "startup/reviewer_startup_fact_report_pre_ack",
                self.startup_fact_report_body(root),
            ),
        )

        self.assertFalse(result["ok"])
        self.assertTrue(result["report_quarantined"])
        self.assertTrue(result["recoverable"])
        quarantine_path = root / result["quarantine_path"]
        self.assertTrue(quarantine_path.exists())
        quarantine = read_json(quarantine_path)
        self.assertEqual(quarantine["status"], "quarantined_audit_only")
        self.assertFalse(quarantine["recovery"]["old_report_may_be_used_as_acceptance_evidence"])
        self.assertEqual(quarantine["pending_return"]["delivery_attempt_id"], action["delivery_attempt_id"])
        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"]["startup_fact_reported"])
        self.assertIsNone(state.get("active_control_blocker"))
        self.assertEqual(state["pending_action"]["action_type"], "await_card_return_event")
        self.assertEqual(state["quarantined_role_reports"][0]["quarantine_path"], result["quarantine_path"])
        self.assertIn(
            "router_quarantined_pre_ack_role_report_for_same_role_ack_recovery",
            [item.get("label") for item in state["history"] if isinstance(item, dict)],
        )

    def test_missing_system_card_ack_wait_reminds_original_envelope_without_duplicate_delivery(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        action = self.deliver_startup_fact_check_card_without_ack(root)
        result = router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(
                root,
                "startup/reviewer_startup_fact_report_pre_ack_reminder",
                self.startup_fact_report_body(root),
            ),
        )

        self.assertFalse(result["ok"])
        state = read_json(router.run_state_path(run_root))
        wait = state["pending_action"]
        self.assertEqual(wait["action_type"], "await_card_return_event")
        self.assertEqual(wait["missing_ack_recovery"], "remind_target_role_to_ack_original_committed_card")
        self.assertEqual(wait["reminder_target"], "original_committed_card")
        self.assertFalse(wait["duplicate_system_card_delivery_allowed"])
        self.assertTrue(wait["reissue_allowed_only_if_original_invalid_lost_stale_or_role_replaced"])
        self.assertEqual(wait["original_envelope_path"], action["card_envelope_path"])
        self.assertEqual(wait["original_expected_return_path"], action["expected_return_path"])
        self.assertTrue(wait["target_role_ack_reminder_allowed"])
        self.assertEqual(wait["controller_delivery_fact"]["controller_delivery_fact_status"], "controller_delivery_fact_unrecorded")
        self.assertTrue(wait["ack_is_read_receipt_only"])
        self.assertTrue(wait["target_work_completion_evidence_required_separately"])
        return_ledger = read_json(run_root / "return_event_ledger.json")
        scope = return_ledger["pending_returns"][0]["ack_clearance_scope"]
        self.assertIn("gate_or_node_boundary_transition", scope["required_before"])
        self.assertIn("formal_work_packet_relay_to_target_role", scope["required_before"])

    def test_missing_system_card_ack_wait_confirms_controller_delivery_before_target_reminder(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        action = self.deliver_startup_fact_check_card_without_ack(root)
        state = read_json(router.run_state_path(run_root))
        router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)

        result = router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(
                root,
                "startup/reviewer_startup_fact_report_pre_ack_controller_delivery_unconfirmed",
                self.startup_fact_report_body(root),
            ),
        )

        self.assertFalse(result["ok"])
        state = read_json(router.run_state_path(run_root))
        wait = state["pending_action"]
        self.assertEqual(wait["action_type"], "await_card_return_event")
        self.assertEqual(wait["missing_ack_recovery"], "confirm_or_reissue_controller_delivery_before_target_ack_reminder")
        self.assertEqual(wait["reminder_target"], "controller_delivery_task")
        self.assertFalse(wait["target_role_ack_reminder_allowed"])
        self.assertTrue(wait["controller_delivery_reissue_required_before_target_ack_reminder"])
        fact = wait["controller_delivery_fact"]
        self.assertEqual(fact["controller_delivery_fact_status"], "controller_delivery_unconfirmed")
        self.assertFalse(fact["target_role_ack_reminder_allowed"])
        self.assertEqual(fact["controller_delivery_reissue_reason"], "controller_delivery_not_marked_done")
        self.assertTrue(fact["matching_controller_actions"])

    def test_missing_system_card_ack_after_controller_delivery_done_reminds_target_role(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        action = self.deliver_startup_fact_check_card_without_ack(root)
        state = read_json(router.run_state_path(run_root))
        router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        router._write_controller_receipt(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            action_id=action["controller_action_id"],
            status="done",
            payload={"delivery_relayed": True},
        )
        router.save_run_state(run_root, state)

        result = router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(
                root,
                "startup/reviewer_startup_fact_report_pre_ack_controller_delivery_done",
                self.startup_fact_report_body(root),
            ),
        )

        self.assertFalse(result["ok"])
        state = read_json(router.run_state_path(run_root))
        wait = state["pending_action"]
        self.assertEqual(wait["missing_ack_recovery"], "remind_target_role_to_ack_original_committed_card")
        self.assertEqual(wait["reminder_target"], "original_committed_card")
        self.assertTrue(wait["target_role_ack_reminder_allowed"])
        self.assertFalse(wait["controller_delivery_reissue_required_before_target_ack_reminder"])
        self.assertEqual(wait["controller_delivery_fact"]["controller_delivery_fact_status"], "controller_delivery_done")

    def test_formal_work_packet_ack_preflight_blocks_target_pending_card_ack(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        pending_return = {
            "card_return_event": "worker_card_ack",
            "status": "pending",
            "card_id": "worker.test",
            "delivery_id": "worker-test-delivery",
            "delivery_attempt_id": "worker-test-delivery-attempt",
            "target_role": "worker_a",
            "target_agent_id": "agent-worker-a",
            "card_envelope_path": f"{run_root.relative_to(root).as_posix()}/mailbox/system_cards/worker-test.json",
            "card_envelope_hash": "0" * 64,
            "expected_receipt_path": f"{run_root.relative_to(root).as_posix()}/runtime_receipts/card_reads/worker-test.receipt.json",
            "expected_return_path": f"{run_root.relative_to(root).as_posix()}/mailbox/outbox/card_acks/worker-test.ack.json",
            "ack_clearance_scope": {
                "schema_version": "flowpilot.system_card_ack_clearance_scope.v1",
                "target_role": "worker_a",
                "required_before": [
                    "gate_or_node_boundary_transition",
                    "formal_work_packet_relay_to_target_role",
                ],
                "ack_is_read_receipt_only": True,
                "target_work_completion_evidence_required_separately": True,
            },
        }
        ledger_path = run_root / "return_event_ledger.json"
        ledger = read_json(ledger_path) if ledger_path.exists() else {"pending_returns": [], "completed_returns": []}
        ledger.setdefault("pending_returns", []).append(pending_return)
        router.write_json(ledger_path, ledger)
        packet_action = router.make_action(
            action_type="relay_material_scan_packets",
            actor="controller",
            label="test_material_packet_relay",
            summary="Relay test material packet.",
            to_role="worker_a",
            extra={"postcondition": "material_scan_packets_relayed"},
        )

        blocked = router._apply_formal_work_packet_ack_preflight(root, state, run_root, packet_action)

        self.assertEqual(blocked["action_type"], "await_card_return_event")
        self.assertEqual(blocked["ack_clearance_reason"], "formal_work_packet_preflight")
        self.assertEqual(blocked["blocked_formal_work_packet"]["action_type"], "relay_material_scan_packets")
        self.assertFalse(blocked["formal_work_packet_ack_preflight"]["passed"])
        self.assertEqual(blocked["formal_work_packet_ack_preflight"]["pending_return_count"], 1)
        self.assertEqual(blocked["missing_ack_recovery"], "confirm_or_reissue_controller_delivery_before_target_ack_reminder")
        self.assertFalse(blocked["target_role_ack_reminder_allowed"])
        self.assertEqual(blocked["controller_delivery_fact"]["controller_delivery_fact_status"], "committed_artifact_missing_or_invalid")
        self.assertFalse(blocked["duplicate_system_card_delivery_allowed"])

    def test_quarantined_pre_ack_report_requires_fresh_report_after_ack(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        action = self.deliver_startup_fact_check_card_without_ack(root)
        quarantined = router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(
                root,
                "startup/reviewer_startup_fact_report_pre_ack",
                self.startup_fact_report_body(root),
            ),
        )
        self.assertTrue(quarantined["report_quarantined"])

        open_result = card_runtime.open_card(
            root,
            envelope_path=str(action["card_envelope_path"]),
            role=str(action["to_role"]),
            agent_id=str(action["target_agent_id"]),
        )
        card_runtime.submit_card_ack(
            root,
            envelope_path=str(action["card_envelope_path"]),
            role=str(action["to_role"]),
            agent_id=str(action["target_agent_id"]),
            receipt_paths=[str(open_result["read_receipt_path"])],
        )
        router.next_action(root)

        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"]["startup_fact_reported"])
        self.assertEqual(len([item for item in state["events"] if item.get("event") == "reviewer_reports_startup_facts"]), 0)

        accepted = router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(
                root,
                "startup/reviewer_startup_fact_report_post_ack",
                self.startup_fact_report_body(root),
            ),
        )

        self.assertTrue(accepted["ok"])
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["startup_fact_reported"])
        self.assertEqual(len([item for item in state["events"] if item.get("event") == "reviewer_reports_startup_facts"]), 1)

    def test_record_external_event_quarantines_invalid_same_role_card_ack_report(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        action = self.deliver_startup_fact_check_card_without_ack(root)
        open_result = card_runtime.open_card(
            root,
            envelope_path=str(action["card_envelope_path"]),
            role=str(action["to_role"]),
            agent_id=str(action["target_agent_id"]),
        )
        card_runtime.submit_card_ack(
            root,
            envelope_path=str(action["card_envelope_path"]),
            role=str(action["to_role"]),
            agent_id=str(action["target_agent_id"]),
            receipt_paths=[str(open_result["read_receipt_path"])],
        )
        ack_path = root / action["expected_return_path"]
        ack = read_json(ack_path)
        ack["role_key"] = "project_manager"
        ack["ack_hash"] = card_runtime.stable_json_hash(ack)
        router.write_json(ack_path, ack)

        result = router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(
                root,
                "startup/reviewer_startup_fact_report",
                self.startup_fact_report_body(root),
            ),
        )

        self.assertFalse(result["ok"])
        self.assertTrue(result["report_quarantined"])
        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"]["startup_fact_reported"])
        self.assertEqual(state["pending_action"]["action_type"], "check_card_return_event")
        return_ledger = read_json(run_root / "return_event_ledger.json")
        self.assertNotEqual(return_ledger["pending_returns"][0].get("status"), "resolved")

    def test_record_external_event_does_not_preconsume_incomplete_bundle_ack(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        self.apply_startup_heartbeat_if_requested(root)
        action = self.next_after_display_sync(root)
        while action["action_type"] in {
            "confirm_controller_core_boundary",
            "write_startup_mechanical_audit",
            "write_display_surface_status",
        }:
            router.apply_action(root, str(action["action_type"]), self.payload_for_action(action))
            action = self.next_after_display_sync(root)
        self.assertIn("check_prompt_manifest", self.router_internal_action_types(root))
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
        receipt_refs = []
        for receipt_path in opened["read_receipt_paths"][:-1]:
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

        result = router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(
                root,
                "startup/reviewer_startup_fact_report",
                self.startup_fact_report_body(root),
            ),
        )
        self.assertFalse(result["ok"])
        self.assertTrue(result["startup_pre_review_ack_join_blocked"])
        self.assertEqual(result["next_required_action"]["action_type"], "await_current_scope_reconciliation")

        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"]["startup_fact_reported"])
        self.assertEqual(state.get("quarantined_role_reports"), [])
        return_ledger = read_json(run_root / "return_event_ledger.json")
        bundle_pending = [
            item for item in return_ledger["pending_returns"]
            if item.get("return_kind") == "system_card_bundle"
            and item.get("card_bundle_id") == action.get("card_bundle_id")
        ][0]
        self.assertEqual(bundle_pending["status"], "bundle_ack_incomplete")

    def test_initial_pm_system_cards_are_delivered_as_same_role_bundle(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        self.apply_startup_heartbeat_if_requested(root)
        action = self.next_after_display_sync(root)
        while action["action_type"] in {
            "confirm_controller_core_boundary",
            "write_startup_mechanical_audit",
            "write_display_surface_status",
        }:
            router.apply_action(root, str(action["action_type"]), self.payload_for_action(action))
            action = self.next_after_display_sync(root)
        expected_card_ids = [
            "pm.core",
            "pm.output_contract_catalog",
            "pm.role_work_request",
            "pm.phase_map",
            "pm.startup_intake",
        ]
        self.assertIn("check_prompt_manifest", self.router_internal_action_types(root))
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
        self.assertGreaterEqual(state["prompt_deliveries"], 5)
        self.assertEqual([item["card_id"] for item in state["delivered_cards"][:5]], expected_card_ids)
        return_ledger = read_json(run_root / "return_event_ledger.json")
        bundle_records = [
            item for item in return_ledger["pending_returns"]
            if isinstance(item, dict) and item.get("return_kind") == "system_card_bundle"
        ]
        self.assertEqual(bundle_records[0]["status"], "resolved")
        self.assert_startup_user_intake_released_to_pm(root)
        next_action = self.next_after_display_sync(root)
        self.assertEqual(next_action["action_type"], "deliver_system_card")
        self.assertEqual(next_action["card_id"], "reviewer.startup_fact_check")

    def test_incomplete_system_card_bundle_ack_waits_for_missing_receipts_then_recovers(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        self.apply_startup_heartbeat_if_requested(root)
        action = self.next_after_display_sync(root)
        while action["action_type"] in {
            "confirm_controller_core_boundary",
            "write_startup_mechanical_audit",
            "write_display_surface_status",
        }:
            router.apply_action(root, str(action["action_type"]), self.payload_for_action(action))
            action = self.next_after_display_sync(root)
        self.assertIn("check_prompt_manifest", self.router_internal_action_types(root))
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
        self.assert_startup_user_intake_released_to_pm(root)
        self.assertEqual(next_action["action_type"], "deliver_system_card")
        self.assertEqual(next_action["card_id"], "reviewer.startup_fact_check")

    def test_pm_card_bundle_ack_releases_router_owned_user_intake_without_deliver_mail(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        self.deliver_expected_card(root, "pm.core")
        self.deliver_expected_card(root, "pm.output_contract_catalog")
        self.deliver_expected_card(root, "pm.role_work_request")
        self.deliver_expected_card(root, "pm.phase_map")
        self.deliver_expected_card(root, "pm.startup_intake")

        action = self.next_after_display_sync(root)

        state = read_json(run_root / "router_state.json")
        packet_ledger = read_json(run_root / "packet_ledger.json")
        action_dir = run_root / "runtime" / "controller_actions"
        controller_action_types = [
            read_json(path).get("action_type")
            for path in sorted(action_dir.glob("*.json"))
        ] if action_dir.exists() else []
        self.assertNotIn("check_packet_ledger", controller_action_types)
        self.assertNotIn("deliver_mail", controller_action_types)
        self.assertTrue(state["flags"]["user_intake_delivered_to_pm"])
        self.assertEqual(state["mail_deliveries"], 1)
        self.assertEqual(packet_ledger["mail"][0]["mail_id"], "user_intake")
        self.assertEqual(packet_ledger["active_packet_holder"], "project_manager")
        self.assertEqual(packet_ledger["active_packet_status"], "envelope-relayed")
        self.assertEqual(packet_ledger["packets"][0]["active_packet_holder"], "project_manager")
        self.assertEqual(packet_ledger["packets"][0]["active_packet_status"], "envelope-relayed")
        self.assertEqual(packet_ledger["packets"][0]["packet_router_release"]["relayed_to_role"], "project_manager")
        mail_envelope = read_json(run_root / "mailbox" / "outbox" / "user_intake.json")
        self.assertEqual(mail_envelope["router_startup_release"]["relayed_to_role"], "project_manager")
        self.assertEqual(action["action_type"], "deliver_system_card")
        self.assertEqual(action["card_id"], "reviewer.startup_fact_check")
        self.assertEqual(packet_ledger["schema_version"], packet_runtime.PACKET_LEDGER_SCHEMA)

    def test_user_intake_router_release_finalizer_is_idempotent(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        self.deliver_expected_card(root, "pm.core")
        self.deliver_expected_card(root, "pm.output_contract_catalog")
        self.deliver_expected_card(root, "pm.role_work_request")
        self.deliver_expected_card(root, "pm.phase_map")
        self.deliver_expected_card(root, "pm.startup_intake")

        state = read_json(router.run_state_path(run_root))
        first = router._run_router_return_settlement_finalizers(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test_idempotent_return_settlement_first",
        )
        second = router._run_router_return_settlement_finalizers(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test_idempotent_return_settlement_second",
        )
        router.save_run_state(run_root, state)

        state = read_json(router.run_state_path(run_root))
        packet_ledger = read_json(run_root / "packet_ledger.json")
        self.assertTrue(first["changed"] or first["startup_user_intake_release"]["already_released"])
        self.assertTrue(second["startup_user_intake_release"]["already_released"])
        self.assertTrue(state["flags"]["user_intake_delivered_to_pm"])
        self.assertFalse(state["ledger_check_requested"])
        self.assertEqual(state["mail_deliveries"], 1)
        self.assertEqual(len(state["delivered_mail"]), 1)
        self.assertEqual(len(packet_ledger["mail"]), 1)
        self.assertEqual(packet_ledger["mail"][0]["mail_id"], "user_intake")
        self.assertEqual(packet_ledger["mail"][0]["to_role"], "project_manager")
        self.assertEqual(packet_ledger["active_packet_holder"], "project_manager")
        self.assertEqual(packet_ledger["active_packet_status"], "envelope-relayed")
        self.assertEqual(packet_ledger["packets"][0]["active_packet_holder"], "project_manager")
        self.assertEqual(packet_ledger["packets"][0]["active_packet_status"], "envelope-relayed")
        self.assertEqual(packet_ledger["packets"][0]["packet_router_release"]["relayed_to_role"], "project_manager")
        self.assertIsNone(state.get("active_control_blocker"))
        self.assertEqual(len(packet_ledger["packets"][0]["router_startup_release_history"]), 1)
        self.assertEqual(len(packet_ledger["packets"][0]["holder_history"]), 2)

    def test_controller_action_reconciliation_ignores_transient_temp_files(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-transient-action-scan")
        state = read_json(router.run_state_path(run_root))
        action_dir = router._controller_actions_dir(run_root)  # type: ignore[attr-defined]
        action_dir.mkdir(parents=True, exist_ok=True)
        (action_dir / ".tmp-1234-action.json").write_text("{", encoding="utf-8")

        ledger = router._rebuild_controller_action_ledger(root, run_root, state)  # type: ignore[attr-defined]
        result = router._reconcile_scheduled_controller_action_receipts(root, run_root, state)  # type: ignore[attr-defined]

        self.assertEqual(ledger["actions"], [])
        self.assertFalse(result["changed"])
        self.assertIsNone(state.get("active_control_blocker"))

    def test_mail_delivery_receipt_waits_for_active_packet_ledger_writer(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        state = read_json(router.run_state_path(run_root))
        state["ledger_check_requested"] = True
        action = {
            "action_type": "deliver_mail",
            "mail_id": "user_intake",
            "to_role": "project_manager",
            "allowed_reads": [self.rel(root, run_root / "mailbox" / "outbox" / "user_intake.json")],
        }
        payload = {
            "mail_id": "user_intake",
            "packet_id": "user_intake",
            "packet_envelope_path": str(action["allowed_reads"][0]),
            "delivered_to_role": "project_manager",
            "delivery_confirmed": True,
        }
        lock_path = run_root / "packet_ledger.json.write.lock"
        lock_path.write_text(json.dumps({"created_at": router.utc_now()}, sort_keys=True), encoding="utf-8")

        with self.assertRaises(router.RouterLedgerWriteInProgress):
            router._fold_mail_delivery_postcondition(  # type: ignore[attr-defined]
                root,
                run_root,
                state,
                action,
                payload,
                source="test_active_writer",
            )

        self.assertIsNone(state.get("active_control_blocker"))
        self.assertFalse(state["flags"].get("user_intake_delivered_to_pm", False))

    def test_daemon_folds_stable_startup_role_flags_from_bootstrap(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-startup-role-fold")
        bootstrap_path = run_root / "bootstrap" / "startup_state.json"
        router.write_json(
            bootstrap_path,
            {
                "schema_version": "flowpilot.startup_state.v1",
                "run_id": run_root.name,
                "run_root": router.project_relative(root, run_root),
                "flags": {
                    "roles_started": True,
                    "role_core_prompts_injected": True,
                },
            },
        )
        state = read_json(router.run_state_path(run_root))

        result = router._fold_stable_startup_role_flags_from_bootstrap(root, run_root, state)  # type: ignore[attr-defined]

        self.assertTrue(result["changed"])
        self.assertTrue(state["flags"]["roles_started"])
        self.assertTrue(state["flags"]["role_core_prompts_injected"])

    def test_partial_startup_role_flags_wait_for_settlement(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-startup-role-partial")
        bootstrap_path = run_root / "bootstrap" / "startup_state.json"
        router.write_json(
            bootstrap_path,
            {
                "schema_version": "flowpilot.startup_state.v1",
                "run_id": run_root.name,
                "run_root": router.project_relative(root, run_root),
                "flags": {
                    "roles_started": True,
                    "role_core_prompts_injected": False,
                },
            },
        )
        state = read_json(router.run_state_path(run_root))

        result = router._fold_stable_startup_role_flags_from_bootstrap(root, run_root, state)  # type: ignore[attr-defined]

        self.assertFalse(result["changed"])
        self.assertTrue(result["waiting_for_settlement"])
        self.assertFalse(state["flags"].get("roles_started", False))
        self.assertFalse(state["flags"].get("role_core_prompts_injected", False))

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
        reset_confirmation = router.record_external_event(root, "controller_role_confirmed_from_pm_reset")
        self.assertTrue(reset_confirmation["already_recorded"])
        boundary = read_json(run_root / "startup" / "controller_boundary_confirmation.json")
        self.assertEqual(boundary["event"], "controller_role_confirmed_from_router_core")
        self.assertFalse(boundary["sealed_body_reads_allowed"])

        self.assertTrue((run_root / "display" / "display_surface.json").exists())
        startup_audit = read_json(run_root / "startup" / "startup_mechanical_audit.json")
        self.assertTrue(startup_audit["mechanical_checks_passed"])
        self.assertTrue(startup_audit["mechanical_checks"]["startup_intake_record_current"])
        self.assertTrue(startup_audit["mechanical_checks"]["startup_intake_receipt_envelope_hash_current"])
        self.assertTrue(startup_audit["mechanical_checks"]["reviewer_live_review_uses_startup_intake_record"])
        self.assertIn(
            f"{run_root.relative_to(root).as_posix()}/startup_intake/startup_intake_record.json",
            {item["path"] for item in startup_audit["source_paths"]},
        )
        self.assertFalse(startup_audit["self_attested_ai_claims_accepted_as_proof"])
        self.assertEqual(startup_audit["router_replacement_scope"], "mechanical_only")
        proof_path = root / startup_audit["router_owned_check_proof_path"]
        self.assertTrue(proof_path.exists())
        proof = read_json(proof_path)
        self.assertEqual(proof["source_kind"], "router_computed")
        self.assertFalse(proof["self_attested_ai_claims_accepted_as_proof"])

        invalid_root = self.make_project()
        self.boot_to_controller(invalid_root)
        self.deliver_startup_fact_check_card(invalid_root)
        self.deliver_initial_pm_cards_and_user_intake(invalid_root)
        with self.assertRaises(router.RouterError):
            router.record_external_event(invalid_root, "reviewer_reports_startup_facts", {"passed": True})
        second_invalid = router.record_external_event(
            invalid_root,
            "reviewer_reports_startup_facts",
            {"reviewed_by_role": "human_like_reviewer", "passed": True},
        )
        self.assertTrue(second_invalid["current_scope_reconciliation_blocked"])
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
        startup_activation_payload = self.role_decision_envelope(
            root,
            "startup/pm_startup_activation",
            {"approved_by_role": "project_manager", "decision": "approved"},
        )
        router.record_external_event(
            root,
            "pm_approves_startup_activation",
            startup_activation_payload,
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

        active_blocker = read_json(router.run_state_path(run_root)).get("active_control_blocker")
        self.assertEqual(active_blocker["originating_event"], "pm_approves_startup_activation")
        router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(
                root,
                "control_blocks/pm_startup_activation_payload_repair",
                self.pm_control_blocker_decision_body(
                    active_blocker["blocker_id"],
                    decision="repair_completed",
                    rerun_target="pm_approves_startup_activation",
                ),
            ),
        )
        replay = router.record_external_event(root, "pm_approves_startup_activation", startup_activation_payload)
        self.assertTrue(replay["control_blocker_resolved"])

        self.apply_next_non_card_action(root)
        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["pm_material_packets_issued"])

    def test_material_work_packet_records_target_ack_preflight_passed(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_startup_activation(root)

        self.apply_next_non_card_action(root)
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.material_scan")
        self.ack_system_card_action(root, action)
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())

        action = self.next_after_display_sync(root)

        self.assertEqual(action["action_type"], "relay_material_scan_packets")
        preflight = action["formal_work_packet_ack_preflight"]
        self.assertTrue(preflight["passed"])
        self.assertEqual(preflight["target_roles"], ["worker_a", "worker_b"])
        self.assertEqual(preflight["pending_return_count"], 0)
        self.assertTrue(action["ack_is_read_receipt_only"])
        self.assertTrue(action["target_work_completion_evidence_required_separately"])

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
        self.assertIn("write_startup_mechanical_audit", self.router_internal_action_types(root))
        self.assertEqual(action["action_type"], "deliver_system_card")
        self.assertEqual(action["card_id"], "reviewer.startup_fact_check")
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

    def test_reconcile_run_recovers_terminal_status_from_current_pointer(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-terminal-drift", status="startup_bootstrap")
        router.write_json(
            root / ".flowpilot" / "current.json",
            {
                "schema_version": "flowpilot.current.v1",
                "current_run_id": run_root.name,
                "current_run_root": router.project_relative(root, run_root),
                "status": "stopped_by_user",
                "updated_at": router.utc_now(),
            },
        )
        router.write_json(
            root / ".flowpilot" / "index.json",
            {
                "schema_version": "flowpilot.index.v1",
                "runs": [
                    {
                        "run_id": run_root.name,
                        "run_root": router.project_relative(root, run_root),
                        "status": "stopped_by_user",
                    }
                ],
            },
        )

        result = router.reconcile_current_run(root)

        self.assertTrue(result["ok"])
        self.assertTrue(result["repaired"]["terminal_status_recovered_from_authority"])
        state = read_json(router.run_state_path(run_root))
        self.assertEqual(state["status"], "stopped_by_user")
        self.assertTrue(state["flags"]["run_stopped_by_user"])
        snapshot = read_json(run_root / "route_state_snapshot.json")
        self.assertEqual(snapshot["state"]["status"], "stopped_by_user")
        self.assertTrue(snapshot["state"]["flags"]["run_stopped_by_user"])
        self.assertEqual(snapshot["authority"]["active_source"], "index_active_runs_with_current_focus")

    def test_terminal_summary_payload_requires_attribution_display_and_run_root_sources(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        router.record_external_event(root, "user_requests_run_stop", {"reason": "user asked to stop"})
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "write_terminal_summary")
        self.assertTrue(action["apply_required"])
        self.assertTrue(action["next_step_contract"]["apply_required"])
        self.assertIn(
            "direct terminal action",
            json.dumps(action["payload_contract"]["structural_requirements"], sort_keys=True),
        )

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

        self.apply_next_non_card_action(root)
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

        self.apply_next_non_card_action(root)
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

        self.apply_next_non_card_action(root)
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

        self.apply_next_non_card_action(root)
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
        research_index_path = run_root / "research" / "research_packet.json"
        research_packet_id = read_json(research_index_path)["packets"][0]["packet_id"]
        research_lease = self.active_holder_lease_for_packet(root, research_packet_id)
        self.assertEqual(research_lease["holder_role"], "worker_a")
        state_after_research_packet = read_json(router.run_state_path(run_root))
        self.assertEqual(state_after_research_packet["ledger_checks"], ledger_checks_before_research + 1)
        self.assertEqual(state_after_research_packet["ledger_check_requests"], ledger_requests_before_research + 1)
        self.assertFalse(state_after_research_packet.get("ledger_check_requested"))
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

        self.apply_next_non_card_action(root)
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

        self.apply_next_non_card_action(root)
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.research_absorb_or_mutate")
        self.ack_system_card_action(root, action)
        router.record_external_event(root, "pm_absorbs_reviewed_research")

        self.apply_next_non_card_action(root)
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

        self.apply_next_non_card_action(root)
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

        self.apply_next_non_card_action(root)
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

        self.apply_next_non_card_action(root)
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.product_behavior_model_decision")
        self.ack_system_card_action(root, action)
        router.record_external_event(root, "pm_accepts_product_behavior_model", self.product_behavior_model_decision_body())

        self.apply_next_non_card_action(root)
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
        self.write_self_interrogation_record(
            root,
            "product_architecture",
            source_path=run_root / "product_function_architecture.json",
        )

        self.apply_next_non_card_action(root)
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

        self.apply_next_non_card_action(root)
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

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_activates_reviewed_route")
        router.record_external_event(root, "pm_freezes_root_acceptance_contract")
        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"].get("product_officer_root_contract_card_delivered", False))
        self.assertFalse(state["flags"].get("root_contract_modelability_passed", False))
        self.assertFalse((run_root / "flowguard" / "root_contract_modelability.json").exists())

        self.apply_next_non_card_action(root)
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

        self.apply_next_non_card_action(root)
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

        self.apply_next_non_card_action(root)
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

        self.apply_next_non_card_action(root)
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
        router.record_external_event(root, "pm_approves_child_skill_manifest_for_route")
        manifest_after_approval = read_json(run_root / "child_skill_gate_manifest.json")
        self.assertTrue(manifest_after_approval["approval"]["reviewer_passed"])
        self.assertFalse(manifest_after_approval["approval"]["process_officer_passed"])
        self.assertTrue(manifest_after_approval["approval"]["process_officer_default_gate_removed"])
        self.assertFalse(manifest_after_approval["approval"]["product_officer_passed"])
        self.assertTrue(manifest_after_approval["approval"]["product_officer_default_gate_removed"])
        self.assertFalse((run_root / "flowguard" / "child_skill_conformance_model.json").exists())
        self.assertFalse((run_root / "flowguard" / "child_skill_product_fit.json").exists())
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
        self.assertIn("heartbeat_rehydration", {item["lifecycle_phase"] for item in resume_receipts})

        role_report = read_json(run_root / "continuation" / "role_recovery_report.json")
        self.assertFalse(role_report["pm_decision_required_before_normal_work"])
        self.assertTrue(role_report["mechanical_obligation_replay_before_pm"])
        self.assertTrue(role_report["mechanical_obligation_replay_completed"])
        replay = read_json(root / role_report["role_recovery_obligation_replay_path"])
        self.assertEqual(replay["candidate_count"], 0)
        self.assertEqual(replay["replacement_count"], 0)
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["role_recovery_obligations_scanned"])
        self.assertTrue(state["flags"]["role_recovery_obligation_replay_completed"])
        self.assertFalse(state["flags"]["role_recovery_pm_escalation_required"])
        self.assertTrue(state["flags"]["pm_resume_recovery_decision_returned"])

        self.deliver_expected_card(root, "controller.resume_reentry")
        action = router.next_action(root)
        self.assertNotEqual(action.get("card_id"), "pm.crew_rehydration_freshness")
        self.assertNotEqual(action.get("card_id"), "pm.resume_decision")
        self.assertNotEqual(action.get("label"), "controller_waits_for_pm_resume_decision")
        self.assertFalse((run_root / "continuation" / "pm_resume_decision.json").exists())

    def test_resume_reentry_attaches_to_live_router_daemon_and_ledger(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        router._refresh_router_daemon_lock(root, run_root)  # type: ignore[attr-defined]

        try:
            router.record_external_event(root, "heartbeat_or_manual_resume_requested")
            action = router.next_action(root)
            self.assertEqual(action["action_type"], "load_resume_state")
            recovery = action["router_daemon_resume_recovery"]
            self.assertTrue(recovery["router_daemon_lock_live"])
            self.assertEqual(recovery["decision"], "attach_controller_to_live_daemon")
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

    def test_resume_reentry_attaches_to_live_owner_after_delayed_heartbeat(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        lock_path = run_root / "runtime" / "router_daemon.lock"
        lock = read_json(lock_path)
        lock["last_tick_at"] = "2000-01-01T00:00:00Z"
        router.write_json(lock_path, lock)

        router.record_external_event(root, "heartbeat_or_manual_resume_requested")
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "load_resume_state")
        recovery = action["router_daemon_resume_recovery"]
        self.assertFalse(recovery["router_daemon_lock_live"])
        self.assertTrue(recovery["router_daemon_owner_process_live"])
        self.assertTrue(recovery["router_daemon_active_owner_live"])
        self.assertEqual(recovery["heartbeat"]["status"], "check_liveness")
        self.assertEqual(recovery["decision"], "attach_controller_to_live_daemon")

        router.apply_action(root, "load_resume_state")
        resume_evidence = read_json(run_root / "continuation" / "resume_reentry.json")
        self.assertTrue(resume_evidence["router_daemon_liveness_checked"])
        self.assertFalse(resume_evidence["router_daemon_restarted_if_dead"])
        self.assertTrue(resume_evidence["controller_action_ledger_loaded"])
        router.stop_router_daemon(root, reason="test_cleanup")

    def test_resume_reentry_marks_dead_daemon_for_restart_after_liveness_check(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        lock_path = run_root / "runtime" / "router_daemon.lock"
        lock = read_json(lock_path)
        lock["last_tick_at"] = "2000-01-01T00:00:00Z"
        lock["owner"] = {"pid": 999999999, "process_name": "missing-test-daemon"}
        router.write_json(lock_path, lock)

        router.record_external_event(root, "heartbeat_or_manual_resume_requested")
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "load_resume_state")
        recovery = action["router_daemon_resume_recovery"]
        self.assertFalse(recovery["router_daemon_lock_live"])
        self.assertFalse(recovery["router_daemon_owner_process_live"])
        self.assertFalse(recovery["router_daemon_active_owner_live"])
        self.assertEqual(recovery["heartbeat"]["status"], "check_liveness")
        self.assertEqual(recovery["decision"], "restart_router_daemon_from_current_state")

        router.apply_action(root, "load_resume_state")
        resume_evidence = read_json(run_root / "continuation" / "resume_reentry.json")
        self.assertTrue(resume_evidence["router_daemon_liveness_checked"])
        self.assertTrue(resume_evidence["router_daemon_restarted_if_dead"])
        self.assertTrue(resume_evidence["controller_action_ledger_loaded"])

    def test_resume_reentry_preempts_active_control_blocker_until_replay_or_pm_decision(self) -> None:
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
        self.assertFalse(report["pm_decision_required_before_normal_work"])
        self.assertTrue(report["mechanical_obligation_replay_completed"])
        replay = read_json(root / report["role_recovery_obligation_replay_path"])
        self.assertEqual(replay["schema_version"], "flowpilot.role_recovery_obligation_replay.v1")
        self.assertFalse(replay["pm_escalation_required"])
        self.assertEqual(report["role_records"][0]["recovery_result"], "targeted_replacement_spawned")
        crew = read_json(run_root / "crew_ledger.json")
        worker_slot = next(slot for slot in crew["role_slots"] if slot["role_key"] == "worker_a")
        self.assertEqual(worker_slot["last_role_recovery_result"], "targeted_replacement_spawned")
        self.assertTrue(worker_slot["superseded_agent_output_quarantined"])

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "handle_control_blocker")
        self.assertEqual(action["blocker_id"], blocker["blocker_id"])

    def test_blocked_role_recovery_receipt_reclaims_existing_report(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        report = self.recover_worker_a_after_liveness_fault(root)
        self.assertTrue(report["all_six_roles_ready"])

        state = read_json(router.run_state_path(run_root))
        action = router.make_action(
            action_type="recover_role_agents",
            actor="controller",
            label="host_recovers_role_agents_before_normal_work_stale_projection",
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
                "Controller action recover_role_agents was marked done, but Router could not "
                "apply its required postcondition before reconciliation."
            ),
            action_type="recover_role_agents",
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

    def test_load_resume_state_does_not_downgrade_existing_role_recovery_report(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        report = self.recover_worker_a_after_liveness_fault(root)
        self.assertFalse(report["pm_decision_required_before_normal_work"])

        state = read_json(router.run_state_path(run_root))
        state["flags"]["resume_reentry_requested"] = True
        state["flags"]["resume_state_loaded"] = False
        state["flags"]["resume_roles_restored"] = False
        state["flags"]["resume_role_agents_rehydrated"] = False
        state["flags"]["crew_rehydration_report_written"] = False
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

    def test_role_no_output_report_reissues_same_work_before_role_recovery(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        wait_action = self.force_startup_fact_role_wait(root)

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

    def test_legacy_liveness_fault_no_output_redirects_to_reissue_not_recovery(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        wait_action = self.force_startup_fact_role_wait(root)

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
        wait_action = self.force_startup_fact_role_wait(root)

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
        self.complete_startup_activation(root)
        original = self.write_worker_recovery_wait_action(root, label="resume_waits_for_worker_existing_output")
        state = read_json(router.run_state_path(run_root))
        state.setdefault("events", []).append(
            {
                "event": "worker_scan_results_returned",
                "summary": "Worker output already reached Router before heartbeat resume replay.",
                "payload": {"result_envelope_path": self.rel(root, run_root / "test_role_outputs" / "resume-existing.json")},
                "recorded_at": router.utc_now(),
            }
        )
        router.save_run_state(run_root, state)

        router.record_external_event(root, "heartbeat_or_manual_resume_requested")
        self.assertEqual(self.next_after_display_sync(root)["action_type"], "load_resume_state")
        router.apply_action(root, "load_resume_state")
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "rehydrate_role_agents")
        router.apply_action(root, "rehydrate_role_agents", self.resume_role_agent_payload(root, action))

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
        self.complete_startup_activation(root)
        original = self.write_worker_recovery_wait_action(root, label="resume_waits_for_worker_missing_output")

        router.record_external_event(root, "heartbeat_or_manual_resume_requested")
        self.assertEqual(self.next_after_display_sync(root)["action_type"], "load_resume_state")
        router.apply_action(root, "load_resume_state")
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "rehydrate_role_agents")
        router.apply_action(root, "rehydrate_role_agents", self.resume_role_agent_payload(root, action))

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
        self.complete_startup_activation(root)
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

        report = self.recover_worker_a_after_liveness_fault(root)
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
        self.complete_startup_activation(root)
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
            summary="Controller waits for worker_a card ACK before recovery.",
            allowed_reads=[envelope_rel],
            allowed_writes=[],
            to_role="worker_a",
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
                "target_role": "worker_a",
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
            report = self.recover_worker_a_after_liveness_fault(root)

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
        self.complete_startup_activation(root)
        first = self.write_worker_recovery_wait_action(root, label="controller_waits_for_worker_output_first")
        second = self.write_worker_recovery_wait_action(root, label="controller_waits_for_worker_output_second")

        report = self.recover_worker_a_after_liveness_fault(root)
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
        self.assertNotEqual(action["action_type"], "create_heartbeat_automation")
        self.assertEqual(action["action_type"], "write_display_surface_status")
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
            "wait_for_recorded_packet_holder_result",
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
        lease = self.active_holder_lease_for_packet(root, "node-packet-001")
        self.assertEqual(lease["holder_role"], "worker_a")
        self.assertEqual(lease["holder_agent_id"], f"agent-{run_root.name}-worker_a")
        self.assertEqual(lease["route_version"], 1)
        self.assertEqual(lease["frontier_version"], 1)

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
        agent_a, result_a_path = self.submit_current_node_result_via_active_holder(
            root,
            packet_id="node-batch-worker-a",
            result_body_text="worker a result",
        )
        self.assertEqual(agent_a, f"agent-{run_root.name}-worker_a")
        results["node-batch-worker-a"] = result_a_path
        router.record_external_event(
            root,
            "worker_current_node_result_returned",
            {"packet_id": "node-batch-worker-a", "result_envelope_path": results["node-batch-worker-a"]},
        )
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertEqual(action["allowed_external_events"], ["worker_current_node_result_returned"])
        self.assertIn("worker_b", action["to_role"])

        agent_b, result_b_path = self.submit_current_node_result_via_active_holder(
            root,
            packet_id="node-batch-worker-b",
            result_body_text="worker b result",
        )
        self.assertEqual(agent_b, f"agent-{run_root.name}-worker_b")
        results["node-batch-worker-b"] = result_b_path
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
                    "agent_role_map": {agent_a: "worker_a", agent_b: "worker_b"},
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

    def test_current_node_pre_review_reconciliation_blocks_reviewer_card(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(
            root,
            packet_id="node-packet-local-reconciliation-card",
            deliver_review_card=False,
        )
        self.set_active_current_node_batch_status(root, "results_relayed_to_pm")

        action = self.next_after_display_sync(root)

        self.assertEqual(action["action_type"], "await_current_scope_reconciliation")
        self.assertEqual(action["scope_kind"], "current_node")
        self.assertTrue(action["local_scope_only"])
        self.assertFalse(action["future_or_sibling_scopes_touched"])
        self.assertEqual(action["review_trigger"], "reviewer.worker_result_review")
        self.assertTrue(any(blocker["kind"] == "current_node_batch_not_absorbed" for blocker in action["blockers"]))

    def test_startup_reconciliation_wait_does_not_hide_router_local_obligation(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        flags = state.setdefault("flags", {})
        flags["controller_role_confirmed"] = True
        flags["startup_mechanical_audit_written"] = False
        state.pop("startup_mechanical_audit", None)
        blockers = router._startup_pre_review_reconciliation_blockers(root, run_root, state)  # type: ignore[attr-defined]
        wait = router._current_scope_pre_review_reconciliation_action(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            blockers=blockers,
            review_trigger="reviewer.startup_fact_check",
        )
        state["pending_action"] = wait
        router.save_run_state(run_root, state)

        action = router.next_action(root)

        self.assertNotEqual(action["action_type"], "await_current_scope_reconciliation")
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["startup_mechanical_audit_written"])
        self.assertTrue(any(
            item.get("label") == "router_local_obligation_preempted_passive_reconciliation_wait"
            for item in state.get("history", [])
        ))

    def test_startup_reconciliation_wait_does_not_block_itself(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        flags = state.setdefault("flags", {})
        for flag in (
            "banner_emitted",
            "roles_started",
            "role_core_prompts_injected",
            "controller_role_confirmed",
            "startup_mechanical_audit_written",
            "startup_display_status_written",
            "continuation_binding_recorded",
            *router._startup_pre_review_card_flags(),  # type: ignore[attr-defined]
        ):
            flags[flag] = True
        state.pop("active_control_blocker", None)
        bootstrap = self.bootstrap_state(root)
        bootstrap.setdefault("flags", {})["banner_emitted"] = True
        bootstrap.setdefault("flags", {})["roles_started"] = True
        router.write_json(router.bootstrap_state_path(root), bootstrap)
        return_ledger_path = run_root / "return_event_ledger.json"
        if return_ledger_path.exists():
            return_ledger = read_json(return_ledger_path)
            return_ledger["pending_returns"] = []
            router.write_json(return_ledger_path, return_ledger)
        action_dir = run_root / "runtime" / "controller_actions"
        if action_dir.exists():
            for action_path in sorted(action_dir.glob("*.json")):
                entry = read_json(action_path)
                if entry.get("schema_version") != router.CONTROLLER_ACTION_SCHEMA:
                    continue
                entry["status"] = "done"
                entry["router_reconciliation_status"] = "reconciled"
                entry["router_reconciled_at"] = router.utc_now()
                router.write_json(action_path, entry)
        router.save_run_state(run_root, state)

        wait = router._current_scope_pre_review_reconciliation_action(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            blockers=[{"kind": "test_reconciled_startup_blocker", "scope_kind": "startup"}],
            review_trigger="reviewer.startup_fact_check",
        )
        state["pending_action"] = wait
        entry = router._write_controller_action_entry(root, run_root, state, wait)  # type: ignore[attr-defined]
        router.save_run_state(run_root, state)
        self.assertFalse(entry["controller_receipt_required"])
        self.assertEqual(entry["controller_projection_kind"], "passive_wait_status")

        state = read_json(router.run_state_path(run_root))
        blockers = router._startup_pre_review_reconciliation_blockers(root, run_root, state)  # type: ignore[attr-defined]
        self.assertEqual(blockers, [])
        self.assertFalse(router._current_scope_reconciliation_wait_still_blocked(root, run_root, state, wait))  # type: ignore[attr-defined]

        action = router.next_action(root)

        self.assertNotEqual(action["action_type"], "await_current_scope_reconciliation")
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(any(
            item.get("label") == "router_rechecks_after_current_scope_reconciliation_cleared"
            for item in state.get("history", [])
        ))

    def test_current_node_reviewer_pass_event_waits_for_local_reconciliation(self) -> None:
        root = self.make_project()
        _run_root, _packet_path, _result_path = self.prepare_current_node_result_for_review(
            root,
            packet_id="node-packet-local-reconciliation-event",
            deliver_review_card=True,
        )
        self.set_active_current_node_batch_status(root, "results_relayed_to_pm")

        result = router.record_external_event(
            root,
            "current_node_reviewer_passes_result",
            self.role_report_envelope(
                root,
                "reviews/current_node_result_waits_for_local_reconciliation",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": True,
                    "agent_role_map": {f"agent-{self.run_root_for(root).name}-worker_a": "worker_a"},
                },
            ),
        )

        self.assertFalse(result["ok"])
        self.assertTrue(result["current_scope_reconciliation_blocked"])
        self.assertEqual(result["next_required_action"]["action_type"], "await_current_scope_reconciliation")
        state = read_json(router.run_state_path(self.run_root_for(root)))
        self.assertFalse(state["flags"]["node_reviewer_passed_result"])

    def test_future_node_pending_return_does_not_block_current_node_review(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(
            root,
            packet_id="node-packet-future-return-not-local",
            deliver_review_card=False,
        )
        self.add_current_node_pending_card_return(root, node_id="node-999")

        action = self.next_after_display_sync(root)
        if action["action_type"] == "check_prompt_manifest":
            self.assertEqual(action["next_card_id"], "reviewer.worker_result_review")
            router.apply_action(root, "check_prompt_manifest")
            action = self.next_after_display_sync(root)

        self.assertEqual(action["action_type"], "deliver_system_card")
        self.assertEqual(action["card_id"], "reviewer.worker_result_review")

    def test_current_node_completion_waits_for_review_created_local_obligations(self) -> None:
        root = self.make_project()
        run_root, _packet_path, _result_path = self.prepare_current_node_result_for_review(
            root,
            packet_id="node-packet-local-reconciliation-exit",
            deliver_review_card=True,
        )
        router.record_external_event(
            root,
            "current_node_reviewer_passes_result",
            self.role_report_envelope(
                root,
                "reviews/current_node_result_exit_waits_for_local_reconciliation",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": True,
                    "agent_role_map": {f"agent-{run_root.name}-worker_a": "worker_a"},
                },
            ),
        )
        self.set_active_current_node_batch_status(root, "pm_absorbed")

        with self.assertRaisesRegex(router.RouterError, "local current-scope reconciliation"):
            router.record_external_event(root, "pm_completes_current_node_from_reviewed_result")

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

        agent_id, result_path = self.submit_current_node_result_via_active_holder(
            root,
            packet_id="node-packet-002",
            result_body_text="reviewable result",
        )

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
                    "agent_role_map": {agent_id: "worker_a"},
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
            agent_id, result_path = self.submit_current_node_result_via_active_holder(
                root,
                packet_id=packet_id,
                result_body_text=f"{node_id} result",
            )
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
        agent_id, result_path = self.submit_current_node_result_via_active_holder(
            root,
            result_body_text="reviewable result",
            packet_id="node-packet-aliases",
        )
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
                    "agent_role_map": {agent_id: "worker_a"},
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

    def test_control_plane_reissue_retry_budget_escalates_to_pm(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-control-reissue-budget")

        blockers: list[dict] = []
        for attempt in range(3):
            with self.assertRaises(router.RouterError) as raised:
                router.record_external_event(
                    root,
                    "current_node_reviewer_passes_result",
                    self.role_report_envelope(
                        root,
                        f"reviews/current_node_result_missing_passed_budget_{attempt}",
                        {
                            "reviewed_by_role": "human_like_reviewer",
                            "agent_role_map": {"agent-worker-a": "worker_a"},
                        },
                    ),
                )
            blocker = raised.exception.control_blocker
            self.assertIsInstance(blocker, dict)
            blockers.append(blocker)
            if attempt < 2:
                self.assertEqual(blocker["handling_lane"], "control_plane_reissue")
                self.assertEqual(blocker["target_role"], "human_like_reviewer")
                self.assertEqual(blocker["direct_retry_attempts_used"], attempt)
                self.assertFalse(blocker["direct_retry_budget_exhausted"])
                self.assertTrue(self.handle_pending_control_blocker(root))
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

    def test_pm_semantic_control_blocker_zero_retry_budget_is_exhausted(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
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

        self.assertEqual(blocker["handling_lane"], "pm_repair_decision_required")
        self.assertEqual(blocker["policy_row_id"], "pm_semantic_repair")
        self.assertEqual(blocker["direct_retry_budget"], 0)
        self.assertEqual(blocker["direct_retry_attempts_used"], 0)
        self.assertTrue(blocker["direct_retry_budget_exhausted"])

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

    def test_fatal_control_blocker_rejects_pm_ordinary_waiver(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)
        state["flags"]["continuation_binding_recorded"] = True
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="envelope payload leaked role body fields to Controller: passed",
            event="host_records_heartbeat_binding",
            payload={"from_role": "host", "passed": True},
        )
        self.assertEqual(blocker["policy_row_id"], "fatal_protocol_violation")
        self.assertTrue(blocker["hard_stop_conditions"])

        self.assertTrue(self.handle_pending_control_blocker(root))
        body = self.pm_control_blocker_decision_body(
            blocker["blocker_id"],
            rerun_target="host_records_heartbeat_binding",
        )
        body["recovery_option"] = "allowed_waiver"
        body["return_gate"] = "host_records_heartbeat_binding"
        with self.assertRaisesRegex(router.RouterError, "not allowed by blocker policy"):
            router.record_external_event(
                root,
                "pm_records_control_blocker_repair_decision",
                self.role_decision_envelope(root, "control_blocks/fatal_pm_waiver_rejected", body),
            )

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
        self.assertEqual(transaction["plan_kind"], "role_reissue")

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

    def test_material_scan_existing_results_reconcile_before_stale_wait(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(
            root,
            "pm_issues_material_and_capability_scan_packets",
            {
                "packets": [
                    {
                        "packet_id": "material-scan-reconcile-a",
                        "to_role": "worker_a",
                        "body_text": "Inspect local materials.",
                    },
                    {
                        "packet_id": "material-scan-reconcile-b",
                        "to_role": "worker_b",
                        "body_text": "Inspect repository state.",
                    },
                ]
            },
        )
        self.apply_next_packet_action(root, "relay_material_scan_packets")
        lease_a = self.active_holder_lease_for_packet(root, "material-scan-reconcile-a")
        lease_b = self.active_holder_lease_for_packet(root, "material-scan-reconcile-b")
        self.assertEqual(lease_a["holder_role"], "worker_a")
        self.assertEqual(lease_b["holder_role"], "worker_b")
        material_index_path = run_root / "material" / "material_scan_packets.json"
        self.open_packets_and_write_results(root, material_index_path)

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_material_scan_results_to_pm")
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["worker_packets_delivered"])
        self.assertTrue(state["flags"]["worker_scan_results_returned"])
        self.assertTrue(
            any(
                item.get("event") == "worker_scan_results_returned"
                and item.get("reconciled_by_router") is True
                for item in state["events"]
                if isinstance(item, dict)
            )
        )

    def test_material_scan_partial_batch_status_names_missing_role(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(
            root,
            "pm_issues_material_and_capability_scan_packets",
            {
                "packets": [
                    {
                        "packet_id": "material-scan-partial-a",
                        "to_role": "worker_a",
                        "body_text": "Inspect local materials.",
                    },
                    {
                        "packet_id": "material-scan-partial-b",
                        "to_role": "worker_b",
                        "body_text": "Inspect repository state.",
                    },
                ]
            },
        )
        self.apply_next_packet_action(root, "relay_material_scan_packets")
        material_index = read_json(run_root / "material" / "material_scan_packets.json")
        for record in material_index["packets"]:
            envelope = packet_runtime.load_envelope(root, record["packet_envelope_path"])
            packet_runtime.read_packet_body_for_role(root, envelope, role=envelope["to_role"])
            if envelope["to_role"] == "worker_a":
                packet_runtime.write_result(
                    root,
                    packet_envelope=envelope,
                    completed_by_role="worker_a",
                    completed_by_agent_id="worker-a-agent",
                    result_body_text="worker A material scan result",
                    next_recipient="project_manager",
                )

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertEqual(action["label"], "controller_waits_for_remaining_material_scan_batch_results")
        self.assertEqual(action["to_role"], "worker_b")
        self.assertEqual(action["allowed_external_events"], ["worker_scan_results_returned"])

        batch_ref = read_json(run_root / "packet_batches" / "active_material_scan.json")
        batch = read_json(root / batch_ref["batch_path"])
        self.assertEqual(batch["counts"]["results_returned"], 1)
        self.assertEqual(batch["member_status"]["returned_roles"], ["worker_a"])
        self.assertEqual(batch["member_status"]["missing_roles"], ["worker_b"])
        status = read_json(run_root / "display" / "current_status_summary.json")
        partial = status["packet"]["active_batch"]["active_partial_batches"][0]
        self.assertEqual(partial["missing_roles"], ["worker_b"])
        self.assertEqual(partial["returned_roles"], ["worker_a"])

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

    def test_pm_repair_decision_rejects_legacy_event_replay_without_existing_producer(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="PM legacy replay has no current producer",
            action_type="controller_no_legal_next_action",
            payload={"path": self.rel(root, router.run_state_path(run_root)), "role": "controller"},
        )
        self.assertTrue(self.handle_pending_control_blocker(root))
        decision = self.pm_control_blocker_decision_body(
            blocker["blocker_id"],
            rerun_target="host_records_heartbeat_binding",
        )
        decision["repair_transaction"] = {"plan_kind": "event_replay"}

        with self.assertRaisesRegex(router.RouterError, "legacy event_replay repair transaction requires an existing producer"):
            router.record_external_event(
                root,
                "pm_records_control_blocker_repair_decision",
                self.role_decision_envelope(root, "control_blocks/legacy_event_replay_no_producer", decision),
            )

    def test_operation_replay_repair_transaction_queues_replay_action(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="Recorded mail delivery operation needs safe replay",
            action_type="deliver_mail",
            payload={"path": self.rel(root, router.run_state_path(run_root)), "role": "controller"},
        )
        self.assertTrue(self.handle_pending_control_blocker(root))
        decision = self.pm_control_blocker_decision_body(
            blocker["blocker_id"],
            rerun_target="host_records_heartbeat_binding",
        )
        decision["repair_transaction"] = {
            "plan_kind": "operation_replay",
            "operation_ref": {
                "operation_kind": "controller_action",
                "action_type": "deliver_mail",
            },
        }
        router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(root, "control_blocks/operation_replay_pm_repair_decision", decision),
        )

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "deliver_mail")
        self.assertEqual(action["repair_transaction_id"], read_json(router.run_state_path(run_root))["active_control_blocker"]["repair_transaction_id"])
        self.assertEqual(action["repair_execution_plan"]["mode"], "operation_replay")

    def test_controller_repair_work_packet_queues_bounded_controller_action(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="Controller needs a bounded repair packet",
            action_type="controller_no_legal_next_action",
            payload={"path": self.rel(root, state_path), "role": "controller"},
        )
        self.assertTrue(self.handle_pending_control_blocker(root))
        decision = self.pm_control_blocker_decision_body(
            blocker["blocker_id"],
            rerun_target="host_records_heartbeat_binding",
        )
        decision["repair_transaction"] = {
            "plan_kind": "controller_repair_work_packet",
            "work_packet": {
                "allowed_reads": [self.rel(root, state_path)],
                "allowed_writes": [self.rel(root, state_path)],
                "forbidden_actions": [
                    "approve gates",
                    "mutate routes",
                    "read sealed bodies",
                ],
                "success_evidence": ["controller records bounded repair evidence"],
            },
        }
        router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(root, "control_blocks/controller_repair_packet_pm_decision", decision),
        )

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "controller_repair_work_packet")
        self.assertFalse(action["controller_may_approve_gate"])
        self.assertFalse(action["controller_may_mutate_route"])
        self.assertFalse(action["controller_may_read_sealed_bodies"])
        self.assertEqual(action["repair_execution_plan"]["mode"], "controller_repair_work_packet")
        result = router.apply_action(
            root,
            "controller_repair_work_packet",
            {"status": "done", "evidence": ["controller records bounded repair evidence"]},
        )
        self.assertEqual(result["repair_transaction_id"], action["repair_transaction_id"])
        transaction = read_json(run_root / "control_blocks" / "repair_transactions" / f"{action['repair_transaction_id']}.json")
        self.assertEqual(transaction["status"], "awaiting_recheck")
        self.assertEqual(transaction["controller_repair_work_packet_result"]["status"], "done")

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
        agent_id, result_path = self.submit_current_node_result_via_active_holder(
            root,
            packet_id="node-packet-quality",
            result_body_text="reviewable result",
        )
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
                    "agent_role_map": {agent_id: "worker_a"},
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
        _, result_path = self.submit_current_node_result_via_active_holder(
            root,
            packet_id="node-packet-003",
            result_body_text="blocked result",
        )
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

        next_action = self.next_after_display_sync(root)
        self.assertNotEqual(next_action["action_type"], "confirm_controller_core_boundary")
        state = read_json(router.run_state_path(router.active_run_root(root)))  # type: ignore[arg-type]
        self.assertTrue(state["flags"]["controller_role_confirmed"])
        boundary_events = [
            item for item in state["events"]
            if item.get("event") == "controller_role_confirmed_from_router_core"
        ]
        self.assertTrue(boundary_events)
        self.assertIn("path", boundary_events[-1]["payload"])
        self.assertIn("sha256", boundary_events[-1]["payload"])
        confirmation = state["controller_boundary_confirmation"]
        self.assertEqual(
            confirmation["output_contract_id"],
            "flowpilot.output_contract.controller_boundary_confirmation.v1",
        )
        self.assertEqual(confirmation["output_type"], "controller_boundary_confirmation")
        self.assertEqual(confirmation["role_output_envelope"]["controller_visibility"], "role_output_envelope_only")

    def test_controller_boundary_done_receipt_missing_deliverable_schedules_repair(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)

        run_root, state, action = self.legacy_controller_boundary_action(root)
        self.assertEqual(action["action_type"], "confirm_controller_core_boundary")
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

        repair = self.next_after_display_sync(root)
        self.assertEqual(repair["action_type"], "complete_missing_controller_deliverable")
        self.assertEqual(repair["repair_of_controller_action_id"], entry["action_id"])
        self.assertEqual(repair["repair_attempt"], 1)
        original = read_json(router._controller_action_path(run_root, entry["action_id"]))  # type: ignore[attr-defined]
        self.assertEqual(original["status"], "repair_pending")
        self.assertEqual(original["deliverable_repair_attempts"], 1)
        self.assertEqual(original["deliverable_repair_failed_receipts"], 0)
        self.assertEqual(original["pending_deliverable_repair_action_id"], repair["controller_action_id"])
        self.assertEqual(original["pending_deliverable_repair_attempt"], 1)
        self.assertEqual(original["missing_deliverables"][0]["deliverable_id"], "controller_boundary_confirmation")
        self.assertEqual(
            original["missing_deliverables"][0]["output_contract_id"],
            "flowpilot.output_contract.controller_boundary_confirmation.v1",
        )
        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state.get("active_control_blocker"))

    def test_controller_boundary_valid_artifact_reclaims_before_repair(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)

        run_root, state, action = self.legacy_controller_boundary_action(root)
        self.assertEqual(action["action_type"], "confirm_controller_core_boundary")
        entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        router._write_controller_boundary_confirmation(root, run_root, state)  # type: ignore[attr-defined]
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

        next_action = self.next_after_display_sync(root)
        self.assertNotEqual(next_action["action_type"], "complete_missing_controller_deliverable")
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["controller_role_confirmed"])
        self.assertTrue(state["flags"]["controller_boundary_confirmation_written"])
        self.assertFalse(state.get("active_control_blocker"))

    def test_controller_boundary_handwritten_artifact_without_runtime_evidence_schedules_repair(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)

        run_root, state, action = self.legacy_controller_boundary_action(root)
        entry = router._write_controller_action_entry(root, run_root, state, action)  # type: ignore[attr-defined]
        body = router._controller_boundary_confirmation_body(root, run_root, state)  # type: ignore[attr-defined]
        router.write_json(run_root / "startup" / "controller_boundary_confirmation.json", body)
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

        repair = self.next_after_display_sync(root)
        self.assertEqual(repair["action_type"], "complete_missing_controller_deliverable")
        self.assertFalse(read_json(router.run_state_path(run_root)).get("active_control_blocker"))

    def test_controller_boundary_repair_action_resolves_original(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)

        run_root, state, action = self.legacy_controller_boundary_action(root)
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
        repair = self.next_after_display_sync(root)

        result = router.apply_action(root, "complete_missing_controller_deliverable")
        self.assertTrue(result["ok"])
        self.assertEqual(result["repair_of_controller_action_id"], entry["action_id"])
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["controller_role_confirmed"])
        original = read_json(router._controller_action_path(run_root, entry["action_id"]))  # type: ignore[attr-defined]
        repair_entry = read_json(router._controller_action_path(run_root, repair["controller_action_id"]))  # type: ignore[attr-defined]
        self.assertEqual(original["status"], "resolved")
        self.assertEqual(original["resolved_by_controller_action_id"], repair["controller_action_id"])
        self.assertIsNone(original["pending_deliverable_repair_action_id"])
        self.assertEqual(original["pending_deliverable_repair_attempt"], 0)
        self.assertEqual(repair_entry["status"], "done")

    def test_controller_boundary_repair_budget_escalates_after_two_failures(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)

        run_root, state, action = self.legacy_controller_boundary_action(root)
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
        state = read_json(router.run_state_path(run_root))
        repair_2 = state["pending_action"]
        self.assertEqual(repair_2["action_type"], "complete_missing_controller_deliverable")
        self.assertEqual(repair_2["repair_attempt"], 2)
        original = read_json(router._controller_action_path(run_root, entry["action_id"]))  # type: ignore[attr-defined]
        self.assertEqual(original["deliverable_repair_attempts"], 2)
        self.assertEqual(original["deliverable_repair_failed_receipts"], 1)
        self.assertEqual(original["pending_deliverable_repair_action_id"], repair_2["controller_action_id"])
        self.assertFalse(state.get("active_control_blocker"))

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
        self.assertEqual(original["deliverable_repair_attempts"], 2)
        self.assertEqual(original["deliverable_repair_failed_receipts"], 2)

    def test_controller_boundary_duplicate_old_receipt_does_not_block_while_second_repair_pending(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)

        run_root, state, action = self.legacy_controller_boundary_action(root)
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
        state = read_json(router.run_state_path(run_root))
        repair_2 = state["pending_action"]
        self.assertEqual(repair_2["repair_attempt"], 2)

        duplicate = router._schedule_controller_deliverable_repair(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            pending_action=repair_1,
            receipt=read_json(router._controller_receipt_path(run_root, repair_1["controller_action_id"])),  # type: ignore[attr-defined]
            apply_result={
                "applied": False,
                "repairable": True,
                "missing_deliverables": repair_1["missing_deliverables"],
            },
            source="duplicate_old_repair_receipt_replay",
        )

        self.assertFalse(duplicate["scheduled"])
        self.assertTrue(duplicate["pending_repair"])
        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state.get("active_control_blocker"))
        original = read_json(router._controller_action_path(run_root, entry["action_id"]))  # type: ignore[attr-defined]
        self.assertEqual(original["status"], "repair_pending")
        self.assertEqual(original["deliverable_repair_attempts"], 2)
        self.assertEqual(original["deliverable_repair_failed_receipts"], 1)

    def test_material_insufficient_event_records_insufficient_state(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.apply_next_non_card_action(root)
        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        self.apply_next_packet_action(root, "relay_material_scan_packets")
        run_root = self.run_root_for(root)
        material_index_path = run_root / "material" / "material_scan_packets.json"
        self.open_packets_and_write_results(root, material_index_path, result_text="insufficient material")
        router.record_external_event(root, "worker_scan_packet_bodies_delivered_after_dispatch")
        router.record_external_event(root, "worker_scan_results_returned")
        self.absorb_material_scan_results_with_pm(root, material_index_path)
        self.apply_next_non_card_action(root)
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
        self.assertEqual(ledger["source_paths"]["self_interrogation_index"], self.rel(root, run_root / "self_interrogation_index.json"))
        self.assertTrue(ledger["evidence_integrity"]["self_interrogation_index_clean"])
        self.assertGreaterEqual(ledger["counts"]["self_interrogation_record_count"], 3)
        self.assertEqual(ledger["counts"]["self_interrogation_unresolved_hard_finding_count"], 0)

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
            "self_interrogation_index_clean",
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
        self.assertTrue(closure["self_interrogation_review"]["clean"])
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

    def test_root_contract_freeze_requires_clean_self_interrogation_records(self) -> None:
        root = self.make_project()
        run_root = root / ".flowpilot" / "runs" / "run-001"
        (run_root / "reviews").mkdir(parents=True, exist_ok=True)
        (run_root / "contract.md").write_text("# contract\n", encoding="utf-8")
        (run_root / "standard_scenario_pack.json").write_text(json.dumps({"schema_version": "flowpilot.standard_scenario_pack.v1"}) + "\n", encoding="utf-8")
        (run_root / "reviews" / "root_contract_challenge.json").write_text(json.dumps({"passed": True}) + "\n", encoding="utf-8")
        (run_root / "root_acceptance_contract.json").write_text(
            json.dumps(
                {
                    "schema_version": "flowpilot.root_acceptance_contract.v1",
                    "completion_policy": {"unresolved_residual_risks_allowed": False},
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        state = {"run_id": "run-001", "flags": {}}

        with self.assertRaisesRegex(router.RouterError, "self-interrogation index is missing"):
            router._freeze_root_acceptance_contract(root, run_root, state)  # type: ignore[attr-defined]

        (root / ".flowpilot").mkdir(exist_ok=True)
        (root / ".flowpilot" / "current.json").write_text(
            json.dumps({"current_run_root": ".flowpilot/runs/run-001"}) + "\n",
            encoding="utf-8",
        )
        self.write_self_interrogation_record(root, "startup", source_path=run_root / "contract.md")
        self.write_self_interrogation_record(root, "product_architecture", clean=False, source_path=run_root / "root_acceptance_contract.json")

        with self.assertRaisesRegex(router.RouterError, "unresolved for a hard/current"):
            router._freeze_root_acceptance_contract(root, run_root, state)  # type: ignore[attr-defined]

        self.write_self_interrogation_record(root, "product_architecture", source_path=run_root / "root_acceptance_contract.json")
        router._freeze_root_acceptance_contract(root, run_root, state)  # type: ignore[attr-defined]
        self.assertEqual(read_json(run_root / "root_acceptance_contract.json")["status"], "frozen")

    def test_current_node_packet_rejects_unresolved_node_entry_self_interrogation(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.deliver_current_node_cards(root)
        run_root = self.run_root_for(root)
        self.write_self_interrogation_record(
            root,
            "node_entry",
            clean=False,
            node_id="node-001",
            source_path=run_root / "routes" / "route-001" / "nodes" / "node-001" / "node_acceptance_plan.json",
        )
        packet = packet_runtime.create_packet(
            root,
            packet_id="node-packet-dirty-self-interrogation",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="current node work",
            metadata={"route_version": 1},
        )

        with self.assertRaisesRegex(router.RouterError, "current-node packet registration requires clean self-interrogation records") as raised:
            router.record_external_event(
                root,
                "pm_registers_current_node_packet",
                {
                    "packet_id": "node-packet-dirty-self-interrogation",
                    "packet_envelope_path": packet["body_path"].replace("packet_body.md", "packet_envelope.json"),
                },
            )
        blocker = raised.exception.control_blocker
        self.assertIsInstance(blocker, dict)
        self.assertEqual(blocker["policy_row_id"], "self_interrogation_repair")
        self.assertEqual(blocker["target_role"], "project_manager")
        self.assertIn("rerun_self_interrogation", blocker["pm_recovery_options"])
        self.assertEqual(blocker["return_policy"]["default_return_gate"], "blocked_self_interrogation_gate")

    def test_final_ledger_rejects_dirty_self_interrogation_index(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id="node-packet-self-interrogation-ledger")
        self.complete_evidence_quality_package(root)
        run_root = self.run_root_for(root)
        self.write_self_interrogation_record(
            root,
            "node_entry",
            clean=False,
            node_id="node-001",
            source_path=run_root / "routes" / "route-001" / "nodes" / "node-001" / "node_acceptance_plan.json",
        )

        self.deliver_expected_card(root, "pm.final_ledger")
        with self.assertRaisesRegex(router.RouterError, "final route-wide ledger requires clean self-interrogation records"):
            router.record_external_event(root, "pm_records_final_route_wide_ledger_clean", self.final_ledger_payload(root))

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
