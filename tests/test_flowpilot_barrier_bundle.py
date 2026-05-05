from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))

import barrier_bundle  # noqa: E402
import packet_runtime  # noqa: E402


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class FlowPilotBarrierBundleTests(unittest.TestCase):
    def make_project(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="flowpilot-barrier-"))
        _write_json(
            root / ".flowpilot" / "current.json",
            {
                "current_run_id": "run-test",
                "current_run_root": ".flowpilot/runs/run-test",
            },
        )
        return root

    def startup_bundle(self) -> dict:
        return {
            "schema_version": barrier_bundle.BARRIER_BUNDLE_SCHEMA,
            "bundle_id": "startup-run-test",
            "barrier_id": "startup",
            "equivalence_mode": barrier_bundle.BARRIER_BUNDLE_EQUIVALENCE_MODE,
            "member_packet_ids": ["packet-001"],
            "obligations": [
                {"id": item, "status": "passed"}
                for item in barrier_bundle.required_obligation_ids("startup")
            ],
            "role_slices": [
                {"role": "controller", "expected_role": "controller", "status": "passed"},
                {"role": "project_manager", "expected_role": "project_manager", "status": "passed"},
                {"role": "human_like_reviewer", "expected_role": "human_like_reviewer", "status": "passed"},
            ],
            "controller_boundary": {
                "controller_read_sealed_body": False,
                "controller_originated_evidence": False,
                "controller_summarized_body": False,
                "ai_discretion_used": False,
            },
        }

    def test_complete_bundle_passes_without_reading_packet_body(self) -> None:
        bundle = self.startup_bundle()
        report = barrier_bundle.validate_barrier_bundle(bundle)

        self.assertTrue(report["ok"])
        self.assertEqual(report["missing_obligations"], [])
        self.assertEqual(report["missing_role_slices"], [])

    def test_missing_obligation_blocks_bundle(self) -> None:
        bundle = self.startup_bundle()
        bundle["obligations"] = bundle["obligations"][:-1]

        report = barrier_bundle.validate_barrier_bundle(bundle)

        self.assertFalse(report["ok"])
        self.assertIn("missing_required_obligations", report["failures"])

    def test_ai_discretion_and_controller_body_access_block_bundle(self) -> None:
        bundle = self.startup_bundle()
        bundle["controller_boundary"]["controller_read_sealed_body"] = True
        bundle["controller_boundary"]["ai_discretion_used"] = True

        report = barrier_bundle.validate_barrier_bundle(bundle)

        self.assertFalse(report["ok"])
        self.assertIn("controller_read_sealed_body", report["failures"])
        self.assertIn("ai_discretion_used", report["failures"])

    def test_wrong_role_and_bad_cache_reuse_block_bundle(self) -> None:
        bundle = self.startup_bundle()
        bundle["role_slices"][1]["role"] = "controller"
        bundle["role_slices"][1]["expected_role"] = "project_manager"
        bundle["cache_reuse"] = {
            "claimed": True,
            "input_hash_same": False,
            "source_hash_same": True,
            "evidence_hash_valid": False,
        }

        report = barrier_bundle.validate_barrier_bundle(bundle)

        self.assertFalse(report["ok"])
        self.assertIn("wrong_role_approval_used", report["failures"])
        self.assertIn("cache_reuse_input_hash_changed", report["failures"])
        self.assertIn("cache_reuse_evidence_hash_invalid", report["failures"])

    def test_route_mutation_requires_stale_mark_and_frontier_rewrite(self) -> None:
        bundle = self.startup_bundle()
        bundle["route_mutation_recorded"] = True
        bundle["stale_evidence_marked"] = False
        bundle["frontier_rewritten_after_mutation"] = False

        report = barrier_bundle.validate_barrier_bundle(bundle)

        self.assertFalse(report["ok"])
        self.assertIn("route_mutation_without_stale_evidence_mark", report["failures"])
        self.assertIn("route_mutation_without_frontier_rewrite", report["failures"])

    def test_packet_ledger_records_bundle_as_metadata_only(self) -> None:
        root = self.make_project()
        bundle = self.startup_bundle()

        envelope = packet_runtime.create_packet(
            root,
            packet_id="packet-001",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="SECRET_BODY must remain target-role-only",
            barrier_bundle=bundle,
        )

        ledger = json.loads((root / ".flowpilot" / "runs" / "run-test" / "packet_ledger.json").read_text(encoding="utf-8"))
        body = (root / envelope["body_path"]).read_text(encoding="utf-8")
        self.assertIn("barrier_bundles", ledger)
        self.assertEqual(ledger["barrier_bundles"][0]["bundle_id"], "startup-run-test")
        self.assertTrue(ledger["barrier_bundles"][0]["validation_report"]["ok"])
        self.assertNotIn("barrier_bundle", body)
        self.assertIn("SECRET_BODY", body)

    def test_packet_ledger_audit_blocks_incomplete_bundle(self) -> None:
        root = self.make_project()
        bundle = self.startup_bundle()
        bundle["obligations"] = bundle["obligations"][:-1]
        packet_runtime.create_packet(
            root,
            packet_id="packet-001",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="packet body",
            barrier_bundle=bundle,
        )

        audit = packet_runtime.audit_barrier_bundles(root)

        self.assertFalse(audit["passed"])
        self.assertEqual(audit["blockers"][0]["code"], "barrier_bundle_invalid")


if __name__ == "__main__":
    unittest.main()
