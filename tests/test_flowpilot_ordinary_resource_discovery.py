from __future__ import annotations

from dataclasses import replace
import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

from flowguard import review_architecture_reduction


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
if str(ASSETS) not in sys.path:
    sys.path.insert(0, str(ASSETS))

packet_result_contracts = importlib.import_module(
    "flowpilot_core_runtime.packet_result_contracts"
)
packet_stage_evidence_matrix = importlib.import_module(
    "flowpilot_core_runtime.packet_stage_evidence_matrix"
)
runtime = importlib.import_module("flowpilot_core_runtime.runtime")
router = importlib.import_module("flowpilot_router")
action_packets = importlib.import_module("flowpilot_router_action_handlers_packets")
action_packets_research = importlib.import_module(
    "flowpilot_router_action_handlers_packets_material"
)
action_providers = importlib.import_module("flowpilot_router_action_providers")
dispatch_policy = importlib.import_module("flowpilot_router_protocol_dispatch_policy")
expected_waits = importlib.import_module("flowpilot_router_expected_waits")
pm_package_reconciliation = importlib.import_module(
    "flowpilot_router_expected_waits_reconciliation_pm_package"
)
receipt_fold_registry = importlib.import_module(
    "flowpilot_router_controller_scheduler_receipts_packet_fold_registry"
)
repair_decisions = importlib.import_module(
    "flowpilot_router_events_repair_repair_decisions"
)
repair_transactions = importlib.import_module(
    "flowpilot_router_events_repair_transactions"
)
work_packet_next_actions = importlib.import_module(
    "flowpilot_router_work_packets_next_actions"
)
repair_transaction_model = importlib.import_module(
    "simulations.flowpilot_repair_transaction_model"
)
resource_discovery_model = importlib.import_module(
    "simulations.flowpilot_ordinary_resource_discovery_model"
)


