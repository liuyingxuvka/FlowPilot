from __future__ import annotations

from itertools import combinations
import json
from pathlib import Path
import tempfile
import unittest

from simulations import flowpilot_singleton_identity_model as model
from simulations import run_flowpilot_singleton_identity_checks as checks


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_current_pointer(root: Path, run_id: str = "run-1") -> Path:
    run_root = root / ".flowpilot" / "runs" / run_id
    _write_json(
        root / ".flowpilot" / "current.json",
        {
            "run_id": run_id,
            "run_root": f".flowpilot/runs/{run_id}",
            "status": "running",
        },
    )
    return run_root


def _valid_live_evidence_payload(relative_path: str, run_id: str = "run-1") -> dict[str, object]:
    if relative_path == "route_state_snapshot.json":
        return {"active_ui_task_catalog": {"active_tasks": []}}
    if relative_path == "runtime/router_daemon.lock":
        return {"status": "active", "single_writer_lock": True, "run_id": run_id}
    if relative_path == "packet_ledger.json":
        return {"active_packet_id": "packet-1", "active_packet_status": "active-holder-lease-issued", "packets": []}
    if relative_path == "execution_frontier.json":
        return {"status": "current_node", "phase": "current_node"}
    raise AssertionError(f"unknown live evidence path: {relative_path}")


def _write_live_evidence(run_root: Path, relative_path: str, *, run_id: str = "run-1") -> None:
    _write_json(run_root / relative_path, _valid_live_evidence_payload(relative_path, run_id=run_id))


