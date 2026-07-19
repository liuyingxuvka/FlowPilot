from __future__ import annotations

import copy
import importlib
import json
import tempfile
import unittest
from pathlib import Path


runner = importlib.import_module("simulations.run_flowpilot_model_mesh_checks")


class FlowPilotModelMeshCoverageReceiptTests(unittest.TestCase):
    def evidence_fixture(self, root: Path) -> tuple[dict[str, object], dict[str, Path]]:
        source_paths = (
            runner.UNIFIED_REPAIR_MODEL_PATH,
            runner.UNIFIED_REPAIR_RUNNER_PATH,
            *runner.UNIFIED_REPAIR_RUNTIME_SOURCE_PATHS,
            runner.UNIFIED_REPAIR_NATIVE_RUNTIME_OWNER_PATH,
            runner.UNIFIED_REPAIR_NATIVE_RUNTIME_FIXTURE_PATH,
            runner.UNIFIED_REPAIR_EXACT_NATIVE_TEST_OWNER_PATH,
            *runner.UNIFIED_REPAIR_EXACT_TEST_PATHS,
        )
        for relative_path in source_paths:
            source_path = root / relative_path
            source_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.write_bytes(f"fixture:{relative_path.as_posix()}".encode("utf-8"))
        unified_source = runner._unified_repair_source_contract(root)

        paths: dict[str, Path] = {}
        for _receipt_id, model_id, _relative_path, ok_field in runner.CONTRACT_COVERAGE_RESULT_SPECS:
            path = root / f"{model_id}.json"
            payload: dict[str, object] = {ok_field: True}
            if model_id == "flowpilot_ai_response_execution_closure":
                payload["execution_closure"] = {
                    "static_mechanical_universe": {"case_ids": ["static:one"]},
                    "receipts": [
                        {"case_id": "execution:one", "execution_status": "passed"},
                        {"case_id": "execution:not-run", "execution_status": "not_run"},
                    ],
                }
            if model_id == "flowpilot_complete_workstream_fake_ai_execution":
                payload["profile_receipts"] = [
                    {"profile_id": "complete", "execution_status": "passed"},
                    {"profile_id": "not-run", "execution_status": "not_run"},
                ]
            if model_id == runner.UNIFIED_REPAIR_MODEL_ID:
                fingerprint = unified_source["source_fingerprint"]
                payload = {
                    "model_id": runner.UNIFIED_REPAIR_MODEL_ID,
                    "model_ok": True,
                    "runtime_conformance_ok": True,
                    "ok": True,
                    "decision": "runtime_conformance_current",
                    "source_fingerprint": fingerprint,
                    "source_fingerprint_algorithm": runner.UNIFIED_REPAIR_SOURCE_FINGERPRINT_ALGORITHM,
                    "source_fingerprints": unified_source["source_fingerprints"],
                    "accepted_traces": [{"case_id": "good", "accepted": True}],
                    "failed_good_cases": [],
                    "known_bad": {
                        "ok": True,
                        "expected_count": 14,
                        "detected_count": 14,
                        "missing": [],
                        "rejected_traces": [
                            {"case_id": "bad", "rejected": True}
                        ],
                    },
                    "conformance": {
                        "required": True,
                        "ok": True,
                        "skipped": False,
                        "source_fingerprint": fingerprint,
                        "model_contract_ok": True,
                        "runtime_evidence_ids": ["runtime.native.current"],
                        "test_evidence_ids": ["tests.native.current"],
                        "missing": [],
                        "runtime_gap_rows": [],
                        "expected_open_gap_ids": [],
                        "unexpected_gap_ids": [],
                    },
                    "skipped_checks": [],
                }
            path.write_text(json.dumps(payload), encoding="utf-8")
            paths[model_id] = path
        proof = {
            "artifact_id": "proof.current",
            "producer_route": "flowguard-test-mesh",
            "command": "python scripts/run_test_tier.py --tier all --background",
            "result_path": "tmp/test-background/current",
            "result_status": "passed",
            "exit_code": 0,
            "artifact_fingerprints": {"current.meta.json": "a" * 64, "current.exit.txt": "b" * 64},
            "covered_obligation_ids": ["current-tests"],
            "assertion_scope": "external_contract",
            "current": True,
            "route_evidence_current": True,
            "progress_only": False,
            "metadata": {"selected_child_command_count": 12, "executed_child_command_count": 12},
        }
        manifest: dict[str, object] = {
            "source_fingerprint": runner.source_fingerprint(),
            "routine": {"suite": {"result_status": "passed", "selected_count": 12, "test_count": 12, "proof_artifact": proof}},
            "release": {"result_status": "passed", "selected_count": 12, "test_count": 12, "proof_artifact": dict(proof, artifact_id="proof.release")},
        }
        return manifest, paths

    @staticmethod
    def child_receipt(report: dict[str, object], model_id: str) -> dict[str, object]:
        return next(
            row
            for row in report["child_receipts"]  # type: ignore[index]
            if row["model_id"] == model_id
        )

    def test_build_report_without_manifest_still_consumes_current_unified_red_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _manifest, paths = self.evidence_fixture(root)
            result_path = root / runner.UNIFIED_REPAIR_RESULT_PATH
            result_path.parent.mkdir(parents=True, exist_ok=True)
            payload = json.loads(
                paths[runner.UNIFIED_REPAIR_MODEL_ID].read_text(encoding="utf-8")
            )
            payload["ok"] = False
            payload["runtime_conformance_ok"] = False
            payload["decision"] = "runtime_conformance_blocked"
            payload["conformance"]["ok"] = False
            payload["conformance"]["missing"] = ["native_runtime_conformance"]
            result_path.write_text(json.dumps(payload), encoding="utf-8")
            report = runner.build_report(
                project_root=root,
                run_id=None,
                include_live_audit=False,
                evidence_manifest=None,
            )

        self.assertIsNone(report["contract_coverage_receipts"])
        self.assertFalse(report["unified_repair_integrity_gate"]["ok"])
        self.assertFalse(report["ok"])
        self.assertIn(
            "unified_conformance_not_green",
            report["unified_repair_integrity_gate"]["blockers"],
        )

    def test_build_report_without_manifest_can_green_with_exact_conformant_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _manifest, paths = self.evidence_fixture(root)
            result_path = root / runner.UNIFIED_REPAIR_RESULT_PATH
            result_path.parent.mkdir(parents=True, exist_ok=True)
            result_path.write_text(
                paths[runner.UNIFIED_REPAIR_MODEL_ID].read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            report = runner.build_report(
                project_root=root,
                run_id=None,
                include_live_audit=False,
                evidence_manifest=None,
            )

        self.assertIsNone(report["contract_coverage_receipts"])
        self.assertTrue(report["unified_repair_integrity_gate"]["ok"], report)
        self.assertEqual(
            report["unified_repair_integrity_gate"]["evidence_tier"],
            "conformance_green",
        )
        self.assertTrue(report["ok"], report)

    def test_parent_consumes_every_current_child_receipt_and_composite_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest, paths = self.evidence_fixture(Path(tmp))
            report = runner._contract_coverage_receipt_report(
                project_root=Path(tmp),
                evidence_manifest=manifest,
                result_path_overrides=paths,
            )

        self.assertTrue(report["ok"], report)
        parent = report["parent_receipt"]
        self.assertEqual(
            set(parent["required_child_receipt_ids"]),
            set(parent["consumed_child_receipt_ids"]),
        )
        self.assertEqual(
            report["development_process_flow"]["exact_evidence_ids"],
            list(runner.DPF_EXACT_EVIDENCE_IDS),
        )
        self.assertEqual(report["missing_child_receipt_ids"], [])
        self.assertIn("static:one", parent["covered_case_ids"])
        self.assertIn("execution:one", parent["covered_case_ids"])
        self.assertNotIn("execution:not-run", parent["covered_case_ids"])
        self.assertIn("profile:complete", parent["covered_case_ids"])
        self.assertNotIn("profile:not-run", parent["covered_case_ids"])
        self.assertIn(
            "case:flowpilot_skillguard_current_contract",
            parent["covered_case_ids"],
        )
        self.assertEqual(
            set(report["composite_handoff_acceptance"]["route_ids"]),
            {
                "flowguard-contract-exhaustion-mesh",
                "flowguard-model-test-alignment",
                "flowguard-test-mesh",
                "flowguard-model-mesh",
            },
        )

    def test_missing_or_failed_child_result_blocks_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, paths = self.evidence_fixture(root)
            missing = paths["flowpilot_contract_exhaustion_mesh"]
            missing.unlink()
            report = runner._contract_coverage_receipt_report(
                project_root=root,
                evidence_manifest=manifest,
                result_path_overrides=paths,
            )

        self.assertFalse(report["ok"])
        self.assertIn("receipt.contract_exhaustion_mesh", report["missing_child_receipt_ids"])

    def test_stale_source_fingerprint_blocks_every_child_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, paths = self.evidence_fixture(root)
            manifest["source_fingerprint"] = "stale-source"
            report = runner._contract_coverage_receipt_report(
                project_root=root,
                evidence_manifest=manifest,
                result_path_overrides=paths,
            )

        self.assertFalse(report["ok"])
        self.assertFalse(report["source_fingerprint_current"])
        self.assertTrue(report["missing_child_receipt_ids"])

    def test_progress_only_or_failed_proof_manifest_blocks_parent(self) -> None:
        for mutation in (
            {"progress_only": True},
            {"result_status": "failed"},
            {"current": False},
        ):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                manifest, paths = self.evidence_fixture(root)
                broken = copy.deepcopy(manifest)
                broken["release"]["proof_artifact"].update(mutation)  # type: ignore[index]
                report = runner._contract_coverage_receipt_report(
                    project_root=root,
                    evidence_manifest=broken,
                    result_path_overrides=paths,
                )

            self.assertFalse(report["ok"])
            self.assertFalse(report["proof_gate_ok"])
            self.assertTrue(report["nonpassing_proofs"])

    def test_reused_proof_without_ticket_blocks_done_release_and_publish(self) -> None:
        for scope in ("done", "release", "publish"):
            with self.subTest(scope=scope), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                manifest, paths = self.evidence_fixture(root)
                manifest["release"]["result_reused"] = True  # type: ignore[index]
                report = runner._contract_coverage_receipt_report(
                    project_root=root,
                    evidence_manifest=manifest,
                    result_path_overrides=paths,
                    claim_scope=scope,
                )
            self.assertFalse(report["ok"])
            self.assertIn("release:missing_test_reuse_ticket", report["nonpassing_proofs"])

    def test_unified_child_rejects_stale_exact_source_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, paths = self.evidence_fixture(root)
            path = paths[runner.UNIFIED_REPAIR_MODEL_ID]
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["source_fingerprint"] = "stale"
            path.write_text(json.dumps(payload), encoding="utf-8")
            report = runner._contract_coverage_receipt_report(
                project_root=root,
                evidence_manifest=manifest,
                result_path_overrides=paths,
            )

        receipt = self.child_receipt(report, runner.UNIFIED_REPAIR_MODEL_ID)
        self.assertFalse(receipt["current"])
        self.assertIn("unified_source_fingerprint_mismatch", receipt["finding_codes"])

    def test_unified_child_rejects_open_or_skipped_required_conformance(self) -> None:
        mutations = (
            (
                lambda payload: (
                    payload.update({"ok": False, "runtime_conformance_ok": False}),
                    payload["conformance"].update({"ok": False}),
                ),
                "unified_conformance_not_green",
            ),
            (
                lambda payload: payload.update(
                    {
                        "skipped_checks": [
                            {
                                "check_id": "native_runtime_conformance",
                                "status": "not_run",
                            }
                        ]
                    }
                ),
                "unified_required_conformance_skipped",
            ),
        )
        for mutate, expected_finding in mutations:
            with self.subTest(expected_finding=expected_finding), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                manifest, paths = self.evidence_fixture(root)
                path = paths[runner.UNIFIED_REPAIR_MODEL_ID]
                payload = json.loads(path.read_text(encoding="utf-8"))
                mutate(payload)
                path.write_text(json.dumps(payload), encoding="utf-8")
                report = runner._contract_coverage_receipt_report(
                    project_root=root,
                    evidence_manifest=manifest,
                    result_path_overrides=paths,
                )

            receipt = self.child_receipt(report, runner.UNIFIED_REPAIR_MODEL_ID)
            self.assertFalse(receipt["current"])
            self.assertIn(expected_finding, receipt["finding_codes"])

    def test_unified_child_requires_both_native_evidence_domains(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, paths = self.evidence_fixture(root)
            path = paths[runner.UNIFIED_REPAIR_MODEL_ID]
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["conformance"]["runtime_evidence_ids"] = []
            payload["conformance"]["test_evidence_ids"] = []
            path.write_text(json.dumps(payload), encoding="utf-8")
            report = runner._contract_coverage_receipt_report(
                project_root=root,
                evidence_manifest=manifest,
                result_path_overrides=paths,
            )

        receipt = self.child_receipt(report, runner.UNIFIED_REPAIR_MODEL_ID)
        self.assertFalse(receipt["current"])
        self.assertIn("unified_runtime_evidence_missing", receipt["finding_codes"])
        self.assertIn("unified_test_evidence_missing", receipt["finding_codes"])

    def test_aggregate_proof_cannot_substitute_for_unified_native_conformance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, paths = self.evidence_fixture(root)
            path = paths[runner.UNIFIED_REPAIR_MODEL_ID]
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload.pop("conformance")
            path.write_text(json.dumps(payload), encoding="utf-8")
            report = runner._contract_coverage_receipt_report(
                project_root=root,
                evidence_manifest=manifest,
                result_path_overrides=paths,
            )

        receipt = self.child_receipt(report, runner.UNIFIED_REPAIR_MODEL_ID)
        contract = receipt["metadata"]["unified_repair_contract"]
        self.assertTrue(report["proof_gate_ok"])
        self.assertFalse(receipt["current"])
        self.assertIsNone(receipt["metadata"]["proof_artifact"])
        self.assertFalse(contract["native_owner_receipt_synthesized"])
        self.assertFalse(contract["aggregate_proof_substitution_allowed"])


if __name__ == "__main__":
    unittest.main()
