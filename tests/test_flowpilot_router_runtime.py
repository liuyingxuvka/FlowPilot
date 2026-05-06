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
        action = self.next_after_display_sync(root)
        return router.apply_action(root, str(action["action_type"]), self.payload_for_action(action, payload))

    def run_root_for(self, root: Path) -> Path:
        current = read_json(root / ".flowpilot" / "current.json")
        return root / current["current_run_root"]

    def control_blocker_path(self, root: Path, blocker: dict) -> Path:
        return root / str(blocker["blocker_artifact_path"])

    def role_report_envelope(self, root: Path, name: str, body: dict) -> dict:
        return self.role_output_envelope(root, name, body, path_key="report_path", hash_key="report_hash")

    def role_decision_envelope(self, root: Path, name: str, body: dict) -> dict:
        return self.role_output_envelope(root, name, body, path_key="decision_path", hash_key="decision_hash")

    def role_output_envelope(self, root: Path, name: str, body: dict, *, path_key: str, hash_key: str) -> dict:
        run_root = self.run_root_for(root)
        safe_name = name.strip("/").replace("\\", "/")
        output_path = run_root / "test_role_outputs" / f"{safe_name}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {
            path_key: self.rel(root, output_path),
            hash_key: hashlib.sha256(output_path.read_bytes()).hexdigest(),
            "controller_visibility": "role_output_envelope_only",
        }

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
        action = self.next_after_display_sync(root)
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
            router.apply_action(root, "sync_display_plan", self.payload_for_action(action))
            action = router.next_action(root)
        return action

    def payload_for_action(self, action: dict, payload: dict | None = None) -> dict:
        payload = dict(payload or {})
        if action.get("requires_user_dialog_display_confirmation"):
            payload["display_confirmation"] = {
                "action_type": action["action_type"],
                "display_kind": action["display_kind"],
                "display_text_sha256": action["display_text_sha256"],
                "provenance": "controller_user_dialog_render",
                "rendered_to": "user_dialog",
            }
        return payload

    def heartbeat_binding_payload(self, root: Path, automation_id: str = "codex-test-heartbeat") -> dict:
        run_root = self.run_root_for(root)
        run_id = read_json(router.run_state_path(run_root))["run_id"]
        return {
            "route_heartbeat_interval_minutes": 1,
            "host_automation_id": automation_id,
            "host_automation_verified": True,
            "host_automation_proof": {
                "source_kind": "host_receipt",
                "run_id": run_id,
                "host_automation_id": automation_id,
                "route_heartbeat_interval_minutes": 1,
                "heartbeat_bound_to_current_run": True,
            },
        }

    def apply_startup_heartbeat_if_requested(self, root: Path) -> dict | None:
        action = self.next_after_display_sync(root)
        if action["action_type"] != "create_heartbeat_automation":
            return None
        return router.apply_action(root, "create_heartbeat_automation", self.heartbeat_binding_payload(root))

    def handle_pending_control_blocker(self, root: Path) -> bool:
        action = self.next_after_display_sync(root)
        if action["action_type"] != "handle_control_blocker":
            return False
        router.apply_action(root, "handle_control_blocker")
        return True

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
                router.apply_action(root, action_type, self.payload_for_action(action))
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

    def resume_role_agent_payload(self, root: Path, action: dict | None = None) -> dict:
        action = action or self.next_after_display_sync(root)
        records = []
        for request in action["role_rehydration_request"]:
            role = request["role_key"]
            record = {
                "role_key": role,
                "agent_id": f"resume-agent-{request['rehydrated_after_resume_tick_id']}-{role}",
                "rehydration_result": "rehydrated_from_current_run_memory",
                "rehydrated_for_run_id": request["rehydrated_for_run_id"],
                "rehydrated_after_resume_tick_id": request["rehydrated_after_resume_tick_id"],
                "spawned_after_resume_state_loaded": True,
                "core_prompt_path": request["core_prompt_path"],
                "core_prompt_hash": request["core_prompt_hash"],
            }
            if request["role_memory_status"] == "available":
                record.update(
                    {
                        "memory_packet_path": request["memory_packet_path"],
                        "memory_packet_hash": request["memory_packet_hash"],
                        "memory_seeded_from_current_run": True,
                    }
                )
            else:
                record.update(
                    {
                        "memory_missing_acknowledged": True,
                        "replacement_seeded_from_common_run_context": True,
                    }
                )
            if role == "project_manager":
                record["pm_resume_context_delivered"] = True
            records.append(record)
        return {
            "background_agents_capability_status": "available",
            "rehydrated_role_agents": records,
        }

    def bootstrap_state(self, root: Path) -> dict:
        return read_json(router.bootstrap_state_path(root))

    def deliver_initial_pm_cards_and_user_intake(self, root: Path) -> None:
        self.apply_startup_heartbeat_if_requested(root)
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
            self.role_report_envelope(
                root,
                "startup/reviewer_startup_fact_report",
                self.startup_fact_report_body(root),
            ),
        )
        self.deliver_expected_card(root, "pm.startup_activation")
        router.record_external_event(
            root,
            "pm_approves_startup_activation",
            self.role_decision_envelope(
                root,
                "startup/pm_startup_activation",
                {"approved_by_role": "project_manager", "decision": "approved"},
            ),
        )
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "write_display_surface_status")
        self.assertIn("display_text", action)
        self.assertIn("```mermaid", action["display_text"])
        self.assertTrue(action["controller_must_display_text_before_apply"])
        self.assertFalse(action["generated_files_alone_satisfy_chat_display"])
        router.apply_action(root, "write_display_surface_status", self.payload_for_action(action))

    def complete_material_flow(self, root: Path, material_understanding_payload: dict | None = None) -> None:
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
            self.role_report_envelope(
                root,
                "material/reviewer_material_sufficiency",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "direct_material_sources_checked": True,
                    "packet_matches_checked_sources": True,
                    "pm_ready": True,
                },
            ),
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
        router.record_external_event(
            root,
            "pm_writes_material_understanding",
            material_understanding_payload or {"material_summary": "reviewed material accepted"},
        )

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
            self.role_report_envelope(
                root,
                "flowguard/product_architecture_modelability",
                {"reviewed_by_role": "product_flowguard_officer", "passed": True},
            ),
        )

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "reviewer.product_architecture_challenge")
        router.apply_action(root, "deliver_system_card")
        router.record_external_event(
            root,
            "reviewer_passes_product_architecture",
            self.role_report_envelope(
                root,
                "reviews/product_architecture_challenge",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
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
            self.role_report_envelope(
                root,
                "reviews/root_contract_challenge",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "product_officer.root_contract_modelability")
        router.apply_action(root, "deliver_system_card")
        router.record_external_event(
            root,
            "product_officer_passes_root_acceptance_contract_modelability",
            self.role_report_envelope(
                root,
                "flowguard/root_contract_modelability",
                {"reviewed_by_role": "product_flowguard_officer", "passed": True},
            ),
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
        self.complete_route_checks(root)

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
            self.role_report_envelope(
                root,
                "reviews/child_skill_gate_manifest_review",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )

        self.deliver_expected_card(root, "process_officer.child_skill_conformance_model")
        router.record_external_event(
            root,
            "process_officer_passes_child_skill_conformance_model",
            self.role_report_envelope(
                root,
                "flowguard/child_skill_conformance_model",
                {"reviewed_by_role": "process_flowguard_officer", "passed": True},
            ),
        )

        self.deliver_expected_card(root, "product_officer.child_skill_product_fit")
        router.record_external_event(
            root,
            "product_officer_passes_child_skill_product_fit",
            self.role_report_envelope(
                root,
                "flowguard/child_skill_product_fit",
                {"reviewed_by_role": "product_flowguard_officer", "passed": True},
            ),
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

    def complete_route_checks(self, root: Path) -> None:
        self.deliver_expected_card(root, "process_officer.route_process_check")
        router.record_external_event(
            root,
            "process_officer_passes_route_check",
            self.role_report_envelope(
                root,
                "flowguard/route_process_check",
                {"reviewed_by_role": "process_flowguard_officer", "passed": True},
            ),
        )
        self.deliver_expected_card(root, "product_officer.route_product_check")
        router.record_external_event(
            root,
            "product_officer_passes_route_check",
            self.role_report_envelope(
                root,
                "flowguard/route_product_check",
                {"reviewed_by_role": "product_flowguard_officer", "passed": True},
            ),
        )
        self.deliver_expected_card(root, "reviewer.route_challenge")
        router.record_external_event(
            root,
            "reviewer_passes_route_check",
            self.role_report_envelope(
                root,
                "reviews/route_challenge",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
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
            self.role_report_envelope(
                root,
                "reviews/node_acceptance_plan_review",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
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
            self.role_report_envelope(
                root,
                "reviews/parent_backward_replay",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )
        self.deliver_expected_card(root, "pm.parent_segment_decision")
        router.record_external_event(
            root,
            "pm_records_parent_segment_decision",
            self.role_decision_envelope(
                root,
                "decisions/parent_segment_decision",
                {
                    "decision_owner": "project_manager",
                    "decision": "continue",
                    **self.prior_path_context_review(root, "Parent segment decision considered current route memory."),
                },
            ),
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
            self.role_report_envelope(
                root,
                "reviews/evidence_quality_review",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
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
            self.role_report_envelope(
                root,
                "reviews/terminal_backward_replay",
                self.terminal_replay_payload(root),
            ),
        )
        terminal_map = read_json(terminal_map_path)
        ledger = read_json(final_ledger_path)
        self.assertEqual(terminal_map["status"], "passed")
        self.assertTrue(ledger["completion_allowed"])

    def rel(self, root: Path, path: Path) -> str:
        return str(path.relative_to(root)).replace("\\", "/")

    def startup_fact_report_body(self, root: Path) -> dict:
        run_root = self.run_root_for(root)
        return {
            "reviewed_by_role": "human_like_reviewer",
            "passed": True,
            "external_fact_review": {
                "reviewed_by_role": "human_like_reviewer",
                "used_router_mechanical_audit": True,
                "self_attested_ai_claims_accepted_as_proof": False,
                "reviewer_checked_requirement_ids": [
                    "startup_user_answer_authenticity",
                    "live_agent_spawn_freshness",
                    "heartbeat_host_automation_current_run_binding",
                    "cockpit_or_display_fallback_reality",
                ],
                "direct_evidence_paths_checked": [
                    self.rel(root, run_root / "startup_answers.json"),
                    self.rel(root, run_root / "crew_ledger.json"),
                    self.rel(root, run_root / "continuation" / "continuation_binding.json"),
                ],
            },
        }

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
        self.deliver_expected_card(root, "reviewer.worker_result_review")
        packet_runtime.read_result_body_for_role(root, read_json(root / result_path), role="human_like_reviewer")
        router.record_external_event(
            root,
            "current_node_reviewer_passes_result",
            self.role_report_envelope(
                root,
                "reviews/current_node_result",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": True,
                    "agent_role_map": {agent_id: "worker_a"},
                },
            ),
        )
        run_root = self.run_root_for(root)
        runtime_audit_path = run_root / "routes" / "route-001" / "nodes" / "node-001" / "reviews" / "current_node_packet_runtime_audit.json"
        self.assertTrue(runtime_audit_path.exists())
        runtime_audit = read_json(runtime_audit_path)
        self.assertTrue(runtime_audit["passed"])
        self.assertEqual(runtime_audit["router_replacement_scope"], "mechanical_only")
        self.assertFalse(runtime_audit["self_attested_ai_claims_accepted_as_proof"])
        runtime_proof = read_json(root / runtime_audit["router_owned_check_proof_path"])
        self.assertEqual(runtime_proof["source_kind"], "packet_runtime_hash")
        self.assertEqual(runtime_proof["reviewer_replacement_scope"], "mechanical_only")
        self.complete_parent_backward_replay_if_due(root)
        router.record_external_event(root, "pm_completes_current_node_from_reviewed_result")

    def prepare_current_node_result_for_review(
        self,
        root: Path,
        *,
        packet_id: str,
        completed_by_role: str = "worker_a",
        completed_by_agent_id: str = "agent-worker-a",
        deliver_review_card: bool = True,
    ) -> tuple[Path, str, str]:
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
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
            completed_by_role=completed_by_role,
            completed_by_agent_id=completed_by_agent_id,
            result_body_text="reviewable result",
            next_recipient="human_like_reviewer",
            strict_role=completed_by_role == "worker_a",
        )
        result_path = result["result_body_path"].replace("result_body.md", "result_envelope.json")
        router.record_external_event(root, "worker_current_node_result_returned", {"packet_id": packet_id, "result_envelope_path": result_path})
        self.apply_until_action(root, "relay_current_node_result_to_reviewer")
        if deliver_review_card:
            self.deliver_expected_card(root, "reviewer.worker_result_review")
            packet_runtime.read_result_body_for_role(root, read_json(root / result_path), role="human_like_reviewer")
        return run_root, packet_path, result_path

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
        self.assertEqual(action["display_kind"], "startup_waiting_state")
        self.assertIn("FlowPilot Startup Status", action["display_text"])
        self.assertEqual(action["native_plan_projection"]["items"][0]["id"], "await_pm_route")
        result = router.apply_action(root, "sync_display_plan", self.payload_for_action(action))
        self.assertEqual(result["host_action"], "replace_visible_plan")
        self.assertEqual(result["display_kind"], "startup_waiting_state")
        waiting_plan = read_json(run_root / "display_plan.json")
        self.assertEqual(waiting_plan["source_role"], "controller")
        self.assertEqual(waiting_plan["route_authority"], "none_until_pm_display_plan")
        waiting_snapshot = read_json(run_root / "route_state_snapshot.json")
        self.assertEqual(waiting_snapshot["schema_version"], "flowpilot.route_state_snapshot.v1")
        self.assertTrue(waiting_snapshot["authority"]["current_pointer_matches_run"])
        self.assertEqual(waiting_snapshot["active_ui_task_catalog"]["active_tasks"][0]["run_id"], waiting_snapshot["run_id"])

        self.complete_pre_route_gates(root)
        route_plan = read_json(run_root / "display_plan.json")
        self.assertEqual(route_plan["source_role"], "project_manager")
        self.assertEqual(route_plan["source_event"], "pm_writes_route_draft")
        self.assertEqual(route_plan["items"][0]["id"], "node-001")

        index_path = root / ".flowpilot" / "index.json"
        index = read_json(index_path)
        index["runs"].append({"run_id": "run-stale", "run_root": ".flowpilot/runs/run-stale", "status": "running"})
        index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        self.activate_route(root)
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "sync_display_plan")
        self.assertEqual(action["native_plan_projection"]["items"][0]["status"], "in_progress")
        router.apply_action(root, "sync_display_plan", self.payload_for_action(action))
        active_snapshot = read_json(run_root / "route_state_snapshot.json")
        self.assertEqual(active_snapshot["route"]["nodes"][0]["id"], "node-001")
        self.assertTrue(active_snapshot["route"]["nodes"][0]["is_active"])
        self.assertEqual(active_snapshot["authority"]["stale_running_index_entries"][0]["run_id"], "run-stale")
        self.assertEqual(
            active_snapshot["active_ui_task_catalog"]["hidden_non_current_running_index_entries"][0]["run_id"],
            "run-stale",
        )

        self.deliver_current_node_cards(root)
        node_plan = read_json(run_root / "display_plan.json")
        self.assertEqual(node_plan["source_event"], "pm_writes_node_acceptance_plan")
        self.assertEqual(node_plan["current_node"]["checklist"][0]["id"], "node-001-req")

    def test_nonterminal_node_completion_does_not_show_completed_node_as_in_progress(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.complete_material_flow(root)
        self.complete_root_contract_before_child_skill_gates(root)
        self.complete_child_skill_gates(root)
        self.deliver_expected_card(root, "pm.prior_path_context")
        self.deliver_expected_card(root, "pm.route_skeleton")
        router.record_external_event(
            root,
            "pm_writes_route_draft",
            {
                "nodes": [
                    {"node_id": "node-001", "title": "First node"},
                    {"node_id": "node-002", "title": "Second node"},
                ],
                **self.prior_path_context_review(root, "Two-node route draft considered current route memory."),
            },
        )
        self.complete_route_checks(root)
        self.activate_route(root)

        self.complete_leaf_node_with_reviewed_result(root, packet_id="node-packet-nonterminal")

        display_plan = read_json(run_root / "display_plan.json")
        statuses = {item["id"]: item["status"] for item in display_plan["items"]}
        self.assertEqual(statuses["node-001"], "completed")
        self.assertEqual(statuses["node-002"], "in_progress")
        self.assertEqual(list(statuses.values()).count("in_progress"), 1)

    def test_reviewed_route_activation_uses_pm_draft_without_dummy_fallback(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)

        self.activate_route(root)

        flow = read_json(run_root / "routes" / "route-001" / "flow.json")
        self.assertEqual(flow["schema_version"], "flowpilot.route.v1")
        self.assertEqual(flow["source"], "pm_activates_reviewed_route")
        self.assertEqual(flow["nodes"], [{"node_id": "node-001"}])
        self.assertIn("flow.draft.json", flow["activated_from_draft_path"])
        self.assertTrue(flow["activated_from_draft_hash"])
        self.assertNotEqual(flow["nodes"][0].get("title"), "Current node")

    def test_route_check_results_require_router_delivered_check_cards(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.complete_material_flow(root)
        self.complete_root_contract_before_child_skill_gates(root)
        self.complete_child_skill_gates(root)
        self.deliver_expected_card(root, "pm.prior_path_context")
        self.deliver_expected_card(root, "pm.route_skeleton")
        router.record_external_event(
            root,
            "pm_writes_route_draft",
            {
                "nodes": [{"node_id": "node-001"}],
                **self.prior_path_context_review(root, "Route draft considered prior context before route checks."),
            },
        )

        with self.assertRaisesRegex(router.RouterError, "process_officer_route_check_card_delivered"):
            router.record_external_event(
                root,
                "process_officer_passes_route_check",
                self.role_report_envelope(
                    root,
                    "flowguard/route_process_check",
                    {"reviewed_by_role": "process_flowguard_officer", "passed": True},
                ),
            )
        self.deliver_expected_card(root, "process_officer.route_process_check")
        router.record_external_event(
            root,
            "process_officer_passes_route_check",
            self.role_report_envelope(
                root,
                "flowguard/route_process_check",
                {"reviewed_by_role": "process_flowguard_officer", "passed": True},
            ),
        )

        with self.assertRaisesRegex(router.RouterError, "product_officer_route_check_card_delivered"):
            router.record_external_event(
                root,
                "product_officer_passes_route_check",
                self.role_report_envelope(
                    root,
                    "flowguard/route_product_check",
                    {"reviewed_by_role": "product_flowguard_officer", "passed": True},
                ),
            )
        self.deliver_expected_card(root, "product_officer.route_product_check")
        router.record_external_event(
            root,
            "product_officer_passes_route_check",
            self.role_report_envelope(
                root,
                "flowguard/route_product_check",
                {"reviewed_by_role": "product_flowguard_officer", "passed": True},
            ),
        )

        with self.assertRaisesRegex(router.RouterError, "reviewer_route_check_card_delivered"):
            router.record_external_event(
                root,
                "reviewer_passes_route_check",
                self.role_report_envelope(
                    root,
                    "reviews/route_challenge",
                    {"reviewed_by_role": "human_like_reviewer", "passed": True},
                ),
            )
        self.deliver_expected_card(root, "reviewer.route_challenge")
        router.record_external_event(
            root,
            "reviewer_passes_route_check",
            self.role_report_envelope(
                root,
                "reviews/route_challenge",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )

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
        self.assertEqual(action["display_text_format"], "plain_text")
        self.assertTrue(action["controller_must_display_text_before_apply"])
        self.assertTrue(action["requires_user_dialog_display_confirmation"])
        self.assertEqual(action["required_render_target"], "user_dialog")
        self.assertEqual(action["requires_payload"], "display_confirmation")
        self.assertFalse(action["generated_files_alone_satisfy_chat_display"])
        self.assertIn("user dialog", action["controller_display_rule"])
        self.assertIn("```text", action["display_text"])
        self.assertIn("FLOWPILOT STARTUP", action["display_text"])
        self.assertIn("PROMPT-ISOLATED ROUTER MODE", action["display_text"])
        self.assertNotIn("FLOWPILOT_IDENTITY_BOUNDARY_V1", action["display_text"])

        with self.assertRaisesRegex(router.RouterError, "display_confirmation"):
            router.apply_action(root, "emit_startup_banner")

        result = router.apply_action(root, "emit_startup_banner", self.payload_for_action(action))
        self.assertTrue(result["display_required"])
        self.assertTrue(result["controller_must_display_text_before_apply"])
        self.assertEqual(result["dialog_display_confirmation"]["rendered_to"], "user_dialog")
        self.assertFalse(result["generated_files_alone_satisfy_chat_display"])
        self.assertIn("FLOWPILOT STARTUP", result["display_text"])

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
                router.apply_action(root, action_type, self.payload_for_action(action))

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
                router.apply_action(root, action_type, self.payload_for_action(action))

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

    def test_role_output_envelope_writes_body_and_keeps_controller_visible_payload_sealed(self) -> None:
        root = self.make_project()
        envelope = router.write_role_output_envelope(
            root,
            output_path="role_outputs/route_process_check.json",
            body={"reviewed_by_role": "process_flowguard_officer", "passed": True},
            event_name="process_officer_passes_route_check",
            from_role="process_flowguard_officer",
        )

        self.assertEqual(envelope["schema_version"], "flowpilot.role_output_envelope.v1")
        self.assertEqual(envelope["controller_visibility"], "role_output_envelope_only")
        self.assertFalse(envelope["chat_response_body_allowed"])
        self.assertNotIn("passed", envelope)
        loaded = router._load_file_backed_role_payload(root, envelope)
        self.assertTrue(loaded["passed"])
        self.assertEqual(loaded["_role_output_envelope"]["body_path_key"], "report_path")

    def test_pm_material_understanding_accepts_file_backed_memo_payload(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        self.complete_material_flow(
            root,
            self.role_output_envelope(
                root,
                "pm/material_understanding",
                {
                    "material_summary": "file backed material understanding",
                    "route_consequences": ["continue route construction"],
                },
                path_key="memo_path",
                hash_key="memo_hash",
            ),
        )

        memo = read_json(run_root / "pm_material_understanding.json")
        self.assertEqual(memo["material_summary"], "file backed material understanding")
        self.assertEqual(memo["route_consequences"], ["continue route construction"])
        self.assertEqual(memo["_role_output_envelope"]["body_path_key"], "memo_path")

    def test_system_card_delivery_requires_manifest_check(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        first = self.next_after_display_sync(root)
        self.assertEqual(first["action_type"], "check_prompt_manifest")
        self.assertEqual(first["next_card_id"], "pm.core")
        self.assertTrue(first["next_step_contract"]["controller_has_explicit_next"])
        self.assertEqual(first["next_step_contract"]["recipient_role"], "project_manager")
        router.apply_action(root, "check_prompt_manifest")

        second = self.next_after_display_sync(root)
        self.assertEqual(second["action_type"], "deliver_system_card")
        self.assertEqual(second["card_id"], "pm.core")
        self.assertEqual(second["next_step_contract"]["recipient_role"], "project_manager")
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
        with self.assertRaisesRegex(router.RouterError, "file-backed body path"):
            router.record_external_event(
                root,
                "reviewer_reports_startup_facts",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            )
        self.assertTrue(self.handle_pending_control_blocker(root))
        router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(
                root,
                "startup/reviewer_startup_fact_report",
                self.startup_fact_report_body(root),
            ),
        )
        self.assertTrue((run_root / "startup" / "startup_fact_report.json").exists())
        startup_audit = read_json(run_root / "startup" / "startup_mechanical_audit.json")
        self.assertTrue(startup_audit["mechanical_checks_passed"])
        self.assertFalse(startup_audit["self_attested_ai_claims_accepted_as_proof"])
        self.assertEqual(startup_audit["router_replacement_scope"], "mechanical_only")
        proof_path = root / startup_audit["router_owned_check_proof_path"]
        self.assertTrue(proof_path.exists())
        proof = read_json(proof_path)
        self.assertEqual(proof["source_kind"], "router_computed")
        self.assertFalse(proof["self_attested_ai_claims_accepted_as_proof"])

        self.deliver_expected_card(root, "pm.startup_activation")

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_approves_startup_activation", {"decision": "blocked"})
        with self.assertRaisesRegex(router.RouterError, "file-backed body path"):
            router.record_external_event(root, "pm_approves_startup_activation", {"decision": "approved"})
        self.assertTrue(self.handle_pending_control_blocker(root))
        router.record_external_event(
            root,
            "pm_approves_startup_activation",
            self.role_decision_envelope(
                root,
                "startup/pm_startup_activation",
                {"approved_by_role": "project_manager", "decision": "approved"},
            ),
        )
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "write_display_surface_status")
        self.assertIn("FlowPilot Route Sign", action["display_text"])
        self.assertIn("```mermaid", action["display_text"])
        self.assertEqual(action["resolved_display_surface"], "chat-requested")
        router.apply_action(root, "write_display_surface_status", self.payload_for_action(action))

        self.assertTrue((run_root / "startup" / "startup_activation.json").exists())
        self.assertTrue((run_root / "display" / "display_surface.json").exists())
        self.assertTrue((run_root / "diagrams" / "current_route_sign.md").exists())
        self.assertTrue((run_root / "diagrams" / "user-flow-diagram.md").exists())
        self.assertTrue((run_root / "diagrams" / "user-flow-diagram.mmd").exists())
        display_surface = read_json(run_root / "display" / "display_surface.json")
        self.assertTrue(display_surface["chat_displayed_by_controller"])
        self.assertEqual(display_surface["selected_surface"], "chat_route_sign")
        self.assertFalse(display_surface["generated_files_alone_satisfy_chat_display"])

        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["pm_material_packets_issued"])

    def test_cockpit_requested_startup_display_records_chat_fallback_mermaid(self) -> None:
        root = self.make_project()
        cockpit_answers = {**STARTUP_ANSWERS, "display_surface": "cockpit"}
        run_root = self.boot_to_controller(root, cockpit_answers)

        self.complete_startup_activation(root)

        display_surface = read_json(run_root / "display" / "display_surface.json")
        self.assertEqual(display_surface["requested_display_surface"], "cockpit")
        self.assertEqual(display_surface["selected_surface"], "chat_route_sign_fallback")
        self.assertEqual(display_surface["cockpit_status"], "not_started_in_router_runtime")
        self.assertTrue(display_surface["cockpit_probe_required_for_requested_cockpit"])
        self.assertTrue(display_surface["reviewer_fallback_check_required_for_requested_cockpit"])
        self.assertTrue(display_surface["fallback_is_display_only_not_product_ui_completion"])
        self.assertIn("user-flow-diagram.md", display_surface["standard_route_sign_markdown_path"])
        self.assertIn("```mermaid", (run_root / "diagrams" / "current_route_sign.md").read_text(encoding="utf-8"))

    def test_startup_fact_report_accepts_file_backed_envelope_only_payload(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.deliver_initial_pm_cards_and_user_intake(root)
        router.record_external_event(root, "pm_first_decision_resets_controller")
        router.record_external_event(root, "controller_role_confirmed_from_pm_reset")
        self.deliver_expected_card(root, "reviewer.startup_fact_check")

        report_body = self.startup_fact_report_body(root)
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

    def test_router_owned_check_proof_rejects_self_attested_and_stale_audit(self) -> None:
        root = self.make_project()
        run_root = root / ".flowpilot" / "runs" / "run-proof"
        audit_path = run_root / "proof" / "audit.json"
        router.write_json(audit_path, {"schema_version": "test.audit.v1", "run_id": "run-proof", "passed": True})

        with self.assertRaisesRegex(router.RouterError, "unsupported router-owned proof source"):
            router._write_router_owned_check_proof(
                root,
                run_root,
                check_name="unit_proof_check",
                audit_path=audit_path,
                source_kind="self_attested_ai",
                evidence_paths=[audit_path],
            )

        router._write_router_owned_check_proof(
            root,
            run_root,
            check_name="unit_proof_check",
            audit_path=audit_path,
            source_kind="router_computed",
            evidence_paths=[audit_path],
        )
        proof = router._validate_router_owned_check_proof(
            root,
            run_root,
            check_name="unit_proof_check",
            audit_path=audit_path,
        )
        self.assertFalse(proof["self_attested_ai_claims_accepted_as_proof"])

        router.write_json(audit_path, {"schema_version": "test.audit.v1", "run_id": "run-proof", "passed": False})
        with self.assertRaisesRegex(router.RouterError, "audit hash is stale"):
            router._validate_router_owned_check_proof(
                root,
                run_root,
                check_name="unit_proof_check",
                audit_path=audit_path,
            )

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
            self.role_report_envelope(
                root,
                "material/reviewer_material_insufficient",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "direct_material_sources_checked": True,
                    "packet_matches_checked_sources": True,
                    "pm_ready": False,
                    "blockers": ["missing authoritative source"],
                },
            ),
        )

        self.deliver_expected_card(root, "pm.event.reviewer_report")
        self.deliver_expected_card(root, "pm.material_absorb_or_research")

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
            self.role_report_envelope(
                root,
                "material/reviewer_material_insufficient",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "direct_material_sources_checked": True,
                    "packet_matches_checked_sources": True,
                    "pm_ready": False,
                },
            ),
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
            self.role_report_envelope(
                root,
                "research/reviewer_direct_source_check",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
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
        self.assertTrue(self.handle_pending_control_blocker(root))
        router.record_external_event(
            root,
            "product_officer_passes_product_architecture_modelability",
            self.role_report_envelope(
                root,
                "flowguard/product_architecture_modelability",
                {"reviewed_by_role": "product_flowguard_officer", "passed": True},
            ),
        )

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "reviewer.product_architecture_challenge")
        router.apply_action(root, "deliver_system_card")
        router.record_external_event(
            root,
            "reviewer_passes_product_architecture",
            self.role_report_envelope(
                root,
                "reviews/product_architecture_challenge",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
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
            self.role_report_envelope(
                root,
                "reviews/root_contract_challenge",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )

        router.apply_action(root, str(router.next_action(root)["action_type"]))
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "product_officer.root_contract_modelability")
        router.apply_action(root, "deliver_system_card")
        router.record_external_event(
            root,
            "product_officer_passes_root_acceptance_contract_modelability",
            self.role_report_envelope(
                root,
                "flowguard/root_contract_modelability",
                {"reviewed_by_role": "product_flowguard_officer", "passed": True},
            ),
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
        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "process_officer_passes_route_check",
                self.role_report_envelope(
                    root,
                    "flowguard/route_process_check",
                    {"reviewed_by_role": "process_flowguard_officer", "passed": True},
                ),
            )
        self.complete_route_checks(root)
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
            self.role_report_envelope(
                root,
                "reviews/child_skill_gate_manifest_review",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )
        self.deliver_expected_card(root, "process_officer.child_skill_conformance_model")
        router.record_external_event(
            root,
            "process_officer_passes_child_skill_conformance_model",
            self.role_report_envelope(
                root,
                "flowguard/child_skill_conformance_model",
                {"reviewed_by_role": "process_flowguard_officer", "passed": True},
            ),
        )
        self.deliver_expected_card(root, "product_officer.child_skill_product_fit")
        router.record_external_event(
            root,
            "product_officer_passes_child_skill_product_fit",
            self.role_report_envelope(
                root,
                "flowguard/child_skill_product_fit",
                {"reviewed_by_role": "product_flowguard_officer", "passed": True},
            ),
        )
        router.record_external_event(root, "pm_approves_child_skill_manifest_for_route")
        router.record_external_event(root, "capability_evidence_synced")
        self.assertTrue((run_root / "capabilities" / "capability_sync.json").exists())

    def test_resume_reentry_loads_state_before_resume_cards(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        for _ in range(4):
            action = router.next_action(root)
            router.apply_action(root, str(action["action_type"]), self.payload_for_action(action))
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
        self.assertTrue(resume_evidence["role_rehydration_required"])
        self.assertFalse(resume_evidence["roles_restored_or_replaced"])

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "rehydrate_role_agents")
        self.assertTrue(action["requires_host_spawn"])
        self.assertEqual(action["spawn_policy"], "spawn_or_confirm_all_six_live_resume_roles_before_pm_resume_decision")
        self.assertEqual(len(action["role_rehydration_request"]), 6)
        pm_request = next(item for item in action["role_rehydration_request"] if item["role_key"] == "project_manager")
        self.assertTrue(pm_request["pm_resume_context_required"])
        self.assertIn("pm_prior_path_context", pm_request["pm_resume_context_paths"])
        with self.assertRaisesRegex(router.RouterError, "background_agents_capability_status"):
            router.apply_action(root, "rehydrate_role_agents")
        payload = self.resume_role_agent_payload(root, action)
        payload["rehydrated_role_agents"] = payload["rehydrated_role_agents"][:-1]
        with self.assertRaisesRegex(router.RouterError, "missing rehydrated live role agent records"):
            router.apply_action(root, "rehydrate_role_agents", payload)
        action = router.next_action(root)
        payload = self.resume_role_agent_payload(root, action)
        payload["rehydrated_role_agents"][0]["memory_packet_hash"] = "bad"
        with self.assertRaisesRegex(router.RouterError, "memory packet hash mismatch"):
            router.apply_action(root, "rehydrate_role_agents", payload)
        action = router.next_action(root)
        router.apply_action(root, "rehydrate_role_agents", self.resume_role_agent_payload(root, action))
        rehydration = read_json(run_root / "continuation" / "crew_rehydration_report.json")
        self.assertTrue(rehydration["all_six_roles_ready"])
        self.assertTrue(rehydration["current_run_memory_complete"])
        self.assertTrue(rehydration["pm_memory_rehydrated"])

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
        self.assertEqual(action["card_id"], "pm.crew_rehydration_freshness")
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
            self.role_decision_envelope(
                root,
                "continuation/pm_resume_decision",
                {
                    "decision_owner": "project_manager",
                    "decision": "continue_current_packet_loop",
                    **self.prior_path_context_review(root, "PM resume decision considered current route memory."),
                    "controller_reminder": {
                        "controller_only": True,
                        "controller_may_read_sealed_bodies": False,
                        "controller_may_infer_from_chat_history": False,
                        "controller_may_advance_or_close_route": False,
                    },
                },
            ),
        )
        self.assertTrue((run_root / "continuation" / "pm_resume_decision.json").exists())
        decision = read_json(run_root / "continuation" / "pm_resume_decision.json")
        self.assertEqual(
            decision["source_paths"]["crew_rehydration_report"],
            self.rel(root, run_root / "continuation" / "crew_rehydration_report.json"),
        )

    def test_resume_ambiguous_state_blocks_continue_without_recovery_evidence(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        (run_root / "crew_memory" / "worker_b.json").unlink()

        router.record_external_event(root, "heartbeat_or_manual_resume_requested")
        self.assertEqual(self.next_after_display_sync(root)["action_type"], "load_resume_state")
        router.apply_action(root, "load_resume_state")
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "rehydrate_role_agents")
        self.assertEqual(action["memory_missing_role_keys"], ["worker_b"])
        router.apply_action(root, "rehydrate_role_agents", self.resume_role_agent_payload(root, action))
        self.deliver_expected_card(root, "controller.resume_reentry")
        self.deliver_expected_card(root, "pm.crew_rehydration_freshness")
        self.deliver_expected_card(root, "pm.resume_decision")

        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "pm_resume_recovery_decision_returned",
                self.role_decision_envelope(
                    root,
                    "continuation/pm_resume_decision_continue_ambiguous",
                    {
                        "decision_owner": "project_manager",
                        "decision": "continue_current_packet_loop",
                        **self.prior_path_context_review(root, "PM resume decision considered ambiguous current route memory."),
                        "controller_reminder": {
                        "controller_only": True,
                        "controller_may_read_sealed_bodies": False,
                        "controller_may_infer_from_chat_history": False,
                        "controller_may_advance_or_close_route": False,
                        },
                    },
                ),
            )
        router.record_external_event(
            root,
            "pm_resume_recovery_decision_returned",
            self.role_decision_envelope(
                root,
                "continuation/pm_resume_decision_restore",
                {
                    "decision_owner": "project_manager",
                    "decision": "restore_or_replace_roles_from_memory",
                    **self.prior_path_context_review(root, "PM chose role restoration from current route memory and resume evidence."),
                    "controller_reminder": {
                        "controller_only": True,
                        "controller_may_read_sealed_bodies": False,
                        "controller_may_infer_from_chat_history": False,
                        "controller_may_advance_or_close_route": False,
                    },
                },
            ),
        )
        decision = read_json(run_root / "continuation" / "pm_resume_decision.json")
        self.assertTrue(decision["resume_ambiguous"])
        self.assertEqual(decision["decision"], "restore_or_replace_roles_from_memory")

    def test_heartbeat_startup_records_one_minute_active_binding_for_resume_reentry(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root, startup_answers=HEARTBEAT_STARTUP_ANSWERS)
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "create_heartbeat_automation")
        self.assertTrue(action["requires_host_automation"])
        self.assertEqual(action["automation_update_request"]["kind"], "heartbeat")
        self.assertEqual(action["automation_update_request"]["rrule"], "FREQ=MINUTELY;INTERVAL=1")
        self.assertEqual(action["expected_payload"]["route_heartbeat_interval_minutes"], 1)
        self.assertTrue(action["proof_required_before_apply"])
        with self.assertRaisesRegex(router.RouterError, "host_automation_proof"):
            router.apply_action(
                root,
                "create_heartbeat_automation",
                {
                    "route_heartbeat_interval_minutes": 1,
                    "host_automation_id": "codex-test-heartbeat",
                    "host_automation_verified": True,
                },
            )
        router.apply_action(root, "create_heartbeat_automation", self.heartbeat_binding_payload(root))
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
        self.assertEqual(binding["host_automation_proof"]["source_kind"], "host_receipt")

        router.record_external_event(root, "heartbeat_or_manual_resume_requested", {"source": "heartbeat", "work_chain_status": "broken_or_unknown"})
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "load_resume_state")
        self.assertEqual(
            action["resume_next_recipient_from_packet_ledger"]["controller_next_action"],
            "relay_packet_envelope_to_recorded_recipient",
        )
        self.assertEqual(action["resume_next_recipient_from_packet_ledger"]["next_recipient_role"], "project_manager")
        router.apply_action(root, "load_resume_state")
        resume_evidence = read_json(run_root / "continuation" / "resume_reentry.json")
        self.assertIn("continuation_binding", resume_evidence["loaded_paths"])
        self.assertEqual(resume_evidence["loaded_paths"]["continuation_binding"], self.rel(root, binding_path))
        self.assertEqual(resume_evidence["resume_next_recipient_from_packet_ledger"]["source"], "packet_ledger")

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
        resume_next = router._derive_resume_next_recipient_from_packet_ledger(self.run_root_for(root))
        self.assertEqual(resume_next["controller_next_action"], "relay_packet_envelope_to_recorded_recipient")
        self.assertEqual(resume_next["next_recipient_role"], "worker_a")

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
        self.deliver_expected_card(root, "reviewer.worker_result_review")
        relayed_result = read_json(root / result_path)
        packet_runtime.read_result_body_for_role(root, relayed_result, role="human_like_reviewer")

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_completes_current_node_from_reviewed_result")

        router.record_external_event(
            root,
            "current_node_reviewer_passes_result",
            self.role_report_envelope(
                root,
                "reviews/current_node_result_agent_a_1",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": True,
                    "agent_role_map": {"agent-worker-a-1": "worker_a"},
                },
            ),
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

    def test_current_node_packet_and_result_accept_safe_envelope_aliases(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.deliver_current_node_cards(root)

        packet = packet_runtime.create_packet(
            root,
            packet_id="node-packet-aliases",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="current node work",
            metadata={"route_version": 1},
        )
        packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
        packet_file = root / packet_path
        packet_envelope = read_json(packet_file)
        packet_envelope["packet_body_path"] = packet_envelope.pop("body_path")
        packet_envelope["packet_body_hash"] = packet_envelope.pop("body_hash")
        packet_file.write_text(json.dumps(packet_envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        router.record_external_event(root, "pm_registers_current_node_packet", {"packet_id": "node-packet-aliases", "packet_envelope_path": packet_path})
        self.deliver_expected_card(root, "reviewer.current_node_dispatch")
        router.record_external_event(root, "reviewer_allows_current_node_dispatch")
        self.apply_until_action(root, "relay_current_node_packet")
        relayed_packet = packet_runtime.load_envelope(root, packet_path)
        self.assertIn("body_path", relayed_packet)
        packet_runtime.read_packet_body_for_role(root, relayed_packet, role="worker_a")

        result = packet_runtime.write_result(
            root,
            packet_envelope=relayed_packet,
            completed_by_role="worker_a",
            completed_by_agent_id="agent-worker-aliases",
            result_body_text="reviewable result",
            next_recipient="human_like_reviewer",
        )
        result_path = result["result_body_path"].replace("result_body.md", "result_envelope.json")
        result_file = root / result_path
        result_envelope = read_json(result_file)
        result_envelope["body_path"] = result_envelope.pop("result_body_path")
        result_envelope["body_hash"] = result_envelope.pop("result_body_hash")
        result_envelope["to_role"] = result_envelope.pop("next_recipient")
        result_file.write_text(json.dumps(result_envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        router.record_external_event(root, "worker_current_node_result_returned", {"packet_id": "node-packet-aliases", "result_envelope_path": result_path})
        self.apply_until_action(root, "relay_current_node_result_to_reviewer")
        self.deliver_expected_card(root, "reviewer.worker_result_review")
        relayed_result = packet_runtime.load_envelope(root, result_path)
        self.assertIn("result_body_path", relayed_result)
        self.assertEqual(relayed_result["next_recipient"], "human_like_reviewer")
        packet_runtime.read_result_body_for_role(root, relayed_result, role="human_like_reviewer")

        router.record_external_event(
            root,
            "current_node_reviewer_passes_result",
            self.role_report_envelope(
                root,
                "reviews/current_node_result_aliases",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": True,
                    "agent_role_map": {"agent-worker-aliases": "worker_a"},
                },
            ),
        )

    def test_current_node_result_decision_requires_review_card_after_result_relay(self) -> None:
        root = self.make_project()
        _, _, result_path = self.prepare_current_node_result_for_review(
            root,
            packet_id="node-packet-review-card-required",
            deliver_review_card=False,
        )

        with self.assertRaisesRegex(router.RouterError, "reviewer_worker_result_card_delivered"):
            router.record_external_event(
                root,
                "current_node_reviewer_passes_result",
                self.role_report_envelope(
                    root,
                    "reviews/current_node_result_before_card",
                    {
                        "reviewed_by_role": "human_like_reviewer",
                        "passed": True,
                        "agent_role_map": {"agent-worker-a": "worker_a"},
                    },
                ),
            )
        with self.assertRaisesRegex(router.RouterError, "reviewer_worker_result_card_delivered"):
            router.record_external_event(root, "current_node_reviewer_blocks_result")

        self.deliver_expected_card(root, "reviewer.worker_result_review")
        packet_runtime.read_result_body_for_role(root, packet_runtime.load_envelope(root, result_path), role="human_like_reviewer")
        router.record_external_event(
            root,
            "current_node_reviewer_passes_result",
            self.role_report_envelope(
                root,
                "reviews/current_node_result_after_card",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": True,
                    "agent_role_map": {"agent-worker-a": "worker_a"},
                },
            ),
        )

    def test_router_hard_rejection_returns_control_plane_reissue_action(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-control-reissue")

        with self.assertRaises(router.RouterError) as raised:
            router.record_external_event(
                root,
                "current_node_reviewer_passes_result",
                self.role_report_envelope(
                    root,
                    "reviews/current_node_result_missing_passed",
                    {
                        "reviewed_by_role": "human_like_reviewer",
                        "agent_role_map": {"agent-worker-a": "worker_a"},
                    },
                ),
            )

        blocker = raised.exception.control_blocker
        self.assertIsInstance(blocker, dict)
        self.assertEqual(blocker["handling_lane"], "control_plane_reissue")
        self.assertEqual(blocker["target_role"], "human_like_reviewer")
        blocker_path = self.control_blocker_path(root, blocker)
        self.assertTrue(blocker_path.exists())
        saved = read_json(blocker_path)
        self.assertIn("same-role reissue", saved["controller_instruction"])
        self.assertFalse(saved["pm_decision_required"])
        self.assertEqual(saved["skill_observation_reminder"]["suggested_kind"], "controller_compensation")

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "handle_control_blocker")
        self.assertEqual(action["to_role"], "human_like_reviewer")
        self.assertEqual(action["next_step_contract"]["recipient_role"], "human_like_reviewer")
        self.assertFalse(action["next_step_contract"]["sealed_body_reads_allowed"])
        self.assertEqual(action["handling_lane"], "control_plane_reissue")
        self.assertIn("sealed", " ".join(action["controller_forbidden_actions"]))
        self.assertTrue(action["skill_observation_reminder"]["should_consider_recording"])
        router.apply_action(root, "handle_control_blocker")

        delivered = read_json(blocker_path)
        self.assertEqual(delivered["delivery_status"], "delivered")
        self.assertEqual(delivered["delivered_to_role"], "human_like_reviewer")

        router.record_external_event(
            root,
            "current_node_reviewer_passes_result",
            self.role_report_envelope(
                root,
                "reviews/current_node_result_reissued",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": True,
                    "agent_role_map": {"agent-worker-a": "worker_a"},
                },
            ),
        )
        state = read_json(router.run_state_path(router.active_run_root(root)))  # type: ignore[arg-type]
        self.assertIsNone(state["active_control_blocker"])

    def test_already_recorded_event_can_resolve_delivered_control_blocker(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-control-reissue-race")

        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "current_node_reviewer_passes_result",
                self.role_report_envelope(
                    root,
                    "reviews/current_node_result_missing_passed_race",
                    {
                        "reviewed_by_role": "human_like_reviewer",
                        "agent_role_map": {"agent-worker-a": "worker_a"},
                    },
                ),
            )

        reissued_payload = self.role_report_envelope(
            root,
            "reviews/current_node_result_reissued_before_blocker_delivery",
            {
                "reviewed_by_role": "human_like_reviewer",
                "passed": True,
                "agent_role_map": {"agent-worker-a": "worker_a"},
            },
        )
        router.record_external_event(root, "current_node_reviewer_passes_result", reissued_payload)

        state = read_json(router.run_state_path(router.active_run_root(root)))  # type: ignore[arg-type]
        self.assertEqual(state["active_control_blocker"]["delivery_status"], "pending")

        router.next_action(root)
        router.apply_action(root, "handle_control_blocker")
        state = read_json(router.run_state_path(router.active_run_root(root)))  # type: ignore[arg-type]
        self.assertEqual(state["active_control_blocker"]["delivery_status"], "delivered")

        result = router.record_external_event(root, "current_node_reviewer_passes_result", reissued_payload)

        self.assertTrue(result["already_recorded"])
        self.assertTrue(result["control_blocker_resolved"])
        state = read_json(router.run_state_path(router.active_run_root(root)))  # type: ignore[arg-type]
        self.assertIsNone(state["active_control_blocker"])
        self.assertIsNone(state["latest_control_blocker_path"])
        self.assertEqual(len(state["resolved_control_blockers"]), 1)

    def test_already_recorded_event_does_not_resolve_pm_required_control_blocker(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)
        state["flags"]["continuation_binding_recorded"] = True
        state["events"].append(
            {
                "event": "host_records_heartbeat_binding",
                "summary": "Host recorded the active run heartbeat/manual-resume binding before startup fact review.",
                "payload": {},
                "recorded_at": "2026-05-05T00:00:00Z",
            }
        )
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="envelope payload leaked role body fields to Controller: passed",
            event="host_records_heartbeat_binding",
            payload={"from_role": "host", "passed": True},
        )
        self.assertEqual(blocker["handling_lane"], "fatal_protocol_violation")

        self.assertTrue(self.handle_pending_control_blocker(root))
        result = router.record_external_event(root, "host_records_heartbeat_binding")

        self.assertTrue(result["already_recorded"])
        self.assertNotIn("control_blocker_resolved", result)
        state = read_json(state_path)
        self.assertEqual(state["active_control_blocker"]["blocker_id"], blocker["blocker_id"])
        self.assertEqual(state["active_control_blocker"]["delivery_status"], "delivered")
        self.assertEqual(state["latest_control_blocker_path"], blocker["blocker_artifact_path"])

    def test_router_packet_audit_rejection_routes_pm_repair_decision(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(
            root,
            packet_id="node-packet-wrong-role",
            completed_by_role="worker_b",
            completed_by_agent_id="agent-worker-b",
        )

        with self.assertRaises(router.RouterError) as raised:
            router.record_external_event(
                root,
                "current_node_reviewer_passes_result",
                self.role_report_envelope(
                    root,
                    "reviews/current_node_result_wrong_role",
                    {
                        "reviewed_by_role": "human_like_reviewer",
                        "passed": True,
                        "agent_role_map": {"agent-worker-b": "worker_b"},
                    },
                ),
            )

        blocker = raised.exception.control_blocker
        self.assertIsInstance(blocker, dict)
        self.assertEqual(blocker["handling_lane"], "pm_repair_decision_required")
        self.assertEqual(blocker["target_role"], "project_manager")
        self.assertTrue(blocker["pm_decision_required"])
        saved = read_json(self.control_blocker_path(root, blocker))
        self.assertIn("PM", saved["controller_instruction"])
        self.assertIn("contact the worker directly", " ".join(saved["controller_forbidden_actions"]))

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "handle_control_blocker")
        self.assertEqual(action["to_role"], "project_manager")
        self.assertEqual(action["handling_lane"], "pm_repair_decision_required")
        router.apply_action(root, "handle_control_blocker")

        router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(
                root,
                "control_blocks/wrong_role_pm_repair_decision",
                {
                    "decided_by_role": "project_manager",
                    "blocker_id": blocker["blocker_id"],
                    "decision": "repair_not_required",
                },
            ),
        )
        state = read_json(router.run_state_path(router.active_run_root(root)))  # type: ignore[arg-type]
        self.assertIsNone(state["active_control_blocker"])
        self.assertEqual(state["resolved_control_blockers"][-1]["blocker_id"], blocker["blocker_id"])
        self.assertTrue((self.run_root_for(root) / "control_blocks" / f"{blocker['blocker_id']}.pm_repair_decision.json").exists())

    def test_pm_repair_decision_can_repeat_for_new_control_blocker(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)
        first = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="packet group reviewer audit failed: first reviewer audit issue",
            event="reviewer_reports_material_sufficient",
            payload={"report_path": ".flowpilot/runs/test/reviews/first.json"},
        )
        self.assertEqual(first["handling_lane"], "pm_repair_decision_required")
        self.assertTrue(self.handle_pending_control_blocker(root))
        router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(
                root,
                "control_blocks/first_pm_repair_decision",
                {
                    "decided_by_role": "project_manager",
                    "blocker_id": first["blocker_id"],
                    "decision": "repair_not_required",
                },
            ),
        )

        state = read_json(state_path)
        second = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="packet group reviewer audit failed: second reviewer audit issue",
            event="reviewer_reports_material_sufficient",
            payload={"report_path": ".flowpilot/runs/test/reviews/second.json"},
        )
        self.assertEqual(second["handling_lane"], "pm_repair_decision_required")
        self.assertTrue(self.handle_pending_control_blocker(root))
        result = router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(
                root,
                "control_blocks/second_pm_repair_decision",
                {
                    "decided_by_role": "project_manager",
                    "blocker_id": second["blocker_id"],
                    "decision": "repair_not_required",
                },
            ),
        )

        self.assertNotIn("already_recorded", result)
        state = read_json(state_path)
        self.assertIsNone(state["active_control_blocker"])
        self.assertEqual(state["resolved_control_blockers"][-1]["blocker_id"], second["blocker_id"])
        self.assertTrue((run_root / "control_blocks" / f"{second['blocker_id']}.pm_repair_decision.json").exists())

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

    def test_validate_artifact_reports_node_acceptance_missing_fields_together(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        plan_path = root / ".flowpilot" / "partial_node_acceptance_plan.json"
        plan_path.write_text(
            json.dumps(
                {
                    "schema_version": "flowpilot.node_acceptance_plan.v1",
                    "run_id": "run-test",
                    "route_id": "route-001",
                    "route_version": 1,
                    "node_id": "node-001",
                    "node_requirements": [{"requirement_id": "req-001"}],
                    "experiment_plan": [],
                    "high_standard_recheck": {"decision": "proceed"},
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        result = router.validate_artifact(root, "node_acceptance_plan", self.rel(root, plan_path))
        fields = {issue["field"] for issue in result["errors"]}

        self.assertFalse(result["ok"])
        self.assertEqual(result["next_action"], "repair_node_acceptance_plan")
        self.assertIn("prior_path_context_review", fields)
        self.assertIn("prior_path_context_review.source_paths", fields)
        self.assertIn("high_standard_recheck.ideal_outcome", fields)
        self.assertIn("high_standard_recheck.why_current_plan_meets_highest_reasonable_standard", fields)

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
        self.deliver_expected_card(root, "reviewer.worker_result_review")
        packet_runtime.read_result_body_for_role(root, read_json(root / result_path), role="human_like_reviewer")
        router.record_external_event(
            root,
            "current_node_reviewer_passes_result",
            self.role_report_envelope(
                root,
                "reviews/current_node_result_quality",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": True,
                    "agent_role_map": {"agent-worker-quality": "worker_a"},
                },
            ),
        )
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
            self.role_report_envelope(
                root,
                "reviews/evidence_quality_review",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
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
            self.role_report_envelope(
                root,
                "reviews/terminal_backward_replay",
                self.terminal_replay_payload(root),
            ),
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
        self.deliver_expected_card(root, "reviewer.worker_result_review")
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
        self.deliver_expected_card(root, "reviewer.worker_result_review")
        packet_runtime.read_result_body_for_role(root, read_json(root / result_path), role="human_like_reviewer")
        router.record_external_event(
            root,
            "current_node_reviewer_passes_result",
            self.role_report_envelope(
                root,
                "reviews/current_node_parent_result",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": True,
                    "agent_role_map": {"agent-worker-a-parent": "worker_a"},
                },
            ),
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
        self.deliver_expected_card(root, "reviewer.worker_result_review")
        packet_runtime.read_result_body_for_role(root, read_json(root / result_path), role="human_like_reviewer")
        router.record_external_event(
            root,
            "current_node_reviewer_passes_result",
            self.role_report_envelope(
                root,
                "reviews/current_node_parent_noncontinue_result",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": True,
                    "agent_role_map": {"agent-worker-a-parent-noncontinue": "worker_a"},
                },
            ),
        )
        self.deliver_expected_card(root, "pm.parent_backward_targets")
        router.record_external_event(root, "pm_builds_parent_backward_targets")
        self.deliver_expected_card(root, "reviewer.parent_backward_replay")
        router.record_external_event(
            root,
            "reviewer_passes_parent_backward_replay",
            self.role_report_envelope(
                root,
                "reviews/parent_backward_replay_noncontinue",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )
        self.deliver_expected_card(root, "pm.parent_segment_decision")
        router.record_external_event(
            root,
            "pm_records_parent_segment_decision",
            self.role_decision_envelope(
                root,
                "decisions/parent_segment_repair_decision",
                {
                    "decision_owner": "project_manager",
                    "decision": "repair_existing_child",
                    **self.prior_path_context_review(root, "Parent segment repair decision considered prior route memory and replay evidence."),
                },
            ),
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
            self.role_report_envelope(
                root,
                "material/reviewer_material_insufficient",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "direct_material_sources_checked": True,
                    "packet_matches_checked_sources": True,
                    "pm_ready": False,
                },
            ),
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
        self.assertIn("pm.crew_rehydration_freshness", card_ids)
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
