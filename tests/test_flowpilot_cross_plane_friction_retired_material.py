from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import fields
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulations"))

import flowpilot_cross_plane_friction_model as model  # noqa: E402
import run_flowpilot_cross_plane_friction_checks as runner  # noqa: E402


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class FlowPilotCrossPlaneFrictionRetiredMaterialTests(unittest.TestCase):
    def test_current_model_has_no_positive_material_dispatch_state_family(self) -> None:
        state_fields = {field.name for field in fields(model.State)}

        self.assertTrue(
            {
                "current_prework_contract_observed",
                "retired_material_protocol_absent",
                "shallow_skill_inventory_preserved",
                "ordinary_resource_work_optional",
                "complete_workstream_report_contract_preserved",
            }.issubset(state_fields)
        )
        self.assertTrue(
            {
                "material_scan_packets_observed",
                "material_output_contract_role_scoped",
                "material_dispatch_write_target_explicit",
                "unsupported_material_packets_rejected",
            }.isdisjoint(state_fields)
        )

    def test_current_source_projection_preserves_agreed_contract(self) -> None:
        report = model.audit_current_prework_sources(ROOT)

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["projected_invariant_failures"], [])

    def test_current_run_rejects_every_retired_authority_shape_without_opening_bodies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_id = "run-retired-material"
            run_root = root / ".flowpilot" / "runs" / run_id
            _write_json(
                root / ".flowpilot" / "current.json",
                {
                    "run_id": run_id,
                    "run_root": f".flowpilot/runs/{run_id}",
                },
            )
            _write_json(
                run_root / "router_state.json",
                {
                    "status": "running",
                    "flags": {"material_scan_packets_relayed": True},
                    "expected_external_event": "reviewer_reports_material_sufficient",
                    "current_card_id": "pm.material_understanding",
                },
            )
            _write_json(run_root / "execution_frontier.json", {"status": "running"})
            _write_json(
                run_root / "packet_ledger.json",
                {
                    "packets": [
                        {
                            "packet_id": "material-scan-worker-001",
                            "packet_type": "material_scan",
                            "body_path": "packet_body.md",
                        }
                    ]
                },
            )

            report = model.audit_live_run(root)

        self.assertFalse(report["ok"], report)
        findings = {str(finding["code"]): finding for finding in report["findings"]}
        finding = findings["retired_material_protocol_authority_present"]
        self.assertIn("reviewer_reports_material_sufficient", finding["evidence"]["events"])
        self.assertIn("material_scan_packets_relayed", finding["evidence"]["fields"])
        self.assertIn("pm.material_understanding", finding["evidence"]["card_ids"])
        self.assertIn("material_scan", finding["evidence"]["packet_families"])
        self.assertIn("material-scan-worker-001", finding["evidence"]["packet_ids"])
        self.assertFalse(report["body_files_opened"])
        self.assertTrue(
            any(
                "retired mandatory material protocol is still active" in failure
                for failure in report["projected_invariant_failures"]
            )
        )

    def test_ordinary_optional_research_packet_is_not_a_retired_material_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_id = "run-ordinary-research"
            run_root = root / ".flowpilot" / "runs" / run_id
            _write_json(
                root / ".flowpilot" / "current.json",
                {
                    "run_id": run_id,
                    "run_root": f".flowpilot/runs/{run_id}",
                },
            )
            _write_json(
                run_root / "router_state.json",
                {
                    "status": "running",
                    "flags": {"research_package_written_by_pm": True},
                    "expected_external_event": "worker_research_report_returned",
                    "current_card_id": "pm.research_package",
                },
            )
            _write_json(run_root / "execution_frontier.json", {"status": "running"})
            _write_json(
                run_root / "packet_ledger.json",
                {
                    "packets": [
                        {
                            "packet_id": "research-worker-001",
                            "packet_type": "role_work",
                        }
                    ]
                },
            )

            report = model.audit_live_run(root)

        codes = {str(finding["code"]) for finding in report["findings"]}
        self.assertNotIn("retired_material_protocol_authority_present", codes)

    def test_runner_known_bad_space_covers_each_contracted_prework_risk(self) -> None:
        expected = {
            "retired_material_protocol_reintroduced",
            "mandatory_shallow_skill_inventory_removed",
            "ordinary_resource_work_forced_as_gate",
            "complete_workstream_report_contract_dropped",
        }

        self.assertTrue(expected.issubset(runner.HAZARD_EXPECTED_FAILURES))
        self.assertTrue(expected.issubset(model.hazard_states()))
        for hazard_id in expected:
            with self.subTest(hazard_id=hazard_id):
                failures = model.invariant_failures(model.hazard_states()[hazard_id])
                self.assertTrue(failures)


if __name__ == "__main__":
    unittest.main()
