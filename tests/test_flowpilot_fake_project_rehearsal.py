from __future__ import annotations

import importlib
import json
import tempfile
from pathlib import Path
import sys
import unittest
from unittest import mock


fake_project_cli = importlib.import_module("simulations.flowpilot_fake_project_rehearsal_cli")
fake_project_runner = importlib.import_module("simulations.run_flowpilot_fake_project_rehearsal_checks")
CORE_RUNTIME = fake_project_cli.ASSETS / "flowpilot_core_runtime"
if str(CORE_RUNTIME) not in sys.path:
    sys.path.insert(0, str(CORE_RUNTIME))
packet_result_contracts = importlib.import_module("packet_result_contracts")


def unit_open_result_fixture(
    packet: dict[str, object],
    *,
    result_skeleton: dict[str, object] | None = None,
    branch_valid_shapes: dict[str, object] | None = None,
) -> dict[str, object]:
    envelope = packet.get("envelope") if isinstance(packet.get("envelope"), dict) else packet
    effective = packet_result_contracts.effective_result_contract_from_envelope(envelope)
    packet_id = str(packet.get("packet_id") or "packet-unit-open")
    packet_kind = str(envelope.get("packet_kind") or "task")
    route_scope = str(envelope.get("route_scope") or "")
    responsibility = {
        "flowguard_check": "flowguard_operator",
        "review": "reviewer",
    }.get(packet_kind, "pm")
    family_id = packet_result_contracts.packet_result_family_id(envelope)
    report_contract = {
        "output_contract": {},
        "result_contract_profile_ids": list(effective["result_contract_profile_ids"]),
        "result_contract_profile_bindings": json.loads(json.dumps(effective["result_contract_profile_bindings"])),
        "required_result_body_fields": list(effective["required_fields"]),
        "required_child_fields": list(effective["required_child_fields"]),
        "explicit_array_fields": list(effective["explicit_array_fields"]),
        "non_empty_array_fields": list(effective["non_empty_array_fields"]),
        "allowed_value_options": json.loads(json.dumps(effective["allowed_value_options"])),
        "field_type_requirements": json.loads(json.dumps(effective["field_type_requirements"])),
        "forbidden_fields": list(effective["forbidden_fields"]),
        "forbidden_aliases": json.loads(json.dumps(effective["forbidden_aliases"])),
        "minimal_valid_shape": result_skeleton if result_skeleton is not None else effective["minimal_valid_shape"],
        "branch_valid_shapes": branch_valid_shapes if branch_valid_shapes is not None else effective["branch_valid_shapes"],
    }
    handoff = {
        "schema_version": "black_box_flowpilot.current_handoff_contract.v2",
        "contract_id": "black_box_flowpilot.current_handoff_contract.v2",
        "packet_id": packet_id,
        "packet_kind": packet_kind,
        "route_scope": route_scope,
        "recipient_responsibility": responsibility,
        "contract_family_id": family_id,
        "current_run_only": True,
        "route_version": 1,
        "source_generation": 1,
        "required_report_contract": report_contract,
        "input_material_manifest": {
            "route_node_id": str(packet.get("route_node_id") or ""),
            "target_result_id": str(packet.get("target_result_id") or ""),
            "authorized_result_read_ids": [],
            "required_authorized_reads_before_submit": [],
            "required_authorized_read_count": 0,
            "all_required_authorized_result_bodies_must_be_opened_before_submit": True,
        },
    }
    checklist = {
        "schema_version": "black_box_flowpilot.submission_checklist.v2",
        "source": "current_handoff_contract",
        "run_id": "run-unit-open",
        "packet_id": packet_id,
        "lease_id": "lease-unit-open",
        "route_version": 1,
        "source_generation": 1,
        "contract_family_id": family_id,
        "current_packet_body_inspected": False,
        "current_handoff_contract_inspected": True,
        "required_result_body_fields": list(report_contract["required_result_body_fields"]),
        "required_child_fields": list(report_contract["required_child_fields"]),
        "explicit_array_fields": list(report_contract["explicit_array_fields"]),
        "non_empty_array_fields": list(report_contract["non_empty_array_fields"]),
        "allowed_value_options": json.loads(json.dumps(report_contract["allowed_value_options"])),
        "field_type_requirements": json.loads(json.dumps(report_contract["field_type_requirements"])),
        "forbidden_fields": list(report_contract["forbidden_fields"]),
        "forbidden_aliases": json.loads(json.dumps(report_contract["forbidden_aliases"])),
        "result_skeleton": json.loads(json.dumps(report_contract["minimal_valid_shape"])),
        "branch_valid_shapes": json.loads(json.dumps(report_contract["branch_valid_shapes"])),
        "input_material_manifest": json.loads(json.dumps(handoff["input_material_manifest"])),
        "authorized_input_materials_count": 0,
        "required_authorized_input_materials_count": 0,
        "authorized_result_read_ids": [],
        "required_authorized_result_read_ids": [],
        "required_authorized_read_count": 0,
        "all_required_authorized_result_bodies_must_be_opened_before_submit": True,
    }
    fake_ai = fake_project_cli.contract_driven_fake_ai
    checklist["contract_fingerprint"] = fake_ai._fingerprint_for_payload(
        fake_ai._fingerprint_payload(
            run_id="run-unit-open",
            packet_id=packet_id,
            lease_id="lease-unit-open",
            route_version=1,
            source_generation=1,
            contract_family_id=family_id,
            required_report_contract=report_contract,
            review_window=None,
        )
    )
    body_hash = "unit-body-hash"
    return {
        "ok": True,
        "schema_version": "black_box_flowpilot.open_packet_result.v1",
        "run_id": "run-unit-open",
        "packet": {
            "packet_id": packet_id,
            "packet_kind": packet_kind,
            "responsibility": responsibility,
            "route_version": 1,
            "body_hash": body_hash,
            "current_handoff_contract": handoff,
        },
        "lease": {
            "lease_id": "lease-unit-open",
            "responsibility": responsibility,
            "ack_received": True,
        },
        "sealed_packet_body": str(packet.get("body") or "{}"),
        "authorized_input_materials": [],
        "authorized_input_materials_delivered": True,
        "submission_checklist": checklist,
        "open_receipt": {
            "event_type": "sealed_packet_body_opened",
            "packet_id": packet_id,
            "lease_id": "lease-unit-open",
            "body_hash": body_hash,
        },
    }


