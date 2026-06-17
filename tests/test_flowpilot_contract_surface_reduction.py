from __future__ import annotations

import importlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
CORE_RUNTIME = ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_core_runtime"
if str(ASSETS) not in sys.path:
    sys.path.insert(0, str(ASSETS))
if str(CORE_RUNTIME) not in sys.path:
    sys.path.insert(0, str(CORE_RUNTIME))

runtime = importlib.import_module("flowpilot_core_runtime.runtime")
packet_result_contracts = importlib.import_module("packet_result_contracts")
packet_stage_evidence_matrix = importlib.import_module("packet_stage_evidence_matrix")


def packet_for_family(family_id: str) -> dict[str, object]:
    row = packet_result_contracts.contract_for_family(family_id)
    if row is None:
        raise AssertionError(f"missing contract row for {family_id}")
    route_scope = str(row["route_scope"])
    if route_scope == "<subject_route_scope>":
        route_scope = "node"
    return {
        "packet_id": f"packet-{family_id.replace('.', '-').replace('_', '-')}",
        "body": "{}",
        "envelope": {
            "packet_kind": str(row["packet_kind"]),
            "route_scope": route_scope,
            "responsibility": "pm",
            "route_node_id": "parent-node" if family_id == "task.parent_backward_replay" else "node-001",
        },
    }


