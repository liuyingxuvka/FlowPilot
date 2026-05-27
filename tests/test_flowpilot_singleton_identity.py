from __future__ import annotations

import json
from pathlib import Path
import unittest

from simulations import flowpilot_singleton_identity_model as model
from simulations import run_flowpilot_singleton_identity_checks as checks


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class FlowPilotSingletonIdentityTests(unittest.TestCase):
    def test_authority_matrix_has_required_singleton_rows(self) -> None:
        rows = {row.object_family: row for row in model.authority_matrix()}

        self.assertLessEqual(
            {
                "parallel_flowpilot_runs",
                "router_daemon_writer",
                "packet_active_holder",
                "pm_package_disposition",
                "route_replacement_current_authority",
                "material_progress_generation",
                "ack_vs_output_completion",
                "final_closure_evidence",
            },
            set(rows),
        )
        for row in rows.values():
            self.assertTrue(row.singleton_scope)
            self.assertTrue(row.canonical_owner)
            self.assertTrue(row.identity_key)
            self.assertTrue(row.old_object_disposition)

    def test_known_bad_singleton_hazards_are_detected(self) -> None:
        report = checks._hazard_report()

        self.assertIs(report["ok"], True)
        hazards = report["hazards"]
        self.assertEqual(
            {
                "plurality_without_target_marked_safe",
                "duplicate_daemon_writer_marked_safe",
                "package_conflict_marked_replay",
                "replacement_without_disposition_marked_safe",
                "stale_material_flag_marked_current",
                "ack_only_output_marked_complete",
                "progress_only_final_marked_complete",
                "missing_ledger_marked_safe",
                "idempotent_replay_overblocked",
            },
            set(hazards),
        )

    def test_live_audit_classifies_duplicate_packet_holder(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            run_root = tmp_path / ".flowpilot" / "runs" / "run-1"
            _write_json(
                tmp_path / ".flowpilot" / "current.json",
                {
                    "current_run_id": "run-1",
                    "current_run_root": ".flowpilot/runs/run-1",
                    "status": "running",
                },
            )
            _write_json(
                run_root / "route_state_snapshot.json",
                {
                    "active_ui_task_catalog": {
                        "active_tasks": [
                            {"target_id": "run:run-1", "operation_target_allowed": True}
                        ]
                    }
                },
            )
            _write_json(
                run_root / "runtime" / "router_daemon.lock",
                {
                    "status": "active",
                    "single_writer_lock": True,
                    "run_id": "run-1",
                },
            )
            _write_json(run_root / "runtime" / "router_daemon_status.json", {"error": None})
            _write_json(
                run_root / "packet_ledger.json",
                {
                    "active_packet_id": "packet-1",
                    "active_packet_status": "active-holder-lease-issued",
                    "packets": [
                        {
                            "packet_id": "packet-1",
                            "active_packet_holder": "worker_a",
                            "active_packet_status": "active-holder-lease-issued",
                        },
                        {
                            "packet_id": "packet-1",
                            "active_packet_holder": "worker_b",
                            "active_packet_status": "active-holder-acknowledged",
                        },
                    ],
                },
            )
            _write_json(run_root / "execution_frontier.json", {"status": "material_scan"})
            _write_json(run_root / "router_state.json", {"flags": {}})

            audit = model.build_live_singleton_audit(tmp_path)

        self.assertIs(audit["ok"], False)
        self.assertEqual(1, audit["risk_count"])
        risky = [surface for surface in audit["surfaces"] if surface["status"] == "risk"]
        self.assertEqual("packet_active_holder", risky[0]["surface"])

    def test_singleton_check_report_shape(self) -> None:
        report = checks.run_checks()

        self.assertEqual("flowpilot_singleton_identity", report["result_type"])
        self.assertGreaterEqual(report["authority_matrix_count"], 8)
        self.assertIs(report["safe_graph"]["ok"], True)
        self.assertIs(report["hazard_detection"]["ok"], True)
        self.assertIn(report["confidence"], {"full", "scoped"})