class FlowPilotFakeProjectRehearsalTests(unittest.TestCase):
    def test_core_fake_e2e_uses_public_role_and_submit_commands_only(self) -> None:
        source = (CORE_RUNTIME / "fake_e2e.py").read_text(encoding="utf-8")

        self.assertIn("from flowpilot_new_role_commands import ack, dispatch_current_role, open_packet", source)
        self.assertIn("from flowpilot_new_run_commands import submit_result", source)
        self.assertNotIn("_submission_checklist_from_current_handoff_contract", source)
        self.assertNotIn("minimal_valid_shape_for_family", source)
        self.assertNotIn("host.lease_responsibility", source)
        self.assertNotIn("host.submit_host_result", source)

    def test_fake_project_rehearsal_declares_all_required_scenarios(self) -> None:
        scenario_names = {name for name, _fn in fake_project_runner.rehearsal_scenarios.SCENARIOS}

        self.assertEqual(
            scenario_names,
            {
                "normal_full_path",
                "complete_workstream_ordinary_evidence",
                "wrong_role_recovery",
                "planning_chain_does_not_terminal",
                "route_mutation_recovery",
                "terminal_supplemental_repair",
                "missing_ack_block",
                "ack_only_wait",
                "lifecycle_guard_resume_and_patrol",
                "missing_current_result_fields_reissue",
                "cross_run_public_open_isolation",
                "slow_reviewer_progress_preserved",
                "accepted_packet_reassignment_rejected",
                "stop_terminal_fence",
                "progress_evidence_replacement",
                "orphan_runner_summary_recovery",
                "unsupported_side_command",
            },
        )

    def test_complete_workstream_ordinary_evidence_scenario_reaches_terminal(self) -> None:
        result = fake_project_runner.run_checks(
            scenario_names={"complete_workstream_ordinary_evidence"}
        )

        self.assertTrue(result["ok"], result)
        scenario = result["scenarios"][0]
        self.assertEqual(scenario["name"], "complete_workstream_ordinary_evidence")
        observations = scenario["observations"]
        self.assertEqual(observations["terminal_action"]["action_type"], "terminal_complete")
        self.assertGreater(observations["workstream_report_count"], 0)
        self.assertGreaterEqual(observations["integrated_delegation_count"], 1)
        self.assertGreaterEqual(observations["ordinary_evidence_work_count"], 1)

    def test_missing_ack_scenario_submits_current_json_contract_and_blocks(self) -> None:
        result = fake_project_runner.run_checks(
            scenario_names={"missing_ack_block"}
        )

        self.assertTrue(result["ok"], result)
        scenario = result["scenarios"][0]
        self.assertEqual(scenario["name"], "missing_ack_block")
        self.assertEqual(scenario["observations"]["result_status"], "result_blocked")
        self.assertEqual(scenario["observations"]["next_action"], "repair_packet")
        self.assertEqual(scenario["observations"]["submitted_body_type"], "object")
        self.assertFalse(scenario["observations"]["runtime_ack_received_before_submit"])

    def test_fake_project_results_remove_machine_local_roots(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="flowpilot_fake_project_portable_",
            dir=fake_project_runner.REPO_ROOT / "tmp",
        ) as tmp:
            result = fake_project_runner.run_checks(
                Path(tmp),
                scenario_names={"unsupported_side_command"},
            )

        serialized = json.dumps(result, sort_keys=True)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["work_root"], "<work-root>")
        self.assertNotIn(str(fake_project_runner.REPO_ROOT.resolve()), serialized)
        self.assertNotIn(str(Path(tmp).resolve()), serialized)

    def test_blackbox_fake_project_rehearsal_smoke_uses_public_cli(self) -> None:
        result = fake_project_runner.run_checks(
            scenario_names={
                "unsupported_side_command",
            }
        )

        self.assertTrue(result["ok"], result)
        self.assertTrue(result["black_box_contract"]["uses_public_cli_subprocesses"])
        self.assertTrue(result["black_box_contract"]["uses_startup_ui_script"])
        self.assertFalse(result["black_box_contract"]["uses_internal_e2e_helper"])
        scenario_names = {scenario["name"] for scenario in result["scenarios"]}
        self.assertEqual(
            scenario_names,
            {
                "unsupported_side_command",
            },
        )
        self.assertIn("wrong_role_lease_accepted", result["hazard_detection"]["hazards"])
        self.assertIn("missing_ack_result_accepted", result["hazard_detection"]["hazards"])
        self.assertIn("planning_chain_terminal", result["hazard_detection"]["hazards"])
        self.assertIn("terminal_missing_route_node", result["hazard_detection"]["hazards"])
        self.assertIn("route_mutation_without_frontier_rewrite", result["hazard_detection"]["hazards"])
        self.assertIn("side_command_surface_available", result["hazard_detection"]["hazards"])
        self.assertIn("lifecycle_resume_from_chat", result["hazard_detection"]["hazards"])
        self.assertIn("lifecycle_patrol_allows_nonterminal_stop", result["hazard_detection"]["hazards"])
        self.assertIn("lifecycle_repeated_wait_not_recovered", result["hazard_detection"]["hazards"])
        self.assertIn("slow_live_reviewer_replaced", result["hazard_detection"]["hazards"])
        self.assertIn("accepted_packet_reassignment_allowed", result["hazard_detection"]["hazards"])
        self.assertIn("foreground_final_preflight_missing", result["hazard_detection"]["hazards"])
        self.assertIn("passive_wait_completed", result["hazard_detection"]["hazards"])
        self.assertIn("scoped_closure_final_return_allowed", result["hazard_detection"]["hazards"])
        recursive_hazards = result["recursive_route_hazard_detection"]["hazards"]
        self.assertIn("missing_node_terminal_complete", recursive_hazards)
        self.assertIn("wrong_flowguard_target_accepted", recursive_hazards)
        self.assertIn("stale_node_evidence_accepted", recursive_hazards)
        self.assertIn("dead_lease_advances_node", recursive_hazards)
        self.assertIn("mutation_without_frontier_rewrite", recursive_hazards)

    def test_blackbox_terminal_supplemental_repair_uses_public_cli(self) -> None:
        result = fake_project_runner.run_checks(
            scenario_names={
                "terminal_supplemental_repair",
            }
        )

        self.assertTrue(result["ok"], result)
        scenario = result["scenarios"][0]
        self.assertEqual(scenario["name"], "terminal_supplemental_repair")
        self.assertTrue(scenario["observations"]["terminal_replay_blocked"])
        self.assertEqual(
            scenario["observations"]["supplemental_contract_ids"],
            ["terminal-supplemental-repair-r1"],
        )
        rows = {row["id"]: row for row in result["test_mesh"]["rows"]}
        self.assertEqual(
            rows["fake_project_blackbox_cli_terminal_supplemental_repair"]["status"],
            "passed",
        )

    def test_fake_rehearsal_high_standard_contract_matches_public_open_contract(self) -> None:
        high_standard_body = json.loads(
            fake_project_cli.current_contract_body_from_open_result(
                unit_open_result_fixture(
                    {"packet_id": "packet-hs", "packet_kind": "task", "route_scope": "high_standard_contract"}
                )
            )
        )
        self.assertIn("requirements", high_standard_body)
        self.assertIn("acceptance_item_registry", high_standard_body)
        self.assertNotIn("decision", high_standard_body)
        self.assertNotIn("pm_visible_summary", high_standard_body)

        skill_standard_body = json.loads(
            fake_project_cli.current_contract_body_from_open_result(
                unit_open_result_fixture(
                    {"packet_id": "packet-skill", "packet_kind": "task", "route_scope": "skill_standard"}
                )
            )
        )
        self.assertIn("obligations", skill_standard_body)
        self.assertNotIn("selected_skills", skill_standard_body)

    def test_fake_project_success_bodies_use_declared_contract_fields(self) -> None:
        packets = [
            {"packet_id": "packet-hs", "packet_kind": "task", "route_scope": "high_standard_contract"},
            {"packet_id": "packet-discovery", "packet_kind": "task", "route_scope": "discovery"},
            {"packet_id": "packet-skill", "packet_kind": "task", "route_scope": "skill_standard"},
            {"packet_id": "packet-plan", "packet_kind": "task", "route_scope": "planning"},
            {
                "packet_id": "packet-context",
                "packet_kind": "task",
                "route_scope": "node_acceptance_plan",
                "route_node_id": "node-001",
            },
            {"packet_id": "packet-node", "packet_kind": "task", "route_scope": "node"},
            {"packet_id": "packet-flowguard", "packet_kind": "flowguard_check", "route_scope": "node"},
            {"packet_id": "packet-review", "packet_kind": "review", "route_scope": "node"},
            {"packet_id": "packet-pm", "packet_kind": "pm_disposition", "route_scope": "node_pm_disposition"},
        ]

        for packet in packets:
            with self.subTest(packet=packet["packet_id"]):
                opened = unit_open_result_fixture(packet)
                family_id = packet_result_contracts.packet_result_family_id(packet)
                body = json.loads(fake_project_cli.current_contract_body_from_open_result(opened))
                self.assertFalse(
                    packet_result_contracts.undeclared_success_fields_for_family(family_id, body),
                    (family_id, body),
                )
                self.assertFalse(
                    packet_result_contracts.forbidden_success_fields_for_family(family_id, body),
                    (family_id, body),
                )

    def test_flowguard_fake_body_consumes_required_subject_artifacts(self) -> None:
        packet = {
            "packet_id": "packet-flowguard-parent-repair",
            "packet_kind": "flowguard_check",
            "route_scope": "node_acceptance_plan",
            "result_contract_profile_ids": ["flowguard.subject_artifacts_consumed_required"],
            "result_contract_profile_bindings": {
                "flowguard.subject_artifacts_consumed_required": {
                    "artifact_ids": [
                        "parent_repair_scope_contract:parent-repair-contract-001",
                        "active_repair_child_node:parent-repair-child-001",
                    ]
                }
            },
            "body": json.dumps(
                {
                    "required_subject_artifacts": [
                        {
                            "artifact_id": "parent_repair_scope_contract:parent-repair-contract-001",
                            "artifact_type": "parent_repair_scope_contract",
                        },
                        {
                            "artifact_id": "active_repair_child_node:parent-repair-child-001",
                            "artifact_type": "active_repair_child_node",
                        },
                    ]
                }
            ),
        }

        body = json.loads(
            fake_project_cli.current_contract_body_from_open_result(unit_open_result_fixture(packet))
        )

        self.assertEqual(
            {row["artifact_id"] for row in body["subject_artifacts_consumed"]},
            {
                "parent_repair_scope_contract:parent-repair-contract-001",
                "active_repair_child_node:parent-repair-child-001",
            },
        )

    def test_flowguard_fake_body_consumes_semantic_recheck_contract(self) -> None:
        packet = {
            "packet_id": "packet-flowguard-repair",
            "packet_kind": "flowguard_check",
            "route_scope": "pm_repair_decision",
            "result_contract_profile_ids": ["flowguard.semantic_recheck_required"],
            "result_contract_profile_bindings": {
                "flowguard.semantic_recheck_required": {
                    "blocker_id": "blocker-001",
                    "coverage_boundary": "subject_bound_semantic",
                    "authorized_result_read_ids": ["result-worker-001"],
                    "repair_obligation_ids": ["repair-obligation-001"],
                }
            },
            "body": json.dumps(
                {
                    "semantic_recheck_contract": {
                        "blocker_id": "blocker-001",
                        "subject_bound_required": True,
                        "must_consume_repair_obligation_ids": ["repair-obligation-001"],
                    }
                }
            ),
        }

        body = json.loads(
            fake_project_cli.current_contract_body_from_open_result(unit_open_result_fixture(packet))
        )

        self.assertEqual(body["semantic_recheck"]["blocker_id"], "blocker-001")
        self.assertTrue(body["semantic_recheck"]["subject_result_consumed"])
        self.assertTrue(body["semantic_recheck"]["subject_bound_semantic_coverage"])
        self.assertEqual(body["semantic_recheck"]["coverage_boundary"], "subject_bound_semantic")
        self.assertEqual(body["semantic_recheck"]["consumed_authorized_result_read_ids"], ["result-worker-001"])
        self.assertEqual(body["semantic_recheck"]["consumed_repair_obligation_ids"], ["repair-obligation-001"])

    def test_pm_repair_redesign_fake_body_uses_branch_route_plan(self) -> None:
        current_skeleton = {"decision": "repair_current_scope", "reason": "current checklist"}
        current_branches = {
            "decision=redesign_route": {
                "decision": "redesign_route",
                "reason": "replace blocked route",
                "route_plan": {
                    "schema_version": "flowpilot.route_plan.v1",
                    "nodes": [
                        {
                            "node_id": "repair-node-001",
                            "title": "Repair current blocker",
                            "responsibility": "worker",
                        }
                    ],
                },
            }
        }
        packet = {
            "packet_id": "packet-pm-repair",
            "packet_kind": "pm_repair_decision",
            "route_scope": "pm_repair_decision",
            "body": json.dumps(
                {
                    "semantic_repair_note": "Repair the blocked route.",
                    "minimal_valid_shape": {"decision": "stale-body-mirror"},
                }
            ),
        }

        packet = unit_open_result_fixture(
            packet,
            result_skeleton=current_skeleton,
            branch_valid_shapes=current_branches,
        )
        body = json.loads(
            fake_project_cli.current_contract_body_from_open_result(
                packet,
                pm_repair_decision="redesign_route",
            )
        )

        self.assertEqual(body["decision"], "redesign_route")
        self.assertEqual(body["route_plan"]["nodes"][0]["node_id"], "repair-node-001")

    def test_flowguard_fake_worker_writes_required_evidence_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_root = Path(tmp) / "evidence" / "flowguard" / "packet-001"
            packet = {
                "packet_id": "packet-001",
                "packet_kind": "flowguard_check",
                "route_scope": "pm_repair_decision",
                "body": json.dumps(
                    {
                        "evidence_output_policy": {
                            "required_for_formal_run": True,
                            "run_local_evidence_root": str(evidence_root),
                        }
                    }
                ),
            }

            path = fake_project_cli.write_flowguard_evidence_artifact_for_packet(packet)

            self.assertEqual(path, evidence_root / "flowguard_evidence.json")
            artifact = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(artifact["model_test_alignment_report"]["decision"], "pass")

    def test_open_current_packet_inputs_uses_authorized_reads_from_sealed_packet(self) -> None:
        calls: list[tuple[str, ...]] = []
        sealed_body = json.dumps({"segment_targets": [{"segment_id": "seg-current", "summary": "Current segment"}]})
        public_open = unit_open_result_fixture(
            {
                "packet_id": "packet-001",
                "packet_kind": "task",
                "route_scope": "high_standard_contract",
                "body": sealed_body,
            }
        )

        def fake_run_cli(_root: Path, _command_log: list[dict[str, object]], *args: str, **_kwargs: object) -> dict[str, object]:
            calls.append(args)
            if args[0] == "open-packet":
                return public_open
            raise AssertionError(f"unexpected CLI command: {args}")

        with mock.patch.object(fake_project_cli, "run_cli", side_effect=fake_run_cli):
            opened = fake_project_cli.open_current_packet_inputs(
                Path("fake-root"),
                [],
                lease_id="lease-001",
                packet={"packet_id": "packet-001", "target_result_id": "result-public-projection"},
            )

        self.assertIn(("open-packet", "--lease-id", "lease-001", "--packet-id", "packet-001"), calls)
        self.assertFalse(any(call and call[0] == "open-result" for call in calls))
        self.assertNotIn("result-public-projection", {part for call in calls for part in call})
        self.assertEqual(opened["sealed_packet_body"], sealed_body)
        self.assertEqual(opened["submission_checklist"]["source"], "current_handoff_contract")

    def test_public_open_rejects_each_required_result_body_without_current_receipt(self) -> None:
        opened = unit_open_result_fixture(
            {"packet_id": "packet-required-reads", "packet_kind": "flowguard_check", "route_scope": "node"}
        )
        checklist = opened["submission_checklist"]
        handoff_manifest = opened["packet"]["current_handoff_contract"]["input_material_manifest"]
        required_ids = ["result-required-a", "result-required-b"]
        checklist["authorized_result_read_ids"] = list(required_ids)
        checklist["required_authorized_result_read_ids"] = list(required_ids)
        checklist["required_authorized_read_count"] = len(required_ids)
        handoff_manifest["authorized_result_read_ids"] = list(required_ids)
        handoff_manifest["required_authorized_reads_before_submit"] = list(required_ids)
        handoff_manifest["required_authorized_read_count"] = len(required_ids)
        opened["authorized_input_materials"] = [
            {
                "result_id": result_id,
                "required_before_submit": True,
                "body_hash": f"hash-{result_id}",
                "open_receipt": {
                    "result_id": result_id,
                    "packet_id": "packet-required-reads",
                    "lease_id": "lease-unit-open",
                    "body_hash": f"hash-{result_id}",
                },
            }
            for result_id in required_ids
        ]

        fake_project_cli._canonical_open_context(opened)
        for missing_result_id in required_ids:
            with self.subTest(missing_result_id=missing_result_id):
                tampered = json.loads(json.dumps(opened))
                for material in tampered["authorized_input_materials"]:
                    if material["result_id"] == missing_result_id:
                        material.pop("open_receipt")
                with self.assertRaisesRegex(
                    fake_project_cli.RehearsalFailure,
                    missing_result_id,
                ):
                    fake_project_cli._canonical_open_context(tampered)

    def test_fake_project_generator_fails_closed_without_current_public_identity(self) -> None:
        with self.assertRaises(fake_project_cli.RehearsalFailure):
            fake_project_cli.current_contract_body_from_open_result(
                {"packet_id": "packet-never-opened"}
            )

        mutations = {
            "no_ack": lambda row: row["lease"].__setitem__("ack_received", False),
            "wrong_packet": lambda row: row["submission_checklist"].__setitem__(
                "packet_id", "packet-other"
            ),
            "wrong_lease": lambda row: row["submission_checklist"].__setitem__(
                "lease_id", "lease-other"
            ),
            "wrong_role": lambda row: row["lease"].__setitem__(
                "responsibility", "reviewer"
            ),
            "missing_family": lambda row: row["packet"]["current_handoff_contract"].__setitem__(
                "contract_family_id", ""
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                opened = unit_open_result_fixture(
                    {
                        "packet_id": f"packet-{label}",
                        "packet_kind": "task",
                        "route_scope": "high_standard_contract",
                    }
                )
                mutate(opened)
                with self.assertRaises(fake_project_cli.RehearsalFailure):
                    fake_project_cli.current_contract_body_from_open_result(opened)

    def test_packet_body_contract_conflict_cannot_override_public_checklist(self) -> None:
        opened = unit_open_result_fixture(
            {
                "packet_id": "packet-body-conflict",
                "packet_kind": "task",
                "route_scope": "high_standard_contract",
                "body": json.dumps(
                    {
                        "minimal_valid_shape": {"decision": "body-bypass"},
                        "required_result_body_fields": ["decision"],
                    }
                ),
            }
        )

        payload = json.loads(
            fake_project_cli.current_contract_body_from_open_result(opened)
        )

        self.assertNotEqual(payload.get("decision"), "body-bypass")
        self.assertIn("requirements", payload)
        self.assertFalse(hasattr(fake_project_cli, "current_contract_body_for_packet"))
        self.assertFalse(hasattr(fake_project_cli, "_high_standard_contract_body"))
        self.assertFalse(hasattr(fake_project_cli, "_generic_current_result_body"))

    def test_terminal_backward_replay_fake_body_uses_current_segment_targets(self) -> None:
        packet = {
            "packet_id": "packet-terminal",
            "packet_kind": "review",
            "route_scope": "terminal_backward_replay",
            "body": json.dumps(
                {
                    "segment_targets": [
                        {"segment_id": "seg-acceptance", "segment_kind": "acceptance_item", "summary": "Check acceptance registry"},
                        {"segment_id": "seg-route", "segment_kind": "route_node", "summary": "Check node repair loop"},
                    ]
                }
            ),
        }

        body = json.loads(
            fake_project_cli.current_contract_body_from_open_result(unit_open_result_fixture(packet))
        )

        self.assertEqual(
            [row["segment_id"] for row in body["route_segment_replay"]],
            ["seg-acceptance", "seg-route"],
        )
        self.assertEqual(
            [row["segment_kind"] for row in body["route_segment_replay"]],
            ["acceptance_item", "route_node"],
        )
        self.assertEqual(body["route_segment_replay"][0]["status"], "closed")
        self.assertIn("Check acceptance registry", body["route_segment_replay"][0]["basis"])
        self.assertEqual(body["final_blockers"], [])

    def test_pm_disposition_fake_body_dispositions_current_acceptance_items(self) -> None:
        packet = {
            "packet_id": "packet-pm",
            "packet_kind": "pm_disposition",
            "route_scope": "node_pm_disposition",
            "body": json.dumps({"node_acceptance_item_ids": ["acc-current-a", "acc-current-b"]}),
        }

        opened = unit_open_result_fixture(packet)
        accepted = json.loads(
            fake_project_cli.current_contract_body_from_open_result(
                opened,
                pm_disposition_decision="accept",
            )
        )
        blocked = json.loads(
            fake_project_cli.current_contract_body_from_open_result(
                opened,
                pm_disposition_decision="redesign_route",
            )
        )

        self.assertEqual(
            [row["acceptance_item_id"] for row in accepted["acceptance_item_disposition"]],
            ["acc-current-a", "acc-current-b"],
        )
        self.assertEqual(
            {row["disposition"] for row in accepted["acceptance_item_disposition"]},
            {"accepted"},
        )
        self.assertEqual(
            [row["acceptance_item_id"] for row in blocked["acceptance_item_disposition"]],
            ["acc-current-a", "acc-current-b"],
        )
        self.assertEqual(
            {row["disposition"] for row in blocked["acceptance_item_disposition"]},
            {"blocked"},
        )

    def test_pm_repair_fake_body_preserves_parent_repair_contract_shape(self) -> None:
        current_skeleton = {
            "decision": "repair_parent_scope",
            "reason": "Parent scope must be replaced.",
            "repair_parent_scope_contract": {
                "schema_version": "flowpilot.parent_repair_scope_contract.v1",
                "source_parent_node_id": "parent-001",
                "inherit_existing_children": True,
                "repair_child_specs": [
                    {
                        "node_id": "parent-001-repair-child-001",
                        "purpose": "Repair parent replay input wiring.",
                        "required_evidence": ["current repair child result"],
                    }
                ],
            },
        }
        packet = {
            "packet_id": "packet-parent-repair",
            "packet_kind": "pm_repair_decision",
            "route_scope": "pm_repair_decision",
            "body": json.dumps(
                {
                    "semantic_repair_note": "Repair the parent scope.",
                    "minimal_valid_shape": {"decision": "stale-body-mirror"},
                }
            ),
        }

        packet = unit_open_result_fixture(
            packet,
            result_skeleton=current_skeleton,
        )
        body = json.loads(fake_project_cli.current_contract_body_from_open_result(packet))

        self.assertEqual(body["decision"], "repair_parent_scope")
        self.assertEqual(body["repair_parent_scope_contract"]["source_parent_node_id"], "parent-001")
        self.assertEqual(
            body["repair_parent_scope_contract"]["repair_child_specs"][0]["node_id"],
            "parent-001-repair-child-001",
        )

    def test_pm_repair_fake_body_derives_terminal_supplemental_contract_from_opened_packet(self) -> None:
        current_skeleton = {
            "decision": "redesign_route",
            "reason": "current checklist reason",
            "supplemental_repair_contract": {
                "schema_version": "flowpilot.terminal_supplemental_repair_contract.v1",
                "contract_id": "terminal-supplemental-repair-r1",
                "round_number": 1,
                "repair_items": [
                    {
                        "repair_item_id": "terminal-gap-r1-item-1",
                        "owner_repair_node_id": "node-001",
                    }
                ],
            },
            "route_plan": {
                "schema_version": "flowpilot.route_plan.v1",
                "nodes": [
                    {
                        "node_id": "node-001",
                        "responsibility": "worker",
                        "supplemental_repair_contract_ids": ["terminal-supplemental-repair-r1"],
                        "supplemental_repair_item_ids": ["terminal-gap-r1-item-1"],
                    }
                ],
            },
        }
        packet = {
            "packet_id": "packet-repair",
            "packet_kind": "pm_repair_decision",
            "route_scope": "pm_repair_decision",
            "body": json.dumps(
                {
                    "semantic_repair_note": "Repair terminal closure.",
                    "minimal_valid_shape": {"decision": "stale-body-mirror"},
                }
            ),
        }

        packet = unit_open_result_fixture(
            packet,
            result_skeleton=current_skeleton,
        )
        body = json.loads(fake_project_cli.current_contract_body_from_open_result(packet))

        self.assertEqual(body["decision"], "redesign_route")
        self.assertEqual(
            body["supplemental_repair_contract"]["contract_id"],
            "terminal-supplemental-repair-r1",
        )
        self.assertEqual(
            body["route_plan"]["nodes"][0]["supplemental_repair_contract_ids"],
            ["terminal-supplemental-repair-r1"],
        )
        self.assertNotIn("supplemental_contract", body)

    def test_pm_repair_fake_body_uses_current_terminal_reissue_checklist_branch(self) -> None:
        packet = {
            "packet_id": "packet-repair-reissue",
            "packet_kind": "pm_repair_decision",
            "route_scope": "pm_repair_decision",
            "body": json.dumps({"minimal_valid_shape": {"decision": "stale-body-mirror"}}),
        }

        current_skeleton = {
            "decision": "redesign_route",
            "reason": "current terminal supplemental repair",
            "supplemental_repair_contract": {
                "schema_version": "flowpilot.terminal_supplemental_repair_contract.v1",
                "contract_id": "terminal-supplemental-repair-r1",
                "round_number": 1,
                "original_contract_hash": "current-contract-hash",
                "terminal_blocker_id": "blocker-0001",
                "terminal_gap_report_result_id": "result-0031",
                "repair_items": [
                    {
                        "repair_item_id": "terminal-gap-r1-item-1",
                        "owner_repair_node_id": "repair-current-scope-leaf",
                    }
                ],
            },
        }
        current_branch = {
            "decision": "redesign_route",
            "route_plan": {
                "schema_version": "flowpilot.route_plan.v1",
                "nodes": [
                    {
                        "node_id": "repair-current-scope",
                        "responsibility": "worker",
                        "child_node_ids": ["repair-current-scope-leaf"],
                    },
                    {
                        "node_id": "repair-current-scope-leaf",
                        "responsibility": "worker",
                        "child_node_ids": [],
                        "supplemental_repair_contract_ids": [],
                        "supplemental_repair_item_ids": [],
                    },
                ],
            },
        }

        terminal_branch = fake_project_cli._merge_json_objects(
            current_skeleton,
            current_branch,
        )
        packet = unit_open_result_fixture(
            packet,
            result_skeleton=current_skeleton,
            branch_valid_shapes={
                "decision=redesign_route_terminal_supplemental": terminal_branch,
                "decision=redesign_route": terminal_branch,
            },
        )
        body = json.loads(
            fake_project_cli.current_contract_body_from_open_result(
                packet,
                pm_repair_decision="redesign_route",
            )
        )

        self.assertEqual(body["supplemental_repair_contract"]["original_contract_hash"], "current-contract-hash")
        leaf = body["route_plan"]["nodes"][1]
        self.assertEqual(leaf["supplemental_repair_contract_ids"], ["terminal-supplemental-repair-r1"])
        self.assertEqual(leaf["supplemental_repair_item_ids"], ["terminal-gap-r1-item-1"])
        self.assertNotIn("supplemental_contract", body)


if __name__ == "__main__":
    unittest.main()