class FlowPilotContractSurfaceReductionTests(unittest.TestCase):
    def test_every_packet_result_family_has_current_matrix_row(self) -> None:
        contract_families = {
            str(row["family_id"]) for row in packet_result_contracts.PACKET_RESULT_CONTRACTS
        }
        matrix_families = set(packet_stage_evidence_matrix.PACKET_FAMILY_IDS)

        self.assertEqual(contract_families, matrix_families)

        required_matrix_keys = {
            "family_id",
            "lifecycle_stage",
            "required_evidence_owner",
            "current_required_fields",
            "moved_fields",
            "deleted_fields",
            "allowed_value_options",
            "allowed_blocker_classes",
            "blocker_next_actions",
            "blocker_repair_packet_contracts",
            "repeat_repair_required_fields",
            "repair_node_required_context_fields",
            "parent_replacement_required_context_fields",
        }
        for family_id in sorted(matrix_families):
            with self.subTest(family_id=family_id):
                row = packet_stage_evidence_matrix.stage_evidence_row_for_family(family_id)
                self.assertTrue(required_matrix_keys.issubset(row))
                self.assertTrue(
                    set(packet_result_contracts.required_fields_for_family(family_id)).issubset(
                        set(row["current_required_fields"])
                    )
                )
                self.assertTrue(row["allowed_blocker_classes"])
                self.assertTrue(row["allowed_value_options"])

        with self.assertRaises(KeyError):
            packet_stage_evidence_matrix.stage_evidence_row_for_family("legacy.unknown_family")

    def test_role_visible_stage_matrix_omits_lifecycle_history(self) -> None:
        for family_id in packet_stage_evidence_matrix.PACKET_FAMILY_IDS:
            with self.subTest(family_id=family_id):
                internal_row = packet_stage_evidence_matrix.stage_evidence_row_json(family_id)
                role_row = packet_stage_evidence_matrix.role_visible_stage_evidence_row_json(family_id)

                self.assertIn("moved_fields", internal_row)
                self.assertIn("deleted_fields", internal_row)
                self.assertNotIn("moved_fields", role_row)
                self.assertNotIn("deleted_fields", role_row)
                self.assertEqual(internal_row["current_required_fields"], role_row["current_required_fields"])
                self.assertEqual(internal_row["allowed_blocker_classes"], role_row["allowed_blocker_classes"])

    def test_deleted_and_moved_fields_are_not_success_requirements(self) -> None:
        checks = {
            "task.high_standard_contract": {
                "required": ("requirements[].closure_rule", "acceptance_item_registry.items[].future_evidence_rule"),
                "deleted": ("requirements[].closure_blocking", "acceptance_item_registry.items[].final_replay_required"),
            },
            "task.discovery": {
                "required": ("candidate_skill_inventory",),
                "deleted": ("local_skill_inventory", "candidate_only_skill_policy"),
            },
            "task.skill_standard": {
                "required": ("obligations[].evidence_rule",),
                "deleted": ("obligations[].evidence_required", "obligations[].closure_blocking"),
            },
            "task.node_acceptance_plan": {
                "required": ("decision",),
                "deleted": ("work_packet_projection", "test_obligation_matrix.pre_worker[]"),
            },
            "flowguard_check.post_result": {
                "required": ("modeled_boundary", "blockers", "contract_self_check"),
                "deleted": ("evidence_consistency", "model_obligations", "ordinary_test_evidence"),
            },
            "review.any_current_subject": {
                "required": ("findings", "blockers", "contract_self_check"),
                "deleted": ("direct_evidence_paths_checked", "independent_challenge"),
            },
            "review.terminal_backward_replay": {
                "required": ("route_segment_replay", "final_blockers"),
                "deleted": ("segment_reviews", "final_artifact_hygiene_review"),
            },
            "pm_disposition.node_pm_disposition": {
                "required": ("acceptance_item_disposition",),
                "deleted": ("accepted_acceptance_item_ids", "reviewer_absorption", "flowguard_absorption"),
            },
        }

        for family_id, expectation in checks.items():
            with self.subTest(family_id=family_id):
                required_fields = set(packet_result_contracts.required_fields_for_family(family_id))
                required_child_fields = set(packet_result_contracts.required_child_fields_for_family(family_id))
                success_fields = required_fields | required_child_fields
                forbidden_fields = set(packet_result_contracts.forbidden_fields_for_family(family_id))
                deleted_fields = set(packet_stage_evidence_matrix.deleted_fields_for_family(family_id))

                for field in expectation["required"]:
                    self.assertIn(field, success_fields)
                for field in expectation["deleted"]:
                    self.assertNotIn(field, success_fields)
                    self.assertTrue(
                        field in forbidden_fields or field in deleted_fields,
                        f"{family_id} must explicitly reject deleted field {field}",
                    )

    def test_every_blocker_class_has_one_next_action_and_repair_packet_contract(self) -> None:
        all_allowed: set[str] = set()
        for family_id in packet_stage_evidence_matrix.PACKET_FAMILY_IDS:
            row = packet_stage_evidence_matrix.stage_evidence_row_for_family(family_id)
            allowed = set(row["allowed_blocker_classes"])
            all_allowed.update(allowed)
            self.assertEqual(set(row["blocker_next_actions"]), allowed)
            self.assertEqual(set(row["blocker_repair_packet_contracts"]), allowed)
            for blocker_class in allowed:
                self.assertEqual(
                    row["blocker_next_actions"][blocker_class],
                    packet_stage_evidence_matrix.next_action_for_blocker_class(blocker_class),
                )

        self.assertEqual(all_allowed, set(packet_stage_evidence_matrix.BLOCKER_CLASS_TO_NEXT_ACTION))
        self.assertEqual(all_allowed, set(packet_stage_evidence_matrix.BLOCKER_REPAIR_PACKET_CONTRACTS))

        for blocker_class in sorted(all_allowed):
            with self.subTest(blocker_class=blocker_class):
                contract = packet_stage_evidence_matrix.blocker_repair_packet_contract(blocker_class)
                for field in (
                    "repair_packet_family",
                    "owner_role",
                    "required_context_fields",
                    "required_payload_fields",
                    "return_gate",
                    "repeat_repair_must_carry_lineage",
                ):
                    self.assertIn(field, contract)
                self.assertTrue(contract["required_context_fields"])
                self.assertTrue(contract["required_payload_fields"])
                self.assertTrue(contract["repeat_repair_must_carry_lineage"])

        with self.assertRaises(KeyError):
            packet_stage_evidence_matrix.next_action_for_blocker_class("legacy_freeform_blocker")
        with self.assertRaises(KeyError):
            packet_stage_evidence_matrix.blocker_repair_packet_contract("legacy_freeform_blocker")

    def test_needs_user_authority_ref_is_branch_conditional_not_global(self) -> None:
        contract = packet_stage_evidence_matrix.blocker_repair_packet_contract("needs_user")

        self.assertEqual(
            packet_stage_evidence_matrix.next_action_for_blocker_class("needs_user"),
            "stop_for_user_or_waive_with_authority",
        )
        self.assertNotIn("authority_ref", contract["required_payload_fields"])
        self.assertEqual(
            contract["conditional_required_fields"],
            {"waive_with_authority": ("authority_ref",)},
        )
        self.assertEqual(
            contract["return_gate"],
            "terminal_user_stop_or_authority_waiver_gate",
        )

    def test_pm_owned_blockers_do_not_preselect_pm_repair_route(self) -> None:
        pm_owned_blockers = (
            "local_artifact",
            "evidence_gap",
            "flowguard_failure",
            "route_decomposition",
            "composition",
            "system_validation_failure",
            "terminal_closure",
        )
        forbidden_preselected_routes = {
            "repair_current_scope",
            "repair_parent_scope",
            "redesign_route",
            "terminal_supplemental_repair_or_redesign_route",
        }

        for blocker_class in pm_owned_blockers:
            with self.subTest(blocker_class=blocker_class):
                contract = packet_stage_evidence_matrix.blocker_repair_packet_contract(blocker_class)

                self.assertEqual(
                    packet_stage_evidence_matrix.next_action_for_blocker_class(blocker_class),
                    "pm_repair_decision",
                )
                self.assertEqual(contract["repair_packet_family"], "pm_repair_decision.pm_repair_decision")
                self.assertEqual(contract["required_payload_fields"], packet_stage_evidence_matrix.PM_REPAIR_PAYLOAD_FIELDS)
                self.assertEqual(contract["return_gate"], "pm_selected_repair_gate")
                self.assertNotIn(
                    packet_stage_evidence_matrix.next_action_for_blocker_class(blocker_class),
                    forbidden_preselected_routes,
                )

    def test_repeated_repair_and_parent_repair_contracts_carry_prior_materials(self) -> None:
        self.assertEqual(
            set(packet_stage_evidence_matrix.repair_lineage_required_fields()),
            {
                "original_blocker_id",
                "prior_repair_packet_id",
                "prior_repair_result_id",
                "prior_repair_evidence_refs",
                "failed_recheck_report_id",
                "prior_failure_reason",
                "current_blocking_report_id",
                "new_repair_delta",
                "return_gate",
            },
        )
        self.assertIn(
            "repair_parent_scope_contract.inherit_existing_children",
            packet_stage_evidence_matrix.parent_replacement_context_required_fields(),
        )
        self.assertIn(
            "repair_parent_scope_contract.repair_child_specs[]",
            packet_stage_evidence_matrix.parent_replacement_context_required_fields(),
        )

        for blocker_class in ("local_artifact", "evidence_gap", "system_validation_failure"):
            contract = packet_stage_evidence_matrix.blocker_repair_packet_contract(blocker_class)
            self.assertIn("leaf_repair_route_shape", contract)
            self.assertIn("parent_repair_route_shape", contract)
            self.assertIn("parent_repair_required_context_fields", contract)
        composition = packet_stage_evidence_matrix.blocker_repair_packet_contract("composition")
        self.assertIn("parent_repair_route_shape", composition)
        self.assertIn("parent_repair_required_context_fields", composition)

    def test_allowed_value_options_match_current_contract_fields(self) -> None:
        for family_id in packet_stage_evidence_matrix.PACKET_FAMILY_IDS:
            with self.subTest(family_id=family_id):
                options = packet_stage_evidence_matrix.allowed_value_options_for_family(family_id)
                self.assertTrue(options)
                for field_path, allowed_values in options.items():
                    self.assertTrue(allowed_values, field_path)
                    self.assertNotIn("legacy", field_path)
                    self.assertNotIn("fallback", field_path)

        pm_disposition_options = packet_stage_evidence_matrix.allowed_value_options_for_family(
            "pm_disposition.node_pm_disposition"
        )
        self.assertIn("acceptance_item_disposition[].disposition", pm_disposition_options)
        self.assertNotIn("acceptance_item_disposition[].status_for_this_node", pm_disposition_options)
        reviewer_options = packet_stage_evidence_matrix.allowed_value_options_for_family("review.any_current_subject")
        self.assertEqual(reviewer_options["reviewed_by_role"], ("human_like_reviewer",))

    def test_runtime_rejects_values_outside_allowed_value_options(self) -> None:
        invalid_payloads = {
            "task.high_standard_contract": (
                ("requirements[].classification",),
                {
                    **packet_result_contracts.minimal_valid_shape_for_family("task.high_standard_contract"),
                    "requirements": [
                        {
                            **packet_result_contracts.minimal_valid_shape_for_family(
                                "task.high_standard_contract"
                            )["requirements"][0],
                            "classification": "hard-current-prose",
                        }
                    ],
                },
            ),
            "task.skill_standard": (
                ("obligations[].role_use",),
                {
                    **packet_result_contracts.minimal_valid_shape_for_family("task.skill_standard"),
                    "obligations": [
                        {
                            **packet_result_contracts.minimal_valid_shape_for_family(
                                "task.skill_standard"
                            )["obligations"][0],
                            "role_use": "modeler",
                        }
                    ],
                },
            ),
            "flowguard_check.post_result": (
                ("reviewed_by_role",),
                {
                    **packet_result_contracts.minimal_valid_shape_for_family("flowguard_check.post_result"),
                    "reviewed_by_role": "flowguard model reviewer",
                },
            ),
            "pm_disposition.node_pm_disposition": (
                ("acceptance_item_disposition[].disposition",),
                {
                    **packet_result_contracts.minimal_valid_shape_for_family(
                        "pm_disposition.node_pm_disposition"
                    ),
                    "acceptance_item_disposition": [
                        {
                            **packet_result_contracts.minimal_valid_shape_for_family(
                                "pm_disposition.node_pm_disposition"
                            )["acceptance_item_disposition"][0],
                            "disposition": "accepted_with_notes",
                        }
                    ],
                },
            ),
        }

        for family_id, (expected_fields, payload) in invalid_payloads.items():
            with self.subTest(family_id=family_id):
                packet = packet_for_family(family_id)
                result = {"result_id": "result-current", "body": json.dumps(payload)}
                check = runtime._current_result_submission_contract_violation({}, packet, result)
                self.assertFalse(check.ok)
                self.assertIn("allowed_value_options", check.blocked_reason)
                for field in expected_fields:
                    self.assertIn(field, check.missing_required_fields)


if __name__ == "__main__":
    unittest.main()