class FlowPilotOrdinaryResourceDiscoveryTests(unittest.TestCase):
    def test_runtime_projects_current_shallow_local_inventory_before_pm_selection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            project_skill = project / "skills" / "project-skill"
            agent_skill = project / ".agents" / "skills" / "agent-skill"
            project_skill.mkdir(parents=True)
            agent_skill.mkdir(parents=True)
            (project_skill / "SKILL.md").write_text("# Project skill\n", encoding="utf-8")
            (agent_skill / "SKILL.md").write_text("# Agent skill\n", encoding="utf-8")

            ledger = runtime.new_ledger("Goal", "Acceptance")
            ledger["project_root"] = str(project)
            inventory = runtime._runtime_local_capability_inventory(ledger)

            self.assertEqual(
                inventory["schema_version"],
                "flowpilot.runtime_local_capability_inventory.v1",
            )
            self.assertEqual(inventory["scan_policy"], "shallow_path_and_availability_only")
            self.assertEqual(inventory["selection_owner"], "pm")
            self.assertEqual(inventory["deep_read_policy"], "selected_skills_only")
            rows = {row["skill_id"]: row for row in inventory["skills"]}
            self.assertIn("project-skill", rows)
            self.assertIn("agent-skill", rows)
            self.assertTrue(rows["project-skill"]["available"])
            self.assertEqual(
                rows["project-skill"]["inspection_depth"],
                "path_and_availability_only",
            )

    def test_discovery_packet_contains_inventory_but_no_material_specific_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            skill = project / "skills" / "current-skill"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("# Current skill\n", encoding="utf-8")
            ledger = runtime.new_ledger("Goal", "Acceptance")
            ledger["project_root"] = str(project)
            runtime.create_route(ledger, "Route", ["Plan"])
            packet_id = runtime._ensure_discovery_packet(ledger)
            body = json.loads(ledger["packets"][packet_id]["body"])

            self.assertIn("runtime_local_capability_inventory", body)
            self.assertIn("current-skill", [row["skill_id"] for row in body["runtime_local_capability_inventory"]["skills"]])
            self.assertEqual(
                set(body["required_output"]),
                {"decision", "candidate_skill_inventory"},
            )
            body_text = json.dumps(body, sort_keys=True)
            self.assertNotIn('"material_sources"', body_text)
            self.assertNotIn('"material_sufficiency"', body_text)
            self.assertIn("ordinary PM role-work path", body["instruction"])

    def test_narrowed_discovery_contract_keeps_one_existing_family(self) -> None:
        self.assertEqual(len(packet_result_contracts.PACKET_RESULT_CONTRACTS_BY_FAMILY), 13)
        row = packet_result_contracts.contract_for_family("task.discovery")
        self.assertIsNotNone(row)
        self.assertEqual(
            tuple(row["required_fields"]),
            ("decision", "candidate_skill_inventory"),
        )
        self.assertEqual(tuple(row["explicit_array_fields"]), ("candidate_skill_inventory",))
        self.assertFalse(row["non_empty_array_fields"])
        for removed in ("material_sources", "material_sufficiency", "material_current"):
            self.assertIn(removed, row["forbidden_fields"])
            self.assertNotIn(removed, row["fake_ai_success_fields"])
        matrix = packet_stage_evidence_matrix.stage_evidence_row_for_family("task.discovery")
        self.assertEqual(matrix["lifecycle_stage"], "preplanning_capability_discovery")
        self.assertEqual(matrix["required_evidence_owner"], "pm_skill_candidate_selection")

    def test_retained_facades_delegate_to_one_canonical_owner(self) -> None:
        plan = resource_discovery_model.build_architecture_reduction_plan()
        candidates = {row.candidate_id: row for row in plan.candidates}
        expected = {
            "retain_discovery_family_facade": (
                "commit.local_capability_inventory_precedes_pm_selection",
                "resource_discovery.current_result_contract",
                resource_discovery_model.DISCOVERY_AUTHORITY,
            ),
            "retain_optional_material_map": (
                "commit.material_map_is_optional_navigation_only",
                "material_artifact_map.navigation_status",
                resource_discovery_model.MATERIAL_MAP_AUTHORITY,
            ),
        }
        for candidate_id, (commitment_id, owner_contract, authority) in expected.items():
            with self.subTest(candidate_id=candidate_id):
                row = candidates[candidate_id]
                self.assertEqual(row.required_next_route, "structure_mesh")
                self.assertTrue(row.affected_public_entrypoints)
                self.assertEqual(row.behavior_commitment_id, commitment_id)
                self.assertEqual(row.business_intent_id, authority.business_intent_id)
                self.assertEqual(row.primary_path_id, authority.primary_path_id)
                self.assertEqual(row.owner_code_contract_id, owner_contract)
                self.assertEqual(row.delegates_to_code_contract_id, owner_contract)
                self.assertEqual(
                    row.delegates_to_primary_path_id,
                    authority.primary_path_id,
                )
                self.assertTrue(row.delegation_evidence_current)
                self.assertTrue(row.delegation_only)
                self.assertFalse(row.independent_business_authority)

    def test_retained_facade_authority_drift_is_rejected(self) -> None:
        plan = resource_discovery_model.build_architecture_reduction_plan()
        index = next(
            i
            for i, row in enumerate(plan.candidates)
            if row.candidate_id == "retain_optional_material_map"
        )
        base = plan.candidates[index]
        mutations = (
            (
                "missing_authority",
                replace(base, business_intent_id=""),
                "facade_delegation_contract_incomplete",
            ),
            (
                "wrong_target",
                replace(base, delegates_to_primary_path_id="path.wrong"),
                "facade_delegation_target_mismatch",
            ),
            (
                "stale_evidence",
                replace(base, delegation_evidence_current=False),
                "facade_delegation_evidence_stale",
            ),
            (
                "independent_authority",
                replace(base, independent_business_authority=True),
                "facade_independent_business_authority",
            ),
        )
        for name, mutated, expected_code in mutations:
            with self.subTest(name=name):
                rows = list(plan.candidates)
                rows[index] = mutated
                report = review_architecture_reduction(
                    replace(plan, candidates=tuple(rows))
                )
                self.assertFalse(report.ok)
                self.assertIn(
                    expected_code,
                    {finding.code for finding in report.findings},
                )

    def test_current_discovery_result_rejects_old_material_shape_without_fallback(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        runtime.create_route(ledger, "Route", ["Plan"])
        packet_id = runtime._ensure_discovery_packet(ledger)
        packet = ledger["packets"][packet_id]
        old_payload = {
            "decision": "pass",
            "candidate_skill_inventory": [],
            "material_sources": ["startup"],
            "material_sufficiency": "sufficient",
        }
        check = runtime._discovery_result_violation(
            packet,
            {"body": json.dumps(old_payload)},
        )
        self.assertFalse(check.ok)
        self.assertEqual(
            set(check.forbidden_fields_seen),
            {"material_sources", "material_sufficiency"},
        )
        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "removed material-specific"):
            runtime._parse_discovery_result(json.dumps(old_payload))
        self.assertEqual(
            runtime._parse_discovery_result(
                json.dumps({"decision": "pass", "candidate_skill_inventory": []})
            ),
            {"candidate_skill_inventory": []},
        )

    def test_ordinary_material_work_uses_existing_research_worker_task_path(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        runtime.create_route(ledger, "Route", ["Targeted evidence work"])
        packet_id = runtime.issue_task_packet(
            ledger,
            "research_worker",
            "Verify one source needed by PM",
            json.dumps(
                {
                    "instruction": "Perform bounded source verification as ordinary role work.",
                    "decision_owner": "pm",
                }
            ),
            route_scope="node",
        )
        packet = ledger["packets"][packet_id]
        self.assertEqual(packet["envelope"]["responsibility"], "research_worker")
        self.assertEqual(
            packet_result_contracts.packet_result_family_id(packet["envelope"]),
            "task.node",
        )
        self.assertNotIn("material", packet["envelope"]["route_scope"])
        research_card = (
            ASSETS / "runtime_kit/cards/phases/pm_research_package.md"
        ).read_text(encoding="utf-8").lower()
        normalized_card = " ".join(research_card.split())
        self.assertIn("ordinary bounded reading, research", normalized_card)
        self.assertIn("not a mandatory startup phase", normalized_card)
        self.assertIn("risk-appropriate existing reviewer/flowguard", normalized_card)

    def test_ordinary_router_research_writer_remains_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            run_root = project / ".flowpilot" / "runs" / "run-research"
            (run_root / "research").mkdir(parents=True)
            run_state = {"run_id": "run-research", "flags": {}}

            router._write_research_package(
                project,
                run_root,
                run_state,
                {
                    "decision_question": "Which source evidence should PM verify?",
                    "allowed_source_types": ["local"],
                    "packets": [
                        {
                            "packet_id": "research-source-check",
                            "to_role": "worker",
                            "body_text": "Verify the bounded source question.",
                        }
                    ],
                },
            )

            package = json.loads(
                (run_root / "research" / "research_package.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(package["schema_version"], "flowpilot.research_package.v1")
            self.assertEqual(package["written_by_role"], "project_manager")
            self.assertEqual(package["packets"][0]["packet_id"], "research-source-check")

    def test_material_map_absence_is_nonblocking(self) -> None:
        runtime_text = (ASSETS / "flowpilot_core_runtime/runtime.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("material_artifact_map", runtime_text)
        ledger = runtime.new_ledger("Goal", "Acceptance")
        ledger["high_standard_control_flow_required"] = True
        ledger["high_standard_contract"] = {"status": "accepted"}
        ledger["preplanning_discovery"] = {"status": "accepted"}
        ledger["skill_standard_contract"] = {"status": "accepted"}
        self.assertTrue(runtime.preplanning_gates_accepted(ledger))

    def test_removed_material_discovery_fields_have_only_negative_or_historical_hits(self) -> None:
        fake_e2e = (ASSETS / "flowpilot_core_runtime/fake_e2e.py").read_text(
            encoding="utf-8"
        )
        manifest = (ASSETS / "runtime_kit/manifest.json").read_text(encoding="utf-8")
        contract_index = (
            ASSETS / "runtime_kit/contracts/contract_index.json"
        ).read_text(encoding="utf-8")
        output_catalog = (
            ASSETS / "runtime_kit/cards/phases/pm_output_contract_catalog.md"
        ).read_text(encoding="utf-8")
        packet_schema = (ASSETS / "packet_runtime_schema.py").read_text(
            encoding="utf-8"
        )
        role_output_schema = (
            ASSETS / "role_output_runtime_schema_specs.py"
        ).read_text(encoding="utf-8")
        router_export_registry = (
            ASSETS / "runtime_kit/router_facade_owner_exports.json"
        ).read_text(encoding="utf-8")
        self.assertNotIn('"material_sources"', fake_e2e)
        self.assertNotIn('"material_sufficiency"', fake_e2e)
        for card_id in (
            "pm.material_scan",
            "reviewer.material_sufficiency",
            "pm.material_absorb_or_research",
            "pm.material_understanding",
        ):
            self.assertNotIn(card_id, manifest)
        self.assertNotIn("worker_material_scan_result", contract_index)
        self.assertNotIn("material_sufficiency_report", contract_index)
        self.assertNotIn("worker.material_scan", contract_index)
        self.assertNotIn("reviewer.material_sufficiency", contract_index)
        self.assertNotIn("worker_material_scan_result", output_catalog)
        self.assertNotIn("pm_records_material_scan_result_disposition", output_catalog)
        self.assertNotIn("worker.material_scan", packet_schema)
        self.assertNotIn("worker_material_scan_result", packet_schema)
        self.assertNotIn("material_sufficiency_report", role_output_schema)
        for removed_export in (
            "_material_scan_index_path",
            "_next_material_packet_action",
            "_write_material_scan_packets",
            "_write_material_sufficiency_report",
            "_write_material_understanding",
            "_commit_material_scan_repair_generation",
            "_repair_packet_specs_from_decision",
            "_try_reconcile_material_scan_body_delivery",
            "_try_reconcile_material_scan_results",
        ):
            self.assertNotIn(removed_export, router_export_registry)
        for deleted_path in (
            ASSETS / "runtime_kit/cards/phases/pm_material_scan.md",
            ASSETS / "runtime_kit/cards/reviewer/material_sufficiency.md",
            ASSETS / "runtime_kit/cards/phases/pm_material_absorb_or_research.md",
            ASSETS / "runtime_kit/cards/phases/pm_material_understanding.md",
            ROOT / "templates/flowpilot/material_intake_packet.template.json",
            ROOT / "templates/flowpilot/pm_material_understanding.template.json",
        ):
            self.assertFalse(deleted_path.exists())

        current_template_paths = (
            ROOT / "templates/flowpilot/capabilities.template.json",
            ROOT / "templates/flowpilot/state.template.json",
            ROOT / "templates/flowpilot/execution_frontier.template.json",
            ROOT / "templates/flowpilot/product_function_architecture.template.json",
            ROOT / "templates/flowpilot/root_acceptance_contract.template.json",
            ROOT / "templates/flowpilot/routes/route-001/flow.template.json",
            ROOT / "templates/flowpilot/routes/route-001/flow.template.md",
            ROOT / "templates/flowpilot/packets/packet_body.template.md",
            ROOT / "templates/flowpilot/routes/route-001/nodes/node-001-start/node.template.json",
            ROOT / "templates/flowpilot/runs/run-001/run.template.json",
        )
        current_template_text = "\n".join(
            path.read_text(encoding="utf-8") for path in current_template_paths
        )
        for removed_template_authority in (
            '"material_intake_packet"',
            '"pm_material_understanding"',
            '"material_sufficiency"',
            "material_intake_packet_written",
            "material_reviewer_sufficiency_approved",
        ):
            self.assertNotIn(removed_template_authority, current_template_text)
        capability_template = json.loads(
            (ROOT / "templates/flowpilot/capabilities.template.json").read_text(
                encoding="utf-8"
            )
        )
        capability_ids = {row["id"] for row in capability_template["capabilities"]}
        self.assertIn("local_capability_inventory", capability_ids)
        self.assertNotIn("material_intake_handoff", capability_ids)

        row = packet_result_contracts.contract_for_family("task.discovery")
        for removed in ("material_sources", "material_sufficiency", "material_current"):
            self.assertIn(removed, row["forbidden_fields"])
        runtime_text = (ASSETS / "flowpilot_core_runtime/runtime.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("removed material-specific field", runtime_text)
        self.assertNotIn("setdefault(\"material_sufficiency\"", runtime_text)
        self.assertNotIn("payload.get(\"material_sufficiency\") or", runtime_text)
        parallel_contract = (ROOT / "docs/parallel_packet_batch_plan.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("This document describes the current single FlowPilot path", parallel_contract)
        self.assertIn("ordinary PM-selected work package", parallel_contract)
        self.assertIn("## Retired positive surfaces", parallel_contract)
        self.assertNotIn("Add router helpers for a `parallel_packet_batch` index", parallel_contract)
        self.assertNotIn("Move the existing material `packets[]` path", parallel_contract)
        process_binding_contract = (
            ROOT / "docs/flowpilot_process_contract_binding_plan.md"
        ).read_text(encoding="utf-8")
        self.assertIn("ordinary_material_evidence_work", process_binding_contract)
        self.assertNotIn("| `material_scan` | PM material scan package", process_binding_contract)
        self.assertNotIn("`worker.material_scan`", process_binding_contract)

    def test_retired_material_router_path_has_no_positive_dispatch_or_repair_surface(self) -> None:
        retired_names = (
            "_next_material_packet_action",
            "_commit_material_scan_repair_generation",
            "_repair_packet_specs_from_decision",
            "_try_reconcile_material_scan_body_delivery",
            "_try_reconcile_material_scan_results",
            "_apply_relay_material_scan_packets",
            "_apply_relay_material_scan_results",
        )
        for name in retired_names:
            with self.subTest(name=name):
                self.assertFalse(hasattr(router, name))
                self.assertNotIn(name, repair_transactions.__all__)
                self.assertNotIn(name, work_packet_next_actions.__all__)
                self.assertNotIn(name, action_packets.__all__)
                self.assertFalse(hasattr(expected_waits, name))

        self.assertEqual(
            set(action_packets_research.__all__),
            {"_apply_relay_research_packet", "_apply_relay_research_result"},
        )
        self.assertNotIn("material_packet", action_providers.PROVIDER_ORDER)
        self.assertNotIn("packet_reissue", router.REPAIR_TRANSACTION_EXECUTABLE_PLAN_KINDS)
        self.assertNotIn(
            "packet_reissue", repair_transaction_model.EXECUTABLE_REPAIR_PLAN_KINDS
        )
        self.assertIn(
            "retired_packet_reissue_accepted",
            repair_transaction_model.hazard_states(),
        )
        self.assertIn(
            "retired_material_dispatch_repair_lane_reintroduced",
            repair_transaction_model.hazard_states(),
        )
        contract_index = json.loads(
            (ASSETS / "runtime_kit/contracts/contract_index.json").read_text(
                encoding="utf-8"
            )
        )
        repair_contract = next(
            row
            for row in contract_index["contracts"]
            if row.get("contract_id")
            == "flowpilot.output_contract.pm_control_blocker_repair_decision.v1"
        )
        self.assertNotIn(
            "packet_reissue",
            repair_contract["allowed_repair_transaction_plan_kind_values"],
        )
        self.assertNotIn(
            "repair_transaction.replacement_packets",
            repair_contract["explicit_array_fields"],
        )
        self.assertNotIn(
            "packet_reissue_requires_atomic_generation_commit", repair_contract
        )
        role_output_contract_source = (
            ASSETS / "role_output_runtime_contracts.py"
        ).read_text(encoding="utf-8")
        role_output_schema_source = (
            ASSETS / "role_output_runtime_schema_specs.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("replacement_packet_specs_path", role_output_contract_source)
        self.assertNotIn("replacement_packet_specs_hash", role_output_contract_source)
        self.assertNotIn('"replacement_packets": []', role_output_contract_source)
        self.assertNotIn(
            '"repair_transaction.replacement_packets"', role_output_schema_source
        )
        self.assertNotIn(
            "relay_material_scan_packets",
            router.REPAIR_TRANSACTION_SAFE_REPLAY_ACTION_TYPES,
        )
        self.assertNotIn(
            "relay_material_scan_results_to_pm",
            router.REPAIR_TRANSACTION_SAFE_REPLAY_ACTION_TYPES,
        )
        for retired_action in (
            "relay_material_scan_packets",
            "relay_material_scan_results_to_pm",
            "relay_material_scan_results_to_reviewer",
        ):
            self.assertNotIn(
                retired_action,
                receipt_fold_registry.CONTROLLER_RECEIPT_EVIDENCE_FOLD_REGISTRY,
            )
        self.assertNotIn(
            "relay_material_scan_packets",
            dispatch_policy.FORMAL_WORK_PACKET_RELAY_ACTION_TYPES,
        )
        self.assertNotIn(
            "relay_material_scan_packets",
            dispatch_policy.DISPATCH_RECIPIENT_GATE_ACTION_OUTPUT_EVENTS,
        )
        self.assertNotIn(
            "pm_records_material_scan_result_disposition",
            pm_package_reconciliation._RECONCILED_PM_PACKAGE_DOMAIN_COMMITS,
        )
        parallel_reconciliation_source = (
            ASSETS / "flowpilot_router_work_packets_parallel_reconciliation.py"
        ).read_text(encoding="utf-8")
        status_summary_source = (
            ASSETS / "flowpilot_router_route_frontier_status_summary.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn('"material_scan": "project_manager"', parallel_reconciliation_source)
        self.assertNotIn(
            '("material_scan", "research", "current_node", "pm_role_work")',
            parallel_reconciliation_source,
        )
        self.assertNotIn(
            "('material_scan', 'research', 'current_node', 'pm_role_work')",
            status_summary_source,
        )
        router_loop_state_source = (
            ROOT / "simulations/flowpilot_router_loop_model_state.py"
        ).read_text(encoding="utf-8")
        router_loop_invariant_source = (
            ROOT / "simulations/flowpilot_router_loop_model_invariants.py"
        ).read_text(encoding="utf-8")
        router_loop_hazard_source = (
            ROOT / "simulations/flowpilot_router_loop_model_hazards.py"
        ).read_text(encoding="utf-8")
        router_structure_catalog = (
            ROOT / "simulations/flowpilot_router_facade_split_catalog.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("current_node | material_scan", router_loop_state_source)
        self.assertNotIn(
            '{"current_node", "material_scan", "research", "pm_role_work"}',
            router_loop_invariant_source,
        )
        self.assertNotIn(
            '"material_active_holder_lease_without_packet_registration"',
            router_loop_hazard_source,
        )
        self.assertNotIn('"_next_material_packet_action"', router_structure_catalog)
        self.assertIn(
            "relay_research_packet",
            receipt_fold_registry.CONTROLLER_RECEIPT_EVIDENCE_FOLD_REGISTRY,
        )
        self.assertEqual(
            tuple(row[0] for row in router.PRE_ROUTE_PHASE_ITEMS),
            (
                "product_architecture",
                "root_contract",
                "dependency_policy",
                "child_skill_gate_manifest",
            ),
        )
        with self.assertRaisesRegex(router.RouterError, "ordinary PM role-work repair"):
            repair_decisions._repair_transaction_normalized_plan_kind(
                router,
                "packet_reissue",
            )
        self.assertIn(
            "replacement packets are not supported by the current repair contract",
            (ASSETS / "flowpilot_router_events_repair_repair_decisions.py").read_text(
                encoding="utf-8"
            ),
        )
        research_owner_source = (
            ASSETS / "flowpilot_router_work_packets_material.py"
        ).read_text(encoding="utf-8")
        reconciliation_source = (
            ASSETS / "flowpilot_router_work_packets_result_reconciliation.py"
        ).read_text(encoding="utf-8")
        for retired_definition in (
            "def _material_packet_body_text_from_spec",
            "def _write_material_scan_packets",
            "def _write_material_dispatch_block_report",
            "def _write_material_dispatch_recheck_protocol_blocker",
            "def _write_material_sufficiency_report",
            "def _write_material_understanding",
        ):
            self.assertNotIn(retired_definition, research_owner_source)
        self.assertIn("def _write_research_package", research_owner_source)
        self.assertIn("def _write_worker_research_report", research_owner_source)
        self.assertNotIn("'material_scan':", reconciliation_source)
        self.assertNotIn("def _try_reconcile_material_scan", reconciliation_source)
        self.assertIn("def _try_reconcile_research_results", reconciliation_source)
        for deleted_module in (
            ASSETS / "flowpilot_router_work_packets_material_next.py",
            ASSETS / "flowpilot_router_events_repair_transaction_material.py",
        ):
            self.assertFalse(deleted_module.exists())


if __name__ == "__main__":
    unittest.main()
