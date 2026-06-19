from __future__ import annotations

import contextlib
import hashlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))

import packet_runtime  # noqa: E402
import flowpilot_runtime  # noqa: E402
import packet_control_plane_model_state  # noqa: E402
import packet_runtime_active_holder  # noqa: E402
import packet_runtime_cli  # noqa: E402
import packet_runtime_creation_startup  # noqa: E402
import packet_runtime_ledger  # noqa: E402
import packet_runtime_progress  # noqa: E402
import packet_runtime_relay_checks  # noqa: E402
import packet_runtime_sessions  # noqa: E402


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class FlowPilotPacketRuntimeTests(unittest.TestCase):
    def make_project(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="flowpilot-packets-"))
        _write_json(
            root / ".flowpilot" / "current.json",
            {
                "run_id": "run-test",
                "run_root": ".flowpilot/runs/run-test",
            },
        )
        return root

    def write_live_runtime_roles_slot(self, root: Path, *, role: str = "worker", agent_id: str = "agent-worker-1-1") -> None:
        _write_json(
            root / ".flowpilot" / "runs" / "run-test" / "role_binding_ledger.json",
            {
                "schema_version": "flowpilot.role_binding_ledger.v1",
                "run_id": "run-test",
                "role_slots": [
                    {
                        "role_key": role,
                        "status": "live_agent_started",
                        "agent_id": agent_id,
                        "binding_open_result": "opened_for_current_task",
                        "opened_for_run_id": "run-test",
                        "opened_after_startup_answers": True,
                        "role_surface_addressable": True,
                        "current_run_binding_decision": "existing_current_agent_reused",
                        "role_binding_generation": 1,
                        "role_binding_epoch": 1,
                    }
                ],
            },
        )

    def packet_dir(self, root: Path, packet_id: str = "packet-001") -> Path:
        return root / ".flowpilot" / "runs" / "run-test" / "packets" / packet_id

    def packet_envelope_path(self, root: Path, packet_id: str = "packet-001") -> Path:
        return self.packet_dir(root, packet_id) / "packet_envelope.json"

    def result_envelope_path(self, root: Path, packet_id: str = "packet-001") -> Path:
        return self.packet_dir(root, packet_id) / "result_envelope.json"

    def read_json(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def run_packet_cli(self, root: Path, args: list[str], *, expected_rc: int = 0) -> dict:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            rc = packet_runtime.main(["--root", str(root), *args])
        self.assertEqual(rc, expected_rc)
        return json.loads(output.getvalue())

    def run_packet_cli_text(self, root: Path, args: list[str], *, expected_rc: int = 0) -> str:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            rc = packet_runtime.main(["--root", str(root), *args])
        self.assertEqual(rc, expected_rc)
        return output.getvalue()

    def run_flowpilot_runtime(self, root: Path, args: list[str], *, expected_rc: int = 0) -> dict:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            rc = flowpilot_runtime.main(["--root", str(root), *args])
        self.assertEqual(rc, expected_rc)
        return json.loads(output.getvalue())

    def test_current_run_pointer_rejects_legacy_field_names(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="flowpilot-packets-legacy-pointer-"))
        try:
            _write_json(
                root / ".flowpilot" / "current.json",
                {
                    "current_run_id": "run-test",
                    "current_run_root": ".flowpilot/runs/run-test",
                },
            )
            with self.assertRaisesRegex(packet_runtime.PacketRuntimeError, "unsupported fields"):
                packet_runtime.packet_paths(root, "packet-001")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def issue_packet(self, root: Path, *, packet_id: str = "packet-001", body_text: str = "SECRET_WORKER_BODY") -> dict:
        return packet_runtime.create_packet(
            root,
            packet_id=packet_id,
            from_role="project_manager",
            to_role="worker",
            node_id="node-001",
            body_text=body_text,
        )

    def relay_packet(self, root: Path, envelope: dict, *, packet_id: str = "packet-001", to_role: str = "worker") -> dict:
        return packet_runtime.deliver_envelope_metadata(
            root,
            envelope=envelope,
            envelope_path=self.packet_envelope_path(root, packet_id),
            controller_agent_id="agent-controller-1",
            received_from_role=envelope.get("from_role"),
            relayed_to_role=to_role,
        )

    def relay_result(self, root: Path, result: dict, *, packet_id: str = "packet-001", to_role: str = "human_like_reviewer") -> dict:
        return packet_runtime.deliver_envelope_metadata(
            root,
            envelope=result,
            envelope_path=self.result_envelope_path(root, packet_id),
            controller_agent_id="agent-controller-1",
            received_from_role=result.get("completed_by_role"),
            relayed_to_role=to_role,
        )

    def test_flowpilot_runtime_current_assignment_delivery_records_ledger_and_lease(self) -> None:
        root = self.make_project()
        self.relay_packet(root, self.issue_packet(root))
        self.write_live_runtime_roles_slot(root, agent_id="agent-worker-1-runtime")

        result = self.run_flowpilot_runtime(
            root,
            [
                "issue-active-holder-lease",
                "--envelope-path",
                ".flowpilot/runs/run-test/packets/packet-001/packet_envelope.json",
                "--holder-role",
                "worker",
                "--holder-agent-id",
                "agent-worker-1-runtime",
                "--route-version",
                "1",
                "--frontier-version",
                "1",
            ],
        )

        self.assertEqual(result["holder_agent_id"], "agent-worker-1-runtime")
        self.assertEqual(result["holder_role"], "worker")
        self.assertTrue(result["holder_binding_evidence"]["current_role_binding_proven"])

        envelope = self.read_json(self.packet_envelope_path(root))
        self.assertNotIn("controller_relay", envelope)
        ledger = self.read_json(root / ".flowpilot" / "runs" / "run-test" / "packet_ledger.json")
        record = ledger["packets"][0]
        self.assertEqual(record["active_packet_holder"], "worker")
        self.assertEqual(record["active_packet_status"], "active-holder-lease-issued")
        self.assertTrue(record["active_holder_lease_issued"])
        self.assertTrue(record["active_holder_binding_proven"])
        self.assertNotIn("packet_controller_relay", record)

    def test_pm_issue_writes_physical_envelope_body_and_ledger(self) -> None:
        root = self.make_project()
        body_text = "SECRET_BODY_SENTINEL controller must never see this"

        envelope = self.issue_packet(root, body_text=body_text)

        envelope_path = self.packet_envelope_path(root)
        body_path = self.packet_dir(root) / "packet_body.md"
        ledger_path = root / ".flowpilot" / "runs" / "run-test" / "packet_ledger.json"
        status_path = root / envelope["controller_status_packet_path"]

        self.assertTrue(envelope_path.exists())
        self.assertTrue(body_path.exists())
        self.assertTrue(ledger_path.exists())
        self.assertTrue(status_path.exists())
        written_body = body_path.read_text(encoding="utf-8")
        self.assertIn(packet_runtime.PACKET_IDENTITY_MARKER, written_body)
        self.assertIn("recipient_role: worker", written_body)
        self.assertIn(body_text, written_body)
        self.assertEqual(envelope["body_hash"], hashlib.sha256(body_path.read_bytes()).hexdigest())

        ledger = self.read_json(ledger_path)
        self.assertEqual(ledger["schema_version"], "flowpilot.packet_ledger.v2")
        self.assertEqual(ledger["active_packet_id"], "packet-001")
        self.assertEqual(ledger["packets"][0]["packet_body_path"], envelope["body_path"])
        self.assertTrue(ledger["packets"][0]["physical_packet_files_written"])
        self.assertTrue(ledger["packets"][0]["controller_context_body_exclusion_verified"])
        self.assertTrue(ledger["controller_boundary"]["all_formal_mail_must_use_current_assignment"])
        self.assertTrue(ledger["controller_boundary"]["recipient_must_verify_current_assignment_before_body_open"])
        self.assertFalse(ledger["controller_boundary"]["controller_may_read_packet_body"])
        self.assertTrue(ledger["controller_boundary"]["role_output_body_must_be_file_backed"])
        self.assertTrue(ledger["controller_boundary"]["role_chat_response_must_be_envelope_only"])
        self.assertTrue(ledger["controller_boundary"]["role_chat_body_content_contaminates_mail"])

    def test_packet_ledger_corrupt_tail_is_backed_up_and_recovered(self) -> None:
        root = self.make_project()
        envelope = self.issue_packet(root)
        ledger_path = root / ".flowpilot" / "runs" / "run-test" / "packet_ledger.json"
        ledger_path.write_text(
            ledger_path.read_text(encoding="utf-8") + "\n{\"duplicate_tail\": true}\n",
            encoding="utf-8",
        )

        self.relay_packet(root, envelope)

        ledger = self.read_json(ledger_path)
        self.assertEqual(ledger["schema_version"], packet_runtime.PACKET_LEDGER_SCHEMA)
        self.assertTrue(ledger["last_recovery"]["corrupt_backup_path"])
        self.assertTrue((root / ledger["last_recovery"]["corrupt_backup_path"]).exists())
        self.assertEqual(ledger["packets"][0]["active_packet_holder"], "worker")

    def test_packet_runtime_owner_modules_expose_direct_external_contracts(self) -> None:
        root = self.make_project()
        envelope = packet_runtime_creation_startup.create_user_intake_packet(
            root,
            packet_id="startup-intake-001",
            node_id="startup-node",
            body_text="INITIAL USER REQUEST",
            run_id="run-test",
            router_owned_startup_material=True,
            body_visibility=packet_runtime.SEALED_BODY_VISIBILITY,
            startup_options={"background_collaboration_authorized": True},
        )
        ledger_record = packet_runtime_ledger.packet_ledger_record_for_envelope(root, envelope)
        self.assertIsNotNone(ledger_record)
        self.assertEqual(ledger_record["packet_id"], "startup-intake-001")
        self.assertTrue(ledger_record["router_owned_startup_material"])
        self.assertEqual(
            packet_runtime_active_holder._require_concrete_agent_id(
                "agent-worker-1-runtime",
                role="worker",
            ),
            "agent-worker-1-runtime",
        )
        self.assertEqual(packet_runtime_progress._validate_progress_message("Working on envelope metadata"), "Working on envelope metadata")
        parsed = packet_runtime_cli.parse_args(
            [
                "--root",
                str(root),
                "user-intake",
                "--packet-id",
                "startup-intake-002",
                "--node-id",
                "startup-node",
                "--background-collaboration-authorized",
                "--body-text",
                "hello",
            ]
        )
        self.assertEqual(parsed.command, "user-intake")

        relayed = packet_runtime.router_release_startup_user_intake(
            root,
            envelope=envelope,
            envelope_path=self.packet_envelope_path(root, "startup-intake-001"),
        )
        self.assertTrue(relayed["router_startup_release"]["delivered_by_router"])
        self.assertFalse(relayed["router_startup_release"]["body_was_read_by_router"])
        self.assertEqual(relayed["router_startup_release"]["recipient_open_authority"], "current_assignment_required")
        release = packet_runtime_relay_checks.verify_router_startup_release(
            relayed,
            recipient_role="project_manager",
        )
        self.assertEqual(release["relayed_to_role"], "project_manager")
        chain_audit = packet_runtime.audit_packet_chain(root, run_id="run-test", node_id="startup-node")
        self.assertEqual(chain_audit["schema_version"], packet_runtime.CHAIN_AUDIT_SCHEMA)
        self.assertEqual(chain_audit["checked_packet_count"], 1)
        session_dir = packet_runtime_sessions._runtime_sessions_dir(
            root,
            self.packet_envelope_path(root, "startup-intake-001"),
        )
        self.assertEqual(session_dir.name, "runtime_sessions")

        model_packet = packet_control_plane_model_state._packet_from_id("wrong_delivery-case")
        self.assertEqual(model_packet.delivered_to_role, "human_like_reviewer")
        self.assertFalse(
            packet_control_plane_model_state._packet_from_id(
                "missing_physical_files-case"
            ).physical_files_written
        )

    def test_controller_handoff_contains_envelope_only_not_body_content(self) -> None:
        root = self.make_project()
        body_text = "DO_NOT_LEAK_PACKET_BODY_7f4ec1"
        envelope = self.issue_packet(root, body_text=body_text)

        handoff = packet_runtime.build_controller_handoff(
            envelope,
            envelope_path=".flowpilot/runs/run-test/packets/packet-001/packet_envelope.json",
        )
        handoff_text = packet_runtime.controller_handoff_text(handoff)

        self.assertIn("packet_envelope_only", handoff_text)
        self.assertIn("packet_body.md", handoff_text)
        self.assertIn("This mail is for `worker` only", handoff_text)
        self.assertEqual(handoff["mutual_role_reminder"]["schema_version"], "flowpilot.mutual_role_reminder.v1")
        self.assertIn("You are Controller only", handoff["mutual_role_reminder"]["controller_reminder"])
        self.assertIn("project_manager", handoff["mutual_role_reminder"]["sender_reminder"])
        self.assertIn("worker", handoff["mutual_role_reminder"]["recipient_reminder"])
        self.assertIn("next envelope", handoff["reply_continuation_reminder"])
        self.assertFalse(handoff["chat_response_body_allowed"])
        self.assertNotIn(body_text, handoff_text)
        self.assertIn("read_packet_body", handoff["controller_forbidden_actions"])
        self.assertEqual(handoff["instruction"], "Deliver this envelope metadata only. Do not read, summarize, execute, edit, or quote the sealed body.")

    def test_only_target_role_reads_packet_body_for_current_assignment(self) -> None:
        root = self.make_project()
        envelope = self.issue_packet(root, body_text="worker-only instructions")

        with self.assertRaises(packet_runtime.PacketRuntimeError):
            packet_runtime.read_packet_body_for_role(root, envelope, role="controller")

        body = packet_runtime.read_packet_body_for_role(root, envelope, role="worker")
        self.assertIn(packet_runtime.PACKET_IDENTITY_MARKER, body)
        self.assertIn("recipient_role: worker", body)
        self.assertIn("mail_only_reminder", body)
        self.assertIn("worker-only instructions", body)
        opened = self.read_json(self.packet_envelope_path(root))
        self.assertEqual(opened["packet_open_work_authority"]["source"], "current_assignment")
        self.assertTrue(opened["packet_open_work_authority"]["do_not_wait_for_additional_delivery"])
        self.assertNotIn("controller_relay", opened)
        with self.assertRaises(packet_runtime.PacketRuntimeError):
            packet_runtime.read_packet_body_for_role(root, opened, role="controller")

    def test_worker_result_writes_physical_result_files_and_reviewer_passes(self) -> None:
        root = self.make_project()
        envelope = self.relay_packet(root, self.issue_packet(root))
        packet_runtime.read_packet_body_for_role(root, envelope, role="worker")

        result = packet_runtime.write_result(
            root,
            packet_envelope=envelope,
            completed_by_role="worker",
            completed_by_agent_id="agent-worker-1-1",
            result_body_text="RESULT_BODY_SECRET commands, files, screenshots, and findings",
            next_recipient="human_like_reviewer",
        )
        result_handoff = packet_runtime.build_controller_handoff(
            result,
            envelope_path=".flowpilot/runs/run-test/packets/packet-001/result_envelope.json",
        )
        result_handoff_text = packet_runtime.controller_handoff_text(result_handoff)
        self.assertEqual(result_handoff["envelope_kind"], "result_envelope")
        self.assertEqual(result_handoff["controller_visibility"], "result_envelope_only")
        self.assertIn("result_body.md", result_handoff_text)
        self.assertIn("worker", result_handoff["mutual_role_reminder"]["sender_reminder"])
        self.assertIn("human_like_reviewer", result_handoff["mutual_role_reminder"]["recipient_reminder"])
        self.assertIn("same visible mutual-role reminder", result_handoff["reply_continuation_reminder"])
        self.assertNotIn("RESULT_BODY_SECRET", result_handoff_text)

        result = self.relay_result(root, result)
        self.assertNotIn("controller_relay", result)
        packet_runtime.read_result_body_for_role(root, result, role="human_like_reviewer")
        audit = packet_runtime.validate_for_reviewer(
            root,
            packet_envelope=envelope,
            result_envelope=result,
            agent_role_map={"agent-worker-1-1": "worker"},
        )

        result_body_path = self.packet_dir(root) / "result_body.md"
        self.assertTrue(self.result_envelope_path(root).exists())
        self.assertTrue(result_body_path.exists())
        result_body = result_body_path.read_text(encoding="utf-8")
        self.assertIn(packet_runtime.RESULT_IDENTITY_MARKER, result_body)
        self.assertIn("completed_by_role: worker", result_body)
        self.assertIn("chat response must contain envelope metadata only", result_body)
        self.assertIn("RESULT_BODY_SECRET", result_body)
        self.assertEqual(result["result_body_hash"], hashlib.sha256(result_body_path.read_bytes()).hexdigest())
        self.assertTrue(audit["passed"])
        self.assertTrue(audit["packet_runtime_physical_files_checked"])
        self.assertTrue(audit["controller_context_body_exclusion_checked"])
        self.assertTrue(audit["packet_body_opened_by_target"])
        self.assertTrue(audit["result_body_opened_by_reviewer_or_pm"])
        self.assertEqual(audit["blockers"], [])
        with self.assertRaises(packet_runtime.PacketRuntimeError):
            packet_runtime.read_result_body_for_role(root, result, role="controller")

    def test_role_packet_session_opens_packet_and_generates_result_envelope(self) -> None:
        root = self.make_project()
        self.relay_packet(root, self.issue_packet(root, body_text="SESSION_PACKET_SECRET"))

        session = packet_runtime.begin_role_packet_session(
            root,
            envelope_path=".flowpilot/runs/run-test/packets/packet-001/packet_envelope.json",
            role="worker",
            agent_id="agent-worker-1-1",
        )

        self.assertIn("SESSION_PACKET_SECRET", session["body_text"])
        session_record = self.read_json(root / session["session_path"])
        self.assertEqual(session_record["schema_version"], packet_runtime.ROLE_PACKET_SESSION_SCHEMA)
        self.assertEqual(session_record["role"], "worker")
        self.assertEqual(session_record["agent_id"], "agent-worker-1-1")
        self.assertFalse(session_record["body_text_persisted_in_session"])
        self.assertNotIn("body_text", session_record)
        self.assertTrue(session_record["packet_open_authorizes_work"])
        self.assertTrue(session_record["work_authority"]["authorized"])
        self.assertTrue(session_record["work_authority"]["do_not_wait_for_additional_delivery"])
        self.assertEqual(session_record["work_authority"]["required_exit"], "expected_packet_result_or_existing_formal_blocker")

        ledger_path = root / ".flowpilot" / "runs" / "run-test" / "packet_ledger.json"
        ledger = self.read_json(ledger_path)
        packet_record = ledger["packets"][0]
        self.assertEqual(packet_record["packet_runtime_session_id"], session["session_id"])
        self.assertEqual(packet_record["packet_body_opened_by_agent_id"], "agent-worker-1-1")
        self.assertTrue(packet_record["packet_body_opened_by_runtime_session"])
        self.assertTrue(packet_record["packet_open_authorizes_work"])
        self.assertEqual(packet_record["packet_open_required_exit"], "expected_packet_result_or_existing_formal_blocker")

        opened_envelope = self.read_json(self.packet_envelope_path(root))
        self.assertTrue(opened_envelope["packet_open_work_authority"]["authorized"])
        status_packet = self.read_json(root / opened_envelope["controller_status_packet_path"])
        self.assertTrue(status_packet["work_authority"]["authorized"])

        result = packet_runtime.complete_role_packet_session(
            root,
            session_path=session["session_path"],
            result_body_text="SESSION_RESULT_SECRET commands, files, screenshots, and findings",
            next_recipient="human_like_reviewer",
        )

        self.assertEqual(result["completed_by_role"], "worker")
        self.assertEqual(result["completed_by_agent_id"], "agent-worker-1-1")
        self.assertEqual(result["source_packet_runtime_session_id"], session["session_id"])
        self.assertTrue(result["result_generated_by_runtime_session"])
        result_file = self.read_json(self.result_envelope_path(root))
        self.assertEqual(result_file["source_packet_runtime_session_id"], session["session_id"])

        opened_envelope = packet_runtime.load_envelope(
            root,
            ".flowpilot/runs/run-test/packets/packet-001/packet_envelope.json",
        )
        audit = packet_runtime.validate_result_ready_for_reviewer_relay(
            root,
            packet_envelope=opened_envelope,
            result_envelope=result,
            agent_role_map={"agent-worker-1-1": "worker"},
        )
        self.assertTrue(audit["passed"])
        self.assertEqual(
            audit["recipient_neutral_schema_version"],
            "flowpilot.result_ready_for_recipient_relay_audit.v1",
        )
        neutral_audit = packet_runtime.validate_result_ready_for_recipient_relay(
            root,
            packet_envelope=opened_envelope,
            result_envelope=result,
            agent_role_map={"agent-worker-1-1": "worker"},
        )
        self.assertTrue(neutral_audit["passed"])
        self.assertEqual(
            neutral_audit["schema_version"],
            "flowpilot.result_ready_for_recipient_relay_audit.v1",
        )

        ledger = self.read_json(ledger_path)
        packet_record = ledger["packets"][0]
        self.assertEqual(packet_record["result_runtime_session_id"], session["session_id"])
        self.assertTrue(packet_record["result_generated_by_runtime_session"])
        self.assertEqual(packet_record["completed_by_agent_id"], "agent-worker-1-1")

    def test_controller_aside_is_process_metadata_on_packet_status_and_result(self) -> None:
        root = self.make_project()
        envelope = self.issue_packet(root)

        self.assertTrue(
            envelope["controller_process_aside_contract"]["authority_boundary"]["does_not_satisfy_wait"]
        )
        self.assertFalse(
            envelope["controller_process_aside_contract"]["authority_boundary"]["router_semantic_inspection_allowed"]
        )

        status = packet_runtime.update_controller_progress(
            root,
            envelope_path=self.packet_envelope_path(root),
            role="worker",
            agent_id="agent-worker-1-aside",
            progress=35,
            message="Working on packet envelope metadata.",
            controller_aside="I opened the packet and am checking the return shape.",
        )
        aside = status["controller_aside"]
        self.assertEqual(aside["to_role"], "controller")
        self.assertEqual(aside["text"], "I opened the packet and am checking the return shape.")
        self.assertTrue(aside["not_formal_evidence"])
        self.assertTrue(aside["does_not_satisfy_wait"])
        self.assertFalse(aside["router_semantic_inspection_allowed"])

        result = packet_runtime.write_result(
            root,
            packet_envelope=envelope,
            completed_by_role="worker",
            completed_by_agent_id="agent-worker-1-aside",
            result_body_text="Packet result body stays sealed from Controller.",
            next_recipient="human_like_reviewer",
            strict_role=False,
            controller_aside="Submitted the result envelope; waiting for Router handling.",
        )
        self.assertEqual(
            result["controller_aside"]["text"],
            "Submitted the result envelope; waiting for Router handling.",
        )
        self.assertTrue(result["controller_aside"]["not_decision_or_approval"])
        latest_status = self.read_json(root / envelope["controller_status_packet_path"])
        self.assertEqual(
            latest_status["controller_aside"]["text"],
            "Submitted the result envelope; waiting for Router handling.",
        )

        with self.assertRaisesRegex(packet_runtime.PacketRuntimeError, "controller_aside"):
            packet_runtime.update_controller_progress(
                root,
                envelope_path=self.packet_envelope_path(root),
                role="worker",
                agent_id="agent-worker-1-aside",
                progress=40,
                message="Still working.",
                controller_aside="line1\nline2\nline3\nline4",
            )

    def test_result_review_session_records_reviewer_receipt_without_persisting_body(self) -> None:
        root = self.make_project()
        self.relay_packet(root, self.issue_packet(root))
        worker_session = packet_runtime.begin_role_packet_session(
            root,
            envelope_path=".flowpilot/runs/run-test/packets/packet-001/packet_envelope.json",
            role="worker",
            agent_id="agent-worker-1-1",
        )
        result = packet_runtime.complete_role_packet_session(
            root,
            session_path=worker_session["session_path"],
            result_body_text="REVIEW_SESSION_RESULT_SECRET commands, files, screenshots, and findings",
            next_recipient="human_like_reviewer",
        )
        result = self.relay_result(root, result)

        review_session = packet_runtime.begin_result_review_session(
            root,
            result_envelope_path=".flowpilot/runs/run-test/packets/packet-001/result_envelope.json",
            role="human_like_reviewer",
            agent_id="agent-reviewer-1",
        )

        self.assertIn("REVIEW_SESSION_RESULT_SECRET", review_session["body_text"])
        session_record = self.read_json(root / review_session["session_path"])
        self.assertEqual(session_record["schema_version"], packet_runtime.RESULT_REVIEW_SESSION_SCHEMA)
        self.assertEqual(session_record["role"], "human_like_reviewer")
        self.assertEqual(session_record["agent_id"], "agent-reviewer-1")
        self.assertEqual(session_record["source_packet_runtime_session_id"], worker_session["session_id"])
        self.assertFalse(session_record["body_text_persisted_in_session"])
        self.assertNotIn("body_text", session_record)

        relayed_result = packet_runtime.load_envelope(
            root,
            ".flowpilot/runs/run-test/packets/packet-001/result_envelope.json",
        )
        opened_envelope = packet_runtime.load_envelope(
            root,
            ".flowpilot/runs/run-test/packets/packet-001/packet_envelope.json",
        )
        audit = packet_runtime.validate_for_reviewer(
            root,
            packet_envelope=opened_envelope,
            result_envelope=relayed_result,
            agent_role_map={"agent-worker-1-1": "worker"},
        )
        self.assertTrue(audit["passed"])

        ledger_path = root / ".flowpilot" / "runs" / "run-test" / "packet_ledger.json"
        ledger = self.read_json(ledger_path)
        packet_record = ledger["packets"][0]
        self.assertEqual(packet_record["result_review_runtime_session_id"], review_session["session_id"])
        self.assertEqual(packet_record["result_body_opened_by_agent_id"], "agent-reviewer-1")
        self.assertTrue(packet_record["result_body_opened_by_runtime_session"])

    def test_reviewer_audit_requires_ledger_open_receipts_not_envelope_markers_only(self) -> None:
        root = self.make_project()
        envelope = self.relay_packet(root, self.issue_packet(root))
        packet_runtime.read_packet_body_for_role(root, envelope, role="worker")
        result = packet_runtime.write_result(
            root,
            packet_envelope=envelope,
            completed_by_role="worker",
            completed_by_agent_id="agent-worker-1-1",
            result_body_text="valid result",
            next_recipient="human_like_reviewer",
        )
        result = self.relay_result(root, result)
        forged_result = dict(result)
        forged_result["result_body_opened_by_role"] = {
            "role": "human_like_reviewer",
            "opened_at": "2026-05-07T00:00:00Z",
            "body_hash_verified": True,
        }

        audit = packet_runtime.validate_for_reviewer(
            root,
            packet_envelope=envelope,
            result_envelope=forged_result,
            agent_role_map={"agent-worker-1-1": "worker"},
        )

        self.assertFalse(audit["passed"])
        self.assertTrue(audit["result_body_opened_by_reviewer_or_pm"])
        self.assertFalse(audit["packet_ledger_result_body_opened_by_reviewer_or_pm"])
        self.assertIn("packet_ledger_missing_result_body_open_receipt", audit["blockers"])

    def test_worker_result_requires_packet_ledger_open_receipt_not_envelope_marker_only(self) -> None:
        root = self.make_project()
        envelope = self.relay_packet(root, self.issue_packet(root))
        forged_envelope = dict(envelope)
        forged_envelope["body_opened_by_role"] = {
            "role": "worker",
            "opened_at": "2026-05-07T00:00:00Z",
            "body_hash_verified": True,
        }

        with self.assertRaisesRegex(packet_runtime.PacketRuntimeError, "packet ledger missing packet body open receipt"):
            packet_runtime.write_result(
                root,
                packet_envelope=forged_envelope,
                completed_by_role="worker",
                completed_by_agent_id="agent-worker-1-1",
                result_body_text="forged open marker result",
                next_recipient="human_like_reviewer",
            )

    def test_result_ready_for_reviewer_relay_requires_result_ledger_absorption(self) -> None:
        root = self.make_project()
        envelope = self.relay_packet(root, self.issue_packet(root))
        packet_runtime.read_packet_body_for_role(root, envelope, role="worker")
        result = packet_runtime.write_result(
            root,
            packet_envelope=envelope,
            completed_by_role="worker",
            completed_by_agent_id="agent-worker-1-1",
            result_body_text="valid result",
            next_recipient="human_like_reviewer",
        )
        ledger_path = root / ".flowpilot" / "runs" / "run-test" / "packet_ledger.json"
        ledger = self.read_json(ledger_path)
        ledger["packets"][0]["result_body_hash"] = "stale-result-hash"
        _write_json(ledger_path, ledger)

        audit = packet_runtime.validate_result_ready_for_reviewer_relay(
            root,
            packet_envelope=envelope,
            result_envelope=result,
            agent_role_map={"agent-worker-1-1": "worker"},
        )

        self.assertFalse(audit["passed"])
        self.assertFalse(audit["packet_ledger_result_absorbed"])
        self.assertIn("packet_ledger_missing_result_absorption", audit["blockers"])

    def test_reviewer_audit_rejects_completed_agent_id_role_string(self) -> None:
        root = self.make_project()
        envelope = self.relay_packet(root, self.issue_packet(root))
        packet_runtime.read_packet_body_for_role(root, envelope, role="worker")
        result = packet_runtime.write_result(
            root,
            packet_envelope=envelope,
            completed_by_role="worker",
            completed_by_agent_id="worker",
            result_body_text="valid result with role string as agent id",
            next_recipient="human_like_reviewer",
        )
        result = self.relay_result(root, result)
        packet_runtime.read_result_body_for_role(root, result, role="human_like_reviewer")

        audit = packet_runtime.validate_for_reviewer(
            root,
            packet_envelope=envelope,
            result_envelope=result,
            agent_role_map={"worker": "worker"},
        )

        self.assertFalse(audit["passed"])
        self.assertIn("completed_agent_id_is_role_key_not_agent_id", audit["blockers"])
        self.assertIn("completed_agent_id_not_assigned_to_role", audit["blockers"])

    def test_reviewer_blocks_packet_or_result_hash_mismatch(self) -> None:
        root = self.make_project()
        envelope = self.relay_packet(root, self.issue_packet(root))
        packet_runtime.read_packet_body_for_role(root, envelope, role="worker")
        result = packet_runtime.write_result(
            root,
            packet_envelope=envelope,
            completed_by_role="worker",
            completed_by_agent_id="agent-worker-1-1",
            result_body_text="valid result",
            next_recipient="human_like_reviewer",
        )
        result = self.relay_result(root, result)
        packet_runtime.read_result_body_for_role(root, result, role="human_like_reviewer")
        body_path = root / envelope["body_path"]
        body_path.write_text("tampered packet body", encoding="utf-8")

        audit = packet_runtime.validate_for_reviewer(
            root,
            packet_envelope=envelope,
            result_envelope=result,
            agent_role_map={"agent-worker-1-1": "worker"},
        )

        self.assertFalse(audit["passed"])
        self.assertIn("packet_body_hash_mismatch", audit["blockers"])

    def test_reviewer_blocks_wrong_role_and_controller_origin(self) -> None:
        root = self.make_project()
        envelope = self.relay_packet(root, self.issue_packet(root))
        packet_runtime.read_packet_body_for_role(root, envelope, role="worker")

        wrong_role_result = packet_runtime.write_result(
            root,
            packet_envelope=envelope,
            completed_by_role="human_like_reviewer",
            completed_by_agent_id="agent-reviewer-1",
            result_body_text="wrong role result",
            next_recipient="human_like_reviewer",
            strict_role=False,
        )
        wrong_role_result = self.relay_result(root, wrong_role_result)
        packet_runtime.read_result_body_for_role(root, wrong_role_result, role="human_like_reviewer")
        wrong_role_audit = packet_runtime.validate_for_reviewer(
            root,
            packet_envelope=envelope,
            result_envelope=wrong_role_result,
            agent_role_map={"agent-reviewer-1": "human_like_reviewer"},
        )
        self.assertFalse(wrong_role_audit["passed"])
        self.assertIn("result_completed_by_wrong_role", wrong_role_audit["blockers"])

        controller_result = packet_runtime.write_result(
            root,
            packet_envelope=envelope,
            completed_by_role="controller",
            completed_by_agent_id="agent-controller-1",
            result_body_text="controller tried to complete worker scope",
            next_recipient="human_like_reviewer",
            strict_role=False,
        )
        controller_result = self.relay_result(root, controller_result)
        packet_runtime.read_result_body_for_role(root, controller_result, role="human_like_reviewer")
        controller_audit = packet_runtime.validate_for_reviewer(
            root,
            packet_envelope=envelope,
            result_envelope=controller_result,
            agent_role_map={"agent-controller-1": "controller"},
        )
        self.assertFalse(controller_audit["passed"])
        self.assertIn("controller_origin_artifact", controller_audit["blockers"])
        self.assertIn("result_completed_by_wrong_role", controller_audit["blockers"])

    def test_controller_contamination_returns_to_sender_and_blocks_chain(self) -> None:
        root = self.make_project()
        envelope = self.issue_packet(root)

        with self.assertRaises(packet_runtime.PacketRuntimeError):
            packet_runtime.deliver_envelope_metadata(
                root,
                envelope=envelope,
                envelope_path=self.packet_envelope_path(root),
                controller_agent_id="agent-controller-1",
                received_from_role="project_manager",
                relayed_to_role="worker",
                body_was_read_by_controller=True,
            )

        contaminated = self.read_json(self.packet_envelope_path(root))
        self.assertTrue(contaminated["controller_return_to_sender"]["contaminated"])
        audit = packet_runtime.audit_packet_chain(root, node_id="node-001")
        self.assertFalse(audit["passed"])
        self.assertIn("contaminated_packet_without_replacement", {item["code"] for item in audit["blockers"]})

    def test_chain_audit_flags_unopened_packet_for_pm_decision(self) -> None:
        root = self.make_project()
        self.relay_packet(root, self.issue_packet(root))

        audit = packet_runtime.audit_packet_chain(root, node_id="node-001")

        self.assertFalse(audit["passed"])
        self.assertTrue(audit["pm_decision_required"])
        self.assertIn("packet_body_unopened_by_recipient", {item["code"] for item in audit["blockers"]})
        self.assertIn("create_repair_node", audit["pm_options"])

    def test_replacement_packet_satisfies_contaminated_packet_audit(self) -> None:
        root = self.make_project()
        original = self.issue_packet(root, packet_id="packet-old")
        with self.assertRaises(packet_runtime.PacketRuntimeError):
            packet_runtime.deliver_envelope_metadata(
                root,
                envelope=original,
                envelope_path=self.packet_envelope_path(root, "packet-old"),
                controller_agent_id="agent-controller-1",
                received_from_role="project_manager",
                relayed_to_role="worker",
                body_was_read_by_controller=True,
            )

        replacement = packet_runtime.create_packet(
            root,
            packet_id="packet-new",
            from_role="project_manager",
            to_role="worker",
            node_id="node-001",
            body_text="replacement work",
            replacement_for="packet-old",
        )
        replacement = self.relay_packet(root, replacement, packet_id="packet-new")
        packet_runtime.read_packet_body_for_role(root, replacement, role="worker")
        audit = packet_runtime.audit_packet_chain(root, node_id="node-001")
        codes = {item["code"] for item in audit["blockers"]}
        self.assertNotIn("contaminated_packet_without_replacement", codes)

    def test_user_intake_packet_records_startup_visibility_and_relays_to_pm(self) -> None:
        root = self.make_project()
        envelope = packet_runtime.create_user_intake_packet(
            root,
            packet_id="user-intake-001",
            node_id="startup",
            body_text="user task prompt",
            startup_options={
                "background_collaboration_authorized": True,
            },
        )
        envelope = packet_runtime.deliver_envelope_metadata(
            root,
            envelope=envelope,
            envelope_path=self.packet_envelope_path(root, "user-intake-001"),
            controller_agent_id="agent-controller-1",
            received_from_role="user",
            relayed_to_role="project_manager",
        )

        self.assertEqual(envelope["packet_type"], "user_intake")
        self.assertEqual(envelope["body_visibility"], packet_runtime.USER_INTAKE_BODY_VISIBILITY)
        self.assertNotIn("controller_relay", envelope)
        user_intake_body = packet_runtime.read_packet_body_for_role(root, envelope, role="project_manager")
        self.assertIn(packet_runtime.PACKET_IDENTITY_MARKER, user_intake_body)
        self.assertIn("recipient_role: project_manager", user_intake_body)
        self.assertIn("pm_startup_repair_request", user_intake_body)
        self.assertIn("user task prompt", user_intake_body)
        opened_envelope = self.read_json(self.packet_envelope_path(root, "user-intake-001"))
        self.assertEqual(
            opened_envelope["packet_open_work_authority"]["required_exit"],
            "expected_pm_packet_output_or_existing_pm_recovery_decision",
        )
        self.assertTrue(opened_envelope["metadata"]["controller_bootstrap_scope"]["background_collaboration_authorized"])
        self.assertNotIn("runtime_role_assistance_authorized", opened_envelope["metadata"]["controller_bootstrap_scope"])
        self.assertNotIn("heartbeat_requested", opened_envelope["metadata"]["controller_bootstrap_scope"])

    def test_user_intake_rejects_unsupported_startup_option_fields(self) -> None:
        root = self.make_project()
        with self.assertRaisesRegex(packet_runtime.PacketRuntimeError, "unsupported startup option field"):
            packet_runtime.create_user_intake_packet(
                root,
                packet_id="user-intake-legacy",
                node_id="startup",
                body_text="user task prompt",
                startup_options={
                    "runtime_role_assistance_authorized": True,
                    "heartbeat_requested": True,
                    "scheduled_continuation": "manual",
                    "display_surface": "chat",
                    "background_collaboration_authorized": True,
                },
            )

    def test_user_intake_router_startup_release_uses_current_assignment_authority(self) -> None:
        root = self.make_project()
        envelope = packet_runtime.create_user_intake_packet(
            root,
            packet_id="user-intake-router-only",
            node_id="startup",
            body_text="user task prompt",
            body_visibility=packet_runtime.SEALED_BODY_VISIBILITY,
            router_owned_startup_material=True,
            startup_options={"background_collaboration_authorized": True},
        )
        released = packet_runtime.router_release_startup_user_intake(
            root,
            envelope=envelope,
            envelope_path=self.packet_envelope_path(root, "user-intake-router-only"),
            released_to_role="project_manager",
        )

        self.assertEqual(released["router_startup_release"]["recipient_open_authority"], "current_assignment_required")
        body = packet_runtime.read_packet_body_for_role(root, released, role="project_manager")
        self.assertIn("user task prompt", body)
        opened = self.read_json(self.packet_envelope_path(root, "user-intake-router-only"))
        self.assertEqual(opened["packet_open_work_authority"]["source"], "current_assignment")
        self.assertTrue(opened["packet_open_work_authority"]["do_not_wait_for_additional_delivery"])

    def test_packet_identity_boundary_is_required_on_read(self) -> None:
        root = self.make_project()
        envelope = self.relay_packet(root, self.issue_packet(root, body_text="worker work"))
        body_path = root / envelope["body_path"]
        body_path.write_text("worker work without identity boundary", encoding="utf-8")
        envelope["body_hash"] = hashlib.sha256(body_path.read_bytes()).hexdigest()

        with self.assertRaises(packet_runtime.PacketRuntimeError):
            packet_runtime.read_packet_body_for_role(root, envelope, role="worker")

    def test_result_identity_boundary_is_required_on_read(self) -> None:
        root = self.make_project()
        envelope = self.relay_packet(root, self.issue_packet(root))
        packet_runtime.read_packet_body_for_role(root, envelope, role="worker")
        result = packet_runtime.write_result(
            root,
            packet_envelope=envelope,
            completed_by_role="worker",
            completed_by_agent_id="agent-worker-1-1",
            result_body_text="valid result",
            next_recipient="human_like_reviewer",
        )
        result = self.relay_result(root, result)
        result_path = root / result["result_body_path"]
        result_path.write_text("result without identity boundary", encoding="utf-8")
        result["result_body_hash"] = hashlib.sha256(result_path.read_bytes()).hexdigest()

        with self.assertRaises(packet_runtime.PacketRuntimeError):
            packet_runtime.read_result_body_for_role(root, result, role="human_like_reviewer")

    def test_active_holder_fast_lane_closes_with_controller_notice(self) -> None:
        root = self.make_project()
        envelope = self.relay_packet(root, self.issue_packet(root))
        self.write_live_runtime_roles_slot(root)
        lease = packet_runtime.issue_active_holder_lease(
            root,
            packet_envelope=envelope,
            holder_role="worker",
            holder_agent_id="agent-worker-1-1",
            route_version=1,
            frontier_version=1,
        )

        ack = packet_runtime.active_holder_ack(
            root,
            lease_path=lease["lease_path"],
            role="worker",
            agent_id="agent-worker-1-1",
            route_version=1,
            frontier_version=1,
        )
        self.assertEqual(ack["event"], "active_holder_ack")

        progress = packet_runtime.active_holder_progress(
            root,
            lease_path=lease["lease_path"],
            role="worker",
            agent_id="agent-worker-1-1",
            progress=20,
            message="Implementation is underway.",
            route_version=1,
            frontier_version=1,
        )
        self.assertEqual(progress["holder"], "worker")
        self.assertEqual(progress["status"], "working")

        session = packet_runtime.begin_role_packet_session(
            root,
            envelope_path=".flowpilot/runs/run-test/packets/packet-001/packet_envelope.json",
            role="worker",
            agent_id="agent-worker-1-1",
        )
        self.assertEqual(session["agent_id"], "agent-worker-1-1")

        submission = packet_runtime.active_holder_submit_result(
            root,
            lease_path=lease["lease_path"],
            role="worker",
            agent_id="agent-worker-1-1",
            result_body_text="FAST_LANE_RESULT_SECRET commands and files",
            next_recipient="human_like_reviewer",
            route_version=1,
            frontier_version=1,
        )

        self.assertTrue(submission["passed"])
        notice = submission["controller_next_action_notice"]
        self.assertEqual(notice["schema_version"], packet_runtime.CONTROLLER_NEXT_ACTION_NOTICE_SCHEMA)
        self.assertEqual(notice["next_action"], "deliver_result_to_reviewer")
        self.assertEqual(notice["to"], "controller")
        self.assertFalse(notice["controller_may_read_result_body"])
        notice_path = self.packet_dir(root) / "controller_next_action_notice.json"
        self.assertTrue(notice_path.exists())

        ledger = self.read_json(root / ".flowpilot" / "runs" / "run-test" / "packet_ledger.json")
        packet_record = ledger["packets"][0]
        self.assertTrue(packet_record["active_holder_lease_issued"])
        self.assertTrue(packet_record["active_holder_ack_recorded"])
        self.assertTrue(packet_record["active_holder_progress_recorded"])
        self.assertTrue(packet_record["fast_lane_result_mechanics_passed"])
        self.assertTrue(packet_record["fast_lane_controller_notice_written"])
        self.assertEqual(ledger["active_packet_holder"], "controller")
        self.assertEqual(ledger["active_packet_status"], "router-next-action-ready-for-controller")

        result = self.read_json(self.result_envelope_path(root))
        self.assertNotIn("controller_relay", result)
        relayed = self.relay_result(root, result)
        packet_runtime.read_result_body_for_role(root, relayed, role="human_like_reviewer")
        audit = packet_runtime.validate_for_reviewer(
            root,
            packet_envelope=self.read_json(self.packet_envelope_path(root)),
            result_envelope=relayed,
            agent_role_map={"agent-worker-1-1": "worker"},
        )
        self.assertTrue(audit["passed"])

    def test_active_holder_lease_requires_live_runtime_roles_slot(self) -> None:
        root = self.make_project()
        envelope = self.relay_packet(root, self.issue_packet(root))

        with self.assertRaisesRegex(packet_runtime.PacketRuntimeError, "requires current role slot"):
            packet_runtime.issue_active_holder_lease(
                root,
                packet_envelope=envelope,
                holder_role="worker",
                holder_agent_id="agent-worker-1-1",
                route_version=1,
                frontier_version=1,
            )

    def test_active_holder_lease_rejects_replacement_without_current_binding_evidence(self) -> None:
        root = self.make_project()
        envelope = self.relay_packet(root, self.issue_packet(root))
        _write_json(
            root / ".flowpilot" / "runs" / "run-test" / "role_binding_ledger.json",
            {
                "schema_version": "flowpilot.role_binding_ledger.v1",
                "run_id": "run-test",
                "role_slots": [
                    {
                        "role_key": "worker",
                        "status": "live_agent_recovered",
                        "agent_id": "replacement-worker-1",
                        "role_surface_addressable": False,
                        "current_run_binding_decision": "current_run_replacement_opened",
                        "last_role_recovery_result": "targeted_replacement_opened",
                    }
                ],
            },
        )

        with self.assertRaisesRegex(packet_runtime.PacketRuntimeError, "requires current role binding evidence"):
            packet_runtime.issue_active_holder_lease(
                root,
                packet_envelope=envelope,
                holder_role="worker",
                holder_agent_id="replacement-worker-1",
                route_version=1,
                frontier_version=1,
            )

    def test_active_holder_cli_round_trip_writes_controller_notice(self) -> None:
        root = self.make_project()
        self.relay_packet(root, self.issue_packet(root))
        self.write_live_runtime_roles_slot(root)
        packet_path = ".flowpilot/runs/run-test/packets/packet-001/packet_envelope.json"

        lease = self.run_packet_cli(
            root,
            [
                "issue-active-holder-lease",
                "--envelope-path",
                packet_path,
                "--holder-role",
                "worker",
                "--holder-agent-id",
                "agent-worker-1-1",
                "--route-version",
                "1",
                "--frontier-version",
                "1",
            ],
        )
        self.assertEqual(lease["holder_agent_id"], "agent-worker-1-1")

        ack = self.run_packet_cli(
            root,
            [
                "active-holder-ack",
                "--lease-path",
                lease["lease_path"],
                "--role",
                "worker",
                "--agent-id",
                "agent-worker-1-1",
                "--route-version",
                "1",
                "--frontier-version",
                "1",
            ],
        )
        self.assertEqual(ack["event"], "active_holder_ack")

        body_text = self.run_packet_cli_text(
            root,
            [
                "read-packet",
                "--envelope-path",
                packet_path,
                "--role",
                "worker",
            ],
        )
        self.assertIn("SECRET_WORKER_BODY", body_text)
        submission = self.run_packet_cli(
            root,
            [
                "active-holder-submit-result",
                "--lease-path",
                lease["lease_path"],
                "--role",
                "worker",
                "--agent-id",
                "agent-worker-1-1",
                "--result-body-text",
                "CLI fast lane result",
                "--next-recipient",
                "human_like_reviewer",
                "--route-version",
                "1",
                "--frontier-version",
                "1",
            ],
        )

        self.assertTrue(submission["passed"])
        notice = submission["controller_next_action_notice"]
        self.assertEqual(notice["notice_path"], ".flowpilot/runs/run-test/packets/packet-001/controller_next_action_notice.json")
        self.assertEqual(notice["next_action"], "deliver_result_to_reviewer")

    def test_active_holder_fast_lane_rejects_wrong_or_stale_contact(self) -> None:
        root = self.make_project()
        envelope = self.relay_packet(root, self.issue_packet(root))
        self.write_live_runtime_roles_slot(root)
        lease = packet_runtime.issue_active_holder_lease(
            root,
            packet_envelope=envelope,
            holder_role="worker",
            holder_agent_id="agent-worker-1-1",
            route_version=1,
            frontier_version=1,
        )

        with self.assertRaisesRegex(packet_runtime.PacketRuntimeError, "wrong_role"):
            packet_runtime.active_holder_ack(
                root,
                lease_path=lease["lease_path"],
                role="human_like_reviewer",
                agent_id="agent-reviewer-1",
                route_version=1,
                frontier_version=1,
            )

        with self.assertRaisesRegex(packet_runtime.PacketRuntimeError, "wrong_agent"):
            packet_runtime.active_holder_ack(
                root,
                lease_path=lease["lease_path"],
                role="worker",
                agent_id="agent-worker-1-2",
                route_version=1,
                frontier_version=1,
            )

        with self.assertRaisesRegex(packet_runtime.PacketRuntimeError, "route_version_stale"):
            packet_runtime.active_holder_ack(
                root,
                lease_path=lease["lease_path"],
                role="worker",
                agent_id="agent-worker-1-1",
                route_version=2,
                frontier_version=1,
            )

    def test_active_holder_mechanical_reject_keeps_current_holder(self) -> None:
        root = self.make_project()
        envelope = self.relay_packet(root, self.issue_packet(root))
        self.write_live_runtime_roles_slot(root)
        lease = packet_runtime.issue_active_holder_lease(
            root,
            packet_envelope=envelope,
            holder_role="worker",
            holder_agent_id="agent-worker-1-1",
            route_version=1,
            frontier_version=1,
        )
        packet_runtime.active_holder_ack(
            root,
            lease_path=lease["lease_path"],
            role="worker",
            agent_id="agent-worker-1-1",
        )
        packet_runtime.begin_role_packet_session(
            root,
            envelope_path=".flowpilot/runs/run-test/packets/packet-001/packet_envelope.json",
            role="worker",
            agent_id="agent-worker-1-1",
        )
        wrong_agent_result = packet_runtime.write_result(
            root,
            packet_envelope=self.read_json(self.packet_envelope_path(root)),
            completed_by_role="worker",
            completed_by_agent_id="agent-worker-1-2",
            result_body_text="wrong agent result",
            next_recipient="human_like_reviewer",
        )

        rejected = packet_runtime.active_holder_submit_existing_result(
            root,
            lease_path=lease["lease_path"],
            role="worker",
            agent_id="agent-worker-1-1",
            result_envelope_path=wrong_agent_result["result_body_path"].rsplit("/", 1)[0] + "/result_envelope.json",
        )

        self.assertFalse(rejected["passed"])
        self.assertIn("active_holder_result_completed_by_wrong_agent", rejected["audit"]["blockers"])
        ledger = self.read_json(root / ".flowpilot" / "runs" / "run-test" / "packet_ledger.json")
        self.assertEqual(ledger["active_packet_holder"], "worker")
        self.assertEqual(ledger["active_packet_status"], "active-holder-mechanical-reject")
        self.assertTrue(ledger["packets"][0]["fast_lane_mechanical_reject_recorded"])
        self.assertFalse((self.packet_dir(root) / "controller_next_action_notice.json").exists())


if __name__ == "__main__":
    unittest.main()
