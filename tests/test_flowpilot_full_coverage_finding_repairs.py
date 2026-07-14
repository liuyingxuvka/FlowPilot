from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from dataclasses import fields
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulations"))

import flowpilot_control_plane_friction_model_audit as control_audit  # noqa: E402
import flowpilot_control_plane_friction_model as control_model  # noqa: E402
import flowpilot_cross_plane_friction_model_audit as cross_audit  # noqa: E402
import flowpilot_daemon_reconciliation_checks_projection_common as daemon_projection  # noqa: E402
import flowpilot_model_mesh_model as model_mesh  # noqa: E402
import run_flowpilot_full_model_coverage_inventory as inventory  # noqa: E402
from scripts import run_flowguard_coverage_sweep as coverage_sweep  # noqa: E402


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class FlowPilotFullCoverageFindingRepairTests(unittest.TestCase):
    def test_control_plane_live_audit_redacts_project_root_from_public_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp).resolve()
            run_root = project_root / ".flowpilot" / "runs" / "run-test"
            _write_json(
                project_root / ".flowpilot" / "current.json",
                {
                    "run_id": "run-test",
                    "run_root": str(run_root),
                    "status": "running",
                },
            )

            report = control_audit.audit_live_run(project_root, source_root=ROOT)

            self.assertNotIn(str(project_root), json.dumps(report, sort_keys=True))

    def test_control_plane_model_retires_material_specific_positive_protocol(self) -> None:
        forbidden_fragments = {
            "material_gate",
            "material_dispatch",
            "pm_material_understanding",
            "material_repair_generation",
            "material_progress",
        }
        state_fields = {field.name for field in fields(control_model.State)}
        invariant_names = {invariant.name for invariant in control_model.INVARIANTS}
        hazard_rows = control_model.hazard_states()

        for fragment in forbidden_fragments:
            self.assertFalse(any(fragment in name for name in state_fields), fragment)
            self.assertFalse(any(fragment in name for name in invariant_names), fragment)
            self.assertFalse(any(fragment in name for name in hazard_rows), fragment)
        self.assertFalse(hasattr(control_audit, "_audit_material_scan_dispatch_integrity"))
        self.assertFalse(hasattr(control_audit, "_audit_material_repair_generation_protocol"))
        retired = hazard_rows["ordinary_work_dispatch_retired_family"]
        self.assertEqual(retired.ordinary_work_dispatch_family, "material_scan")
        self.assertTrue(control_model.invariant_failures(retired))

    def test_cross_plane_audit_resolves_split_completion_helper(self) -> None:
        findings = cross_audit._audit_router_source(ROOT)

        self.assertNotIn(
            "node_completion_idempotency_global_only",
            {str(finding.get("code")) for finding in findings},
        )

    def test_control_plane_audit_resolves_split_external_event_contracts(self) -> None:
        contracts, error = control_audit._router_external_event_contracts(ROOT)

        self.assertIsNone(error)
        self.assertIn("pm_registers_role_work_request", contracts)
        self.assertIn("worker_current_node_result_returned", contracts)
        self.assertIn("pm_records_research_result_disposition", contracts)
        self.assertTrue(
            control_audit.RETIRED_MATERIAL_EVENT_NAMES.isdisjoint(contracts)
        )
        absence = control_audit.audit_retired_material_surfaces(ROOT)
        self.assertTrue(absence["ok"], absence)
        self.assertEqual(absence["retired_actions"], [])
        self.assertEqual(absence["retired_packet_families"], [])

    def test_ordinary_work_dispatch_accepts_research_and_rejects_retired_family(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            run_root = project_root / ".flowpilot" / "runs" / "run-test"
            result_body_path = ".flowpilot/runs/run-test/packets/research/result.md"
            _write_json(
                run_root / "packet_ledger.json",
                {
                    "packets": [
                        {
                            "packet_id": "research-1",
                            "packet_type": "research",
                            "result_body_path": result_body_path,
                            "output_contract": {
                                "contract_id": "flowpilot.output_contract.research.v1",
                                "expected_result_body_path": result_body_path,
                            },
                        }
                    ],
                },
            )
            current = control_audit._audit_ordinary_work_dispatch_integrity(
                project_root=project_root,
                run_root=run_root,
            )
            ledger, _ = control_audit._read_json(run_root / "packet_ledger.json")
            ledger["packets"].append(
                {
                    "packet_id": "retired-1",
                    "packet_type": "material_scan",
                    "result_body_path": "retired.md",
                    "output_contract": {"contract_id": "retired"},
                }
            )
            _write_json(run_root / "packet_ledger.json", ledger)
            retired = control_audit._audit_ordinary_work_dispatch_integrity(
                project_root=project_root,
                run_root=run_root,
            )

        self.assertTrue(current["allowed"])
        self.assertEqual(current["ordinary_packet_details"][0]["packet_family"], "research")
        self.assertFalse(retired["allowed"])
        self.assertEqual(retired["retired_packet_details"][0]["packet_family"], "material_scan")

    def test_daemon_projection_treats_recipient_opened_result_status_as_released(self) -> None:
        packet = {
            "packet_holder": "project_manager",
            "packet_status": "packet-body-opened-by-recipient",
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

    def test_control_plane_audit_synthesizes_explicit_authority_from_index_for_current_snapshot(self) -> None:
        snapshot = control_audit._active_set_authority_snapshot_from_index(
            current={"run_id": "run-a", "run_root": ".flowpilot/runs/run-a", "status": "stopped_by_user"},
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
            audit_path = run_root / "research" / "research_packet_review_audit.json"
            packet_id = "research-runtime-data-worker-1"
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
                    "audit_path": ".flowpilot/runs/run-test/research/research_packet_review_audit.json",
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

    def test_model_mesh_ignores_retired_material_packet_review_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp) / ".flowpilot" / "runs" / "run-test"
            audit_path = run_root / "material" / "material_packet_review_audit.json"
            _write_json(
                audit_path,
                {
                    "schema_version": "flowpilot.packet_group_reviewer_audit.v1",
                    "run_id": "run-test",
                    "passed": True,
                    "overall_passed": True,
                    "self_attested_ai_claims_accepted_as_proof": False,
                    "blockers": [],
                    "audits": [
                        {
                            "packet_id": "material-scan-retired",
                            "passed": True,
                            "blockers": [],
                            "packet_ledger_record_found": True,
                            "result_envelope_checked": True,
                            "result_envelope_completed_by_role_checked": True,
                            "completed_agent_id_belongs_to_role": True,
                        }
                    ],
                },
            )
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
                    "self_attested_ai_claims_accepted_as_proof": False,
                },
            )

            trusted_ids = model_mesh._trusted_packet_authority_audit_ids(run_root)

        self.assertEqual(trusted_ids, set())

    def test_model_mesh_blocks_current_lifecycle_guard_stuck(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            run_root = project_root / ".flowpilot" / "runs" / "run-stuck"
            run_root.mkdir(parents=True)
            _write_json(
                project_root / ".flowpilot" / "current.json",
                {
                    "run_id": "run-stuck",
                    "run_root": ".flowpilot/runs/run-stuck",
                    "status": "created",
                },
            )
            _write_json(
                run_root / "ledger.json",
                {
                    "lifecycle_guard": {
                        "decision": "control_plane_stuck",
                        "reason": "previous stuck decision for the same nonterminal action remains unresolved",
                        "action_key": "open_startup_intake:none",
                        "repeated_count": 15,
                        "next_action": {
                            "action_type": "open_startup_intake",
                        },
                    },
                    "foreground_duty": {
                        "action": "control_plane_blocker",
                        "lifecycle_guard_decision": "control_plane_stuck",
                        "final_return_preflight": {
                            "blockers": ["guard_decision:control_plane_stuck"],
                        },
                    },
                },
            )

            projection = model_mesh.project_live_run(project_root)

        self.assertNotEqual(projection["decision"], "mesh_green_can_continue")
        self.assertFalse(projection["current_run_can_continue"])
        reasons = {finding["reason"] for finding in projection["findings"]}
        self.assertIn("lifecycle_guard_control_plane_stuck", reasons)
        projected_state = projection["projected_state"]
        self.assertTrue(projected_state["lifecycle_guard_control_plane_stuck"])

    def test_model_mesh_treats_current_lifecycle_state_as_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            run_root = project_root / ".flowpilot" / "runs" / "run-stopped"
            run_root.mkdir(parents=True)
            _write_json(
                project_root / ".flowpilot" / "current.json",
                {
                    "run_id": "run-stopped",
                    "run_root": ".flowpilot/runs/run-stopped",
                    "lifecycle_state": "stopped_by_user",
                    "terminal_lifecycle_status": "stopped_by_user",
                    "ledger_lifecycle_state": "stopped_by_user",
                },
            )
            _write_json(
                run_root / "ledger.json",
                {
                    "terminal_lifecycle": {
                        "terminal": True,
                        "state": "stopped_by_user",
                        "status": "stopped_by_user",
                    },
                    "lifecycle_guard": {
                        "decision": "terminal_return",
                        "next_action": {
                            "action_type": "terminal_lifecycle",
                            "subject_id": "stopped_by_user",
                        },
                    },
                },
            )

            projection = model_mesh.project_live_run(project_root)

        self.assertTrue(projection["terminal_disposition"]["terminal_run"])
        self.assertFalse(projection["current_run_can_continue"])
        self.assertNotEqual(projection["decision"], "mesh_green_can_continue")

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
