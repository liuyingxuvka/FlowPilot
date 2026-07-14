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


if __name__ == "__main__":
    unittest.main()