class FlowPilotSingletonIdentityTests(unittest.TestCase):
    def test_live_audit_projects_absolute_current_run_root_as_repository_relative(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            run_root = root / ".flowpilot" / "runs" / "run-1"
            _write_json(
                root / ".flowpilot" / "current.json",
                {
                    "run_id": "run-1",
                    "run_root": str(run_root),
                    "status": "running",
                },
            )

            report = model.build_live_singleton_audit(root)
            serialized = json.dumps(report, sort_keys=True)

            self.assertNotIn(str(root), serialized)
            pointer = next(
                surface
                for surface in report["surfaces"]
                if surface["surface"] == "current_run_pointer"
            )
            self.assertEqual(pointer["evidence"]["run_root"], ".flowpilot/runs/run-1")

    def test_authority_matrix_has_required_singleton_rows(self) -> None:
        rows = {row.object_family: row for row in model.authority_matrix()}

        self.assertLessEqual(
            {
                "parallel_flowpilot_runs",
                "router_daemon_writer",
                "packet_active_holder",
                "pm_package_disposition",
                "route_replacement_current_authority",
                "ordinary_packet_batch_generation",
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
                "stale_packet_batch_ref_marked_current",
                "retired_material_authority_marked_safe",
                "ack_only_output_marked_complete",
                "progress_only_final_marked_complete",
                "missing_ledger_marked_safe",
                "idempotent_replay_overblocked",
            },
            set(hazards),
        )

    def test_live_audit_classifies_duplicate_packet_holder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            run_root = tmp_path / ".flowpilot" / "runs" / "run-1"
            _write_json(
                tmp_path / ".flowpilot" / "current.json",
                {
                    "run_id": "run-1",
                    "run_root": ".flowpilot/runs/run-1",
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
                            "active_packet_holder": "worker",
                            "active_packet_status": "active-holder-lease-issued",
                        },
                        {
                            "packet_id": "packet-1",
                            "active_packet_holder": "worker",
                            "active_packet_status": "active-holder-acknowledged",
                        },
                    ],
                },
            )
            _write_json(run_root / "execution_frontier.json", {"status": "current_node"})

            audit = model.build_live_singleton_audit(tmp_path)

        self.assertIs(audit["ok"], False)
        self.assertEqual(1, audit["risk_count"])
        risky = [surface for surface in audit["surfaces"] if surface["status"] == "risk"]
        self.assertEqual("packet_active_holder", risky[0]["surface"])

    def test_live_audit_required_evidence_powerset_full_only_when_all_core_files_exist(self) -> None:
        required_paths = [
            row["relative_path"]
            for row in model.live_singleton_required_evidence_files()
        ]
        self.assertEqual(len(required_paths), 4)

        for size in range(len(required_paths) + 1):
            for selected in combinations(required_paths, size):
                with self.subTest(selected=selected):
                    with tempfile.TemporaryDirectory() as tmp:
                        tmp_path = Path(tmp)
                        run_root = _write_current_pointer(tmp_path)
                        for relative_path in selected:
                            _write_live_evidence(run_root, relative_path)

                        audit = model.build_live_singleton_audit(tmp_path)

                    if set(selected) == set(required_paths):
                        self.assertEqual(audit["risk_count"], 0, audit)
                        self.assertEqual(audit["evidence_insufficient_count"], 0, audit)
                        self.assertTrue(audit["ok"], audit)
                    else:
                        self.assertGreater(audit["evidence_insufficient_count"], 0, audit)

    def test_live_audit_present_but_invalid_evidence_is_not_marked_safe(self) -> None:
        required_paths = [
            row["relative_path"]
            for row in model.live_singleton_required_evidence_files()
        ]
        invalid_cases = {
            "route_state_snapshot.json": "{not strict json}",
            "runtime/router_daemon.lock": json.dumps(
                {"status": "active", "single_writer_lock": True, "run_id": "run-other"}
            ),
            "packet_ledger.json": "[not an object]",
            "execution_frontier.json": "{not strict json}",
        }

        for invalid_path, invalid_text in invalid_cases.items():
            with self.subTest(invalid_path=invalid_path):
                with tempfile.TemporaryDirectory() as tmp:
                    tmp_path = Path(tmp)
                    run_root = _write_current_pointer(tmp_path)
                    for relative_path in required_paths:
                        _write_live_evidence(run_root, relative_path)
                    invalid_file = run_root / invalid_path
                    invalid_file.parent.mkdir(parents=True, exist_ok=True)
                    invalid_file.write_text(invalid_text, encoding="utf-8")

                    audit = model.build_live_singleton_audit(tmp_path)

                surface_by_path = {
                    row["relative_path"]: row["surface"]
                    for row in model.live_singleton_required_evidence_files()
                }
                matching = [
                    surface
                    for surface in audit["surfaces"]
                    if surface["surface"] == surface_by_path[invalid_path]
                ]
                self.assertEqual(len(matching), 1, audit)
                self.assertNotEqual(matching[0]["status"], "safe", audit)

    def test_live_audit_accepts_ordinary_batch_identity_and_rejects_retired_material_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            run_root = _write_current_pointer(tmp_path)
            for row in model.live_singleton_required_evidence_files():
                _write_live_evidence(run_root, row["relative_path"])
            batch_path = run_root / "packet_batches" / "research-001.json"
            _write_json(
                batch_path,
                {
                    "batch_id": "research-001",
                    "batch_kind": "research",
                    "packet_ids": ["research-worker-001"],
                },
            )
            _write_json(
                run_root / "packet_batches" / "active_research.json",
                {
                    "batch_kind": "research",
                    "active_batch_id": "research-001",
                    "batch_path": ".flowpilot/runs/run-1/packet_batches/research-001.json",
                },
            )

            clean = model.build_live_singleton_audit(tmp_path)
            _write_json(
                run_root / "packet_batches" / "active_material_scan.json",
                {
                    "batch_kind": "material_scan",
                    "active_batch_id": "retired-material-001",
                    "batch_path": ".flowpilot/runs/run-1/packet_batches/retired-material-001.json",
                },
            )
            retired = model.build_live_singleton_audit(tmp_path)

        clean_surface = next(
            row
            for row in clean["surfaces"]
            if row["surface"] == "ordinary_packet_batch_generation"
        )
        self.assertEqual(clean_surface["status"], "safe", clean_surface)
        retired_surface = next(
            row
            for row in retired["surfaces"]
            if row["surface"] == "ordinary_packet_batch_generation"
        )
        self.assertEqual(retired_surface["status"], "risk", retired_surface)
        self.assertTrue(retired_surface["evidence"]["retired_material_refs"])

    def test_singleton_check_report_shape(self) -> None:
        report = checks.run_checks()

        self.assertEqual("flowpilot_singleton_identity", report["result_type"])
        self.assertGreaterEqual(report["authority_matrix_count"], 8)
        self.assertIs(report["safe_graph"]["ok"], True)
        self.assertIs(report["hazard_detection"]["ok"], True)
        self.assertIn(report["confidence"], {"full", "scoped"})
