from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulations"))

import flowpilot_control_plane_friction_model_audit as control_audit  # noqa: E402
import flowpilot_cross_plane_friction_model_audit as cross_audit  # noqa: E402
import flowpilot_daemon_reconciliation_checks_projection_common as daemon_projection  # noqa: E402
import flowpilot_model_mesh_model as model_mesh  # noqa: E402
import run_flowpilot_full_model_coverage_inventory as inventory  # noqa: E402
from scripts import run_flowguard_coverage_sweep as coverage_sweep  # noqa: E402


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class FlowPilotFullCoverageFindingRepairTests(unittest.TestCase):
    def test_cross_plane_audit_resolves_split_completion_helper(self) -> None:
        findings = cross_audit._audit_router_source(ROOT)

        self.assertNotIn(
            "node_completion_idempotency_global_only",
            {str(finding.get("code")) for finding in findings},
        )

    def test_control_plane_audit_resolves_split_external_event_contracts(self) -> None:
        contracts, error = control_audit._router_external_event_contracts(ROOT)

        self.assertIsNone(error)
        self.assertEqual(
            contracts["reviewer_reports_material_sufficient"]["requires_flag"],
            "reviewer_material_sufficiency_card_delivered",
        )
        self.assertEqual(
            contracts["reviewer_reports_material_insufficient"]["requires_flag"],
            "reviewer_material_sufficiency_card_delivered",
        )

    def test_material_scan_file_backed_pm_spec_counts_as_materialized_packet_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            run_root = project_root / ".flowpilot" / "runs" / "run-test"
            packet_id = "material-scan-runtime-data-worker-1"
            result_body_path = ".flowpilot/runs/run-test/packets/material/result_body.md"
            spec_body_path = ".flowpilot/runs/run-test/material/packet_bodies/spec.md"
            packet_body_path = ".flowpilot/runs/run-test/packets/material/packet_body.md"
            envelope_path = ".flowpilot/runs/run-test/packets/material/packet_envelope.json"
            output_contract = {
                "contract_id": "flowpilot.output_contract.worker_material_scan_result.v1",
                "task_family": "worker.material_scan",
                "recipient_role": "worker",
                "expected_result_body_path": result_body_path,
            }
            spec_text = "Inspect runtime data and return the material scan result."
            packet_text = (
                f"{spec_text}\n\n## Output Contract\n```json\n"
                f"{json.dumps(output_contract, indent=2, sort_keys=True)}\n```\n\n"
                f"Write result to {result_body_path}.\n"
            )
            (project_root / spec_body_path).parent.mkdir(parents=True, exist_ok=True)
            (project_root / spec_body_path).write_text(spec_text, encoding="utf-8")
            (project_root / packet_body_path).parent.mkdir(parents=True, exist_ok=True)
            (project_root / packet_body_path).write_text(packet_text, encoding="utf-8")
            envelope = {
                "packet_id": packet_id,
                "packet_type": "material_scan",
                "to_role": "worker",
                "body_path": packet_body_path,
                "body_hash": hashlib.sha256(packet_text.encode("utf-8")).hexdigest(),
                "result_body_path": result_body_path,
                "output_contract": output_contract,
            }
            _write_json(project_root / envelope_path, envelope)
            _write_json(
                run_root / "material" / "material_scan_packets.json",
                {
                    "router_direct_dispatch_required_before_worker": True,
                    "packets": [
                        {
                            "packet_id": packet_id,
                            "packet_envelope_path": envelope_path,
                            "result_body_path": result_body_path,
                        }
                    ],
                },
            )
            _write_json(
                run_root / "material" / "pm_material_scan_packet_specs.project_manager.json",
                {
                    "packets": [
                        {
                            "packet_id": packet_id,
                            "body_path": spec_body_path,
                            "body_hash": hashlib.sha256(spec_text.encode("utf-8")).hexdigest(),
                        }
                    ]
                },
            )
            _write_json(
                run_root / "packet_ledger.json",
                {
                    "packets": [
                        {
                            "packet_id": packet_id,
                            "result_body_path": result_body_path,
                        }
                    ]
                },
            )

            result = control_audit._audit_material_scan_dispatch_integrity(
                project_root=project_root,
                run_root=run_root,
                router_state={"phase": "material_scan", "flags": {}},
                frontier={"phase": "material_scan", "status": "material_scan"},
            )

        self.assertTrue(result["single_canonical_body"])
        self.assertTrue(result["packet_details"][0]["pm_spec_body_materialized"])

    def test_daemon_projection_treats_recipient_opened_result_status_as_controller_relayed(self) -> None:
        packet = {
            "packet_holder": "project_manager",
            "packet_status": "packet-body-opened-by-recipient",
            "controller_relay_recorded": True,
            "terminal_lifecycle": None,
        }
        packet_ledger = {
            "active_packet_holder": "project_manager",
            "active_packet_status": "result-body-opened-by-recipient",
        }

        self.assertTrue(daemon_projection._user_intake_router_released(packet, packet_ledger))

    def test_default_result_file_omission_is_not_skipped_evidence_gap(self) -> None:
        classes = inventory._gap_classes(
            {
                "parsed": True,
                "ok": True,
                "findings": [],
                "skipped_checks": {
                    "default_results_file": "skipped_with_reason: no --json-out path was provided",
                },
                "sections": {"live": {"present": False}, "source": {"present": False}},
                "coverage_tier": "coverage_strong",
            },
            "ordinary_test_text_reference",
            {},
        )

        self.assertNotIn("skipped_or_scoped_evidence", classes)
        self.assertEqual(classes, ["currently_consumable_inventory_evidence"])

    def test_control_plane_audit_reads_background_projection_from_authority(self) -> None:
        ids = control_audit._background_running_projection_ids(
            {
                "authority": {
                    "background_running_index_entries": [
                        {"run_id": "run-a", "status": "running"},
                        {"run_id": "run-b", "status": "running"},
                    ]
                }
            }
        )

        self.assertEqual(ids, ["run-a", "run-b"])

    def test_control_plane_audit_accepts_explicit_parallel_active_set_authority(self) -> None:
        snapshot = {
            "authority": {
                "current_pointer_is_ui_focus_only": True,
                "index_running_entries_are_parallel_run_authority": True,
                "global_main_required": False,
                "operation_target_required": True,
                "background_running_index_entries": [
                    {"run_id": "run-b", "target_id": "run:run-b", "operation_target_allowed": True}
                ],
            },
            "active_ui_task_catalog": {
                "authority": "explicit_active_set",
                "global_main_required": False,
                "operation_target_required": True,
                "background_active_tasks": [
                    {"run_id": "run-b", "target_id": "run:run-b", "operation_target_allowed": True}
                ],
                "operation_targets": {
                    "single_targets": [
                        {"run_id": "run-a", "target_id": "run:run-a"},
                        {"run_id": "run-b", "target_id": "run:run-b"},
                    ],
                    "all_active": {"target_scope": "all_active", "run_ids": ["run-a", "run-b"]},
                },
            },
        }

        self.assertTrue(
            control_audit._active_set_authority_is_explicit(
                snapshot,
                non_current_running_entries=["run-b"],
                missing_background_projection=[],
            )
        )

    def test_control_plane_audit_rejects_parallel_active_set_without_targets(self) -> None:
        snapshot = {
            "authority": {
                "current_pointer_is_ui_focus_only": True,
                "index_running_entries_are_parallel_run_authority": True,
                "global_main_required": False,
                "operation_target_required": True,
                "background_running_index_entries": [{"run_id": "run-b"}],
            },
            "active_ui_task_catalog": {
                "authority": "explicit_active_set",
                "background_active_tasks": [{"run_id": "run-b", "operation_target_allowed": True}],
                "operation_targets": {"single_targets": [{"run_id": "run-a", "target_id": "run:run-a"}]},
            },
        }

        self.assertFalse(
            control_audit._active_set_authority_is_explicit(
                snapshot,
                non_current_running_entries=["run-b"],
                missing_background_projection=[],
            )
        )

    def test_control_plane_audit_synthesizes_explicit_authority_from_index_for_old_snapshot(self) -> None:
        snapshot = control_audit._active_set_authority_snapshot_from_index(
            current={"current_run_id": "run-a", "status": "stopped_by_user"},
            index={
                "runs": [
                    {"run_id": "run-b", "run_root": ".flowpilot/runs/run-b", "status": "running"},
                    {"run_id": "run-c", "run_root": ".flowpilot/runs/run-c", "status": "running"},
                    {"run_id": "run-old", "status": "complete"},
                ]
            },
            current_run_id="run-a",
        )

        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        self.assertEqual(snapshot["active_ui_task_catalog"]["authority"], "explicit_active_set")
        self.assertEqual(
            sorted(control_audit._background_running_projection_ids(snapshot)),
            ["run-b", "run-c"],
        )
        self.assertTrue(
            control_audit._active_set_authority_is_explicit(
                snapshot,
                non_current_running_entries=["run-b", "run-c"],
                missing_background_projection=[],
            )
        )

    def test_model_mesh_does_not_require_role_origin_audit_for_plain_user_packet_body(self) -> None:
        packet_ledger = {
            "packets": [
                {
                    "packet_id": "user_intake",
                    "packet_body_hash": "abc123",
                    "role_origin_audit": {
                        "result_envelope_completed_by_role_checked": False,
                    },
                }
            ]
        }

        self.assertFalse(model_mesh._packet_authority_unchecked(packet_ledger))

    def test_model_mesh_accepts_router_owned_packet_review_audit_for_result_role_origin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            run_root = project_root / ".flowpilot" / "runs" / "run-test"
            audit_path = run_root / "material" / "material_packet_review_audit.json"
            packet_id = "material-scan-runtime-data-worker-1"
            audit = {
                "schema_version": "flowpilot.packet_group_reviewer_audit.v1",
                "run_id": "run-test",
                "passed": True,
                "overall_passed": True,
                "self_attested_ai_claims_accepted_as_proof": False,
                "blockers": [],
                "audits": [
                    {
                        "packet_id": packet_id,
                        "passed": True,
                        "blockers": [],
                        "packet_ledger_record_found": True,
                        "result_envelope_checked": True,
                        "result_envelope_completed_by_role_checked": True,
                        "completed_agent_id_belongs_to_role": True,
                    }
                ],
            }
            _write_json(audit_path, audit)
            audit_hash = hashlib.sha256(audit_path.read_bytes()).hexdigest()
            _write_json(
                audit_path.with_name(audit_path.name + ".proof.json"),
                {
                    "schema_version": "flowpilot.router_owned_check_proof.v1",
                    "run_id": "run-test",
                    "audit_path": ".flowpilot/runs/run-test/material/material_packet_review_audit.json",
                    "audit_sha256": audit_hash,
                    "check_name": "packet_group_reviewer_audit",
                    "check_owner": "flowpilot_router",
                    "source_kind": "packet_runtime_hash",
                    "trust_basis": "non_self_attested_recomputed_or_host_bound",
                    "self_attested_ai_claims_accepted_as_proof": False,
                },
            )
            packet_ledger = {
                "packets": [
                    {
                        "packet_id": packet_id,
                        "result_body_hash": "def456",
                        "result_envelope": {
                            "completed_agent_id_belongs_to_role": False,
                        },
                        "role_origin_audit": {
                            "result_envelope_completed_by_role_checked": False,
                        },
                    }
                ]
            }

            trusted_ids = model_mesh._trusted_packet_authority_audit_ids(run_root)

        self.assertEqual(trusted_ids, {packet_id})
        self.assertFalse(
            model_mesh._packet_authority_unchecked(packet_ledger, trusted_packet_ids=trusted_ids)
        )

    def test_source_known_bad_findings_are_classified_as_boundary_checks(self) -> None:
        self.assertEqual(
            coverage_sweep._classify_finding(
                {
                    "section": "source",
                    "section_path": "source_known_bad_sanity_checks.0.report",
                    "severity": "blocker",
                }
            ),
            "boundary_expected_or_informational",
        )


if __name__ == "__main__":
    unittest.main()
