from __future__ import annotations

import contextlib
import hashlib
import io
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
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class FlowPilotPacketRuntimeTests(unittest.TestCase):
    def make_project(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="flowpilot-packets-"))
        _write_json(
            root / ".flowpilot" / "current.json",
            {
                "current_run_id": "run-test",
                "current_run_root": ".flowpilot/runs/run-test",
            },
        )
        return root

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

    def issue_packet(self, root: Path, *, packet_id: str = "packet-001", body_text: str = "SECRET_WORKER_BODY") -> dict:
        return packet_runtime.create_packet(
            root,
            packet_id=packet_id,
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text=body_text,
        )

    def relay_packet(self, root: Path, envelope: dict, *, packet_id: str = "packet-001", to_role: str = "worker_a") -> dict:
        return packet_runtime.controller_relay_envelope(
            root,
            envelope=envelope,
            envelope_path=self.packet_envelope_path(root, packet_id),
            controller_agent_id="agent-controller-1",
            received_from_role=envelope.get("from_role"),
            relayed_to_role=to_role,
        )

    def relay_result(self, root: Path, result: dict, *, packet_id: str = "packet-001", to_role: str = "human_like_reviewer") -> dict:
        return packet_runtime.controller_relay_envelope(
            root,
            envelope=result,
            envelope_path=self.result_envelope_path(root, packet_id),
            controller_agent_id="agent-controller-1",
            received_from_role=result.get("completed_by_role"),
            relayed_to_role=to_role,
        )

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
        self.assertIn("recipient_role: worker_a", written_body)
        self.assertIn(body_text, written_body)
        self.assertEqual(envelope["body_hash"], hashlib.sha256(body_path.read_bytes()).hexdigest())

        ledger = self.read_json(ledger_path)
        self.assertEqual(ledger["schema_version"], "flowpilot.packet_ledger.v2")
        self.assertEqual(ledger["active_packet_id"], "packet-001")
        self.assertEqual(ledger["packets"][0]["packet_body_path"], envelope["body_path"])
        self.assertTrue(ledger["packets"][0]["physical_packet_files_written"])
        self.assertTrue(ledger["packets"][0]["controller_context_body_exclusion_verified"])
        self.assertTrue(ledger["packets"][0]["controller_relay_signature_required"])
        self.assertTrue(ledger["packets"][0]["recipient_must_verify_controller_relay_before_body_open"])
        self.assertFalse(ledger["controller_boundary"]["controller_may_read_packet_body"])
        self.assertTrue(ledger["controller_boundary"]["role_output_body_must_be_file_backed"])
        self.assertTrue(ledger["controller_boundary"]["role_chat_response_must_be_envelope_only"])
        self.assertTrue(ledger["controller_boundary"]["role_chat_body_content_contaminates_mail"])

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
        self.assertIn("This mail is for `worker_a` only", handoff_text)
        self.assertEqual(handoff["mutual_role_reminder"]["schema_version"], "flowpilot.mutual_role_reminder.v1")
        self.assertIn("You are Controller only", handoff["mutual_role_reminder"]["controller_reminder"])
        self.assertIn("project_manager", handoff["mutual_role_reminder"]["sender_reminder"])
        self.assertIn("worker_a", handoff["mutual_role_reminder"]["recipient_reminder"])
        self.assertIn("next envelope", handoff["reply_continuation_reminder"])
        self.assertFalse(handoff["chat_response_body_allowed"])
        self.assertNotIn(body_text, handoff_text)
        self.assertIn("read_packet_body", handoff["controller_forbidden_actions"])
        self.assertTrue(handoff["controller_relay_signature_required"])

    def test_only_target_role_reads_packet_body_after_controller_relay(self) -> None:
        root = self.make_project()
        envelope = self.issue_packet(root, body_text="worker-only instructions")

        with self.assertRaises(packet_runtime.PacketRuntimeError):
            packet_runtime.read_packet_body_for_role(root, envelope, role="worker_a")

        envelope = self.relay_packet(root, envelope)
        self.assertIn("This mail is for `worker_a` only", envelope["controller_relay"]["recipient_role_reminder"])
        self.assertIn("You are Controller only", envelope["controller_relay"]["mutual_role_reminder"]["controller_reminder"])
        self.assertIn("project_manager", envelope["controller_relay"]["mutual_role_reminder"]["sender_reminder"])
        self.assertIn("worker_a", envelope["controller_relay"]["mutual_role_reminder"]["recipient_reminder"])
        self.assertIn("next envelope", envelope["controller_relay"]["reply_continuation_reminder"])
        self.assertFalse(envelope["controller_relay"]["chat_response_body_allowed"])
        body = packet_runtime.read_packet_body_for_role(root, envelope, role="worker_a")
        self.assertIn(packet_runtime.PACKET_IDENTITY_MARKER, body)
        self.assertIn("recipient_role: worker_a", body)
        self.assertIn("mail_only_reminder", body)
        self.assertIn("worker-only instructions", body)
        with self.assertRaises(packet_runtime.PacketRuntimeError):
            packet_runtime.read_packet_body_for_role(root, envelope, role="controller")

    def test_worker_result_writes_physical_result_files_and_reviewer_passes(self) -> None:
        root = self.make_project()
        envelope = self.relay_packet(root, self.issue_packet(root))
        packet_runtime.read_packet_body_for_role(root, envelope, role="worker_a")

        result = packet_runtime.write_result(
            root,
            packet_envelope=envelope,
            completed_by_role="worker_a",
            completed_by_agent_id="agent-worker-a-1",
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
        self.assertIn("worker_a", result_handoff["mutual_role_reminder"]["sender_reminder"])
        self.assertIn("human_like_reviewer", result_handoff["mutual_role_reminder"]["recipient_reminder"])
        self.assertIn("same visible mutual-role reminder", result_handoff["reply_continuation_reminder"])
        self.assertNotIn("RESULT_BODY_SECRET", result_handoff_text)

        result = self.relay_result(root, result)
        self.assertIn("worker_a", result["controller_relay"]["mutual_role_reminder"]["sender_reminder"])
        self.assertIn("human_like_reviewer", result["controller_relay"]["mutual_role_reminder"]["recipient_reminder"])
        self.assertIn("same visible mutual-role reminder", result["controller_relay"]["reply_continuation_reminder"])
        packet_runtime.read_result_body_for_role(root, result, role="human_like_reviewer")
        audit = packet_runtime.validate_for_reviewer(
            root,
            packet_envelope=envelope,
            result_envelope=result,
            agent_role_map={"agent-worker-a-1": "worker_a"},
        )

        result_body_path = self.packet_dir(root) / "result_body.md"
        self.assertTrue(self.result_envelope_path(root).exists())
        self.assertTrue(result_body_path.exists())
        result_body = result_body_path.read_text(encoding="utf-8")
        self.assertIn(packet_runtime.RESULT_IDENTITY_MARKER, result_body)
        self.assertIn("completed_by_role: worker_a", result_body)
        self.assertIn("chat response must contain envelope metadata only", result_body)
        self.assertIn("RESULT_BODY_SECRET", result_body)
        self.assertEqual(result["result_body_hash"], hashlib.sha256(result_body_path.read_bytes()).hexdigest())
        self.assertTrue(audit["passed"])
        self.assertTrue(audit["packet_runtime_physical_files_checked"])
        self.assertTrue(audit["controller_context_body_exclusion_checked"])
        self.assertTrue(audit["packet_controller_relay_valid"])
        self.assertTrue(audit["result_controller_relay_valid"])
        self.assertEqual(audit["blockers"], [])
        with self.assertRaises(packet_runtime.PacketRuntimeError):
            packet_runtime.read_result_body_for_role(root, result, role="controller")

    def test_role_packet_session_opens_packet_and_generates_result_envelope(self) -> None:
        root = self.make_project()
        self.relay_packet(root, self.issue_packet(root, body_text="SESSION_PACKET_SECRET"))

        session = packet_runtime.begin_role_packet_session(
            root,
            envelope_path=".flowpilot/runs/run-test/packets/packet-001/packet_envelope.json",
            role="worker_a",
            agent_id="agent-worker-a-1",
        )

        self.assertIn("SESSION_PACKET_SECRET", session["body_text"])
        session_record = self.read_json(root / session["session_path"])
        self.assertEqual(session_record["schema_version"], packet_runtime.ROLE_PACKET_SESSION_SCHEMA)
        self.assertEqual(session_record["role"], "worker_a")
        self.assertEqual(session_record["agent_id"], "agent-worker-a-1")
        self.assertFalse(session_record["body_text_persisted_in_session"])
        self.assertNotIn("body_text", session_record)

        ledger_path = root / ".flowpilot" / "runs" / "run-test" / "packet_ledger.json"
        ledger = self.read_json(ledger_path)
        packet_record = ledger["packets"][0]
        self.assertEqual(packet_record["packet_runtime_session_id"], session["session_id"])
        self.assertEqual(packet_record["packet_body_opened_by_agent_id"], "agent-worker-a-1")
        self.assertTrue(packet_record["packet_body_opened_by_runtime_session"])

        result = packet_runtime.complete_role_packet_session(
            root,
            session_path=session["session_path"],
            result_body_text="SESSION_RESULT_SECRET commands, files, screenshots, and findings",
            next_recipient="human_like_reviewer",
        )

        self.assertEqual(result["completed_by_role"], "worker_a")
        self.assertEqual(result["completed_by_agent_id"], "agent-worker-a-1")
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
            agent_role_map={"agent-worker-a-1": "worker_a"},
        )
        self.assertTrue(audit["passed"])

        ledger = self.read_json(ledger_path)
        packet_record = ledger["packets"][0]
        self.assertEqual(packet_record["result_runtime_session_id"], session["session_id"])
        self.assertTrue(packet_record["result_generated_by_runtime_session"])
        self.assertEqual(packet_record["completed_by_agent_id"], "agent-worker-a-1")

    def test_result_review_session_records_reviewer_receipt_without_persisting_body(self) -> None:
        root = self.make_project()
        self.relay_packet(root, self.issue_packet(root))
        worker_session = packet_runtime.begin_role_packet_session(
            root,
            envelope_path=".flowpilot/runs/run-test/packets/packet-001/packet_envelope.json",
            role="worker_a",
            agent_id="agent-worker-a-1",
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
            agent_role_map={"agent-worker-a-1": "worker_a"},
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
        packet_runtime.read_packet_body_for_role(root, envelope, role="worker_a")
        result = packet_runtime.write_result(
            root,
            packet_envelope=envelope,
            completed_by_role="worker_a",
            completed_by_agent_id="agent-worker-a-1",
            result_body_text="valid result",
            next_recipient="human_like_reviewer",
        )
        result = self.relay_result(root, result)
        forged_result = dict(result)
        forged_result["result_body_opened_by_role"] = {
            "role": "human_like_reviewer",
            "opened_at": "2026-05-07T00:00:00Z",
            "controller_relay_verified": True,
            "body_hash_verified": True,
        }

        audit = packet_runtime.validate_for_reviewer(
            root,
            packet_envelope=envelope,
            result_envelope=forged_result,
            agent_role_map={"agent-worker-a-1": "worker_a"},
        )

        self.assertFalse(audit["passed"])
        self.assertTrue(audit["result_body_opened_by_reviewer_or_pm_after_relay_check"])
        self.assertFalse(audit["packet_ledger_result_body_opened_by_reviewer_or_pm_after_relay_check"])
        self.assertIn("packet_ledger_missing_result_body_open_receipt", audit["blockers"])

    def test_worker_result_requires_packet_ledger_open_receipt_not_envelope_marker_only(self) -> None:
        root = self.make_project()
        envelope = self.relay_packet(root, self.issue_packet(root))
        forged_envelope = dict(envelope)
        forged_envelope["body_opened_by_role"] = {
            "role": "worker_a",
            "opened_at": "2026-05-07T00:00:00Z",
            "controller_relay_verified": True,
            "body_hash_verified": True,
        }

        with self.assertRaisesRegex(packet_runtime.PacketRuntimeError, "packet ledger missing packet body open receipt"):
            packet_runtime.write_result(
                root,
                packet_envelope=forged_envelope,
                completed_by_role="worker_a",
                completed_by_agent_id="agent-worker-a-1",
                result_body_text="forged open marker result",
                next_recipient="human_like_reviewer",
            )

    def test_result_ready_for_reviewer_relay_requires_result_ledger_absorption(self) -> None:
        root = self.make_project()
        envelope = self.relay_packet(root, self.issue_packet(root))
        packet_runtime.read_packet_body_for_role(root, envelope, role="worker_a")
        result = packet_runtime.write_result(
            root,
            packet_envelope=envelope,
            completed_by_role="worker_a",
            completed_by_agent_id="agent-worker-a-1",
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
            agent_role_map={"agent-worker-a-1": "worker_a"},
        )

        self.assertFalse(audit["passed"])
        self.assertFalse(audit["packet_ledger_result_absorbed"])
        self.assertIn("packet_ledger_missing_result_absorption", audit["blockers"])

    def test_reviewer_audit_rejects_completed_agent_id_role_string(self) -> None:
        root = self.make_project()
        envelope = self.relay_packet(root, self.issue_packet(root))
        packet_runtime.read_packet_body_for_role(root, envelope, role="worker_a")
        result = packet_runtime.write_result(
            root,
            packet_envelope=envelope,
            completed_by_role="worker_a",
            completed_by_agent_id="worker_a",
            result_body_text="valid result with role string as agent id",
            next_recipient="human_like_reviewer",
        )
        result = self.relay_result(root, result)
        packet_runtime.read_result_body_for_role(root, result, role="human_like_reviewer")

        audit = packet_runtime.validate_for_reviewer(
            root,
            packet_envelope=envelope,
            result_envelope=result,
            agent_role_map={"worker_a": "worker_a"},
        )

        self.assertFalse(audit["passed"])
        self.assertIn("completed_agent_id_is_role_key_not_agent_id", audit["blockers"])
        self.assertIn("completed_agent_id_not_assigned_to_role", audit["blockers"])

    def test_reviewer_blocks_packet_or_result_hash_mismatch(self) -> None:
        root = self.make_project()
        envelope = self.relay_packet(root, self.issue_packet(root))
        packet_runtime.read_packet_body_for_role(root, envelope, role="worker_a")
        result = packet_runtime.write_result(
            root,
            packet_envelope=envelope,
            completed_by_role="worker_a",
            completed_by_agent_id="agent-worker-a-1",
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
            agent_role_map={"agent-worker-a-1": "worker_a"},
        )

        self.assertFalse(audit["passed"])
        self.assertIn("packet_body_hash_mismatch", audit["blockers"])

    def test_reviewer_blocks_wrong_role_and_controller_origin(self) -> None:
        root = self.make_project()
        envelope = self.relay_packet(root, self.issue_packet(root))
        packet_runtime.read_packet_body_for_role(root, envelope, role="worker_a")

        wrong_role_result = packet_runtime.write_result(
            root,
            packet_envelope=envelope,
            completed_by_role="worker_b",
            completed_by_agent_id="agent-worker-b-1",
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
            agent_role_map={"agent-worker-b-1": "worker_b"},
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
            packet_runtime.controller_relay_envelope(
                root,
                envelope=envelope,
                envelope_path=self.packet_envelope_path(root),
                controller_agent_id="agent-controller-1",
                received_from_role="project_manager",
                relayed_to_role="worker_a",
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
            packet_runtime.controller_relay_envelope(
                root,
                envelope=original,
                envelope_path=self.packet_envelope_path(root, "packet-old"),
                controller_agent_id="agent-controller-1",
                received_from_role="project_manager",
                relayed_to_role="worker_a",
                body_was_read_by_controller=True,
            )

        replacement = packet_runtime.create_packet(
            root,
            packet_id="packet-new",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="replacement work",
            replacement_for="packet-old",
        )
        replacement = self.relay_packet(root, replacement, packet_id="packet-new")
        packet_runtime.read_packet_body_for_role(root, replacement, role="worker_a")
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
                "background_agents_authorized": True,
                "heartbeat_requested": True,
                "display_surface": "chat-mermaid",
            },
        )
        envelope = packet_runtime.controller_relay_envelope(
            root,
            envelope=envelope,
            envelope_path=self.packet_envelope_path(root, "user-intake-001"),
            controller_agent_id="agent-controller-1",
            received_from_role="user",
            relayed_to_role="project_manager",
        )

        self.assertEqual(envelope["packet_type"], "user_intake")
        self.assertEqual(envelope["body_visibility"], packet_runtime.USER_INTAKE_BODY_VISIBILITY)
        self.assertTrue(envelope["controller_relay"]["external_user_input_visible_to_controller"])
        user_intake_body = packet_runtime.read_packet_body_for_role(root, envelope, role="project_manager")
        self.assertIn(packet_runtime.PACKET_IDENTITY_MARKER, user_intake_body)
        self.assertIn("recipient_role: project_manager", user_intake_body)
        self.assertIn("user task prompt", user_intake_body)

    def test_packet_identity_boundary_is_required_on_read(self) -> None:
        root = self.make_project()
        envelope = self.relay_packet(root, self.issue_packet(root, body_text="worker work"))
        body_path = root / envelope["body_path"]
        body_path.write_text("worker work without identity boundary", encoding="utf-8")
        envelope["body_hash"] = hashlib.sha256(body_path.read_bytes()).hexdigest()
        envelope["controller_relay"]["envelope_hash"] = packet_runtime.envelope_hash(envelope)

        with self.assertRaises(packet_runtime.PacketRuntimeError):
            packet_runtime.read_packet_body_for_role(root, envelope, role="worker_a")

    def test_result_identity_boundary_is_required_on_read(self) -> None:
        root = self.make_project()
        envelope = self.relay_packet(root, self.issue_packet(root))
        packet_runtime.read_packet_body_for_role(root, envelope, role="worker_a")
        result = packet_runtime.write_result(
            root,
            packet_envelope=envelope,
            completed_by_role="worker_a",
            completed_by_agent_id="agent-worker-a-1",
            result_body_text="valid result",
            next_recipient="human_like_reviewer",
        )
        result = self.relay_result(root, result)
        result_path = root / result["result_body_path"]
        result_path.write_text("result without identity boundary", encoding="utf-8")
        result["result_body_hash"] = hashlib.sha256(result_path.read_bytes()).hexdigest()
        result["controller_relay"]["envelope_hash"] = packet_runtime.envelope_hash(result)

        with self.assertRaises(packet_runtime.PacketRuntimeError):
            packet_runtime.read_result_body_for_role(root, result, role="human_like_reviewer")

    def test_active_holder_fast_lane_closes_with_controller_notice(self) -> None:
        root = self.make_project()
        envelope = self.relay_packet(root, self.issue_packet(root))
        lease = packet_runtime.issue_active_holder_lease(
            root,
            packet_envelope=envelope,
            holder_role="worker_a",
            holder_agent_id="agent-worker-a-1",
            route_version=1,
            frontier_version=1,
        )

        ack = packet_runtime.active_holder_ack(
            root,
            lease_path=lease["lease_path"],
            role="worker_a",
            agent_id="agent-worker-a-1",
            route_version=1,
            frontier_version=1,
        )
        self.assertEqual(ack["event"], "active_holder_ack")

        progress = packet_runtime.active_holder_progress(
            root,
            lease_path=lease["lease_path"],
            role="worker_a",
            agent_id="agent-worker-a-1",
            progress=20,
            message="Implementation is underway.",
            route_version=1,
            frontier_version=1,
        )
        self.assertEqual(progress["holder"], "worker_a")
        self.assertEqual(progress["status"], "working")

        session = packet_runtime.begin_role_packet_session(
            root,
            envelope_path=".flowpilot/runs/run-test/packets/packet-001/packet_envelope.json",
            role="worker_a",
            agent_id="agent-worker-a-1",
        )
        self.assertEqual(session["agent_id"], "agent-worker-a-1")

        submission = packet_runtime.active_holder_submit_result(
            root,
            lease_path=lease["lease_path"],
            role="worker_a",
            agent_id="agent-worker-a-1",
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
            agent_role_map={"agent-worker-a-1": "worker_a"},
        )
        self.assertTrue(audit["passed"])

    def test_active_holder_cli_round_trip_writes_controller_notice(self) -> None:
        root = self.make_project()
        self.relay_packet(root, self.issue_packet(root))
        packet_path = ".flowpilot/runs/run-test/packets/packet-001/packet_envelope.json"

        lease = self.run_packet_cli(
            root,
            [
                "issue-active-holder-lease",
                "--envelope-path",
                packet_path,
                "--holder-role",
                "worker_a",
                "--holder-agent-id",
                "agent-worker-a-1",
                "--route-version",
                "1",
                "--frontier-version",
                "1",
            ],
        )
        self.assertEqual(lease["holder_agent_id"], "agent-worker-a-1")

        ack = self.run_packet_cli(
            root,
            [
                "active-holder-ack",
                "--lease-path",
                lease["lease_path"],
                "--role",
                "worker_a",
                "--agent-id",
                "agent-worker-a-1",
                "--route-version",
                "1",
                "--frontier-version",
                "1",
            ],
        )
        self.assertEqual(ack["event"], "active_holder_ack")

        self.run_packet_cli(
            root,
            [
                "open-packet-session",
                "--envelope-path",
                packet_path,
                "--role",
                "worker_a",
                "--agent-id",
                "agent-worker-a-1",
            ],
        )
        submission = self.run_packet_cli(
            root,
            [
                "active-holder-submit-result",
                "--lease-path",
                lease["lease_path"],
                "--role",
                "worker_a",
                "--agent-id",
                "agent-worker-a-1",
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
        lease = packet_runtime.issue_active_holder_lease(
            root,
            packet_envelope=envelope,
            holder_role="worker_a",
            holder_agent_id="agent-worker-a-1",
            route_version=1,
            frontier_version=1,
        )

        with self.assertRaisesRegex(packet_runtime.PacketRuntimeError, "wrong_role"):
            packet_runtime.active_holder_ack(
                root,
                lease_path=lease["lease_path"],
                role="worker_b",
                agent_id="agent-worker-b-1",
                route_version=1,
                frontier_version=1,
            )

        with self.assertRaisesRegex(packet_runtime.PacketRuntimeError, "wrong_agent"):
            packet_runtime.active_holder_ack(
                root,
                lease_path=lease["lease_path"],
                role="worker_a",
                agent_id="agent-worker-a-2",
                route_version=1,
                frontier_version=1,
            )

        with self.assertRaisesRegex(packet_runtime.PacketRuntimeError, "route_version_stale"):
            packet_runtime.active_holder_ack(
                root,
                lease_path=lease["lease_path"],
                role="worker_a",
                agent_id="agent-worker-a-1",
                route_version=2,
                frontier_version=1,
            )

    def test_active_holder_mechanical_reject_keeps_current_holder(self) -> None:
        root = self.make_project()
        envelope = self.relay_packet(root, self.issue_packet(root))
        lease = packet_runtime.issue_active_holder_lease(
            root,
            packet_envelope=envelope,
            holder_role="worker_a",
            holder_agent_id="agent-worker-a-1",
            route_version=1,
            frontier_version=1,
        )
        packet_runtime.active_holder_ack(
            root,
            lease_path=lease["lease_path"],
            role="worker_a",
            agent_id="agent-worker-a-1",
        )
        packet_runtime.begin_role_packet_session(
            root,
            envelope_path=".flowpilot/runs/run-test/packets/packet-001/packet_envelope.json",
            role="worker_a",
            agent_id="agent-worker-a-1",
        )
        wrong_agent_result = packet_runtime.write_result(
            root,
            packet_envelope=self.read_json(self.packet_envelope_path(root)),
            completed_by_role="worker_a",
            completed_by_agent_id="agent-worker-a-2",
            result_body_text="wrong agent result",
            next_recipient="human_like_reviewer",
        )

        rejected = packet_runtime.active_holder_submit_existing_result(
            root,
            lease_path=lease["lease_path"],
            role="worker_a",
            agent_id="agent-worker-a-1",
            result_envelope_path=wrong_agent_result["result_body_path"].rsplit("/", 1)[0] + "/result_envelope.json",
        )

        self.assertFalse(rejected["passed"])
        self.assertIn("active_holder_result_completed_by_wrong_agent", rejected["audit"]["blockers"])
        ledger = self.read_json(root / ".flowpilot" / "runs" / "run-test" / "packet_ledger.json")
        self.assertEqual(ledger["active_packet_holder"], "worker_a")
        self.assertEqual(ledger["active_packet_status"], "active-holder-mechanical-reject")
        self.assertTrue(ledger["packets"][0]["fast_lane_mechanical_reject_recorded"])
        self.assertFalse((self.packet_dir(root) / "controller_next_action_notice.json").exists())


if __name__ == "__main__":
    unittest.main()
