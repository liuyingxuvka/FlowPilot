from __future__ import annotations

import importlib.util
from itertools import combinations, product
from math import prod
import sys
import unittest
from pathlib import Path

from scripts.test_tier.source_fingerprint import file_fingerprint, source_snapshot


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    old_path = list(sys.path)
    old_module = sys.modules.get(name)
    sys.modules[name] = module
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old_path
        if old_module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = old_module
    return module


model = load_module(
    "flowpilot_contract_exhaustion_mesh_model",
    ROOT / "simulations" / "flowpilot_contract_exhaustion_mesh_model.py",
)
contract_fake_ai = load_module(
    "flowpilot_contract_driven_fake_ai",
    ROOT / "simulations" / "flowpilot_contract_driven_fake_ai.py",
)
runner = load_module(
    "run_flowpilot_contract_exhaustion_mesh_checks",
    ROOT / "simulations" / "run_flowpilot_contract_exhaustion_mesh_checks.py",
)


def compact_fake_ai_failure(report: dict[str, object]) -> dict[str, object]:
    fake_ai = report.get("fake_ai_responder")
    if not isinstance(fake_ai, dict):
        return {"report_ok": report.get("ok"), "fake_ai_responder": fake_ai}
    summary = fake_ai.get("summary")
    if isinstance(summary, dict):
        return {"report_ok": report.get("ok"), "fake_ai_responder": summary}
    return {
        "report_ok": report.get("ok"),
        "projection_findings": fake_ai.get("projection_findings", [])[:5],
        "missing_required_cell_count": len(fake_ai.get("missing_required_cells", [])),
        "missing_required_cells_sample": fake_ai.get("missing_required_cells", [])[:10],
        "missing_option_value_cell_count": len(fake_ai.get("missing_option_value_cells", [])),
        "missing_option_value_cells_sample": fake_ai.get("missing_option_value_cells", [])[:10],
    }


