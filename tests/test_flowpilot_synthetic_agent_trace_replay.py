from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))
sys.path.insert(0, str(ROOT / "scripts"))

import flowpilot_defects  # noqa: E402
import packet_runtime  # noqa: E402
from scripts.test_tier import background as test_tier_background  # noqa: E402
from tests.synthetic_agent_trace_replay import (  # noqa: E402
    SyntheticTracePackage,
    read_json,
    run_worker_result_trace,
    start_worker_trace,
)


class FlowPilotSyntheticAgentTraceReplayTests(unittest.TestCase):
    def test_happy_path_worker_trace_reaches_pm_disposition(self) -> None:
        package = SyntheticTracePackage(
            name="packet_happy_worker_result",
            evidence_kind="synthetic",
            next_recipient="project_manager",
            expected_outcome="pm_disposition_required",
        )

        replay = run_worker_result_trace(package)

        self.assertEqual(package.evidence_kind, "synthetic")
        self.assertEqual(
            replay.submission["controller_next_action_notice"]["next_action"],  # type: ignore[index]
            "deliver_result_to_pm_for_disposition",
        )
        self.assertFalse(
            replay.submission["controller_next_action_notice"]["controller_may_read_result_body"]  # type: ignore[index]
        )

        record = replay.packet_record()
        self.assertTrue(record["active_holder_ack_recorded"])
        self.assertEqual(record["packet_body_opened_by_role"], "worker_a")
        self.assertTrue(record["packet_body_opened_after_controller_relay_check"])
        self.assertTrue(record["fast_lane_result_mechanics_passed"])
        self.assertEqual(record["result_envelope"]["next_recipient"], "project_manager")

        replay.relay_result()
        body = replay.open_result_body(role="project_manager")
        self.assertIn("Synthetic worker result", body)

        disposition = replay.pm_disposition()
        self.assertEqual(disposition["output_type"], "pm_package_result_disposition")
        self.assertEqual(disposition["from_role"], "project_manager")
        self.assertEqual(disposition["controller_visibility"], "role_output_envelope_only")
        self.assertFalse(disposition["chat_response_body_allowed"])

    def test_ack_only_trace_keeps_semantic_work_open(self) -> None:
        replay = start_worker_trace(
            SyntheticTracePackage(
                name="ack_only_not_completion",
                expected_outcome="semantic_work_still_waiting",
            )
        )

        replay.ack()

        ledger = replay.ledger()
        record = replay.packet_record()
        self.assertEqual(ledger["active_packet_holder"], "worker_a")
        self.assertEqual(ledger["active_packet_status"], "active-holder-acknowledged")
        self.assertTrue(record["active_holder_ack_recorded"])
        self.assertIsNone(record["result_body_hash"])
        self.assertFalse(record["result_body_hash_verified"])
        self.assertFalse((replay.packet_dir / "controller_next_action_notice.json").exists())

    def test_trace_rejects_sealed_body_wrong_identity_and_stale_hash(self) -> None:
        replay = start_worker_trace(SyntheticTracePackage(name="sealed_body_and_identity_guards"))

        with self.assertRaisesRegex(
            packet_runtime.PacketRuntimeError,
            "controller relay target .* does not match recipient 'controller'",
        ):
            packet_runtime.read_packet_body_for_role(
                replay.root,
                replay.packet_envelope,
                role="controller",
            )

        with self.assertRaisesRegex(packet_runtime.PacketRuntimeError, "wrong_role"):
            packet_runtime.active_holder_ack(
                replay.root,
                lease_path=replay.lease["lease_path"],  # type: ignore[index]
                role="worker_b",
                agent_id="agent-worker-b-1",
                route_version=1,
                frontier_version=1,
            )

        with self.assertRaisesRegex(packet_runtime.PacketRuntimeError, "wrong_agent"):
            packet_runtime.active_holder_ack(
                replay.root,
                lease_path=replay.lease["lease_path"],  # type: ignore[index]
                role="worker_a",
                agent_id="agent-worker-a-2",
                route_version=1,
                frontier_version=1,
            )

        replay.ack()
        replay.open_packet_body()
        replay.submit_result()
        replay.relay_result()
        replay.tamper_result_body()

        with self.assertRaisesRegex(packet_runtime.PacketRuntimeError, "result body hash mismatch"):
            replay.open_result_body(role="project_manager")

    def test_raw_worker_result_cannot_skip_pm_disposition_to_reviewer_pass(self) -> None:
        replay = run_worker_result_trace(
            SyntheticTracePackage(
                name="raw_worker_result_to_reviewer_blocked",
                next_recipient="project_manager",
                expected_outcome="reviewer_blocks_missing_pm_disposition",
            )
        )

        replay.relay_result(to_role="human_like_reviewer")
        replay.open_result_body(role="human_like_reviewer")

        audit = packet_runtime.validate_for_reviewer(
            replay.root,
            packet_envelope=read_json(replay.packet_envelope_path),
            result_envelope=read_json(replay.result_envelope_path),
            agent_role_map={"agent-worker-a-1": "worker_a"},
        )
        self.assertFalse(audit["passed"])
        self.assertIn("missing_or_invalid_result_controller_relay", audit["blockers"])

    def test_fixture_evidence_is_disclosed_but_not_live_completion_evidence(self) -> None:
        replay = start_worker_trace(
            SyntheticTracePackage(
                name="fixture_evidence_cannot_close_live_completion",
                evidence_kind="fixture",
                expected_outcome="fixture_only_disclosed",
            )
        )

        self.assertEqual(replay.package.evidence_kind, "fixture")
        self.assertEqual(flowpilot_defects.main(["--root", str(replay.root), "init"]), 0)
        self.assertEqual(
            flowpilot_defects.main(
                [
                    "--root",
                    str(replay.root),
                    "add-evidence",
                    "--evidence-id",
                    "synthetic-trace-fixture-evidence",
                    "--kind",
                    "trace_replay",
                    "--path",
                    "synthetic-traces/fixture-result.json",
                    "--status",
                    "valid",
                    "--source-kind",
                    "fixture",
                    "--role",
                    "worker_a",
                    "--reason",
                    "Fixture proves control-flow behavior but not live project completion.",
                ]
            ),
            0,
        )
        self.assertEqual(
            flowpilot_defects.main(
                [
                    "--root",
                    str(replay.root),
                    "pause-snapshot",
                    "--reason",
                    "synthetic_trace_replay",
                    "--next-allowed-action",
                    "continue_current_run",
                    "--automation-checked",
                    "--safe-to-delete",
                    "synthetic trace temp output",
                    "--preserve",
                    "live project evidence",
                    "--must-not-reuse",
                    "fixture evidence as live completion proof",
                    "--summary",
                    "Synthetic trace fixture evidence recorded as non-live evidence.",
                ]
            ),
            0,
        )
        snapshot = json.loads((replay.run_root / "pause_snapshot.json").read_text(encoding="utf-8"))
        self.assertEqual(
            snapshot["evidence_summary"]["fixture_only_evidence_to_disclose"],
            ["synthetic-trace-fixture-evidence"],
        )

    def test_background_progress_only_trace_is_not_pass_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-synthetic-bg-") as tmp_name:
            root = Path(tmp_name)
            paths = test_tier_background.artifact_paths(root, "synthetic_progress_only")
            paths["combined"].parent.mkdir(parents=True, exist_ok=True)
            paths["combined"].write_text("still exploring states\n", encoding="utf-8")

            evidence = test_tier_background.classify_background_artifact(
                root,
                "synthetic_progress_only",
            )

        self.assertEqual(evidence["status"], "progress_only")
        self.assertFalse(evidence["ok"])
        self.assertIn("missing_exit", evidence["reasons"])


if __name__ == "__main__":
    unittest.main()
