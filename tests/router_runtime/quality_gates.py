from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase


class QualityGatesRuntimeTests(FlowPilotRouterRuntimeTestBase):
    def test_next_effective_node_returns_parent_before_sibling_module_after_last_child(self) -> None:
        route = {
            "route_id": "route-001",
            "nodes": [
                {
                    "node_id": "route-root",
                    "title": "Root",
                    "node_kind": "root",
                    "children": [
                        {
                            "node_id": "module-a",
                            "title": "Module A",
                            "node_kind": "module",
                            "children": [
                                {"node_id": "leaf-a1", "title": "A1", "node_kind": "leaf"},
                                {"node_id": "leaf-a2", "title": "A2", "node_kind": "leaf"},
                            ],
                        },
                        {
                            "node_id": "module-b",
                            "title": "Module B",
                            "node_kind": "module",
                            "children": [
                                {"node_id": "leaf-b1", "title": "B1", "node_kind": "leaf"},
                            ],
                        },
                    ],
                }
            ],
        }

        next_node_id = router._next_effective_node_id(
            route,
            {},
            ["leaf-a1", "leaf-a2"],
            "leaf-a2",
        )
        self.assertEqual(next_node_id, "module-a")

        next_node_after_parent_review = router._next_effective_node_id(
            route,
            {},
            ["leaf-a1", "leaf-a2", "module-a"],
            "module-a",
        )
        self.assertEqual(next_node_after_parent_review, "module-b")
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

        with self.assertRaisesRegex(router.RouterError, "flowguard_operator_route_scope_route_check_card_delivered"):
            router.record_external_event(
                root,
                "flowguard_operator_submits_process_route_model",
                self.role_report_envelope(
                    root,
                    "flowguard/process_route_model",
                    self.route_process_pass_body(),
                ),
            )
        self.deliver_expected_card(root, "flowguard_operator.route_process_check")
        router.record_external_event(
            root,
            "flowguard_operator_submits_process_route_model",
            self.role_report_envelope(
                root,
                "flowguard/process_route_model",
                self.route_process_pass_body(),
            ),
        )
        self.deliver_expected_card(root, "pm.process_route_model_decision")
        router.record_external_event(root, "pm_accepts_process_route_model", self.process_route_model_decision_body())

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
    def test_route_draft_requires_product_behavior_model_report(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.complete_material_flow(root)
        self.complete_root_contract_before_child_skill_gates(root)
        self.complete_child_skill_gates(root)
        (run_root / "flowguard" / "product_behavior_model.json").unlink()
        (run_root / "flowguard" / "product_architecture_modelability.json").unlink()

        self.deliver_expected_card(root, "pm.prior_path_context")
        self.deliver_expected_card(root, "pm.route_skeleton")
        with self.assertRaisesRegex(router.RouterError, "product behavior model report"):
            router.record_external_event(
                root,
                "pm_writes_route_draft",
                {
                    "nodes": [{"node_id": "node-001"}],
                    **self.prior_path_context_review(root, "Route draft attempted without product model."),
                },
            )
    def test_route_check_reports_require_hard_gate_verdict_fields(self) -> None:
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

        self.deliver_expected_card(root, "flowguard_operator.route_process_check")
        with self.assertRaisesRegex(router.RouterError, "process_viability_verdict=pass"):
            router.record_external_event(
                root,
                "flowguard_operator_submits_process_route_model",
                self.role_report_envelope(
                    root,
                    "flowguard/route_process_check_missing_verdict",
                    {"reviewed_by_role": "flowguard_operator", "passed": True},
                ),
            )

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
        self.deliver_expected_card(root, "flowguard_operator.route_process_check")
        with self.assertRaisesRegex(router.RouterError, "product_behavior_model_checked=true"):
            router.record_external_event(
                root,
                "flowguard_operator_submits_process_route_model",
                self.role_report_envelope(
                    root,
                    "flowguard/route_process_check_missing_product_coverage",
                    {
                        "reviewed_by_role": "flowguard_operator",
                        "passed": True,
                        "process_viability_verdict": "pass",
                        "repair_return_policy_checked": True,
                        "serial_execution_model_checked": True,
                        "all_effective_nodes_reachable_in_order": True,
                        "recursive_child_routes_serialized": True,
                    },
                ),
            )
    def test_process_route_repair_required_blocks_activation_and_reopens_pm_route_draft(self) -> None:
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
                **self.prior_path_context_review(root, "Route draft considered prior context before process check."),
            },
        )
        self.deliver_expected_card(root, "flowguard_operator.route_process_check")
        router.record_external_event(
            root,
            "flowguard_operator_requests_process_route_model_repair",
            self.role_report_envelope(
                root,
                "flowguard/route_process_repair_required",
                {
                    "reviewed_by_role": "flowguard_operator",
                    "passed": False,
                    "process_viability_verdict": "repair_required",
                    "product_behavior_model_checked": True,
                    "route_can_reach_product_model": False,
                    "repair_return_policy_checked": False,
                    "recommended_resolution": "PM should redraft route nodes to cover missing product-model recovery path.",
                    "blocking_findings": ["route cannot yet reach modeled recovery state"],
                },
            ),
        )

        with self.assertRaisesRegex(router.RouterError, "reviewer_route_check_passed"):
            router.record_external_event(root, "pm_activates_reviewed_route")
        state = read_json(router.run_state_path(self.run_root_for(root)))
        self.assertFalse(state["flags"]["route_draft_written_by_pm"])
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertIn("pm_writes_route_draft", action["allowed_external_events"])
    def test_host_role_mode_requires_fresh_role_binding_records(self) -> None:
        def scheduled_role_slots_action() -> tuple[Path, Path, dict, dict]:
            root = self.make_project()
            router.run_until_wait(root, new_invocation=True)
            router.apply_action(root, "open_startup_intake_ui", self.startup_intake_payload(root))
            result = router.run_until_wait(root)
            self.assertEqual(result["action_type"], "load_controller_core")
            router.apply_action(root, "load_controller_core", self.payload_for_action(result))
            run_root = self.run_root_for(root)
            controller_ledger = read_json(run_root / "runtime" / "controller_action_ledger.json")
            row = next(item for item in controller_ledger["actions"] if item.get("action_type") == "start_role_slots")
            entry = read_json(run_root / "runtime" / "controller_actions" / f"{row['action_id']}.json")
            return root, run_root, entry["action"], row

        root, run_root, action, row = scheduled_role_slots_action()

        self.assert_controller_receipt_action_projection(action)
        self.assertTrue(action["requires_host_role_binding"])
        self.assertEqual(action["payload_contract"]["name"], "role_slots_startup_receipt")
        self.assertEqual(action["role_binding_open_policy"], "open_runtime_required_role_bindings_before_controller_receipt")
        self.assert_payload_contract_mentions(
            action["payload_contract"],
            "role_bindings[].role_key",
            "role_bindings[].agent_id",
            "role_bindings[].model_policy",
            "role_bindings[].reasoning_effort_policy",
            "role_bindings[].opened_for_run_id",
            "role_bindings[].opened_after_startup_answers",
            "role_bindings[].host_role_binding_receipt.source_kind",
            "exactly one non-duplicate role-binding record",
        )
        self.assertEqual(action["background_role_agent_model_policy"]["model_policy"], "strongest_available")
        self.assertEqual(
            action["background_role_agent_model_policy"]["reasoning_effort_policy"],
            "highest_available",
        )
        self.assertFalse(action["background_role_agent_model_policy"]["inherit_foreground_model_allowed"])
        self.assertEqual(
            {item["model_policy"] for item in action["role_spawn_request"]},
            {"strongest_available"},
        )
        self.assertEqual(
            {item["reasoning_effort_policy"] for item in action["role_spawn_request"]},
            {"highest_available"},
        )
        self.assertEqual(len(action["role_spawn_request"]), 6)

        def assert_role_slots_receipt_blocked(payload_factory, expected_text: str) -> None:
            blocked_root, blocked_run_root, _, blocked_row = scheduled_role_slots_action()
            payload = payload_factory(blocked_root)
            router.record_controller_action_receipt(
                blocked_root,
                action_id=blocked_row["action_id"],
                status="done",
                payload=payload,
            )
            entry = read_json(blocked_run_root / "runtime" / "controller_actions" / f"{blocked_row['action_id']}.json")
            self.assertIn(entry["router_reconciliation_status"], {"blocked", "retry_pending"})
            reconciliation = (
                entry.get("router_reconciliation_blocker")
                if entry["router_reconciliation_status"] == "blocked"
                else entry.get("router_reconciliation")
            )
            self.assertIn(expected_text, json.dumps(reconciliation, sort_keys=True))

        assert_role_slots_receipt_blocked(lambda _: None, "role_bindings")

        def missing_role_payload(blocked_root: Path) -> dict:
            payload = self.role_agent_payload(blocked_root)
            payload["role_bindings"] = payload["role_bindings"][:-1]
            return payload

        assert_role_slots_receipt_blocked(missing_role_payload, "missing live role-binding records")

        def stale_run_payload(blocked_root: Path) -> dict:
            payload = self.role_agent_payload(blocked_root)
            payload["role_bindings"][0]["opened_for_run_id"] = "run-old"
            return payload

        assert_role_slots_receipt_blocked(stale_run_payload, "opened_for_run_id")

        router.record_controller_action_receipt(
            root,
            action_id=row["action_id"],
            status="done",
            payload=self.role_agent_payload(root),
        )
        role_binding = read_json(run_root / "role_binding_ledger.json")
        self.assertEqual({slot["status"] for slot in role_binding["role_slots"]}, {"live_agent_started"})
        self.assertEqual({slot["binding_open_result"] for slot in role_binding["role_slots"]}, {"opened_for_current_task"})
        self.assertEqual({slot["model_policy"] for slot in role_binding["role_slots"]}, {"strongest_available"})
        self.assertEqual({slot["reasoning_effort_policy"] for slot in role_binding["role_slots"]}, {"highest_available"})
        role_io = read_json(run_root / "role_io_protocol_ledger.json")
        self.assertEqual(role_io["schema_version"], "flowpilot.role_io_protocol_ledger.v1")
        self.assertEqual(len(role_io["injection_receipts"]), 6)
        self.assertEqual({item["lifecycle_phase"] for item in role_io["injection_receipts"]}, {"fresh_spawn"})
        self.assertTrue(all((root / item["receipt_path"]).exists() for item in role_io["injection_receipts"]))
    def test_single_agent_answer_records_authorized_role_continuity_without_live_agents(self) -> None:
        root = self.make_project()
        answers = {**STARTUP_ANSWERS, "runtime_role_assistances": "single-agent"}
        run_root = self.boot_to_controller(root, startup_answers=answers)
        role_binding = read_json(run_root / "role_binding_ledger.json")
        self.assertEqual({slot["status"] for slot in role_binding["role_slots"]}, {"single_agent_continuity_authorized"})
        self.assertEqual({slot["agent_id"] for slot in role_binding["role_slots"]}, {None})
    def test_role_output_envelope_hash_survives_same_path_envelope_rewrite(self) -> None:
        root = self.make_project()
        body_path = root / "role_outputs" / "same_path_report.json"
        body = {"reviewed_by_role": "human_like_reviewer", "passed": True}
        router.write_json(body_path, body)
        raw_hash = hashlib.sha256(body_path.read_bytes()).hexdigest()

        loaded = router._load_file_backed_role_payload(
            root,
            {
                "report_path": self.rel(root, body_path),
                "report_hash": raw_hash,
                "controller_visibility": "role_output_envelope_only",
            },
        )
        router.write_json(body_path, loaded)

        reloaded = router._load_file_backed_role_payload(
            root,
            {
                "report_path": self.rel(root, body_path),
                "report_hash": raw_hash,
                "controller_visibility": "role_output_envelope_only",
            },
        )
        self.assertTrue(reloaded["passed"])
        self.assertEqual(
            reloaded["_role_output_envelope"]["body_hash"],
            loaded["_role_output_envelope"]["body_hash"],
        )
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
    def test_reviewer_and_flowguard_operator_gate_event_groups_have_non_pass_outcomes(self) -> None:
        pass_markers = ("passes", "passed", "approves", "allows", "sufficient")
        non_pass_markers = ("blocks", "blocked", "insufficient", "requires_repair", "requests_repair", "protocol_dead_end")
        groups: dict[str, list[str]] = {}
        for event_name, meta in router.EXTERNAL_EVENTS.items():
            required_flag = str(meta.get("requires_flag") or "")
            if not required_flag:
                continue
            role_events = groups.setdefault(required_flag, [])
            if event_name.startswith(("reviewer_", "current_node_reviewer_", "flowguard_operator_route_scope_", "flowguard_operator_product_scope_")):
                role_events.append(event_name)

        pass_only: dict[str, list[str]] = {}
        for required_flag, event_names in groups.items():
            if required_flag == "reviewer_startup_fact_check_card_delivered":
                continue
            classes = {
                "non_pass" if any(marker in event_name for marker in non_pass_markers)
                else "pass" if any(marker in event_name for marker in pass_markers)
                else "other"
                for event_name in event_names
            }
            if "pass" in classes and "non_pass" not in classes:
                pass_only[required_flag] = sorted(event_names)

        self.assertEqual(pass_only, {})
    def test_gate_outcome_block_specs_are_registered_and_reset_stale_passes(self) -> None:
        self.assertTrue(router.GATE_OUTCOME_BLOCK_EVENT_SPECS)
        for event_name, spec in router.GATE_OUTCOME_BLOCK_EVENT_SPECS.items():
            self.assertIn(event_name, router.EXTERNAL_EVENTS)
            self.assertIn(event_name, router.GATE_OUTCOME_BLOCK_EVENTS)
            self.assertTrue(spec.get("checked_paths"))
            reset_flags = tuple(spec.get("reset_flags") or ())
            self.assertTrue(reset_flags)
            self.assertNotIn(router.EXTERNAL_EVENTS[event_name]["flag"], reset_flags)

        for event_name, clear_flags in router.GATE_OUTCOME_PASS_CLEAR_FLAGS.items():
            self.assertIn(event_name, router.EXTERNAL_EVENTS)
            self.assertTrue(clear_flags)
    def test_child_skill_gate_manifest_block_records_repair_without_approval(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.complete_material_flow(root)
        self.complete_root_contract_before_child_skill_gates(root)

        selected_skills = [
            {
                "skill_name": "model-first-function-flow",
                "decision": "required",
                "supported_capabilities": ["cap-001"],
                "gates": [
                    {
                        "gate_id": "process-model",
                        "required_approver": "flowguard_operator",
                        "controller_can_approve": False,
                    }
                ],
            }
        ]
        self.deliver_expected_card(root, "pm.dependency_policy")
        router.record_external_event(root, "pm_records_dependency_policy", {"allowed_dependency_actions": ["use_existing_local_skill"]})
        router.record_external_event(
            root,
            "pm_writes_capabilities_manifest",
            {"capabilities": [{"capability_id": "cap-001", "behavior": "model and gate route work"}]},
        )
        self.deliver_expected_card(root, "pm.child_skill_selection")
        router.record_external_event(root, "pm_writes_child_skill_selection", {"selected_skills": selected_skills})
        self.deliver_expected_card(root, "pm.child_skill_gate_manifest")
        router.record_external_event(root, "pm_writes_child_skill_gate_manifest", {"selected_skills": selected_skills})

        self.deliver_expected_card(root, "reviewer.child_skill_gate_manifest_review")
        router.record_external_event(
            root,
            "reviewer_blocks_child_skill_gate_manifest",
            self.role_report_envelope(
                root,
                "reviews/child_skill_gate_manifest_block",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": False,
                    "blocking_findings": ["selected skills lack compiled standard contracts"],
                    "repair_recommendation": "PM must rewrite manifest with per-gate mappings before rerun.",
                },
            ),
        )

        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["child_skill_manifest_reviewer_blocked"])
        self.assertFalse(state["flags"]["child_skill_manifest_reviewer_passed"])
        self.assertFalse(state["flags"]["child_skill_gate_manifest_written"])
        self.assertFalse(state["flags"]["child_skill_flowguard_operator_route_scope_passed"])
        self.assertFalse(state["flags"]["child_skill_flowguard_operator_product_scope_passed"])
        self.assertFalse(state["flags"]["child_skill_manifest_pm_approved_for_route"])
        self.assertTrue((run_root / "reviews" / "child_skill_gate_manifest_block.json").exists())

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertIn("pm_writes_child_skill_gate_manifest", action["allowed_external_events"])
    def test_child_skill_gate_manifest_repair_pass_clears_active_gate_block(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.complete_material_flow(root)
        self.complete_root_contract_before_child_skill_gates(root)

        selected_skills = [
            {
                "skill_name": "model-first-function-flow",
                "decision": "required",
                "supported_capabilities": ["cap-001"],
                "gates": [
                    {
                        "gate_id": "process-model",
                        "required_approver": "flowguard_operator",
                        "evidence_required": ["model-check-result"],
                        "controller_can_approve": False,
                    }
                ],
            }
        ]
        self.deliver_expected_card(root, "pm.dependency_policy")
        router.record_external_event(root, "pm_records_dependency_policy", {"allowed_dependency_actions": ["use_existing_local_skill"]})
        router.record_external_event(
            root,
            "pm_writes_capabilities_manifest",
            {"capabilities": [{"capability_id": "cap-001", "behavior": "model and gate route work"}]},
        )
        self.deliver_expected_card(root, "pm.child_skill_selection")
        router.record_external_event(root, "pm_writes_child_skill_selection", {"selected_skills": selected_skills})
        self.deliver_expected_card(root, "pm.child_skill_gate_manifest")
        router.record_external_event(root, "pm_writes_child_skill_gate_manifest", {"selected_skills": selected_skills})

        self.deliver_expected_card(root, "reviewer.child_skill_gate_manifest_review")
        router.record_external_event(
            root,
            "reviewer_blocks_child_skill_gate_manifest",
            self.role_report_envelope(
                root,
                "reviews/child_skill_gate_manifest_block",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": False,
                    "blocking_findings": ["selected skills lack compiled standard contracts"],
                    "repair_recommendation": "PM must rewrite manifest with per-gate mappings before rerun.",
                },
            ),
        )

        state = read_json(router.run_state_path(run_root))
        self.assertEqual(state["active_gate_outcome_block"]["event"], "reviewer_blocks_child_skill_gate_manifest")

        router.record_external_event(root, "pm_writes_child_skill_gate_manifest", {"selected_skills": selected_skills})
        self.deliver_expected_card(root, "reviewer.child_skill_gate_manifest_review")
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertIn("reviewer_passes_child_skill_gate_manifest", action["allowed_external_events"])
        self.assertIn("reviewer_blocks_child_skill_gate_manifest", action["allowed_external_events"])

        router.record_external_event(
            root,
            "reviewer_passes_child_skill_gate_manifest",
            self.role_report_envelope(
                root,
                "reviews/child_skill_gate_manifest_review_repaired",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )

        state = read_json(router.run_state_path(run_root))
        self.assertIsNone(state.get("active_gate_outcome_block"))
        self.assertFalse(state["flags"]["child_skill_manifest_reviewer_blocked"])
        self.assertTrue(state["flags"]["child_skill_manifest_reviewer_passed"])
        manifest = read_json(run_root / "child_skill_gate_manifest.json")
        self.assertTrue(manifest["approval"]["reviewer_passed"])
    def test_node_completion_idempotency_is_scoped_to_active_node(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        router.record_external_event(
            root,
            "pm_activates_reviewed_route",
            {
                "route_id": "route-001",
                "active_node_id": "node-001",
                "route_version": 1,
                "route": {
                    "schema_version": "flowpilot.route.v1",
                    "route_id": "route-001",
                    "route_version": 1,
                    "active_node_id": "node-001",
                    "nodes": [
                        {"node_id": "node-001", "status": "active", "title": "First node"},
                        {"node_id": "node-002", "status": "pending", "title": "Second node"},
                    ],
                },
            },
        )

        def complete_active_node(node_id: str, packet_id: str, agent_id: str) -> dict:
            self.deliver_current_node_cards(root)
            packet = packet_runtime.create_packet(
                root,
                packet_id=packet_id,
                from_role="project_manager",
                to_role="worker",
                node_id=node_id,
                body_text=f"{node_id} work",
                metadata={"route_version": 1},
            )
            packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
            router.record_external_event(root, "pm_registers_current_node_packet", {"packet_id": packet_id, "packet_envelope_path": packet_path})
            self.apply_until_action(root, "relay_current_node_packet")
            agent_id, result_path = self.submit_current_node_result_via_active_holder(
                root,
                packet_id=packet_id,
                result_body_text=f"{node_id} result",
            )
            router.record_external_event(root, "worker_current_node_result_returned", {"packet_id": packet_id, "result_envelope_path": result_path})
            self.absorb_current_node_results_with_pm(root, [result_path])
            self.deliver_expected_card(root, "reviewer.worker_result_review")
            router.record_external_event(
                root,
                "current_node_reviewer_passes_result",
                self.role_report_envelope(
                    root,
                    f"reviews/current_node_result_{node_id}",
                    {
                        "reviewed_by_role": "human_like_reviewer",
                        "passed": True,
                        "agent_role_map": {agent_id: "worker"},
                    },
                ),
            )
            self.complete_parent_backward_replay_if_due(root)
            return router.record_external_event(root, "pm_completes_current_node_from_reviewed_result", {"node_id": node_id})

        first_result = complete_active_node("node-001", "node-packet-first", "agent-worker-first")
        self.assertNotIn("already_recorded", first_result)
        first_ledger_path = run_root / "routes" / "route-001" / "nodes" / "node-001" / "node_completion_ledger.json"
        self.assertTrue(first_ledger_path.exists())
        frontier = read_json(run_root / "execution_frontier.json")
        self.assertEqual(frontier["active_node_id"], "node-002")
        self.assertIn("node-001", frontier["completed_nodes"])
        self.assertFalse(read_json(router.run_state_path(run_root))["flags"]["node_completed_by_pm"])

        stale_state = read_json(router.run_state_path(run_root))
        stale_state["flags"]["node_completed_by_pm"] = True
        stale_state["flags"]["node_completion_ledger_updated"] = False
        router.run_state_path(run_root).write_text(json.dumps(stale_state, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        second_result = complete_active_node("node-002", "node-packet-second", "agent-worker-second")
        self.assertNotIn("already_recorded", second_result)
        second_ledger_path = run_root / "routes" / "route-001" / "nodes" / "node-002" / "node_completion_ledger.json"
        self.assertTrue(second_ledger_path.exists())
        frontier = read_json(run_root / "execution_frontier.json")
        self.assertEqual(frontier["active_node_id"], "node-002")
        self.assertEqual(frontier["status"], "node_completed_by_pm")
        self.assertIn("node-002", frontier["completed_nodes"])
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
    def test_gate_decision_event_records_ledger_and_state(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        body = self.gate_decision_body(root)
        router.record_external_event(
            root,
            "role_records_gate_decision",
            self.role_decision_envelope(root, "gate_decisions/quality_gate_001", body),
        )

        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["gate_decision_recorded"])
        self.assertEqual(len(state["gate_decisions"]), 1)
        self.assertEqual(state["gate_decisions"][0]["gate_id"], "quality-gate-001")
        self.assertEqual(state["gate_decisions"][0]["decision"], "pass")
        decision_record = read_json(root / state["gate_decisions"][0]["decision_path"])
        self.assertEqual(decision_record["schema_version"], "flowpilot.gate_decision_record.v1")
        self.assertEqual(decision_record["gate_decision"]["owner_role"], "human_like_reviewer")
        ledger = read_json(run_root / "gate_decisions" / "gate_decision_ledger.json")
        self.assertEqual(ledger["gate_decision_count"], 1)
    def test_gate_decision_same_identity_replay_is_already_recorded(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        envelope = self.role_decision_envelope(
            root,
            "gate_decisions/replayed_quality_gate",
            self.gate_decision_body(root, gate_id="replayed-quality-gate"),
        )

        router.record_external_event(root, "role_records_gate_decision", envelope)
        state = read_json(router.run_state_path(run_root))
        record_path = root / state["gate_decisions"][0]["decision_path"]
        first_recorded_at = read_json(record_path)["recorded_at"]

        replay = router.record_external_event(root, "role_records_gate_decision", envelope)

        self.assertTrue(replay["already_recorded"])
        self.assertEqual(read_json(record_path)["recorded_at"], first_recorded_at)
        state = read_json(router.run_state_path(run_root))
        self.assertEqual(len(state["gate_decisions"]), 1)
        processed = state["external_event_idempotency"]["processed"]["role_records_gate_decision"]
        self.assertEqual(len(processed), 1)
    def test_gate_decision_rejects_mechanical_contradictions(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        body = self.gate_decision_body(root, blocking=True)

        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "role_records_gate_decision",
                self.role_decision_envelope(root, "gate_decisions/contradictory_pass", body),
            )
    def test_validate_artifact_reports_gate_decision_issues_together(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        bad = self.gate_decision_body(root)
        bad.pop("reason")
        bad["owner_role"] = "controller"
        bad["blocking"] = True
        gate_path = root / ".flowpilot" / "bad_gate_decision.json"
        gate_path.write_text(json.dumps(bad, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        result = router.validate_artifact(root, "gate_decision", self.rel(root, gate_path))
        fields = {issue["field"] for issue in result["errors"]}

        self.assertFalse(result["ok"])
        self.assertEqual(result["next_action"], "repair_gate_decision")
        self.assertIn("reason", fields)
        self.assertIn("owner_role", fields)
        self.assertIn("blocking", fields)
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
            to_role="worker",
            node_id="node-001",
            body_text="current node work",
            metadata={"route_version": 1},
        )
        packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
        router.record_external_event(root, "pm_registers_current_node_packet", {"packet_id": "node-packet-quality", "packet_envelope_path": packet_path})
        self.apply_until_action(root, "relay_current_node_packet")
        agent_id, result_path = self.submit_current_node_result_via_active_holder(
            root,
            packet_id="node-packet-quality",
            result_body_text="reviewable result",
        )
        router.record_external_event(root, "worker_current_node_result_returned", {"packet_id": "node-packet-quality", "result_envelope_path": result_path})
        self.absorb_current_node_results_with_pm(root, [result_path])
        self.deliver_expected_card(root, "reviewer.worker_result_review")
        router.record_external_event(
            root,
            "current_node_reviewer_passes_result",
            self.role_report_envelope(
                root,
                "reviews/current_node_result_quality",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": True,
                    "agent_role_map": {agent_id: "worker"},
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
    def test_root_contract_freeze_requires_clean_self_interrogation_records(self) -> None:
        root = self.make_project()
        run_root = root / ".flowpilot" / "runs" / "run-001"
        (run_root / "reviews").mkdir(parents=True, exist_ok=True)
        (run_root / "contract.md").write_text("# contract\n", encoding="utf-8")
        (run_root / "standard_scenario_pack.json").write_text(json.dumps({"schema_version": "flowpilot.standard_scenario_pack.v1"}) + "\n", encoding="utf-8")
        (run_root / "reviews" / "root_contract_challenge.json").write_text(json.dumps({"passed": True}) + "\n", encoding="utf-8")
        (run_root / "root_acceptance_contract.json").write_text(
            json.dumps(
                {
                    "schema_version": "flowpilot.root_acceptance_contract.v1",
                    "completion_policy": {"unresolved_residual_risks_allowed": False},
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        state = {"run_id": "run-001", "flags": {}}

        with self.assertRaisesRegex(router.RouterError, "self-interrogation index is missing"):
            router._freeze_root_acceptance_contract(root, run_root, state)  # type: ignore[attr-defined]

        (root / ".flowpilot").mkdir(exist_ok=True)
        (root / ".flowpilot" / "current.json").write_text(
            json.dumps({"current_run_root": ".flowpilot/runs/run-001"}) + "\n",
            encoding="utf-8",
        )
        self.write_self_interrogation_record(root, "startup", source_path=run_root / "contract.md")
        self.write_self_interrogation_record(root, "product_architecture", clean=False, source_path=run_root / "root_acceptance_contract.json")

        with self.assertRaisesRegex(router.RouterError, "unresolved for a hard/current"):
            router._freeze_root_acceptance_contract(root, run_root, state)  # type: ignore[attr-defined]

        self.write_self_interrogation_record(root, "product_architecture", source_path=run_root / "root_acceptance_contract.json")
        router._freeze_root_acceptance_contract(root, run_root, state)  # type: ignore[attr-defined]
        self.assertEqual(read_json(run_root / "root_acceptance_contract.json")["status"], "frozen")
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
        self.assertIn("pm.role_binding_recovery_freshness", card_ids)
        self.assertIn("pm.resume_decision", card_ids)
        self.assertIn("pm.role_work_request", card_ids)
        self.assertIn("pm.material_understanding", card_ids)
        self.assertIn("pm.research_package", card_ids)
        self.assertIn("pm.product_architecture", card_ids)
        self.assertIn("pm.root_contract", card_ids)
        self.assertIn("reviewer.research_direct_source_check", card_ids)
        self.assertIn("flowguard_operator_product_scope.root_contract_modelability", card_ids)
        self.assertIn("reviewer.worker_result_review", card_ids)
    def test_reviewer_block_events_are_registered_in_external_taxonomy(self) -> None:
        self.assertNotIn("reviewer_blocks_current_node_dispatch", router.EXTERNAL_EVENTS)
        self.assertNotIn("flowguard_operator_product_scope_model_report", router.EXTERNAL_EVENTS)
        self.assertEqual(
            router.EXTERNAL_EVENTS["router_direct_material_scan_dispatch_recheck_blocked"]["flag"],
            "material_scan_dispatch_recheck_blocked",
        )
        self.assertEqual(router.EXTERNAL_EVENTS["reviewer_blocks_node_acceptance_plan"]["flag"], "node_acceptance_plan_review_blocked")
    def test_model_miss_review_block_flags_stay_in_sync(self) -> None:
        expected_flags = set(router.MODEL_MISS_REVIEW_BLOCK_FLAGS)
        event_flags = {
            router.EXTERNAL_EVENTS[event_name]["flag"]
            for event_name in router.MODEL_MISS_REVIEW_BLOCK_EVENTS
        }
        card_flags_by_id = {
            entry["card_id"]: set(entry.get("requires_any_flag", []))
            for entry in router.SYSTEM_CARD_SEQUENCE
            if entry.get("card_id") in {"pm.model_miss_triage", "pm.review_repair", "pm.event.reviewer_blocked"}
        }
        repair_writer_flags = set(router.MODEL_MISS_ROUTE_MUTATION_BLOCK_FLAGS) | set(
            router.MODEL_MISS_MATERIAL_DISPATCH_REPAIR_FLAGS
        )

        self.assertEqual(event_flags, expected_flags)
        self.assertEqual(repair_writer_flags, expected_flags)
        self.assertEqual(set(card_flags_by_id), {"pm.model_miss_triage", "pm.review_repair", "pm.event.reviewer_blocked"})
        for card_flags in card_flags_by_id.values():
            self.assertEqual(card_flags, expected_flags)
