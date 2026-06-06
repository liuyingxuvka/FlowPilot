from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase, read_json, router
from flowpilot_router_controller_wait_audit import (
    ASIDE_CLAIM_WITHOUT_FORMAL_RETURN,
    FORMAL_RETURN_MALFORMED,
    FORMAL_RETURN_READY,
    NO_FORMAL_RETURN_SEEN,
    RESULT_ENVELOPE_SEEN_BUT_NO_NEXT_NOTICE,
    controller_wait_receipt_audit,
)


class ControllerWaitReceiptAuditUnitTests(unittest.TestCase):
    def make_run_root(self) -> tuple[Path, Path]:
        root = Path(tempfile.mkdtemp(prefix="flowpilot-wait-audit-"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        run_root = root / ".flowpilot" / "runs" / "run-1"
        run_root.mkdir(parents=True, exist_ok=True)
        return root, run_root

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def current_wait(self) -> dict:
        return {
            "action_type": "await_role_decision",
            "waiting_for_role": "worker",
            "target_role": "worker",
            "wait_class": "current_node_result",
            "allowed_external_events": ["worker_current_node_result_returned"],
            "packet_id": "pkt-1",
            "expected_return_path": ".flowpilot/runs/run-1/packets/pkt-1/result_envelope.json",
        }

    def test_audit_reports_no_formal_return_when_wait_has_no_metadata(self) -> None:
        root, run_root = self.make_run_root()

        audit = controller_wait_receipt_audit(root, run_root, self.current_wait())

        self.assertEqual(audit["classification"], NO_FORMAL_RETURN_SEEN)
        self.assertFalse(audit["formal_return_seen"])
        self.assertFalse(audit["control_plane_stuck"])
        self.assertTrue(audit["metadata_only"])
        self.assertFalse(audit["sealed_body_reads_allowed"])

    def test_audit_does_not_treat_controller_aside_done_claim_as_formal_return(self) -> None:
        root, run_root = self.make_run_root()
        self.write_json(
            run_root / "packet_ledger.json",
            {
                "packets": [
                    {
                        "packet_id": "pkt-1",
                        "holder_role": "human_like_reviewer",
                        "active_holder_latest_progress_event": {
                            "controller_aside": {"text": "I submitted the work."}
                        },
                    }
                ]
            },
        )

        audit = controller_wait_receipt_audit(root, run_root, self.current_wait())

        self.assertEqual(audit["classification"], ASIDE_CLAIM_WITHOUT_FORMAL_RETURN)
        self.assertTrue(audit["aside_claim_seen"])
        self.assertFalse(audit["formal_return_seen"])
        self.assertFalse(audit["authority_boundary"]["controller_aside_satisfies_wait"])

    def test_audit_flags_result_envelope_without_next_notice_as_stuck(self) -> None:
        root, run_root = self.make_run_root()
        self.write_json(
            run_root / "packets" / "pkt-1" / "result_envelope.json",
            {
                "completed_by_role": "worker",
                "result_body_path": ".flowpilot/runs/run-1/packets/pkt-1/result_body.md",
                "result_body_hash": "abc123",
            },
        )

        audit = controller_wait_receipt_audit(root, run_root, self.current_wait())

        self.assertEqual(audit["classification"], RESULT_ENVELOPE_SEEN_BUT_NO_NEXT_NOTICE)
        self.assertTrue(audit["result_envelope_seen"])
        self.assertFalse(audit["next_action_notice_seen"])
        self.assertTrue(audit["control_plane_stuck"])
        self.assertTrue(audit["user_visible_message_required"])

    def test_audit_marks_formal_return_ready_when_next_notice_exists(self) -> None:
        root, run_root = self.make_run_root()
        result_path = ".flowpilot/runs/run-1/packets/pkt-1/result_envelope.json"
        self.write_json(
            run_root / "packets" / "pkt-1" / "result_envelope.json",
            {
                "completed_by_role": "worker",
                "result_body_path": ".flowpilot/runs/run-1/packets/pkt-1/result_body.md",
                "result_body_hash": "abc123",
            },
        )
        self.write_json(
            run_root / "packets" / "pkt-1" / "controller_next_action_notice.json",
            {
                "next_action": "deliver_result_to_pm_for_disposition",
                "result_envelope_path": result_path,
            },
        )

        audit = controller_wait_receipt_audit(root, run_root, self.current_wait())

        self.assertEqual(audit["classification"], FORMAL_RETURN_READY)
        self.assertTrue(audit["next_action_notice_seen"])
        self.assertTrue(audit["controller_should_reenter_ledger"])
        self.assertFalse(audit["control_plane_stuck"])

    def test_audit_flags_malformed_formal_return_before_reading_body(self) -> None:
        root, run_root = self.make_run_root()
        self.write_json(
            run_root / "packets" / "pkt-1" / "result_envelope.json",
            {
                "completed_by_role": "worker",
                "result_body_path": ".flowpilot/runs/run-1/packets/pkt-1/missing_body.md",
            },
        )

        audit = controller_wait_receipt_audit(root, run_root, self.current_wait())

        self.assertEqual(audit["classification"], FORMAL_RETURN_MALFORMED)
        self.assertTrue(audit["formal_return_malformed"])
        self.assertTrue(audit["control_plane_stuck"])
        self.assertTrue(audit["matches"]["malformed"])


class ControllerWaitReceiptAuditRuntimeTests(FlowPilotRouterRuntimeTestBase):
    def test_standby_snapshot_includes_wait_receipt_audit_for_live_wait(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        self.force_current_role_result_wait(root)

        standby = router.foreground_controller_standby(
            root,
            max_seconds=0,
            poll_seconds=0.01,
            bounded_diagnostic=True,
        )

        self.assertEqual(standby["wait_receipt_audit"]["classification"], NO_FORMAL_RETURN_SEEN)
        self.assertEqual(
            standby["current_wait"]["wait_receipt_audit"]["classification"],
            NO_FORMAL_RETURN_SEEN,
        )
        self.assertTrue(standby["metadata_only"])
        self.assertFalse(standby["sealed_body_reads_allowed"])

    def write_json_file(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()

