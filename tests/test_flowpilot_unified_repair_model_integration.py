from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SIMULATIONS = ROOT / "simulations"
if str(SIMULATIONS) not in sys.path:
    sys.path.insert(0, str(SIMULATIONS))

import flowpilot_blocker_repair_information_flow_model as blocker_model
import flowpilot_control_transaction_registry_model as registry_model
import flowpilot_route_replanning_policy_model as replanning_model
import flowpilot_validation_pm_gate_model as validation_gate_model
import run_flowpilot_blocker_repair_information_flow_checks as blocker_runner
import run_flowpilot_contract_exhaustion_mesh_checks as contract_exhaustion_runner
import run_flowpilot_control_transaction_registry_checks as registry_runner
import run_flowpilot_repair_transaction_checks as repair_transaction_runner
import run_flowpilot_route_replanning_policy_checks as replanning_runner
import run_flowpilot_unified_repair_exact_native_test_owner as exact_native_test_runner
import run_flowpilot_unified_repair_integrity_checks as unified_runner
import run_flowpilot_unified_repair_native_runtime_conformance as native_runtime_runner
import run_flowpilot_validation_pm_gate_checks as validation_gate_runner


class FlowPilotUnifiedRepairModelIntegrationTests(unittest.TestCase):
    def test_native_owner_command_is_public_and_machine_independent(self) -> None:
        self.assertEqual(
            native_runtime_runner.OWNER_COMMAND,
            "python simulations/run_flowpilot_unified_repair_native_runtime_conformance.py",
        )
        self.assertNotIn("\\Users\\", native_runtime_runner.OWNER_COMMAND)
        self.assertNotRegex(native_runtime_runner.OWNER_COMMAND, r"^[A-Za-z]:")
        exact_command = " ".join(exact_native_test_runner._portable_command())
        self.assertTrue(exact_command.startswith("python -m pytest "))
        self.assertNotIn("\\Users\\", exact_command)
        self.assertNotRegex(exact_command, r"^[A-Za-z]:")

    def test_pm_historical_defect_is_direct_post_work_repair_not_blocker(self) -> None:
        valid = replanning_model._scenario_state(
            replanning_model.VALID_PM_HISTORICAL_DEFECT_REPAIR
        )
        forced_blocker = replanning_model._scenario_state(
            replanning_model.PM_HISTORICAL_DEFECT_FORCED_THROUGH_BLOCKER
        )
        missing_observation = replanning_model._scenario_state(
            replanning_model.PM_HISTORICAL_DEFECT_WITHOUT_OBSERVATION
        )

        self.assertEqual(replanning_model.policy_failures(valid), [])
        self.assertFalse(valid.blocker_prerequisite_required)
        self.assertTrue(valid.post_work_repair)
        self.assertFalse(valid.pre_work_decomposition)
        self.assertTrue(replanning_model.policy_failures(forced_blocker))
        self.assertTrue(replanning_model.policy_failures(missing_observation))
        self.assertTrue(replanning_runner.run_checks()["ok"])

    def test_blocker_child_delegates_typed_origin_to_shared_engine(self) -> None:
        worker = blocker_model._scenario_state(
            blocker_model.VALID_WORKER_BLOCKER_REISSUE
        )
        pm_direct = blocker_model._scenario_state(
            blocker_model.PM_PROACTIVE_REPAIR_MISROUTED_TO_BLOCKER_CHILD
        )
        origin_mismatch = blocker_model._scenario_state(
            blocker_model.BLOCKER_SOURCE_TRIGGER_ORIGIN_MISMATCH
        )

        self.assertEqual(worker.repair_trigger_origin, "worker_failure")
        self.assertTrue(worker.shared_engine_handoff_recorded)
        self.assertEqual(blocker_model.information_flow_failures(worker), [])
        self.assertTrue(blocker_model.information_flow_failures(pm_direct))
        self.assertIn(
            "blocker source role and typed trigger origin do not describe the same intake",
            blocker_model.information_flow_failures(origin_mismatch),
        )
        self.assertTrue(blocker_runner.run_checks()["ok"])

    def test_repair_transaction_reaches_shared_engine_handoff(self) -> None:
        report = repair_transaction_runner.run_checks()

        self.assertTrue(report["ok"], report["hazard_checks"])
        self.assertIn(
            "router_hands_blocker_trigger_to_unified_repair_engine",
            repair_transaction_runner.REQUIRED_LABELS,
        )
        self.assertTrue(
            report["hazard_checks"]["hazards"][
                "blocker_child_claims_shared_engine_ownership"
            ]["detected"]
        )

    def test_staged_effect_gate_has_atomic_commit_and_safe_disposal(self) -> None:
        report = validation_gate_runner.run_checks()
        labels = validation_gate_model.REQUIRED_SAFE_LABELS

        self.assertTrue(report["ok"], report["hazard_detection"])
        self.assertIn("dispose_rejected_staged_effect_without_worker", labels)
        self.assertIn("dispose_cancelled_staged_effect_without_worker", labels)
        for scenario in (
            "rejected_staged_effect_not_disposed",
            "cancelled_staged_effect_not_disposed",
            "rejected_staged_effect_opens_worker",
            "accepted_staged_effect_commit_not_atomic",
        ):
            self.assertTrue(
                report["hazard_detection"]["hazards"][scenario],
                scenario,
            )

    def test_control_transaction_registry_owns_commit_and_disposal_targets(self) -> None:
        report = registry_runner.run_checks()
        committed = registry_model._scenario_state(
            registry_model.VALID_STAGED_REPAIR_EFFECT_COMMIT
        )
        rejected = registry_model._scenario_state(
            registry_model.VALID_REJECTED_STAGED_EFFECT_DISPOSAL
        )

        self.assertTrue(report["ok"], report["hazard_checks"])
        self.assertEqual(
            registry_model.required_commit_targets(committed),
            registry_model.STAGED_EFFECT_COMMIT_TARGETS,
        )
        self.assertEqual(
            registry_model.required_commit_targets(rejected),
            registry_model.STAGED_EFFECT_DISPOSITION_TARGETS,
        )
        self.assertEqual(registry_model.control_transaction_failures(committed), [])
        self.assertEqual(registry_model.control_transaction_failures(rejected), [])

    def test_native_evidence_manifest_has_singular_owners_and_fails_closed(
        self,
    ) -> None:
        inventory = unified_runner._native_owner_inventory_report()
        self.assertTrue(inventory["ok"], inventory)
        by_check: dict[str, list[dict[str, object]]] = {}
        for row in inventory["rows"]:
            by_check.setdefault(str(row["check_id"]), []).append(row)
        self.assertEqual(
            set(by_check),
            {
                "unified_repair.model_runner",
                "unified_repair.source_audit",
                "unified_repair.synthetic_replay",
                "native_runtime_conformance",
                "exact_native_test_conformance",
                "unified_repair.parent_receipt",
            },
        )
        self.assertTrue(all(len(rows) == 1 for rows in by_check.values()))

        fingerprints = unified_runner._source_fingerprints()
        missing_paths = [
            str(row["path"])
            for value in fingerprints.values()
            for row in (
                value
                if isinstance(value, list)
                else [value]
            )
            if isinstance(row, dict) and row.get("exists") is not True
        ]
        self.assertEqual(missing_paths, [])

        tmp_root = ROOT / "tmp"
        tmp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="unified-repair-native-evidence-",
            dir=tmp_root,
        ) as temp_dir:
            manifest = self._native_manifest(
                Path(temp_dir),
                fingerprints,
            )
            current = unified_runner._native_evidence_report(
                manifest,
                fingerprints,
            )
            self.assertTrue(current["ok"], current)
            projection = unified_runner._native_execution_projection(current)
            self.assertEqual(projection["skipped_checks"], [])
            self.assertEqual(
                {
                    row["check_id"]
                    for row in projection["consumed_native_owner_receipts"]
                },
                {
                    "native_runtime_conformance",
                    "exact_native_test_conformance",
                },
            )

            tampered_hash = deepcopy(manifest)
            tampered_hash["receipts"][0]["result_sha256"] = "0" * 64
            self.assertFalse(
                unified_runner._native_evidence_report(
                    tampered_hash,
                    fingerprints,
                )["ok"]
            )

            wrong_owner = deepcopy(manifest)
            wrong_owner["receipts"][0][
                "execution_owner"
            ] = "consumer.illegal_relabel"
            wrong_owner["receipts"][0][
                "request_identity"
            ] = unified_runner.native_receipt_request_identity(
                wrong_owner["receipts"][0]
            )
            wrong_owner_report = unified_runner._native_evidence_report(
                wrong_owner,
                fingerprints,
            )
            self.assertIn(
                "native_runtime_conformance:execution_owner_mismatch",
                wrong_owner_report["failures"],
            )

            malformed_coverage = deepcopy(manifest)
            malformed_coverage["receipts"][0][
                "covered_obligation_ids"
            ] = {"unexpected": "mapping"}
            malformed_coverage["receipts"][0][
                "request_identity"
            ] = unified_runner.native_receipt_request_identity(
                malformed_coverage["receipts"][0]
            )
            malformed_report = unified_runner._native_evidence_report(
                malformed_coverage,
                fingerprints,
            )
            self.assertFalse(malformed_report["ok"])
            self.assertTrue(
                any(
                    "covered_obligation_ids_incomplete" in failure
                    for failure in malformed_report["failures"]
                )
            )

            invalid_waiver = deepcopy(manifest)
            invalid_waiver["typed_runtime_evidence"][0][
                "repair_packet_allowed"
            ] = True
            waiver_report = unified_runner._native_evidence_report(
                invalid_waiver,
                fingerprints,
            )
            self.assertIn(
                "authorized_waiver_semantics:repair_packet_allowed",
                waiver_report["failures"],
            )

    def test_contract_exhaustion_consumes_exact_parent_receipt_read_only(
        self,
    ) -> None:
        fingerprints = unified_runner._source_fingerprints()
        coverage = unified_runner._coverage_receipt_report(
            accepted_traces=(
                {
                    "case_id": "good.pm_historical_defect.repair_same_slot",
                    "input": {"origin": "pm_historical_defect"},
                },
            ),
            known_bad={
                "ok": True,
                "rejected_traces": [
                    {"case_id": "bad.pm_historical_defect.fake_blocker"}
                ],
            },
            model_contract_ok=True,
            file_inventory_ok=True,
            conformance={
                "expected_open_gap_ids": [],
                "runtime_gap_rows": [
                    {
                        "source_observation_id": (
                            "observation.unified_repair.pm_historical"
                        )
                    }
                ],
            },
            native_evidence={
                "receipts": [
                    {
                        "check_id": "native_runtime_conformance",
                        "current": True,
                        "failures": [],
                    },
                    {
                        "check_id": "exact_native_test_conformance",
                        "current": True,
                        "failures": [],
                    },
                ],
                "waiver_semantics": {
                    "ok": True,
                    "current": True,
                    "failures": [],
                },
            },
        )
        producer_result = {
            "model_id": unified_runner.model.MODEL_ID,
            "ok": True,
            "runtime_conformance_ok": True,
            "source_fingerprint": (
                unified_runner._combined_source_fingerprint(
                    unified_runner.SOURCE_FINGERPRINT_INPUTS
                )
            ),
            "source_fingerprints": fingerprints,
            "coverage_receipts": coverage,
        }

        consumed = (
            contract_exhaustion_runner
            ._unified_repair_coverage_receipt_report(producer_result)
        )
        self.assertTrue(consumed["ok"], consumed)
        self.assertEqual(
            consumed["execution_mode"],
            "read_only_receipt_consumer",
        )
        self.assertEqual(
            consumed["parent_receipt"]["receipt_id"],
            "receipt.unified_repair.integrity_parent",
        )
        self.assertEqual(
            consumed["source_result_path"],
            "simulations/flowpilot_unified_repair_integrity_results.json",
        )

        second_owner = deepcopy(producer_result)
        second_owner["coverage_receipts"][
            "parent_consumption_requirements"
        ].append(
            deepcopy(
                second_owner["coverage_receipts"][
                    "parent_consumption_requirements"
                ][0]
            )
        )
        second_owner["coverage_receipts"][
            "parent_consumption_requirements"
        ][-1]["consumer_id"] = (
            contract_exhaustion_runner.UNIFIED_REPAIR_CONSUMER_ID
        )
        duplicate = (
            contract_exhaustion_runner
            ._unified_repair_coverage_receipt_report(second_owner)
        )
        self.assertFalse(duplicate["ok"])
        self.assertIn(
            "unified_repair_consumer_requirement_not_singular",
            duplicate["failures"],
        )

    @staticmethod
    def _native_manifest(
        artifact_root: Path,
        fingerprints: dict[str, object],
    ) -> dict[str, object]:
        receipts: list[dict[str, object]] = []
        for check_id, requirement in (
            unified_runner.REQUIRED_NATIVE_RECEIPTS.items()
        ):
            artifact = artifact_root / f"{check_id}.json"
            artifact.write_text(
                json.dumps(
                    {
                        "check_id": check_id,
                        "status": "passed",
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            receipt: dict[str, object] = {
                "receipt_id": requirement["receipt_id"],
                "check_id": check_id,
                "execution_owner": requirement["execution_owner"],
                "terminal_status": "passed",
                "exit_code": 0,
                "current": True,
                "immutable": True,
                "command": f"native-owner --check {check_id}",
                "input_fingerprints": (
                    unified_runner._flatten_fingerprint_groups(
                        fingerprints,
                        requirement["required_input_groups"],
                    )
                ),
                "covered_obligation_ids": list(
                    requirement["covered_obligation_ids"]
                ),
                "result_path": artifact.relative_to(ROOT).as_posix(),
                "result_sha256": hashlib.sha256(
                    artifact.read_bytes()
                ).hexdigest(),
            }
            receipt["request_identity"] = (
                unified_runner.native_receipt_request_identity(receipt)
            )
            receipts.append(receipt)
        return {
            "schema_version": (
                unified_runner.NATIVE_EVIDENCE_MANIFEST_SCHEMA
            ),
            "model_id": unified_runner.model.MODEL_ID,
            "receipts": receipts,
            "typed_runtime_evidence": [
                {
                    "evidence_id": (
                        unified_runner.WAIVER_TYPED_EVIDENCE_ID
                    ),
                    "native_receipt_id": (
                        unified_runner.REQUIRED_NATIVE_RECEIPTS[
                            "native_runtime_conformance"
                        ]["receipt_id"]
                    ),
                    "status": "passed",
                    "model_action": "authorized_waiver",
                    "runtime_action": "waive_with_authority",
                    "authority_ref_required": True,
                    "terminal_disposition": True,
                    "repair_packet_allowed": False,
                    "covered_obligation_ids": [
                        "unified_repair.action_runtime_refinement"
                    ],
                }
            ],
        }


if __name__ == "__main__":
    unittest.main()
