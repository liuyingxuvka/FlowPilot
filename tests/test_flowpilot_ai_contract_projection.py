from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS_ROOT = ROOT / "skills" / "flowpilot" / "assets"
RUNTIME_ROOT = ASSETS_ROOT / "flowpilot_core_runtime"
if str(ASSETS_ROOT) not in sys.path:
    sys.path.insert(0, str(ASSETS_ROOT))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    old_path = list(sys.path)
    old_module = sys.modules.get(name)
    sys.modules[name] = module
    sys.path.insert(0, str(path.parent))
    sys.path.insert(0, str(ASSETS_ROOT))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old_path
        if old_module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = old_module
    return module


runtime = load_module("flowpilot_ai_contract_projection_runtime", RUNTIME_ROOT / "runtime.py")
runtime_runner = load_module(
    "flowpilot_ai_contract_projection_runner",
    ROOT / "simulations" / "run_flowpilot_core_runtime_checks.py",
)
contract_fake_ai = load_module(
    "flowpilot_contract_driven_fake_ai",
    ROOT / "simulations" / "flowpilot_contract_driven_fake_ai.py",
)
from flowpilot_core_runtime import formal_artifact_contracts  # noqa: E402


def flowguard_result_payload(summary: str) -> dict[str, object]:
    return {
        "pm_visible_summary": [summary],
        "reviewed_by_role": "flowguard_operator",
        "passed": True,
        "modeled_boundary": "Current packet and current result only.",
        "blockers": [],
        "pm_suggestion_items": [],
        "contract_self_check": {
            "all_required_fields_present": True,
            "exact_field_names_used": True,
            "empty_required_arrays_explicit": True,
            "runtime_mechanical_validation_passed": True,
            "semantic_sufficiency_reviewed_by_runtime": False,
        },
    }


