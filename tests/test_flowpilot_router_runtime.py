from __future__ import annotations

import json
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))

import flowpilot_router as router  # noqa: E402
import packet_runtime  # noqa: E402


STARTUP_ANSWERS = {
    "background_agents": "allow",
    "scheduled_continuation": "manual",
    "display_surface": "chat",
    "provenance": "explicit_user_reply",
}

HEARTBEAT_STARTUP_ANSWERS = {
    **STARTUP_ANSWERS,
    "scheduled_continuation": "allow",
}

USER_REQUEST = {
    "text": "Use FlowPilot to complete the requested project with PM-owned route control.",
    "provenance": "explicit_user_request",
    "source": "activation_turn",
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class FlowPilotRouterRuntimeTests(unittest.TestCase):
    def make_project(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="flowpilot-router-"))

    def next_and_apply(self, root: Path, payload: dict | None = None) -> dict:
        action = router.next_action(root)
        return router.apply_action(root, str(action["action_type"]), payload or {})

    def run_root_for(self, root: Path) -> Path:
        current = read_json(root / ".flowpilot" / "current.json")
        return root / current["current_run_root"]

    def flag(self, root: Path, name: str) -> bool:
        run_root = self.run_root_for(root)
        state = read_json(router.run_state_path(run_root))
        return bool(state["flags"].get(name))

    def material_scan_payload(self) -> dict:
        return {
            "packets": [
                {
                    "packet_id": "material-scan-001",
                    "to_role": "worker_a",
                    "body_text": "Inspect the current request, repository state, and available local materials.",
                }
            ]
        }

    def apply_next_packet_action(self, root: Path, expected_action_type: str) -> dict:
        action = router.next_action(root)
        if action["action_type"] == "check_packet_ledger":
            router.apply_action(root, "check_packet_ledger")
            action = router.next_action(root)
        self.assertEqual(action["action_type"], expected_action_type)
        return router.apply_action(root, expected_action_type)

    def open_packets_and_write_results(self, root: Path, index_path: Path, *, result_text: str = "worker result") -> None:
        index = read_json(index_path)
        for record in index["packets"]:
            envelope = packet_runtime.load_envelope(root, record["packet_envelope_path"])
            packet_runtime.read_packet_body_for_role(root, envelope, role=envelope["to_role"])
            packet_runtime.write_result(
                root,
                packet_envelope=envelope,
                completed_by_role=envelope["to_role"],
                completed_by_agent_id=f"{envelope['to_role']}-agent",
                result_body_text=result_text,
                next_recipient="human_like_reviewer",
            )

    def open_results_for_reviewer(self, root: Path, index_path: Path) -> None:
        index = read_json(index_path)
        for record in index["packets"]:
            result = packet_runtime.load_envelope(root, record["result_envelope_path"])
            packet_runtime.read_result_body_for_role(root, result, role="human_like_reviewer")

    def next_after_display_sync(self, root: Path) -> dict:
        action = router.next_action(root)
        while action["action_type"] == "sync_display_plan":
            router.apply_action(root, "sync_display_plan")
            action = router.next_action(root)
        return action

    def deliver_expected_card(self, root: Path, card_id: str) -> dict:
        action = self.next_after_display_sync(root)
        if action["action_type"] == "check_prompt_manifest":
            router.apply_action(root, "check_prompt_manifest")
            action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "deliver_system_card")
        self.assertEqual(action["card_id"], card_id)
        router.apply_action(root, "deliver_system_card")
        return action

    def deliver_user_intake_mail(self, root: Path) -> None:
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "check_packet_ledger")
        self.assertEqual(action["next_mail_id"], "user_intake")
        router.apply_action(root, "check_packet_ledger")
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "deliver_mail")
        self.assertEqual(action["mail_id"], "user_intake")
        router.apply_action(root, "deliver_mail")

    def boot_to_controller(self, root: Path, startup_answers: dict | None = None) -> Path:
        startup_answers = startup_answers or STARTUP_ANSWERS
        while True:
            action = router.next_action(root)
            action_type = str(action["action_type"])
            if action_type == "record_startup_answers":
                router.apply_action(root, action_type, {"startup_answers": startup_answers})
            elif action_type == "record_user_request":
                router.apply_action(root, action_type, {"user_request": USER_REQUEST})
            elif action_type == "start_role_slots":
                router.apply_action(root, action_type, self.role_agent_payload(root, startup_answers))
            else:
                router.apply_action(root, action_type)
            if action_type == "load_controller_core":
                break
        current = read_json(root / ".flowpilot" / "current.json")
        return root / current["current_run_root"]

    def role_agent_payload(self, root: Path, startup_answers: dict | None = None) -> dict:
        startup_answers = startup_answers or STARTUP_ANSWERS
        if startup_answers.get("background_agents") == "single-agent":
            return {}
        bootstrap = self.bootstrap_state(root)
        run_id = bootstrap["run_id"]
        return {
            "background_agents_capability_status": "available",
            "role_agents": [
                {
                    "role_key": role,
                    "agent_id": f"agent-{run_id}-{role}",
                    "spawn_result": "spawned_fresh_for_task",
                    "spawned_for_run_id": run_id,
                    "spawned_after_startup_answers": True,
                }
                for role in router.CREW_ROLE_KEYS
            ],
        }

    def bootstrap_state(self, root: Path) -> dict:
        return read_json(router.bootstrap_state_path(root))

    def deliver_initial_pm_cards_and_user_intake(self, root: Path) -> None:
        self.deliver_expected_card(root, "pm.core")
        self.deliver_expected_card(root, "pm.controller_reset_duty")
        self.deliver_expected_card(root, "pm.phase_map")
        self.deliver_expected_card(root, "pm.startup_intake")
        self.deliver_user_intake_mail(root)

    def complete_startup_activation(self, root: Path) -> None:
        self.deliver_initial_pm_cards_and_user_intake(root)
        router.record_external_event(root, "pm_first_decision_resets_controller")
        router.record_external_event(root, "controller_role_confirmed_from_pm_reset")
        self.deliver_expected_card(root, "reviewer.startup_fact_check")
        router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            {"reviewed_by_role": "human_like_reviewer", "passed": True},
        )
        self.deliver_expected_card(root, "pm.startup_activation")
        router.record_external_event(root, "pm_approves_startup_activation", {"decision": "approved"})
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "write_display_surface_status")
        router.apply_action(root, "write_display_surface_status")

    def complete_material_flow(self, root: Path) -> None:
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "deliver_system_card")
        self.assertEqual(action["card_id"], "pm.material_scan")
        router.apply_action(root, "deliver_system_card")

        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "reviewer.dispatch_request")
        router.apply_action(root, "deliver_system_card")

        router.record_external_event(root, "reviewer_allows_material_scan_dispatch")
        self.apply_next_packet_action(root, "relay_material_scan_packets")
        run_root = self.run_root_for(root)
        material_index_path = run_root / "material" / "material_scan_packets.json"
        self.open_packets_and_write_results(root, material_index_path, result_text="material scan result")
        router.record_external_event(root, "worker_scan_packet_bodies_delivered_after_dispatch")
        router.record_external_event(root, "worker_scan_results_returned")
        self.apply_next_packet_action(root, "relay_material_scan_results_to_reviewer")
        self.open_results_for_reviewer(root, material_index_path)

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "reviewer.material_sufficiency")
        router.apply_action(root, "deliver_system_card")

        router.record_external_event(
            root,
            "reviewer_reports_material_sufficient",
            {
                "reviewed_by_role": "human_like_reviewer",
                "direct_material_sources_checked": True,
                "packet_matches_checked_sources": True,
                "pm_ready": True,
            },
        )
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.event.reviewer_report")
        router.apply_action(root, "deliver_system_card")

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.material_absorb_or_research")
        router.apply_action(root, "deliver_system_card")

        router.record_external_event(root, "pm_accepts_reviewed_material")
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.material_understanding")
        router.apply_action(root, "deliver_system_card")
        router.record_external_event(root, "pm_writes_material_understanding", {"material_summary": "reviewed material accepted"})

    def complete_root_contract_before_child_skill_gates(self, root: Path) -> None:
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.product_architecture")
        router.apply_action(root, "deliver_system_card")
        router.record_external_event(
            root,
            "pm_writes_product_function_architecture",
            {
                "user_task_map": [{"task_id": "task-001", "goal": "complete the requested project"}],
                "product_capability_map": [{"capability_id": "cap-001", "behavior": "complete requested work"}],
                "feature_decisions": [{"feature_id": "feature-001", "decision": "must"}],
                "highest_achievable_product_target": {"product_vision": "professional completion"},
                "semantic_fidelity_policy": {"silent_downgrade_forbidden": True},
                "functional_acceptance_matrix": [{"acceptance_id": "root-001"}],
            },
        )

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "product_officer.product_architecture_modelability")
        router.apply_action(root, "deliver_system_card")
        router.record_external_event(
            root,
            "product_officer_passes_product_architecture_modelability",
            {"reviewed_by_role": "product_flowguard_officer", "passed": True},
        )

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "reviewer.product_architecture_challenge")
        router.apply_action(root, "deliver_system_card")
        router.record_external_event(
            root,
            "reviewer_passes_product_architecture",
            {"reviewed_by_role": "human_like_reviewer", "passed": True},
        )

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.root_contract")
        router.apply_action(root, "deliver_system_card")
        router.record_external_event(
            root,
            "pm_writes_root_acceptance_contract",
            {
                "root_requirements": [
                    {
                        "requirement_id": "root-001",
                        "priority": "must",
                        "proof_required": "mixed",
                    }
                ],
                "proof_matrix": [{"requirement_id": "root-001", "expected_final_replay": True}],
                "selected_scenario_ids": ["terminal_complete_state"],
            },
        )

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "reviewer.root_contract_challenge")
        router.apply_action(root, "deliver_system_card")
        router.record_external_event(
            root,
            "reviewer_passes_root_acceptance_contract",
            {"reviewed_by_role": "human_like_reviewer", "passed": True},
        )

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "product_officer.root_contract_modelability")
        router.apply_action(root, "deliver_system_card")
        router.record_external_event(
            root,
            "product_officer_passes_root_acceptance_contract_modelability",
            {"reviewed_by_role": "product_flowguard_officer", "passed": True},
        )
        router.record_external_event(root, "pm_freezes_root_acceptance_contract")

    def complete_product_architecture_and_contract(self, root: Path) -> None:
        self.complete_root_contract_before_child_skill_gates(root)
        self.complete_child_skill_gates(root)

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.prior_path_context")
        router.apply_action(root, "deliver_system_card")

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.route_skeleton")
        router.apply_action(root, "deliver_system_card")
        router.record_external_event(
            root,
            "pm_writes_route_draft",
            {
                "nodes": [{"node_id": "node-001"}],
                **self.prior_path_context_review(root, "Initial route draft considered the empty current-run route history."),
            },
        )
        router.record_external_event(root, "process_officer_passes_route_check")
        router.record_external_event(root, "product_officer_passes_route_check")
        router.record_external_event(root, "reviewer_passes_route_check")

    def complete_child_skill_gates(self, root: Path) -> None:
        selected_skills = [
            {
                "skill_name": "model-first-function-flow",
                "decision": "required",
                "supported_capabilities": ["cap-001"],
                "references_loaded_now": [],
                "references_deferred_with_reason": [],
                "gates": [
                    {
                        "gate_id": "process-model",
                        "required_approver": "process_flowguard_officer",
                        "evidence_required": ["model-check-result"],
                        "controller_can_approve": False,
                    }
                ],
            }
        ]

        if not self.flag(root, "pm_dependency_policy_card_delivered"):
            self.deliver_expected_card(root, "pm.dependency_policy")
        router.record_external_event(
            root,
            "pm_records_dependency_policy",
            {
                "allowed_dependency_actions": ["use_existing_local_skill"],
                "host_level_install_requested": False,
            },
        )
        router.record_external_event(
            root,
            "pm_writes_capabilities_manifest",
            {
                "capabilities": [{"capability_id": "cap-001", "behavior": "model and gate route work"}],
                "capability_to_skill_needs": [{"capability_id": "cap-001", "candidate_skill": "model-first-function-flow"}],
            },
        )

        self.deliver_expected_card(root, "pm.child_skill_selection")
        router.record_external_event(root, "pm_writes_child_skill_selection", {"selected_skills": selected_skills})

        self.deliver_expected_card(root, "pm.child_skill_gate_manifest")
        router.record_external_event(root, "pm_writes_child_skill_gate_manifest", {"selected_skills": selected_skills})

        self.deliver_expected_card(root, "reviewer.child_skill_gate_manifest_review")
        router.record_external_event(
            root,
            "reviewer_passes_child_skill_gate_manifest",
            {"reviewed_by_role": "human_like_reviewer", "passed": True},
        )

        self.deliver_expected_card(root, "process_officer.child_skill_conformance_model")
        router.record_external_event(
            root,
            "process_officer_passes_child_skill_conformance_model",
            {"reviewed_by_role": "process_flowguard_officer", "passed": True},
        )

        self.deliver_expected_card(root, "product_officer.child_skill_product_fit")
        router.record_external_event(
            root,
            "product_officer_passes_child_skill_product_fit",
            {"reviewed_by_role": "product_flowguard_officer", "passed": True},
        )
        router.record_external_event(root, "pm_approves_child_skill_manifest_for_route")
        router.record_external_event(root, "capability_evidence_synced")

    def complete_pre_route_gates(self, root: Path) -> None:
        self.complete_startup_activation(root)
        self.complete_material_flow(root)
        self.complete_product_architecture_and_contract(root)

    def test_controller_route_memory_is_refreshed_and_required_for_pm_route_draft(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        history_path = run_root / "route_memory" / "route_history_index.json"
        context_path = run_root / "route_memory" / "pm_prior_path_context.json"
        self.assertTrue(history_path.exists())
        self.assertTrue(context_path.exists())
        history = read_json(history_path)
        context = read_json(context_path)
        self.assertEqual(history["schema_version"], "flowpilot.route_history_index.v1")
        self.assertEqual(context["schema_version"], "flowpilot.pm_prior_path_context.v1")
        self.assertEqual(history["generated_by"], "controller")
        self.assertFalse(history["sealed_packet_or_result_bodies_read"])
        self.assertFalse(context["controller_decision_authority"])

        self.complete_startup_activation(root)
        self.complete_material_flow(root)
        self.complete_root_contract_before_child_skill_gates(root)
        self.complete_child_skill_gates(root)

        action = self.deliver_expected_card(root, "pm.prior_path_context")
        self.assertTrue(action["pm_prior_path_context_required_for_decision"])
        self.assertEqual(
            action["pm_context_paths"]["pm_prior_path_context"],
            self.rel(root, context_path),
        )

        self.deliver_expected_card(root, "pm.route_skeleton")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_route_draft", {"nodes": [{"node_id": "node-001"}]})

        router.record_external_event(
            root,
            "pm_writes_route_draft",
            {
                "nodes": [{"node_id": "node-001"}],
                **self.prior_path_context_review(root, "Route draft used current Controller route-memory indexes."),
            },
        )
        draft = read_json(run_root / "routes" / "route-001" / "flow.draft.json")
        self.assertEqual(draft["prior_path_context_review"]["source_paths"][0], self.rel(root, context_path))

    def activate_route(self, root: Path, node_id: str = "node-001") -> None:
        router.record_external_event(
            root,
            "pm_activates_reviewed_route",
            {"route_id": "route-001", "active_node_id": node_id, "route_version": 1},
        )

    def deliver_current_node_cards(self, root: Path) -> None:
        self.deliver_expected_card(root, "pm.current_node_loop")
        self.deliver_expected_card(root, "pm.event.node_started")
        self.deliver_expected_card(root, "pm.node_acceptance_plan")
        router.record_external_event(
            root,
            "pm_writes_node_acceptance_plan",
            {
                **self.prior_path_context_review(root, "Node acceptance plan considered route memory and active frontier."),
                "high_standard_recheck": {
                    "ideal_outcome": "complete the current node at the highest practical standard",
                    "unacceptable_outcomes": ["partial work", "unverified closure", "controller downgrade"],
                    "higher_standard_opportunities": ["tighten acceptance evidence before dispatch"],
                    "semantic_downgrade_risks": ["treating packet existence as product acceptance"],
                    "decision": "proceed",
                    "why_current_plan_meets_highest_reasonable_standard": "PM listed node requirements, proof, and direct review gates before work dispatch.",
                },
                "node_requirements": [
                    {
                        "requirement_id": "node-001-req",
                        "acceptance_statement": "current node work is complete",
                        "proof_required": "mixed",
                    }
                ],
                "experiment_plan": [],
            },
        )
        self.deliver_expected_card(root, "reviewer.node_acceptance_plan_review")
        router.record_external_event(
            root,
            "reviewer_passes_node_acceptance_plan",
            {"reviewed_by_role": "human_like_reviewer", "passed": True},
        )

    def complete_parent_backward_replay_if_due(self, root: Path) -> None:
        action = router.next_action(root)
        if action["action_type"] == "check_prompt_manifest" and action.get("next_card_id") == "pm.parent_backward_targets":
            router.apply_action(root, "check_prompt_manifest")
            action = router.next_action(root)
        if action.get("card_id") != "pm.parent_backward_targets":
            return
        router.apply_action(root, "deliver_system_card")
        router.record_external_event(root, "pm_builds_parent_backward_targets")
        self.deliver_expected_card(root, "reviewer.parent_backward_replay")
        router.record_external_event(
            root,
            "reviewer_passes_parent_backward_replay",
            {"reviewed_by_role": "human_like_reviewer", "passed": True},
        )
        self.deliver_expected_card(root, "pm.parent_segment_decision")
        router.record_external_event(
            root,
            "pm_records_parent_segment_decision",
            {
                "decision": "continue",
                **self.prior_path_context_review(root, "Parent segment decision considered current route memory."),
            },
        )

    def complete_evidence_quality_package(self, root: Path) -> None:
        run_root = self.run_root_for(root)
        self.deliver_expected_card(root, "pm.evidence_quality_package")
        router.record_external_event(
            root,
            "pm_records_evidence_quality_package",
            {
                **self.prior_path_context_review(root, "Evidence quality package considered current route memory."),
                "evidence_items": [
                    {
                        "evidence_id": "current-node-reviewed-result",
                        "path": ".flowpilot/current-node-result",
                        "status": "current",
                    }
                ],
                "generated_resources": [],
                "ui_visual_evidence_required": False,
            },
        )
        self.assertTrue((run_root / "evidence" / "evidence_ledger.json").exists())
        self.assertTrue((run_root / "generated_resource_ledger.json").exists())
        self.assertTrue((run_root / "quality" / "quality_package.json").exists())
        self.deliver_expected_card(root, "reviewer.evidence_quality_review")
        router.record_external_event(
            root,
            "reviewer_passes_evidence_quality_package",
            {"reviewed_by_role": "human_like_reviewer", "passed": True},
        )

    def complete_final_ledger_and_terminal_replay(self, root: Path) -> None:
        run_root = self.run_root_for(root)
        self.deliver_expected_card(root, "pm.final_ledger")
        router.record_external_event(root, "pm_records_final_route_wide_ledger_clean", self.final_ledger_payload(root))
        final_ledger_path = run_root / "final_route_wide_gate_ledger.json"
        terminal_map_path = run_root / "terminal_human_backward_replay_map.json"
        self.assertTrue(final_ledger_path.exists())
        self.assertTrue(terminal_map_path.exists())
        ledger = read_json(final_ledger_path)
        self.assertEqual(ledger["status"], "clean")
        self.assertFalse(ledger["completion_allowed"])

        self.deliver_expected_card(root, "reviewer.final_backward_replay")
        router.record_external_event(
            root,
            "reviewer_final_backward_replay_passed",
            self.terminal_replay_payload(root),
        )
        terminal_map = read_json(terminal_map_path)
        ledger = read_json(final_ledger_path)
        self.assertEqual(terminal_map["status"], "passed")
        self.assertTrue(ledger["completion_allowed"])

    def rel(self, root: Path, path: Path) -> str:
        return str(path.relative_to(root)).replace("\\", "/")

    def prior_path_context_review(self, root: Path, impact: str = "PM considered current route memory before deciding") -> dict:
        run_root = self.run_root_for(root)
        return {
            "prior_path_context_review": {
                "reviewed": True,
                "source_paths": [
                    self.rel(root, run_root / "route_memory" / "pm_prior_path_context.json"),
                    self.rel(root, run_root / "route_memory" / "route_history_index.json"),
                ],
                "completed_nodes_considered": [],
                "superseded_nodes_considered": [],
                "stale_evidence_considered": [],
                "prior_blocks_or_experiments_considered": [],
                "impact_on_decision": impact,
                "controller_summary_used_as_evidence": False,
            }
        }

    def final_ledger_payload(self, root: Path) -> dict:
        run_root = self.run_root_for(root)
        root_contract_path = self.rel(root, run_root / "root_acceptance_contract.json")
        scenario_pack_path = self.rel(root, run_root / "standard_scenario_pack.json")
        route_flow_path = self.rel(root, run_root / "routes" / "route-001" / "flow.json")
        node_plan_path = self.rel(root, run_root / "routes" / "route-001" / "nodes" / "node-001" / "node_acceptance_plan.json")
        quality_review_path = self.rel(root, run_root / "reviews" / "evidence_quality_review.json")
        return {
            "pm_owned": True,
            **self.prior_path_context_review(root, "PM rebuilt final ledger from current route memory and source-of-truth ledgers."),
            "standard_scenarios_replayed": True,
            "root_contract_replay": [
                {
                    "requirement_id": "root-001",
                    "status": "approved",
                    "evidence_paths": [root_contract_path, scenario_pack_path],
                    "standard_scenarios_replayed": True,
                }
            ],
            "entries": [
                {
                    "entry_id": "route-001:root-contract",
                    "route_version": 1,
                    "node_id": "root",
                    "gate_family": "root_acceptance_contract",
                    "required_approver": "project_manager",
                    "status": "approved",
                    "source_of_truth_paths": [root_contract_path, scenario_pack_path],
                    "evidence_paths": [root_contract_path, scenario_pack_path],
                },
                {
                    "entry_id": "route-001:node-001:acceptance",
                    "route_version": 1,
                    "node_id": "node-001",
                    "gate_family": "node_acceptance",
                    "required_approver": "human_like_reviewer",
                    "status": "approved",
                    "source_of_truth_paths": [route_flow_path, node_plan_path],
                    "evidence_paths": [node_plan_path, quality_review_path],
                },
            ],
            "terminal_replay_segments": [
                {"segment_id": "delivered_product", "source_of_truth_paths": [root_contract_path]},
                {"segment_id": "root_acceptance", "source_of_truth_paths": [root_contract_path, scenario_pack_path]},
                {"segment_id": "leaf:node-001", "source_of_truth_paths": [route_flow_path, node_plan_path]},
            ],
            "pm_segment_decisions": [
                {"segment_id": "delivered_product", "decision": "continue"},
                {"segment_id": "root_acceptance", "decision": "continue"},
                {"segment_id": "leaf:node-001", "decision": "continue"},
            ],
        }

    def terminal_replay_payload(self, root: Path) -> dict:
        run_root = self.run_root_for(root)
        terminal_map = read_json(run_root / "terminal_human_backward_replay_map.json")
        segment_reviews = [
            {
                "segment_id": segment["segment_id"],
                "reviewed_by_role": "human_like_reviewer",
                "passed": True,
                "pm_segment_decision": "continue",
            }
            for segment in terminal_map["segments"]
        ]
        return {
            "reviewed_by_role": "human_like_reviewer",
            "passed": True,
            "segment_reviews": segment_reviews,
        }

    def complete_leaf_node_with_reviewed_result(
        self,
        root: Path,
        *,
        packet_id: str = "node-packet-leaf",
        agent_id: str = "agent-worker-leaf",
    ) -> None:
        self.deliver_current_node_cards(root)
        packet = packet_runtime.create_packet(
            root,
            packet_id=packet_id,
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="current node work",
            metadata={"route_version": 1},
        )
        packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
        router.record_external_event(root, "pm_registers_current_node_packet", {"packet_id": packet_id, "packet_envelope_path": packet_path})
        self.deliver_expected_card(root, "reviewer.current_node_dispatch")
        router.record_external_event(root, "reviewer_allows_current_node_dispatch")
        self.apply_until_action(root, "relay_current_node_packet")
        packet_runtime.read_packet_body_for_role(root, read_json(root / packet_path), role="worker_a")
        result = packet_runtime.write_result(
            root,
            packet_envelope=read_json(root / packet_path),
            completed_by_role="worker_a",
            completed_by_agent_id=agent_id,
            result_body_text="reviewable result",
            next_recipient="human_like_reviewer",
        )
        result_path = result["result_body_path"].replace("result_body.md", "result_envelope.json")
        router.record_external_event(root, "worker_current_node_result_returned", {"packet_id": packet_id, "result_envelope_path": result_path})
        self.apply_until_action(root, "relay_current_node_result_to_reviewer")
        packet_runtime.read_result_body_for_role(root, read_json(root / result_path), role="human_like_reviewer")
        router.record_external_event(root, "current_node_reviewer_passes_result", {"agent_role_map": {agent_id: "worker_a"}})
        self.complete_parent_backward_replay_if_due(root)
        router.record_external_event(root, "pm_completes_current_node_from_reviewed_result")

    def apply_until_action(self, root: Path, expected_action_type: str, max_steps: int = 12) -> dict:
        for _ in range(max_steps):
            action = router.next_action(root)
            action_type = str(action["action_type"])
            router.apply_action(root, action_type)
            if action_type == expected_action_type:
                return action
        raise AssertionError(f"did not apply {expected_action_type} within {max_steps} router steps")

    def test_bootloader_action_requires_pending_router_action(self) -> None:
        root = self.make_project()

        with self.assertRaises(router.RouterError):
            router.apply_action(root, "ask_startup_questions")

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "load_router")
        self.assertEqual(self.next_and_apply(root)["applied"], "load_router")

    def test_startup_sequence_creates_prompt_isolated_run(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        bootstrap = self.bootstrap_state(root)
        self.assertTrue(bootstrap["router_loaded"])
        self.assertEqual(bootstrap["bootstrap_scope"], "run_scoped")
        self.assertEqual(root / bootstrap["run_root"], run_root)
        self.assertEqual(bootstrap["bootloader_actions"], 14)
        self.assertEqual(bootstrap["router_action_requests"], 14)
        self.assertIsNone(bootstrap["pending_action"])
        self.assertEqual(bootstrap["startup_answers"], STARTUP_ANSWERS)
        self.assertEqual(bootstrap["user_request"], USER_REQUEST)

        self.assertTrue((run_root / "runtime_kit" / "manifest.json").exists())
        self.assertTrue((run_root / "packet_ledger.json").exists())
        self.assertTrue((run_root / "execution_frontier.json").exists())
        self.assertEqual(len(list((run_root / "crew_memory").glob("*.json"))), 6)
        self.assertTrue((run_root / "user_request.json").exists())
        self.assertTrue((run_root / "mailbox" / "outbox" / "user_intake.json").exists())
        self.assertTrue((run_root / "role_core_prompt_delivery.json").exists())

        crew = read_json(run_root / "crew_ledger.json")
        self.assertEqual(len(crew["role_slots"]), 6)
        self.assertNotIn("controller", {slot["role_key"] for slot in crew["role_slots"]})
        self.assertEqual({slot["status"] for slot in crew["role_slots"]}, {"live_agent_started"})
        self.assertTrue(all(slot["agent_id"] for slot in crew["role_slots"]))

    def test_display_plan_is_controller_synced_projection_from_pm_plan(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "sync_display_plan")
        self.assertEqual(action["native_plan_projection"]["items"][0]["id"], "await_pm_route")
        result = router.apply_action(root, "sync_display_plan")
        self.assertEqual(result["host_action"], "replace_visible_plan")
        waiting_plan = read_json(run_root / "display_plan.json")
        self.assertEqual(waiting_plan["source_role"], "controller")
        self.assertEqual(waiting_plan["route_authority"], "none_until_pm_display_plan")

        self.complete_pre_route_gates(root)
        route_plan = read_json(run_root / "display_plan.json")
        self.assertEqual(route_plan["source_role"], "project_manager")
        self.assertEqual(route_plan["source_event"], "pm_writes_route_draft")
        self.assertEqual(route_plan["items"][0]["id"], "node-001")

        self.activate_route(root)
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "sync_display_plan")
        self.assertEqual(action["native_plan_projection"]["items"][0]["status"], "in_progress")
        router.apply_action(root, "sync_display_plan")

        self.deliver_current_node_cards(root)
        node_plan = read_json(run_root / "display_plan.json")
        self.assertEqual(node_plan["source_event"], "pm_writes_node_acceptance_plan")
        self.assertEqual(node_plan["current_node"]["checklist"][0]["id"], "node-001-req")

    def test_startup_waits_for_answers_before_banner_or_run_shell(self) -> None:
        root = self.make_project()

        self.assertEqual(self.next_and_apply(root)["applied"], "load_router")
        self.assertEqual(self.next_and_apply(root)["applied"], "ask_startup_questions")

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "record_startup_answers")
        self.assertTrue(action["requires_user"])
        self.assertEqual(action["requires_payload"], "startup_answers")

        with self.assertRaises(router.RouterError):
            router.apply_action(root, "emit_startup_banner")
        with self.assertRaises(router.RouterError):
            router.apply_action(root, "create_run_shell")

        bootstrap = self.bootstrap_state(root)
        self.assertEqual(bootstrap["startup_state"], "awaiting_answers_stopped")
        self.assertEqual(bootstrap["bootstrap_scope"], "run_scoped")
        self.assertTrue(bootstrap["flags"]["startup_state_written_awaiting_answers"])
        self.assertTrue(bootstrap["flags"]["dialog_stopped_for_answers"])
        self.assertIsNone(bootstrap["startup_answers"])
        self.assertIsNotNone(bootstrap["run_id"])
        self.assertTrue((root / ".flowpilot" / "current.json").exists())
        self.assertTrue((root / bootstrap["run_root"] / "bootstrap" / "startup_state.json").exists())
        self.assertFalse((root / bootstrap["run_root"] / "router_state.json").exists())

    def test_startup_banner_action_and_result_are_user_visible(self) -> None:
        root = self.make_project()
        self.assertEqual(self.next_and_apply(root)["applied"], "load_router")
        self.assertEqual(self.next_and_apply(root)["applied"], "ask_startup_questions")
        self.assertEqual(router.next_action(root)["action_type"], "record_startup_answers")
        router.apply_action(root, "record_startup_answers", {"startup_answers": STARTUP_ANSWERS})

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "emit_startup_banner")
        self.assertTrue(action["display_required"])
        self.assertIn("FLOWPILOT PROMPT-ISOLATED STARTUP", action["display_text"])
        self.assertNotIn("FLOWPILOT_IDENTITY_BOUNDARY_V1", action["display_text"])

        result = router.apply_action(root, "emit_startup_banner")
        self.assertTrue(result["display_required"])
        self.assertIn("FLOWPILOT PROMPT-ISOLATED STARTUP", result["display_text"])

    def test_user_intake_requires_explicit_user_request_and_includes_it(self) -> None:
        root = self.make_project()
        while True:
            action = router.next_action(root)
            action_type = str(action["action_type"])
            if action_type == "record_startup_answers":
                router.apply_action(root, action_type, {"startup_answers": STARTUP_ANSWERS})
            elif action_type == "record_user_request":
                break
            else:
                router.apply_action(root, action_type)

        inferred_request = {**USER_REQUEST, "provenance": "inferred_by_assistant"}
        with self.assertRaisesRegex(router.RouterError, "provenance=explicit_user_request"):
            router.apply_action(root, "record_user_request", {"user_request": inferred_request})

        router.apply_action(root, "record_user_request", {"user_request": USER_REQUEST})
        self.assertEqual(router.next_action(root)["action_type"], "write_user_intake")
        router.apply_action(root, "write_user_intake")

        run_root = root / self.bootstrap_state(root)["run_root"]
        body = (run_root / "packets" / "user_intake" / "packet_body.md").read_text(encoding="utf-8")
        body_payload = json.loads(body[body.index("{") :])
        self.assertEqual(body_payload["user_request"], USER_REQUEST)
        self.assertEqual(body_payload["startup_answers"], STARTUP_ANSWERS)
        self.assertTrue((run_root / "user_request.json").exists())

    def test_background_agents_allow_requires_six_fresh_live_agent_records(self) -> None:
        root = self.make_project()
        while True:
            action = router.next_action(root)
            action_type = str(action["action_type"])
            if action_type == "record_startup_answers":
                router.apply_action(root, action_type, {"startup_answers": STARTUP_ANSWERS})
            elif action_type == "record_user_request":
                router.apply_action(root, action_type, {"user_request": USER_REQUEST})
            elif action_type == "start_role_slots":
                break
            else:
                router.apply_action(root, action_type)

        self.assertTrue(action["requires_host_spawn"])
        self.assertEqual(len(action["role_spawn_request"]), 6)
        with self.assertRaisesRegex(router.RouterError, "role_agents"):
            router.apply_action(root, "start_role_slots")

        payload = self.role_agent_payload(root)
        payload["role_agents"] = payload["role_agents"][:-1]
        with self.assertRaisesRegex(router.RouterError, "missing live role agent records"):
            router.apply_action(root, "start_role_slots", payload)

        payload = self.role_agent_payload(root)
        payload["role_agents"][0]["spawned_for_run_id"] = "run-old"
        with self.assertRaisesRegex(router.RouterError, "spawned_for_run_id"):
            router.apply_action(root, "start_role_slots", payload)

        router.apply_action(root, "start_role_slots", self.role_agent_payload(root))
        run_root = root / self.bootstrap_state(root)["run_root"]
        crew = read_json(run_root / "crew_ledger.json")
        self.assertEqual({slot["status"] for slot in crew["role_slots"]}, {"live_agent_started"})
        self.assertEqual({slot["spawn_result"] for slot in crew["role_slots"]}, {"spawned_fresh_for_task"})

    def test_single_agent_answer_records_authorized_role_continuity_without_live_agents(self) -> None:
        root = self.make_project()
        answers = {**STARTUP_ANSWERS, "background_agents": "single-agent"}
        run_root = self.boot_to_controller(root, startup_answers=answers)
        crew = read_json(run_root / "crew_ledger.json")
        self.assertEqual({slot["status"] for slot in crew["role_slots"]}, {"single_agent_continuity_authorized"})
        self.assertEqual({slot["agent_id"] for slot in crew["role_slots"]}, {None})

    def test_startup_answer_resume_normalizes_old_stop_boundary_state(self) -> None:
        root = self.make_project()
        self.assertEqual(self.next_and_apply(root)["applied"], "load_router")
        self.assertEqual(self.next_and_apply(root)["applied"], "ask_startup_questions")

        state_path = router.bootstrap_state_path(root)
        bootstrap = read_json(state_path)
        bootstrap["flags"]["startup_state_written_awaiting_answers"] = False
        bootstrap["flags"]["dialog_stopped_for_answers"] = False
        bootstrap["startup_state"] = "asking_questions"
        bootstrap["pending_action"] = {
            "action_type": "stop_for_startup_answers",
            "label": "dialog_stopped_for_startup_answers",
        }
        state_path.write_text(json.dumps(bootstrap, indent=2, sort_keys=True), encoding="utf-8")

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "record_startup_answers")
        router.apply_action(root, "record_startup_answers", {"startup_answers": STARTUP_ANSWERS})
        self.assertEqual(router.next_action(root)["action_type"], "emit_startup_banner")

    def test_new_invocation_creates_fresh_run_scoped_bootstrap_over_stale_state(self) -> None:
        root = self.make_project()
        old_run_root = root / ".flowpilot" / "runs" / "run-old-stopped"
        old_run_root.mkdir(parents=True, exist_ok=True)
        (root / ".flowpilot" / "bootstrap").mkdir(parents=True, exist_ok=True)
        (root / ".flowpilot" / "bootstrap" / "startup_state.json").write_text(
            json.dumps(
                {
                    "schema_version": "flowpilot.bootstrap_state.v1",
                    "status": "running",
                    "startup_state": "answers_complete",
                    "startup_answers": {
                        "background_agents": "allow",
                        "scheduled_continuation": "allow",
                        "display_surface": "cockpit",
                    },
                    "flags": {"startup_answers_recorded": True},
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        (root / ".flowpilot" / "current.json").write_text(
            json.dumps(
                {
                    "schema_version": "flowpilot.current.v1",
                    "current_run_id": "run-old-stopped",
                    "current_run_root": ".flowpilot/runs/run-old-stopped",
                    "status": "stopped_by_user",
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        action = router.next_action(root, new_invocation=True)
        self.assertEqual(action["action_type"], "load_router")
        current = read_json(root / ".flowpilot" / "current.json")
        self.assertNotEqual(current["current_run_id"], "run-old-stopped")
        self.assertIn("/bootstrap/startup_state.json", current["startup_bootstrap_path"])
        bootstrap = self.bootstrap_state(root)
        self.assertEqual(bootstrap["bootstrap_scope"], "run_scoped")
        self.assertIsNone(bootstrap["startup_answers"])
        self.assertFalse(bootstrap["flags"]["startup_answers_recorded"])
        self.assertEqual(action["allowed_reads"], [current["startup_bootstrap_path"]])

    def test_record_startup_answers_rejects_naked_inferred_or_invalid_values(self) -> None:
        root = self.make_project()
        self.assertEqual(self.next_and_apply(root)["applied"], "load_router")
        self.assertEqual(self.next_and_apply(root)["applied"], "ask_startup_questions")
        self.assertEqual(router.next_action(root)["action_type"], "record_startup_answers")

        naked_answers = {key: value for key, value in STARTUP_ANSWERS.items() if key != "provenance"}
        with self.assertRaisesRegex(router.RouterError, "provenance=explicit_user_reply"):
            router.apply_action(root, "record_startup_answers", {"startup_answers": naked_answers})

        inferred_answers = {**STARTUP_ANSWERS, "provenance": "inferred_by_assistant"}
        with self.assertRaisesRegex(router.RouterError, "provenance=explicit_user_reply"):
            router.apply_action(root, "record_startup_answers", {"startup_answers": inferred_answers})

        prose_answers = {
            **STARTUP_ANSWERS,
            "background_agents": "No additional background subagents because the assistant inferred a default.",
        }
        with self.assertRaisesRegex(router.RouterError, "background_agents"):
            router.apply_action(root, "record_startup_answers", {"startup_answers": prose_answers})

        extra_answers = {**STARTUP_ANSWERS, "objective": "assistant-filled task summary"}
        with self.assertRaisesRegex(router.RouterError, "unsupported fields"):
            router.apply_action(root, "record_startup_answers", {"startup_answers": extra_answers})

        router.apply_action(root, "record_startup_answers", {"startup_answers": STARTUP_ANSWERS})
        bootstrap = self.bootstrap_state(root)
        self.assertEqual(bootstrap["startup_answers"], STARTUP_ANSWERS)

    def test_cli_accepts_json_after_subcommand(self) -> None:
        parsed = router.parse_args(["--root", "C:/tmp/project", "next", "--json"])
        self.assertEqual(parsed.command, "next")
        self.assertTrue(parsed.json)

        parsed = router.parse_args(
            ["--root", "C:/tmp/project", "apply", "--action-type", "load_router", "--json"]
        )
        self.assertEqual(parsed.command, "apply")
        self.assertEqual(parsed.action_type, "load_router")
        self.assertTrue(parsed.json)

    def test_system_card_delivery_requires_manifest_check(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        first = self.next_after_display_sync(root)
        self.assertEqual(first["action_type"], "check_prompt_manifest")
        self.assertEqual(first["next_card_id"], "pm.core")
        router.apply_action(root, "check_prompt_manifest")

        second = self.next_after_display_sync(root)
        self.assertEqual(second["action_type"], "deliver_system_card")
        self.assertEqual(second["card_id"], "pm.core")
        self.assertEqual(second["from"], "system")
        self.assertEqual(second["issued_by"], "router")
        self.assertEqual(second["delivered_by"], "controller")
        router.apply_action(root, "deliver_system_card")

        state = read_json(run_root / "router_state.json")
        self.assertTrue(state["flags"]["pm_core_delivered"])
        self.assertEqual(state["manifest_checks"], 1)
        self.assertEqual(state["prompt_deliveries"], 1)
        self.assertEqual(state["delivered_cards"][0]["card_id"], "pm.core")

    def test_user_intake_mail_requires_packet_ledger_check_after_pm_cards(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        self.deliver_expected_card(root, "pm.core")
        self.deliver_expected_card(root, "pm.controller_reset_duty")
        self.deliver_expected_card(root, "pm.phase_map")
        self.deliver_expected_card(root, "pm.startup_intake")

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "check_packet_ledger")
        self.assertEqual(action["next_mail_id"], "user_intake")
        router.apply_action(root, "check_packet_ledger")

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "deliver_mail")
        self.assertEqual(action["mail_id"], "user_intake")
        router.apply_action(root, "deliver_mail")

        state = read_json(run_root / "router_state.json")
        packet_ledger = read_json(run_root / "packet_ledger.json")
        self.assertTrue(state["flags"]["user_intake_delivered_to_pm"])
        self.assertEqual(state["ledger_checks"], 1)
        self.assertEqual(state["mail_deliveries"], 1)
        self.assertEqual(packet_ledger["mail"][0]["mail_id"], "user_intake")
        self.assertEqual(packet_ledger["schema_version"], packet_runtime.PACKET_LEDGER_SCHEMA)

    def test_startup_activation_requires_reviewer_facts_before_work(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.deliver_initial_pm_cards_and_user_intake(root)

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_issues_material_and_capability_scan_packets")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_activates_reviewed_route")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_approves_startup_activation", {"decision": "approved"})

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "controller_role_confirmed_from_pm_reset")
        router.record_external_event(root, "pm_first_decision_resets_controller")
        router.record_external_event(root, "controller_role_confirmed_from_pm_reset")

        self.deliver_expected_card(root, "reviewer.startup_fact_check")

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "reviewer_reports_startup_facts", {"passed": True})
        router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            {"reviewed_by_role": "human_like_reviewer", "passed": True},
        )
        self.assertTrue((run_root / "startup" / "startup_fact_report.json").exists())

        self.deliver_expected_card(root, "pm.startup_activation")

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_approves_startup_activation", {"decision": "blocked"})
        router.record_external_event(root, "pm_approves_startup_activation", {"decision": "approved"})
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "write_display_surface_status")
        router.apply_action(root, "write_display_surface_status")

        self.assertTrue((run_root / "startup" / "startup_activation.json").exists())
        self.assertTrue((run_root / "display" / "display_surface.json").exists())
        self.assertTrue((run_root / "diagrams" / "current_route_sign.md").exists())

        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["pm_material_packets_issued"])

    def test_startup_fact_report_accepts_file_backed_envelope_only_payload(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.deliver_initial_pm_cards_and_user_intake(root)
        router.record_external_event(root, "pm_first_decision_resets_controller")
        router.record_external_event(root, "controller_role_confirmed_from_pm_reset")
        self.deliver_expected_card(root, "reviewer.startup_fact_check")

        report_body = {"reviewed_by_role": "human_like_reviewer", "passed": True}
        report_text = json.dumps(report_body, indent=2, sort_keys=True)
        private_report = run_root / "startup" / "reviewer_private_startup_fact_report.json"
        private_report.parent.mkdir(parents=True, exist_ok=True)
        private_report.write_text(report_text, encoding="utf-8")
        report_hash = hashlib.sha256(private_report.read_bytes()).hexdigest()
        report_path = str(private_report.relative_to(root))

        with self.assertRaisesRegex(router.RouterError, "leaked role body fields"):
            router.record_external_event(
                root,
                "reviewer_reports_startup_facts",
                {
                    "report_path": report_path,
                    "report_hash": report_hash,
                    "controller_visibility": "role_output_envelope_only",
                    "blockers": [],
                },
            )

        router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            {
                "report_path": report_path,
                "report_hash": report_hash,
                "controller_visibility": "role_output_envelope_only",
            },
        )

        canonical_report = read_json(run_root / "startup" / "startup_fact_report.json")
        self.assertEqual(
            canonical_report["_role_output_envelope"]["controller_visibility"],
            "role_output_envelope_only",
        )
        self.assertFalse(canonical_report["_role_output_envelope"]["chat_response_body_allowed"])

    def test_material_acceptance_requires_reviewer_sufficiency_and_pm_absorb_card(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_accepts_reviewed_material")

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.material_scan")
        router.apply_action(root, "deliver_system_card")
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "worker_scan_results_returned")

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.record_external_event(root, "reviewer_allows_material_scan_dispatch")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "worker_scan_packet_bodies_delivered_after_dispatch")
        self.apply_next_packet_action(root, "relay_material_scan_packets")
        material_index_path = run_root / "material" / "material_scan_packets.json"
        self.open_packets_and_write_results(root, material_index_path, result_text="insufficient material scan result")
        router.record_external_event(root, "worker_scan_packet_bodies_delivered_after_dispatch")
        router.record_external_event(root, "worker_scan_results_returned")

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "reviewer_reports_material_sufficient")
        self.apply_next_packet_action(root, "relay_material_scan_results_to_reviewer")
        self.open_results_for_reviewer(root, material_index_path)

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "reviewer.material_sufficiency")
        router.apply_action(root, "deliver_system_card")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "reviewer_reports_material_insufficient")
        router.record_external_event(
            root,
            "reviewer_reports_material_insufficient",
            {
                "reviewed_by_role": "human_like_reviewer",
                "direct_material_sources_checked": True,
                "packet_matches_checked_sources": True,
                "pm_ready": False,
                "blockers": ["missing authoritative source"],
            },
        )

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.apply_action(root, str(router.next_action(root)["action_type"]))

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_accepts_reviewed_material")
        router.record_external_event(root, "pm_requests_research_after_material_insufficient")
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["pm_research_requested"])

    def test_research_required_blocks_product_architecture_until_absorbed(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.record_external_event(root, "reviewer_allows_material_scan_dispatch")
        self.apply_next_packet_action(root, "relay_material_scan_packets")
        material_index_path = run_root / "material" / "material_scan_packets.json"
        self.open_packets_and_write_results(root, material_index_path, result_text="research needed")
        router.record_external_event(root, "worker_scan_packet_bodies_delivered_after_dispatch")
        router.record_external_event(root, "worker_scan_results_returned")
        self.apply_next_packet_action(root, "relay_material_scan_results_to_reviewer")
        self.open_results_for_reviewer(root, material_index_path)
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.record_external_event(
            root,
            "reviewer_reports_material_insufficient",
            {
                "reviewed_by_role": "human_like_reviewer",
                "direct_material_sources_checked": True,
                "packet_matches_checked_sources": True,
                "pm_ready": False,
            },
        )
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.record_external_event(root, "pm_requests_research_after_material_insufficient")

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_material_understanding")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_product_function_architecture")

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.research_package")
        router.apply_action(root, "deliver_system_card")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_research_package", {})
        router.record_external_event(root, "pm_writes_research_package", {"decision_question": "which source is authoritative?"})
        router.record_external_event(root, "research_capability_decision_recorded", {"allowed_sources": ["repo"]})

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "worker.research_report")
        router.apply_action(root, "deliver_system_card")
        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "worker_research_report_returned",
                {"completed_by_role": "worker_a", "answers_decision_question": True},
            )
        self.apply_next_packet_action(root, "relay_research_packet")
        research_index_path = run_root / "research" / "research_packet.json"
        self.open_packets_and_write_results(root, research_index_path, result_text="research report result")
        router.record_external_event(
            root,
            "worker_research_report_returned",
            {"completed_by_role": "worker_a", "answers_decision_question": True},
        )
        self.apply_next_packet_action(root, "relay_research_result_to_reviewer")
        self.open_results_for_reviewer(root, research_index_path)

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "reviewer.research_direct_source_check")
        router.apply_action(root, "deliver_system_card")
        router.record_external_event(
            root,
            "reviewer_passes_research_direct_source_check",
            {"reviewed_by_role": "human_like_reviewer", "passed": True},
        )

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.research_absorb_or_mutate")
        router.apply_action(root, "deliver_system_card")
        router.record_external_event(root, "pm_absorbs_reviewed_research")

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.material_understanding")
        router.apply_action(root, "deliver_system_card")
        router.record_external_event(root, "pm_writes_material_understanding", {"material_summary": "research absorbed"})
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["research_result_absorbed_by_pm"])
        self.assertTrue(state["flags"]["material_accepted_by_pm"])
        self.assertTrue((run_root / "pm_material_understanding.json").exists())

    def test_product_architecture_and_root_contract_gate_route_skeleton(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.complete_material_flow(root)

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_activates_reviewed_route")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_product_function_architecture")

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.product_architecture")
        router.apply_action(root, "deliver_system_card")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_product_function_architecture", {"user_task_map": []})
        router.record_external_event(
            root,
            "pm_writes_product_function_architecture",
            {
                "user_task_map": [{"task_id": "task-001", "goal": "ship FlowPilot"}],
                "product_capability_map": [{"capability_id": "cap-001", "behavior": "ship FlowPilot"}],
                "feature_decisions": [{"feature_id": "feature-001", "decision": "must"}],
                "highest_achievable_product_target": {"product_vision": "complete FlowPilot route control"},
                "semantic_fidelity_policy": {"silent_downgrade_forbidden": True},
                "functional_acceptance_matrix": [{"acceptance_id": "root-001"}],
            },
        )
        self.assertTrue((run_root / "product_function_architecture.json").exists())

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_root_acceptance_contract", {"root_requirements": [{"requirement_id": "root-001"}]})

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "product_officer.product_architecture_modelability")
        router.apply_action(root, "deliver_system_card")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "product_officer_passes_product_architecture_modelability", {"passed": True})
        router.record_external_event(
            root,
            "product_officer_passes_product_architecture_modelability",
            {"reviewed_by_role": "product_flowguard_officer", "passed": True},
        )

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "reviewer.product_architecture_challenge")
        router.apply_action(root, "deliver_system_card")
        router.record_external_event(
            root,
            "reviewer_passes_product_architecture",
            {"reviewed_by_role": "human_like_reviewer", "passed": True},
        )

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.root_contract")
        router.apply_action(root, "deliver_system_card")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_root_acceptance_contract", {"root_requirements": []})
        router.record_external_event(
            root,
            "pm_writes_root_acceptance_contract",
            {
                "root_requirements": [
                    {
                        "requirement_id": "root-001",
                        "priority": "must",
                        "proof_required": "mixed",
                    }
                ],
                "proof_matrix": [{"requirement_id": "root-001", "expected_final_replay": True}],
                "selected_scenario_ids": ["terminal_complete_state"],
            },
        )
        self.assertTrue((run_root / "root_acceptance_contract.json").exists())
        self.assertTrue((run_root / "standard_scenario_pack.json").exists())
        self.assertTrue((run_root / "contract.md").exists())

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_activates_reviewed_route")

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "reviewer.root_contract_challenge")
        router.apply_action(root, "deliver_system_card")
        router.record_external_event(
            root,
            "reviewer_passes_root_acceptance_contract",
            {"reviewed_by_role": "human_like_reviewer", "passed": True},
        )

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "product_officer.root_contract_modelability")
        router.apply_action(root, "deliver_system_card")
        router.record_external_event(
            root,
            "product_officer_passes_root_acceptance_contract_modelability",
            {"reviewed_by_role": "product_flowguard_officer", "passed": True},
        )
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_activates_reviewed_route")
        router.record_external_event(root, "pm_freezes_root_acceptance_contract")

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.dependency_policy")
        router.apply_action(root, "deliver_system_card")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_route_draft", {"nodes": [{"node_id": "node-001"}]})
        self.complete_child_skill_gates(root)

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.prior_path_context")
        router.apply_action(root, "deliver_system_card")

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.route_skeleton")
        router.apply_action(root, "deliver_system_card")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_activates_reviewed_route")
        router.record_external_event(
            root,
            "pm_writes_route_draft",
            {
                "nodes": [{"node_id": "node-001"}],
                **self.prior_path_context_review(root, "Route draft considered prior path context before activation."),
            },
        )
        router.record_external_event(root, "process_officer_passes_route_check")
        router.record_external_event(root, "product_officer_passes_route_check")
        router.record_external_event(root, "reviewer_passes_route_check")
        router.record_external_event(root, "pm_activates_reviewed_route")

    def test_child_skill_gates_block_raw_inventory_and_controller_approval(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.complete_material_flow(root)
        self.complete_root_contract_before_child_skill_gates(root)

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.dependency_policy")
        router.apply_action(root, "deliver_system_card")
        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "pm_records_dependency_policy",
                {
                    "host_level_install_requested": True,
                    "explicit_user_approval_recorded": False,
                },
            )
        router.record_external_event(root, "pm_records_dependency_policy", {"allowed_dependency_actions": ["use_existing_local_skill"]})

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_capabilities_manifest", {"raw_inventory_is_authority": True})
        router.record_external_event(
            root,
            "pm_writes_capabilities_manifest",
            {"capabilities": [{"capability_id": "cap-001", "behavior": "route capability"}]},
        )

        self.deliver_expected_card(root, "pm.child_skill_selection")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_child_skill_selection", {"raw_inventory_used_as_authority": True})
        controller_selected_skill = [
            {
                "skill_name": "bad-controller-approved-skill",
                "decision": "required",
                "gates": [{"gate_id": "bad", "required_approver": "controller", "controller_can_approve": True}],
            }
        ]
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_child_skill_selection", {"selected_skills": controller_selected_skill})
        safe_selected_skill = [
            {
                "skill_name": "model-first-function-flow",
                "decision": "required",
                "supported_capabilities": ["cap-001"],
                "gates": [
                    {
                        "gate_id": "process-model",
                        "required_approver": "process_flowguard_officer",
                        "controller_can_approve": False,
                    }
                ],
            }
        ]
        router.record_external_event(root, "pm_writes_child_skill_selection", {"selected_skills": safe_selected_skill})

        self.deliver_expected_card(root, "pm.child_skill_gate_manifest")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_writes_child_skill_gate_manifest", {"selected_skills": controller_selected_skill})

        router.record_external_event(root, "pm_writes_child_skill_gate_manifest", {"selected_skills": safe_selected_skill})
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_approves_child_skill_manifest_for_route")

        self.deliver_expected_card(root, "reviewer.child_skill_gate_manifest_review")
        router.record_external_event(
            root,
            "reviewer_passes_child_skill_gate_manifest",
            {"reviewed_by_role": "human_like_reviewer", "passed": True},
        )
        self.deliver_expected_card(root, "process_officer.child_skill_conformance_model")
        router.record_external_event(
            root,
            "process_officer_passes_child_skill_conformance_model",
            {"reviewed_by_role": "process_flowguard_officer", "passed": True},
        )
        self.deliver_expected_card(root, "product_officer.child_skill_product_fit")
        router.record_external_event(
            root,
            "product_officer_passes_child_skill_product_fit",
            {"reviewed_by_role": "product_flowguard_officer", "passed": True},
        )
        router.record_external_event(root, "pm_approves_child_skill_manifest_for_route")
        router.record_external_event(root, "capability_evidence_synced")
        self.assertTrue((run_root / "capabilities" / "capability_sync.json").exists())

    def test_resume_reentry_loads_state_before_resume_cards(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        for _ in range(4):
            router.apply_action(root, str(router.next_action(root)["action_type"]))
            router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.apply_action(root, str(router.next_action(root)["action_type"]))

        router.record_external_event(root, "heartbeat_or_manual_resume_requested")

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "load_resume_state")
        self.assertFalse(action["sealed_body_reads_allowed"])
        self.assertFalse(action["chat_history_progress_inference_allowed"])
        router.apply_action(root, "load_resume_state")

        resume_evidence = read_json(run_root / "continuation" / "resume_reentry.json")
        self.assertTrue(resume_evidence["stable_launcher"])
        self.assertTrue(resume_evidence["controller_only"])
        self.assertFalse(resume_evidence["controller_may_read_packet_body"])
        self.assertFalse(resume_evidence["controller_may_read_result_body"])
        self.assertFalse(resume_evidence["controller_may_infer_route_progress_from_chat_history"])
        self.assertEqual(resume_evidence["missing_paths"], [])
        self.assertTrue(resume_evidence["roles_restored_or_replaced"])

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "check_prompt_manifest")
        self.assertEqual(action["next_card_id"], "controller.resume_reentry")
        router.apply_action(root, "check_prompt_manifest")
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "deliver_system_card")
        self.assertEqual(action["card_id"], "controller.resume_reentry")
        router.apply_action(root, "deliver_system_card")

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.resume_decision")
        router.apply_action(root, "deliver_system_card")
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertEqual(action["label"], "controller_waits_for_pm_resume_decision")

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_resume_recovery_decision_returned", {"decision": "continue_current_packet_loop"})

        router.record_external_event(
            root,
            "pm_resume_recovery_decision_returned",
            {
                "decision": "continue_current_packet_loop",
                **self.prior_path_context_review(root, "PM resume decision considered current route memory."),
                "controller_reminder": {
                    "controller_only": True,
                    "controller_may_read_sealed_bodies": False,
                    "controller_may_infer_from_chat_history": False,
                    "controller_may_advance_or_close_route": False,
                },
            },
        )
        self.assertTrue((run_root / "continuation" / "pm_resume_decision.json").exists())

    def test_resume_ambiguous_state_blocks_continue_without_recovery_evidence(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        (run_root / "crew_memory" / "worker_b.json").unlink()

        router.record_external_event(root, "heartbeat_or_manual_resume_requested")
        self.assertEqual(self.next_after_display_sync(root)["action_type"], "load_resume_state")
        router.apply_action(root, "load_resume_state")
        self.deliver_expected_card(root, "controller.resume_reentry")
        self.deliver_expected_card(root, "pm.resume_decision")

        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "pm_resume_recovery_decision_returned",
            {
                "decision": "continue_current_packet_loop",
                **self.prior_path_context_review(root, "PM resume decision considered ambiguous current route memory."),
                "controller_reminder": {
                        "controller_only": True,
                        "controller_may_read_sealed_bodies": False,
                        "controller_may_infer_from_chat_history": False,
                        "controller_may_advance_or_close_route": False,
                    },
                },
            )
        router.record_external_event(
            root,
            "pm_resume_recovery_decision_returned",
            {
                "decision": "restore_or_replace_roles_from_memory",
                **self.prior_path_context_review(root, "PM chose role restoration from current route memory and resume evidence."),
                "controller_reminder": {
                    "controller_only": True,
                    "controller_may_read_sealed_bodies": False,
                    "controller_may_infer_from_chat_history": False,
                    "controller_may_advance_or_close_route": False,
                },
            },
        )
        decision = read_json(run_root / "continuation" / "pm_resume_decision.json")
        self.assertTrue(decision["resume_ambiguous"])
        self.assertEqual(decision["decision"], "restore_or_replace_roles_from_memory")

    def test_heartbeat_startup_records_one_minute_active_binding_for_resume_reentry(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root, startup_answers=HEARTBEAT_STARTUP_ANSWERS)
        router.record_external_event(
            root,
            "host_records_heartbeat_binding",
            {
                "route_heartbeat_interval_minutes": 1,
                "host_automation_id": "codex-test-heartbeat",
                "host_automation_verified": True,
            },
        )
        self.complete_startup_activation(root)

        binding_path = run_root / "continuation" / "continuation_binding.json"
        self.assertTrue(binding_path.exists())
        binding = read_json(binding_path)
        self.assertEqual(binding["run_id"], read_json(run_root / "router_state.json")["run_id"])
        self.assertEqual(binding["mode"], "scheduled_heartbeat")
        self.assertEqual(binding["route_heartbeat_interval_minutes"], 1)
        self.assertTrue(binding["heartbeat_active"])
        self.assertEqual(binding["host_automation_id"], "codex-test-heartbeat")
        self.assertTrue(binding["host_automation_verified"])

        router.record_external_event(root, "heartbeat_or_manual_resume_requested", {"source": "heartbeat", "work_chain_status": "broken_or_unknown"})
        self.assertEqual(router.next_action(root)["action_type"], "load_resume_state")
        router.apply_action(root, "load_resume_state")
        resume_evidence = read_json(run_root / "continuation" / "resume_reentry.json")
        self.assertIn("continuation_binding", resume_evidence["loaded_paths"])
        self.assertEqual(resume_evidence["loaded_paths"]["continuation_binding"], self.rel(root, binding_path))

    def test_current_node_packet_relay_requires_reviewer_dispatch(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)

        packet = packet_runtime.create_packet(
            root,
            packet_id="node-packet-without-plan",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="current node work",
            metadata={"route_version": 1},
        )
        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "pm_registers_current_node_packet",
                {
                    "packet_id": "node-packet-without-plan",
                    "packet_envelope_path": packet["body_path"].replace("packet_body.md", "packet_envelope.json"),
                },
            )

        self.deliver_current_node_cards(root)

        packet = packet_runtime.create_packet(
            root,
            packet_id="node-packet-001",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="current node work",
            metadata={"route_version": 1},
        )
        router.record_external_event(
            root,
            "pm_registers_current_node_packet",
            {"packet_id": "node-packet-001", "packet_envelope_path": packet["body_path"].replace("packet_body.md", "packet_envelope.json")},
        )

        action = router.next_action(root)
        if action["action_type"] == "check_prompt_manifest":
            self.assertEqual(action["next_card_id"], "reviewer.current_node_dispatch")
            router.apply_action(root, "check_prompt_manifest")
            action = router.next_action(root)
            self.assertEqual(action["action_type"], "deliver_system_card")
            router.apply_action(root, "deliver_system_card")

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "await_role_decision")

        router.record_external_event(root, "reviewer_allows_current_node_dispatch")
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "check_packet_ledger")
        router.apply_action(root, "check_packet_ledger")
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "relay_current_node_packet")
        self.assertFalse(action["sealed_body_reads_allowed"])
        router.apply_action(root, "relay_current_node_packet")

        envelope = read_json(root / packet["body_path"].replace("packet_body.md", "packet_envelope.json"))
        self.assertEqual(envelope["controller_relay"]["relayed_to_role"], "worker_a")
        self.assertFalse(envelope["controller_relay"]["body_was_read_by_controller"])

    def test_current_node_completion_requires_reviewer_passed_packet_audit(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.deliver_current_node_cards(root)

        packet = packet_runtime.create_packet(
            root,
            packet_id="node-packet-002",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="current node work",
            metadata={"route_version": 1},
        )
        packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
        router.record_external_event(root, "pm_registers_current_node_packet", {"packet_id": "node-packet-002", "packet_envelope_path": packet_path})
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.record_external_event(root, "reviewer_allows_current_node_dispatch")
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.apply_action(root, str(router.next_action(root)["action_type"]))

        relayed_packet = read_json(root / packet_path)
        packet_runtime.read_packet_body_for_role(root, relayed_packet, role="worker_a")
        result = packet_runtime.write_result(
            root,
            packet_envelope=read_json(root / packet_path),
            completed_by_role="worker_a",
            completed_by_agent_id="agent-worker-a-1",
            result_body_text="reviewable result",
            next_recipient="human_like_reviewer",
        )
        result_path = result["result_body_path"].replace("result_body.md", "result_envelope.json")

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_completes_current_node_from_reviewed_result")

        router.record_external_event(root, "worker_current_node_result_returned", {"packet_id": "node-packet-002", "result_envelope_path": result_path})
        self.apply_until_action(root, "relay_current_node_result_to_reviewer")
        relayed_result = read_json(root / result_path)
        packet_runtime.read_result_body_for_role(root, relayed_result, role="human_like_reviewer")

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_completes_current_node_from_reviewed_result")

        router.record_external_event(
            root,
            "current_node_reviewer_passes_result",
            {"agent_role_map": {"agent-worker-a-1": "worker_a"}},
        )
        self.complete_parent_backward_replay_if_due(root)
        router.record_external_event(root, "pm_completes_current_node_from_reviewed_result")

        current = read_json(root / ".flowpilot" / "current.json")
        frontier = read_json(root / current["current_run_root"] / "execution_frontier.json")
        self.assertEqual(frontier["status"], "node_completed_by_pm")
        self.assertIn("node-001", frontier["completed_nodes"])

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_records_final_route_wide_ledger_clean")
        self.complete_evidence_quality_package(root)
        self.complete_final_ledger_and_terminal_replay(root)
        self.deliver_expected_card(root, "pm.closure")

    def test_node_acceptance_plan_requires_pm_high_standard_recheck(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.deliver_expected_card(root, "pm.current_node_loop")
        self.deliver_expected_card(root, "pm.event.node_started")
        self.deliver_expected_card(root, "pm.node_acceptance_plan")

        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "pm_writes_node_acceptance_plan",
                {
                    "node_requirements": [
                        {
                            "requirement_id": "node-001-req",
                            "acceptance_statement": "current node work is complete",
                            "proof_required": "mixed",
                        }
                    ],
                    "experiment_plan": [],
                },
            )

    def test_evidence_quality_package_blocks_stale_and_missing_visual_evidence(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.deliver_current_node_cards(root)

        packet = packet_runtime.create_packet(
            root,
            packet_id="node-packet-quality",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="current node work",
            metadata={"route_version": 1},
        )
        packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
        router.record_external_event(root, "pm_registers_current_node_packet", {"packet_id": "node-packet-quality", "packet_envelope_path": packet_path})
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.record_external_event(root, "reviewer_allows_current_node_dispatch")
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        relayed_packet = read_json(root / packet_path)
        packet_runtime.read_packet_body_for_role(root, relayed_packet, role="worker_a")
        result = packet_runtime.write_result(
            root,
            packet_envelope=read_json(root / packet_path),
            completed_by_role="worker_a",
            completed_by_agent_id="agent-worker-quality",
            result_body_text="reviewable result",
            next_recipient="human_like_reviewer",
        )
        result_path = result["result_body_path"].replace("result_body.md", "result_envelope.json")
        router.record_external_event(root, "worker_current_node_result_returned", {"packet_id": "node-packet-quality", "result_envelope_path": result_path})
        self.apply_until_action(root, "relay_current_node_result_to_reviewer")
        packet_runtime.read_result_body_for_role(root, read_json(root / result_path), role="human_like_reviewer")
        router.record_external_event(root, "current_node_reviewer_passes_result", {"agent_role_map": {"agent-worker-quality": "worker_a"}})
        router.record_external_event(root, "pm_completes_current_node_from_reviewed_result")

        self.deliver_expected_card(root, "pm.evidence_quality_package")
        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "pm_records_evidence_quality_package",
                {"evidence_items": [{"evidence_id": "stale", "status": "stale"}]},
            )
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_records_evidence_quality_package", {"ui_visual_evidence_required": True})
        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "pm_records_evidence_quality_package",
                {
                    "ui_visual_evidence_required": True,
                    "ui_visual_evidence": {"screenshot_paths": ["ui.png"], "old_assets_reused": True},
                },
            )

        router.record_external_event(
            root,
            "pm_records_evidence_quality_package",
            {
                **self.prior_path_context_review(root, "Evidence quality package considered visual evidence and route memory."),
                "evidence_items": [{"evidence_id": "reviewed-result", "status": "current"}],
                "generated_resources": [{"resource_id": "diagram-1", "disposition": "qa_evidence"}],
                "ui_visual_evidence_required": True,
                "ui_visual_evidence": {"screenshot_paths": ["screenshots/current-ui.png"], "old_assets_reused": False},
            },
        )
        self.deliver_expected_card(root, "reviewer.evidence_quality_review")
        router.record_external_event(
            root,
            "reviewer_passes_evidence_quality_package",
            {"reviewed_by_role": "human_like_reviewer", "passed": True},
        )
        self.deliver_expected_card(root, "pm.final_ledger")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_records_final_route_wide_ledger_clean", {"unresolved_count": 1})
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "reviewer_final_backward_replay_passed", {"reviewed_by_role": "human_like_reviewer", "passed": True})
        router.record_external_event(root, "pm_records_final_route_wide_ledger_clean", self.final_ledger_payload(root))
        self.deliver_expected_card(root, "reviewer.final_backward_replay")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "reviewer_final_backward_replay_passed", {"reviewed_by_role": "project_manager", "passed": True})
        router.record_external_event(
            root,
            "reviewer_final_backward_replay_passed",
            self.terminal_replay_payload(root),
        )

    def test_route_mutation_and_final_ledger_have_required_preconditions(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_mutates_route_after_review_block")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_records_final_route_wide_ledger_clean")

        self.activate_route(root)
        self.deliver_current_node_cards(root)
        packet = packet_runtime.create_packet(
            root,
            packet_id="node-packet-003",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="current node work",
            metadata={"route_version": 1},
        )
        packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
        router.record_external_event(root, "pm_registers_current_node_packet", {"packet_id": "node-packet-003", "packet_envelope_path": packet_path})
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.record_external_event(root, "reviewer_allows_current_node_dispatch")
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        relayed_packet = read_json(root / packet_path)
        packet_runtime.read_packet_body_for_role(root, relayed_packet, role="worker_a")
        result = packet_runtime.write_result(
            root,
            packet_envelope=read_json(root / packet_path),
            completed_by_role="worker_a",
            completed_by_agent_id="agent-worker-a-2",
            result_body_text="blocked result",
            next_recipient="human_like_reviewer",
        )
        result_path = result["result_body_path"].replace("result_body.md", "result_envelope.json")
        router.record_external_event(root, "worker_current_node_result_returned", {"packet_id": "node-packet-003", "result_envelope_path": result_path})
        self.apply_until_action(root, "relay_current_node_result_to_reviewer")
        packet_runtime.read_result_body_for_role(root, read_json(root / result_path), role="human_like_reviewer")
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        router.record_external_event(
            root,
            "pm_mutates_route_after_review_block",
            {
                "repair_node_id": "node-001-repair",
                "reason": "reviewer_block",
                "stale_evidence": ["node-packet-003"],
                **self.prior_path_context_review(root, "Route mutation considered blocked node result and stale evidence."),
            },
        )

        current = read_json(root / ".flowpilot" / "current.json")
        frontier = read_json(root / current["current_run_root"] / "execution_frontier.json")
        self.assertEqual(frontier["status"], "route_mutated_repair_pending")
        self.assertEqual(frontier["active_node_id"], "node-001-repair")

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "reviewer_final_backward_replay_passed")

    def test_parent_node_requires_backward_replay_before_completion(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        router.record_external_event(
            root,
            "pm_activates_reviewed_route",
            {
                "route_id": "route-001",
                "active_node_id": "parent-001",
                "route_version": 1,
                "route": {
                    "schema_version": "flowpilot.route.v1",
                    "route_id": "route-001",
                    "route_version": 1,
                    "active_node_id": "parent-001",
                    "nodes": [
                        {
                            "node_id": "parent-001",
                            "status": "active",
                            "title": "Parent node",
                            "child_node_ids": ["child-001"],
                        },
                        {"node_id": "child-001", "status": "completed", "title": "Child node"},
                    ],
                },
            },
        )
        self.deliver_current_node_cards(root)
        packet = packet_runtime.create_packet(
            root,
            packet_id="parent-node-packet",
            from_role="project_manager",
            to_role="worker_a",
            node_id="parent-001",
            body_text="parent node work",
            metadata={"route_version": 1},
        )
        packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
        router.record_external_event(root, "pm_registers_current_node_packet", {"packet_id": "parent-node-packet", "packet_envelope_path": packet_path})
        self.deliver_expected_card(root, "reviewer.current_node_dispatch")
        router.record_external_event(root, "reviewer_allows_current_node_dispatch")
        self.apply_until_action(root, "relay_current_node_packet")
        packet_runtime.read_packet_body_for_role(root, read_json(root / packet_path), role="worker_a")
        result = packet_runtime.write_result(
            root,
            packet_envelope=read_json(root / packet_path),
            completed_by_role="worker_a",
            completed_by_agent_id="agent-worker-a-parent",
            result_body_text="parent node result",
            next_recipient="human_like_reviewer",
        )
        result_path = result["result_body_path"].replace("result_body.md", "result_envelope.json")
        router.record_external_event(root, "worker_current_node_result_returned", {"packet_id": "parent-node-packet", "result_envelope_path": result_path})
        self.apply_until_action(root, "relay_current_node_result_to_reviewer")
        packet_runtime.read_result_body_for_role(root, read_json(root / result_path), role="human_like_reviewer")
        router.record_external_event(
            root,
            "current_node_reviewer_passes_result",
            {"agent_role_map": {"agent-worker-a-parent": "worker_a"}},
        )

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_completes_current_node_from_reviewed_result")

        self.complete_parent_backward_replay_if_due(root)
        router.record_external_event(root, "pm_completes_current_node_from_reviewed_result")
        frontier = read_json(run_root / "execution_frontier.json")
        self.assertIn("parent-001", frontier["completed_nodes"])
        self.assertTrue((run_root / "routes" / "route-001" / "nodes" / "parent-001" / "parent_backward_replay.json").exists())

    def test_parent_backward_non_continue_decision_mutates_route_and_requires_rerun(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        router.record_external_event(
            root,
            "pm_activates_reviewed_route",
            {
                "route_id": "route-001",
                "active_node_id": "parent-001",
                "route_version": 1,
                "route": {
                    "schema_version": "flowpilot.route.v1",
                    "route_id": "route-001",
                    "route_version": 1,
                    "active_node_id": "parent-001",
                    "nodes": [
                        {
                            "node_id": "parent-001",
                            "status": "active",
                            "title": "Parent node",
                            "child_node_ids": ["child-001"],
                        },
                        {"node_id": "child-001", "status": "completed", "title": "Child node"},
                    ],
                },
            },
        )
        self.deliver_current_node_cards(root)
        packet = packet_runtime.create_packet(
            root,
            packet_id="parent-node-noncontinue",
            from_role="project_manager",
            to_role="worker_a",
            node_id="parent-001",
            body_text="parent node work",
            metadata={"route_version": 1},
        )
        packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
        router.record_external_event(root, "pm_registers_current_node_packet", {"packet_id": "parent-node-noncontinue", "packet_envelope_path": packet_path})
        self.deliver_expected_card(root, "reviewer.current_node_dispatch")
        router.record_external_event(root, "reviewer_allows_current_node_dispatch")
        self.apply_until_action(root, "relay_current_node_packet")
        packet_runtime.read_packet_body_for_role(root, read_json(root / packet_path), role="worker_a")
        result = packet_runtime.write_result(
            root,
            packet_envelope=read_json(root / packet_path),
            completed_by_role="worker_a",
            completed_by_agent_id="agent-worker-a-parent-noncontinue",
            result_body_text="parent node result",
            next_recipient="human_like_reviewer",
        )
        result_path = result["result_body_path"].replace("result_body.md", "result_envelope.json")
        router.record_external_event(root, "worker_current_node_result_returned", {"packet_id": "parent-node-noncontinue", "result_envelope_path": result_path})
        self.apply_until_action(root, "relay_current_node_result_to_reviewer")
        packet_runtime.read_result_body_for_role(root, read_json(root / result_path), role="human_like_reviewer")
        router.record_external_event(
            root,
            "current_node_reviewer_passes_result",
            {"agent_role_map": {"agent-worker-a-parent-noncontinue": "worker_a"}},
        )
        self.deliver_expected_card(root, "pm.parent_backward_targets")
        router.record_external_event(root, "pm_builds_parent_backward_targets")
        self.deliver_expected_card(root, "reviewer.parent_backward_replay")
        router.record_external_event(
            root,
            "reviewer_passes_parent_backward_replay",
            {"reviewed_by_role": "human_like_reviewer", "passed": True},
        )
        self.deliver_expected_card(root, "pm.parent_segment_decision")
        router.record_external_event(
            root,
            "pm_records_parent_segment_decision",
            {
                "decision": "repair_existing_child",
                **self.prior_path_context_review(root, "Parent segment repair decision considered prior route memory and replay evidence."),
            },
        )

        frontier = read_json(run_root / "execution_frontier.json")
        self.assertEqual(frontier["status"], "route_mutated_repair_pending")
        self.assertNotEqual(frontier["active_node_id"], "parent-001")
        decision = read_json(run_root / "routes" / "route-001" / "nodes" / "parent-001" / "pm_parent_segment_decision.json")
        self.assertTrue(decision["same_parent_replay_rerun_required"])

    def test_role_event_recording_does_not_let_controller_infer_body_content(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.deliver_initial_pm_cards_and_user_intake(root)

        result = router.record_external_event(
            root,
            "pm_first_decision_resets_controller",
            {"decision_id": "pm-decision-001"},
        )

        self.assertTrue(result["ok"])
        state = read_json(router.run_state_path(router.active_run_root(root)))  # type: ignore[arg-type]
        self.assertTrue(state["flags"]["pm_controller_reset_decision_returned"])
        self.assertEqual(state["events"][0]["payload"], {"decision_id": "pm-decision-001"})

    def test_material_insufficient_event_records_insufficient_state(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_startup_activation(root)
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.record_external_event(root, "reviewer_allows_material_scan_dispatch")
        self.apply_next_packet_action(root, "relay_material_scan_packets")
        run_root = self.run_root_for(root)
        material_index_path = run_root / "material" / "material_scan_packets.json"
        self.open_packets_and_write_results(root, material_index_path, result_text="insufficient material")
        router.record_external_event(root, "worker_scan_packet_bodies_delivered_after_dispatch")
        router.record_external_event(root, "worker_scan_results_returned")
        self.apply_next_packet_action(root, "relay_material_scan_results_to_reviewer")
        self.open_results_for_reviewer(root, material_index_path)
        router.apply_action(root, str(router.next_action(root)["action_type"]))
        router.apply_action(root, str(router.next_action(root)["action_type"]))

        router.record_external_event(
            root,
            "reviewer_reports_material_insufficient",
            {
                "reviewed_by_role": "human_like_reviewer",
                "direct_material_sources_checked": True,
                "packet_matches_checked_sources": True,
                "pm_ready": False,
            },
        )

        state = read_json(router.run_state_path(router.active_run_root(root)))  # type: ignore[arg-type]
        self.assertTrue(state["flags"]["material_review_insufficient"])
        self.assertEqual(state["material_review"], "insufficient")

    def test_final_ledger_rejects_missing_source_of_truth_entries_and_contract_replay(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id="node-packet-final-ledger-preconditions")
        self.complete_evidence_quality_package(root)
        self.deliver_expected_card(root, "pm.final_ledger")

        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "pm_records_final_route_wide_ledger_clean",
                {
                    "pm_owned": True,
                    "entries": [
                        {
                            "entry_id": "route-001:node-001",
                            "node_id": "node-001",
                            "gate_family": "human_review",
                            "required_approver": "human_like_reviewer",
                            "status": "approved",
                            "evidence_paths": [".flowpilot/current-node-result"],
                        }
                    ],
                },
            )

    def test_terminal_replay_requires_reviewed_segments_and_pm_segment_decisions(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id="node-packet-terminal-segments")
        self.complete_evidence_quality_package(root)
        self.deliver_expected_card(root, "pm.final_ledger")
        router.record_external_event(root, "pm_records_final_route_wide_ledger_clean", self.final_ledger_payload(root))
        self.deliver_expected_card(root, "reviewer.final_backward_replay")

        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "reviewer_final_backward_replay_passed",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            )

    def test_final_ledger_records_frozen_contract_replay_source_paths(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id="node-packet-final-ledger-sources")
        self.complete_evidence_quality_package(root)
        self.deliver_expected_card(root, "pm.final_ledger")
        router.record_external_event(root, "pm_records_final_route_wide_ledger_clean", self.final_ledger_payload(root))

        ledger = read_json(run_root / "final_route_wide_gate_ledger.json")
        self.assertEqual(ledger["root_contract_replay"][0]["requirement_id"], "root-001")
        self.assertIn(self.rel(root, run_root / "root_acceptance_contract.json"), ledger["root_contract_replay"][0]["evidence_paths"])
        self.assertEqual(ledger["source_paths"]["root_acceptance_contract"], self.rel(root, run_root / "root_acceptance_contract.json"))
        gate_families = {entry["gate_family"] for entry in ledger["entries"]}
        self.assertIn("root_acceptance", gate_families)
        self.assertIn("route_node", gate_families)
        self.assertIn("child_skill_gate", gate_families)
        self.assertIn("evidence_integrity", gate_families)

    def test_closure_lifecycle_blocks_when_ledgers_are_dirty_after_terminal_replay(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id="node-packet-dirty-closure")
        self.complete_evidence_quality_package(root)
        self.complete_final_ledger_and_terminal_replay(root)

        evidence_ledger_path = run_root / "evidence" / "evidence_ledger.json"
        evidence_ledger = read_json(evidence_ledger_path)
        evidence_ledger["unresolved_count"] = 1
        evidence_ledger_path.write_text(json.dumps(evidence_ledger, indent=2, sort_keys=True), encoding="utf-8")

        action = router.next_action(root)
        card_id = action.get("next_card_id") or action.get("card_id")
        self.assertNotEqual(card_id, "pm.closure")

    def test_manifest_references_existing_system_cards(self) -> None:
        manifest = read_json(ROOT / "skills" / "flowpilot" / "assets" / "runtime_kit" / "manifest.json")
        kit_root = ROOT / "skills" / "flowpilot" / "assets" / "runtime_kit"
        card_ids = set()

        for card in manifest["cards"]:
            card_ids.add(card["id"])
            self.assertEqual(card["source"], "system")
            self.assertEqual(card["issued_by"], "router")
            self.assertTrue((kit_root / card["path"]).exists(), card["path"])

        self.assertIn("pm.core", card_ids)
        self.assertIn("pm.final_ledger", card_ids)
        self.assertIn("pm.evidence_quality_package", card_ids)
        self.assertIn("reviewer.evidence_quality_review", card_ids)
        self.assertIn("reviewer.final_backward_replay", card_ids)
        self.assertIn("controller.resume_reentry", card_ids)
        self.assertIn("pm.resume_decision", card_ids)
        self.assertIn("pm.material_understanding", card_ids)
        self.assertIn("pm.research_package", card_ids)
        self.assertIn("pm.product_architecture", card_ids)
        self.assertIn("pm.root_contract", card_ids)
        self.assertIn("reviewer.research_direct_source_check", card_ids)
        self.assertIn("product_officer.root_contract_modelability", card_ids)
        self.assertIn("reviewer.worker_result_review", card_ids)

    def test_skill_entrypoint_remains_small_router_launcher(self) -> None:
        skill_text = (ROOT / "skills" / "flowpilot" / "SKILL.md").read_text(encoding="utf-8")
        line_count = len(skill_text.splitlines())

        self.assertLess(line_count, 120)
        self.assertIn("flowpilot_router.py", skill_text)
        self.assertIn("Do not read FlowPilot reference files", skill_text)
        self.assertNotIn("Final Route-Wide Gate Ledger", skill_text)


if __name__ == "__main__":
    unittest.main()
