from __future__ import annotations

import sys
import unittest
import json
from dataclasses import replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulations"))

import flowpilot_field_mesh_model as model  # noqa: E402
import run_flowpilot_field_mesh_checks as runner  # noqa: E402


class FlowPilotFieldMeshModelTests(unittest.TestCase):
    _field_mesh_result: dict | None = None

    @classmethod
    def field_mesh_result(cls) -> dict:
        if cls._field_mesh_result is None:
            cls._field_mesh_result = runner.run_checks()
        return cls._field_mesh_result

    def test_field_mesh_has_parent_and_child_layers(self) -> None:
        self.assertGreaterEqual(len(model.FIELD_CHILD_MODELS), 8)
        self.assertIn("startup_fields", model.FIELD_CHILD_MODELS)
        self.assertIn("packet_result_fields", model.FIELD_CHILD_MODELS)
        self.assertIn("background_collaboration_fields", model.FIELD_CHILD_MODELS)
        self.assertIn("critical_transition", model.IMPORTANCE_TIERS)
        self.assertEqual(
            {
                "current",
                "mechanical_runtime_owned",
                "pm_decision_owned",
                "reviewer_quality_owned",
                "flowguard_process_owned",
                "terminal_monotonic",
                "append_only_audit",
                "single_authority_pointer",
                "pending_until_commit",
                "derived_projection",
                "retired",
                "forbidden_legacy",
            },
            set(model.FIELD_LIFECYCLE_STATES),
        )

    def test_generated_field_mesh_covers_all_observed_fields(self) -> None:
        result = self.field_mesh_result()

        self.assertTrue(result["ok"], result["mesh_state"])
        self.assertEqual(result["transition"], "accept_field_mesh")
        self.assertGreater(result["observed_field_count"], 100)
        self.assertEqual(
            result["mesh_state"]["classified_field_count"],
            result["mesh_state"]["observed_field_count"],
        )
        self.assertEqual(
            result["mesh_state"]["lifecycle_status_count"],
            len(model.FIELD_LIFECYCLE_STATES),
        )
        self.assertFalse(result["production_legacy_references"], result["production_legacy_references"][:10])
        self.assertFalse(result["prompt_legacy_references"], result["prompt_legacy_references"][:10])
        self.assertFalse(result["stale_fixed_role_gate_references"], result["stale_fixed_role_gate_references"][:10])

    def test_critical_field_contracts_are_bound_to_code(self) -> None:
        result = self.field_mesh_result()
        unbound = [binding for binding in result["critical_bindings"] if not binding["bound"]]

        self.assertFalse(unbound, unbound)

    def test_skillguard_native_bindings_have_one_current_field_lifecycle(self) -> None:
        contracts = {
            row["field"]: row
            for row in model.MAINTENANCE_AUTHORITY_FIELD_CONTRACTS
        }
        self.assertEqual(
            {
                "skillguard.contract_source.native_route_bindings[]",
                "skillguard.contract_source.native_check_bindings[]",
            },
            set(contracts),
        )
        for row in contracts.values():
            self.assertEqual(row["owner"], "flowpilot_skillguard_contract_source")
            self.assertEqual(row["writers"], ("flowpilot_contract_maintainer",))
            self.assertIn("skillguard_global_router", row["readers"])
            self.assertTrue(row["projections"])
            self.assertEqual(row["lifecycle"], "current")
            self.assertEqual(row["missing_disposition"], "global_skill_selection_blocked")
            self.assertFalse(row["default_allowed"])
            self.assertFalse(row["fallback_allowed"])

        report = self.field_mesh_result()["maintenance_authority_report"]
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["contract_count"], 2)
        self.assertEqual(report["current_contract_count"], 2)
        self.assertFalse(report["findings"])

    def test_missing_skillguard_native_binding_blocks_field_mesh_without_fallback(self) -> None:
        source = json.loads(runner.SKILLGUARD_CONTRACT_SOURCE_PATH.read_text(encoding="utf-8"))
        source["native_route_bindings"] = []
        authority = runner._maintenance_authority_report(source)
        self.assertFalse(authority["ok"])
        self.assertIn("native_route_bindings_stale_or_incomplete", authority["findings"])

        state = replace(
            model.State(
                observed_field_count=1,
                classified_field_count=1,
                child_model_count=len(model.FIELD_CHILD_MODELS),
                importance_tier_count=len(model.IMPORTANCE_TIERS),
                lifecycle_status_count=len(model.FIELD_LIFECYCLE_STATES),
                critical_contract_count=1,
                critical_contracts_bound_to_code=1,
                maintenance_authority_contract_count=(
                    model.REQUIRED_MAINTENANCE_AUTHORITY_FIELD_CONTRACT_COUNT
                ),
                maintenance_authority_contracts_current=(
                    model.REQUIRED_MAINTENANCE_AUTHORITY_FIELD_CONTRACT_COUNT
                ),
                full_inventory_written=True,
                child_partition_summary_written=True,
            ),
            maintenance_authority_contract_count=authority["contract_count"],
            maintenance_authority_contracts_current=authority["current_contract_count"],
            maintenance_authority_finding_count=len(authority["findings"]),
        )
        transition = list(model.next_safe_states(state))[0]
        self.assertEqual(transition.label, "block_stale_maintenance_authority_field_projection")
        self.assertEqual(transition.state.status, "blocked")

    def test_router_runtime_tests_do_not_synthesize_default_agent_ids(self) -> None:
        offenders: list[str] = []
        forbidden_fragments = (
            "completed_by_agent_id=f\"{envelope['to_role']}-agent\"",
            "completed_by_agent_id=f\"{role}-agent\"",
            "completed_by_agent_id=f'agent-{role}'",
            "completed_by_agent_id=f\"agent-{role}\"",
            "agent-fixed-{",
        )

        for path in (ROOT / "tests" / "router_runtime").rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for fragment in forbidden_fragments:
                if fragment in text:
                    offenders.append(f"{path.relative_to(ROOT).as_posix()}: {fragment}")

        self.assertFalse(offenders, offenders)


if __name__ == "__main__":
    unittest.main()