class FlowPilotContractExhaustionMeshTests(unittest.TestCase):
    @staticmethod
    def current_manifest(*, reused_without_ticket: bool = False) -> dict[str, object]:
        owner_ids = sorted(
            {
                str(definition["execution_owner_id"])
                for definition in runner.TEST_MESH_CHILD_SUITE_DEFINITIONS.values()
            }
        )
        relative_input = Path(__file__).resolve().relative_to(ROOT).as_posix()
        input_fingerprint = file_fingerprint(Path(__file__).resolve())
        owners: dict[str, object] = {}
        for owner_id in owner_ids:
            result_fingerprint = __import__("hashlib").sha256(
                owner_id.encode("utf-8")
            ).hexdigest()
            owner_proof = {
                "artifact_id": f"proof.contract-exhaustion-current.{owner_id}",
                "producer_route": "flowpilot.test-tier.selective-execution",
                "command": f"python -m pytest {relative_input} -q",
                "result_path": f"tmp/test_background/{owner_id}.combined.txt",
                "result_status": "passed",
                "exit_code": 0,
                "artifact_fingerprints": {
                    f"{owner_id}.combined.txt": result_fingerprint
                },
                "covered_obligation_ids": [f"owner:{owner_id}"],
                "assertion_scope": "external_contract",
                "current": True,
                "route_evidence_current": True,
                "progress_only": False,
                "metadata": {"result_fingerprint": result_fingerprint},
            }
            owners[owner_id] = {
                "owner_id": owner_id,
                "result_status": "passed",
                "result_reused": False,
                "identity": {
                    "command_fingerprint": "a" * 64,
                    "test_source_fingerprint": "b" * 64,
                    "tested_artifact_fingerprint": "c" * 64,
                    "dependency_fingerprints": {"fixture": "e" * 64},
                    "environment_fingerprint": "d" * 64,
                    "covered_input_fingerprint": input_fingerprint,
                    "covered_input_fingerprints": {
                        relative_input: input_fingerprint
                    },
                    "covered_obligation_ids": [f"owner:{owner_id}"],
                },
                "result_fingerprint": result_fingerprint,
                "proof_artifact": owner_proof,
                "reuse_ticket": None,
            }
        aggregate_proof = {
            "artifact_id": "proof.contract-exhaustion-current",
            "producer_route": "flowguard-test-mesh",
            "command": "python scripts/run_test_tier.py --tier all --background",
            "result_path": "tmp/test_background/current-all",
            "result_status": "passed",
            "exit_code": 0,
            "artifact_fingerprints": {"all.meta.json": "a" * 64, "all.exit.txt": "b" * 64},
            "covered_obligation_ids": ["all-current-tests"],
            "assertion_scope": "external_contract",
            "current": True,
            "route_evidence_current": True,
            "progress_only": False,
            "metadata": {
                "selected_child_command_count": 23,
                "executed_child_command_count": 23,
                "reused_child_command_count": 0,
                "proof_backed_child_command_count": 23,
            },
        }
        return {
            "schema_version": "flowpilot.acceptance_testmesh_evidence_manifest.v4",
            "snapshot": source_snapshot(),
            "owners": owners,
            "routine": {
                "all": {
                    "result_status": "passed",
                    "selected_count": 23,
                    "test_count": 23,
                    "result_reused": reused_without_ticket,
                    "owner_evidence_ids": owner_ids,
                    "owner_reuse_tickets": {},
                    "proof_artifact": aggregate_proof,
                }
            },
        }

    def test_contract_exhaustion_mesh_accepts_valid_and_rejects_hazards(self) -> None:
        report = runner.run_checks(declaration_only=True)

        self.assertTrue(report["ok"], compact_fake_ai_failure(report))
        self.assertEqual(report["claim_scope"], "declaration_only")
        self.assertEqual(report["evidence_status"], "not_run")
        self.assertEqual(report["model_id"], model.MODEL_ID)
        self.assertGreater(report["required_cells"]["cell_count"], 80)
        self.assertGreaterEqual(report["required_cells"]["family_count"], len(model.CONTRACT_FAMILIES))
        self.assertLessEqual(set(model.CONTRACT_FAMILIES), set(report["required_cells"]["by_family"]))
        self.assertEqual(report["hazards"]["missing_expected_failures"], {})
        self.assertIn(
            "reviewer_packet_issued_with_empty_required_flowguard_manifest",
            report["hazards"]["hazards"]["empty_manifest_review_issued"],
        )
        self.assertIn(
            "flowguard_reissue_lost_evidence_output_policy",
            report["hazards"]["hazards"]["flowguard_reissue_loses_policy"],
        )
        self.assertIn(
            "flowguard_reissue_lost_authorized_result_reads",
            report["hazards"]["hazards"]["flowguard_reissue_loses_authorized_reads"],
        )
        self.assertIn(
            "flowguard_reissue_lost_required_body_open_gate",
            report["hazards"]["hazards"]["flowguard_reissue_loses_required_body_open_gate"],
        )
        self.assertIn(
            "same_root_no_delta_retry_did_not_trigger_break_glass",
            report["hazards"]["hazards"]["same_root_no_delta_without_break_glass"],
        )
        self.assertIn(
            "ordinary_rehearsal_entered_glass_break",
            report["hazards"]["hazards"]["ordinary_rehearsal_enters_glass_break"],
        )
        self.assertNotIn("valid_break_glass_same_root", model.VALID_SCENARIOS)
        self.assertIn("valid_same_root_repaired_before_glass_break", model.VALID_SCENARIOS)
        self.assertIn("same_blocker_six_times_triggers_glass_break_alarm", model.VALID_SCENARIOS)
        self.assertNotIn("same_blocker_six_times_triggers_glass_break_alarm", report["hazards"]["hazards"])
        self.assertEqual(
            model.contract_exhaustion_failures(
                model.SCENARIOS["same_blocker_six_times_triggers_glass_break_alarm"]
            ),
            [],
        )

    def test_contract_exhaustion_required_cells_name_runtime_and_synthetic_owners(self) -> None:
        cells = list(model.REQUIRED_CONTRACT_EXHAUSTION_CELLS)
        owners = {cell["required_evidence_owner"] for cell in cells}
        mutation_kinds = {cell["mutation_kind"] for cell in cells}

        self.assertIn("contract_exhaustion_runtime_matrix", owners)
        self.assertIn("contract_exhaustion_fake_ai_matrix", owners)
        self.assertIn("contract_exhaustion_historical_failure_matrix", owners)
        self.assertIn("review_window_completeness_matrix", owners)
        self.assertIn("review_window_fake_ai_matrix", owners)
        self.assertIn("fake_ai_runtime_replay_matrix", owners)
        self.assertIn("control_plane_ledger_hygiene_fake_ai_matrix", owners)
        self.assertIn("real_issue_backfeed_matrix", owners)
        self.assertIn("integration_cartesian_coverage_matrix", owners)
        self.assertIn("complete_workstream_fake_ai_matrix", owners)

        self.assertLessEqual(model.SYNTHETIC_MUTATION_KINDS, mutation_kinds)
        self.assertTrue(
            [
                cell
                for cell in cells
                if cell["family"] == "flowguard_reissue_packet"
                and cell["mutation_kind"] == "reissue_loses_inherited_policy"
            ]
        )
        self.assertTrue(
            [
                cell
                for cell in cells
                if cell["family"] == "flowguard_reissue_packet"
                and cell["mutation_kind"] == "reissue_loses_inherited_authorized_reads"
            ]
        )
        self.assertTrue(
            [
                cell
                for cell in cells
                if cell["family"] == "flowguard_reissue_packet"
                and cell["mutation_kind"] == "reissue_loses_required_read_manifest"
            ]
        )
        self.assertTrue(
            [
                cell
                for cell in cells
                if cell["family"] == "review_packet"
                and cell["mutation_kind"] == "empty_required_manifest"
            ]
        )
        for family, mutation in (
            ("runtime_pointer_file", "current_pointer.zero_bytes"),
            ("runtime_pointer_file", "index_pointer.zero_bytes"),
            ("runtime_pointer_file", "current_pointer.ambiguous_recovery"),
            ("runtime_pointer_file", "pointer_write_lock.active"),
            ("submit_result_body_entry", "body_entry.stringified_json_object"),
            ("submit_result_body_entry", "body_entry.source_conflict"),
            ("submit_result_body_entry", "body_entry.file_unreadable"),
        ):
            with self.subTest(family=family, mutation=mutation):
                self.assertTrue(
                    [
                        cell
                        for cell in cells
                        if cell["family"] == family
                        and cell["mutation_kind"] == mutation
                        and cell["required_evidence_owner"] == "contract_exhaustion_runtime_matrix"
                    ]
                )
        self.assertTrue(
            [
                cell
                for cell in cells
                if cell["family"] == "review_packet"
                and cell.get("contract_path") == "envelope.review_window"
                and cell["mutation_kind"] == "missing_required_field"
            ]
        )
        self.assertTrue(
            [
                cell
                for cell in cells
                if cell["family"] == "task_packet_body"
                and cell.get("contract_path")
                == "current_handoff_contract.required_report_contract.ownership_coverage_rule"
            ]
        )
        self.assertTrue(
            [
                cell
                for cell in cells
                if cell["family"] == "integration_cartesian_coverage"
                and cell["mutation_kind"] == "missing_integration_cartesian_shard"
            ]
        )
        workstream_profile_cells = {
            str(cell["mutation_kind"])
            for cell in cells
            if cell["required_evidence_owner"] == "complete_workstream_fake_ai_matrix"
        }
        self.assertEqual(
            workstream_profile_cells,
            {
                *contract_fake_ai.COMPLETE_WORKSTREAM_PROFILE_IDS,
                *contract_fake_ai.RESOURCE_DISCOVERY_PROFILE_IDS,
            },
        )

    def test_every_semantic_child_suite_names_one_execution_owner(self) -> None:
        definitions = runner.TEST_MESH_CHILD_SUITE_DEFINITIONS
        required_owner_ids = {
            str(cell["required_evidence_owner"])
            for cell in model.REQUIRED_CONTRACT_EXHAUSTION_CELLS
        }

        self.assertEqual(set(definitions), required_owner_ids)
        for semantic_owner_id, definition in definitions.items():
            with self.subTest(semantic_owner_id=semantic_owner_id):
                execution_owner_id = definition.get("execution_owner_id")
                self.assertIsInstance(execution_owner_id, str)
                self.assertTrue(execution_owner_id)

    def test_complete_workstream_and_resource_universes_are_full_cartesian_with_oracles(self) -> None:
        universes = (
            (
                model.COMPLETE_WORKSTREAM_CARTESIAN_AXES,
                model.complete_workstream_cartesian_cells(),
                model.COMPLETE_WORKSTREAM_HIGH_RISK_INTERACTION_GROUPS,
            ),
            (
                model.RESOURCE_DISCOVERY_CARTESIAN_AXES,
                model.resource_discovery_cartesian_cells(),
                model.RESOURCE_DISCOVERY_HIGH_RISK_INTERACTION_GROUPS,
            ),
        )
        for axes, cells, high_risk_groups in universes:
            with self.subTest(axis_names=tuple(axes)):
                self.assertEqual(len(cells), prod(len(values) for values in axes.values()))
                self.assertEqual(len({cell["cell_id"] for cell in cells}), len(cells))
                self.assertTrue(all(cell["expected_outcome"] for cell in cells))
                self.assertTrue(
                    all(
                        cell["required_evidence_owner"] == "complete_workstream_cartesian_matrix"
                        for cell in cells
                    )
                )
                axis_names = tuple(axes)
                for left, right in combinations(axis_names, 2):
                    observed = {
                        (
                            cell["axis_assignment"][left],
                            cell["axis_assignment"][right],
                        )
                        for cell in cells
                    }
                    expected = set(product(axes[left], axes[right]))
                    self.assertEqual(observed, expected, (left, right))
                for group in high_risk_groups:
                    observed = {
                        tuple(cell["axis_assignment"][axis] for axis in group)
                        for cell in cells
                    }
                    expected = set(product(*(axes[axis] for axis in group)))
                    self.assertEqual(observed, expected, group)

    def test_review_window_completeness_cells_cover_every_declared_flow(self) -> None:
        cells = list(model.REQUIRED_CONTRACT_EXHAUSTION_CELLS)
        flow_ids = set(model.review_window_contracts.review_flow_ids())
        path_cells = {
            str(cell.get("review_flow_id"))
            for cell in cells
            if cell.get("required_evidence_owner") == "review_window_completeness_matrix"
            and cell.get("mutation_kind") == "missing_window_path"
        }
        fake_ai_cells = {
            str(cell.get("review_flow_id"))
            for cell in cells
            if cell.get("required_evidence_owner") == "review_window_fake_ai_matrix"
        }
        profile_cells = {
            (
                str(cell.get("review_flow_id")),
                str(cell.get("mutation_kind")),
                str(cell.get("material_state_class")),
                str(cell.get("retry_count_class")),
            )
            for cell in cells
            if cell.get("required_evidence_owner") == "review_window_fake_ai_matrix"
        }

        self.assertLessEqual(flow_ids, path_cells)
        self.assertLessEqual(flow_ids, fake_ai_cells)
        for flow_id in flow_ids:
            for profile_id in model.review_window_contracts.REVIEW_WINDOW_FAKE_AI_PROFILE_IDS:
                for material_state in model.review_window_contracts.REVIEW_WINDOW_MATERIAL_STATE_CLASSES:
                    for retry_class in model.review_window_contracts.RETRY_COUNT_CLASSES:
                        self.assertIn((flow_id, profile_id, material_state, retry_class), profile_cells)

    def test_ai_contract_projection_and_retry_cells_are_required(self) -> None:
        cells = list(model.REQUIRED_CONTRACT_EXHAUSTION_CELLS)
        cell_index = {
            (
                cell.get("family", ""),
                cell.get("contract_path", ""),
                cell.get("mutation_kind", ""),
                cell.get("required_evidence_owner", ""),
            )
            for cell in cells
        }

        expected_cells = {
            (
                "flowguard_check_packet",
                "envelope.result_contract_profile_ids[flowguard.semantic_recheck_required]",
                "missing_result_contract_profile",
                "contract_exhaustion_runtime_matrix",
            ),
            (
                "flowguard_check_packet",
                "current_handoff_contract.required_report_contract.allowed_value_options.semantic_recheck.subject_bound_semantic_coverage",
                "missing_allowed_value_options",
                "contract_exhaustion_runtime_matrix",
            ),
            (
                "flowguard_check_packet",
                "current_handoff_contract.required_report_contract.field_type_requirements.semantic_recheck.subject_bound_semantic_coverage",
                "missing_field_type_requirements",
                "contract_exhaustion_runtime_matrix",
            ),
            (
                "flowguard_check_packet",
                "current_handoff_contract.required_report_contract.forbidden_aliases.semantic_recheck.authorized_result_body_consumed",
                "forbidden_alias_used",
                "contract_exhaustion_runtime_matrix",
            ),
            (
                "flowguard_check_result",
                "result.semantic_recheck.subject_bound_semantic_coverage",
                "wrong_allowed_value",
                "contract_exhaustion_fake_ai_matrix",
            ),
            (
                "flowguard_check_result",
                "result.semantic_recheck.authorized_result_body_consumed",
                "forbidden_alias_used",
                "contract_exhaustion_fake_ai_matrix",
            ),
            (
                "flowguard_check_result",
                "result.semantic_recheck.subject_bound_semantic_coverage",
                "corrected_second_retry",
                "contract_exhaustion_fake_ai_matrix",
            ),
            (
                "flowguard_check_result",
                "result.body",
                "malformed_body.unquoted_keys",
                "contract_exhaustion_fake_ai_matrix",
            ),
            (
                "review_packet",
                "result.body",
                "malformed_body.markdown_wrapped_json",
                "contract_exhaustion_fake_ai_matrix",
            ),
        }
        self.assertLessEqual(expected_cells, cell_index)

    def test_historical_failure_families_require_normal_repair_before_glass_break(self) -> None:
        cells = [
            cell
            for cell in model.REQUIRED_CONTRACT_EXHAUSTION_CELLS
            if cell["required_evidence_owner"] == "contract_exhaustion_historical_failure_matrix"
        ]
        source_classes = {cell["source_class"] for cell in cells}

        self.assertGreaterEqual(len(model.HISTORICAL_FAILURE_FAMILIES), 9)
        self.assertGreaterEqual(len(cells), 20)
        for source_class in (
            "worker_output_contract_failure",
            "mail_chain_or_packet_body_loss",
            "wrong_address_or_current_wait",
            "route_mutation_stale_evidence",
            "historical_or_background_evidence_loss",
            "install_source_split_brain",
            "pm_repair_target_or_producer_loss",
            "pm_repair_information_flow_loss",
            "same_family_control_blocker_repetition",
            "current_control_pointer_corruption",
        ):
            with self.subTest(source_class=source_class):
                self.assertIn(source_class, source_classes)
        for cell in cells:
            with self.subTest(cell_id=cell["cell_id"]):
                self.assertFalse(cell["glass_break_allowed_in_acceptance"])
                self.assertTrue(cell["normal_repair_route"])

    def test_contract_exhaustion_test_mesh_registers_every_required_owner(self) -> None:
        report = runner.run_checks(evidence_manifest=self.current_manifest())
        required_owners = {
            cell["required_evidence_owner"]
            for cell in report["required_cells"]["required_cells"]
        }
        child_suites = report["test_mesh"]["child_suites"]

        self.assertTrue(report["test_mesh"]["ok"], report["test_mesh"])
        self.assertEqual(set(report["test_mesh"]["required_child_suite_owners"]), required_owners)
        self.assertEqual(set(child_suites), required_owners)
        self.assertEqual(report["test_mesh"]["unregistered_required_child_suites"], [])
        self.assertEqual(report["test_mesh"]["missing_or_stale_child_suites"], [])
        for suite in child_suites.values():
            self.assertEqual(suite["test_count"], 23)
            self.assertNotEqual(suite["test_count"], suite["owned_cell_count"])
            self.assertTrue(suite["proof_artifact"])
            self.assertTrue(suite["reuse_ticket"])
        self.assertGreater(
            child_suites["contract_exhaustion_historical_failure_matrix"]["owned_cell_count"],
            0,
        )
        self.assertGreater(
            child_suites["fake_ai_runtime_replay_matrix"]["owned_cell_count"],
            0,
        )
        self.assertGreater(
            child_suites["fake_ai_runtime_replay_matrix"]["owned_declared_cell_count"],
            child_suites["fake_ai_runtime_replay_matrix"]["owned_cell_count"],
        )
        self.assertTrue(
            child_suites["fake_ai_runtime_replay_matrix"]["child_declaration_receipts"]
        )
        self.assertGreater(
            child_suites["control_plane_ledger_hygiene_fake_ai_matrix"]["owned_cell_count"],
            0,
        )
        self.assertGreater(
            child_suites["control_plane_ledger_hygiene_fake_ai_matrix"]["owned_declared_cell_count"],
            child_suites["control_plane_ledger_hygiene_fake_ai_matrix"]["owned_cell_count"],
        )
        self.assertTrue(
            child_suites["control_plane_ledger_hygiene_fake_ai_matrix"]["child_declaration_receipts"]
        )
        self.assertGreater(
            child_suites["real_issue_backfeed_matrix"]["owned_cell_count"],
            0,
        )

    def test_contract_exhaustion_summary_keeps_large_cell_matrix_out_of_file_artifact(self) -> None:
        report = runner.run_checks(evidence_manifest=self.current_manifest())
        summary = runner._summary_report(report)

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["required_cell_count"], report["required_cells"]["cell_count"])
        self.assertIn("control_plane_ledger_hygiene_fake_ai_matrix", summary["required_child_suite_owners"])
        self.assertNotIn("required_cells", summary)
        self.assertIn("child_suites", summary)
        for suite in summary["child_suites"].values():
            self.assertNotIn("owned_case_ids", suite)

    def test_contract_exhaustion_reused_proof_without_ticket_blocks_strict_evidence(self) -> None:
        report = runner.run_checks(evidence_manifest=self.current_manifest(reused_without_ticket=True))

        self.assertFalse(report["ok"])
        self.assertIn(
            "all:missing_test_reuse_ticket",
            report["test_mesh"]["execution_evidence"]["failures"],
        )

    def test_contract_exhaustion_registers_runtime_replay_and_backfeed_cells(self) -> None:
        cells = list(model.REQUIRED_CONTRACT_EXHAUSTION_CELLS)
        runtime_replay_receipts = [
            cell
            for cell in cells
            if cell["required_evidence_owner"] == "fake_ai_runtime_replay_matrix"
        ]
        hygiene_receipts = [
            cell
            for cell in cells
            if cell["required_evidence_owner"] == "control_plane_ledger_hygiene_fake_ai_matrix"
        ]
        backfeed_cells = [
            cell
            for cell in cells
            if cell["required_evidence_owner"] == "real_issue_backfeed_matrix"
        ]
        replay_reactions = {
            reaction
            for cell in runtime_replay_receipts
            for reaction in cell.get("child_reaction_ids", ())
        }
        backfeed_ids = {cell["cell_id"] for cell in backfeed_cells}

        self.assertEqual(len(runtime_replay_receipts), 1)
        self.assertEqual(len(hygiene_receipts), 1)
        self.assertGreater(runtime_replay_receipts[0]["child_declared_cell_count"], 400)
        self.assertGreater(hygiene_receipts[0]["child_declared_cell_count"], 100_000)
        self.assertEqual(len(runtime_replay_receipts[0]["child_receipt_sha256"]), 64)
        self.assertEqual(len(hygiene_receipts[0]["child_receipt_sha256"]), 64)
        self.assertGreaterEqual(len(backfeed_cells), 6)
        self.assertIn("mechanical_reject_reissue_with_strict_json_feedback", replay_reactions)
        self.assertIn("accepted_after_reissue", replay_reactions)
        self.assertIn("breakglass_after_fifth_same_failure", replay_reactions)
        self.assertIn("real_issue_backfeed.real.fake_ai.pseudo_json_repeated_reissue", backfeed_ids)
        self.assertIn("real_issue_backfeed.real.contract_surface.acceptance_owner_hidden_rule", backfeed_ids)

    def test_contract_exhaustion_runner_checks_fake_ai_responder_cartesian_parity(self) -> None:
        report = runner.run_checks(declaration_only=True)
        fake_ai = report["fake_ai_responder"]
        summary = fake_ai["summary"]

        self.assertIn("missing_by_contract", summary)
        self.assertIn("missing_by_mutation_kind", summary)
        self.assertEqual(summary["projection_finding_count"], len(fake_ai["projection_findings"]))
        self.assertEqual(summary["missing_required_cell_count"], len(fake_ai["missing_required_cells"]))
        self.assertEqual(summary["missing_option_value_cell_count"], len(fake_ai["missing_option_value_cells"]))
        self.assertTrue(fake_ai["ok"], compact_fake_ai_failure(report))
        self.assertEqual(fake_ai["projection_findings"], [])
        self.assertEqual(fake_ai["missing_required_cells"], [])
        self.assertEqual(fake_ai["missing_option_value_cells"], [])
        self.assertGreater(fake_ai["contract_count"], len(model.packet_result_contracts.PACKET_RESULT_CONTRACTS))
        self.assertGreater(fake_ai["required_responder_cell_count"], 50)
        self.assertGreaterEqual(fake_ai["generated_cell_count"], fake_ai["required_responder_cell_count"])
        self.assertEqual(
            fake_ai["generated_option_value_cell_count"],
            fake_ai["required_option_value_cell_count"],
        )
        self.assertGreater(fake_ai["required_option_value_cell_count"], 150)

    def test_fake_ai_responder_parity_does_not_absorb_runtime_owned_cells(self) -> None:
        report = runner.run_checks(declaration_only=True)
        fake_ai_missing = {
            (
                cell["contract_family_id"],
                cell["contract_path"],
                cell["mutation_kind"],
            )
            for cell in report["fake_ai_responder"]["missing_required_cells"]
        }
        runtime_owned_supported = {
            (
                str(cell.get("contract_family_id") or ""),
                str(cell.get("contract_path") or ""),
                str(cell.get("mutation_kind") or ""),
            )
            for cell in model.REQUIRED_CONTRACT_EXHAUSTION_CELLS
            if cell.get("required_evidence_owner") == "contract_exhaustion_runtime_matrix"
            and cell.get("mutation_kind") in runner.RESPONDER_SUPPORTED_MUTATIONS
        }

        self.assertEqual(fake_ai_missing & runtime_owned_supported, set())

    def test_contract_driven_fake_ai_enumerates_every_packet_result_contract(self) -> None:
        for row in model.packet_result_contracts.PACKET_RESULT_CONTRACTS:
            family_id = str(row["family_id"])
            with self.subTest(family_id=family_id):
                contract = model.packet_result_contracts.effective_result_contract_for_family(family_id)
                responder = contract_fake_ai.ContractDrivenFakeAIResponder(contract)
                cells = {
                    (cell["contract_path"], cell["mutation_kind"])
                    for cell in responder.coverage_cells()
                }

                self.assertEqual(responder.projection_findings(), [])
                for field in responder.required_fields:
                    self.assertIn((str(field), "missing_required_field"), cells)
                    self.assertIn((str(field), "wrong_type"), cells)
                for field in responder.required_child_fields:
                    self.assertIn((str(field), "missing_required_child_field"), cells)
                    self.assertIn((str(field), "wrong_type"), cells)
                for field in responder.non_empty_array_fields:
                    self.assertIn((str(field), "empty_required_array"), cells)
                for field in responder.forbidden_fields:
                    self.assertIn((str(field), "forbidden_field_present"), cells)
                for field_path in responder.allowed_value_options:
                    self.assertIn(
                        (
                            "current_handoff_contract.required_report_contract."
                            f"allowed_value_options.{field_path}",
                            "missing_allowed_value_options",
                        ),
                        cells,
                    )
                    self.assertIn((f"result.{field_path}", "wrong_allowed_value"), cells)
                    for value in responder.allowed_value_options[field_path]:
                        with self.subTest(family_id=family_id, field=field_path, value=value):
                            payload = responder.allowed_value_payload(field_path, value)
                            self.assertIn(value, responder.option_values_seen(payload, field_path))

    def test_contract_driven_fake_ai_enumerates_result_contract_profiles(self) -> None:
        for profile_id in model.packet_result_contracts.packet_stage_evidence_matrix.RESULT_CONTRACT_PROFILE_IDS:
            with self.subTest(profile_id=profile_id):
                profile = model.packet_result_contracts.packet_stage_evidence_matrix.result_contract_profile(profile_id)
                family_id = str(profile["family_id"])
                sample_binding = model.PROFILE_EXHAUSTION_SAMPLE_BINDINGS.get(profile_id, {})
                contract = model.packet_result_contracts.effective_result_contract_for_family(
                    family_id,
                    result_contract_profile_ids=(profile_id,),
                    result_contract_profile_bindings={profile_id: sample_binding},
                )
                responder = contract_fake_ai.ContractDrivenFakeAIResponder(contract)
                cells = {
                    (cell["contract_path"], cell["mutation_kind"])
                    for cell in responder.coverage_cells()
                }

                self.assertEqual(responder.projection_findings(), [])
                for field in profile.get("required_fields", ()):
                    self.assertIn((str(field), "missing_required_field"), cells)
                    self.assertIn((str(field), "wrong_type"), cells)
                for field in profile.get("required_child_fields", ()):
                    self.assertIn((str(field), "missing_required_child_field"), cells)
                    self.assertIn((str(field), "wrong_type"), cells)
                for field in profile.get("non_empty_array_fields", ()):
                    self.assertIn((str(field), "empty_required_array"), cells)
                for field in contract.get("field_type_requirements", ()):
                    field_path = str(field)
                    self.assertIn(
                        (
                            "current_handoff_contract.required_report_contract."
                            f"field_type_requirements.{field_path}",
                            "missing_field_type_requirements",
                        ),
                        cells,
                    )
                    self.assertIn((f"result.{field_path}", "wrong_type"), cells)
                for alias in contract.get("forbidden_aliases", ()):
                    alias_path = str(alias)
                    self.assertIn(
                        (
                            "current_handoff_contract.required_report_contract."
                            f"forbidden_aliases.{alias_path}",
                            "forbidden_alias_used",
                        ),
                        cells,
                    )
                    self.assertIn((f"result.{alias_path}", "forbidden_alias_used"), cells)
                for field_path, values in responder.allowed_value_options.items():
                    for value in values:
                        with self.subTest(profile_id=profile_id, field=field_path, value=value):
                            payload = responder.allowed_value_payload(field_path, value)
                            self.assertIn(value, responder.option_values_seen(payload, field_path))

    def test_contract_driven_fake_ai_materializes_supported_payload_mutations(self) -> None:
        for contract_id, contract in runner._responder_contracts().items():
            responder = contract_fake_ai.ContractDrivenFakeAIResponder(contract)
            if responder.projection_findings():
                continue
            with self.subTest(contract_id=contract_id, mutation="missing_required_field"):
                for field_path in responder.required_fields:
                    self.assertIsInstance(responder.missing_required_field_payload(field_path), dict)
            with self.subTest(contract_id=contract_id, mutation="missing_required_child_field"):
                for field_path in responder.required_child_fields:
                    self.assertIsInstance(responder.missing_required_child_field_payload(field_path), dict)
            with self.subTest(contract_id=contract_id, mutation="wrong_type"):
                for field_path in (*responder.required_fields, *responder.required_child_fields):
                    self.assertIsInstance(responder.wrong_type_payload(field_path), dict)
            with self.subTest(contract_id=contract_id, mutation="empty_required_array"):
                for field_path in responder.non_empty_array_fields:
                    self.assertIsInstance(responder.empty_required_array_payload(field_path), dict)
            with self.subTest(contract_id=contract_id, mutation="forbidden_field_present"):
                for field_path in responder.forbidden_fields:
                    self.assertIsInstance(responder.forbidden_field_payload(field_path), dict)
            with self.subTest(contract_id=contract_id, mutation="wrong_allowed_value"):
                for field_path, values in responder.allowed_value_options.items():
                    payload = responder.invalid_allowed_value_payload(field_path)
                    seen_values = responder.option_values_seen(payload, field_path)
                    self.assertTrue(any(value not in values for value in seen_values))
            with self.subTest(contract_id=contract_id, mutation="forbidden_alias_used"):
                for alias_path in responder.forbidden_aliases:
                    self.assertIsInstance(responder.alias_payload(alias_path), dict)
            with self.subTest(contract_id=contract_id, mutation="malformed_body"):
                for profile_id in contract_fake_ai.MALFORMED_BODY_PROFILE_IDS:
                    self.assertIsInstance(responder.malformed_body(profile_id), str)
            if contract_id == model.FORMAL_ARTIFACT_EXHAUSTION_CONTRACT_ID:
                with self.subTest(contract_id=contract_id, mutation="formal_artifact"):
                    mutation_kinds = {
                        cell["mutation_kind"]
                        for cell in responder.formal_artifact_cells()
                    }
                    self.assertEqual(
                        mutation_kinds,
                        set(contract_fake_ai.FORMAL_ARTIFACT_PROFILE_IDS),
                    )

    def test_packet_result_contract_fields_are_expanded_into_cells(self) -> None:
        cells = list(model.REQUIRED_CONTRACT_EXHAUSTION_CELLS)
        cell_index = {
            (
                cell.get("contract_family_id", ""),
                cell.get("contract_path", ""),
                cell.get("mutation_kind", ""),
            )
            for cell in cells
        }

        for row in model.packet_result_contracts.PACKET_RESULT_CONTRACTS:
            family_id = str(row["family_id"])
            for field in row.get("required_fields", ()):
                with self.subTest(family_id=family_id, field=field, mutation="missing_required_field"):
                    self.assertIn((family_id, str(field), "missing_required_field"), cell_index)
                with self.subTest(family_id=family_id, field=field, mutation="wrong_type"):
                    self.assertIn((family_id, str(field), "wrong_type"), cell_index)
            for field in row.get("required_child_fields", ()):
                with self.subTest(family_id=family_id, field=field, mutation="missing_required_child_field"):
                    self.assertIn((family_id, str(field), "missing_required_child_field"), cell_index)
            for field in row.get("forbidden_fields", ()):
                with self.subTest(family_id=family_id, field=field, mutation="forbidden_field_present"):
                    self.assertIn((family_id, str(field), "forbidden_field_present"), cell_index)

    def test_packet_result_contract_allowed_options_are_expanded_into_cells(self) -> None:
        cells = list(model.REQUIRED_CONTRACT_EXHAUSTION_CELLS)
        cell_index = {
            (
                cell.get("contract_family_id", ""),
                cell.get("contract_path", ""),
                cell.get("mutation_kind", ""),
                cell.get("required_evidence_owner", ""),
            )
            for cell in cells
        }

        for row in model.packet_result_contracts.PACKET_RESULT_CONTRACTS:
            family_id = str(row["family_id"])
            for field in model.packet_result_contracts.allowed_value_options_for_family(family_id):
                field_path = str(field)
                with self.subTest(family_id=family_id, field=field_path, mutation="missing_allowed_value_options"):
                    self.assertIn(
                        (
                            family_id,
                            "current_handoff_contract.required_report_contract."
                            f"allowed_value_options.{field_path}",
                            "missing_allowed_value_options",
                            "contract_exhaustion_runtime_matrix",
                        ),
                        cell_index,
                    )
                with self.subTest(family_id=family_id, field=field_path, mutation="wrong_allowed_value"):
                    self.assertIn(
                        (
                            family_id,
                            f"result.{field_path}",
                            "wrong_allowed_value",
                            "contract_exhaustion_fake_ai_matrix",
                        ),
                        cell_index,
                    )

    def test_result_contract_profile_allowed_options_are_expanded_into_cells(self) -> None:
        cells = list(model.REQUIRED_CONTRACT_EXHAUSTION_CELLS)
        cell_index = {
            (
                cell.get("contract_family_id", ""),
                cell.get("contract_path", ""),
                cell.get("mutation_kind", ""),
                cell.get("required_evidence_owner", ""),
            )
            for cell in cells
        }

        for profile_id in model.packet_result_contracts.packet_stage_evidence_matrix.RESULT_CONTRACT_PROFILE_IDS:
            profile = model.packet_result_contracts.packet_stage_evidence_matrix.result_contract_profile(profile_id)
            family_id = str(profile["family_id"])
            sample_binding = model.PROFILE_EXHAUSTION_SAMPLE_BINDINGS.get(profile_id, {})
            effective_contract = model.packet_result_contracts.effective_result_contract_for_family(
                family_id,
                result_contract_profile_ids=(profile_id,),
                result_contract_profile_bindings={profile_id: sample_binding},
            )
            base_allowed_fields = set(model.packet_result_contracts.allowed_value_options_for_family(family_id))
            profile_allowed_fields = sorted(
                str(field)
                for field in (effective_contract.get("allowed_value_options") or {})
                if str(field) not in base_allowed_fields
            )

            self.assertGreater(
                len(profile_allowed_fields),
                0,
                f"{profile_id} sample binding did not expose any profile-owned finite option fields",
            )
            for field_path in profile_allowed_fields:
                with self.subTest(profile_id=profile_id, field=field_path, mutation="missing_allowed_value_options"):
                    self.assertIn(
                        (
                            profile_id,
                            "current_handoff_contract.required_report_contract."
                            f"allowed_value_options.{field_path}",
                            "missing_allowed_value_options",
                            "contract_exhaustion_runtime_matrix",
                        ),
                        cell_index,
                    )
                with self.subTest(profile_id=profile_id, field=field_path, mutation="wrong_allowed_value"):
                    self.assertIn(
                        (
                            profile_id,
                            f"result.{field_path}",
                            "wrong_allowed_value",
                            "contract_exhaustion_fake_ai_matrix",
                        ),
                        cell_index,
                    )

    def test_formal_artifact_contract_faults_are_expanded_into_fake_ai_cells(self) -> None:
        cells = list(model.REQUIRED_CONTRACT_EXHAUSTION_CELLS)
        cell_index = {
            (
                cell.get("contract_family_id", ""),
                cell.get("mutation_kind", ""),
                cell.get("required_evidence_owner", ""),
            )
            for cell in cells
        }

        for artifact_contract in model.formal_artifact_contracts.all_contracts():
            contract_id = str(artifact_contract["contract_id"])
            for profile_id in model.formal_artifact_contracts.fault_modes(artifact_contract):
                with self.subTest(contract_id=contract_id, profile_id=profile_id):
                    self.assertIn(
                        (
                            contract_id,
                            profile_id,
                            "contract_exhaustion_fake_ai_matrix",
                        ),
                        cell_index,
                    )

    def test_formal_artifact_exhaustion_contracts_cover_registry(self) -> None:
        contract_ids = set(model.FORMAL_ARTIFACT_EXHAUSTION_CONTRACTS)
        cell_contract_ids = {
            str(cell.get("contract_family_id") or "")
            for cell in model.REQUIRED_CONTRACT_EXHAUSTION_CELLS
            if str(cell.get("contract_path") or "").startswith("artifact.")
        }

        for artifact_contract in model.formal_artifact_contracts.all_contracts():
            contract_id = str(artifact_contract["contract_id"])
            with self.subTest(contract_id=contract_id):
                self.assertIn(contract_id, contract_ids)
                self.assertIn(contract_id, cell_contract_ids)
                exhaustion_contract = model.FORMAL_ARTIFACT_EXHAUSTION_CONTRACTS[contract_id]
                formal_contract = exhaustion_contract["formal_artifact_contract"]
                self.assertEqual(formal_contract["artifact_id"], artifact_contract["artifact_id"])
                self.assertEqual(
                    tuple(formal_contract["required_field_paths"]),
                    model.formal_artifact_contracts.required_field_paths(artifact_contract),
                )

    def test_contract_exhaustion_runtime_regressions_exist(self) -> None:
        test_text = (ROOT / "tests" / "test_flowpilot_core_runtime.py").read_text(encoding="utf-8")

        for test_name in (
            "test_review_packet_is_not_issued_with_empty_required_flowguard_manifest",
            "test_flowguard_packet_rejects_missing_evidence_output_policy",
            "test_break_glass_counts_same_flowguard_root_cause_across_surface_gates",
            "test_flowguard_fallback_evidence_is_mechanically_reissued",
            "test_flowguard_reissue_inherits_required_authorized_result_reads",
            "test_flowguard_semantic_recheck_reissue_inherits_required_authorized_reads",
            "test_reissued_flowguard_result_blocks_without_inherited_body_open",
            "test_pm_repair_decision_reason_only_is_rejected_when_obligations_exist",
            "test_pm_repair_obligation_rejects_stale_or_registry_only_disposition",
            "test_repair_packet_and_flowguard_recheck_must_consume_repair_obligations",
            "test_semantic_recheck_contract_projects_ai_facing_fields_and_options",
            "test_semantic_recheck_near_synonyms_reissue_with_correct_minimal_shape",
            "test_semantic_recheck_wrong_value_then_corrected_retry_returns_to_legal_path",
            "test_corrupt_current_pointer_recovers_from_single_current_run_evidence",
            "test_corrupt_index_pointer_rebuilds_without_new_pointer_fields",
            "test_pointer_recovery_respects_active_runtime_json_write_lock",
            "test_submit_result_body_file_accepts_top_level_json_object",
            "test_submit_result_rejects_pseudo_json_before_loading_current_run",
            "test_submit_result_rejects_invalid_body_sources_without_normalizing",
        ):
            with self.subTest(test_name=test_name):
                if test_name.startswith("test_semantic_recheck_"):
                    projection_text = (ROOT / "tests" / "test_flowpilot_ai_contract_projection.py").read_text(
                        encoding="utf-8"
                    )
                    self.assertIn(test_name, projection_text)
                elif test_name.startswith("test_submit_result_"):
                    entrypoint_text = (ROOT / "tests" / "test_flowpilot_new_entrypoint.py").read_text(
                        encoding="utf-8"
                    )
                    self.assertIn(test_name, entrypoint_text)
                else:
                    self.assertIn(test_name, test_text)


if __name__ == "__main__":
    unittest.main()
