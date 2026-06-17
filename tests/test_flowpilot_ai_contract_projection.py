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
) -> None:
    if not ledger.get("run_root"):
        ledger["run_root"] = tempfile.mkdtemp(prefix="flowpilot-ai-contract-test-")
    packet = ledger["packets"][packet_id]
    path = runtime._flowguard_packet_evidence_artifact_path(ledger, packet)
    assert path is not None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "flowpilot.flowguard_evidence.v1",
                "model_test_alignment_report": {
                    "decision": decision,
                    "failed_predicates": [] if decision == "pass" else ["semantic_contract_missing"],
                },
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

    def test_contract_driven_fake_ai_uses_projected_minimal_shape_for_legal_path(self) -> None:
        ledger, packet_id = self.issue_semantic_recheck_packet()
        packet = ledger["packets"][packet_id]
        responder = self.contract_driven_responder(packet)

        self.assertEqual(responder.projection_findings(), [])
        payload = responder.legal_payload()
        self.assertEqual(payload["semantic_recheck"]["blocker_id"], "blocker-semantic-001")
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