def write_flowguard_evidence_artifact(
    ledger: dict[str, object],
    packet_id: str,
    *,
    decision: str = "pass",
    mode: str = "valid",
) -> None:
    if not ledger.get("run_root"):
        ledger["run_root"] = tempfile.mkdtemp(prefix="flowpilot-ai-contract-test-")
    packet = ledger["packets"][packet_id]
    path = runtime._flowguard_packet_evidence_artifact_path(ledger, packet)
    assert path is not None
    if mode == "missing":
        return
    if mode == "wrong_path":
        path = path.parent.parent / f"{packet_id}-wrong" / "flowguard_evidence.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if mode == "invalid_json":
        path.write_text("{not: strict json", encoding="utf-8")
        return
    report: dict[str, object] = {
        "failed_predicates": [] if decision == "pass" else ["semantic_contract_missing"],
    }
    if mode != "missing_decision":
        report["decision"] = decision
    path.write_text(
        json.dumps(
            {
                "schema_version": "flowpilot.flowguard_evidence.v1",
                "model_test_alignment_report": report,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


class FlowPilotAIContractProjectionTests(unittest.TestCase):
    def issue_semantic_recheck_packet(
        self,
        *,
        include_profile: bool = True,
    ) -> tuple[dict[str, object], str]:
        ledger, subject_packet_id, _worker = runtime_runner._base_ledger()
        run_root = Path(tempfile.mkdtemp(prefix="flowpilot-ai-contract-run-"))
        ledger["run_root"] = str(run_root)
        runtime.ack_lease(ledger, _worker, subject_packet_id)
        target_result_id = runtime.submit_result(
            ledger,
            _worker,
            subject_packet_id,
            json.dumps(
                {
                    "decision": "pass",
                    "pm_visible_summary": ["Worker result for semantic recheck projection."],
                    "current_evidence_refs": ["worker-current-evidence"],
                },
                sort_keys=True,
            ),
        )
        packet_id = "packet-semantic-recheck-001"
        issue_kwargs = {
            "ledger": ledger,
            "responsibility": "flowguard_operator",
            "objective": "Run blocker-bound semantic recheck",
            "body": json.dumps(
                {
                    "evidence_output_policy": {
                        "run_local_evidence_root": str(run_root / "flowguard" / packet_id),
                        "required_for_formal_run": True,
                    },
                    "subject_packet_id": subject_packet_id,
                    "target_result_id": target_result_id,
                    "semantic_recheck_contract": {
                        "schema_version": "black_box_flowpilot.semantic_flowguard_recheck_contract.v1",
                        "blocker_id": "blocker-semantic-001",
                        "subject_packet_id": subject_packet_id,
                        "target_result_id": target_result_id,
                        "subject_bound_required": True,
                        "must_consume_authorized_result_read_purposes": [
                            "subject_result_for_flowguard_check"
                        ],
                        "must_consume_repair_obligation_ids": ["repair-obligation-001"],
                        "forbidden_pass_boundaries": ["shape_only", "current_contract_only"],
                    }
                },
                sort_keys=True,
            ),
            "packet_kind": "flowguard_check",
            "required_flowguard_target": "",
            "preassigned_packet_id": packet_id,
            "subject_id": subject_packet_id,
            "target_result_id": target_result_id,
            "route_scope": "pm_repair_decision",
            "repair_blocker_id": "blocker-semantic-001",
            "authorized_result_reads": [
                {
                    "result_id": target_result_id,
                    "allowed_roles": ["flowguard_operator"],
                    "purpose": "subject_result_for_flowguard_check",
                    "required_before_submit": True,
                }
            ],
        }
        if include_profile:
            issue_kwargs["result_contract_profile_ids"] = ["flowguard.semantic_recheck_required"]
            issue_kwargs["result_contract_profile_bindings"] = {
                "flowguard.semantic_recheck_required": {
                    "blocker_id": "blocker-semantic-001",
                    "coverage_boundary": "subject_bound_semantic",
                    "authorized_result_read_ids": [target_result_id],
                    "repair_obligation_ids": ["repair-obligation-001"],
                }
            }
        packet_id = runtime.issue_task_packet(
            **issue_kwargs,
        )
        return ledger, packet_id

    def assign_flowguard(self, ledger: dict[str, object], packet_id: str, agent_id: str = "") -> str:
        packet = ledger["packets"][packet_id]
        lease_id = str(packet.get("assigned_lease_id") or "")
        if not lease_id:
            if agent_id:
                lease_id = runtime.lease_agent(
                    ledger,
                    "flowguard_operator",
                    agent_id=agent_id,
                    packet_id=packet_id,
                )
            else:
                lease_id = runtime.lease_agent(
                    ledger,
                    "flowguard_operator",
                    packet_id=packet_id,
                )
            runtime.assign_packet(ledger, packet_id, lease_id)
        if not ledger["leases"][lease_id].get("ack_received"):
            runtime.ack_lease(ledger, lease_id, packet_id)
        runtime.open_authorized_input_materials_for_role(ledger, packet_id, lease_id)
        return lease_id

    def latest_reissue_packet_id(self, ledger: dict[str, object], blocked_packet_id: str) -> str:
        for event in reversed(ledger["events"]):
            if (
                event["event_type"] == "current_contract_reissue_packet_issued"
                and event["payload"]["blocked_packet_id"] == blocked_packet_id
            ):
                return str(event["payload"]["fresh_packet_id"])
        self.fail(f"no reissue packet found for {blocked_packet_id}")

    def contract_driven_responder(self, packet: dict[str, object]):
        return contract_fake_ai.ContractDrivenFakeAIResponder.from_packet(packet)

    def node_context_package_result_id(
        self,
        ledger: dict[str, object],
        package: dict[str, object],
    ) -> str:
        result_id = f"result-node-context-{len(ledger.get('results', {})) + 1:04d}"
        ledger.setdefault("results", {})[result_id] = {
            "result_id": result_id,
            "body": json.dumps({"decision": "pass", "node_context_package": package}, sort_keys=True),
            "status": "mechanically_valid",
        }
        return result_id

    def test_semantic_recheck_contract_projects_ai_facing_fields_and_options(self) -> None:
        ledger, packet_id = self.issue_semantic_recheck_packet()
        packet = ledger["packets"][packet_id]
        packet_body = json.loads(packet["body"])
        report_contract = packet_body["current_handoff_contract"]["required_report_contract"]
        options = report_contract["allowed_value_options"]
        minimal_shape = report_contract["minimal_valid_shape"]
        semantic_profile_binding = report_contract["result_contract_profile_bindings"][
            "flowguard.semantic_recheck_required"
        ]

        self.assertIn("semantic_recheck", report_contract["required_result_body_fields"])
        self.assertEqual(
            options["semantic_recheck.subject_result_consumed"],
            [True],
        )
        self.assertEqual(
            options["semantic_recheck.subject_bound_semantic_coverage"],
            [True],
        )
        self.assertEqual(
            options["semantic_recheck.consumed_authorized_result_read_ids[]"],
            [semantic_profile_binding["authorized_result_read_ids"][0]],
        )
        self.assertEqual(
            options["semantic_recheck.consumed_repair_obligation_ids[]"],
            ["repair-obligation-001"],
        )
        self.assertEqual(
            minimal_shape["semantic_recheck"],
            {
                "blocker_id": "blocker-semantic-001",
                "subject_result_consumed": True,
                "subject_bound_semantic_coverage": True,
                "coverage_boundary": "subject_bound_semantic",
                "consumed_authorized_result_read_ids": semantic_profile_binding["authorized_result_read_ids"],
                "consumed_repair_obligation_ids": ["repair-obligation-001"],
            },
        )
        self.assertNotIn("forbidden_aliases", report_contract)
        self.assertNotIn("forbidden_result_body_fields", report_contract)
        self.assertEqual(
            report_contract["output_contract"]["forbidden_fields"],
            runtime.packet_result_contracts.effective_result_contract_from_envelope(
                packet["envelope"]
            )["forbidden_fields"],
        )

    def test_contract_driven_fake_ai_uses_projected_minimal_shape_for_legal_path(self) -> None:
        ledger, packet_id = self.issue_semantic_recheck_packet()
        packet = ledger["packets"][packet_id]
        responder = self.contract_driven_responder(packet)

        self.assertEqual(responder.projection_findings(), [])
        payload = responder.legal_payload()
        binding_ids = packet["envelope"]["result_contract_profile_bindings"][
            "flowguard.semantic_recheck_required"
        ]["authorized_result_read_ids"]
        self.assertEqual(payload["semantic_recheck"]["blocker_id"], "blocker-semantic-001")
        self.assertEqual(
            payload["semantic_recheck"]["consumed_authorized_result_read_ids"],
            binding_ids,
        )
        self.assertEqual(
            payload["semantic_recheck"]["consumed_repair_obligation_ids"],
            ["repair-obligation-001"],
        )

        lease_id = self.assign_flowguard(ledger, packet_id, "fg-contract-driven-legal")
        write_flowguard_evidence_artifact(ledger, packet_id)
        result_id = runtime.submit_result(
            ledger,
            lease_id,
            packet_id,
            json.dumps(payload, sort_keys=True),
        )

        self.assertEqual(ledger["results"][result_id]["status"], "accepted")

    def test_contract_driven_fake_ai_refuses_to_guess_when_finite_options_are_missing(self) -> None:
        ledger, packet_id = self.issue_semantic_recheck_packet()
        packet = json.loads(json.dumps(ledger["packets"][packet_id]))
        packet_body = json.loads(packet["body"])
        options = packet_body["current_handoff_contract"]["required_report_contract"]["allowed_value_options"]
        del options["semantic_recheck.subject_bound_semantic_coverage"]
        options["semantic_recheck.coverage_boundary"] = []
        packet["body"] = json.dumps(packet_body, sort_keys=True)

        responder = self.contract_driven_responder(packet)
        findings = responder.projection_findings()

        self.assertIn(
            ("projection_missing_options", "semantic_recheck.coverage_boundary"),
            {(finding.code, finding.field_path) for finding in findings},
        )
        self.assertNotIn(
            "semantic_recheck.subject_bound_semantic_coverage",
            responder.allowed_value_options,
        )

    def test_contract_driven_fake_ai_wrong_value_rows_repair_each_finite_option(self) -> None:
        ledger, packet_id = self.issue_semantic_recheck_packet()
        responder = self.contract_driven_responder(ledger["packets"][packet_id])
        fields = sorted(responder.allowed_value_options)
        self.assertGreaterEqual(len(fields), 5)

        for field_path in fields:
            with self.subTest(field_path=field_path):
                ledger, packet_id = self.issue_semantic_recheck_packet()
                packet = ledger["packets"][packet_id]
                responder = self.contract_driven_responder(packet)
                payload = responder.invalid_allowed_value_payload(field_path)
                seen_values = responder.option_values_seen(payload, field_path)
                self.assertTrue(seen_values)
                self.assertFalse(
                    set(seen_values).issubset(set(responder.allowed_value_options[field_path]))
                )

                lease_id = self.assign_flowguard(
                    ledger,
                    packet_id,
                    f"fg-wrong-{field_path.replace('.', '-').replace('[]', 'array')}",
                )
                result_id = runtime.submit_result(
                    ledger,
                    lease_id,
                    packet_id,
                    json.dumps(payload, sort_keys=True),
                )
                result = ledger["results"][result_id]
                reissue_packet_id = self.latest_reissue_packet_id(ledger, packet_id)
                reissue_body = json.loads(ledger["packets"][reissue_packet_id]["body"])
                diagnostic_text = json.dumps(
                    {
                        "blocked_reason": result.get("blocked_reason"),
                        "missing_required_fields": result.get("missing_required_fields"),
                        "mechanical_contract_failure": result.get("mechanical_contract_failure"),
                    },
                    sort_keys=True,
                )

                self.assertEqual(result["status"], "mechanical_contract_blocked")
                self.assertTrue(
                    field_path in diagnostic_text or field_path.replace("[]", "") in diagnostic_text,
                    diagnostic_text,
                )
                self.assertIn(field_path, reissue_body["allowed_value_options"])
                corrected_payload = responder.repaired_payload_from_reissue(reissue_body)

                corrected_lease_id = self.assign_flowguard(ledger, reissue_packet_id)
                write_flowguard_evidence_artifact(ledger, reissue_packet_id)
                corrected_result_id = runtime.submit_result(
                    ledger,
                    corrected_lease_id,
                    reissue_packet_id,
                    json.dumps(corrected_payload, sort_keys=True),
                )

                self.assertEqual(ledger["results"][corrected_result_id]["status"], "accepted")
                self.assertFalse(
                    [
                        event
                        for event in ledger["events"]
                        if event["event_type"] == "repair_loop_break_glass_required"
                    ]
                )

    def test_contract_driven_fake_ai_malformed_body_profiles_reissue_with_strict_json_feedback(self) -> None:
        for profile_id in contract_fake_ai.MALFORMED_BODY_PROFILE_IDS:
            with self.subTest(profile_id=profile_id):
                ledger, packet_id = self.issue_semantic_recheck_packet()
                packet = ledger["packets"][packet_id]
                responder = self.contract_driven_responder(packet)
                lease_id = self.assign_flowguard(
                    ledger,
                    packet_id,
                    f"fg-malformed-{profile_id}",
                )

                result_id = runtime.submit_result(
                    ledger,
                    lease_id,
                    packet_id,
                    responder.malformed_body(profile_id),
                )

                result = ledger["results"][result_id]
                reissue_packet_id = self.latest_reissue_packet_id(ledger, packet_id)
                reissue_body = json.loads(ledger["packets"][reissue_packet_id]["body"])
                corrected_payload = responder.repaired_payload_from_reissue(reissue_body)

                self.assertEqual(result["status"], "mechanical_contract_blocked")
                self.assertIn("strict JSON object", result["blocked_reason"])
                self.assertEqual(result["accepted"], False)
                self.assertIn("minimal_valid_shape", reissue_body)
                self.assertIn("semantic_recheck", reissue_body["minimal_valid_shape"])

                corrected_lease_id = self.assign_flowguard(ledger, reissue_packet_id)
                write_flowguard_evidence_artifact(ledger, reissue_packet_id)
                corrected_result_id = runtime.submit_result(
                    ledger,
                    corrected_lease_id,
                    reissue_packet_id,
                    json.dumps(corrected_payload, sort_keys=True),
                )

                self.assertEqual(ledger["results"][corrected_result_id]["status"], "accepted")
                self.assertFalse(
                    [
                        event
                        for event in ledger["events"]
                        if event["event_type"] == "repair_loop_break_glass_required"
                    ]
                )

    def test_contract_driven_fake_ai_coverage_cells_include_raw_body_and_retry_profiles(self) -> None:
        ledger, packet_id = self.issue_semantic_recheck_packet()
        responder = self.contract_driven_responder(ledger["packets"][packet_id])
        cells = responder.coverage_cells()
        mutation_kinds = {cell["mutation_kind"] for cell in cells}

        for profile_id in contract_fake_ai.MALFORMED_BODY_PROFILE_IDS:
            self.assertIn(f"malformed_body.{profile_id}", mutation_kinds)
        for profile_id in contract_fake_ai.RETRY_PROFILE_IDS:
            self.assertIn(profile_id, mutation_kinds)
        self.assertIn("finite_option_mistake", mutation_kinds)

    def test_existing_required_arrays_project_to_empty_array_fake_ai_cells(self) -> None:
        expected_non_empty_arrays = {
            "task.high_standard_contract": {"requirements", "acceptance_item_registry.items"},
            "task.discovery": {"material_sources"},
            "task.skill_standard": {"obligations"},
            "task.planning": {"nodes"},
        }

        for family_id, expected_fields in expected_non_empty_arrays.items():
            with self.subTest(family_id=family_id):
                contract = runtime.packet_result_contracts.effective_result_contract_for_family(family_id)
                responder = contract_fake_ai.ContractDrivenFakeAIResponder(contract)
                cells = {
                    (cell["contract_path"], cell["mutation_kind"])
                    for cell in responder.coverage_cells()
                }

                self.assertEqual(responder.projection_findings(), [])
                self.assertLessEqual(expected_fields, set(responder.non_empty_array_fields))
                for field_path in expected_fields:
                    self.assertIn((field_path, "empty_required_array"), cells)
                    payload = responder.empty_required_array_payload(field_path)
                    self.assertIsInstance(payload, dict)

    def test_node_acceptance_projection_owner_set_matrix_rejects_bad_rows_and_accepts_complete_rows(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        node = {
            "node_id": "node-001",
            "title": "Node",
            "route_version": 1,
            "repair_generation": 0,
            "acceptance_item_ids": ["acc-001", "acc-002"],
        }
        subject_packet = {"packet_id": "packet-node-acceptance-001"}
        base_package: dict[str, object] = {
            "node_id": "node-001",
            "purpose": "Provide current starting context.",
            "acceptance_criteria": ["criterion"],
            "relevant_references": ["reference"],
            "known_risks": ["risk"],
        }

        complete_package = {
            **base_package,
            "acceptance_item_projection": [
                {
                    "acceptance_item_id": "acc-001",
                    "status_for_this_node": "covered",
                    "future_evidence_rule": "Worker must prove acc-001.",
                },
                {
                    "acceptance_item_id": "acc-002",
                    "status_for_this_node": "covered",
                    "future_evidence_rule": "Worker must prove acc-002.",
                },
            ],
        }
        complete_result_id = self.node_context_package_result_id(ledger, complete_package)
        normalized = runtime._node_context_package_from_pm_result(
            ledger,
            node,
            subject_packet,
            complete_result_id,
        )
        self.assertEqual(
            [row["acceptance_item_id"] for row in normalized["acceptance_item_projection"]],
            ["acc-001", "acc-002"],
        )

        bad_packages = {
            "missing_one_owner": {
                **base_package,
                "acceptance_item_projection": [
                    {
                        "acceptance_item_id": "acc-001",
                        "status_for_this_node": "covered",
                        "future_evidence_rule": "Worker must prove acc-001.",
                    }
                ],
            },
            "extra_unknown_owner": {
                **base_package,
                "acceptance_item_projection": [
                    {
                        "acceptance_item_id": "acc-001",
                        "status_for_this_node": "covered",
                        "future_evidence_rule": "Worker must prove acc-001.",
                    },
                    {
                        "acceptance_item_id": "acc-999",
                        "status_for_this_node": "covered",
                        "future_evidence_rule": "Worker must prove acc-999.",
                    },
                ],
            },
            "malformed_row": {
                **base_package,
                "acceptance_item_projection": ["acc-001"],
            },
        }
        expected_messages = {
            "missing_one_owner": "missing node-owned acceptance item",
            "extra_unknown_owner": "allowed node owner set",
            "malformed_row": "must be an object",
        }
        for name, package in bad_packages.items():
            with self.subTest(name=name):
                result_id = self.node_context_package_result_id(ledger, package)
                with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, expected_messages[name]):
                    runtime._node_context_package_from_pm_result(
                        ledger,
                        node,
                        subject_packet,
                        result_id,
                    )

        for field_name in ("acceptance_criteria", "relevant_references", "known_risks"):
            with self.subTest(empty_context_list=field_name):
                package = {**complete_package, field_name: []}
                result_id = self.node_context_package_result_id(ledger, package)
                with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, f"missing required list field: {field_name}"):
                    runtime._node_context_package_from_pm_result(
                        ledger,
                        node,
                        subject_packet,
                        result_id,
                    )

        empty_owner_node = {
            "node_id": "node-empty",
            "title": "Node Empty",
            "route_version": 1,
            "repair_generation": 0,
            "acceptance_item_ids": [],
        }
        empty_package = {**base_package, "node_id": "node-empty", "acceptance_item_projection": []}
        empty_result_id = self.node_context_package_result_id(ledger, empty_package)
        empty_normalized = runtime._node_context_package_from_pm_result(
            ledger,
            empty_owner_node,
            subject_packet,
            empty_result_id,
        )
        self.assertEqual(empty_normalized["acceptance_item_projection"], [])

        empty_extra_package = {
            **base_package,
            "node_id": "node-empty",
            "acceptance_item_projection": [
                {
                    "acceptance_item_id": "acc-001",
                    "status_for_this_node": "covered",
                    "future_evidence_rule": "Worker must prove acc-001.",
                }
            ],
        }
        empty_extra_result_id = self.node_context_package_result_id(ledger, empty_extra_package)
        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "allowed node owner set: \\[\\]"):
            runtime._node_context_package_from_pm_result(
                ledger,
                empty_owner_node,
                subject_packet,
                empty_extra_result_id,
            )

        owner_contract = {
            "minimal_valid_shape": {
                "decision": "pass",
                "node_context_package": {
                    "acceptance_item_projection": complete_package["acceptance_item_projection"],
                },
            },
            "required_node_acceptance_item_ids": ["acc-001", "acc-002"],
            "required_child_fields": [
                "node_context_package.acceptance_item_projection[].acceptance_item_id",
            ],
            "allowed_value_options": {
                "node_context_package.acceptance_item_projection[].acceptance_item_id": ["acc-001", "acc-002"],
            },
        }
        empty_owner_contract = {
            "minimal_valid_shape": {
                "decision": "pass",
                "node_context_package": {"acceptance_item_projection": []},
            },
            "required_node_acceptance_item_ids": [],
        }
        owner_cells = contract_fake_ai.ContractDrivenFakeAIResponder(owner_contract).projection_gap_cells()
        empty_owner_cells = contract_fake_ai.ContractDrivenFakeAIResponder(empty_owner_contract).projection_gap_cells()
        owner_mutations = {cell["mutation_kind"] for cell in owner_cells}
        empty_owner_mutations = {cell["mutation_kind"] for cell in empty_owner_cells}

        for mutation in (
            "complete_owner_coverage",
            "missing_active_id_coverage",
            "partial_owner_set_missing_id",
            "extra_owner_id",
            "malformed_projection_row",
        ):
            self.assertIn(mutation, owner_mutations)
        self.assertIn("complete_owner_coverage", empty_owner_mutations)
        self.assertIn("empty_owner_set_extra_id", empty_owner_mutations)

    def test_formal_artifact_fake_ai_cells_are_declared(self) -> None:
        contract = {
            "minimal_valid_shape": flowguard_result_payload("FlowGuard legal body."),
            "evidence_output_policy": {
                "required_for_formal_run": True,
                "run_local_evidence_root": ".flowpilot/runs/<run-id>/evidence/flowguard/<packet-id>",
            },
            "formal_artifact_contract": {
                "artifact_id": "flowguard_evidence.json",
                "required_field_paths": ["model_test_alignment_report.decision"],
                "allowed_value_options": {
                    "model_test_alignment_report.decision": ["pass"],
                },
            },
        }
        responder = contract_fake_ai.ContractDrivenFakeAIResponder(contract)
        cells = responder.formal_artifact_cells()
        mutation_kinds = {cell["mutation_kind"] for cell in cells}

        self.assertEqual(mutation_kinds, set(contract_fake_ai.FORMAL_ARTIFACT_PROFILE_IDS))
        for cell in cells:
            self.assertEqual(cell["required_evidence_owner"], "contract_exhaustion_fake_ai_matrix")
            self.assertTrue(cell["contract_path"].startswith("artifact.flowguard_evidence.json"))

    def test_formal_artifact_registry_boundary_is_file_backed_and_current_contract_only(self) -> None:
        artifact_ids = set(formal_artifact_contracts.artifact_ids())
        flowguard_contract = formal_artifact_contracts.contract_for_artifact_id("flowguard_evidence.json")

        self.assertIn("flowguard_evidence.json", artifact_ids)
        self.assertEqual(
            flowguard_contract["target_root_field"],
            "evidence_output_policy.run_local_evidence_root",
        )
        self.assertEqual(
            formal_artifact_contracts.artifact_field_path(
                flowguard_contract,
                str(flowguard_contract["decision_field_path"]),
            ),
            runtime._FLOWGUARD_FORMAL_ARTIFACT_DECISION_FIELD,
        )
        self.assertEqual(
            tuple(
                flowguard_contract["allowed_value_options"][
                    flowguard_contract["decision_field_path"]
                ]
            ),
            runtime._FLOWGUARD_FORMAL_ARTIFACT_ALLOWED_PASS_DECISIONS,
        )
        for prefix in formal_artifact_contracts.EXCLUDED_LOGICAL_ARTIFACT_PREFIXES:
            with self.subTest(prefix=prefix):
                self.assertFalse(any(artifact_id.startswith(prefix) for artifact_id in artifact_ids))
        for runtime_file in formal_artifact_contracts.EXCLUDED_RUNTIME_FILE_FAMILIES:
            with self.subTest(runtime_file=runtime_file):
                self.assertNotIn(runtime_file, artifact_ids)

    def test_runtime_known_formal_artifact_fake_ai_cells_cover_registry(self) -> None:
        cells = contract_fake_ai.runtime_known_formal_artifact_cells()
        cell_ids = {cell["cell_id"] for cell in cells}
        path_index = {(cell["contract_path"], cell["mutation_kind"]) for cell in cells}

        for artifact_contract in formal_artifact_contracts.all_contracts():
            contract_id = str(artifact_contract["contract_id"])
            decision_path = formal_artifact_contracts.artifact_contract_path(
                artifact_contract,
                str(artifact_contract["decision_field_path"]),
            )
            artifact_path = formal_artifact_contracts.artifact_contract_path(artifact_contract)
            for mode in formal_artifact_contracts.fault_modes(artifact_contract):
                with self.subTest(contract_id=contract_id, mode=mode):
                    self.assertIn(f"fake_ai.formal_artifact.{contract_id}.{mode}", cell_ids)
                    expected_path = (
                        decision_path
                        if "decision" in mode or "blocks" in mode
                        else artifact_path
                    )
                    self.assertIn((expected_path, mode), path_index)

    def test_flowguard_formal_artifact_faults_reissue_with_executable_feedback(self) -> None:
        fault_cases = (
            ("missing", "pass", "flowguard_evidence.json"),
            ("wrong_path", "pass", "flowguard_evidence.json"),
            ("invalid_json", "pass", "flowguard_evidence.json"),
            (
                "missing_decision",
                "pass",
                "flowguard_evidence.json.model_test_alignment_report.decision",
            ),
            (
                "valid",
                "__invalid_option__",
                "flowguard_evidence.json.model_test_alignment_report.decision",
            ),
            (
                "valid",
                "missing_code_contract",
                "flowguard_evidence.json.model_test_alignment_report.decision",
            ),
        )
        for mode, decision, missing_field in fault_cases:
            with self.subTest(mode=mode, decision=decision):
                ledger, packet_id = self.issue_semantic_recheck_packet()
                packet = ledger["packets"][packet_id]
                responder = self.contract_driven_responder(packet)
                payload = responder.legal_payload()
                lease_id = self.assign_flowguard(
                    ledger,
                    packet_id,
                    f"fg-artifact-{mode}-{decision}".replace("_", "-"),
                )
                write_flowguard_evidence_artifact(
                    ledger,
                    packet_id,
                    decision=decision,
                    mode=mode,
                )

                result_id = runtime.submit_result(
                    ledger,
                    lease_id,
                    packet_id,
                    json.dumps(payload, sort_keys=True),
                )
                result = ledger["results"][result_id]
                reissue_packet_id = self.latest_reissue_packet_id(ledger, packet_id)
                reissue_packet = ledger["packets"][reissue_packet_id]
                reissue_body = json.loads(reissue_packet["body"])
                feedback_text = json.dumps(reissue_body, sort_keys=True)

                self.assertEqual(result["status"], "mechanical_contract_blocked")
                self.assertIn(missing_field, result["missing_required_fields"])
                self.assertIn("flowguard_evidence.json", feedback_text)
                self.assertIn("evidence_output_policy.run_local_evidence_root", feedback_text)
                self.assertIn("model_test_alignment_report.decision", feedback_text)
                self.assertIn("result body alone cannot satisfy", feedback_text)
                self.assertIn(
                    "flowguard_evidence.json.model_test_alignment_report.decision",
                    reissue_body["allowed_value_options"],
                )
                self.assertEqual(
                    reissue_body["allowed_value_options"][
                        "flowguard_evidence.json.model_test_alignment_report.decision"
                    ],
                    ["pass"],
                )

                corrected_lease_id = self.assign_flowguard(ledger, reissue_packet_id)
                corrected_payload = responder.repaired_payload_from_reissue(reissue_body)
                write_flowguard_evidence_artifact(ledger, reissue_packet_id)
                corrected_result_id = runtime.submit_result(
                    ledger,
                    corrected_lease_id,
                    reissue_packet_id,
                    json.dumps(corrected_payload, sort_keys=True),
                )

                self.assertEqual(ledger["results"][corrected_result_id]["status"], "accepted")

    def test_flowguard_failure_pm_repair_packet_projects_formal_evidence_path_and_failed_checks(self) -> None:
        ledger, packet_id = self.issue_semantic_recheck_packet()
        responder = self.contract_driven_responder(ledger["packets"][packet_id])
        payload = responder.legal_payload()
        payload["pm_visible_summary"] = ["FlowGuard found a current model-test gap."]
        payload["passed"] = False
        payload["blockers"] = [
            {
                "blocker_id": "fg-blocker-001",
                "blocker_class": "flowguard_failure",
                "summary": "FlowGuard evidence check failed.",
                "recommended_resolution": "Repair the current FlowGuard evidence failures.",
            }
        ]
        lease_id = self.assign_flowguard(ledger, packet_id, "fg-blocking-evidence")
        write_flowguard_evidence_artifact(ledger, packet_id, decision="missing_code_contract")

        result_id = runtime.submit_result(
            ledger,
            lease_id,
            packet_id,
            json.dumps(payload, sort_keys=True),
        )
        result = ledger["results"][result_id]
        blocker = next(iter(ledger["active_blockers"].values()))
        pm_packet = ledger["packets"][blocker["pm_repair_packet_id"]]
        pm_body = json.loads(pm_packet["body"])
        pm_body_text = json.dumps(pm_body, sort_keys=True)

        self.assertEqual(result["status"], "flowguard_blocked")
        self.assertEqual(blocker["blocker_class"], "flowguard_failure")
        self.assertTrue(pm_body["flowguard_evidence_path"].endswith("flowguard_evidence.json"))
        self.assertIn("semantic_contract_missing", pm_body_text)
        self.assertIn("flowguard_evidence_path", pm_body)
        self.assertIn("flowguard_evidence_path", pm_body["required_context_fields"])

    def test_subject_artifact_ids_remain_body_contract_feedback_not_file_artifacts(self) -> None:
        ledger, packet_id = self.issue_semantic_recheck_packet()
        packet = ledger["packets"][packet_id]
        envelope = packet["envelope"]
        profile_ids = list(envelope.get("result_contract_profile_ids") or [])
        profile_ids.append("flowguard.subject_artifacts_consumed_required")
        envelope["result_contract_profile_ids"] = profile_ids
        bindings = dict(envelope.get("result_contract_profile_bindings") or {})
        bindings["flowguard.subject_artifacts_consumed_required"] = {
            "artifact_ids": ["subject_packet:packet-subject-required-001"],
        }
        envelope["result_contract_profile_bindings"] = bindings
        responder = self.contract_driven_responder(packet)
        payload = responder.legal_payload()
        lease_id = self.assign_flowguard(ledger, packet_id, "fg-subject-artifact-missing")
        write_flowguard_evidence_artifact(ledger, packet_id)

        result_id = runtime.submit_result(
            ledger,
            lease_id,
            packet_id,
            json.dumps(payload, sort_keys=True),
        )
        result = ledger["results"][result_id]
        reissue_packet_id = self.latest_reissue_packet_id(ledger, packet_id)
        reissue_body = json.loads(ledger["packets"][reissue_packet_id]["body"])
        reissue_text = json.dumps(reissue_body, sort_keys=True)

        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertIn("subject_artifacts_consumed", result["missing_required_fields"])
        self.assertIn("subject_packet:packet-subject-required-001", result["blocked_reason"])
        self.assertIn("subject_packet:packet-subject-required-001", reissue_text)
        self.assertNotIn(
            "subject_packet:packet-subject-required-001",
            formal_artifact_contracts.artifact_ids(),
        )

    def test_repeated_formal_artifact_mechanical_blocks_reach_break_glass_threshold(self) -> None:
        ledger, packet_id = self.issue_semantic_recheck_packet()
        current_packet_id = packet_id
        for index in range(1, 6):
            packet = ledger["packets"][current_packet_id]
            responder = self.contract_driven_responder(packet)
            lease_id = self.assign_flowguard(ledger, current_packet_id)
            result_id = runtime.submit_result(
                ledger,
                lease_id,
                current_packet_id,
                json.dumps(responder.legal_payload(), sort_keys=True),
            )
            result = ledger["results"][result_id]

            self.assertEqual(result["status"], "mechanical_contract_blocked")
            self.assertIn("flowguard_evidence.json", result["missing_required_fields"])
            if index < 5:
                self.assertNotEqual(runtime.router_next_action(ledger).action_type, "control_plane_blocker")
                current_packet_id = self.latest_reissue_packet_id(ledger, current_packet_id)

        action = runtime.router_next_action(ledger)
        break_glass_events = [
            event
            for event in ledger["events"]
            if event["event_type"] == "repair_loop_break_glass_required"
        ]

        self.assertEqual(action.action_type, "control_plane_blocker")
        self.assertIn("flowguard_evidence.json", action.subject_id)
        self.assertTrue(break_glass_events)
        self.assertEqual(break_glass_events[-1]["payload"]["attempt_count"], 5)

    def test_contract_driven_fake_ai_review_window_profiles_are_declared(self) -> None:
        cells = contract_fake_ai.review_window_behavior_cells()
        profile_ids = {cell["mutation_kind"] for cell in cells}
        flow_ids = {cell["review_flow_id"] for cell in cells}
        material_state_classes = {cell["material_state_class"] for cell in cells}
        retry_count_classes = {cell["retry_count_class"] for cell in cells}

        self.assertLessEqual(set(contract_fake_ai.REVIEW_WINDOW_FAKE_AI_PROFILE_IDS), profile_ids)
        self.assertGreaterEqual(len(flow_ids), 9)
        self.assertEqual(
            material_state_classes,
            set(contract_fake_ai.review_window_contracts.REVIEW_WINDOW_MATERIAL_STATE_CLASSES),
        )
        self.assertEqual(
            retry_count_classes,
            set(contract_fake_ai.review_window_contracts.RETRY_COUNT_CLASSES),
        )
        cell_keys = {
            (
                cell["review_flow_id"],
                cell["mutation_kind"],
                cell["material_state_class"],
                cell["retry_count_class"],
            )
            for cell in cells
        }
        for flow_id in flow_ids:
            for profile_id in contract_fake_ai.REVIEW_WINDOW_FAKE_AI_PROFILE_IDS:
                for material_state in contract_fake_ai.review_window_contracts.REVIEW_WINDOW_MATERIAL_STATE_CLASSES:
                    for retry_class in contract_fake_ai.review_window_contracts.RETRY_COUNT_CLASSES:
                        self.assertIn(
                            (flow_id, profile_id, material_state, retry_class),
                            cell_keys,
                        )

        ledger, packet_id = self.issue_semantic_recheck_packet()
        responder = self.contract_driven_responder(ledger["packets"][packet_id])
        sample_window = {
            "review_flow_id": "node_acceptance_plan_review",
            "subject_lifecycle_stage": "node_plan_definition",
            "required_authorized_result_read_ids_before_submit": ["result-node-plan"],
        }
        for profile_id in contract_fake_ai.REVIEW_WINDOW_FAKE_AI_PROFILE_IDS:
            for material_state in contract_fake_ai.review_window_contracts.REVIEW_WINDOW_MATERIAL_STATE_CLASSES:
                for retry_class in contract_fake_ai.review_window_contracts.RETRY_COUNT_CLASSES:
                    payload = responder.review_window_behavior_payload(
                        profile_id,
                        sample_window,
                        material_state_class=material_state,
                        retry_count_class=retry_class,
                    )
                    trace = payload["review_window_trace"]
                    self.assertEqual(trace["material_state_class"], material_state)
                    self.assertEqual(trace["retry_count_class"], retry_class)
                    if retry_class == "same_failure_attempt_5":
                        self.assertEqual(trace["same_failure_retry_class"], "break_glass_threshold")

        skipped = responder.review_window_behavior_payload("reviewer_skips_required_read", sample_window)
        future = responder.review_window_behavior_payload("reviewer_future_stage_demand", sample_window)
        threshold = responder.review_window_behavior_payload(
            "reviewer_shallow_pass",
            sample_window,
            retry_count_class="same_failure_attempt_5",
        )

        self.assertEqual(skipped["review_window_trace"]["consumed_authorized_result_read_ids"], [])
        self.assertEqual(future["passed"], False)
        self.assertIn("future-stage", future["blockers"][0]["summary"])
        self.assertEqual(threshold["review_window_trace"]["same_failure_retry_class"], "break_glass_threshold")

        expected_score_profiles = {
            "reviewer_quality_score_10_exceeds_standard",
            "reviewer_quality_score_6_soft_pm_optimization",
            "reviewer_quantitative_gap_blocks",
            "reviewer_overblocks_sub9_soft_score",
            "reviewer_recheck_consumes_score_context",
        }
        self.assertLessEqual(expected_score_profiles, set(contract_fake_ai.REVIEW_WINDOW_FAKE_AI_PROFILE_IDS))
        expected_challenge_profiles = {
            "reviewer_stage_specific_challenge_pass",
            "reviewer_generic_optimization_only",
        }
        self.assertLessEqual(expected_challenge_profiles, set(contract_fake_ai.REVIEW_WINDOW_FAKE_AI_PROFILE_IDS))
        expected_core_downgrade_profiles = {
            "reviewer_reachable_only_downgrade_blocks",
            "reviewer_honest_missing_substitute_blocks",
            "reviewer_status_only_closure_blocks",
            "reviewer_partial_deliverable_count_blocks",
            "reviewer_weaker_child_skill_output_blocks",
        }
        self.assertEqual(
            set(contract_fake_ai.CORE_DELIVERABLE_DOWNGRADE_FAKE_AI_PROFILE_IDS),
            expected_core_downgrade_profiles,
        )
        self.assertLessEqual(expected_core_downgrade_profiles, set(contract_fake_ai.REVIEW_WINDOW_FAKE_AI_PROFILE_IDS))
        score_10 = responder.review_window_behavior_payload(
            "reviewer_quality_score_10_exceeds_standard",
            sample_window,
        )
        soft_6 = responder.review_window_behavior_payload(
            "reviewer_quality_score_6_soft_pm_optimization",
            sample_window,
        )
        quantitative = responder.review_window_behavior_payload(
            "reviewer_quantitative_gap_blocks",
            sample_window,
        )
        overblock = responder.review_window_behavior_payload(
            "reviewer_overblocks_sub9_soft_score",
            sample_window,
        )
        recheck = responder.review_window_behavior_payload(
            "reviewer_recheck_consumes_score_context",
            sample_window,
        )

        self.assertIn("Quality score: 10/10", score_10["pm_visible_summary"][0])
        self.assertEqual(score_10["review_window_trace"]["quality_score"], 10)
        self.assertEqual(soft_6["passed"], True)
        self.assertEqual(soft_6["blockers"], [])
        self.assertIn("Quality score: 6/10", soft_6["pm_visible_summary"][0])
        self.assertTrue(soft_6["review_window_trace"]["soft_score_pm_decision_support"])
        self.assertEqual(quantitative["passed"], False)
        self.assertIn("required 100 items, delivered 5, gap 95", quantitative["blockers"][0]["summary"])
        self.assertEqual(quantitative["review_window_trace"]["quantitative_gap"]["gap"], 95)
        self.assertEqual(overblock["passed"], False)
        self.assertTrue(overblock["review_window_trace"]["overblocked_soft_score"])
        self.assertTrue(recheck["review_window_trace"]["prior_score_context_consumed"])

        stage_specific = responder.review_window_behavior_payload(
            "reviewer_stage_specific_challenge_pass",
            sample_window,
        )
        generic_only = responder.review_window_behavior_payload(
            "reviewer_generic_optimization_only",
            sample_window,
        )
        self.assertTrue(stage_specific["review_window_trace"]["stage_specific_challenge_projected"])
        self.assertTrue(stage_specific["review_window_trace"]["stage_specific_challenge_performed"])
        self.assertEqual(
            stage_specific["review_window_trace"]["stage_challenge_binding_card_id"],
            "reviewer.node_acceptance_plan_review",
        )
        self.assertIn("node acceptance plan", stage_specific["pm_visible_summary"][0])
        self.assertIn("weakest evidence", stage_specific["pm_suggestion_items"][0])
        self.assertTrue(generic_only["review_window_trace"]["generic_optimization_only"])
        self.assertFalse(generic_only["review_window_trace"]["stage_specific_challenge_projected"])
        self.assertIn("mechanical pass style", generic_only["pm_visible_summary"][0])
        self.assertIn("consider optimization toward 9/10", generic_only["pm_suggestion_items"][0])

        for profile_id in expected_core_downgrade_profiles:
            with self.subTest(profile_id=profile_id):
                payload = responder.review_window_behavior_payload(profile_id, sample_window)
                trace = payload["review_window_trace"]
                self.assertEqual(payload["passed"], False)
                self.assertEqual(trace["minimum_hard_gate_passed"], False)
                self.assertTrue(trace["core_deliverable_non_downgrade_checked"])
                self.assertIn("core-deliverable", payload["blockers"][0]["blocker_id"])
                self.assertIn("existing blocker/repair/research/waiver/mutation/user-stop path", payload["recommended_resolution"])

    def test_body_semantic_recheck_context_without_profile_does_not_create_hidden_fields(self) -> None:
        ledger, packet_id = self.issue_semantic_recheck_packet(include_profile=False)
        packet = ledger["packets"][packet_id]
        packet_body = json.loads(packet["body"])
        report_contract = packet_body["current_handoff_contract"]["required_report_contract"]

        self.assertEqual(packet["envelope"].get("result_contract_profile_ids"), None)
        self.assertNotIn("semantic_recheck", report_contract["required_result_body_fields"])
        self.assertNotIn("semantic_recheck", report_contract["minimal_valid_shape"])
        self.assertNotIn(
            "semantic_recheck.subject_result_consumed",
            report_contract["allowed_value_options"],
        )

    def test_semantic_recheck_near_synonyms_reissue_with_correct_minimal_shape(self) -> None:
        ledger, packet_id = self.issue_semantic_recheck_packet()
        lease_id = self.assign_flowguard(ledger, packet_id, "fg-near-synonym")
        payload = flowguard_result_payload("FlowGuard used near-synonym semantic fields.")
        payload["semantic_recheck"] = {
            "blocker_id": "blocker-semantic-001",
            "authorized_result_body_consumed": True,
            "blocker_bound_semantic_requirement_satisfied": True,
            "repair_evidence_obligations_consumed": ["repair-obligation-001"],
            "coverage_boundary": "subject_bound_semantic",
        }

        result_id = runtime.submit_result(ledger, lease_id, packet_id, json.dumps(payload))
        result = ledger["results"][result_id]
        reissue_packet_id = self.latest_reissue_packet_id(ledger, packet_id)
        reissue_body = json.loads(ledger["packets"][reissue_packet_id]["body"])

        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertIn(
            "semantic_recheck.authorized_result_body_consumed",
            result["forbidden_fields_seen"],
        )
        self.assertIn(
            "subject_bound_semantic_coverage",
            reissue_body["minimal_valid_shape"]["semantic_recheck"],
        )
        self.assertNotIn("forbidden_aliases", reissue_body)
        self.assertEqual(
            reissue_body["minimal_valid_shape"]["semantic_recheck"]["consumed_repair_obligation_ids"],
            ["repair-obligation-001"],
        )

    def test_semantic_recheck_purpose_string_is_rejected_as_consumed_result_id(self) -> None:
        ledger, packet_id = self.issue_semantic_recheck_packet()
        packet = ledger["packets"][packet_id]
        lease_id = self.assign_flowguard(ledger, packet_id, "fg-purpose-string")
        write_flowguard_evidence_artifact(ledger, packet_id)
        payload = flowguard_result_payload("FlowGuard used a purpose string instead of the bound result id.")
        payload["semantic_recheck"] = {
            "blocker_id": "blocker-semantic-001",
            "subject_result_consumed": True,
            "subject_bound_semantic_coverage": True,
            "coverage_boundary": "subject_bound_semantic",
            "consumed_authorized_result_read_ids": ["subject_result_for_flowguard_check"],
            "consumed_repair_obligation_ids": ["repair-obligation-001"],
        }

        result_id = runtime.submit_result(ledger, lease_id, packet_id, json.dumps(payload))
        result = ledger["results"][result_id]
        reissue_packet_id = self.latest_reissue_packet_id(ledger, packet_id)
        reissue_body = json.loads(ledger["packets"][reissue_packet_id]["body"])

        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertIn(
            "semantic_recheck.consumed_authorized_result_read_ids[]",
            result["missing_required_fields"],
        )
        self.assertEqual(
            reissue_body["minimal_valid_shape"]["semantic_recheck"]["consumed_authorized_result_read_ids"],
            packet["envelope"]["result_contract_profile_bindings"][
                "flowguard.semantic_recheck_required"
            ]["authorized_result_read_ids"],
        )

    def test_semantic_recheck_wrong_value_then_corrected_retry_returns_to_legal_path(self) -> None:
        ledger, packet_id = self.issue_semantic_recheck_packet()
        packet = ledger["packets"][packet_id]
        lease_id = self.assign_flowguard(ledger, packet_id, "fg-wrong-type")
        payload = flowguard_result_payload("FlowGuard wrote an object instead of literal true.")
        payload["semantic_recheck"] = {
            "blocker_id": "blocker-semantic-001",
            "subject_result_consumed": True,
            "subject_bound_semantic_coverage": {"basis": "subject result consumed"},
            "coverage_boundary": "subject_bound_semantic",
            "consumed_authorized_result_read_ids": [
                packet["envelope"]["result_contract_profile_bindings"][
                    "flowguard.semantic_recheck_required"
                ]["authorized_result_read_ids"][0]
            ],
            "consumed_repair_obligation_ids": ["repair-obligation-001"],
        }

        result_id = runtime.submit_result(ledger, lease_id, packet_id, json.dumps(payload))
        result = ledger["results"][result_id]
        reissue_packet_id = self.latest_reissue_packet_id(ledger, packet_id)
        reissue_packet = ledger["packets"][reissue_packet_id]
        reissue_body = json.loads(reissue_packet["body"])

        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertIn(
            "semantic_recheck.subject_bound_semantic_coverage",
            result["missing_required_fields"],
        )
        corrected_lease_id = self.assign_flowguard(ledger, reissue_packet_id)
        write_flowguard_evidence_artifact(ledger, reissue_packet_id)
        corrected_payload = reissue_body["minimal_valid_shape"]
        corrected_result_id = runtime.submit_result(
            ledger,
            corrected_lease_id,
            reissue_packet_id,
            json.dumps(corrected_payload),
        )

        self.assertEqual(ledger["results"][corrected_result_id]["status"], "accepted")
        self.assertFalse(
            [
                event
                for event in ledger["events"]
                if event["event_type"] == "repair_loop_break_glass_required"
            ]
        )


if __name__ == "__main__":
    unittest.main()
