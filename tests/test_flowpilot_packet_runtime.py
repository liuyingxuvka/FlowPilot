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


if __name__ == "__main__":
    unittest.main()
