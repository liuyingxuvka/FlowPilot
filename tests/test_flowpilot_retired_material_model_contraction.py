from __future__ import annotations

from dataclasses import fields, replace
from pathlib import Path
from types import SimpleNamespace
import unittest

from simulations import flowpilot_control_plane_state_consistency_model as consistency
from simulations import flowpilot_protocol_contract_conformance_model as conformance
from simulations import flowpilot_singleton_identity_model as singleton


ROOT = Path(__file__).resolve().parents[1]


class FlowPilotRetiredMaterialModelContractionTests(unittest.TestCase):
    def test_protocol_conformance_uses_current_workstream_authority_only(self) -> None:
        state_fields = {field.name for field in fields(conformance.State)}
        self.assertTrue(
            {
                "retired_material_authority_absent",
                "mandatory_shallow_skill_inventory_contract_present",
                "complete_workstream_report_contract_present",
            }.issubset(state_fields)
        )
        self.assertTrue(
            {
                "material_scan_card_requires_file_backed_packet_bodies",
                "material_scan_router_accepts_file_backed_packet_specs",
                "material_dispatch_block_event_registered",
                "material_dispatch_frontier_phase_synchronized",
            }.isdisjoint(state_fields)
        )
        self.assertFalse(
            any("material_scan|worker.material_scan" in row for row in conformance.PROCESS_CONTRACT_BINDING_REQUIRED)
        )
        self.assertTrue(any(row.startswith("research|") for row in conformance.PROCESS_CONTRACT_BINDING_REQUIRED))
        self.assertTrue(any(row.startswith("current_node_work|") for row in conformance.PROCESS_CONTRACT_BINDING_REQUIRED))
        self.assertTrue(any(row.startswith("pm_role_work_request|") for row in conformance.PROCESS_CONTRACT_BINDING_REQUIRED))

        source_state = conformance.collect_source_state(ROOT)
        self.assertEqual(conformance.protocol_failures(source_state), [])
        self.assertTrue(source_state.retired_material_authority_absent)
        self.assertTrue(source_state.mandatory_shallow_skill_inventory_contract_present)
        self.assertTrue(source_state.complete_workstream_report_contract_present)

        retired_export = SimpleNamespace(
            EXTERNAL_EVENTS={},
            SYSTEM_CARD_SEQUENCE=(),
            RUNTIME_FLAG_DEFAULTS={},
            PROCESS_CONTRACT_BINDINGS={},
            _material_scan_index_path=lambda: None,
        )
        self.assertFalse(
            conformance._retired_material_authority_absent(  # noqa: SLF001 - negative source probe
                retired_export,
                "",
            )
        )

    def test_control_plane_consistency_has_generic_review_and_packet_projections(self) -> None:
        state_fields = {field.name for field in fields(consistency.State)}
        self.assertTrue(
            {
                "packet_results_joined",
                "review_block_projection_synced",
                "review_block_pm_repair_branch_exposed",
                "retired_material_projection_absent",
            }.issubset(state_fields)
        )
        self.assertTrue(
            {
                "material_results_joined",
                "material_review_projection_synced",
                "material_insufficient_pm_repair_branch_exposed",
            }.isdisjoint(state_fields)
        )
        retired = consistency.scenario_state(
            consistency.RETIRED_MATERIAL_PROJECTION_REINTRODUCED
        )
        self.assertTrue(
            any(
                "retired material_scan/material_sufficiency/material_understanding projection is active"
                in failure
                for failure in consistency.consistency_failures(retired)
            )
        )

    def test_singleton_identity_replaces_material_generation_with_ordinary_batches(self) -> None:
        rows = {row.object_family: row for row in singleton.authority_matrix()}
        self.assertNotIn("material_progress_generation", rows)
        self.assertIn("ordinary_packet_batch_generation", rows)
        ordinary = rows["ordinary_packet_batch_generation"]
        self.assertIn("research/current_node/pm_role_work", ordinary.singleton_scope)
        self.assertNotIn(
            "router_state.json",
            {
                row["relative_path"]
                for row in singleton.live_singleton_required_evidence_files()
            },
        )
        retired = singleton._selected_state(  # noqa: SLF001 - model known-bad probe
            singleton.RETIRED_MATERIAL_SINGLETON_AUTHORITY_PRESENT
        )
        retired = replace(retired, status="safe")
        self.assertTrue(
            any("retired material_scan" in failure for failure in singleton.invariant_failures(retired))
        )


if __name__ == "__main__":
    unittest.main()
