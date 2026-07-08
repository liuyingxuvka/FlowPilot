from __future__ import annotations

import importlib.util
import copy
import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS_ROOT = ROOT / "skills" / "flowpilot" / "assets"
RUNTIME_ROOT = ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_core_runtime"
if str(ASSETS_ROOT) not in sys.path:
    sys.path.insert(0, str(ASSETS_ROOT))

from flowpilot_core_runtime import (  # noqa: E402
    packet_result_contracts,
    packets,
    pointer_store,
    review_window_contracts,
    runtime as package_runtime,
    role_handoff,
    run_shell,
)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    old_path = list(sys.path)
    old_module = sys.modules.get(name)
    sys.modules[name] = module
    sys.path.insert(0, str(path.parent))
    sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old_path
        if old_module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = old_module
    return module


runtime = load_module("flowpilot_core_runtime_under_test", RUNTIME_ROOT / "runtime.py")
runtime_runner = load_module(
    "flowpilot_core_runtime_runner_under_test",
    ROOT / "simulations" / "run_flowpilot_core_runtime_checks.py",
)
development_runner = load_module(
    "flowpilot_core_runtime_development_runner_under_test",
    ROOT / "simulations" / "run_flowpilot_core_runtime_development_checks.py",
)
control_plane_duty_runner = load_module(
    "flowpilot_new_control_plane_duty_runner_under_test",
    ROOT / "simulations" / "run_flowpilot_new_control_plane_duty_checks.py",
)
control_plane_audit = load_module(
    "flowpilot_control_plane_friction_model_audit_under_test",
    ROOT / "simulations" / "flowpilot_control_plane_friction_model_audit.py",
)
control_surface = runtime.control_surface

DEFAULT_REVIEW_PM_SUGGESTION = (
    "PM decision-support: weakest evidence was inspected; PM may adopt a named verification or reject it because current evidence already supports this gate."
)
DEFAULT_TERMINAL_PM_SUGGESTION = (
    "PM decision-support: terminal replay passes; consider whether an optional quality improvement is useful."
)


def role_result_body(summary: str, **fields: object) -> str:
    payload: dict[str, object] = {
        "decision": "pass",
        "pm_visible_summary": [summary],
        "current_evidence_refs": ["current-runtime-evidence"],
    }
    payload.update(fields)
    return json.dumps(payload)


def flowguard_result_body(summary: str, **fields: object) -> str:
    payload: dict[str, object] = {
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
    payload.update(fields)
    return json.dumps(payload)


def semantic_recheck_fields(
    blocker_id: str,
    *,
    consumed_authorized_result_read_ids: list[str] | None = None,
    coverage_boundary: str = "subject_bound_semantic",
) -> dict[str, object]:
    return {
        "semantic_recheck": {
            "blocker_id": blocker_id,
            "subject_result_consumed": True,
            "subject_bound_semantic_coverage": True,
            "coverage_boundary": coverage_boundary,
            "consumed_authorized_result_read_ids": consumed_authorized_result_read_ids or [],
            "consumed_repair_obligation_ids": [],
        }
    }


def semantic_recheck_fields_from_packet(
    ledger: dict[str, object],
    flowguard_packet_id: str,
    blocker_id: str,
    *,
    coverage_boundary: str = "subject_bound_semantic",
) -> dict[str, object]:
    flowguard_packet_row = ledger["packets"][flowguard_packet_id]
    authorized_read_ids = [
        str(row.get("result_id") or "")
        for row in flowguard_packet_row["envelope"].get("authorized_result_reads", [])
        if row.get("required_before_submit") is True and str(row.get("result_id") or "")
    ]
    payload = semantic_recheck_fields(
        blocker_id,
        consumed_authorized_result_read_ids=authorized_read_ids,
        coverage_boundary=coverage_boundary,
    )
    profile_bindings = flowguard_packet_row["envelope"].get("result_contract_profile_bindings", {})
    semantic_binding = (
        profile_bindings.get("flowguard.semantic_recheck_required", {})
        if isinstance(profile_bindings, dict)
        else {}
    )
    obligation_ids = list(
        semantic_binding.get("repair_obligation_ids")
        if isinstance(semantic_binding, dict)
        else []
        or []
    )
    payload["semantic_recheck"]["consumed_repair_obligation_ids"] = obligation_ids
    return payload


def pm_repair_decision_body(
    ledger: dict[str, object],
    pm_packet_id: str,
    *,
    decision: str = "repair_current_scope",
    reason: str = "Current PM repair decision.",
    **fields: object,
) -> str:
    packet_body = json.loads(ledger["packets"][pm_packet_id]["body"])
    obligations = packet_body.get("repair_evidence_obligations") or []
    envelope = ledger["packets"][pm_packet_id].get("envelope", {})
    subject_blocker_id = ""
    if isinstance(envelope, dict):
        subject_blocker_id = str(envelope.get("subject_id") or "")
    payload: dict[str, object] = {
        "decision": decision,
        "reason": reason,
        "target_blocker_id": subject_blocker_id or "blocker-current",
        "next_action": decision,
    }
    if obligations:
        payload["repair_obligation_disposition"] = runtime._repair_obligation_disposition_minimal_shape(
            obligations,
            decision,
        )
    payload.update(fields)
    return json.dumps(payload)


def write_flowguard_evidence_artifact(
    ledger: dict[str, object],
    packet_id: str,
    *,
    decision: str = "pass",
) -> Path:
    if not ledger.get("run_root"):
        ledger["run_root"] = tempfile.mkdtemp(prefix="flowpilot-core-test-")
    packet = ledger["packets"][packet_id]
    packet_body = json.loads(packet["body"])
    evidence_policy = packet_body.get("evidence_output_policy")
    if isinstance(evidence_policy, dict):
        root_text = str(evidence_policy.get("run_local_evidence_root") or "")
        if "<" in root_text or ">" in root_text:
            evidence_root = Path(str(ledger["run_root"])) / "evidence" / "flowguard" / packet_id
            evidence_policy["run_local_evidence_root"] = str(evidence_root)
            packet["body"] = json.dumps(packet_body, sort_keys=True)
            packet["envelope"]["body_hash"] = runtime.hash_text(packet["body"])
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
    return path


def review_result_body(summary: str, **fields: object) -> str:
    passed = bool(fields.pop("passed", True))
    blocking_findings = fields.pop("blocking_findings", [])
    if not isinstance(blocking_findings, list):
        blocking_findings = []
    payload: dict[str, object] = {
        "pm_visible_summary": [summary],
        "reviewed_by_role": "human_like_reviewer",
        "passed": passed,
        "findings": blocking_findings if not passed else [],
        "blockers": blocking_findings,
        "pm_suggestion_items": [DEFAULT_REVIEW_PM_SUGGESTION],
        "contract_self_check": {
            "all_required_fields_present": True,
            "exact_field_names_used": True,
            "empty_required_arrays_explicit": True,
            "runtime_mechanical_validation_passed": True,
            "semantic_sufficiency_reviewed_by_runtime": False,
        },
    }
    payload.update(fields)
    return json.dumps(payload)


def authorize_background_collaboration(ledger: dict[str, object], *, authorized: bool = True) -> None:
    ledger["startup_intake"] = {
        "status": "confirmed",
        "current_run_authority": True,
        "controller_may_read_body": False,
        "body_text_included": False,
        "startup_answers": {"background_collaboration_authorized": authorized},
    }


def open_required_result_reads(ledger: dict[str, object], packet_id: str, lease_id: str) -> None:
    runtime.open_authorized_input_materials_for_role(ledger, packet_id, lease_id)


class FlowPilotCoreRuntimeTests(unittest.TestCase):
    def _ledger_with_final_quality_node(self) -> tuple[dict[str, object], str, str]:
        ledger = runtime.new_ledger("Goal", "Contract")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Do work"])
        ledger["recursive_route_execution_required"] = True
        node_id = "node-001"
        route_version = ledger["active_route_version"]
        ledger["routes"][str(route_version)]["node_order"] = [node_id]
        ledger["route_nodes"][node_id] = {
            "node_id": node_id,
            "route_version": route_version,
            "status": "active",
            "responsibility": "worker",
            "modeled_target": "development_process",
            "acceptance_criteria": ["accepted"],
            "packet_ids": [],
        }
        ledger["execution_frontier"] = {
            "active_route_version": route_version,
            "active_node_id": node_id,
            "completed_nodes": [],
            "status": "node_execution",
            "pending_route_mutation": None,
            "updated_at": runtime.now_iso(),
        }
        runtime_runner._mark_node_ready_for_final_closure(ledger, node_id)
        return ledger, node_id, str(ledger["latest_validation_evidence_id"])

    def _terminal_replay_body_for_packet(
        self,
        packet: dict[str, object],
        *,
        omit_last: bool = False,
        unexpected: bool = False,
    ) -> str:
        packet_body = json.loads(str(packet["body"]))
        targets = list(packet_body["segment_targets"])
        if omit_last:
            targets = targets[:-1]
        route_segment_replay = [
            {
                "segment_id": target["segment_id"],
                "segment_kind": target["segment_kind"],
                "status": "closed",
                "basis": "Current evidence closes this segment.",
            }
            for target in targets
        ]
        if unexpected:
            route_segment_replay.append(
                {
                    "segment_id": "unexpected-segment",
                    "segment_kind": "route_node",
                    "status": "closed",
                    "basis": "Unexpected segment should be rejected.",
                }
            )
        acceptance_item_closure = [
            {
                "id": str(target["segment_id"]).removeprefix("acceptance-item:"),
                "status": "closed",
                "basis": "Current terminal replay evidence closes this acceptance item.",
            }
            for target in targets
            if str(target.get("segment_id", "")).startswith("acceptance-item:")
        ] or [
            {
                "id": "acc-001",
                "status": "closed",
                "basis": "Current terminal replay evidence closes the active acceptance item.",
            }
        ]
        payload: dict[str, object] = {
            "final_artifact_refs": [
                {"id": "delivered-product", "status": "closed", "basis": "Final artifact inspected directly."}
            ],
            "acceptance_item_closure": acceptance_item_closure,
            "route_segment_replay": route_segment_replay,
            "waiver_records": [],
            "final_blockers": [],
        }
        return json.dumps(payload)

    def _terminal_replay_block_body_for_packet(self, packet: dict[str, object], *, omit_blockers: bool = False) -> str:
        payload = json.loads(self._terminal_replay_body_for_packet(packet))
        first_segment = payload["route_segment_replay"][0]
        first_segment["status"] = "blocked"
        first_segment["basis"] = "Delivered product signposting does not match the current accepted route."
        payload["final_blockers"] = [
            {
                "blocker_id": "terminal-blocker-001",
                "blocker_class": "terminal_closure",
                "recommended_resolution": "Repair delivered-product signposting and restart terminal replay.",
            }
        ]
        if omit_blockers:
            payload["final_blockers"] = []
        return json.dumps(payload)

    def _prepare_terminal_supplemental_projection(
        self,
        ledger: dict[str, object],
        node_id: str,
        *,
        contract_id: str = "terminal-supplemental-repair-r1",
        item_id: str = "terminal-gap-r1-item-1",
    ) -> None:
        ledger["acceptance_item_registry"] = {
            "schema_version": "flowpilot.acceptance_item_registry.v1",
            "items": [
                {
                    "acceptance_item_id": "acc-001",
                    "source_type": "user_explicit",
                    "summary": "Complete the current user goal.",
                    "quality_floor": "high_quality_required",
                    "future_evidence_rule": "Fresh implementation, validation, PM disposition, and terminal replay evidence.",
                    "status": "active",
                }
            ],
        }
        node = ledger["route_nodes"][node_id]
        node["acceptance_item_ids"] = ["acc-001"]
        node["supplemental_repair_contract_ids"] = [contract_id]
        node["supplemental_repair_item_ids"] = [item_id]
        disposition_id = node.get("pm_disposition_id")
        if disposition_id:
            disposition = ledger.setdefault("pm_dispositions", {}).setdefault(disposition_id, {})
            disposition["acceptance_item_disposition"] = [
                {
                    "acceptance_item_id": "acc-001",
                    "disposition": "accepted",
                    "basis": "Current node evidence closes this item.",
                }
            ]

    def _terminal_supplemental_contract(
        self,
        ledger: dict[str, object],
        blocker_id: str,
        node_id: str,
        *,
        round_number: int = 1,
        contract_id: str | None = None,
        item_id: str | None = None,
        gap_kind: str = "latent_high_standard_requirement",
        hygiene_category: str | None = None,
    ) -> dict[str, object]:
        contract_id = contract_id or f"terminal-supplemental-repair-r{round_number}"
        item_id = item_id or f"terminal-gap-r{round_number}-item-1"
        blocker = ledger["active_blockers"][blocker_id]
        repair_item = {
            "repair_item_id": item_id,
            "gap_kind": gap_kind,
            "original_goal_link": "The final product must satisfy the original user goal at high standard.",
            "reviewer_gap": "The delivered product still misses terminal signposting.",
            "required_repair": "Repair terminal signposting and rerun terminal replay.",
            "owner_repair_node_id": node_id,
            "acceptance_item_ids": ["acc-001"],
            "required_evidence": ["fresh implementation evidence", "fresh validation evidence"],
            "status": "open",
        }
        if hygiene_category is not None:
            repair_item["hygiene_category"] = hygiene_category
        return {
            "schema_version": "flowpilot.terminal_supplemental_repair_contract.v1",
            "contract_id": contract_id,
            "round_number": round_number,
            "original_contract_hash": ledger["contract_hash"],
            "terminal_blocker_id": blocker_id,
            "terminal_gap_report_result_id": blocker["result_id"],
            "pm_reason": "Terminal Reviewer found an original-goal gap that must be repaired.",
            "repair_items": [repair_item],
        }

    def _lease_ack_and_open_packet(
        self,
        ledger: dict[str, object],
        packet_id: str,
        responsibility: str,
    ) -> str:
        lease_id = runtime.lease_agent(ledger, responsibility, packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)
        open_required_result_reads(ledger, packet_id, lease_id)
        return lease_id

    def _complete_pm_continue_repair_gate(self, ledger: dict[str, object], blocker_id: str) -> None:
        flowguard_packet = runtime_runner._open_packet_by_kind(ledger, "flowguard_check")
        flowguard_lease = self._lease_ack_and_open_packet(ledger, flowguard_packet, "flowguard_operator")
        write_flowguard_evidence_artifact(ledger, flowguard_packet)
        runtime.submit_result(
            ledger,
            flowguard_lease,
            flowguard_packet,
            flowguard_result_body(
                "FlowGuard accepted the staged PM continue-repair decision.",
                **semantic_recheck_fields_from_packet(ledger, flowguard_packet, blocker_id),
            ),
        )

        gate = next(
            row
            for row in ledger["pm_decision_gates"].values()
            if row.get("status") == "awaiting_pm_flowguard_acceptance"
        )
        order = ledger["flowguard_work_orders"][gate["flowguard_order_id"]]
        pm_packet = runtime_runner._open_packet_by_kind(ledger, "pm_flowguard_acceptance")
        pm_lease = self._lease_ack_and_open_packet(ledger, pm_packet, "pm")
        payload = packet_result_contracts.minimal_valid_shape_for_family("pm_flowguard_acceptance.pm_flowguard_acceptance")
        payload.update(
            {
                "reason": "PM absorbed FlowGuard before continuing repair.",
                "flowguard_absorption": "PM accepted the current FlowGuard recheck for the staged repair decision.",
                "accepted_flowguard_result_id": order["proof_result_id"],
            }
        )
        runtime.submit_result(ledger, pm_lease, pm_packet, json.dumps(payload))

        review_packet = runtime_runner._open_packet_by_kind(ledger, "review")
        review_lease = self._lease_ack_and_open_packet(ledger, review_packet, "reviewer")
        runtime.submit_result(
            ledger,
            review_lease,
            review_packet,
            review_result_body("Reviewer accepted the PM-absorbed continue-repair decision."),
        )
        for _ in range(5):
            action = runtime.router_next_action(ledger)
            if action.action_type != "repair_accepted_packet":
                break
            runtime.repair_accepted_packet_assignment(ledger, action.subject_id)

    def _stopped_review_blocker_after_flowguard_failure(
        self,
    ) -> tuple[dict[str, object], str, str, str, str, str]:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(ledger, worker, packet_id, role_result_body("Worker completed the stopped-blocker fixture."))

        flowguard_packet = runtime_runner._open_packet_by_kind(ledger, "flowguard_check")
        flowguard_lease = runtime.lease_agent(
            ledger,
            "flowguard_operator",
            agent_id="flowguard-original",
            packet_id=flowguard_packet,
        )
        runtime.assign_packet(ledger, flowguard_packet, flowguard_lease)
        runtime.ack_lease(ledger, flowguard_lease, flowguard_packet)
        open_required_result_reads(ledger, flowguard_packet, flowguard_lease)
        write_flowguard_evidence_artifact(ledger, flowguard_packet)
        runtime.submit_result(
            ledger,
            flowguard_lease,
            flowguard_packet,
            flowguard_result_body("Original FlowGuard evidence passed before the stopped blocker."),
        )

        review_packet = runtime_runner._open_packet_by_kind(ledger, "review")
        review_lease = runtime.lease_agent(
            ledger,
            "reviewer",
            agent_id="reviewer-original",
            packet_id=review_packet,
        )
        runtime.assign_packet(ledger, review_packet, review_lease)
        runtime.ack_lease(ledger, review_lease, review_packet)
        open_required_result_reads(ledger, review_packet, review_lease)
        runtime.submit_result(
            ledger,
            review_lease,
            review_packet,
            review_result_body(
                "Reviewer requires rerunning the FlowGuard evidence path.",
                passed=False,
                blocker_class="flowguard_failure",
                recommended_resolution="rerun the FlowGuard evidence path",
                blocking_findings=[
                    {
                        "finding": "FlowGuard evidence path must be rerun.",
                        "required_repair": "rerun the FlowGuard evidence path",
                    }
                ],
            ),
        )
        blocker_id = next(
            blocker_id
            for blocker_id, blocker in ledger["active_blockers"].items()
            if blocker["gate_kind"] == "review"
        )
        pm_packet = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
        pm_lease = runtime.lease_agent(ledger, "pm", agent_id="pm-stop", packet_id=pm_packet)
        runtime.assign_packet(ledger, pm_packet, pm_lease)
        runtime.ack_lease(ledger, pm_lease, pm_packet)
        open_required_result_reads(ledger, pm_packet, pm_lease)
        runtime.submit_result(
            ledger,
            pm_lease,
            pm_packet,
            pm_repair_decision_body(
                ledger,
                pm_packet,
                decision="stop_for_user",
                reason="Controller repair is required.",
            ),
        )
        return ledger, packet_id, blocker_id, flowguard_packet, review_packet, pm_packet

    def test_runtime_assets_exist_and_document_boundaries(self) -> None:
        runtime_files = {path.name for path in RUNTIME_ROOT.iterdir() if path.is_file()}
        for required_file in {
            "__init__.py",
            "README.md",
            "runtime.py",
            "cli.py",
            "run_shell.py",
            "host.py",
            "router.py",
            "packets.py",
            "flowguard_orders.py",
            "review_closure.py",
            "cockpit.py",
            "migration.py",
            "role_handoff.py",
        }:
            with self.subTest(required_file=required_file):
                self.assertIn(required_file, runtime_files)
        readme = (RUNTIME_ROOT / "README.md").read_text(encoding="utf-8")
        for phrase in (
            "The ledger is the truth",
            "ACK and progress are liveness only",
            "FlowGuard work orders must name the modeled target",
            "Non-authoritative inputs include prior runtime state",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, readme)

    def test_replacement_worker_can_finish_but_closed_worker_late_output_is_blocked(self) -> None:
        report = runtime_runner.replacement_worker_success()
        self.assertTrue(report["ok"], report)
        self.assertTrue(report["accepted"])
        self.assertIn("closed_or_inactive_lease", report["details"]["late_result_rejected_reason"])

    def test_wrong_flowguard_target_self_review_stale_route_and_stale_evidence_block(self) -> None:
        for scenario_name in (
            "wrong_flowguard_target_blocks",
            "self_review_blocks",
            "stale_route_output_blocks",
            "stale_evidence_blocks",
        ):
            with self.subTest(scenario=scenario_name):
                report = runtime_runner.SCENARIOS[scenario_name]()
                self.assertTrue(report["ok"], report)
                self.assertFalse(report["accepted"])

    def test_ack_and_progress_do_not_complete_packet(self) -> None:
        report = runtime_runner.ack_only_timeout_stays_incomplete()
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["details"]["before_timeout"]["action_type"], "wait_for_result")
        self.assertEqual(report["details"]["after_timeout"]["action_type"], "replace_lease")

    def test_terminal_backward_replay_block_routes_to_terminal_replay(self) -> None:
        report = runtime_runner.terminal_backward_replay_block_does_not_replan()

        self.assertTrue(report["ok"], report)
        self.assertTrue(report["accepted"])
        self.assertEqual(report["details"]["next_action"]["action_type"], "issue_terminal_backward_replay_packet")

    def test_public_console_hides_sealed_bodies(self) -> None:
        report = runtime_runner.console_does_not_leak_sealed_bodies()
        self.assertTrue(report["ok"], report)
        self.assertFalse(report["details"]["leaked"])
        rendered = json.dumps(report, sort_keys=True)
        self.assertNotIn("SEALED_TASK_BODY", rendered)
        self.assertNotIn("SEALED_RESULT_BODY", rendered)

    def test_current_progress_fraction_is_zero_before_work_expands(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")

        progress = runtime.current_progress_fraction(ledger)

        self.assertEqual(progress["display"], "0/1")
        self.assertEqual(progress["ended_nodes"], 0)
        self.assertEqual(progress["expanded_nodes"], 1)
        self.assertEqual(progress["source"], "initial_planning_node")
        self.assertFalse(progress["packet_projection_used"])
        self.assertFalse(progress["percent_provided"])
        self.assertTrue(progress["controller_relay_only"])
        self.assertFalse(progress["sealed_bodies_visible"])

    def test_current_progress_fraction_does_not_use_packet_projection_before_route_nodes(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Do work"])
        packet_id = runtime.issue_task_packet(ledger, "worker", "Do work", "SEALED_TASK_BODY")

        self.assertEqual(runtime.current_progress_fraction(ledger)["display"], "0/1")

        lease_id = runtime.lease_agent(ledger, "worker", agent_id="worker-1", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)
        runtime.record_progress(ledger, lease_id, packet_id, "still_working")
        progress = runtime.current_progress_fraction(ledger)

        self.assertEqual(progress["display"], "0/1")
        self.assertEqual(progress["ended_nodes"], 0)
        self.assertEqual(progress["expanded_nodes"], 1)
        self.assertEqual(progress["source"], "initial_planning_node")
        self.assertFalse(progress["packet_projection_used"])

    def test_task_packet_acceptance_criteria_include_replayable_artifact_rule(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        runtime.create_route(ledger, "Route", ["Do work"])

        packet_id = runtime.issue_task_packet(
            ledger,
            "worker",
            "Do work",
            "SEALED_TASK_BODY",
            acceptance_criteria=["specific criterion"],
        )

        criteria = ledger["packets"][packet_id]["envelope"]["acceptance_criteria"]
        self.assertEqual(criteria[0], "specific criterion")
        self.assertIn(runtime.REPLAYABLE_ARTIFACT_ACCEPTANCE_CRITERION, criteria)

    def test_packet_handoff_contract_is_visible_in_envelope_body_and_role_handoff(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Do work"])
        packet_id = runtime.issue_task_packet(
            ledger,
            "worker",
            "Do work",
            json.dumps({"instruction": "Produce the current deliverable."}),
            route_scope="node",
        )
        packet = ledger["packets"][packet_id]
        envelope_contract = packet["envelope"]["current_handoff_contract"]
        body = json.loads(packet["body"])

        self.assertEqual(body["current_handoff_contract"], envelope_contract)
        self.assertEqual(envelope_contract["contract_family_id"], "task.node")
        self.assertEqual(
            envelope_contract["required_report_contract"]["required_result_body_fields"],
            ["decision", "pm_visible_summary", "current_evidence_refs"],
        )
        self.assertEqual(envelope_contract["downstream_consumer"]["next_consumer_authority"], "runtime_router")
        self.assertTrue(envelope_contract["status_projection_requirements"]["repair_chain_visible_when_current"])
        self.assertEqual(runtime.hash_text(packet["body"]), packet["envelope"]["body_hash"])

        lease_id = runtime.lease_agent(ledger, "worker", agent_id="worker-handoff", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, lease_id)
        with tempfile.TemporaryDirectory() as tmp:
            handoff = role_handoff.render_current_packet_handoff(
                ledger,
                root=Path(tmp),
                script_path=ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_new.py",
                run_id="run-test",
                packet_id=packet_id,
                lease_id=lease_id,
            )

        self.assertEqual(handoff["current_handoff_contract"], envelope_contract)
        self.assertIn("current_handoff_contract", handoff["text"])

    def test_role_handoff_tells_recipient_to_read_all_authorized_bodies(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["First source", "Second source", "Repair"])
        source_result_ids: list[str] = []
        for index in range(2):
            source_packet = runtime.issue_task_packet(
                ledger,
                "worker",
                f"Produce source evidence {index}",
                json.dumps({"instruction": f"source {index}"}),
                route_scope="node",
            )
            source_lease = runtime.lease_agent(ledger, "worker", packet_id=source_packet)
            runtime.assign_packet(ledger, source_packet, source_lease)
            runtime.ack_lease(ledger, source_lease, source_packet)
            source_result_ids.append(
                runtime.submit_result(
                    ledger,
                    source_lease,
                    source_packet,
                    role_result_body(f"Source result {index}."),
                )
            )

        repair_packet = runtime.issue_task_packet(
            ledger,
            "worker",
            "Repair using all related evidence",
            json.dumps({"instruction": "repair"}),
            authorized_result_reads=[
                runtime._authorized_read_for_result(
                    ledger,
                    source_result_ids[0],
                    allowed_roles=["worker"],
                    purpose="blocked_target_result_body_for_repair",
                    required_before_submit=True,
                ),
                runtime._authorized_read_for_result(
                    ledger,
                    source_result_ids[1],
                    allowed_roles=["worker"],
                    purpose="upstream_context_for_blocker",
                    required_before_submit=True,
                ),
            ],
        )
        repair_lease = runtime.lease_agent(ledger, "worker", packet_id=repair_packet)
        runtime.assign_packet(ledger, repair_packet, repair_lease)
        with tempfile.TemporaryDirectory() as tmp:
            handoff = role_handoff.render_current_packet_handoff(
                ledger,
                root=Path(tmp),
                script_path=ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_new.py",
                run_id="run-test",
                packet_id=repair_packet,
                lease_id=repair_lease,
            )

        text = handoff["text"]
        self.assertEqual(
            [row["result_id"] for row in handoff["authorized_result_reads"]],
            source_result_ids,
        )
        self.assertIn("Read every delivered authorized body before submit-result", text)
        self.assertIn("blocker, target, and upstream context bodies", text)
        self.assertIn("one selected result body", text)
        self.assertIn("multiple authorized bodies", text)

    def test_review_packet_authorizes_matching_flowguard_result_read(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        subject_result_id = runtime.submit_result(
            ledger,
            worker,
            packet_id,
            role_result_body("Worker produced implementation result evidence."),
        )
        flowguard_packet = runtime_runner._open_packet_by_kind(ledger, "flowguard_check")
        flowguard_lease = runtime.lease_agent(
            ledger,
            "flowguard_operator",
            agent_id="flowguard-current",
            packet_id=flowguard_packet,
        )
        runtime.assign_packet(ledger, flowguard_packet, flowguard_lease)
        runtime.ack_lease(ledger, flowguard_lease, flowguard_packet)
        open_required_result_reads(ledger, flowguard_packet, flowguard_lease)
        write_flowguard_evidence_artifact(ledger, flowguard_packet)
        flowguard_result_id = runtime.submit_result(
            ledger,
            flowguard_lease,
            flowguard_packet,
            flowguard_result_body("FlowGuard evidence passed for the current packet."),
        )

        review_packet = runtime_runner._open_packet_by_kind(ledger, "review")
        review_record = ledger["packets"][review_packet]
        read_ids = {
            row["result_id"]
            for row in review_record["envelope"]["authorized_result_reads"]
            if row.get("required_before_submit") is True
        }
        review_body = json.loads(review_record["body"])
        handoff_required_reads = set(
            review_body["current_handoff_contract"]["input_material_manifest"]["required_authorized_reads_before_submit"]
        )

        self.assertIn(subject_result_id, read_ids)
        self.assertIn(flowguard_result_id, read_ids)
        self.assertIn(subject_result_id, handoff_required_reads)
        self.assertIn(flowguard_result_id, handoff_required_reads)
        self.assertEqual(
            review_body["flowguard_evidence_manifest"]["entries"][0]["flowguard_result_id"],
            flowguard_result_id,
        )

        reviewer = runtime.lease_agent(ledger, "reviewer", agent_id="reviewer-current", packet_id=review_packet)
        runtime.assign_packet(ledger, review_packet, reviewer)
        runtime.ack_lease(ledger, reviewer, review_packet)
        delivered = runtime.open_authorized_input_materials_for_role(ledger, review_packet, reviewer)
        accepted_review_result = runtime.submit_result(
            ledger,
            reviewer,
            review_packet,
            review_result_body("Reviewer received worker and FlowGuard evidence through open-packet."),
        )

        self.assertEqual({row["result_id"] for row in delivered}, {subject_result_id, flowguard_result_id})
        self.assertEqual(ledger["results"][accepted_review_result]["status"], "accepted")

    def test_reviewer_report_without_pm_suggestions_reissues_current_contract(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(ledger, worker, packet_id, role_result_body("Worker produced current result."))
        flowguard_packet = runtime_runner._open_packet_by_kind(ledger, "flowguard_check")
        flowguard_lease = runtime.lease_agent(
            ledger,
            "flowguard_operator",
            agent_id="flowguard-suggestion-required",
            packet_id=flowguard_packet,
        )
        runtime.assign_packet(ledger, flowguard_packet, flowguard_lease)
        runtime.ack_lease(ledger, flowguard_lease, flowguard_packet)
        open_required_result_reads(ledger, flowguard_packet, flowguard_lease)
        write_flowguard_evidence_artifact(ledger, flowguard_packet)
        runtime.submit_result(
            ledger,
            flowguard_lease,
            flowguard_packet,
            flowguard_result_body("FlowGuard evidence passed."),
        )

        review_packet = runtime_runner._open_packet_by_kind(ledger, "review")
        reviewer = runtime.lease_agent(
            ledger,
            "reviewer",
            agent_id="reviewer-empty-suggestion",
            packet_id=review_packet,
        )
        runtime.assign_packet(ledger, review_packet, reviewer)
        runtime.ack_lease(ledger, reviewer, review_packet)
        open_required_result_reads(ledger, review_packet, reviewer)

        result_id = runtime.submit_result(
            ledger,
            reviewer,
            review_packet,
            review_result_body("Reviewer passed but forgot PM decision-support.", pm_suggestion_items=[]),
        )

        result = ledger["results"][result_id]
        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertIn("pm_suggestion_items", result["missing_required_fields"])
        reissue_packet_id = next(
            event["payload"]["fresh_packet_id"]
            for event in reversed(ledger["events"])
            if event["event_type"] == "current_contract_reissue_packet_issued"
            and event["payload"]["blocked_packet_id"] == review_packet
        )
        reissue_body = json.loads(ledger["packets"][reissue_packet_id]["body"])
        self.assertIn("pm_suggestion_items", reissue_body["non_empty_array_fields"])
        self.assertTrue(reissue_body["minimal_valid_shape"]["pm_suggestion_items"])

    def test_create_new_reviewer_rejects_reusing_forbidden_prior_agent(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(ledger, worker, packet_id, role_result_body("Worker produced current result."))
        flowguard_packet = runtime_runner._open_packet_by_kind(ledger, "flowguard_check")
        flowguard_lease = runtime.lease_agent(
            ledger,
            "flowguard_operator",
            agent_id="flowguard-self-review-lease",
            packet_id=flowguard_packet,
        )
        runtime.assign_packet(ledger, flowguard_packet, flowguard_lease)
        runtime.ack_lease(ledger, flowguard_lease, flowguard_packet)
        open_required_result_reads(ledger, flowguard_packet, flowguard_lease)
        write_flowguard_evidence_artifact(ledger, flowguard_packet)
        runtime.submit_result(
            ledger,
            flowguard_lease,
            flowguard_packet,
            flowguard_result_body("FlowGuard evidence passed."),
        )
        review_packet = runtime_runner._open_packet_by_kind(ledger, "review")

        prior_reviewer = runtime.lease_agent(ledger, "reviewer", agent_id="worker-1")
        self.assertEqual(ledger["leases"][prior_reviewer]["agent_id"], "worker-1")
        assignment = runtime.resolve_role_assignment(ledger, "reviewer", packet_id=review_packet)
        self.assertEqual(assignment["disposition"], "create_new_role")
        self.assertEqual(assignment["prior_agent_id"], "worker-1")
        self.assertEqual(assignment["replacement_reason"], "reviewer_self_review_forbidden")

        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "cannot reuse forbidden prior agent id"):
            runtime.lease_agent(
                ledger,
                "reviewer",
                agent_id="worker-1",
                packet_id=review_packet,
                assignment_id=assignment["assignment_id"],
            )

        reviewer = runtime.lease_agent(
            ledger,
            "reviewer",
            agent_id="reviewer-replacement",
            packet_id=review_packet,
            assignment_id=assignment["assignment_id"],
        )
        self.assertEqual(ledger["leases"][reviewer]["agent_id"], "reviewer-replacement")

    def test_flowguard_operator_rejects_checking_own_target_result(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(ledger, worker, packet_id, role_result_body("Worker produced current result."))
        flowguard_packet = runtime_runner._open_packet_by_kind(ledger, "flowguard_check")

        prior_flowguard = runtime.lease_agent(ledger, "flowguard_operator", agent_id="worker-1")
        self.assertEqual(ledger["leases"][prior_flowguard]["agent_id"], "worker-1")
        assignment = runtime.resolve_role_assignment(ledger, "flowguard_operator", packet_id=flowguard_packet)
        self.assertEqual(assignment["disposition"], "create_new_role")
        self.assertEqual(assignment["prior_agent_id"], "worker-1")
        self.assertEqual(assignment["replacement_reason"], "flowguard_operator_self_check_forbidden")

        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "cannot reuse forbidden prior agent id"):
            runtime.lease_agent(
                ledger,
                "flowguard_operator",
                agent_id="worker-1",
                packet_id=flowguard_packet,
                assignment_id=assignment["assignment_id"],
            )

        replacement = runtime.lease_agent(
            ledger,
            "flowguard_operator",
            agent_id="flowguard-replacement",
            packet_id=flowguard_packet,
            assignment_id=assignment["assignment_id"],
        )
        self.assertEqual(ledger["leases"][replacement]["agent_id"], "flowguard-replacement")

    def test_flowguard_operator_self_check_submission_is_mechanically_blocked(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(ledger, worker, packet_id, role_result_body("Worker produced current result."))
        flowguard_packet = runtime_runner._open_packet_by_kind(ledger, "flowguard_check")
        flowguard_lease = runtime.lease_agent(
            ledger,
            "flowguard_operator",
            agent_id="flowguard-original",
            packet_id=flowguard_packet,
        )
        runtime.assign_packet(ledger, flowguard_packet, flowguard_lease)
        runtime.ack_lease(ledger, flowguard_lease, flowguard_packet)
        open_required_result_reads(ledger, flowguard_packet, flowguard_lease)
        write_flowguard_evidence_artifact(ledger, flowguard_packet)

        ledger["leases"][flowguard_lease]["agent_id"] = "worker-1"
        result_id = runtime.submit_result(
            ledger,
            flowguard_lease,
            flowguard_packet,
            flowguard_result_body("Illegal same-agent FlowGuard self-check."),
        )

        result = ledger["results"][result_id]
        self.assertEqual(result["status"], "blocked")
        self.assertIn("flowguard_operator_self_check_forbidden", result["mechanical_blockers"])
        self.assertEqual(ledger["packets"][flowguard_packet]["status"], "result_blocked")

    def test_flowguard_operator_reuse_allowed_for_different_target_producer(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        reusable_flowguard = runtime.lease_agent(ledger, "flowguard_operator", agent_id="flowguard-reusable")
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(ledger, worker, packet_id, role_result_body("Worker produced current result."))
        flowguard_packet = runtime_runner._open_packet_by_kind(ledger, "flowguard_check")

        assignment = runtime.resolve_role_assignment(ledger, "flowguard_operator", packet_id=flowguard_packet)

        self.assertEqual(assignment["disposition"], "reuse_existing_role")
        self.assertEqual(assignment["effective_agent_id"], "flowguard-reusable")
        self.assertEqual(assignment["replacement_reason"], "")
        lease = runtime.lease_agent(
            ledger,
            "flowguard_operator",
            packet_id=flowguard_packet,
            assignment_id=assignment["assignment_id"],
        )
        self.assertNotEqual(lease, reusable_flowguard)
        self.assertEqual(ledger["leases"][lease]["agent_id"], "flowguard-reusable")
        self.assertTrue(ledger["leases"][lease]["role_continuity"]["reused"])

    def test_system_validation_rejects_blocked_or_self_review_records(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        subject_result_id = runtime.submit_result(
            ledger,
            worker,
            packet_id,
            role_result_body("Worker result cannot be validated by self-review."),
        )
        review_id = runtime.review_result(
            ledger,
            subject_result_id,
            worker,
            decision="accept",
            checks_evidence=True,
            direct_evidence_ids=[],
        )

        evidence_id = runtime._record_system_validation_for_packet(
            ledger,
            packet_id,
            source_packet_id=packet_id,
            source_result_id=subject_result_id,
            review_id=review_id,
        )

        evidence = ledger["validation_evidence"][evidence_id]
        self.assertEqual(evidence["status"], "failed")
        self.assertIn("review_not_accepted:block", evidence["blockers"])
        self.assertIn("review_not_independent:self_review", evidence["blockers"])
        self.assertIn("review_missing_direct_evidence", evidence["blockers"])

    def test_current_progress_fraction_counts_undispositioned_nodes_when_node_order_shrinks(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        ledger["active_route_version"] = 1
        ledger["routes"] = {
            "1": {"route_version": 1, "status": "active", "node_order": ["node-cover-active-acceptance-items"]},
        }
        ledger["route_nodes"] = {
            "node-previous-accepted": {
                "node_id": "node-previous-accepted",
                "route_version": 1,
                "status": "accepted",
            },
            "node-previous-awaiting": {
                "node_id": "node-previous-awaiting",
                "route_version": 1,
                "status": "awaiting_pm_disposition",
            },
            "node-cover-active-acceptance-items": {
                "node_id": "node-cover-active-acceptance-items",
                "route_version": 1,
                "status": "running",
            },
        }

        progress = runtime.current_progress_fraction(ledger)

        self.assertEqual(progress["display"], "2/4")
        self.assertEqual(progress["ended_nodes"], 2)
        self.assertEqual(progress["expanded_nodes"], 4)
        self.assertEqual(progress["source"], "route_nodes_lifecycle_with_initial_planning_node")
        self.assertFalse(progress["includes_repair_generations"])
        self.assertFalse(progress["packet_projection_used"])

    def test_current_progress_fraction_repair_replacement_removes_superseded_node(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        ledger["active_route_version"] = 2
        ledger["routes"] = {
            "1": {"route_version": 1, "status": "superseded", "node_order": ["node-1", "node-2", "node-3"]},
            "2": {
                "route_version": 2,
                "status": "active",
                "node_order": ["node-1", "node-2-repair-v2", "node-3"],
            },
        }
        ledger["route_nodes"] = {
            "node-1": {"node_id": "node-1", "route_version": 1, "status": "accepted"},
            "node-2": {
                "node_id": "node-2",
                "route_version": 1,
                "status": "superseded",
                "repair_generation": 3,
                "superseded_by": "node-2-repair-v2",
            },
            "node-2-repair-v2": {
                "node_id": "node-2-repair-v2",
                "route_version": 2,
                "status": "running",
                "repair_generation": 1,
            },
            "node-3": {"node_id": "node-3", "route_version": 1, "status": "pending"},
        }

        progress = runtime.current_progress_fraction(ledger)

        self.assertEqual(progress["display"], "2/4")
        self.assertEqual(progress["ended_nodes"], 2)
        self.assertEqual(progress["expanded_nodes"], 4)
        self.assertEqual(progress["repair_generations"], 1)
        self.assertEqual(progress["source"], "route_nodes_lifecycle_with_initial_planning_node")
        self.assertTrue(progress["includes_repair_generations"])
        self.assertFalse(progress["packet_projection_used"])

    def test_public_console_exposes_progress_fraction_without_completion_authority(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        ledger["active_route_version"] = 1
        ledger["routes"] = {
            "1": {"route_version": 1, "status": "active", "node_order": ["node-1", "node-2"]},
        }
        ledger["route_nodes"] = {
            "node-1": {"node_id": "node-1", "status": "accepted", "repair_generation": 0},
            "node-2": {"node_id": "node-2", "status": "running", "repair_generation": 0},
        }

        full = runtime.render_console(ledger)
        compact = runtime.render_compact_console(ledger)

        self.assertEqual(full["progress_fraction"]["display"], "2/3")
        self.assertEqual(compact["progress_fraction"]["display"], "2/3")
        self.assertFalse(compact["progress_fraction"]["percent_provided"])
        self.assertEqual(compact["counts"]["progress_ended_nodes"], 2)
        self.assertEqual(compact["counts"]["progress_expanded_nodes"], 3)
        self.assertEqual(compact["status_projection_authority"], "display_only")

    def test_reassignment_supersedes_older_active_packet_lease(self) -> None:
        ledger, packet_id, first_lease = runtime_runner._base_ledger()
        assignment = runtime.resolve_role_assignment(ledger, "worker", packet_id=packet_id, host_kind="fake")
        second_lease = runtime.lease_agent(
            ledger,
            "worker",
            packet_id=packet_id,
            assignment_id=assignment["assignment_id"],
        )

        runtime.assign_packet(ledger, packet_id, second_lease)

        self.assertEqual(ledger["packets"][packet_id]["assigned_lease_id"], second_lease)
        self.assertEqual(ledger["leases"][first_lease]["status"], "superseded")
        self.assertEqual(ledger["leases"][first_lease]["superseded_by"], second_lease)
        self.assertEqual(ledger["leases"][second_lease]["status"], "active")
        self.assertEqual(ledger["leases"][second_lease]["packet_id"], packet_id)

    def test_background_collaboration_ack_required_before_role_assignment(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        authorize_background_collaboration(ledger, authorized=False)
        runtime.create_route(ledger, "Route", ["Do work"])
        packet_id = runtime.issue_task_packet(ledger, "worker", "Do work", "SEALED_TASK_BODY")

        assignment = runtime.resolve_role_assignment(ledger, "worker", packet_id=packet_id, host_kind="fake")

        self.assertEqual(assignment["status"], "blocked")
        self.assertEqual(assignment["disposition"], "blocked")
        self.assertIn("background_collaboration_authorized=true required", assignment["blocker_reason"])
        self.assertIn("background_collaboration_authorized_disabled", assignment["blocker_reason"])
        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "background_collaboration_authorized=true required"):
            runtime.lease_agent(ledger, "worker", agent_id="worker-1", packet_id=packet_id)
        self.assertFalse(ledger["leases"])

    def test_fake_ai_result_without_current_background_ack_is_blocked_then_corrected(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Do work"])
        packet_id = runtime.issue_task_packet(ledger, "worker", "Do work", "SEALED_TASK_BODY")
        lease_id = runtime.lease_agent(ledger, "worker", agent_id="fake-worker", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)

        ledger["startup_intake"]["startup_answers"]["background_collaboration_authorized"] = False
        blocked_result = runtime.submit_result(
            ledger,
            lease_id,
            packet_id,
            role_result_body("Fake AI submitted without current background acknowledgement."),
        )

        self.assertEqual(ledger["results"][blocked_result]["status"], "blocked")
        self.assertIn(
            "background_collaboration_authorized_disabled",
            ledger["results"][blocked_result]["mechanical_blockers"],
        )
        self.assertEqual(ledger["packets"][packet_id]["status"], "result_blocked")
        self.assertFalse(ledger["packets"][packet_id].get("accepted_result_id"))

        ledger["startup_intake"]["startup_answers"]["background_collaboration_authorized"] = True
        corrected_result = runtime.submit_result(
            ledger,
            lease_id,
            packet_id,
            role_result_body("Fake AI submitted after the current background acknowledgement was restored."),
        )

        self.assertEqual(ledger["results"][corrected_result]["status"], "mechanically_valid")
        self.assertNotIn(
            "background_collaboration_authorized_disabled",
            ledger["results"][corrected_result]["mechanical_blockers"],
        )

    def test_final_preflight_blocks_stale_active_accepted_packet_lease(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime_runner._complete_happy_path(ledger, packet_id, worker)
        stale_lease = runtime._next_id(ledger, "lease")
        ledger["leases"][stale_lease] = {
            **ledger["leases"][worker],
            "lease_id": stale_lease,
            "agent_id": "stale-worker",
            "status": "active",
            "packet_id": packet_id,
            "ack_received": True,
        }

        health = runtime.accepted_packet_lease_health(ledger)
        preflight = runtime.final_return_preflight(ledger)

        self.assertFalse(health["ok"])
        self.assertEqual(health["findings"][0]["active_lease_ids"], [stale_lease])
        self.assertFalse(preflight["allowed"])
        self.assertIn(f"accepted_packet_lease_health:{packet_id}", preflight["blockers"])
        self.assertEqual(runtime.router_next_action(ledger).action_type, "repair_accepted_packet")

    def test_compact_status_projection_hides_sealed_bodies(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime_runner._complete_happy_path(ledger, packet_id, worker)

        compact = runtime.render_compact_console(ledger)
        rendered = json.dumps(compact, sort_keys=True)

        self.assertEqual(compact["projection"], "compact_controller_status")
        self.assertFalse(compact["sealed_bodies_visible"])
        self.assertNotIn("SEALED_TASK_BODY", rendered)
        self.assertNotIn("SEALED_RESULT_BODY", rendered)
        self.assertIn("body_free", compact["body_policy"])

    def test_terminal_status_projection_converges_current_console_closure_and_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            shell = run_shell.create_run_shell(Path(tmp), "Goal", "Contract", run_id="run-status-projection")
            ledger = run_shell.load_run_ledger(shell)
            ledger["closure"] = {"decision": "complete", "blockers": []}
            package_runtime.record_terminal_lifecycle(
                ledger,
                "stopped_by_user",
                reason="terminal closure accepted",
            )

            run_shell.save_run_ledger(shell, ledger)

            saved_ledger = json.loads(shell.ledger_path.read_text(encoding="utf-8"))
            console = json.loads((shell.run_root / "console" / "status.json").read_text(encoding="utf-8"))
            final_closure = json.loads((shell.run_root / "closure" / "final_closure.json").read_text(encoding="utf-8"))
            current = json.loads((shell.root / ".flowpilot" / "current.json").read_text(encoding="utf-8"))

        projection = saved_ledger["status_projection"]
        for surface in (projection, console, final_closure, current):
            self.assertEqual(surface["run_id"], "run-status-projection")
            self.assertEqual(surface["closure_decision"], "complete")
            self.assertTrue(surface["controller_stop_allowed"])
            self.assertTrue(surface["final_return_allowed"])
            self.assertTrue(surface["updated_at"])
        self.assertNotEqual(projection["display_surface"]["active"], "unknown")
        self.assertEqual(console["status_projection_authority"], "display_only")

    def test_role_memory_seed_exposes_only_current_visible_blockers(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        ledger["active_blockers"]["blocker-cleared"] = {
            "blocker_id": "blocker-cleared",
            "status": "cleared",
            "packet_id": "",
            "subject_packet_id": "",
            "repair_target_packet_id": "",
            "required_recheck_role": "reviewer",
            "owner_role": "worker",
            "blocker_class": "local_artifact",
            "cleared_by_outcome_id": "outcome-accepted",
        }
        ledger["active_blockers"]["blocker-current"] = {
            "blocker_id": "blocker-current",
            "status": "active",
            "packet_id": "",
            "subject_packet_id": "",
            "repair_target_packet_id": "",
            "required_recheck_role": "reviewer",
            "owner_role": "worker",
            "blocker_class": "local_artifact",
            "cleared_by_outcome_id": "",
        }

        seed = runtime._build_role_memory_seed(ledger, "pm")
        blocker_ids = {row["blocker_id"] for row in seed["active_blockers"]}

        self.assertEqual(blocker_ids, {"blocker-current"})

    def test_repair_dossier_projection_does_not_keep_noncurrent_blocker_active(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        blocker = {
            "blocker_id": "blocker-cleared",
            "status": "cleared",
            "packet_id": "",
            "subject_packet_id": "",
            "repair_target_packet_id": "",
            "route_node_id": "node-1",
            "required_recheck_role": "reviewer",
            "owner_role": "worker",
            "blocker_class": "local_artifact",
            "cleared_by_outcome_id": "outcome-accepted",
        }
        ledger["route_nodes"]["node-1"] = {"node_id": "node-1", "status": "accepted"}
        ledger["active_blockers"]["blocker-cleared"] = blocker

        dossier = runtime._repair_dossier_projection(ledger, blocker)

        self.assertEqual(dossier["active_blocker_id"], "")
        self.assertIn("blocker-cleared", dossier["blocker_ids"])

    def test_pm_disposition_converges_node_closure_projection(self) -> None:
        for decision, expected_status in (
            ("accept", "accepted"),
            ("repair_current_scope", "repair_current_scope"),
            ("redesign_route", "redesign_route"),
            ("block", "blocked"),
            ("stop", "stopped"),
        ):
            with self.subTest(decision=decision):
                ledger = runtime.new_ledger("Goal", "Contract")
                ledger["active_route_version"] = 1
                ledger["routes"] = {
                    "1": {"route_version": 1, "status": "active", "node_order": ["node-1"]},
                }
                ledger["route_nodes"]["node-1"] = {
                    "node_id": "node-1",
                    "route_version": 1,
                    "title": "Node One",
                    "status": "running",
                    "responsibility": "worker",
                    "modeled_target": "development_process",
                    "acceptance_criteria": ["current acceptance"],
                    "child_node_ids": [],
                    "repair_generation": 0,
                }
                closure_id = runtime._record_node_closure(ledger, "node-1", "system-closure-1")

                disposition_id = runtime.record_pm_disposition(
                    ledger,
                    "node-1",
                    "result-1",
                    decision=decision,
                )

                closure = ledger["node_closures"][closure_id]
                self.assertEqual(closure["status"], expected_status)
                self.assertEqual(closure["pm_disposition_id"], disposition_id)
                self.assertEqual(closure["pm_disposition_decision"], decision)

    def test_routing_projection_excludes_noncurrent_node_packets_without_blocking_closure(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Do work"])
        ledger["route_nodes"]["node-001"] = {"node_id": "node-001", "status": "accepted"}
        packet_id = runtime.issue_task_packet(
            ledger,
            "worker",
            "Do work",
            "SEALED_TASK_BODY",
            route_node_id="node-001",
            route_scope="node",
        )
        ledger["packets"][packet_id]["status"] = "result_blocked"
        runtime.record_validation_evidence(ledger, "unit-validation")

        self.assertTrue(runtime._packet_is_noncurrent_for_routing(ledger, ledger["packets"][packet_id]))
        compact = runtime.render_compact_console(ledger)
        closure = runtime.attempt_final_closure(ledger, "unit-validation")

        self.assertNotIn(packet_id, {packet["packet_id"] for packet in compact["active_packets"]})
        self.assertNotIn(f"packet_not_accepted:{packet_id}", closure["blockers"])

    def test_closure_accepted_evidence_projection_keeps_accepted_node_packets(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Do work"])
        ledger["route_nodes"]["node-001"] = {"node_id": "node-001", "status": "active", "packet_ids": []}
        ledger["execution_frontier"] = {
            "active_node_id": "node-001",
            "status": "node_active",
            "route_version": ledger["active_route_version"],
            "pending_route_mutation": None,
        }
        runtime_runner._mark_node_ready_for_final_closure(ledger, "node-001")
        validation_id = ledger["latest_validation_evidence_id"]

        self.assertEqual(runtime._current_packets_for_routing(ledger), [])
        accepted_packets = runtime._accepted_packets_for_closure_evidence(ledger)
        closure = runtime.attempt_final_closure(ledger, validation_id)

        self.assertEqual([packet["packet_id"] for packet in accepted_packets], ledger["route_nodes"]["node-001"]["packet_ids"])
        self.assertNotIn("missing_accepted_packet_result", closure["blockers"])
        self.assertEqual(closure["decision"], "complete")

    def test_closure_accepted_evidence_projection_excludes_superseded_node_packets(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Do work"])
        ledger["route_nodes"]["node-001"] = {"node_id": "node-001", "status": "active", "packet_ids": []}
        ledger["execution_frontier"] = {
            "active_node_id": "node-001",
            "status": "node_active",
            "route_version": ledger["active_route_version"],
            "pending_route_mutation": None,
        }
        runtime_runner._mark_node_ready_for_final_closure(ledger, "node-001")
        validation_id = ledger["latest_validation_evidence_id"]
        ledger["route_nodes"]["node-001"]["status"] = "superseded"

        accepted_packets = runtime._accepted_packets_for_closure_evidence(ledger)
        closure = runtime.attempt_final_closure(ledger, validation_id)

        self.assertEqual(accepted_packets, [])
        self.assertIn("missing_accepted_packet_result", closure["blockers"])

    def test_final_matrix_rejects_blocked_review_evidence_id(self) -> None:
        ledger, node_id, validation_id = self._ledger_with_final_quality_node()
        review_id = ledger["route_nodes"][node_id]["review_ids"][0]
        ledger["reviews"][review_id]["decision"] = "block"
        ledger["reviews"][review_id]["blockers"] = ["current_gate_blocker"]

        matrix = runtime.build_final_requirement_evidence_matrix(ledger)
        closure = runtime.attempt_final_closure(ledger, validation_id)
        review_row = next(row for row in matrix["rows"] if row["row_id"] == f"{node_id}:review")

        self.assertEqual(review_row["status"], "invalid")
        self.assertIn(f"review:{node_id}:review:invalid", matrix["unresolved"])
        self.assertIn(f"review:{node_id}:review:invalid", closure["blockers"])

    def test_final_matrix_rejects_stale_flowguard_evidence_id(self) -> None:
        ledger, node_id, validation_id = self._ledger_with_final_quality_node()
        order_id = ledger["route_nodes"][node_id]["flowguard_order_ids"][0]
        ledger["flowguard_work_orders"][order_id]["proof_stale"] = True

        matrix = runtime.build_final_requirement_evidence_matrix(ledger)
        closure = runtime.attempt_final_closure(ledger, validation_id)
        flowguard_row = next(row for row in matrix["rows"] if row["row_id"] == f"{node_id}:flowguard")

        self.assertEqual(flowguard_row["status"], "invalid")
        self.assertIn(f"flowguard:{node_id}:flowguard:invalid", matrix["unresolved"])
        self.assertIn(f"flowguard:{node_id}:flowguard:invalid", closure["blockers"])

    def test_final_matrix_rejects_failed_validation_evidence_id(self) -> None:
        ledger, node_id, validation_id = self._ledger_with_final_quality_node()
        ledger["validation_evidence"][validation_id]["status"] = "failed"
        ledger["validation_evidence"][validation_id]["blockers"] = ["test_failed"]

        matrix = runtime.build_final_requirement_evidence_matrix(ledger)
        closure = runtime.attempt_final_closure(ledger, validation_id)
        validation_row = next(row for row in matrix["rows"] if row["row_id"] == f"{node_id}:validation")

        self.assertEqual(validation_row["status"], "invalid")
        self.assertIn(f"validation:{node_id}:validation:invalid", matrix["unresolved"])
        self.assertIn(f"validation:{node_id}:validation:invalid", closure["blockers"])
        self.assertIn("validation_not_passing", closure["blockers"])

    def test_final_matrix_ignores_old_route_evidence(self) -> None:
        ledger, node_id, _validation_id = self._ledger_with_final_quality_node()
        old_node = copy.deepcopy(ledger["route_nodes"][node_id])
        old_node["node_id"] = "old-node-001"
        old_node["route_version"] = 1
        ledger["route_nodes"]["old-node-001"] = old_node
        ledger["active_route_version"] = 2
        ledger["routes"] = {
            "1": {"route_version": 1, "status": "superseded", "node_order": ["old-node-001"]},
            "2": {"route_version": 2, "status": "active", "node_order": ["node-002"]},
        }
        ledger["route_nodes"] = {
            "old-node-001": old_node,
            "node-002": {
                "node_id": "node-002",
                "route_version": 2,
                "status": "accepted",
                "responsibility": "worker",
                "modeled_target": "development_process",
                "acceptance_criteria": ["accepted"],
                "packet_ids": [],
                "pm_disposition_id": "pm-disposition-current",
            },
        }

        matrix = runtime.build_final_requirement_evidence_matrix(ledger)
        row_ids = {row["row_id"] for row in matrix["rows"]}
        review_row = next(row for row in matrix["rows"] if row["row_id"] == "node-002:review")

        self.assertNotIn("old-node-001:review", row_ids)
        self.assertEqual(review_row["status"], "missing")

    def test_terminal_replay_rejects_missing_or_unexpected_segments(self) -> None:
        ledger, _node_id, validation_id = self._ledger_with_final_quality_node()
        packet_id = runtime.ensure_terminal_backward_replay_packet(ledger, validation_id)
        packet = ledger["packets"][packet_id]

        missing_check = runtime._terminal_backward_replay_result_violation(
            packet,
            {"body": self._terminal_replay_body_for_packet(packet, omit_last=True)},
        )
        unexpected_check = runtime._terminal_backward_replay_result_violation(
            packet,
            {"body": self._terminal_replay_body_for_packet(packet, unexpected=True)},
        )
        passing_check = runtime._terminal_backward_replay_result_violation(
            packet,
            {"body": self._terminal_replay_body_for_packet(packet)},
        )

        self.assertFalse(missing_check.ok)
        self.assertIn("missing segment id", missing_check.blocked_reason)
        self.assertFalse(unexpected_check.ok)
        self.assertIn("unexpected segment id", unexpected_check.blocked_reason)
        self.assertTrue(passing_check.ok)

    def test_terminal_replay_requires_final_artifact_hygiene_segment_in_route_replay(self) -> None:
        ledger, _node_id, validation_id = self._ledger_with_final_quality_node()
        packet_id = runtime.ensure_terminal_backward_replay_packet(ledger, validation_id)
        packet = ledger["packets"][packet_id]
        packet_body = json.loads(packet["body"])

        self.assertIn(
            "final-artifact-hygiene",
            [target["segment_id"] for target in packet_body["segment_targets"]],
        )

        payload = json.loads(self._terminal_replay_body_for_packet(packet))
        payload["route_segment_replay"] = [
            row
            for row in payload["route_segment_replay"]
            if row["segment_id"] != "final-artifact-hygiene"
        ]
        check = runtime._terminal_backward_replay_result_violation(packet, {"body": json.dumps(payload)})

        self.assertFalse(check.ok)
        self.assertIn("missing segment id", check.blocked_reason)

    def test_terminal_replay_final_blockers_are_semantic_not_shape_failure(self) -> None:
        ledger, _node_id, validation_id = self._ledger_with_final_quality_node()
        packet_id = runtime.ensure_terminal_backward_replay_packet(ledger, validation_id)
        packet = ledger["packets"][packet_id]
        payload = json.loads(self._terminal_replay_block_body_for_packet(packet))
        payload["final_blockers"].append(
            {
                "blocker_id": "terminal-blocker-hygiene",
                "blocker_class": "terminal_closure",
                "recommended_resolution": "Repair final artifact hygiene before terminal replay can close.",
            }
        )

        check = runtime._terminal_backward_replay_result_violation(packet, {"body": json.dumps(payload)})

        self.assertTrue(check.ok)

    def test_terminal_replay_pass_records_without_legacy_hygiene_review(self) -> None:
        ledger, _node_id, validation_id = self._ledger_with_final_quality_node()
        packet_id = runtime.ensure_terminal_backward_replay_packet(ledger, validation_id)
        lease_id = self._lease_ack_and_open_packet(ledger, packet_id, "reviewer")
        payload = json.loads(self._terminal_replay_body_for_packet(ledger["packets"][packet_id]))

        runtime.submit_result(ledger, lease_id, packet_id, json.dumps(payload))
        final_ledger = runtime.build_final_route_wide_gate_ledger(ledger)
        matrix = runtime.build_final_requirement_evidence_matrix(ledger)

        self.assertEqual(ledger["terminal_backward_replay_id"], "terminal_replay-0001")
        self.assertNotIn("terminal_replay-0001", ledger.get("final_artifact_hygiene_reviews", {}))
        self.assertNotIn("final_artifact_hygiene", "\n".join(final_ledger["unresolved"]))
        self.assertNotIn("final_artifact_hygiene", "\n".join(matrix["unresolved"]))

    def test_terminal_replay_valid_block_records_semantic_blocker_not_mechanical_reissue(self) -> None:
        ledger, _node_id, validation_id = self._ledger_with_final_quality_node()
        packet_id = runtime.ensure_terminal_backward_replay_packet(ledger, validation_id)
        lease_id = runtime.lease_agent(ledger, "reviewer", agent_id="reviewer-terminal-block", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)

        result_id = runtime.submit_result(
            ledger,
            lease_id,
            packet_id,
            self._terminal_replay_block_body_for_packet(ledger["packets"][packet_id]),
        )

        result = ledger["results"][result_id]
        self.assertEqual(result["status"], "review_blocked")
        self.assertFalse(result["accepted"])
        self.assertEqual(ledger["packets"][packet_id]["status"], "review_blocked")
        self.assertFalse(ledger.get("terminal_backward_replays"))
        self.assertFalse(ledger.get("closure_confirmed_by_backward_replay", False))
        self.assertTrue(ledger["active_blockers"])
        blocker = next(iter(ledger["active_blockers"].values()))
        self.assertEqual(blocker["route_scope"], "terminal_backward_replay")
        self.assertIn("signposting", blocker["recommended_resolution"])
        self.assertFalse(
            [event for event in ledger["events"] if event["event_type"] == "current_contract_reissue_packet_issued"]
        )

    def test_terminal_replay_repair_current_scope_preserves_targets_and_closes(self) -> None:
        ledger, node_id, validation_id = self._ledger_with_final_quality_node()
        self._prepare_terminal_supplemental_projection(ledger, node_id)
        packet_id = runtime.ensure_terminal_backward_replay_packet(ledger, validation_id)
        lease_id = self._lease_ack_and_open_packet(ledger, packet_id, "reviewer")
        block_result_id = runtime.submit_result(
            ledger,
            lease_id,
            packet_id,
            self._terminal_replay_block_body_for_packet(ledger["packets"][packet_id]),
        )
        blocker_id = next(iter(ledger["active_blockers"]))
        self.assertEqual(ledger["results"][block_result_id]["status"], "review_blocked")

        pm_packet_id = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
        pm_lease_id = self._lease_ack_and_open_packet(ledger, pm_packet_id, "pm")
        runtime.submit_result(
            ledger,
            pm_lease_id,
            pm_packet_id,
            pm_repair_decision_body(
                ledger,
                pm_packet_id,
                decision="repair_current_scope",
                reason="Repair terminal replay blocker and rerun terminal replay.",
                pm_visible_summary=["PM chose current-scope terminal replay repair."],
                supplemental_repair_contract=self._terminal_supplemental_contract(
                    ledger,
                    blocker_id,
                    node_id,
                ),
            ),
        )
        self.assertEqual(ledger["terminal_supplemental_repair"]["current_round"], 1)
        self.assertIn("terminal-supplemental-repair-r1", ledger["supplemental_repair_contracts"])
        self._complete_pm_continue_repair_gate(ledger, blocker_id)

        repair_packet_id = ledger["active_blockers"][blocker_id]["repair_packet_id"]
        repair_packet = ledger["packets"][repair_packet_id]
        repair_body = json.loads(repair_packet["body"])
        self.assertEqual(repair_packet["envelope"]["packet_kind"], "review")
        self.assertEqual(repair_packet["envelope"]["route_scope"], "terminal_backward_replay")
        self.assertEqual(repair_body["schema_version"], "black_box_flowpilot.terminal_backward_replay_repair_packet.v1")
        self.assertTrue(repair_body["segment_targets"])
        self.assertIn(
            "supplemental-repair-item:terminal-supplemental-repair-r1:terminal-gap-r1-item-1",
            {target["segment_id"] for target in repair_body["segment_targets"]},
        )

        action = runtime.router_next_action(ledger)
        self.assertEqual(action.action_type, "dispatch_current_role")
        self.assertEqual(action.subject_id, repair_packet_id)

        repair_lease_id = self._lease_ack_and_open_packet(ledger, repair_packet_id, "reviewer")
        pass_result_id = runtime.submit_result(
            ledger,
            repair_lease_id,
            repair_packet_id,
            self._terminal_replay_body_for_packet(repair_packet),
        )

        self.assertEqual(ledger["results"][pass_result_id]["status"], "accepted")
        self.assertEqual(ledger["active_blockers"][blocker_id]["status"], "cleared")
        self.assertTrue(ledger["terminal_backward_replays"])
        self.assertTrue(ledger["closure_confirmed_by_backward_replay"])
        self.assertEqual(ledger["terminal_supplemental_repair"]["status"], "clean")
        self.assertEqual(ledger["closure"]["decision"], "complete")
        self.assertEqual(runtime.router_next_action(ledger).action_type, "terminal_complete")
        current_blocking_outcomes = [
            outcome
            for outcome in ledger["packet_outcomes"].values()
            if runtime._packet_outcome_is_current_blocker(ledger, outcome)
        ]
        self.assertEqual(current_blocking_outcomes, [])

    def test_terminal_pm_repair_for_terminal_gap_requires_supplemental_contract(self) -> None:
        ledger, _node_id, validation_id = self._ledger_with_final_quality_node()
        packet_id = runtime.ensure_terminal_backward_replay_packet(ledger, validation_id)
        lease_id = self._lease_ack_and_open_packet(ledger, packet_id, "reviewer")
        runtime.submit_result(
            ledger,
            lease_id,
            packet_id,
            self._terminal_replay_block_body_for_packet(ledger["packets"][packet_id]),
        )
        blocker_id = next(iter(ledger["active_blockers"]))
        pm_packet_id = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
        pm_lease_id = self._lease_ack_and_open_packet(ledger, pm_packet_id, "pm")

        result_id = runtime.submit_result(
            ledger,
            pm_lease_id,
            pm_packet_id,
            pm_repair_decision_body(
                ledger,
                pm_packet_id,
                decision="repair_current_scope",
                reason="Repair terminal replay blocker without the required supplemental contract.",
            ),
        )

        result = ledger["results"][result_id]
        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertIn("supplemental_repair_contract", result["missing_required_fields"])
        self.assertFalse(ledger["supplemental_repair_contracts"])
        self.assertFalse(ledger["pm_repair_decisions"])

    def test_terminal_hygiene_supplemental_contract_requires_category(self) -> None:
        ledger, node_id, validation_id = self._ledger_with_final_quality_node()
        self._prepare_terminal_supplemental_projection(ledger, node_id)
        packet_id = runtime.ensure_terminal_backward_replay_packet(ledger, validation_id)
        lease_id = self._lease_ack_and_open_packet(ledger, packet_id, "reviewer")
        runtime.submit_result(
            ledger,
            lease_id,
            packet_id,
            self._terminal_replay_block_body_for_packet(ledger["packets"][packet_id]),
        )
        blocker_id = next(iter(ledger["active_blockers"]))
        pm_packet_id = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
        pm_lease_id = self._lease_ack_and_open_packet(ledger, pm_packet_id, "pm")

        result_id = runtime.submit_result(
            ledger,
            pm_lease_id,
            pm_packet_id,
            pm_repair_decision_body(
                ledger,
                pm_packet_id,
                decision="repair_current_scope",
                reason="Repair final artifact hygiene through supplemental repair.",
                pm_visible_summary=["PM chose current-scope hygiene repair."],
                supplemental_repair_contract=self._terminal_supplemental_contract(
                    ledger,
                    blocker_id,
                    node_id,
                    gap_kind="final_artifact_hygiene_gap",
                ),
            ),
        )

        result = ledger["results"][result_id]
        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertIn("hygiene_category", result["quarantine_reason"])
        self.assertFalse(ledger["supplemental_repair_contracts"])

    def test_terminal_hygiene_supplemental_contract_projects_to_final_ledgers(self) -> None:
        ledger, node_id, validation_id = self._ledger_with_final_quality_node()
        self._prepare_terminal_supplemental_projection(ledger, node_id)
        ledger["active_blockers"]["blocker-terminal"] = {
            "blocker_id": "blocker-terminal",
            "result_id": "terminal-gap-result",
            "route_scope": "terminal_backward_replay",
        }
        contract = self._terminal_supplemental_contract(
            ledger,
            "blocker-terminal",
            node_id,
            gap_kind="final_artifact_hygiene_gap",
            hygiene_category="code_maintainability",
        )
        contract["terminal_blocker_id"] = "blocker-terminal"
        contract["terminal_gap_report_result_id"] = "terminal-gap-result"
        contract["source_packet_id"] = "pm-packet"
        ledger["supplemental_repair_contracts"][contract["contract_id"]] = contract

        final_ledger = runtime.build_final_route_wide_gate_ledger(ledger)
        matrix = runtime.build_final_requirement_evidence_matrix(ledger)

        self.assertEqual(
            final_ledger["final_artifact_hygiene_closure"][0]["finding_id"],
            "terminal-supplemental-repair-r1:terminal-gap-r1-item-1",
        )
        self.assertEqual(final_ledger["final_artifact_hygiene_closure"][0]["artifact_family"], "code_maintainability")
        self.assertFalse(final_ledger["final_artifact_hygiene_closure"][0]["unresolved"])
        self.assertNotIn(
            "final_artifact_hygiene_unresolved:terminal-supplemental-repair-r1:terminal-gap-r1-item-1",
            final_ledger["unresolved"],
        )
        self.assertNotIn(
            "final_artifact_hygiene:terminal-supplemental-repair-r1:terminal-gap-r1-item-1:missing",
            matrix["unresolved"],
        )

    def test_unresolved_required_hygiene_finding_blocks_final_closure(self) -> None:
        ledger, _node_id, validation_id = self._ledger_with_final_quality_node()
        ledger["final_artifact_hygiene_findings"].append(
            {
                "finding_id": "hygiene-required-closure",
                "artifact_family": "test_coverage",
                "surface_path": "tests/test_flowpilot_core_runtime.py",
                "classification": "current_goal_required_repair",
                "required_repair": "Add a missing regression for required hygiene closure.",
                "disposition": "",
                "evidence_ids": [],
            }
        )

        final_ledger = runtime.build_final_route_wide_gate_ledger(ledger)
        blockers = runtime._closure_blockers(
            ledger,
            validation_evidence_id=validation_id,
            required_flowguard_target="development_process",
        )

        self.assertIn("final_artifact_hygiene_unresolved:hygiene-required-closure", final_ledger["unresolved"])
        self.assertIn("final_artifact_hygiene_unresolved:hygiene-required-closure", blockers)

    def test_terminal_pm_repair_packet_supplies_current_supplemental_contract_shape(self) -> None:
        ledger, _node_id, validation_id = self._ledger_with_final_quality_node()
        packet_id = runtime.ensure_terminal_backward_replay_packet(ledger, validation_id)
        lease_id = self._lease_ack_and_open_packet(ledger, packet_id, "reviewer")
        runtime.submit_result(
            ledger,
            lease_id,
            packet_id,
            self._terminal_replay_block_body_for_packet(ledger["packets"][packet_id]),
        )
        blocker_id = next(iter(ledger["active_blockers"]))
        blocker = ledger["active_blockers"][blocker_id]
        pm_packet_id = blocker["pm_repair_packet_id"]
        pm_body = json.loads(ledger["packets"][pm_packet_id]["body"])
        minimal_shape = pm_body["minimal_valid_shape"]
        allowed_options = pm_body["current_handoff_contract"]["required_report_contract"]["allowed_value_options"]
        supplemental_contract = minimal_shape["supplemental_repair_contract"]
        route_nodes = minimal_shape["route_plan"]["nodes"]
        hygiene_options = allowed_options[
            "supplemental_repair_contract.repair_items[].hygiene_category when gap_kind=final_artifact_hygiene_gap"
        ]

        self.assertEqual(supplemental_contract["original_contract_hash"], ledger["contract_hash"])
        self.assertEqual(supplemental_contract["terminal_blocker_id"], blocker_id)
        self.assertEqual(supplemental_contract["terminal_gap_report_result_id"], blocker["result_id"])
        self.assertEqual(supplemental_contract["repair_items"][0]["hygiene_category"], "artifact_lineage")
        self.assertIn("artifact_lineage", hygiene_options)
        self.assertNotIn("current_goal_required", hygiene_options)
        self.assertIn("terminal-supplemental-repair-r1", route_nodes[1]["supplemental_repair_contract_ids"])
        self.assertIn("terminal-gap-r1-item-1", route_nodes[1]["supplemental_repair_item_ids"])

    def test_supplemental_repair_item_projection_blocks_final_ledgers(self) -> None:
        ledger, node_id, _validation_id = self._ledger_with_final_quality_node()
        self._prepare_terminal_supplemental_projection(ledger, node_id)
        ledger["active_blockers"]["blocker-terminal"] = {
            "blocker_id": "blocker-terminal",
            "result_id": "terminal-gap-result",
        }
        contract = self._terminal_supplemental_contract(
            ledger,
            "blocker-terminal",
            node_id,
        )
        contract["terminal_blocker_id"] = "blocker-terminal"
        contract["terminal_gap_report_result_id"] = "terminal-gap-result"
        contract["source_packet_id"] = "pm-packet"
        contract["source_result_id"] = "pm-result"
        ledger["supplemental_repair_contracts"][contract["contract_id"]] = contract
        ledger["route_nodes"][node_id]["supplemental_repair_item_ids"] = []

        route_ledger = runtime.build_final_route_wide_gate_ledger(ledger)
        matrix = runtime.build_final_requirement_evidence_matrix(ledger)

        self.assertIn(
            "supplemental_repair_item_projection_missing:terminal-supplemental-repair-r1:terminal-gap-r1-item-1",
            route_ledger["unresolved"],
        )
        self.assertIn(
            "terminal_supplemental_repair_item:terminal-supplemental-repair-r1:terminal-gap-r1-item-1:projection_missing",
            matrix["unresolved"],
        )

    def test_terminal_supplemental_repair_exhausts_after_third_round_without_pm_packet(self) -> None:
        ledger, _node_id, validation_id = self._ledger_with_final_quality_node()
        ledger["terminal_supplemental_repair"]["status"] = "active"
        ledger["terminal_supplemental_repair"]["current_round"] = 3
        ledger["terminal_supplemental_repair"]["active_contract_id"] = "terminal-supplemental-repair-r3"
        packet_id = runtime.ensure_terminal_backward_replay_packet(ledger, validation_id)
        lease_id = self._lease_ack_and_open_packet(ledger, packet_id, "reviewer")

        runtime.submit_result(
            ledger,
            lease_id,
            packet_id,
            self._terminal_replay_block_body_for_packet(ledger["packets"][packet_id]),
        )

        self.assertEqual(ledger["terminal_lifecycle"]["status"], "repair_rounds_exhausted")
        self.assertTrue(
            any(event["event_type"] == "run_repair_rounds_exhausted" for event in ledger["events"])
        )
        self.assertFalse(
            any(
                event["event_type"] == "run_cancelled_by_user"
                and event["payload"].get("status") == "repair_rounds_exhausted"
                for event in ledger["events"]
            )
        )
        blocker = next(iter(ledger["active_blockers"].values()))
        self.assertEqual(blocker["route_scope"], "terminal_backward_replay")
        self.assertEqual(blocker["pm_repair_packet_id"], "")
        self.assertFalse(
            [
                packet
                for packet in ledger["packets"].values()
                if packet["envelope"].get("packet_kind") == "pm_repair_decision"
                and packet["status"] in {"open", "assigned", "acknowledged"}
            ]
        )

    def test_terminal_replay_block_branch_requires_repair_evidence(self) -> None:
        ledger, _node_id, validation_id = self._ledger_with_final_quality_node()
        packet_id = runtime.ensure_terminal_backward_replay_packet(ledger, validation_id)
        packet = ledger["packets"][packet_id]

        check = runtime._terminal_backward_replay_result_violation(
            packet,
            {"body": self._terminal_replay_block_body_for_packet(packet, omit_blockers=True)},
        )

        self.assertFalse(check.ok)
        self.assertIn("final_blockers", check.blocked_reason)

    def test_terminal_replay_mechanical_reissue_preserves_segment_targets(self) -> None:
        ledger, _node_id, validation_id = self._ledger_with_final_quality_node()
        packet_id = runtime.ensure_terminal_backward_replay_packet(ledger, validation_id)
        expected_targets = json.loads(ledger["packets"][packet_id]["body"])["segment_targets"]
        lease_id = runtime.lease_agent(ledger, "reviewer", agent_id="reviewer-terminal-reissue", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)

        result_id = runtime.submit_result(
            ledger,
            lease_id,
            packet_id,
            self._terminal_replay_body_for_packet(ledger["packets"][packet_id], omit_last=True),
        )

        result = ledger["results"][result_id]
        self.assertEqual(result["status"], "mechanical_contract_blocked")
        reissue_events = [
            event for event in ledger["events"] if event["event_type"] == "current_contract_reissue_packet_issued"
        ]
        self.assertEqual(len(reissue_events), 1)
        reissue_packet_id = reissue_events[0]["payload"]["fresh_packet_id"]
        reissue_body = json.loads(ledger["packets"][reissue_packet_id]["body"])
        self.assertEqual(reissue_body["schema_version"], "black_box_flowpilot.terminal_backward_replay_reissue_packet.v1")
        self.assertEqual(reissue_body["segment_targets"], expected_targets)
        self.assertEqual(reissue_body["route_scope"], "terminal_backward_replay")
        action = runtime.router_next_action(ledger)
        self.assertEqual(action.action_type, "dispatch_current_role")
        self.assertEqual(action.subject_id, reissue_packet_id)

    def test_quarantined_packet_rejects_late_submit_and_stays_out_of_active_projection(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.create_route(ledger, "Replacement route", ["Replacement node"])

        before_result_ids = list(ledger["packets"][packet_id]["result_ids"])
        before_result_count = len(ledger["results"])
        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "quarantined_packet|stale_route_version"):
            runtime.submit_result(ledger, worker, packet_id, role_result_body("Late result"))
        runtime.record_validation_evidence(ledger, "unit-validation")
        compact = runtime.render_compact_console(ledger)
        closure = runtime.attempt_final_closure(ledger, "unit-validation")

        self.assertEqual(ledger["packets"][packet_id]["status"], "quarantined_after_route_mutation")
        self.assertEqual(ledger["packets"][packet_id]["result_ids"], before_result_ids)
        self.assertEqual(len(ledger["results"]), before_result_count)
        self.assertNotIn(packet_id, {packet["packet_id"] for packet in compact["active_packets"]})
        self.assertNotIn(f"packet_not_accepted:{packet_id}", closure["blockers"])

    def test_pending_route_mutation_clears_after_replacement_node_acceptance(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        mutation = {
            "mutation_id": "mutation-001",
            "old_route_version": 1,
            "new_route_version": 2,
            "replacement_node_id": "node-001",
            "created_at": runtime.now_iso(),
        }
        ledger["active_route_version"] = 2
        ledger["routes"]["2"] = {
            "route_version": 2,
            "route_id": "route-v2",
            "status": "active",
            "node_order": ["node-001", "node-002"],
        }
        ledger["route_nodes"] = {
            "node-001": {
                "node_id": "node-001",
                "title": "Accepted node",
                "status": "accepted",
                "responsibility": "worker",
                "modeled_target": "development_process",
                "acceptance_criteria": ["accepted"],
                "packet_ids": [],
            },
            "node-002": {
                "node_id": "node-002",
                "title": "Running node",
                "status": "running",
                "responsibility": "worker",
                "modeled_target": "development_process",
                "acceptance_criteria": ["running"],
                "packet_ids": [],
            },
        }
        ledger["execution_frontier"] = {
            "active_route_version": 2,
            "active_node_id": "node-001",
            "completed_nodes": [],
            "status": "node_execution",
            "pending_route_mutation": dict(mutation),
            "updated_at": runtime.now_iso(),
        }
        ledger["route_mutations"] = [dict(mutation)]

        runtime._advance_frontier_after_node_acceptance(ledger, "node-001")

        self.assertIsNone(ledger["execution_frontier"]["pending_route_mutation"])
        self.assertEqual(ledger["route_mutations"][0]["status"], "committed")
        self.assertEqual(ledger["route_mutations"][0]["committed_node_id"], "node-001")
        self.assertEqual(ledger["execution_frontier"]["active_node_id"], "node-002")

    def test_unmatched_pending_route_mutation_survives_unrelated_node_acceptance(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        mutation = {
            "mutation_id": "mutation-001",
            "old_route_version": 1,
            "new_route_version": 2,
            "replacement_node_id": "node-replacement",
            "created_at": runtime.now_iso(),
        }
        ledger["active_route_version"] = 2
        ledger["routes"]["2"] = {
            "route_version": 2,
            "route_id": "route-v2",
            "status": "active",
            "node_order": ["node-001", "node-002", "node-replacement"],
        }
        ledger["route_nodes"] = {
            "node-001": {
                "node_id": "node-001",
                "title": "Accepted node",
                "status": "accepted",
                "responsibility": "worker",
                "modeled_target": "development_process",
                "acceptance_criteria": ["accepted"],
                "packet_ids": [],
            },
            "node-002": {
                "node_id": "node-002",
                "title": "Running node",
                "status": "running",
                "responsibility": "worker",
                "modeled_target": "development_process",
                "acceptance_criteria": ["running"],
                "packet_ids": [],
            },
            "node-replacement": {
                "node_id": "node-replacement",
                "title": "Replacement node",
                "status": "running",
                "responsibility": "worker",
                "modeled_target": "development_process",
                "acceptance_criteria": ["replacement"],
                "packet_ids": [],
            },
        }
        ledger["execution_frontier"] = {
            "active_route_version": 2,
            "active_node_id": "node-001",
            "completed_nodes": [],
            "status": "node_execution",
            "pending_route_mutation": dict(mutation),
            "updated_at": runtime.now_iso(),
        }
        ledger["route_mutations"] = [dict(mutation)]

        runtime._advance_frontier_after_node_acceptance(ledger, "node-001")

        self.assertEqual(ledger["execution_frontier"]["pending_route_mutation"]["mutation_id"], "mutation-001")
        self.assertNotIn("status", ledger["route_mutations"][0])
        self.assertEqual(ledger["execution_frontier"]["active_node_id"], "node-002")

    def test_recover_or_reissue_payload_names_concrete_command(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        ledger["leases"][worker]["ack_received_at"] = "2000-01-01T00:00:00+00:00"

        guard = runtime.preview_lifecycle_guard(ledger, trigger="patrol")
        duty = runtime.preview_foreground_duty(ledger, guard=guard, trigger="patrol")
        command = duty["recovery"]["recommended_command"]

        self.assertEqual(duty["action"], "recover_or_reissue")
        self.assertEqual(command["command"], "dispatch-current-role")
        self.assertEqual(command["packet_id"], packet_id)
        self.assertEqual(command["responsibility"], "worker")
        self.assertEqual(command["host_kind"], "live")
        self.assertNotIn("--agent-id", command["cli"])
        self.assertNotIn("<new-agent-id>", command["cli"])
        self.assertIn(worker, command["stale_lease_ids"])
        self.assertFalse(command["sealed_bodies_visible"])

    def test_nested_node_context_package_is_rejected(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        node = {"node_id": "node-1", "title": "Node One", "repair_generation": 0}
        ledger["route_nodes"]["node-1"] = node
        package = {
            "node_id": "node-1",
            "purpose": "Give every role enough starting context without granting command authority.",
            "acceptance_criteria": ["criterion"],
            "relevant_references": ["reference"],
            "evidence_targets": ["evidence"],
            "inspection_targets": ["inspection"],
            "known_risks": ["risk"],
            "flowguard_targets": ["development_process"],
            "reviewer_starting_points": ["start here"],
        }
        ledger["results"]["result-node"] = {
            "result_id": "result-node",
            "body": json.dumps({"node_acceptance_plan": {"node_context_package": package}}),
        }

        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "top-level node_context_package"):
            runtime._node_context_package_from_pm_result(
                ledger,
                node,
                {"packet_id": "packet-node", "accepted_result_id": "result-node"},
                "result-node",
            )
        self.assertFalse(
            [event for event in ledger["events"] if event["event_type"] == "node_context_package_accepted"]
        )

    def test_planning_result_old_route_nodes_shape_reissues_current_planning_packet(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Planning route", ["Plan"])
        packet_id = runtime.issue_task_packet(
            ledger,
            "pm",
            "Write current route plan",
            "PLANNING_PACKET",
            route_scope="planning",
        )
        lease_id = runtime.lease_agent(ledger, "pm", agent_id="pm-plan", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)

        result_id = runtime.submit_result(
            ledger,
            lease_id,
            packet_id,
            json.dumps(
                {
                    "schema_version": runtime.ROUTE_PLAN_SCHEMA_VERSION,
                    "route_nodes": [{"node_id": "node-1", "title": "Old alias"}],
                }
            ),
        )

        result = ledger["results"][result_id]
        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertIn("current_result_contract_violation", result["mechanical_blockers"])
        self.assertEqual(ledger["packets"][packet_id]["status"], "superseded_after_repair")
        reissues = [
            packet
            for packet in ledger["packets"].values()
            if packet["packet_id"] != packet_id
            and packet["envelope"]["route_scope"] == "planning"
            and packet["status"] == "open"
        ]
        self.assertEqual(len(reissues), 1)
        self.assertEqual(reissues[0]["envelope"]["responsibility"], "pm")
        self.assertEqual(reissues[0]["envelope"]["packet_kind"], "task")

    def test_node_acceptance_plan_result_stages_effect_before_closure(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Node one"])
        ledger["route_nodes"]["node-1"] = {
            "node_id": "node-1",
            "title": "Node One",
            "status": "pending",
            "repair_generation": 0,
            "acceptance_criteria": ["criterion"],
        }
        packet_id = runtime.ensure_node_acceptance_plan_packet(ledger, "node-1")
        lease_id = runtime.lease_agent(ledger, "pm", agent_id="pm-node", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)
        package = copy.deepcopy(
            packet_result_contracts.minimal_valid_shape_for_family("task.node_acceptance_plan")["node_context_package"]
        )
        package.update(
            {
                "node_id": "node-1",
                "purpose": "Provide current starting context.",
                "acceptance_criteria": ["criterion"],
                "relevant_references": ["reference"],
                "known_risks": ["risk"],
                "acceptance_item_projection": [],
            }
        )

        result_id = runtime.submit_result(
            ledger,
            lease_id,
            packet_id,
            json.dumps({"node_context_package": package, "decision": "pass"}),
        )

        result = ledger["results"][result_id]
        self.assertEqual(result["staged_effect"]["effect_kind"], "commit_node_acceptance_plan")
        self.assertEqual(result["staged_effect"]["status"], "pending")
        self.assertFalse(ledger["node_acceptance_plans"])
        self.assertFalse(ledger["node_context_packages"])
        flowguard_packets = [
            packet for packet in ledger["packets"].values()
            if packet["envelope"]["packet_kind"] == "flowguard_check"
            and packet["envelope"]["subject_id"] == packet_id
        ]
        review_packets = [
            packet for packet in ledger["packets"].values()
            if packet["envelope"]["packet_kind"] == "review"
            and packet["envelope"]["subject_id"] == packet_id
        ]
        self.assertEqual(flowguard_packets, [])
        self.assertEqual(len(review_packets), 1)
        self.assertEqual(json.loads(review_packets[0]["body"])["staged_effect"]["effect_kind"], "commit_node_acceptance_plan")

    def _accept_node_entry_gate(self, ledger: dict[str, object], node_id: str) -> None:
        node = ledger["route_nodes"][node_id]
        generation = int(node.get("repair_generation", 0))
        plan_id = f"plan-{node_id}"
        context_id = f"context-{node_id}"
        ledger.setdefault("node_acceptance_plans", {})[plan_id] = {
            "plan_id": plan_id,
            "status": "accepted",
            "node_id": node_id,
            "repair_generation": generation,
            "created_at": runtime.now_iso(),
        }
        ledger.setdefault("node_context_packages", {})[context_id] = {
            "context_package_id": context_id,
            "status": "accepted",
            "node_id": node_id,
            "repair_generation": generation,
            "purpose": "Current parent/module entry context.",
            "acceptance_criteria": list(node.get("acceptance_criteria") or []),
            "relevant_references": [],
            "known_risks": [],
            "acceptance_item_projection": [],
            "created_at": runtime.now_iso(),
        }
        node["node_acceptance_plan_id"] = plan_id
        node["node_context_package_id"] = context_id
        node["node_context_package_repair_generation"] = generation

    def _parent_replacement_replay_fixture(
        self,
        *,
        active_child_result_id: str = "active-child-result",
    ) -> tuple[dict[str, object], str, str, str]:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        authorize_background_collaboration(ledger)
        ledger["high_standard_control_flow_required"] = True
        runtime.create_route(ledger, "Route", ["Parent", "Child"])
        route_version = ledger["active_route_version"]
        parent_id = "parent-1"
        old_child_id = "child-1"
        active_child_id = "child-1-repair-v2"
        ledger["routes"][str(route_version)]["node_order"] = [parent_id, old_child_id, active_child_id]
        ledger["route_nodes"][parent_id] = {
            "node_id": parent_id,
            "route_version": route_version,
            "title": "Parent",
            "node_kind": "module",
            "status": "awaiting_parent_backward_replay",
            "responsibility": "reviewer",
            "modeled_target": "development_process",
            "repair_generation": 0,
            "acceptance_criteria": ["children compose"],
            "child_node_ids": [old_child_id],
        }
        ledger["route_nodes"][old_child_id] = {
            "node_id": old_child_id,
            "route_version": route_version,
            "title": "Old Child",
            "node_kind": "leaf",
            "parent_node_id": parent_id,
            "status": "superseded",
            "accepted_result_id": "old-child-result",
            "superseded_by": active_child_id,
            "repair_generation": 0,
            "acceptance_criteria": ["old child accepted"],
            "child_node_ids": [],
        }
        ledger["route_nodes"][active_child_id] = {
            "node_id": active_child_id,
            "route_version": route_version,
            "title": "Active Child Repair",
            "node_kind": "leaf",
            "parent_node_id": parent_id,
            "status": "accepted",
            "accepted_result_id": active_child_result_id,
            "superseded_by": "",
            "repair_generation": 1,
            "acceptance_criteria": ["active child accepted"],
            "child_node_ids": [],
        }
        self._accept_node_entry_gate(ledger, parent_id)
        return ledger, parent_id, old_child_id, active_child_id

    def test_parent_backward_review_closes_parent_without_second_reviewer_packet(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        authorize_background_collaboration(ledger)
        ledger["high_standard_control_flow_required"] = True
        runtime.create_route(ledger, "Route", ["Parent", "Child"])
        route_version = ledger["active_route_version"]
        parent_id = "parent-1"
        child_id = "child-1"
        ledger["routes"][str(route_version)]["node_order"] = [parent_id, child_id]
        ledger["route_nodes"][parent_id] = {
            "node_id": parent_id,
            "route_version": route_version,
            "title": "Parent",
            "node_kind": "module",
            "status": "awaiting_parent_backward_replay",
            "responsibility": "reviewer",
            "modeled_target": "development_process",
            "repair_generation": 0,
            "acceptance_criteria": ["children compose"],
            "child_node_ids": [child_id],
        }
        ledger["route_nodes"][child_id] = {
            "node_id": child_id,
            "route_version": route_version,
            "title": "Child",
            "node_kind": "leaf",
            "parent_node_id": parent_id,
            "status": "accepted",
            "accepted_result_id": "child-result-1",
            "repair_generation": 0,
            "acceptance_criteria": ["child accepted"],
            "child_node_ids": [],
        }
        self._accept_node_entry_gate(ledger, parent_id)
        packet_id = runtime.ensure_parent_backward_replay_packet(ledger, parent_id)
        packet = ledger["packets"][packet_id]
        self.assertEqual(packet["envelope"]["packet_kind"], "review")
        self.assertEqual(packet["envelope"]["route_scope"], "parent_backward_replay")
        reviewer = runtime.lease_agent(ledger, "reviewer", agent_id="reviewer-parent", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, reviewer)
        runtime.ack_lease(ledger, reviewer, packet_id)
        replay_body = packet_result_contracts.minimal_valid_shape_for_family("review.parent_backward_replay")
        replay_body.update(
            {
                "reviewed_by_role": "human_like_reviewer",
                "passed": True,
                "parent_node_id": parent_id,
                "child_node_ids": [child_id],
                "child_evidence_refs": ["child-result-1"],
                "findings": [],
                "blockers": [],
            }
        )
        replay_result_id = runtime.submit_result(ledger, reviewer, packet_id, json.dumps(replay_body))

        self.assertEqual(ledger["packets"][packet_id]["accepted_result_id"], replay_result_id)
        self.assertTrue(runtime._parent_backward_replay_result_accepted(ledger, parent_id))
        self.assertTrue(runtime._parent_backward_replay_accepted(ledger, parent_id))
        self.assertEqual(ledger["route_nodes"][parent_id]["status"], "awaiting_pm_disposition")
        flowguard_packets = [
            packet
            for packet in ledger["packets"].values()
            if packet["envelope"]["packet_kind"] == "flowguard_check"
            and packet["envelope"].get("subject_id") == packet_id
        ]
        self.assertEqual(flowguard_packets, [])
        second_review_packets = [
            packet
            for packet in ledger["packets"].values()
            if packet["envelope"]["packet_kind"] == "review"
            and packet["packet_id"] != packet_id
            and packet["envelope"].get("subject_id") == packet_id
        ]
        self.assertEqual(second_review_packets, [])
        replay_id = ledger["route_nodes"][parent_id]["parent_backward_replay_id"]
        replay_record = ledger["parent_backward_replays"][replay_id]
        self.assertEqual(replay_record["source_review_packet_id"], packet_id)
        self.assertEqual(replay_record["source_review_result_id"], replay_result_id)
        self.assertEqual(replay_record["reviewed_by_role"], "human_like_reviewer")
        pm_packets = [
            packet
            for packet in ledger["packets"].values()
            if packet["envelope"]["packet_kind"] == "pm_disposition"
            and packet["envelope"].get("subject_id") == packet_id
        ]
        self.assertEqual(len(pm_packets), 1)

    def test_active_child_lineage_resolves_replacement_chain_and_rejects_bad_targets(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        ledger["route_nodes"] = {
            "child-old": {
                "node_id": "child-old",
                "status": "superseded",
                "superseded_by": "child-repair-v2",
            },
            "child-repair-v2": {
                "node_id": "child-repair-v2",
                "status": "superseded",
                "superseded_by": "child-repair-v3",
            },
            "child-repair-v3": {
                "node_id": "child-repair-v3",
                "status": "accepted",
                "superseded_by": "",
            },
        }

        active_ids, lineage = runtime._active_route_child_lineage(ledger, ["child-old"])

        self.assertEqual(active_ids, ["child-repair-v3"])
        self.assertEqual(lineage[0]["lineage_node_ids"], ["child-old", "child-repair-v2", "child-repair-v3"])
        self.assertTrue(lineage[0]["changed"])

        ledger["route_nodes"]["missing-old"] = {
            "node_id": "missing-old",
            "status": "superseded",
            "superseded_by": "missing-repair",
        }
        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "missing route node"):
            runtime._active_route_child_lineage(ledger, ["missing-old"])

        ledger["route_nodes"]["cycle-a"] = {
            "node_id": "cycle-a",
            "status": "superseded",
            "superseded_by": "cycle-b",
        }
        ledger["route_nodes"]["cycle-b"] = {
            "node_id": "cycle-b",
            "status": "superseded",
            "superseded_by": "cycle-a",
        }
        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "cycle"):
            runtime._active_route_child_lineage(ledger, ["cycle-a"])

        ledger["route_nodes"]["route-replaced-child"] = {
            "node_id": "route-replaced-child",
            "status": "superseded",
            "superseded_by": "route-v2",
        }
        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "route replacement"):
            runtime._active_route_child_lineage(ledger, ["route-replaced-child"])

    def test_active_child_lineage_rejects_duplicate_active_targets(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        ledger["route_nodes"] = {
            "child-a-old": {
                "node_id": "child-a-old",
                "status": "superseded",
                "superseded_by": "child-active",
            },
            "child-b-old": {
                "node_id": "child-b-old",
                "status": "superseded",
                "superseded_by": "child-active",
            },
            "child-active": {
                "node_id": "child-active",
                "status": "accepted",
                "superseded_by": "",
            },
        }

        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "duplicate active child"):
            runtime._active_route_child_lineage(ledger, ["child-a-old", "child-b-old"])

    def test_parent_backward_replay_uses_active_child_replacement_result(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        authorize_background_collaboration(ledger)
        ledger["high_standard_control_flow_required"] = True
        runtime.create_route(ledger, "Route", ["Parent", "Child"])
        route_version = ledger["active_route_version"]
        parent_id = "parent-1"
        old_child_id = "child-1"
        active_child_id = "child-1-repair-v2"
        ledger["routes"][str(route_version)]["node_order"] = [parent_id, old_child_id, active_child_id]
        ledger["route_nodes"][parent_id] = {
            "node_id": parent_id,
            "route_version": route_version,
            "title": "Parent",
            "node_kind": "module",
            "status": "awaiting_parent_backward_replay",
            "responsibility": "reviewer",
            "modeled_target": "development_process",
            "repair_generation": 0,
            "acceptance_criteria": ["children compose"],
            "child_node_ids": [old_child_id],
        }
        ledger["route_nodes"][old_child_id] = {
            "node_id": old_child_id,
            "route_version": route_version,
            "title": "Old Child",
            "node_kind": "leaf",
            "parent_node_id": parent_id,
            "status": "superseded",
            "accepted_result_id": "old-child-result",
            "superseded_by": active_child_id,
            "repair_generation": 0,
            "acceptance_criteria": ["old child accepted"],
            "child_node_ids": [],
        }
        ledger["route_nodes"][active_child_id] = {
            "node_id": active_child_id,
            "route_version": route_version,
            "title": "Active Child Repair",
            "node_kind": "leaf",
            "parent_node_id": parent_id,
            "status": "accepted",
            "accepted_result_id": "active-child-result",
            "superseded_by": "",
            "repair_generation": 1,
            "acceptance_criteria": ["active child accepted"],
            "child_node_ids": [],
        }
        self._accept_node_entry_gate(ledger, parent_id)

        packet_id = runtime.ensure_parent_backward_replay_packet(ledger, parent_id)
        packet_body = json.loads(ledger["packets"][packet_id]["body"])

        self.assertEqual(packet_body["child_node_ids"], [active_child_id])
        self.assertEqual(packet_body["current_repair_child_result_ids"], ["active-child-result"])
        self.assertEqual(packet_body["active_child_lineage"][0]["original_child_node_id"], old_child_id)
        self.assertEqual(packet_body["active_child_lineage"][0]["active_child_node_id"], active_child_id)
        self.assertNotIn("old-child-result", packet_body["current_repair_child_result_ids"])

        reviewer = runtime.lease_agent(ledger, "reviewer", agent_id="reviewer-parent-active", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, reviewer)
        runtime.ack_lease(ledger, reviewer, packet_id)
        replay_body = packet_result_contracts.minimal_valid_shape_for_family("review.parent_backward_replay")
        replay_body.update(
            {
                "reviewed_by_role": "human_like_reviewer",
                "passed": True,
                "parent_node_id": parent_id,
                "child_node_ids": [active_child_id],
                "child_evidence_refs": ["active-child-result"],
                "findings": [],
                "blockers": [],
            }
        )
        runtime.submit_result(ledger, reviewer, packet_id, json.dumps(replay_body))

        replay_id = ledger["route_nodes"][parent_id]["parent_backward_replay_id"]
        replay_record = ledger["parent_backward_replays"][replay_id]
        self.assertEqual(replay_record["child_node_ids"], [active_child_id])
        self.assertEqual(replay_record["current_repair_child_result_ids"], ["active-child-result"])
        self.assertEqual(replay_record["active_child_lineage"][0]["original_child_node_id"], old_child_id)

    def test_parent_backward_replay_blocks_active_child_without_current_result(self) -> None:
        ledger, parent_id, _old_child_id, active_child_id = self._parent_replacement_replay_fixture(
            active_child_result_id="",
        )

        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "accepted child results.*" + active_child_id):
            runtime.ensure_parent_backward_replay_packet(ledger, parent_id)

    def test_parent_backward_replay_rejects_reviewer_superseded_child_ids(self) -> None:
        ledger, parent_id, old_child_id, active_child_id = self._parent_replacement_replay_fixture()
        packet_id = runtime.ensure_parent_backward_replay_packet(ledger, parent_id)
        reviewer = runtime.lease_agent(ledger, "reviewer", agent_id="reviewer-parent-old-child", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, reviewer)
        runtime.ack_lease(ledger, reviewer, packet_id)
        replay_body = packet_result_contracts.minimal_valid_shape_for_family("review.parent_backward_replay")
        replay_body.update(
            {
                "reviewed_by_role": "human_like_reviewer",
                "passed": True,
                "parent_node_id": parent_id,
                "child_node_ids": [old_child_id],
                "child_evidence_refs": ["active-child-result"],
                "findings": [],
                "blockers": [],
            }
        )

        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "child_node_ids must match active child lineage"):
            runtime.submit_result(ledger, reviewer, packet_id, json.dumps(replay_body))
        self.assertFalse(ledger["route_nodes"][parent_id].get("parent_backward_replay_id"))
        self.assertEqual(json.loads(ledger["packets"][packet_id]["body"])["child_node_ids"], [active_child_id])

    def test_parent_backward_replay_rejects_superseded_child_evidence_refs(self) -> None:
        ledger, parent_id, _old_child_id, active_child_id = self._parent_replacement_replay_fixture()
        packet_id = runtime.ensure_parent_backward_replay_packet(ledger, parent_id)
        reviewer = runtime.lease_agent(ledger, "reviewer", agent_id="reviewer-parent-old-result", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, reviewer)
        runtime.ack_lease(ledger, reviewer, packet_id)
        replay_body = packet_result_contracts.minimal_valid_shape_for_family("review.parent_backward_replay")
        replay_body.update(
            {
                "reviewed_by_role": "human_like_reviewer",
                "passed": True,
                "parent_node_id": parent_id,
                "child_node_ids": [active_child_id],
                "child_evidence_refs": ["old-child-result"],
                "findings": [],
                "blockers": [],
            }
        )

        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "child_evidence_refs must match active child result ids"):
            runtime.submit_result(ledger, reviewer, packet_id, json.dumps(replay_body))
        self.assertFalse(ledger["route_nodes"][parent_id].get("parent_backward_replay_id"))

    def test_parent_backward_replay_rejects_unresolved_active_child_lineage(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        authorize_background_collaboration(ledger)
        ledger["high_standard_control_flow_required"] = True
        runtime.create_route(ledger, "Route", ["Parent", "Child"])
        route_version = ledger["active_route_version"]
        parent_id = "parent-1"
        child_id = "child-1"
        ledger["route_nodes"][parent_id] = {
            "node_id": parent_id,
            "route_version": route_version,
            "title": "Parent",
            "node_kind": "module",
            "status": "awaiting_parent_backward_replay",
            "responsibility": "reviewer",
            "modeled_target": "development_process",
            "repair_generation": 0,
            "acceptance_criteria": ["children compose"],
            "child_node_ids": [child_id],
        }
        ledger["route_nodes"][child_id] = {
            "node_id": child_id,
            "route_version": route_version,
            "title": "Child",
            "node_kind": "leaf",
            "parent_node_id": parent_id,
            "status": "superseded",
            "accepted_result_id": "old-child-result",
            "superseded_by": "missing-repair",
            "repair_generation": 0,
            "acceptance_criteria": ["old child accepted"],
            "child_node_ids": [],
        }
        self._accept_node_entry_gate(ledger, parent_id)

        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "missing route node"):
            runtime.ensure_parent_backward_replay_packet(ledger, parent_id)

    def test_multiple_parent_backward_review_gaps_return_oldest_parent_gap_to_owner(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        authorize_background_collaboration(ledger)
        ledger["contract_frozen"] = True
        ledger["recursive_route_execution_required"] = True
        ledger["high_standard_control_flow_required"] = True
        runtime.create_route(ledger, "Route", ["Root", "Parent", "Child"])
        route_version = ledger["active_route_version"]
        ledger["routes"][str(route_version)]["node_order"] = ["root", "parent", "child"]
        ledger["route_nodes"] = {
            "root": {
                "node_id": "root",
                "route_version": route_version,
                "title": "Root",
                "node_kind": "module",
                "status": "awaiting_parent_backward_replay",
                "child_node_ids": ["parent"],
            },
            "parent": {
                "node_id": "parent",
                "route_version": route_version,
                "title": "Parent",
                "node_kind": "module",
                "parent_node_id": "root",
                "status": "awaiting_parent_backward_replay",
                "child_node_ids": ["child"],
            },
            "child": {
                "node_id": "child",
                "route_version": route_version,
                "title": "Child",
                "node_kind": "leaf",
                "parent_node_id": "parent",
                "status": "accepted",
                "child_node_ids": [],
            },
        }
        self._accept_node_entry_gate(ledger, "root")
        self._accept_node_entry_gate(ledger, "parent")
        self._accept_node_entry_gate(ledger, "child")
        ledger["execution_frontier"] = {
            "active_route_version": route_version,
            "active_node_id": "",
            "completed_nodes": ["child"],
            "status": "ready_for_final_closure",
        }

        action = runtime.router_next_action(ledger)

        self.assertEqual(action.action_type, "issue_parent_backward_replay_packet")
        self.assertEqual(action.subject_id, "root")
        self.assertEqual(action.reason, "control_plane_hard_gate_escape:missing_parent_backward_replay:root")
        unresolved = ledger["final_route_wide_gate_ledger"]["unresolved"]
        self.assertIn("control_plane_parent_backward_review_multiple_gaps", unresolved)

    def test_terminal_replay_hard_blocks_when_parent_review_gap_reaches_final_gate(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        authorize_background_collaboration(ledger)
        ledger["contract_frozen"] = True
        ledger["recursive_route_execution_required"] = True
        ledger["high_standard_control_flow_required"] = True
        runtime.create_route(ledger, "Route", ["Parent", "Child"])
        route_version = ledger["active_route_version"]
        ledger["routes"][str(route_version)]["node_order"] = ["parent", "child"]
        ledger["execution_frontier"] = {
            "active_route_version": route_version,
            "active_node_id": "",
            "completed_nodes": ["child"],
            "status": "ready_for_final_closure",
        }
        ledger["latest_validation_evidence_id"] = "validation-current"
        ledger["route_nodes"] = {
            "parent": {
                "node_id": "parent",
                "route_version": route_version,
                "title": "Parent",
                "node_kind": "module",
                "status": "accepted",
                "child_node_ids": ["child"],
            },
            "child": {
                "node_id": "child",
                "route_version": route_version,
                "title": "Child",
                "node_kind": "leaf",
                "parent_node_id": "parent",
                "status": "accepted",
                "child_node_ids": [],
            },
        }
        self._accept_node_entry_gate(ledger, "parent")
        self._accept_node_entry_gate(ledger, "child")

        action = runtime.router_next_action(ledger)

        self.assertEqual(action.action_type, "issue_parent_backward_replay_packet")
        self.assertEqual(action.subject_id, "parent")
        self.assertEqual(action.reason, "control_plane_hard_gate_escape:missing_parent_backward_replay:parent")
        self.assertFalse(runtime._final_gate_ledgers_clean_for_terminal_replay(ledger))

    def test_pm_disposition_packet_minimal_shape_uses_current_node_acceptance_items(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Node one"])
        route_version = ledger["active_route_version"]
        ledger["route_nodes"]["node-with-items"] = {
            "node_id": "node-with-items",
            "route_version": route_version,
            "title": "Node With Items",
            "status": "running",
            "responsibility": "worker",
            "modeled_target": "development_process",
            "repair_generation": 0,
            "acceptance_criteria": ["criterion"],
            "child_node_ids": [],
            "acceptance_item_ids": ["acc-node-001", "acc-node-002"],
        }
        ledger["route_nodes"]["node-without-items"] = {
            "node_id": "node-without-items",
            "route_version": route_version,
            "title": "Node Without Items",
            "status": "running",
            "responsibility": "worker",
            "modeled_target": "development_process",
            "repair_generation": 0,
            "acceptance_criteria": ["criterion"],
            "child_node_ids": [],
            "acceptance_item_ids": [],
        }
        subject_with_items = runtime.issue_task_packet(
            ledger,
            "worker",
            "Work with items",
            "BODY",
            route_node_id="node-with-items",
            route_scope="node",
        )
        subject_without_items = runtime.issue_task_packet(
            ledger,
            "worker",
            "Work without items",
            "BODY",
            route_node_id="node-without-items",
            route_scope="node",
        )

        packet_with_items = runtime._ensure_pm_disposition_packet_for_node(
            ledger,
            "node-with-items",
            subject_with_items,
        )
        packet_without_items = runtime._ensure_pm_disposition_packet_for_node(
            ledger,
            "node-without-items",
            subject_without_items,
        )

        body_with_items = json.loads(ledger["packets"][packet_with_items]["body"])
        body_without_items = json.loads(ledger["packets"][packet_without_items]["body"])
        self.assertEqual(body_with_items["node_acceptance_item_ids"], ["acc-node-001", "acc-node-002"])
        self.assertEqual(
            [
                row["acceptance_item_id"]
                for row in body_with_items["minimal_valid_shape"]["acceptance_item_disposition"]
            ],
            ["acc-node-001", "acc-node-002"],
        )
        self.assertEqual(body_without_items["node_acceptance_item_ids"], [])
        self.assertEqual(body_without_items["minimal_valid_shape"]["acceptance_item_disposition"], [])

    def test_pm_disposition_mechanical_reissue_preserves_current_node_acceptance_items(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Node one"])
        route_version = ledger["active_route_version"]
        ledger["route_nodes"]["node-1"] = {
            "node_id": "node-1",
            "route_version": route_version,
            "title": "Node One",
            "status": "running",
            "responsibility": "worker",
            "modeled_target": "development_process",
            "repair_generation": 0,
            "acceptance_criteria": ["criterion"],
            "child_node_ids": [],
            "acceptance_item_ids": ["acc-node-001"],
            "high_standard_requirement_ids": ["hsr-node-001"],
            "validation_evidence_ids": ["validation-node-001"],
        }
        subject_packet_id = runtime.issue_task_packet(
            ledger,
            "worker",
            "Work with items",
            "BODY",
            route_node_id="node-1",
            route_scope="node",
        )
        packet_id = runtime._ensure_pm_disposition_packet_for_node(ledger, "node-1", subject_packet_id)
        lease_id = runtime.lease_agent(ledger, "pm", agent_id="pm-bad-disposition", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)

        result_id = runtime.submit_result(
            ledger,
            lease_id,
            packet_id,
            json.dumps({"decision": "accept", "summary": "old field must be rejected"}),
        )

        self.assertEqual(ledger["results"][result_id]["status"], "mechanical_contract_blocked")
        reissues = [
            packet for packet in ledger["packets"].values()
            if packet["packet_id"] != packet_id
            and packet["envelope"]["packet_kind"] == "pm_disposition"
            and packet["status"] == "open"
        ]
        self.assertEqual(len(reissues), 1)
        reissue_body = json.loads(reissues[0]["body"])
        self.assertEqual(reissue_body["schema_version"], "black_box_flowpilot.pm_disposition_reissue_packet.v1")
        self.assertEqual(reissue_body["node_acceptance_item_ids"], ["acc-node-001"])
        self.assertEqual(
            [
                row["acceptance_item_id"]
                for row in reissue_body["minimal_valid_shape"]["acceptance_item_disposition"]
            ],
            ["acc-node-001"],
        )

    def test_node_acceptance_plan_mechanical_reissue_preserves_acceptance_items(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Node one"])
        route_version = ledger["active_route_version"]
        ledger["route_nodes"]["node-1"] = {
            "node_id": "node-1",
            "route_version": route_version,
            "title": "Node One",
            "status": "pending",
            "responsibility": "worker",
            "modeled_target": "development_process",
            "repair_generation": 0,
            "acceptance_criteria": ["criterion"],
            "child_node_ids": [],
            "acceptance_item_ids": ["acc-node-001"],
        }
        packet_id = runtime.ensure_node_acceptance_plan_packet(ledger, "node-1")
        lease_id = runtime.lease_agent(ledger, "pm", agent_id="pm-node-bad-plan", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)

        result_id = runtime.submit_result(
            ledger,
            lease_id,
            packet_id,
            json.dumps({"decision": "pass"}),
        )

        self.assertEqual(ledger["results"][result_id]["status"], "mechanical_contract_blocked")
        reissues = [
            packet for packet in ledger["packets"].values()
            if packet["packet_id"] != packet_id
            and packet["envelope"]["route_scope"] == "node_acceptance_plan"
            and packet["status"] == "open"
        ]
        self.assertEqual(len(reissues), 1)
        reissue_body = json.loads(reissues[0]["body"])
        self.assertEqual(reissue_body["schema_version"], "black_box_flowpilot.node_acceptance_plan_reissue_packet.v1")
        self.assertEqual(reissue_body["acceptance_item_ids"], ["acc-node-001"])

    def test_node_acceptance_redesign_route_rejects_flat_peer_leaf_split(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Node one"])
        ledger["route_nodes"]["node-1"] = {
            "node_id": "node-1",
            "title": "Node One",
            "status": "pending",
            "repair_generation": 0,
            "acceptance_criteria": ["criterion"],
        }
        packet_id = runtime.ensure_node_acceptance_plan_packet(ledger, "node-1")
        lease_id = runtime.lease_agent(ledger, "pm", agent_id="pm-node-flat-redesign", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)

        result_id = runtime.submit_result(
            ledger,
            lease_id,
            packet_id,
            json.dumps(
                {
                    "decision": "redesign_route",
                    "pm_visible_summary": ["Current node is too broad, but this split is flat."],
                    "reason": "Current node needs decomposition.",
                    "route_plan": {
                        "schema_version": runtime.ROUTE_PLAN_SCHEMA_VERSION,
                        "nodes": [
                            {
                                "node_id": "node-1-a",
                                "title": "Flat child A",
                                "node_kind": "leaf",
                                "acceptance_criteria": ["A is done."],
                            },
                            {
                                "node_id": "node-1-b",
                                "title": "Flat child B",
                                "node_kind": "leaf",
                                "acceptance_criteria": ["B is done."],
                            },
                        ],
                    },
                }
            ),
        )

        result = ledger["results"][result_id]
        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertEqual(result["mechanical_contract_failure"]["failed_branch"], "decision=redesign_route")
        self.assertEqual(result["mechanical_contract_failure"]["failed_field_path"], "route_plan.nodes[].node_kind")
        self.assertFalse(ledger["pm_decision_gates"])

    def test_node_acceptance_redesign_route_accepts_replacement_parent_scope(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Node one"])
        ledger["route_nodes"]["node-1"] = {
            "node_id": "node-1",
            "title": "Node One",
            "status": "pending",
            "repair_generation": 0,
            "acceptance_criteria": ["criterion"],
        }
        packet_id = runtime.ensure_node_acceptance_plan_packet(ledger, "node-1")
        lease_id = runtime.lease_agent(ledger, "pm", agent_id="pm-node-parent-redesign", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)

        result_id = runtime.submit_result(
            ledger,
            lease_id,
            packet_id,
            json.dumps(
                {
                    "decision": "redesign_route",
                    "pm_visible_summary": ["Current node is promoted into a replacement parent scope."],
                    "reason": "Current node needs a child subtree.",
                    "route_plan": {
                        "schema_version": runtime.ROUTE_PLAN_SCHEMA_VERSION,
                        "nodes": [
                            {
                                "node_id": "node-1-replacement",
                                "title": "Replacement parent for Node One",
                                "node_kind": "module",
                                "parent_node_id": "",
                                "child_node_ids": ["node-1-a", "node-1-b"],
                                "acceptance_criteria": ["Children compose into Node One acceptance."],
                            },
                            {
                                "node_id": "node-1-a",
                                "title": "Child A",
                                "node_kind": "leaf",
                                "parent_node_id": "node-1-replacement",
                                "child_node_ids": [],
                                "acceptance_criteria": ["A is done."],
                            },
                            {
                                "node_id": "node-1-b",
                                "title": "Child B",
                                "node_kind": "leaf",
                                "parent_node_id": "node-1-replacement",
                                "child_node_ids": [],
                                "acceptance_criteria": ["B is done."],
                            },
                        ],
                    },
                }
            ),
        )

        result = ledger["results"][result_id]
        self.assertEqual(result["staged_effect"]["effect_kind"], "commit_route_redesign")
        gate = next(iter(ledger["pm_decision_gates"].values()))
        self.assertEqual(gate["status"], "awaiting_flowguard")
        self.assertEqual(gate["staged_effect"]["target_node_id"], "node-1")

    def test_strict_route_plan_topology_rejects_bad_parent_child_shapes(self) -> None:
        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "module node parent requires child_node_ids"):
            runtime._normalize_strict_route_plan_nodes(
                {
                    "nodes": [
                        {"node_id": "parent", "title": "Parent", "node_kind": "module"},
                    ]
                }
            )
        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "leaf node leaf must not have child_node_ids"):
            runtime._normalize_strict_route_plan_nodes(
                {
                    "nodes": [
                        {"node_id": "leaf", "title": "Leaf", "node_kind": "leaf", "child_node_ids": ["child"]},
                        {"node_id": "child", "title": "Child", "node_kind": "leaf"},
                    ]
                }
            )
        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "reference unknown node"):
            runtime._normalize_strict_route_plan_nodes(
                {
                    "nodes": [
                        {"node_id": "parent", "title": "Parent", "node_kind": "module", "child_node_ids": ["missing"]},
                    ]
                }
            )
        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "parent_node_id must match parent"):
            runtime._normalize_strict_route_plan_nodes(
                {
                    "nodes": [
                        {"node_id": "parent", "title": "Parent", "node_kind": "module", "child_node_ids": ["child"]},
                        {"node_id": "other", "title": "Other", "node_kind": "module", "child_node_ids": ["child"]},
                        {"node_id": "child", "title": "Child", "node_kind": "leaf", "parent_node_id": "other"},
                    ]
                }
            )

    def test_node_acceptance_plan_review_packet_marks_plan_stage_boundary(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Node one"])
        ledger["route_nodes"]["node-1"] = {
            "node_id": "node-1",
            "title": "Node One",
            "status": "pending",
            "repair_generation": 0,
            "acceptance_criteria": ["criterion"],
        }
        packet_id = runtime.ensure_node_acceptance_plan_packet(ledger, "node-1")
        lease_id = runtime.lease_agent(ledger, "pm", agent_id="pm-node", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)
        package = copy.deepcopy(
            packet_result_contracts.minimal_valid_shape_for_family("task.node_acceptance_plan")["node_context_package"]
        )
        package.update(
            {
                "node_id": "node-1",
                "purpose": "Provide current starting context.",
                "acceptance_criteria": ["criterion"],
                "relevant_references": ["reference"],
                "known_risks": ["risk"],
                "acceptance_item_projection": [],
            }
        )

        runtime.submit_result(
            ledger,
            lease_id,
            packet_id,
            json.dumps({"node_context_package": package, "decision": "pass"}),
        )

        review_packets = [
            packet for packet in ledger["packets"].values()
            if packet["envelope"]["packet_kind"] == "review"
            and packet["envelope"]["subject_id"] == packet_id
        ]
        self.assertEqual(len(review_packets), 1)
        review_window = review_packets[0]["envelope"]["review_window"]
        self.assertEqual(review_window["review_flow_id"], "node_acceptance_plan_review")
        self.assertEqual(
            review_window["review_depth_rule"],
            review_window_contracts.review_flow_stage_challenge_rule("node_acceptance_plan_review"),
        )
        self.assertIn("reviewer.node_acceptance_plan_review", review_window["review_depth_rule"])
        self.assertIn("weakest", review_window["review_depth_rule"].lower())
        self.assertIn("hypothesis", review_window["review_depth_rule"].lower())
        review_body = json.loads(review_packets[0]["body"])
        self.assertIn("plan-stage review", review_body["instruction"])
        self.assertIn("Do not block solely because Worker artifacts", review_body["instruction"])
        self.assertIn("post-result FlowGuard evidence", review_body["instruction"])
        self.assertFalse(review_body["flowguard_evidence_manifest"]["matching_flowguard_result_reads_required"])
        self.assertEqual(review_body["staged_effect"]["effect_kind"], "commit_node_acceptance_plan")

    def _assert_staged_effect_same_family_rejects_different_formal_blocker_identity(self) -> None:
        record: dict[str, object] = {}

        first = runtime._attach_staged_effect(
            record,
            effect_kind="commit_route_redesign",
            source_packet_id="packet-1",
            source_result_id="result-1",
            target_node_id="node-1",
            blocker_id="blocker-1",
            gate_id="gate-1",
            route_scope="node",
        )
        reused = runtime._attach_staged_effect(
            record,
            effect_kind="commit_route_redesign",
            source_packet_id="packet-2",
            source_result_id="result-2",
            target_node_id="node-2",
            blocker_id="blocker-1",
            gate_id="gate-2",
            route_scope="node",
        )

        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "repair blocker identity mismatch"):
            runtime._attach_staged_effect(
                record,
                effect_kind="commit_route_redesign",
                source_packet_id="packet-3",
                source_result_id="result-3",
                target_node_id="node-3",
                blocker_id="blocker-2",
                gate_id="gate-3",
                route_scope="node",
            )

        self.assertIs(reused, first)
        self.assertEqual(record["staged_effect"], first)
        self.assertEqual(first["source_packet_id"], "packet-1")
        self.assertEqual(first["gate_id"], "gate-1")

    def test_staged_effect_same_family_reuses_pending_effect_and_rejects_different_formal_blocker_identity(self) -> None:
        self._assert_staged_effect_same_family_rejects_different_formal_blocker_identity()

    def test_staged_effect_same_family_rejects_different_formal_blocker_identity(self) -> None:
        self._assert_staged_effect_same_family_rejects_different_formal_blocker_identity()

    def test_formal_repair_identity_mismatch_is_runtime_mechanical_blocker(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Do work"])
        packet_id = runtime.issue_task_packet(
            ledger,
            "worker",
            "Repair",
            json.dumps({"blocker_id": "blocker-body", "instruction": "Repair"}),
            repair_blocker_id="blocker-formal",
        )
        packet = ledger["packets"][packet_id]
        payload = json.loads(packet["body"])
        payload["current_handoff_contract"]["input_material_manifest"]["blocker_id"] = "blocker-body"
        packet["body"] = json.dumps(payload, indent=2, sort_keys=True)
        packet["envelope"]["body_hash"] = runtime.hash_text(packet["body"])
        lease_id = runtime.lease_agent(ledger, "worker", agent_id="worker-formal", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)

        result_id = runtime.submit_result(ledger, lease_id, packet_id, role_result_body("Mismatched blocker."))
        result = ledger["results"][result_id]

        self.assertEqual(result["status"], "blocked")
        self.assertTrue(
            any("repair_blocker_id_mismatch" in item for item in result["mechanical_blockers"]),
            result["mechanical_blockers"],
        )

    def test_repair_packet_handoff_contract_carries_formal_blocker_identity(self) -> None:
        ledger, _packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, _packet_id)
        runtime.submit_result(
            ledger,
            worker,
            _packet_id,
            role_result_body(
                "Worker found a current blocker.",
                decision="block",
                blocking=True,
                blocker_class="needs_repair",
                recommended_resolution="repair current scope",
            ),
        )
        blocker_id = next(iter(ledger["active_blockers"]))
        pm_packet = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
        pm_lease = runtime.lease_agent(ledger, "pm", agent_id="pm-formal", packet_id=pm_packet)
        runtime.assign_packet(ledger, pm_packet, pm_lease)
        runtime.ack_lease(ledger, pm_lease, pm_packet)
        open_required_result_reads(ledger, pm_packet, pm_lease)
        runtime.submit_result(
            ledger,
            pm_lease,
            pm_packet,
            pm_repair_decision_body(
                ledger,
                pm_packet,
                decision="repair_current_scope",
                reason="Repair current packet.",
            ),
        )
        self._complete_pm_continue_repair_gate(ledger, blocker_id)
        repair_packets = [
            packet
            for packet in ledger["packets"].values()
            if packet.get("repair_blocker_id") == blocker_id
            and packet["envelope"]["packet_kind"] == "task"
            and packet["status"] == "open"
        ]
        self.assertEqual(len(repair_packets), 1)
        repair_packet = repair_packets[0]
        body = json.loads(repair_packet["body"])

        self.assertEqual(repair_packet["envelope"]["repair_blocker_id"], blocker_id)
        self.assertEqual(repair_packet["repair_blocker_id"], blocker_id)
        self.assertEqual(body["blocker_id"], blocker_id)
        self.assertEqual(
            repair_packet["envelope"]["current_handoff_contract"]["input_material_manifest"]["blocker_id"],
            blocker_id,
        )
        self.assertEqual(
            body["current_handoff_contract"]["input_material_manifest"]["blocker_id"],
            blocker_id,
        )

    def test_formal_repair_identity_prose_only_is_runtime_mechanical_blocker(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Do work"])
        packet_id = runtime.issue_task_packet(
            ledger,
            "worker",
            "Repair",
            json.dumps({"blocker_id": "blocker-body", "instruction": "Repair"}),
        )
        lease_id = runtime.lease_agent(ledger, "worker", agent_id="worker-prose-only", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)

        result_id = runtime.submit_result(ledger, lease_id, packet_id, role_result_body("Body-only blocker."))
        result = ledger["results"][result_id]

        self.assertEqual(result["status"], "blocked")
        self.assertTrue(
            any("repair_blocker_id_missing_formal_field" in item for item in result["mechanical_blockers"]),
            result["mechanical_blockers"],
        )

    def test_redesign_route_pm_decision_stages_route_effect_until_gate_applies(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Node one"])
        ledger["route_nodes"]["node-1"] = {
            "node_id": "node-1",
            "title": "Node One",
            "status": "running",
            "repair_generation": 0,
            "acceptance_criteria": ["criterion"],
        }
        packet_id = runtime.issue_task_packet(
            ledger,
            "worker",
            "Do node work",
            "NODE_PACKET",
            route_node_id="node-1",
            route_scope="node",
        )
        lease_id = runtime.lease_agent(ledger, "worker", agent_id="worker-node", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)
        runtime.submit_result(
            ledger,
            lease_id,
            packet_id,
            role_result_body("Worker found the current route needs redesign.", decision="block", blocking=True, recommended_resolution="redesign route"),
        )
        blocker_id = next(iter(ledger["active_blockers"]))
        pm_packet = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
        pm_lease = runtime.lease_agent(ledger, "pm", agent_id="pm-route", packet_id=pm_packet)
        runtime.assign_packet(ledger, pm_packet, pm_lease)
        runtime.ack_lease(ledger, pm_lease, pm_packet)
        open_required_result_reads(ledger, pm_packet, pm_lease)
        active_route_version = ledger["active_route_version"]

        result_id = runtime.submit_result(
            ledger,
            pm_lease,
            pm_packet,
            pm_repair_decision_body(
                ledger,
                pm_packet,
                decision="redesign_route",
                reason="Current route cannot complete cleanly.",
                route_plan={
                        "schema_version": runtime.ROUTE_PLAN_SCHEMA_VERSION,
                        "decision": "pass",
                        "nodes": [
                            {
                                "node_id": "node-redesign-001",
                                "title": "Repair redesigned node",
                                "responsibility": "worker",
                                "modeled_target": "development_process",
                                "acceptance_criteria": ["Repair route has fresh executable work."],
                            }
                        ],
                    },
            ),
        )

        gate = next(iter(ledger["pm_decision_gates"].values()))
        self.assertEqual(gate["status"], "awaiting_flowguard")
        self.assertEqual(gate["staged_effect"]["effect_kind"], "commit_route_redesign")
        self.assertEqual(gate["staged_effect"]["status"], "pending")
        self.assertEqual(ledger["results"][result_id]["staged_effect"]["effect_kind"], "commit_route_redesign")
        self.assertEqual(ledger["active_route_version"], active_route_version)

    def test_repair_current_scope_preserves_pm_repair_decision_packet_kind(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        runtime.create_route(ledger, "Route", ["Do work"])
        target_blocker_id = "blocker-target"
        ledger["active_blockers"][target_blocker_id] = {
            "blocker_id": target_blocker_id,
            "status": "active",
            "outcome_id": "outcome-target",
            "packet_id": "packet-target",
            "packet_kind": "task",
            "subject_packet_id": "packet-target",
            "repair_target_packet_id": "packet-target",
            "target_result_id": "",
            "result_id": "result-target",
            "owner_role": "worker",
            "required_recheck_role": "worker",
            "gate_kind": "task",
            "blocker_class": "local_artifact",
            "recommended_resolution": "repair",
            "route_version": ledger["active_route_version"],
            "route_node_id": "",
            "route_scope": "",
            "repair_generation": 0,
            "stale_evidence_ids": [],
            "created_at": runtime.now_iso(),
            "pm_repair_packet_id": "",
            "pm_repair_decision_id": "",
            "cleared_by_outcome_id": "",
        }
        pm_repair_packet = runtime._ensure_pm_repair_decision_packet_for_blocker(ledger, target_blocker_id)
        reissue_blocker_id = "blocker-reissue"
        decision_id = "pm_repair_decision-reissue"
        ledger["active_blockers"][reissue_blocker_id] = {
            **ledger["active_blockers"][target_blocker_id],
            "blocker_id": reissue_blocker_id,
            "repair_target_packet_id": pm_repair_packet,
            "subject_packet_id": pm_repair_packet,
            "packet_id": pm_repair_packet,
            "pm_repair_packet_id": "",
            "pm_repair_decision_id": decision_id,
        }
        ledger["pm_repair_decisions"][decision_id] = {
            "decision_id": decision_id,
            "blocker_id": reissue_blocker_id,
            "packet_id": "packet-decision",
            "result_id": "result-decision",
            "decision": "repair_current_scope",
            "reason": "Replace PM decision in same current scope.",
            "created_at": runtime.now_iso(),
        }

        runtime._apply_pm_repair_decision(ledger, reissue_blocker_id, decision_id)

        fresh_packet_id = ledger["repair_transactions"][decision_id]["fresh_packet_id"]
        fresh = ledger["packets"][fresh_packet_id]
        self.assertEqual(fresh["envelope"]["packet_kind"], "pm_repair_decision")
        self.assertEqual(fresh["envelope"]["route_scope"], "pm_repair_decision")
        self.assertEqual(fresh["envelope"]["subject_id"], pm_repair_packet)

    def _flowguard_reissue_after_forbidden_fallback(self) -> tuple[dict[str, object], str, str, str]:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(ledger, worker, packet_id, role_result_body("Worker submitted current runtime evidence."))
        flowguard_packet = next(
            packet
            for packet in ledger["packets"].values()
            if packet["envelope"]["packet_kind"] == "flowguard_check"
            and packet["envelope"]["subject_id"] == packet_id
        )
        flowguard_lease = runtime.lease_agent(
            ledger,
            "flowguard_operator",
            agent_id="fg",
            packet_id=flowguard_packet["packet_id"],
        )
        runtime.assign_packet(ledger, flowguard_packet["packet_id"], flowguard_lease)
        runtime.ack_lease(ledger, flowguard_lease, flowguard_packet["packet_id"])
        open_required_result_reads(ledger, flowguard_packet["packet_id"], flowguard_lease)

        result_id = runtime.submit_result(
            ledger,
            flowguard_lease,
            flowguard_packet["packet_id"],
            flowguard_result_body(
                "FlowGuard attempted forbidden fallback evidence.",
                evidence_mode="api_fallback_manual_block_eval",
            ),
        )

        self.assertEqual(ledger["results"][result_id]["status"], "mechanical_contract_blocked")
        self.assertEqual(ledger["packets"][flowguard_packet["packet_id"]]["status"], "superseded_after_repair")
        reissues = [
            packet for packet in ledger["packets"].values()
            if packet["packet_id"] != flowguard_packet["packet_id"]
            and packet["envelope"]["packet_kind"] == "flowguard_check"
            and packet["envelope"]["subject_id"] == packet_id
            and packet["status"] == "open"
        ]
        self.assertEqual(len(reissues), 1)
        return ledger, packet_id, flowguard_packet["packet_id"], reissues[0]["packet_id"]

    def test_flowguard_fallback_evidence_is_mechanically_reissued(self) -> None:
        ledger, _packet_id, flowguard_packet_id, reissue_packet_id = self._flowguard_reissue_after_forbidden_fallback()
        reissue_packet = ledger["packets"][reissue_packet_id]
        reissue_body = json.loads(reissue_packet["body"])
        original_body = json.loads(ledger["packets"][flowguard_packet_id]["body"])
        self.assertIn("evidence_output_policy", reissue_body)
        self.assertTrue(reissue_body["evidence_output_policy"]["required_for_formal_run"])
        self.assertNotEqual(
            reissue_body["evidence_output_policy"]["run_local_evidence_root"],
            original_body["evidence_output_policy"]["run_local_evidence_root"],
        )
        self.assertIn(reissue_packet["packet_id"], reissue_body["evidence_output_policy"]["run_local_evidence_root"])

    def test_flowguard_reissue_inherits_required_authorized_result_reads(self) -> None:
        ledger, _packet_id, flowguard_packet_id, reissue_packet_id = self._flowguard_reissue_after_forbidden_fallback()
        source_packet = ledger["packets"][flowguard_packet_id]
        reissue_packet = ledger["packets"][reissue_packet_id]
        source_reads = source_packet["envelope"]["authorized_result_reads"]
        reissue_reads = reissue_packet["envelope"]["authorized_result_reads"]
        source_required = [
            row["result_id"]
            for row in source_reads
            if row["required_before_submit"] is True
        ]
        reissue_required = [
            row["result_id"]
            for row in reissue_reads
            if row["required_before_submit"] is True
        ]
        reissue_body = json.loads(reissue_packet["body"])
        manifest = reissue_packet["envelope"]["current_handoff_contract"]["input_material_manifest"]

        self.assertEqual(reissue_reads, source_reads)
        self.assertEqual(reissue_body["authorized_result_reads"], source_reads)
        self.assertEqual(manifest["required_authorized_reads_before_submit"], source_required)
        self.assertEqual(
            reissue_body["current_handoff_contract"]["input_material_manifest"]["required_authorized_reads_before_submit"],
            source_required,
        )
        self.assertEqual(reissue_required, source_required)
        self.assertGreater(manifest["required_authorized_read_count"], 0)

    def test_reissued_flowguard_result_blocks_without_inherited_body_open(self) -> None:
        ledger, _packet_id, _flowguard_packet_id, reissue_packet_id = self._flowguard_reissue_after_forbidden_fallback()
        required_result_id = ledger["packets"][reissue_packet_id]["envelope"]["authorized_result_reads"][0]["result_id"]
        flowguard_lease = runtime.lease_agent(
            ledger,
            "flowguard_operator",
            packet_id=reissue_packet_id,
        )
        runtime.assign_packet(ledger, reissue_packet_id, flowguard_lease)
        runtime.ack_lease(ledger, flowguard_lease, reissue_packet_id)

        result_id = runtime.submit_result(
            ledger,
            flowguard_lease,
            reissue_packet_id,
            flowguard_result_body("FlowGuard tried to answer the reissued packet without opening inherited material."),
        )
        result = ledger["results"][result_id]

        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["accepted"])
        self.assertIn(f"required_result_body_not_opened:{required_result_id}", result["mechanical_blockers"])

    def test_review_packet_is_not_issued_with_empty_required_flowguard_manifest(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        result_id = runtime.submit_result(
            ledger,
            worker,
            packet_id,
            role_result_body("Worker submitted current runtime evidence before FlowGuard completed."),
        )

        review_packet = runtime._ensure_review_packet_for_task_result(ledger, packet_id, force_new=True)

        self.assertEqual(review_packet, "")
        self.assertFalse(
            [
                packet
                for packet in ledger["packets"].values()
                if packet["envelope"]["packet_kind"] == "review"
            ]
        )
        blockers = list(ledger["active_blockers"].values())
        self.assertEqual(len(blockers), 1)
        blocker = blockers[0]
        self.assertEqual(blocker["blocker_class"], "missing_matching_flowguard_report")
        self.assertEqual(blocker["gate_kind"], "flowguard_review_handoff")
        self.assertEqual(blocker["required_recheck_role"], "flowguard_operator")
        self.assertEqual(blocker["target_result_id"], result_id)
        self.assertIn("flowguard_evidence_manifest.entries[].flowguard_result_id", blocker["missing_required_fields"])
        self.assertIn("flowguard_missing_matching_report", blocker["root_cause_loop_key"])
        self.assertFalse(
            [
                packet
                for packet in ledger["packets"].values()
                if packet["envelope"]["packet_kind"] == "pm_repair_decision"
            ]
        )
        flowguard_packets = [
            packet
            for packet in ledger["packets"].values()
            if packet["envelope"]["packet_kind"] == "flowguard_check"
            and packet.get("repair_blocker_id") == blocker["blocker_id"]
        ]
        self.assertEqual(len(flowguard_packets), 1)
        flowguard_body = json.loads(flowguard_packets[0]["body"])
        self.assertEqual(flowguard_body["recheck_reason"], "missing_matching_flowguard_report")
        self.assertEqual(flowguard_body["repair_dossier_context"]["hard_next_action"], "issue_matching_flowguard_packet")

    def test_review_packet_target_result_uses_accepted_result_id_over_result_ids_tail(self) -> None:
        ledger = runtime.new_ledger("Build", "Finish")
        ledger["startup_intake"] = {
            "sealed": True,
            "startup_answers": {
                runtime.BACKGROUND_COLLABORATION_ACK_FIELD: True,
            },
        }
        runtime.create_route(ledger, "Route", ["Work"])
        packet_id = runtime.issue_task_packet(
            ledger,
            "worker",
            "Do work",
            "sealed body",
            required_flowguard_target="",
        )
        lease_id = runtime.lease_agent(ledger, "worker", agent_id="worker-a", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)
        accepted_result_id = runtime.submit_result(ledger, lease_id, packet_id, role_result_body("accepted"))
        stale_tail_result_id = "result-historical-stale-tail"
        ledger["results"][stale_tail_result_id] = {
            "result_id": stale_tail_result_id,
            "packet_id": packet_id,
            "producer_lease_id": lease_id,
            "status": "blocked",
            "accepted": False,
        }
        packet = ledger["packets"][packet_id]
        packet["accepted_result_id"] = accepted_result_id
        packet["result_ids"].append(stale_tail_result_id)

        review_packet_id = runtime._ensure_review_packet_for_task_result(ledger, packet_id, force_new=True)
        review_packet = ledger["packets"][review_packet_id]
        review_body = json.loads(review_packet["body"])

        self.assertEqual(review_packet["envelope"]["target_result_id"], accepted_result_id)
        self.assertEqual(review_body["target_result_id"], accepted_result_id)
        self.assertIn("Run targeted tests", review_body["instruction"])
        self.assertIn("review-scope tests or fixtures", review_body["instruction"])
        self.assertEqual(
            [row["result_id"] for row in review_packet["envelope"]["authorized_result_reads"]],
            [accepted_result_id],
        )

    def test_break_glass_counts_same_flowguard_root_cause_across_surface_gates(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        runtime.create_route(ledger, "Route", ["Do work"])
        root_cause_key = runtime._flowguard_missing_evidence_root_cause_key(
            subject_packet_id="packet-subject",
            target_result_id="result-subject",
            repair_blocker_id="",
        )
        for index in range(7):
            blocker_id = f"blocker-root-{index}"
            ledger["active_blockers"][blocker_id] = {
                "blocker_id": blocker_id,
                "status": "active",
                "gate_kind": "flowguard_review_handoff" if index % 2 == 0 else "system_validation",
                "blocker_class": "missing_matching_flowguard_report" if index % 2 == 0 else "system_validation_failure",
                "required_recheck_role": "flowguard_operator" if index % 2 == 0 else "system",
                "repair_target_packet_id": "packet-subject",
                "target_result_id": "result-subject",
                "root_cause_loop_key": root_cause_key,
            }

        review = runtime._repair_loop_break_glass_review(
            ledger,
            ledger["active_blockers"]["blocker-root-6"],
        )

        self.assertTrue(review["threshold_exceeded"])
        self.assertEqual(review["attempt_count"], 7)
        self.assertEqual(review["family_key"], root_cause_key)
        self.assertEqual(review["root_cause_loop_key"], root_cause_key)

    def test_break_glass_threshold_triggers_on_fifth_repair_blocker(self) -> None:
        root_cause_key = runtime._flowguard_missing_evidence_root_cause_key(
            subject_packet_id="packet-subject",
            target_result_id="result-subject",
            repair_blocker_id="",
        )

        for attempt_count, threshold_exceeded in ((4, False), (5, True), (6, True)):
            with self.subTest(attempt_count=attempt_count):
                ledger = runtime.new_ledger("Goal", "Contract")
                runtime.create_route(ledger, "Route", ["Do work"])
                for index in range(attempt_count):
                    blocker_id = f"blocker-root-{index}"
                    ledger["active_blockers"][blocker_id] = {
                        "blocker_id": blocker_id,
                        "status": "active",
                        "gate_kind": "flowguard_review_handoff",
                        "blocker_class": "missing_matching_flowguard_report",
                        "required_recheck_role": "flowguard_operator",
                        "repair_target_packet_id": "packet-subject",
                        "target_result_id": "result-subject",
                        "root_cause_loop_key": root_cause_key,
                    }

                review = runtime._repair_loop_break_glass_review(
                    ledger,
                    ledger["active_blockers"][f"blocker-root-{attempt_count - 1}"],
                )

                self.assertEqual(review["attempt_count"], attempt_count)
                self.assertEqual(review["threshold"], 5)
                self.assertEqual(review["threshold_exceeded"], threshold_exceeded)
                self.assertEqual(
                    review["required_action"],
                    "controller_break_glass_diagnosis" if threshold_exceeded else "ordinary_pm_repair_allowed",
                )

    def test_break_glass_counts_cleared_unclosed_same_root_blockers(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        runtime.create_route(ledger, "Route", ["Do work"])
        root_cause_key = "parent_backward_replay|node=parent-1|missing=active-child-lineage"
        for index in range(6):
            blocker_id = f"blocker-root-{index}"
            ledger["active_blockers"][blocker_id] = {
                "blocker_id": blocker_id,
                "status": "cleared" if index < 5 else "active",
                "cleared_by_outcome_id": f"outcome-{index}" if index < 5 else "",
                "gate_kind": "parent_backward_replay",
                "blocker_class": "composition_gap",
                "required_recheck_role": "reviewer",
                "route_node_id": "parent-1-repair-v5",
                "repair_target_packet_id": "packet-subject",
                "target_result_id": "result-subject",
                "root_cause_loop_key": root_cause_key,
            }

        review = runtime._repair_loop_break_glass_review(
            ledger,
            ledger["active_blockers"]["blocker-root-5"],
        )

        self.assertTrue(review["threshold_exceeded"])
        self.assertEqual(review["attempt_count"], 6)
        self.assertEqual(review["family_key"], root_cause_key)
        self.assertEqual(
            [row["cleared_by_outcome_id"] for row in review["same_family_blockers"][:5]],
            [f"outcome-{index}" for index in range(5)],
        )

    def test_break_glass_does_not_count_lineage_verified_closed_blockers(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        runtime.create_route(ledger, "Route", ["Do work"])
        root_cause_key = "parent_backward_replay|node=parent-1|missing=active-child-lineage"
        for index in range(6):
            blocker_id = f"blocker-root-{index}"
            ledger["active_blockers"][blocker_id] = {
                "blocker_id": blocker_id,
                "status": "cleared" if index < 5 else "active",
                "cleared_by_outcome_id": f"outcome-{index}" if index < 5 else "",
                "lineage_verified_closed_by": f"parent-replay-{index}" if index < 5 else "",
                "gate_kind": "parent_backward_replay",
                "blocker_class": "composition_gap",
                "required_recheck_role": "reviewer",
                "route_node_id": "parent-1-repair-v5",
                "repair_target_packet_id": "packet-subject",
                "target_result_id": "result-subject",
                "root_cause_loop_key": root_cause_key,
            }

        review = runtime._repair_loop_break_glass_review(
            ledger,
            ledger["active_blockers"]["blocker-root-5"],
        )

        self.assertFalse(review["threshold_exceeded"])
        self.assertEqual(review["attempt_count"], 1)

    def test_active_child_lineage_break_glass_cartesian_boundary(self) -> None:
        child_cases = {
            "active": ("child-active", False, "child-active"),
            "single_replacement": ("child-old", False, "child-repair-v2"),
            "replacement_chain": ("child-old", False, "child-repair-v3"),
            "missing_replacement": ("child-missing", True, ""),
            "cycle": ("cycle-a", True, ""),
        }
        blocker_history_cases = {
            "active": (lambda index, last: ("active", "", "")),
            "cleared_unclosed": (lambda index, last: ("active", "", "") if index == last else ("cleared", f"outcome-{index}", "")),
            "verified_closed": (
                lambda index, last: ("active", "", "")
                if index == last
                else ("cleared", f"outcome-{index}", f"parent-replay-{index}")
            ),
            "retired": (
                lambda index, last: ("active", "", "")
                if index == last
                else ("retired_after_new_current_blocker", "", "")
            ),
            "different_root": (lambda index, last: ("active", "", "")),
        }
        threshold_counts = {1, 4, 5, 6}

        for child_case, (start_child_id, child_errors, expected_active_child_id) in child_cases.items():
            for blocker_case, blocker_state in blocker_history_cases.items():
                for attempt_count in threshold_counts:
                    with self.subTest(child_case=child_case, blocker_case=blocker_case, attempt_count=attempt_count):
                        ledger = runtime.new_ledger("Goal", "Contract")
                        if child_case == "active":
                            ledger["route_nodes"] = {
                                "child-active": {"node_id": "child-active", "status": "accepted", "superseded_by": ""}
                            }
                        elif child_case == "single_replacement":
                            ledger["route_nodes"] = {
                                "child-old": {
                                    "node_id": "child-old",
                                    "status": "superseded",
                                    "superseded_by": "child-repair-v2",
                                },
                                "child-repair-v2": {
                                    "node_id": "child-repair-v2",
                                    "status": "accepted",
                                    "superseded_by": "",
                                },
                            }
                        elif child_case == "replacement_chain":
                            ledger["route_nodes"] = {
                                "child-old": {
                                    "node_id": "child-old",
                                    "status": "superseded",
                                    "superseded_by": "child-repair-v2",
                                },
                                "child-repair-v2": {
                                    "node_id": "child-repair-v2",
                                    "status": "superseded",
                                    "superseded_by": "child-repair-v3",
                                },
                                "child-repair-v3": {
                                    "node_id": "child-repair-v3",
                                    "status": "accepted",
                                    "superseded_by": "",
                                },
                            }
                        elif child_case == "missing_replacement":
                            ledger["route_nodes"] = {
                                "child-missing": {
                                    "node_id": "child-missing",
                                    "status": "superseded",
                                    "superseded_by": "missing-child",
                                }
                            }
                        else:
                            ledger["route_nodes"] = {
                                "cycle-a": {"node_id": "cycle-a", "status": "superseded", "superseded_by": "cycle-b"},
                                "cycle-b": {"node_id": "cycle-b", "status": "superseded", "superseded_by": "cycle-a"},
                            }

                        if child_errors:
                            with self.assertRaises(runtime.BlackBoxRuntimeError):
                                runtime._active_route_child_lineage(ledger, [start_child_id])
                        else:
                            active_ids, lineage = runtime._active_route_child_lineage(ledger, [start_child_id])
                            self.assertEqual(active_ids, [expected_active_child_id])
                            self.assertEqual(lineage[0]["active_child_node_id"], expected_active_child_id)

                        root_cause_key = "root-cause-active-child-lineage"
                        current_blocker_id = f"blocker-{attempt_count - 1}"
                        for index in range(attempt_count):
                            blocker_id = f"blocker-{index}"
                            status, cleared_by, verified_by = blocker_state(index, attempt_count - 1)
                            candidate_root = (
                                root_cause_key
                                if blocker_case != "different_root" or index == attempt_count - 1
                                else f"different-root-{index}"
                            )
                            ledger["active_blockers"][blocker_id] = {
                                "blocker_id": blocker_id,
                                "status": status,
                                "cleared_by_outcome_id": cleared_by,
                                "lineage_verified_closed_by": verified_by,
                                "gate_kind": "parent_backward_replay",
                                "blocker_class": "composition_gap",
                                "required_recheck_role": "reviewer",
                                "route_node_id": "parent-1-repair-v5",
                                "repair_target_packet_id": "packet-subject",
                                "target_result_id": "result-subject",
                                "root_cause_loop_key": candidate_root,
                            }

                        review = runtime._repair_loop_break_glass_review(
                            ledger,
                            ledger["active_blockers"][current_blocker_id],
                        )
                        expected_count = (
                            1
                            if blocker_case in {"verified_closed"}
                            else attempt_count
                        )
                        self.assertEqual(review["attempt_count"], expected_count)
                        self.assertEqual(review["threshold_exceeded"], expected_count >= 5)

    def test_result_submitted_repair_target_is_superseded_after_reissue(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        result_id = runtime.submit_result(ledger, worker, packet_id, role_result_body("Worker submitted a result for repair-target supersession."))
        self.assertEqual(ledger["packets"][packet_id]["status"], "result_submitted")

        blocker_id = "blocker-result-submitted"
        ledger["active_blockers"][blocker_id] = {
            "blocker_id": blocker_id,
            "status": "active",
            "outcome_id": "outcome-result-submitted",
            "packet_id": packet_id,
            "packet_kind": "task",
            "subject_packet_id": packet_id,
            "repair_target_packet_id": packet_id,
            "target_result_id": result_id,
            "result_id": result_id,
            "owner_role": "worker",
            "required_recheck_role": "worker",
            "gate_kind": "task",
            "blocker_class": "local_artifact",
            "recommended_resolution": "reissue current work",
            "route_version": ledger["active_route_version"],
            "route_node_id": "",
            "route_scope": "",
            "repair_generation": 0,
            "stale_evidence_ids": [result_id],
            "created_at": runtime.now_iso(),
            "pm_repair_packet_id": "",
            "pm_repair_decision_id": "",
            "cleared_by_outcome_id": "",
        }
        decision_id = "pm_repair_decision-result-submitted"
        ledger["pm_repair_decisions"][decision_id] = {
            "decision_id": decision_id,
            "blocker_id": blocker_id,
            "packet_id": "packet-decision",
            "result_id": "result-decision",
            "decision": "repair_current_scope",
            "reason": "Replace a submitted but unaccepted packet.",
            "created_at": runtime.now_iso(),
        }

        runtime._apply_pm_repair_decision(ledger, blocker_id, decision_id)

        self.assertEqual(ledger["packets"][packet_id]["status"], "superseded_after_repair")
        fresh_packet_id = ledger["repair_transactions"][decision_id]["fresh_packet_id"]
        self.assertEqual(ledger["packets"][fresh_packet_id]["status"], "open")
        self.assertEqual(ledger["active_blockers"][blocker_id]["status"], "repair_packet_open")

    def test_final_preflight_blocks_active_blocker_pointing_at_result_submitted_target(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        result_id = runtime.submit_result(ledger, worker, packet_id, role_result_body("Worker submitted a result for final preflight."))
        blocker_id = "blocker-stale-submitted"
        ledger["active_blockers"][blocker_id] = {
            "blocker_id": blocker_id,
            "status": "active",
            "outcome_id": "outcome-stale-submitted",
            "packet_id": packet_id,
            "packet_kind": "task",
            "subject_packet_id": packet_id,
            "repair_target_packet_id": packet_id,
            "target_result_id": result_id,
            "result_id": result_id,
            "owner_role": "worker",
            "required_recheck_role": "worker",
            "gate_kind": "task",
            "blocker_class": "local_artifact",
            "recommended_resolution": "repair",
            "route_version": ledger["active_route_version"],
            "route_node_id": "",
            "route_scope": "",
            "repair_generation": 0,
            "stale_evidence_ids": [result_id],
            "created_at": runtime.now_iso(),
            "pm_repair_packet_id": "",
            "pm_repair_decision_id": "",
            "cleared_by_outcome_id": "",
        }

        preflight = runtime.final_return_preflight(ledger)

        self.assertFalse(preflight["allowed"])
        self.assertTrue(
            any(
                blocker.startswith(f"active_blocker_result_submitted_target:{blocker_id}:")
                for blocker in preflight["blockers"]
            ),
            preflight["blockers"],
        )

    def test_final_preflight_does_not_block_on_repair_packet_open_history(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        result_id = runtime.submit_result(ledger, worker, packet_id, role_result_body("Worker submitted a result for repair history."))
        blocker_id = "blocker-repair-open"
        ledger["active_blockers"][blocker_id] = {
            "blocker_id": blocker_id,
            "status": "active",
            "outcome_id": "outcome-repair-open",
            "packet_id": packet_id,
            "packet_kind": "task",
            "subject_packet_id": packet_id,
            "repair_target_packet_id": packet_id,
            "target_result_id": result_id,
            "result_id": result_id,
            "owner_role": "worker",
            "required_recheck_role": "worker",
            "gate_kind": "task",
            "blocker_class": "local_artifact",
            "recommended_resolution": "repair",
            "route_version": ledger["active_route_version"],
            "route_node_id": "",
            "route_scope": "",
            "repair_generation": 0,
            "stale_evidence_ids": [result_id],
            "created_at": runtime.now_iso(),
            "pm_repair_packet_id": "",
            "pm_repair_decision_id": "",
            "cleared_by_outcome_id": "",
        }
        decision_id = "pm_repair_decision-repair-open"
        ledger["pm_repair_decisions"][decision_id] = {
            "decision_id": decision_id,
            "blocker_id": blocker_id,
            "packet_id": "packet-decision",
            "result_id": "result-decision",
            "decision": "repair_current_scope",
            "reason": "Open a fresh repair packet.",
            "created_at": runtime.now_iso(),
        }

        runtime._apply_pm_repair_decision(ledger, blocker_id, decision_id)
        preflight = runtime.final_return_preflight(ledger)

        self.assertFalse(preflight["allowed"])
        self.assertEqual(ledger["active_blockers"][blocker_id]["status"], "repair_packet_open")
        self.assertFalse(
            [
                blocker
                for blocker in preflight["blockers"]
                if blocker.startswith(f"active_blocker_current_target:{blocker_id}:")
                or blocker.startswith(f"active_blocker_result_submitted_target:{blocker_id}:")
            ],
            preflight["blockers"],
        )

    def test_final_preflight_ignores_accepted_noncurrent_repair_packet_open_blocker(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        result_id = runtime.submit_result(
            ledger,
            worker,
            packet_id,
            role_result_body("Worker submitted a result for accepted repair history."),
        )
        blocker_id = "blocker-accepted-repair-history"
        ledger["active_blockers"][blocker_id] = {
            "blocker_id": blocker_id,
            "status": "active",
            "outcome_id": "outcome-accepted-repair-history",
            "packet_id": packet_id,
            "packet_kind": "task",
            "subject_packet_id": packet_id,
            "repair_target_packet_id": packet_id,
            "target_result_id": result_id,
            "result_id": result_id,
            "owner_role": "worker",
            "required_recheck_role": "worker",
            "gate_kind": "task",
            "blocker_class": "local_artifact",
            "recommended_resolution": "repair",
            "route_version": ledger["active_route_version"],
            "route_node_id": "",
            "route_scope": "",
            "repair_generation": 0,
            "stale_evidence_ids": [result_id],
            "created_at": runtime.now_iso(),
            "pm_repair_packet_id": "",
            "pm_repair_decision_id": "",
            "cleared_by_outcome_id": "",
        }
        decision_id = "pm_repair_decision-accepted-repair-history"
        ledger["pm_repair_decisions"][decision_id] = {
            "decision_id": decision_id,
            "blocker_id": blocker_id,
            "packet_id": "packet-decision",
            "result_id": "result-decision",
            "decision": "repair_current_scope",
            "reason": "Open a fresh repair packet that later becomes accepted history.",
            "created_at": runtime.now_iso(),
        }

        runtime._apply_pm_repair_decision(ledger, blocker_id, decision_id)
        repair_packet_id = ledger["active_blockers"][blocker_id]["repair_packet_id"]
        ledger["packets"][repair_packet_id]["status"] = "accepted"
        preflight = runtime.final_return_preflight(ledger)
        compact = runtime.render_compact_console(ledger)

        self.assertFalse(runtime._blocker_current_effective(ledger, ledger["active_blockers"][blocker_id]))
        self.assertNotIn(blocker_id, {row["blocker_id"] for row in compact["active_blockers"]})
        self.assertFalse(
            [
                blocker
                for blocker in preflight["blockers"]
                if blocker.startswith(f"active_blocker_current_target:{blocker_id}:")
            ],
            preflight["blockers"],
        )

    def test_save_ledger_writes_valid_json_without_leftover_temp_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "run" / "ledger.json"
            ledger = runtime.new_ledger("Goal", "Acceptance")

            runtime.save_ledger(ledger, path)

            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["schema_version"], runtime.SCHEMA_VERSION)
            self.assertFalse(list(path.parent.glob(".ledger.json.tmp-*")))

    def test_load_ledger_retries_transient_incomplete_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            ledger = runtime.new_ledger("Goal", "Acceptance")
            valid = json.dumps(ledger)
            reads = iter(["", "{", valid])
            original_read_text = Path.read_text

            def flaky_read_text(self: Path, *args: object, **kwargs: object) -> str:
                if self == path:
                    return next(reads)
                return original_read_text(self, *args, **kwargs)

            with mock.patch.object(Path, "read_text", flaky_read_text), mock.patch.object(runtime.time, "sleep", lambda _: None):
                loaded = runtime.load_ledger(path)

            self.assertEqual(loaded["schema_version"], runtime.SCHEMA_VERSION)

    def test_load_ledger_persistent_invalid_json_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            path.write_text("{", encoding="utf-8")

            with mock.patch.object(runtime.time, "sleep", lambda _: None):
                with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "invalid runtime ledger JSON"):
                    runtime.load_ledger(path)

    def test_route_mutation_supersedes_repair_open_blocker_for_quarantined_packet(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Node one"])
        route_version = ledger["active_route_version"]
        ledger["route_nodes"]["node-1"] = {
            "node_id": "node-1",
            "route_version": route_version,
            "title": "Node One",
            "status": "running",
            "responsibility": "worker",
            "modeled_target": "development_process",
            "repair_generation": 0,
            "acceptance_criteria": ["criterion"],
            "child_node_ids": [],
        }
        packet_id = runtime.issue_task_packet(
            ledger,
            "worker",
            "Repair node work",
            "NODE_PACKET",
            route_node_id="node-1",
            route_scope="node",
            repair_blocker_id="blocker-old-repair",
        )
        blocker_id = "blocker-old-repair"
        ledger["active_blockers"][blocker_id] = {
            "blocker_id": blocker_id,
            "status": "repair_packet_open",
            "outcome_id": "outcome-old-repair",
            "packet_id": packet_id,
            "packet_kind": "task",
            "subject_packet_id": packet_id,
            "repair_target_packet_id": packet_id,
            "repair_packet_id": packet_id,
            "target_result_id": "",
            "result_id": "",
            "owner_role": "worker",
            "required_recheck_role": "worker",
            "gate_kind": "task",
            "blocker_class": "local_artifact",
            "recommended_resolution": "repair",
            "route_version": route_version,
            "route_node_id": "node-1",
            "route_scope": "node",
            "repair_generation": 0,
            "stale_evidence_ids": [],
            "created_at": runtime.now_iso(),
            "pm_repair_packet_id": "",
            "pm_repair_decision_id": "pm_repair_decision-new",
            "cleared_by_outcome_id": "",
        }
        ledger["packets"][packet_id]["active_blocker_id"] = blocker_id

        replacement_id = runtime._replace_route_node_for_repair(
            ledger,
            "node-1",
            disposition_id="pm_repair_decision-new",
            reason="Replace stale repair route.",
        )
        preflight = runtime.final_return_preflight(ledger)

        blocker = ledger["active_blockers"][blocker_id]
        mutation = ledger["route_mutations"][-1]
        self.assertEqual(ledger["packets"][packet_id]["status"], "quarantined_after_route_mutation")
        self.assertEqual(ledger["packets"][packet_id]["active_blocker_id"], "")
        self.assertEqual(blocker["status"], "superseded_by_route_mutation")
        self.assertEqual(blocker["superseded_repair_packet_id"], packet_id)
        self.assertEqual(blocker["superseded_by_route_mutation_id"], mutation["mutation_id"])
        self.assertEqual(blocker["superseded_by_route_mutation_disposition_id"], "pm_repair_decision-new")
        self.assertEqual(blocker["superseded_replacement_node_id"], replacement_id)
        self.assertFalse(
            [
                item
                for item in preflight["blockers"]
                if item.startswith(f"active_blocker_current_target:{blocker_id}:")
            ],
            preflight["blockers"],
        )

    def test_repair_current_scope_parent_replacement_carries_active_child_lineage(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Parent", "Child"])
        route_version = ledger["active_route_version"]
        parent_id = "parent-1"
        old_child_id = "child-1"
        active_child_id = "child-1-repair-v2"
        ledger["routes"][str(route_version)]["node_order"] = [parent_id, old_child_id, active_child_id]
        ledger["route_nodes"][parent_id] = {
            "node_id": parent_id,
            "route_version": route_version,
            "title": "Parent",
            "node_kind": "module",
            "status": "running",
            "responsibility": "worker",
            "modeled_target": "development_process",
            "repair_generation": 0,
            "acceptance_criteria": ["parent"],
            "child_node_ids": [old_child_id],
        }
        ledger["route_nodes"][old_child_id] = {
            "node_id": old_child_id,
            "route_version": route_version,
            "title": "Old Child",
            "node_kind": "leaf",
            "parent_node_id": parent_id,
            "status": "superseded",
            "accepted_result_id": "old-child-result",
            "superseded_by": active_child_id,
            "repair_generation": 0,
            "acceptance_criteria": ["old"],
            "child_node_ids": [],
        }
        ledger["route_nodes"][active_child_id] = {
            "node_id": active_child_id,
            "route_version": route_version,
            "title": "Active Child",
            "node_kind": "leaf",
            "parent_node_id": parent_id,
            "status": "accepted",
            "accepted_result_id": "active-child-result",
            "superseded_by": "",
            "repair_generation": 1,
            "acceptance_criteria": ["active"],
            "child_node_ids": [],
        }

        replacement_id = runtime._replace_route_node_for_repair(
            ledger,
            parent_id,
            disposition_id="pm-repair-active-child",
            reason="Replace parent without stale child refs.",
        )

        replacement = ledger["route_nodes"][replacement_id]
        self.assertEqual(replacement["child_node_ids"], [active_child_id])
        self.assertEqual(replacement["active_child_lineage"][0]["original_child_node_id"], old_child_id)
        self.assertEqual(replacement["active_child_lineage"][0]["active_child_node_id"], active_child_id)

    def test_route_mutation_supersedes_prior_route_repair_open_blockers(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Node one"])
        route_version = ledger["active_route_version"]
        ledger["route_nodes"]["node-1"] = {
            "node_id": "node-1",
            "route_version": route_version,
            "title": "Node One",
            "status": "running",
            "responsibility": "worker",
            "modeled_target": "development_process",
            "repair_generation": 0,
            "acceptance_criteria": ["criterion"],
            "child_node_ids": [],
        }
        packet_id = runtime.issue_task_packet(
            ledger,
            "worker",
            "Repair node work",
            "NODE_PACKET",
            route_node_id="node-1",
            route_scope="node",
            repair_blocker_id="blocker-current-repair",
        )
        old_same_family_packet_id = runtime.issue_task_packet(
            ledger,
            "worker",
            "Old accepted repair work",
            "OLD_SAME_FAMILY_PACKET",
            route_node_id="node-1",
            route_scope="node",
            repair_blocker_id="blocker-old-same-family",
        )
        old_unrelated_packet_id = runtime.issue_task_packet(
            ledger,
            "worker",
            "Old unrelated repair work",
            "OLD_UNRELATED_PACKET",
            route_node_id="node-1",
            route_scope="node",
            repair_blocker_id="blocker-old-unrelated",
        )
        ledger["packets"][old_same_family_packet_id]["status"] = "accepted"
        ledger["packets"][old_unrelated_packet_id]["status"] = "accepted"

        def repair_open_blocker(blocker_id: str, repair_packet_id: str, blocker_class: str) -> dict[str, object]:
            ledger["packets"][repair_packet_id]["active_blocker_id"] = blocker_id
            return {
                "blocker_id": blocker_id,
                "status": "repair_packet_open",
                "outcome_id": f"outcome-{blocker_id}",
                "packet_id": repair_packet_id,
                "packet_kind": "task",
                "subject_packet_id": repair_packet_id,
                "repair_target_packet_id": repair_packet_id,
                "repair_packet_id": repair_packet_id,
                "target_result_id": "",
                "result_id": "",
                "owner_role": "worker",
                "required_recheck_role": "worker",
                "gate_kind": "task",
                "blocker_class": blocker_class,
                "recommended_resolution": "repair",
                "route_version": route_version,
                "route_node_id": "node-1",
                "route_scope": "node",
                "repair_generation": 0,
                "stale_evidence_ids": [],
                "created_at": runtime.now_iso(),
                "pm_repair_packet_id": "",
                "pm_repair_decision_id": "pm_repair_decision-new",
                "cleared_by_outcome_id": "",
            }

        ledger["active_blockers"]["blocker-current-repair"] = repair_open_blocker(
            "blocker-current-repair",
            packet_id,
            "missing_required_information",
        )
        ledger["active_blockers"]["blocker-old-same-family"] = repair_open_blocker(
            "blocker-old-same-family",
            old_same_family_packet_id,
            "missing_required_information",
        )
        ledger["active_blockers"]["blocker-old-unrelated"] = repair_open_blocker(
            "blocker-old-unrelated",
            old_unrelated_packet_id,
            "different_family",
        )

        runtime._replace_route_node_for_repair(
            ledger,
            "node-1",
            disposition_id="pm_repair_decision-new",
            reason="Replace stale repair route.",
        )

        mutation = ledger["route_mutations"][-1]
        same_family_blocker = ledger["active_blockers"]["blocker-old-same-family"]
        unrelated_blocker = ledger["active_blockers"]["blocker-old-unrelated"]
        self.assertEqual(same_family_blocker["status"], "superseded_by_route_mutation")
        self.assertEqual(same_family_blocker["superseded_repair_packet_id"], old_same_family_packet_id)
        self.assertEqual(same_family_blocker["superseded_by_route_mutation_id"], mutation["mutation_id"])
        self.assertEqual(ledger["packets"][old_same_family_packet_id]["active_blocker_id"], "")
        self.assertEqual(unrelated_blocker["status"], "superseded_by_route_mutation")
        self.assertEqual(unrelated_blocker["superseded_repair_packet_id"], old_unrelated_packet_id)
        self.assertEqual(unrelated_blocker["superseded_by_route_mutation_id"], mutation["mutation_id"])
        self.assertEqual(ledger["packets"][old_unrelated_packet_id]["active_blocker_id"], "")

    def test_route_mutation_preserves_current_unproven_and_dispositioned_repair_open_blockers(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        ledger["active_blockers"] = {
            "blocker-stale": {
                "blocker_id": "blocker-stale",
                "status": "repair_packet_open",
                "repair_packet_id": "packet-stale",
                "route_version": 3,
            },
            "blocker-current": {
                "blocker_id": "blocker-current",
                "status": "repair_packet_open",
                "repair_packet_id": "packet-current",
                "route_version": 4,
            },
            "blocker-unproven": {
                "blocker_id": "blocker-unproven",
                "status": "repair_packet_open",
                "repair_packet_id": "packet-unproven",
                "route_version": "route-v3",
            },
            "blocker-already-history": {
                "blocker_id": "blocker-already-history",
                "status": "superseded_by_route_mutation",
                "repair_packet_id": "packet-history",
                "route_version": 3,
                "superseded_by_route_mutation_id": "mutation-old",
            },
        }

        runtime._supersede_repair_open_blockers_for_route_mutation(
            ledger,
            affected_packets=[],
            mutation_id="mutation-new",
            disposition_id="pm-decision-new",
            replacement_node_id="node-new",
            new_route_version=4,
        )

        self.assertEqual(ledger["active_blockers"]["blocker-stale"]["status"], "superseded_by_route_mutation")
        self.assertEqual(
            ledger["active_blockers"]["blocker-stale"]["superseded_by_route_mutation_id"],
            "mutation-new",
        )
        self.assertEqual(ledger["active_blockers"]["blocker-current"]["status"], "repair_packet_open")
        self.assertEqual(ledger["active_blockers"]["blocker-unproven"]["status"], "repair_packet_open")
        self.assertEqual(ledger["active_blockers"]["blocker-already-history"]["status"], "superseded_by_route_mutation")
        self.assertEqual(
            ledger["active_blockers"]["blocker-already-history"]["superseded_by_route_mutation_id"],
            "mutation-old",
        )

    def test_foreground_recovery_missing_packet_responsibility_hard_blocks(self) -> None:
        ledger = runtime.new_ledger("Goal", "Acceptance")
        runtime.create_route(ledger, "Route", ["Do work"])
        packet_id = runtime.issue_task_packet(ledger, "worker", "Do work", "SEALED_TASK_BODY")
        ledger["packets"][packet_id]["envelope"]["responsibility"] = ""
        guard = {
            "decision": "replace_lease",
            "next_action": {
                "action_type": "replace_lease",
                "subject_id": packet_id,
                "responsibility": "worker",
            },
            "wait_subject": {"packet_id": packet_id},
            "wait_recovery": {"lease_id": "lease-stale"},
        }

        command = runtime._foreground_recovery_command(ledger, guard)

        self.assertEqual(command["command"], "control-plane-blocker")
        self.assertEqual(command["packet_id"], packet_id)
        self.assertEqual(command["responsibility"], "")
        self.assertEqual(command["cli"], "")
        self.assertEqual(command["cleanup_action"], "hard_block_until_current_packet_responsibility_exists")

    def test_evidence_summary_finalizer_excludes_self_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.txt").write_text("A", encoding="utf-8")
            nested = root / "nested"
            nested.mkdir()
            (nested / "b.txt").write_text("B", encoding="utf-8")
            (root / "evidence_summary.md").write_text("summary", encoding="utf-8")
            (root / "evidence_summary.json").write_text("old", encoding="utf-8")

            manifest = runtime.finalize_evidence_summary_manifest(root)
            second_manifest = runtime.finalize_evidence_summary_manifest(root)

            paths = [item["path"] for item in manifest["evidence_files"]]
            self.assertEqual(paths, ["a.txt", "nested/b.txt"])
            self.assertEqual(second_manifest["evidence_files"], manifest["evidence_files"])
            self.assertEqual(json.loads((root / "evidence_summary.json").read_text(encoding="utf-8"))["file_count"], 2)

    def test_terminal_current_pointer_status_uses_final_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shell = run_shell.create_run_shell(root, "Goal", "Acceptance", run_id="run-terminal")
            ledger, packet_id, worker = runtime_runner._base_ledger()
            runtime_runner._complete_happy_path(ledger, packet_id, worker)

            run_shell.save_run_ledger(shell, ledger, guard_trigger="final_preflight")
            current = json.loads((root / ".flowpilot" / "current.json").read_text(encoding="utf-8"))

            self.assertEqual(current["lifecycle_state"], "terminal_complete")
            self.assertEqual(current["ledger_lifecycle_state"], "contract_frozen")
            self.assertTrue(current["final_return_allowed"])
            self.assertEqual(current["closure_decision"], "complete")

    def test_router_closes_only_after_backward_chain_and_validation(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime_runner._complete_happy_path(ledger, packet_id, worker)

        self.assertEqual(ledger["closure"]["decision"], "complete")
        self.assertEqual(runtime.router_next_action(ledger).action_type, "terminal_complete")
        chain = ledger["closure"]["backward_chain"]
        self.assertEqual([item["packet_kind"] for item in chain if item["kind"] == "packet"], [
            "task",
            "flowguard_check",
            "review",
        ])
        self.assertTrue(ledger["system_closures"])
        self.assertFalse([lease for lease in ledger["leases"].values() if lease["status"] == "active"])

    def test_runtime_testmesh_does_not_overclaim_release_evidence(self) -> None:
        report = runtime_runner.run_checks()
        self.assertTrue(report["ok"], report)
        self.assertTrue(report["test_mesh"]["parent_gates"]["routine_runtime_gate"]["ok"])
        self.assertFalse(report["test_mesh"]["parent_gates"]["release_runtime_gate"]["ok"])
        rows = {row["id"]: row for row in report["test_mesh"]["rows"]}
        self.assertEqual(rows["background_meta_capability"]["status"], "not_run")
        self.assertEqual(rows["install_surface_parity"]["status"], "not_run")

    def test_flowguard_development_model_accepts_order_and_rejects_hazards(self) -> None:
        report = development_runner.run_checks()
        self.assertTrue(report["ok"], report)
        self.assertTrue(report["flowguard"]["ok"])
        self.assertTrue(report["target_plan"]["ok"])
        self.assertTrue(report["hazard_detection"]["ok"])
        self.assertIn("fixed_role_topology_reintroduced", report["hazard_detection"]["hazards"])

    def test_flowguard_control_plane_duty_model_matches_runtime_repairs(self) -> None:
        report = control_plane_duty_runner.run_checks()
        self.assertTrue(report["ok"], report)
        self.assertTrue(report["flowguard"]["ok"])
        self.assertTrue(report["source_contract"]["ok"])
        self.assertIn("status_mutates_ledger", report["hazard_detection"]["hazards"])

    def test_current_run_resolver_accepts_new_schema_and_rejects_project_root_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / ".flowpilot" / "runs" / "run-new"
            run_root.mkdir(parents=True)
            ledger_path = run_root / "ledger.json"
            ledger_path.write_text("{}\n", encoding="utf-8")
            current_path = root / ".flowpilot" / "current.json"
            current_path.write_text(
                json.dumps(
                    {
                        "schema_version": "black_box_flowpilot_run_shell.v1",
                        "authority": "current_run_ledger",
                        "run_id": "run-new",
                        "run_root": str(run_root),
                        "ledger_path": str(ledger_path),
                    }
                ),
                encoding="utf-8",
            )

            resolution = control_surface.resolve_current_run(root)

            self.assertTrue(resolution.ok, resolution)
            self.assertEqual(resolution.run_id, "run-new")
            self.assertEqual(resolution.run_root, run_root.resolve())
            self.assertEqual(resolution.source_fields, ("run_id", "run_root"))

            current_path.write_text(
                json.dumps({"run_id": "run-new", "run_root": "."}),
                encoding="utf-8",
            )
            invalid = control_surface.resolve_current_run(root)

            self.assertFalse(invalid.ok)
            self.assertEqual(invalid.error_code, "invalid_run_root")

            current_path.write_text(
                json.dumps({"current_run_id": "run-new", "current_run_root": str(run_root)}),
                encoding="utf-8",
            )
            legacy = control_surface.resolve_current_run(root)

            self.assertFalse(legacy.ok)
            self.assertEqual(legacy.error_code, "unsupported_run_pointer_fields")

    def test_current_run_resolver_missing_pointer_returns_structured_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = control_surface.resolve_current_run(root)

            self.assertFalse(result.ok)
            self.assertEqual(result.error_code, "missing_file")
            finding = result.finding()
            self.assertEqual(finding["code"], "current_run_resolution_failed")
            self.assertIn("current.json", finding["evidence"]["pointer_path"])

    def test_corrupt_current_pointer_recovers_from_single_current_run_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shell = run_shell.create_run_shell(root, "Goal", "Acceptance", run_id="run-recover-current")
            current_path = root / ".flowpilot" / "current.json"
            current_path.write_bytes(b"\x00\x00\x00\x00")

            resolution = control_surface.resolve_current_run(root)

            self.assertTrue(resolution.ok, resolution)
            self.assertEqual(resolution.run_id, "run-recover-current")
            current = json.loads(current_path.read_text(encoding="utf-8"))
            self.assertEqual(current["run_id"], "run-recover-current")
            self.assertEqual(current["run_root"], str(shell.run_root.resolve()))
            self.assertLessEqual(
                set(current),
                {
                    "schema_version",
                    "run_id",
                    "run_root",
                    "ledger_path",
                    "authority",
                    "lifecycle_state",
                    "ledger_lifecycle_state",
                    "terminal_lifecycle_status",
                    "controller_stop_allowed",
                    "final_return_allowed",
                    "closure_decision",
                    "updated_at",
                },
            )
            backups = list((root / ".flowpilot").glob("current.json.corrupt-backup-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), b"\x00\x00\x00\x00")

    def test_corrupt_current_pointer_does_not_guess_between_multiple_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_shell.create_run_shell(root, "Goal A", "Acceptance", run_id="run-a")
            run_shell.create_run_shell(root, "Goal B", "Acceptance", run_id="run-b")
            current_path = root / ".flowpilot" / "current.json"
            current_path.write_bytes(b"\x00")

            resolution = control_surface.resolve_current_run(root)

            self.assertFalse(resolution.ok)
            self.assertEqual(resolution.error_code, "ambiguous_current_recovery")
            self.assertEqual(current_path.read_bytes(), b"\x00")

    def test_corrupt_index_pointer_rebuilds_without_new_pointer_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shell = run_shell.create_run_shell(root, "Goal", "Acceptance", run_id="run-recover-index")
            index_path = root / ".flowpilot" / "index.json"
            index_path.write_bytes(b"\x00\x00")
            ledger = run_shell.load_run_ledger(shell)
            ledger["lifecycle"] = {"state": "index_recovery_probe"}

            run_shell.save_run_ledger(shell, ledger, guard_trigger="index_recovery_probe")

            index = json.loads(index_path.read_text(encoding="utf-8"))
            self.assertEqual(index["schema_version"], "black_box_flowpilot_run_shell.v1")
            self.assertEqual([row["run_id"] for row in index["runs"]], ["run-recover-index"])
            self.assertLessEqual(
                set(index["runs"][0]),
                {
                    "schema_version",
                    "run_id",
                    "run_root",
                    "ledger_path",
                    "authority",
                    "lifecycle_state",
                    "ledger_lifecycle_state",
                    "terminal_lifecycle_status",
                    "controller_stop_allowed",
                    "final_return_allowed",
                    "closure_decision",
                    "updated_at",
                },
            )
            self.assertEqual(len(list((root / ".flowpilot").glob("index.json.corrupt-backup-*"))), 1)

    def test_pointer_recovery_respects_active_runtime_json_write_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_shell.create_run_shell(root, "Goal", "Acceptance", run_id="run-locked-current")
            current_path = root / ".flowpilot" / "current.json"
            current_path.write_bytes(b"\x00")
            lock_path = current_path.with_name("current.json.write.lock")
            lock_path.write_text(
                json.dumps(
                    {
                        "pid": 999999,
                        "target_initial_signature": {"exists": True, "mtime_ns": 0, "size": 1},
                    }
                ),
                encoding="utf-8",
            )

            result = pointer_store.recover_current_pointer(root)

            self.assertFalse(result.ok)
            self.assertEqual(result.error_code, "pointer_write_in_progress")
            self.assertEqual(current_path.read_bytes(), b"\x00")

    def test_safe_json_read_and_live_audit_report_invalid_utf8_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad_utf8 = root / "bad.json"
            bad_utf8.write_bytes(b"\xff\xfe")
            bad_json = root / "bad-syntax.json"
            bad_json.write_text("{", encoding="utf-8")

            utf8_result = control_surface.safe_read_json(bad_utf8)
            json_result = control_surface.safe_read_json(bad_json)

            self.assertFalse(utf8_result.ok)
            self.assertEqual(utf8_result.error_code, "invalid_utf8")
            self.assertFalse(json_result.ok)
            self.assertEqual(json_result.error_code, "invalid_json")

            run_root = root / ".flowpilot" / "runs" / "run-bad"
            run_root.mkdir(parents=True)
            (root / ".flowpilot" / "current.json").write_text(
                json.dumps({"run_id": "run-bad", "run_root": str(run_root)}),
                encoding="utf-8",
            )
            (run_root / "router_state.json").write_bytes(b"\xff\xfe")
            (run_root / "ledger.json").write_text(
                json.dumps(runtime.new_ledger("Goal", "Contract")),
                encoding="utf-8",
            )

            audit = control_plane_audit.audit_live_run(root)

            self.assertFalse(audit["ok"])
            codes = {finding["code"] for finding in audit["findings"]}
            self.assertIn("control_surface_evidence_unreadable", codes)

    def test_packet_control_surface_contracts_are_role_symmetric(self) -> None:
        required_roles = {
            "pm",
            "worker",
            "flowguard_operator",
            "reviewer",
        }
        ledger = runtime.new_ledger("Goal", "Contract")
        runtime.create_route(ledger, "Route", ["Do work"])
        for role in sorted(required_roles):
            packet_id = runtime.issue_task_packet(
                ledger,
                role,
                f"{role} objective",
                json.dumps({"role": role}),
                packet_kind="flowguard_check" if role == "flowguard_operator" else "task",
            )
            envelope = ledger["packets"][packet_id]["envelope"]
            self.assertEqual(envelope["output_contract"]["recipient_responsibility"], role)

        findings = control_surface.audit_packet_contracts(
            ledger,
            required_responsibilities=required_roles,
        )

        self.assertEqual(findings, [])

        bad_ledger = json.loads(json.dumps(ledger))
        reviewer_packet = next(
            packet
            for packet in bad_ledger["packets"].values()
            if packet["envelope"]["responsibility"] == "reviewer"
        )
        reviewer_packet["envelope"].pop("output_contract")
        bad_findings = control_surface.audit_packet_contracts(
            bad_ledger,
            required_responsibilities=required_roles,
        )

        self.assertIn("packet_contract_fields_missing", {finding["code"] for finding in bad_findings})

    def test_packet_result_contract_separates_ack_result_and_acceptance(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Do work"])
        packet_id = runtime.issue_task_packet(ledger, "worker", "Do work", "body")
        lease_id = runtime.lease_agent(ledger, "worker", agent_id="worker-1", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)
        self.assertEqual(ledger["packets"][packet_id]["status"], "acknowledged")

        result_id = runtime.submit_result(ledger, lease_id, packet_id, role_result_body("Worker result keeps ack/result/acceptance separate."))

        packet = ledger["packets"][packet_id]
        result = ledger["results"][result_id]
        self.assertEqual(packet["status"], "result_submitted")
        self.assertEqual(packet["accepted_result_id"], "")
        self.assertTrue(result["envelope"]["ack_result_accepted_separate"])
        self.assertEqual(result["envelope"]["output_contract"]["packet_id"], packet_id)
        flowguard_packets = [
            packet
            for packet in ledger["packets"].values()
            if packet["envelope"]["packet_kind"] == "flowguard_check"
            and packet["envelope"]["subject_id"] == packet_id
        ]
        self.assertEqual(len(flowguard_packets), 1)
        self.assertEqual(runtime.router_next_action(ledger).subject_id, flowguard_packets[0]["packet_id"])
        self.assertEqual(control_surface.audit_packet_contracts(ledger), [])

    def test_missing_pm_visible_summary_is_mechanically_reissued(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Do work"])
        packet_id = runtime.issue_task_packet(ledger, "worker", "Do work", "body")
        lease_id = runtime.lease_agent(ledger, "worker", agent_id="worker-1", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)

        result_id = runtime.submit_result(ledger, lease_id, packet_id, json.dumps({"decision": "pass"}))

        result = ledger["results"][result_id]
        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertIn("pm_visible_summary", result["quarantine_reason"])
        self.assertEqual(ledger["packets"][packet_id]["status"], "superseded_after_repair")
        reissues = [
            packet
            for packet in ledger["packets"].values()
            if packet["packet_id"] != packet_id
            and packet["envelope"]["packet_kind"] == "task"
            and packet["envelope"]["responsibility"] == "worker"
            and packet["status"] == "open"
        ]
        self.assertEqual(len(reissues), 1)
        reissue_body = json.loads(reissues[0]["body"])
        self.assertIn("pm_visible_summary", reissue_body["required_result_body_fields"])
        self.assertFalse(ledger["active_blockers"])

    def test_flowguard_packet_rejects_generic_decision_summary_result(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(ledger, worker, packet_id, role_result_body("Worker submitted current runtime evidence."))
        flowguard_packet = runtime_runner._open_packet_by_kind(ledger, "flowguard_check")
        flowguard_lease = runtime.lease_agent(
            ledger,
            "flowguard_operator",
            agent_id="fg-generic",
            packet_id=flowguard_packet,
        )
        runtime.assign_packet(ledger, flowguard_packet, flowguard_lease)
        runtime.ack_lease(ledger, flowguard_lease, flowguard_packet)
        open_required_result_reads(ledger, flowguard_packet, flowguard_lease)

        result_id = runtime.submit_result(
            ledger,
            flowguard_lease,
            flowguard_packet,
            role_result_body("Old generic FlowGuard shape must not pass."),
        )
        result = ledger["results"][result_id]

        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertEqual(result["contract_family_id"], "flowguard_check.post_result")
        self.assertIn("passed", result["missing_required_fields"])
        self.assertIn("decision", result["forbidden_fields_seen"])

    def test_flowguard_packet_rejects_deleted_commands_run_field(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(ledger, worker, packet_id, role_result_body("Worker submitted current runtime evidence."))
        flowguard_packet = runtime_runner._open_packet_by_kind(ledger, "flowguard_check")
        flowguard_lease = runtime.lease_agent(
            ledger,
            "flowguard_operator",
            agent_id="fg-empty-array",
            packet_id=flowguard_packet,
        )
        runtime.assign_packet(ledger, flowguard_packet, flowguard_lease)
        runtime.ack_lease(ledger, flowguard_lease, flowguard_packet)
        open_required_result_reads(ledger, flowguard_packet, flowguard_lease)

        result_id = runtime.submit_result(
            ledger,
            flowguard_lease,
            flowguard_packet,
            flowguard_result_body("FlowGuard report uses deleted commands_run field.", commands_run=[]),
        )
        result = ledger["results"][result_id]

        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertEqual(result["contract_family_id"], "flowguard_check.post_result")
        self.assertIn("commands_run", result["forbidden_fields_seen"])

    def test_flowguard_packet_rejects_missing_evidence_output_policy(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(ledger, worker, packet_id, role_result_body("Worker submitted current runtime evidence."))
        flowguard_packet = runtime_runner._open_packet_by_kind(ledger, "flowguard_check")
        packet_body = json.loads(ledger["packets"][flowguard_packet]["body"])
        packet_body.pop("evidence_output_policy")
        ledger["packets"][flowguard_packet]["body"] = json.dumps(packet_body)
        flowguard_lease = runtime.lease_agent(
            ledger,
            "flowguard_operator",
            agent_id="fg-missing-policy",
            packet_id=flowguard_packet,
        )
        runtime.assign_packet(ledger, flowguard_packet, flowguard_lease)
        runtime.ack_lease(ledger, flowguard_lease, flowguard_packet)
        open_required_result_reads(ledger, flowguard_packet, flowguard_lease)

        result_id = runtime.submit_result(
            ledger,
            flowguard_lease,
            flowguard_packet,
            flowguard_result_body("FlowGuard body cannot replace packet-owned evidence policy."),
        )
        result = ledger["results"][result_id]

        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertEqual(result["contract_family_id"], "flowguard_check.post_result")
        self.assertIn("evidence_output_policy", result["missing_required_fields"])

    def test_flowguard_artifact_path_uses_packet_policy_before_derived_run_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            ledger, packet_id, worker = runtime_runner._base_ledger()
            ledger["run_root"] = temp_root
            runtime.ack_lease(ledger, worker, packet_id)
            runtime.submit_result(ledger, worker, packet_id, role_result_body("Worker submitted current runtime evidence."))
            flowguard_packet = runtime_runner._open_packet_by_kind(ledger, "flowguard_check")
            declared_root = Path(temp_root) / "declared-flowguard-evidence" / flowguard_packet
            packet = ledger["packets"][flowguard_packet]
            packet_body = json.loads(packet["body"])
            packet_body["evidence_output_policy"]["run_local_evidence_root"] = str(declared_root)
            packet["body"] = json.dumps(packet_body, sort_keys=True)
            packet["envelope"]["body_hash"] = runtime.hash_text(packet["body"])
            derived_path = Path(temp_root) / "evidence" / "flowguard" / flowguard_packet / "flowguard_evidence.json"
            derived_path.parent.mkdir(parents=True, exist_ok=True)
            derived_path.write_text(
                json.dumps(
                    {
                        "schema_version": "flowpilot.flowguard_evidence.v1",
                        "model_test_alignment_report": {
                            "decision": "pass",
                            "failed_predicates": [],
                        },
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                runtime._flowguard_packet_evidence_artifact_path(ledger, packet),
                declared_root / "flowguard_evidence.json",
            )

            flowguard_lease = runtime.lease_agent(
                ledger,
                "flowguard_operator",
                agent_id="fg-policy-path-authority",
                packet_id=flowguard_packet,
            )
            runtime.assign_packet(ledger, flowguard_packet, flowguard_lease)
            runtime.ack_lease(ledger, flowguard_lease, flowguard_packet)
            open_required_result_reads(ledger, flowguard_packet, flowguard_lease)

            result_id = runtime.submit_result(
                ledger,
                flowguard_lease,
                flowguard_packet,
                flowguard_result_body("FlowGuard body cannot pass by using a derived artifact path."),
            )
            result = ledger["results"][result_id]

            self.assertEqual(result["status"], "mechanical_contract_blocked")
            self.assertEqual(result["contract_family_id"], "flowguard_check.post_result")
            self.assertIn("flowguard_evidence.json", result["missing_required_fields"])

    def test_flowguard_packet_rejects_failed_contract_self_check_without_reviewer(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(ledger, worker, packet_id, role_result_body("Worker submitted current runtime evidence."))
        flowguard_packet = runtime_runner._open_packet_by_kind(ledger, "flowguard_check")
        flowguard_lease = runtime.lease_agent(
            ledger,
            "flowguard_operator",
            agent_id="fg-self-check-failed",
            packet_id=flowguard_packet,
        )
        runtime.assign_packet(ledger, flowguard_packet, flowguard_lease)
        runtime.ack_lease(ledger, flowguard_lease, flowguard_packet)
        open_required_result_reads(ledger, flowguard_packet, flowguard_lease)
        body = json.loads(flowguard_result_body("FlowGuard report contradicts its self-check."))
        body["contract_self_check"]["all_required_fields_present"] = False

        result_id = runtime.submit_result(ledger, flowguard_lease, flowguard_packet, json.dumps(body))
        result = ledger["results"][result_id]

        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertEqual(result["contract_family_id"], "flowguard_check.post_result")
        self.assertIn("contract_self_check.all_required_fields_present", result["missing_required_fields"])
        self.assertFalse(
            [
                packet
                for packet in ledger["packets"].values()
                if packet["envelope"]["packet_kind"] == "review"
            ]
        )
        self.assertFalse(
            [
                order
                for order in ledger.get("flowguard_work_orders", {}).values()
                if order.get("decision") == "pass"
            ]
        )

    def test_flowguard_packet_rejects_deleted_evidence_consistency_field_without_reviewer(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(ledger, worker, packet_id, role_result_body("Worker submitted current runtime evidence."))
        flowguard_packet = runtime_runner._open_packet_by_kind(ledger, "flowguard_check")
        flowguard_lease = runtime.lease_agent(
            ledger,
            "flowguard_operator",
            agent_id="fg-child-blocked",
            packet_id=flowguard_packet,
        )
        runtime.assign_packet(ledger, flowguard_packet, flowguard_lease)
        runtime.ack_lease(ledger, flowguard_lease, flowguard_packet)
        open_required_result_reads(ledger, flowguard_packet, flowguard_lease)
        body = json.loads(flowguard_result_body("FlowGuard report has blocked child evidence."))
        body["evidence_consistency"] = {
            "self_check_passed": True,
            "child_reports_all_passed": False,
            "blocking_child_reports": [
                {
                    "report_path": "evidence/flowguard/packet-0071/model_test_alignment_report.json",
                    "decision": "missing_code_contract",
                }
            ],
            "hard_evidence_decision": "missing_code_contract",
        }

        result_id = runtime.submit_result(ledger, flowguard_lease, flowguard_packet, json.dumps(body))
        result = ledger["results"][result_id]

        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertEqual(result["contract_family_id"], "flowguard_check.post_result")
        self.assertIn("evidence_consistency", result["forbidden_fields_seen"])
        self.assertFalse(
            [
                packet
                for packet in ledger["packets"].values()
                if packet["envelope"]["packet_kind"] == "review"
            ]
        )
        self.assertFalse(
            [
                order
                for order in ledger.get("flowguard_work_orders", {}).values()
                if order.get("decision") == "pass"
            ]
        )

    def test_flowguard_parent_repair_requires_subject_artifact_consumption(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(ledger, worker, packet_id, role_result_body("Worker submitted current runtime evidence."))
        flowguard_packet = runtime_runner._open_packet_by_kind(ledger, "flowguard_check")
        packet = ledger["packets"][flowguard_packet]
        envelope = packet["envelope"]
        envelope["result_contract_profile_ids"] = ["flowguard.subject_artifacts_consumed_required"]
        envelope["result_contract_profile_bindings"] = {
            "flowguard.subject_artifacts_consumed_required": {
                "artifact_ids": ["parent_repair_scope_contract:parent-repair-contract-001"],
            }
        }
        handoff_contract = runtime._build_current_handoff_contract(
            ledger,
            envelope,
            runtime._packet_authorized_result_reads(packet),
        )
        envelope["current_handoff_contract"] = handoff_contract
        packet["body"] = runtime._packet_body_with_current_handoff_contract(
            str(packet.get("body", "")),
            handoff_contract,
            replace_existing=True,
        )
        envelope["body_hash"] = runtime.hash_text(packet["body"])
        flowguard_lease = runtime.lease_agent(
            ledger,
            "flowguard_operator",
            agent_id="fg-format-only-parent-repair",
            packet_id=flowguard_packet,
        )
        runtime.assign_packet(ledger, flowguard_packet, flowguard_lease)
        runtime.ack_lease(ledger, flowguard_lease, flowguard_packet)
        open_required_result_reads(ledger, flowguard_packet, flowguard_lease)

        result_id = runtime.submit_result(
            ledger,
            flowguard_lease,
            flowguard_packet,
            flowguard_result_body("FlowGuard report only checked shape."),
        )
        result = ledger["results"][result_id]

        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertEqual(result["contract_family_id"], "flowguard_check.post_result")
        self.assertIn("subject_artifacts_consumed", result["missing_required_fields"])

    def test_flowguard_packet_rejects_artifact_missing_code_contract_without_reviewer(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            ledger, packet_id, worker = runtime_runner._base_ledger()
            ledger["run_root"] = temp_root
            runtime.ack_lease(ledger, worker, packet_id)
            runtime.submit_result(ledger, worker, packet_id, role_result_body("Worker submitted current runtime evidence."))
            flowguard_packet = runtime_runner._open_packet_by_kind(ledger, "flowguard_check")
            write_flowguard_evidence_artifact(ledger, flowguard_packet, decision="missing_code_contract")
            flowguard_lease = runtime.lease_agent(
                ledger,
                "flowguard_operator",
                agent_id="fg-artifact-blocked",
                packet_id=flowguard_packet,
            )
            runtime.assign_packet(ledger, flowguard_packet, flowguard_lease)
            runtime.ack_lease(ledger, flowguard_lease, flowguard_packet)
            open_required_result_reads(ledger, flowguard_packet, flowguard_lease)

            result_id = runtime.submit_result(
                ledger,
                flowguard_lease,
                flowguard_packet,
                flowguard_result_body("FlowGuard body claims pass while artifact blocks."),
            )
            result = ledger["results"][result_id]

            self.assertEqual(result["status"], "mechanical_contract_blocked")
            self.assertEqual(result["contract_family_id"], "flowguard_check.post_result")
            self.assertIn(
                "flowguard_evidence.json.model_test_alignment_report.decision",
                result["missing_required_fields"],
            )
            self.assertFalse(
                [
                    order
                    for order in ledger.get("flowguard_work_orders", {}).values()
                    if order.get("decision") == "pass"
                ]
            )
            self.assertFalse(
                [
                    packet
                    for packet in ledger["packets"].values()
                    if packet["envelope"]["packet_kind"] == "review"
                ]
            )

    def test_repair_task_flowguard_packet_inherits_blocker_identity(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        blocker_id = "blocker-auto-flowguard"
        ledger["active_blockers"][blocker_id] = {
            "blocker_id": blocker_id,
            "status": "active",
            "reason": "Reviewer requires subject-bound FlowGuard evidence.",
            "blocker_class": "local_artifact",
            "gate_kind": "review",
            "required_recheck_role": "reviewer",
        }
        runtime._bind_packet_repair_blocker_identity(ledger, packet_id, blocker_id)

        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(ledger, worker, packet_id, role_result_body("Worker submitted repaired evidence."))

        flowguard_packet = runtime_runner._open_packet_by_kind(ledger, "flowguard_check")
        flowguard = ledger["packets"][flowguard_packet]
        flowguard_body = json.loads(flowguard["body"])
        self.assertEqual(flowguard["repair_blocker_id"], blocker_id)
        self.assertEqual(flowguard["envelope"]["repair_blocker_id"], blocker_id)
        self.assertEqual(flowguard_body["recheck_for_blocker_id"], blocker_id)
        self.assertEqual(flowguard_body["semantic_recheck_contract"]["blocker_id"], blocker_id)
        self.assertTrue(flowguard_body["semantic_recheck_contract"]["subject_bound_required"])

    def test_explicit_flowguard_action_inherits_repair_blocker_identity(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        blocker_id = "blocker-explicit-flowguard"
        runtime._bind_packet_repair_blocker_identity(ledger, packet_id, blocker_id)
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(ledger, worker, packet_id, role_result_body("Worker submitted repaired evidence."))

        action_result = runtime._apply_router_internal_action(
            ledger,
            runtime.RuntimeAction(
                "issue_flowguard_packet",
                "explicit recheck",
                packet_id,
                "flowguard_operator",
            ),
        )

        explicit_packet_id = action_result["packet_id"]
        explicit_packet = ledger["packets"][explicit_packet_id]
        explicit_body = json.loads(explicit_packet["body"])
        self.assertEqual(explicit_packet["repair_blocker_id"], blocker_id)
        self.assertEqual(explicit_packet["envelope"]["repair_blocker_id"], blocker_id)
        self.assertEqual(explicit_body["recheck_for_blocker_id"], blocker_id)
        self.assertEqual(explicit_body["semantic_recheck_contract"]["blocker_id"], blocker_id)

    def test_semantic_recheck_rejects_shape_only_flowguard_pass(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        blocker_id = "blocker-shape-only"
        runtime._bind_packet_repair_blocker_identity(ledger, packet_id, blocker_id)
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(ledger, worker, packet_id, role_result_body("Worker submitted repaired evidence."))
        flowguard_packet = runtime_runner._open_packet_by_kind(ledger, "flowguard_check")
        flowguard_lease = runtime.lease_agent(
            ledger,
            "flowguard_operator",
            agent_id="fg-shape-only",
            packet_id=flowguard_packet,
        )
        runtime.assign_packet(ledger, flowguard_packet, flowguard_lease)
        runtime.ack_lease(ledger, flowguard_lease, flowguard_packet)
        open_required_result_reads(ledger, flowguard_packet, flowguard_lease)
        body = json.loads(flowguard_result_body("FlowGuard checked only packet shape."))
        body["semantic_recheck"] = {
            "blocker_id": blocker_id,
            "subject_result_consumed": True,
            "subject_bound_semantic_coverage": True,
            "coverage_boundary": "current_contract_only",
            "consumed_authorized_result_read_ids": [
                str(row.get("result_id") or "")
                for row in ledger["packets"][flowguard_packet]["envelope"].get("authorized_result_reads", [])
                if row.get("required_before_submit") is True and str(row.get("result_id") or "")
            ],
            "consumed_repair_obligation_ids": [],
        }

        result_id = runtime.submit_result(ledger, flowguard_lease, flowguard_packet, json.dumps(body))
        result = ledger["results"][result_id]

        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertIn("semantic_recheck.coverage_boundary", result["missing_required_fields"])
        self.assertFalse(
            [
                order
                for order in ledger.get("flowguard_work_orders", {}).values()
                if order.get("decision") == "pass"
            ]
        )

    def test_semantic_recheck_subject_bound_flowguard_pass_reaches_reviewer(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            ledger, packet_id, worker = runtime_runner._base_ledger()
            ledger["run_root"] = temp_root
            blocker_id = "blocker-subject-bound"
            runtime._bind_packet_repair_blocker_identity(ledger, packet_id, blocker_id)
            runtime.ack_lease(ledger, worker, packet_id)
            runtime.submit_result(ledger, worker, packet_id, role_result_body("Worker submitted repaired evidence."))
            flowguard_packet = runtime_runner._open_packet_by_kind(ledger, "flowguard_check")
            write_flowguard_evidence_artifact(ledger, flowguard_packet, decision="pass")
            flowguard_lease = runtime.lease_agent(
                ledger,
                "flowguard_operator",
                agent_id="fg-subject-bound",
                packet_id=flowguard_packet,
            )
            runtime.assign_packet(ledger, flowguard_packet, flowguard_lease)
            runtime.ack_lease(ledger, flowguard_lease, flowguard_packet)
            open_required_result_reads(ledger, flowguard_packet, flowguard_lease)
            result_id = runtime.submit_result(
                ledger,
                flowguard_lease,
                flowguard_packet,
                flowguard_result_body(
                    "FlowGuard consumed subject result and passed.",
                    **semantic_recheck_fields_from_packet(ledger, flowguard_packet, blocker_id),
                ),
            )

            review_packets = [
                packet
                for packet in ledger["packets"].values()
                if packet["envelope"]["packet_kind"] == "review"
            ]
            self.assertEqual(ledger["results"][result_id]["status"], "accepted")
            self.assertEqual(len(review_packets), 1)
            flowguard_orders = list(ledger.get("flowguard_work_orders", {}).values())
            self.assertTrue(flowguard_orders)
            self.assertEqual(flowguard_orders[-1]["decision"], "pass")
            self.assertEqual(flowguard_orders[-1]["hard_evidence_decision"], "pass")

    def test_flowguard_packet_block_with_compact_blocker_does_not_issue_reviewer(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(ledger, worker, packet_id, role_result_body("Worker submitted current runtime evidence."))
        flowguard_packet = runtime_runner._open_packet_by_kind(ledger, "flowguard_check")
        flowguard_lease = runtime.lease_agent(
            ledger,
            "flowguard_operator",
            agent_id="fg-current-block",
            packet_id=flowguard_packet,
        )
        runtime.assign_packet(ledger, flowguard_packet, flowguard_lease)
        runtime.ack_lease(ledger, flowguard_lease, flowguard_packet)
        open_required_result_reads(ledger, flowguard_packet, flowguard_lease)
        write_flowguard_evidence_artifact(ledger, flowguard_packet, decision="blocked")
        body = json.loads(flowguard_result_body("FlowGuard blocks on current hard evidence."))
        body["passed"] = False
        body["blockers"] = [
            {
                "blocker_id": "flowguard-block-current",
                "blocker_class": "flowguard_failure",
                "next_action": "pm_flowguard_acceptance",
                "recommended_resolution": "PM must absorb the current FlowGuard blocker.",
            }
        ]

        result_id = runtime.submit_result(ledger, flowguard_lease, flowguard_packet, json.dumps(body))
        result = ledger["results"][result_id]

        self.assertEqual(result["status"], "flowguard_blocked")
        self.assertFalse(result["accepted"])
        self.assertFalse(
            [
                packet
                for packet in ledger["packets"].values()
                if packet["envelope"]["packet_kind"] == "review"
            ]
        )

    def test_review_packet_rejects_generic_decision_summary_result(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(ledger, worker, packet_id, role_result_body("Worker submitted current runtime evidence."))
        flowguard_packet = runtime_runner._open_packet_by_kind(ledger, "flowguard_check")
        flowguard_lease = runtime.lease_agent(
            ledger,
            "flowguard_operator",
            agent_id="fg-current",
            packet_id=flowguard_packet,
        )
        runtime.assign_packet(ledger, flowguard_packet, flowguard_lease)
        runtime.ack_lease(ledger, flowguard_lease, flowguard_packet)
        open_required_result_reads(ledger, flowguard_packet, flowguard_lease)
        write_flowguard_evidence_artifact(ledger, flowguard_packet)
        runtime.submit_result(
            ledger,
            flowguard_lease,
            flowguard_packet,
            flowguard_result_body("FlowGuard evidence passed."),
        )
        review_packet = runtime_runner._open_packet_by_kind(ledger, "review")
        review_lease = runtime.lease_agent(ledger, "reviewer", agent_id="reviewer-generic", packet_id=review_packet)
        runtime.assign_packet(ledger, review_packet, review_lease)
        runtime.ack_lease(ledger, review_lease, review_packet)
        open_required_result_reads(ledger, review_packet, review_lease)

        result_id = runtime.submit_result(
            ledger,
            review_lease,
            review_packet,
            role_result_body("Old generic Reviewer shape must not pass."),
        )
        result = ledger["results"][result_id]

        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertEqual(result["contract_family_id"], "review.any_current_subject")
        self.assertIn("passed", result["missing_required_fields"])
        self.assertIn("contract_self_check", result["missing_required_fields"])
        self.assertIn("decision", result["forbidden_fields_seen"])

    def test_review_packet_rejects_deleted_independent_challenge_field(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(ledger, worker, packet_id, role_result_body("Worker submitted current runtime evidence."))
        flowguard_packet = runtime_runner._open_packet_by_kind(ledger, "flowguard_check")
        flowguard_lease = runtime.lease_agent(
            ledger,
            "flowguard_operator",
            agent_id="fg-current-review-empty",
            packet_id=flowguard_packet,
        )
        runtime.assign_packet(ledger, flowguard_packet, flowguard_lease)
        runtime.ack_lease(ledger, flowguard_lease, flowguard_packet)
        open_required_result_reads(ledger, flowguard_packet, flowguard_lease)
        write_flowguard_evidence_artifact(ledger, flowguard_packet)
        runtime.submit_result(
            ledger,
            flowguard_lease,
            flowguard_packet,
            flowguard_result_body("FlowGuard evidence passed."),
        )
        review_packet = runtime_runner._open_packet_by_kind(ledger, "review")
        review_lease = runtime.lease_agent(ledger, "reviewer", agent_id="reviewer-empty", packet_id=review_packet)
        runtime.assign_packet(ledger, review_packet, review_lease)
        runtime.ack_lease(ledger, review_lease, review_packet)
        open_required_result_reads(ledger, review_packet, review_lease)
        body = json.loads(review_result_body("Reviewer used deleted challenge object."))
        body["independent_challenge"] = {
            "challenge_actions": [],
            "blocking_findings": [],
        }

        result_id = runtime.submit_result(ledger, review_lease, review_packet, json.dumps(body))
        result = ledger["results"][result_id]

        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertEqual(result["contract_family_id"], "review.any_current_subject")
        self.assertIn("independent_challenge", result["forbidden_fields_seen"])

    def test_pm_repair_packet_includes_recent_role_report_summary(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)

        runtime.submit_result(
            ledger,
            worker,
            packet_id,
            role_result_body(
                "Worker found the stale lifecycle path and cannot complete until PM repairs it.",
                decision="block",
                blocking=True,
                recommended_resolution="Replace stale lifecycle path.",
            ),
        )

        blocker_id = next(iter(ledger["active_blockers"]))
        pm_packet = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
        body = json.loads(ledger["packets"][pm_packet]["body"])
        summaries = body["recent_role_report_summary"]
        self.assertEqual(summaries[0]["role"], "worker")
        self.assertEqual(summaries[0]["packet_id"], packet_id)
        self.assertEqual(
            summaries[0]["summary"],
            ["Worker found the stale lifecycle path and cannot complete until PM repairs it."],
        )

    def test_pm_repair_decision_receives_authorized_block_report_with_packet_open(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        blocking_result_id = runtime.submit_result(
            ledger,
            worker,
            packet_id,
            role_result_body(
                "Worker found the stale lifecycle path and cannot complete until PM repairs it.",
                decision="block",
                blocking=True,
                recommended_resolution="Replace stale lifecycle path.",
            ),
        )

        blocker_id = next(iter(ledger["active_blockers"]))
        pm_packet = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
        pm_body = json.loads(ledger["packets"][pm_packet]["body"])
        self.assertEqual(pm_body["recent_role_report_summary"][0]["result_id"], blocking_result_id)
        self.assertEqual(pm_body["authorized_result_reads"][0]["result_id"], blocking_result_id)

        pm_lease = runtime.lease_agent(ledger, "pm", agent_id="pm-a", packet_id=pm_packet)
        runtime.assign_packet(ledger, pm_packet, pm_lease)
        runtime.ack_lease(ledger, pm_lease, pm_packet)
        delivered = runtime.open_authorized_input_materials_for_role(ledger, pm_packet, pm_lease)
        self.assertEqual([row["result_id"] for row in delivered], [blocking_result_id])
        self.assertIn("stale lifecycle path", delivered[0]["sealed_result_body"])
        accepted_decision_id = runtime.submit_result(
            ledger,
            pm_lease,
            pm_packet,
            pm_repair_decision_body(
                ledger,
                pm_packet,
                decision="repair_current_scope",
                reason="repair the stale lifecycle path",
            ),
        )

        self.assertEqual(ledger["results"][accepted_decision_id]["status"], "accepted")
        self._complete_pm_continue_repair_gate(ledger, blocker_id)
        fresh_packets = [
            row
            for row in ledger["packets"].values()
            if row.get("repair_blocker_id") == blocker_id
            and row["packet_id"] != pm_packet
            and row["status"] == "open"
            and row.get("envelope", {}).get("packet_kind") == "task"
        ]
        self.assertEqual(len(fresh_packets), 1)
        fresh_body = json.loads(fresh_packets[0]["body"])
        self.assertEqual(fresh_body["authorized_result_reads"][0]["result_id"], blocking_result_id)

    def test_pm_repair_packet_projects_blocker_body_into_repair_obligations(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        blocking_result_id = runtime.submit_result(
            ledger,
            worker,
            packet_id,
            role_result_body(
                "Worker cannot proceed because direct evidence and FlowGuard replay are missing.",
                decision="block",
                blocking=True,
                recommended_resolution="Add direct evidence, rerun FlowGuard, and then validate the current result.",
            ),
        )

        blocker_id = next(iter(ledger["active_blockers"]))
        pm_packet = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
        pm_body = json.loads(ledger["packets"][pm_packet]["body"])
        obligation_kinds = {row["evidence_kind"] for row in pm_body["repair_evidence_obligations"]}
        self.assertIn("direct_deliverable_evidence", obligation_kinds)
        self.assertIn("formal_flowguard_evidence", obligation_kinds)
        self.assertIn("fresh_current_evidence", obligation_kinds)
        self.assertEqual(pm_body["authorized_result_reads"][0]["result_id"], blocking_result_id)

        pm_lease = runtime.lease_agent(ledger, "pm", agent_id="pm-obligations", packet_id=pm_packet)
        runtime.assign_packet(ledger, pm_packet, pm_lease)
        runtime.ack_lease(ledger, pm_lease, pm_packet)
        delivered = runtime.open_authorized_input_materials_for_role(ledger, pm_packet, pm_lease)
        self.assertIn("direct evidence and FlowGuard replay are missing", delivered[0]["sealed_result_body"])

    def test_pm_repair_decision_reason_only_is_rejected_when_obligations_exist(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(
            ledger,
            worker,
            packet_id,
            role_result_body(
                "Worker blocked on missing direct evidence.",
                decision="block",
                blocking=True,
                recommended_resolution="Add direct evidence.",
            ),
        )
        blocker_id = next(iter(ledger["active_blockers"]))
        pm_packet = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
        pm_lease = runtime.lease_agent(ledger, "pm", agent_id="pm-reason-only", packet_id=pm_packet)
        runtime.assign_packet(ledger, pm_packet, pm_lease)
        runtime.ack_lease(ledger, pm_lease, pm_packet)
        open_required_result_reads(ledger, pm_packet, pm_lease)

        result_id = runtime.submit_result(
            ledger,
            pm_lease,
            pm_packet,
            json.dumps(
                {
                    "decision": "repair_current_scope",
                    "reason": "I will repair it.",
                    "target_blocker_id": blocker_id,
                    "next_action": "repair_current_scope",
                }
            ),
        )

        result = ledger["results"][result_id]
        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertIn("repair_obligation_disposition", result["missing_required_fields"])
        self.assertFalse(ledger["pm_repair_decisions"])

    def test_pm_repair_obligation_rejects_stale_or_registry_only_disposition(self) -> None:
        for mutation in ("stale_evidence_ref", "acceptance_registry_only"):
            with self.subTest(mutation=mutation):
                ledger, packet_id, worker = runtime_runner._base_ledger()
                runtime.ack_lease(ledger, worker, packet_id)
                blocking_result_id = runtime.submit_result(
                    ledger,
                    worker,
                    packet_id,
                    role_result_body(
                        "Worker blocked on missing direct evidence.",
                        decision="block",
                        blocking=True,
                        recommended_resolution="Add direct evidence.",
                    ),
                )
                blocker_id = next(iter(ledger["active_blockers"]))
                pm_packet = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
                body = json.loads(pm_repair_decision_body(ledger, pm_packet, decision="repair_current_scope"))
                if mutation == "stale_evidence_ref":
                    body["repair_obligation_disposition"][0]["evidence_refs"] = [blocking_result_id]
                else:
                    body["repair_obligation_disposition"][0]["disposition"] = "acceptance_registry_only"
                pm_lease = runtime.lease_agent(ledger, "pm", agent_id=f"pm-{mutation}", packet_id=pm_packet)
                runtime.assign_packet(ledger, pm_packet, pm_lease)
                runtime.ack_lease(ledger, pm_lease, pm_packet)
                open_required_result_reads(ledger, pm_packet, pm_lease)

                result_id = runtime.submit_result(ledger, pm_lease, pm_packet, json.dumps(body))

                result = ledger["results"][result_id]
                self.assertEqual(result["status"], "mechanical_contract_blocked")
                self.assertIn("repair_obligation_disposition", result["missing_required_fields"])
                self.assertFalse(ledger["pm_repair_decisions"])

    def test_repair_packet_and_flowguard_recheck_must_consume_repair_obligations(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(
            ledger,
            worker,
            packet_id,
            role_result_body(
                "Worker blocked on missing direct evidence.",
                decision="block",
                blocking=True,
                recommended_resolution="Add direct evidence.",
            ),
        )
        blocker_id = next(iter(ledger["active_blockers"]))
        pm_packet = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
        pm_lease = runtime.lease_agent(ledger, "pm", agent_id="pm-repair-context", packet_id=pm_packet)
        runtime.assign_packet(ledger, pm_packet, pm_lease)
        runtime.ack_lease(ledger, pm_lease, pm_packet)
        open_required_result_reads(ledger, pm_packet, pm_lease)
        runtime.submit_result(
            ledger,
            pm_lease,
            pm_packet,
            pm_repair_decision_body(ledger, pm_packet, decision="repair_current_scope"),
        )
        self._complete_pm_continue_repair_gate(ledger, blocker_id)
        repair_packet = ledger["active_blockers"][blocker_id]["repair_packet_id"]
        repair_body = json.loads(ledger["packets"][repair_packet]["body"])
        self.assertTrue(repair_body["repair_obligation_context"]["repair_evidence_obligations"])
        self.assertEqual(repair_body["repair_evidence_obligations"][0]["source_blocker_id"], blocker_id)

        repair_lease = runtime.lease_agent(ledger, "worker", packet_id=repair_packet)
        runtime.assign_packet(ledger, repair_packet, repair_lease)
        runtime.ack_lease(ledger, repair_lease, repair_packet)
        open_required_result_reads(ledger, repair_packet, repair_lease)
        runtime.submit_result(ledger, repair_lease, repair_packet, role_result_body("Worker submitted repaired evidence."))
        flowguard_packet = runtime_runner._open_packet_by_kind(ledger, "flowguard_check")
        flowguard_body = json.loads(ledger["packets"][flowguard_packet]["body"])
        self.assertEqual(
            flowguard_body["semantic_recheck_contract"]["must_consume_repair_obligation_ids"],
            [row["obligation_id"] for row in flowguard_body["repair_evidence_obligations"]],
        )

        flowguard_lease = runtime.lease_agent(
            ledger,
            "flowguard_operator",
            packet_id=flowguard_packet,
        )
        runtime.assign_packet(ledger, flowguard_packet, flowguard_lease)
        runtime.ack_lease(ledger, flowguard_lease, flowguard_packet)
        open_required_result_reads(ledger, flowguard_packet, flowguard_lease)
        result_id = runtime.submit_result(
            ledger,
            flowguard_lease,
            flowguard_packet,
            flowguard_result_body(
                "FlowGuard forgot to consume the repair obligation.",
                **semantic_recheck_fields(
                    blocker_id,
                    consumed_authorized_result_read_ids=[
                        str(row.get("result_id") or "")
                        for row in ledger["packets"][flowguard_packet]["envelope"].get("authorized_result_reads", [])
                        if row.get("required_before_submit") is True and str(row.get("result_id") or "")
                    ],
                ),
            ),
        )

        result = ledger["results"][result_id]
        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertIn("semantic_recheck.consumed_repair_obligation_ids", result["missing_required_fields"])

    def test_flowguard_semantic_recheck_reissue_inherits_required_authorized_reads(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(
            ledger,
            worker,
            packet_id,
            role_result_body(
                "Worker blocked on missing direct evidence.",
                decision="block",
                blocking=True,
                recommended_resolution="Add direct evidence.",
            ),
        )
        blocker_id = next(iter(ledger["active_blockers"]))
        pm_packet = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
        pm_lease = runtime.lease_agent(ledger, "pm", agent_id="pm-semantic-reissue", packet_id=pm_packet)
        runtime.assign_packet(ledger, pm_packet, pm_lease)
        runtime.ack_lease(ledger, pm_lease, pm_packet)
        open_required_result_reads(ledger, pm_packet, pm_lease)
        runtime.submit_result(
            ledger,
            pm_lease,
            pm_packet,
            pm_repair_decision_body(ledger, pm_packet, decision="repair_current_scope"),
        )
        self._complete_pm_continue_repair_gate(ledger, blocker_id)
        repair_packet = ledger["active_blockers"][blocker_id]["repair_packet_id"]
        repair_lease = runtime.lease_agent(ledger, "worker", packet_id=repair_packet)
        runtime.assign_packet(ledger, repair_packet, repair_lease)
        runtime.ack_lease(ledger, repair_lease, repair_packet)
        open_required_result_reads(ledger, repair_packet, repair_lease)
        runtime.submit_result(ledger, repair_lease, repair_packet, role_result_body("Worker submitted repaired evidence."))

        flowguard_packet_id = runtime_runner._open_packet_by_kind(ledger, "flowguard_check")
        source_reads = ledger["packets"][flowguard_packet_id]["envelope"]["authorized_result_reads"]
        flowguard_lease = runtime.lease_agent(
            ledger,
            "flowguard_operator",
            packet_id=flowguard_packet_id,
        )
        runtime.assign_packet(ledger, flowguard_packet_id, flowguard_lease)
        runtime.ack_lease(ledger, flowguard_lease, flowguard_packet_id)
        open_required_result_reads(ledger, flowguard_packet_id, flowguard_lease)

        result_id = runtime.submit_result(
            ledger,
            flowguard_lease,
            flowguard_packet_id,
            flowguard_result_body("FlowGuard forgot the blocker-bound semantic recheck."),
        )
        result = ledger["results"][result_id]
        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertIn("semantic_recheck", result["missing_required_fields"])
        reissue_event = next(
            event
            for event in reversed(ledger["events"])
            if event["event_type"] == "current_contract_reissue_packet_issued"
            and event["payload"]["blocked_packet_id"] == flowguard_packet_id
        )
        reissue_packet_id = reissue_event["payload"]["fresh_packet_id"]
        reissue_packet = ledger["packets"][reissue_packet_id]
        reissue_manifest = reissue_packet["envelope"]["current_handoff_contract"]["input_material_manifest"]

        self.assertEqual(reissue_packet["envelope"]["authorized_result_reads"], source_reads)
        self.assertEqual(json.loads(reissue_packet["body"])["authorized_result_reads"], source_reads)
        self.assertEqual(
            reissue_manifest["required_authorized_reads_before_submit"],
            [row["result_id"] for row in source_reads if row["required_before_submit"] is True],
        )

    def test_reviewer_required_repair_reaches_pm_repair_packet(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(ledger, worker, packet_id, role_result_body("Worker submitted implementation evidence."))

        flowguard_packet = runtime_runner._open_packet_by_kind(ledger, "flowguard_check")
        flowguard_lease = runtime.lease_agent(ledger, "flowguard_operator", agent_id="fg", packet_id=flowguard_packet)
        runtime.assign_packet(ledger, flowguard_packet, flowguard_lease)
        runtime.ack_lease(ledger, flowguard_lease, flowguard_packet)
        open_required_result_reads(ledger, flowguard_packet, flowguard_lease)
        write_flowguard_evidence_artifact(ledger, flowguard_packet)
        flowguard_result_id = runtime.submit_result(
            ledger,
            flowguard_lease,
            flowguard_packet,
            flowguard_result_body("FlowGuard evidence passed."),
        )

        review_packet = runtime_runner._open_packet_by_kind(ledger, "review")
        review_lease = runtime.lease_agent(ledger, "reviewer", agent_id="reviewer", packet_id=review_packet)
        runtime.assign_packet(ledger, review_packet, review_lease)
        runtime.ack_lease(ledger, review_lease, review_packet)
        open_required_result_reads(ledger, review_packet, review_lease)
        required_repair = (
            "Replace data/product/projectradar_lifecycle.json with "
            "data/product/projectradar_project_lifecycle.json in relevant_references."
        )
        review_result_id = runtime.submit_result(
            ledger,
            review_lease,
            review_packet,
            review_result_body(
                "Reviewer found the node plan still points at the stale lifecycle file.",
                passed=False,
                recommended_resolution="reviewer reported fail",
                blocking_findings=[{"finding": "stale lifecycle path", "required_repair": required_repair}],
            ),
        )

        blocker_id = next(iter(ledger["active_blockers"]))
        blocker = ledger["active_blockers"][blocker_id]
        self.assertEqual(blocker["recommended_resolution"], required_repair)
        pm_packet = blocker["pm_repair_packet_id"]
        body = json.loads(ledger["packets"][pm_packet]["body"])
        self.assertEqual(body["recommended_resolution"], required_repair)
        self.assertEqual(body["recent_role_report_summary"][0]["role"], "reviewer")
        self.assertEqual(
            body["recent_role_report_summary"][0]["summary"],
            ["Reviewer found the node plan still points at the stale lifecycle file."],
        )
        authorized_reads = body["authorized_result_reads"]
        self.assertEqual(authorized_reads[0]["result_id"], review_result_id)
        self.assertTrue(authorized_reads[0]["required_before_submit"])
        authorized_read_ids = {row["result_id"] for row in authorized_reads}
        self.assertIn(review_result_id, authorized_read_ids)
        self.assertIn(flowguard_result_id, authorized_read_ids)

        pm_lease = runtime.lease_agent(ledger, "pm", agent_id="pm-review-context", packet_id=pm_packet)
        runtime.assign_packet(ledger, pm_packet, pm_lease)
        runtime.ack_lease(ledger, pm_lease, pm_packet)
        delivered = runtime.open_authorized_input_materials_for_role(ledger, pm_packet, pm_lease)
        delivered_ids = {row["result_id"] for row in delivered}
        self.assertIn(review_result_id, delivered_ids)
        self.assertIn(flowguard_result_id, delivered_ids)

    def test_reviewer_quality_score_and_quantitative_gap_reach_pm_and_repair_packet(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(ledger, worker, packet_id, role_result_body("Worker delivered 5 of 100 required items."))

        flowguard_packet = runtime_runner._open_packet_by_kind(ledger, "flowguard_check")
        flowguard_lease = runtime.lease_agent(ledger, "flowguard_operator", agent_id="fg", packet_id=flowguard_packet)
        runtime.assign_packet(ledger, flowguard_packet, flowguard_lease)
        runtime.ack_lease(ledger, flowguard_lease, flowguard_packet)
        open_required_result_reads(ledger, flowguard_packet, flowguard_lease)
        write_flowguard_evidence_artifact(ledger, flowguard_packet)
        flowguard_result_id = runtime.submit_result(
            ledger,
            flowguard_lease,
            flowguard_packet,
            flowguard_result_body("FlowGuard evidence passed."),
        )

        review_packet = runtime_runner._open_packet_by_kind(ledger, "review")
        review_lease = runtime.lease_agent(ledger, "reviewer", agent_id="reviewer-score", packet_id=review_packet)
        runtime.assign_packet(ledger, review_packet, review_lease)
        runtime.ack_lease(ledger, review_lease, review_packet)
        open_required_result_reads(ledger, review_packet, review_lease)
        score_summary = (
            "Quality score: 3/10; target: 9/10; minimum hard gate passed: false; "
            "required 100 items, delivered 5, gap 95."
        )
        required_repair = "Produce the missing 95 required items and recheck against the 9/10 target."
        review_result_id = runtime.submit_result(
            ledger,
            review_lease,
            review_packet,
            review_result_body(
                score_summary,
                passed=False,
                recommended_resolution="repair quantitative gap",
                blocking_findings=[
                    {
                        "finding": score_summary,
                        "required_repair": required_repair,
                    }
                ],
            ),
        )

        blocker_id = next(iter(ledger["active_blockers"]))
        blocker = ledger["active_blockers"][blocker_id]
        self.assertEqual(blocker["recommended_resolution"], required_repair)
        pm_packet = blocker["pm_repair_packet_id"]
        pm_body = json.loads(ledger["packets"][pm_packet]["body"])
        self.assertEqual(pm_body["recommended_resolution"], required_repair)
        self.assertEqual(pm_body["recent_role_report_summary"][0]["summary"], [score_summary])
        authorized_read_ids = {row["result_id"] for row in pm_body["authorized_result_reads"]}
        self.assertIn(review_result_id, authorized_read_ids)
        self.assertIn(flowguard_result_id, authorized_read_ids)

        pm_lease = runtime.lease_agent(ledger, "pm", agent_id="pm-score", packet_id=pm_packet)
        runtime.assign_packet(ledger, pm_packet, pm_lease)
        runtime.ack_lease(ledger, pm_lease, pm_packet)
        delivered = runtime.open_authorized_input_materials_for_role(ledger, pm_packet, pm_lease)
        delivered_bodies = "\n".join(str(row.get("sealed_result_body") or "") for row in delivered)
        self.assertIn("Quality score: 3/10", delivered_bodies)
        runtime.submit_result(
            ledger,
            pm_lease,
            pm_packet,
            pm_repair_decision_body(ledger, pm_packet, decision="repair_current_scope"),
        )
        self._complete_pm_continue_repair_gate(ledger, blocker_id)

        repair_packet = ledger["active_blockers"][blocker_id]["repair_packet_id"]
        repair_body = json.loads(ledger["packets"][repair_packet]["body"])
        self.assertIn("Quality score", repair_body["instruction"])
        self.assertIn("target: 9/10", repair_body["instruction"])
        self.assertIn("quantitative required/delivered/gap", repair_body["instruction"])
        self.assertEqual(repair_body["authorized_result_reads"][0]["result_id"], review_result_id)

        repair_lease = runtime.lease_agent(ledger, "worker", packet_id=repair_packet)
        runtime.assign_packet(ledger, repair_packet, repair_lease)
        runtime.ack_lease(ledger, repair_lease, repair_packet)
        repair_delivered = runtime.open_authorized_input_materials_for_role(ledger, repair_packet, repair_lease)
        repair_bodies = "\n".join(str(row.get("sealed_result_body") or "") for row in repair_delivered)
        self.assertIn("Quality score: 3/10", repair_bodies)
        self.assertIn("gap 95", repair_bodies)

    def test_reviewer_soft_low_score_pass_does_not_create_blocker(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(ledger, worker, packet_id, role_result_body("Worker met the minimum user standard."))

        flowguard_packet = runtime_runner._open_packet_by_kind(ledger, "flowguard_check")
        flowguard_lease = runtime.lease_agent(ledger, "flowguard_operator", agent_id="fg", packet_id=flowguard_packet)
        runtime.assign_packet(ledger, flowguard_packet, flowguard_lease)
        runtime.ack_lease(ledger, flowguard_lease, flowguard_packet)
        open_required_result_reads(ledger, flowguard_packet, flowguard_lease)
        write_flowguard_evidence_artifact(ledger, flowguard_packet)
        runtime.submit_result(
            ledger,
            flowguard_lease,
            flowguard_packet,
            flowguard_result_body("FlowGuard evidence passed."),
        )

        review_packet = runtime_runner._open_packet_by_kind(ledger, "review")
        review_lease = runtime.lease_agent(ledger, "reviewer", agent_id="reviewer-soft-score", packet_id=review_packet)
        runtime.assign_packet(ledger, review_packet, review_lease)
        runtime.ack_lease(ledger, review_lease, review_packet)
        open_required_result_reads(ledger, review_packet, review_lease)
        result_id = runtime.submit_result(
            ledger,
            review_lease,
            review_packet,
            review_result_body(
                (
                    "Quality score: 6/10; target: 9/10; minimum hard gate passed: true; "
                    "minimum user standard is just met."
                ),
                pm_suggestion_items=[
                    "PM decision-support: weakest evidence is polish depth after the minimum gate; PM may adopt a named verification or reject it because current hard-gate evidence is sufficient."
                ],
            ),
        )

        self.assertEqual(ledger["results"][result_id]["status"], "accepted")
        self.assertFalse(ledger["active_blockers"])

    def test_pm_repair_decision_blocks_without_opening_all_related_bodies(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(ledger, worker, packet_id, role_result_body("Worker submitted implementation evidence."))

        flowguard_packet = runtime_runner._open_packet_by_kind(ledger, "flowguard_check")
        flowguard_lease = runtime.lease_agent(ledger, "flowguard_operator", agent_id="fg", packet_id=flowguard_packet)
        runtime.assign_packet(ledger, flowguard_packet, flowguard_lease)
        runtime.ack_lease(ledger, flowguard_lease, flowguard_packet)
        open_required_result_reads(ledger, flowguard_packet, flowguard_lease)
        write_flowguard_evidence_artifact(ledger, flowguard_packet)
        flowguard_result_id = runtime.submit_result(
            ledger,
            flowguard_lease,
            flowguard_packet,
            flowguard_result_body("FlowGuard evidence passed."),
        )

        review_packet = runtime_runner._open_packet_by_kind(ledger, "review")
        review_lease = runtime.lease_agent(ledger, "reviewer", agent_id="reviewer", packet_id=review_packet)
        runtime.assign_packet(ledger, review_packet, review_lease)
        runtime.ack_lease(ledger, review_lease, review_packet)
        open_required_result_reads(ledger, review_packet, review_lease)
        review_result_id = runtime.submit_result(
            ledger,
            review_lease,
            review_packet,
            review_result_body(
                "Reviewer found a current evidence gap.",
                passed=False,
                recommended_resolution="repair current evidence",
                blocking_findings=[{"finding": "current evidence gap", "required_repair": "repair current evidence"}],
            ),
        )

        blocker_id = next(iter(ledger["active_blockers"]))
        pm_packet = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
        pm_lease = runtime.lease_agent(ledger, "pm", agent_id="pm-no-open", packet_id=pm_packet)
        runtime.assign_packet(ledger, pm_packet, pm_lease)
        runtime.ack_lease(ledger, pm_lease, pm_packet)

        result_id = runtime.submit_result(
            ledger,
            pm_lease,
            pm_packet,
            pm_repair_decision_body(ledger, pm_packet, decision="repair_current_scope"),
        )

        result = ledger["results"][result_id]
        self.assertEqual(result["status"], "blocked")
        self.assertIn(f"required_result_body_not_opened:{review_result_id}", result["mechanical_blockers"])
        self.assertIn(f"required_result_body_not_opened:{flowguard_result_id}", result["mechanical_blockers"])
        self.assertFalse(ledger["pm_repair_decisions"])

    def test_generated_role_handoff_and_packet_open_are_role_symmetric(self) -> None:
        for role in sorted(runtime.RESPONSIBILITIES):
            with self.subTest(role=role):
                ledger = runtime.new_ledger("Goal", "Contract")
                authorize_background_collaboration(ledger)
                runtime.create_route(ledger, "Route", ["Do work"])
                body = f"SEALED_BODY_FOR_{role}"
                packet_id = runtime.issue_task_packet(
                    ledger,
                    role,
                    f"{role} objective",
                    body,
                    packet_kind="flowguard_check" if role == "flowguard_operator" else "task",
                )
                lease_id = runtime.lease_agent(ledger, role, agent_id=f"{role}-agent", packet_id=packet_id)
                runtime.assign_packet(ledger, packet_id, lease_id)

                handoff = role_handoff.render_current_packet_handoff(
                    ledger,
                    root=ROOT,
                    script_path=ASSETS_ROOT / "flowpilot_new.py",
                    run_id="run-test",
                    packet_id=packet_id,
                    lease_id=lease_id,
                )

                rendered = json.dumps(handoff, sort_keys=True)
                self.assertTrue(handoff["controller_may_read"])
                self.assertFalse(handoff["controller_may_read_packet_body"])
                self.assertFalse(handoff["sealed_body_text_included"])
                self.assertIn("flowpilot_new.py", handoff["commands"]["ack"])
                self.assertIn("open-packet", handoff["commands"]["open_packet"])
                self.assertIn("submit-result", handoff["commands"]["submit_result"])
                self.assertIn("--body-file", handoff["commands"]["submit_result"])
                self.assertNotIn("--body <sealed_result_summary>", handoff["commands"]["submit_result"])
                self.assertNotIn(body, rendered)

                with self.assertRaises(Exception):
                    packets.open_sealed_body_for_role(ledger, packet_id, lease_id)

                runtime.ack_lease(ledger, lease_id, packet_id)
                opened = packets.open_sealed_body_for_role(ledger, packet_id, lease_id)

                self.assertEqual(opened, body)
                open_events = [
                    event
                    for event in ledger["events"]
                    if event["event_type"] == "sealed_packet_body_opened"
                    and event["payload"]["packet_id"] == packet_id
                    and event["payload"]["lease_id"] == lease_id
                ]
                self.assertEqual(len(open_events), 1)

    def test_packet_open_rejects_wrong_stale_or_tampered_authority(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        authorize_background_collaboration(ledger)
        runtime.create_route(ledger, "Route", ["Do work"])
        packet_id = runtime.issue_task_packet(ledger, "worker", "Do work", "sealed")
        lease_id = runtime.lease_agent(ledger, "worker", agent_id="worker-1", packet_id=packet_id)
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)

        wrong_lease = runtime.lease_agent(ledger, "worker", agent_id="worker-2", packet_id=packet_id)
        with self.assertRaises(Exception):
            packets.open_sealed_body_for_role(ledger, packet_id, wrong_lease)

        wrong_role = copy.deepcopy(ledger)
        wrong_role_lease = runtime.lease_agent(wrong_role, "pm", agent_id="pm-1")
        wrong_role["packets"][packet_id]["assigned_lease_id"] = wrong_role_lease
        wrong_role["leases"][wrong_role_lease]["ack_received"] = True
        with self.assertRaises(Exception):
            packets.open_sealed_body_for_role(wrong_role, packet_id, wrong_role_lease)

        accepted = copy.deepcopy(ledger)
        accepted["packets"][packet_id]["status"] = "accepted"
        accepted["packets"][packet_id]["accepted_result_id"] = "result-accepted"
        with self.assertRaises(Exception):
            packets.open_sealed_body_for_role(accepted, packet_id, lease_id)

        tampered = copy.deepcopy(ledger)
        tampered["packets"][packet_id]["body"] = "changed after envelope hash"
        with self.assertRaises(Exception):
            packets.open_sealed_body_for_role(tampered, packet_id, lease_id)

    def test_prose_status_pass_is_mechanically_reissued(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)

        result_id = runtime.submit_result(
            ledger,
            worker,
            packet_id,
            "\n".join(
                [
                    "Status: PASS",
                    "The old topology check failed before this repair.",
                    "The report includes function-block rows and blocker history.",
                ]
            ),
        )

        self.assertEqual(ledger["results"][result_id]["status"], "mechanical_contract_blocked")
        self.assertIn("current_result_contract_violation", ledger["results"][result_id]["mechanical_blockers"])
        self.assertEqual(ledger["packets"][packet_id]["status"], "superseded_after_repair")
        reissues = [
            row
            for row in ledger["packets"].values()
            if row["packet_id"] != packet_id and row["status"] == "open"
        ]
        self.assertEqual(len(reissues), 1)

    def test_declared_block_line_is_mechanically_reissued(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)

        result_id = runtime.submit_result(
            ledger,
            worker,
            packet_id,
            "Decision: block\nReason: current evidence is not sufficient.",
        )

        self.assertEqual(ledger["results"][result_id]["status"], "mechanical_contract_blocked")
        self.assertEqual(ledger["packets"][packet_id]["status"], "superseded_after_repair")
        self.assertFalse(ledger["active_blockers"])
        action = runtime.router_next_action(ledger)
        self.assertEqual(action.action_type, "dispatch_current_role")
        self.assertEqual(action.responsibility, "worker")

    def test_structured_verdict_alias_is_mechanically_reissued(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)

        result_id = runtime.submit_result(
            ledger,
            worker,
            packet_id,
            json.dumps({"verdict": "blocked", "recommended_resolution": "fresh FlowGuard evidence required"}),
        )

        self.assertEqual(ledger["results"][result_id]["status"], "mechanical_contract_blocked")
        self.assertEqual(ledger["packets"][packet_id]["status"], "superseded_after_repair")
        self.assertFalse(ledger["active_blockers"])

    def test_nested_flowguard_report_is_forbidden_in_worker_result(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)

        result_id = runtime.submit_result(
            ledger,
            worker,
            packet_id,
            json.dumps(
                {
                    "decision": "pass",
                    "flowguard_report": {
                        "ok": False,
                        "findings": ["missing_validation_evidence"],
                    },
                    "pm_visible_summary": ["Worker result contains a nested FlowGuard report that is not OK."],
                    "recommended_resolution": "rerun with current-run evidence",
                }
            ),
        )

        result = ledger["results"][result_id]
        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertEqual(ledger["packets"][packet_id]["status"], "superseded_after_repair")
        self.assertIn("flowguard_report", result["forbidden_fields_seen"])
        active = [row for row in ledger["active_blockers"].values() if row["status"] == "active"]
        self.assertEqual(active, [])

    def test_run_until_wait_folds_internal_action_to_role_boundary(self) -> None:
        ledger = runtime.new_ledger("Goal", "Contract")
        ledger["startup_intake"] = {"sealed": True}
        runtime.create_route(ledger, "Route", ["Do work"])

        boundary = runtime.run_until_wait(ledger)

        self.assertEqual(boundary["boundary_class"], "role_dispatch")
        self.assertEqual(boundary["next_action"]["action_type"], "dispatch_current_role")
        self.assertEqual(boundary["folded_applied_count"], 1)
        self.assertEqual(boundary["folded_applied_actions"][0]["action_type"], "issue_task_packet")

    def test_pm_repair_decision_ignores_hostile_prose_when_json_decision_is_present(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(
            ledger,
            worker,
            packet_id,
            role_result_body("Worker reports that PM repair is needed.", decision="block", blocking=True, recommended_resolution="needs repair"),
        )
        blocker_id = next(iter(ledger["active_blockers"]))
        pm_packet = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
        pm_lease = runtime.lease_agent(ledger, "pm", agent_id="pm-a", packet_id=pm_packet)
        runtime.assign_packet(ledger, pm_packet, pm_lease)
        runtime.ack_lease(ledger, pm_lease, pm_packet)
        open_required_result_reads(ledger, pm_packet, pm_lease)

        runtime.submit_result(
            ledger,
            pm_lease,
            pm_packet,
            pm_repair_decision_body(
                ledger,
                pm_packet,
                decision="repair_current_scope",
                reason="This prose mentions stop_for_user and block, but they are not the decision.",
            ),
        )

        decision = next(iter(ledger["pm_repair_decisions"].values()))
        self.assertEqual(decision["decision"], "repair_current_scope")
        self._complete_pm_continue_repair_gate(ledger, blocker_id)
        self.assertEqual(ledger["active_blockers"][blocker_id]["status"], "repair_packet_open")

    def test_removed_pm_repair_decisions_are_rejected(self) -> None:
        for removed in (
            "same_node_repair",
            "sender_reissue",
            "collect_more_evidence",
            "mutate_route",
            "quarantine_evidence",
        ):
            with self.subTest(removed=removed):
                ledger, packet_id, worker = runtime_runner._base_ledger()
                runtime.ack_lease(ledger, worker, packet_id)
                runtime.submit_result(
                    ledger,
                    worker,
                    packet_id,
                    role_result_body("Worker reports that PM must choose a repair.", decision="block", blocking=True, recommended_resolution="needs PM"),
                )
                blocker_id = next(iter(ledger["active_blockers"]))
                pm_packet = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
                pm_lease = runtime.lease_agent(ledger, "pm", agent_id=f"pm-{removed}", packet_id=pm_packet)
                runtime.assign_packet(ledger, pm_packet, pm_lease)
                runtime.ack_lease(ledger, pm_lease, pm_packet)
                open_required_result_reads(ledger, pm_packet, pm_lease)

                bad_result = runtime.submit_result(
                    ledger,
                    pm_lease,
                    pm_packet,
                    json.dumps(
                        {
                            "decision": removed,
                            "reason": "old menu value",
                            "target_blocker_id": blocker_id,
                            "next_action": removed,
                        }
                    ),
                )

                self.assertEqual(ledger["results"][bad_result]["status"], "mechanical_contract_blocked")
                self.assertFalse(ledger["pm_repair_decisions"])
                self.assertIn("allowed_value_options", ledger["results"][bad_result]["quarantine_reason"])
                self.assertEqual(
                    ledger["results"][bad_result]["contract_family_id"],
                    "pm_repair_decision.pm_repair_decision",
                )

    def test_waive_with_authority_requires_authority_ref_and_opens_no_repair_packet(self) -> None:
        for body_factory, expected_status in (
            (
                lambda ledger, pm_packet: pm_repair_decision_body(
                    ledger,
                    pm_packet,
                    decision="waive_with_authority",
                    reason="authorized exception",
                ),
                "mechanical_contract_blocked",
            ),
            (
                lambda ledger, pm_packet: pm_repair_decision_body(
                    ledger,
                    pm_packet,
                    decision="waive_with_authority",
                    reason="authorized exception",
                    authority_ref="AUTH-20260604-001",
                ),
                "waived",
            ),
        ):
            with self.subTest(expected_status=expected_status):
                ledger, packet_id, worker = runtime_runner._base_ledger()
                runtime.ack_lease(ledger, worker, packet_id)
                runtime.submit_result(
                    ledger,
                    worker,
                    packet_id,
                    role_result_body("Worker reports that PM authority is needed.", decision="block", blocking=True, recommended_resolution="needs PM"),
                )
                blocker_id = next(iter(ledger["active_blockers"]))
                blocker = ledger["active_blockers"][blocker_id]
                pm_packet = blocker["pm_repair_packet_id"]
                pm_lease = runtime.lease_agent(ledger, "pm", agent_id=f"pm-{expected_status}", packet_id=pm_packet)
                runtime.assign_packet(ledger, pm_packet, pm_lease)
                runtime.ack_lease(ledger, pm_lease, pm_packet)
                open_required_result_reads(ledger, pm_packet, pm_lease)

                result_id = runtime.submit_result(ledger, pm_lease, pm_packet, body_factory(ledger, pm_packet))

                if expected_status == "mechanical_contract_blocked":
                    self.assertEqual(ledger["results"][result_id]["status"], expected_status)
                    self.assertFalse(ledger["pm_repair_decisions"])
                    self.assertEqual(ledger["results"][result_id]["missing_required_fields"], ["authority_ref"])
                    self.assertEqual(ledger["packets"][pm_packet]["status"], "superseded_after_repair")
                else:
                    self.assertEqual(ledger["active_blockers"][blocker_id]["status"], expected_status)
                    self.assertEqual(ledger["active_blockers"][blocker_id]["authority_ref"], "AUTH-20260604-001")
                    self.assertNotIn("repair_packet_id", ledger["active_blockers"][blocker_id])

    def test_pm_repair_decision_rejects_authority_alias(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(
            ledger,
            worker,
            packet_id,
            role_result_body("Worker reports that PM authority is needed.", decision="block", blocking=True, recommended_resolution="needs PM"),
        )
        blocker_id = next(iter(ledger["active_blockers"]))
        pm_packet = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
        pm_lease = runtime.lease_agent(ledger, "pm", agent_id="pm-authority-alias", packet_id=pm_packet)
        runtime.assign_packet(ledger, pm_packet, pm_lease)
        runtime.ack_lease(ledger, pm_lease, pm_packet)
        open_required_result_reads(ledger, pm_packet, pm_lease)

        result_id = runtime.submit_result(
            ledger,
            pm_lease,
            pm_packet,
            json.dumps(
                {
                    "decision": "waive_with_authority",
                    "reason": "authorized exception",
                    "target_blocker_id": blocker_id,
                    "next_action": "waive_with_authority",
                    "authority": "AUTH-LEGACY-ALIAS",
                }
            ),
        )

        self.assertEqual(ledger["results"][result_id]["status"], "mechanical_contract_blocked")
        self.assertFalse(ledger["pm_repair_decisions"])
        self.assertEqual(ledger["results"][result_id]["missing_required_fields"], ["authority_ref"])
        self.assertEqual(ledger["results"][result_id]["forbidden_fields_seen"], ["authority"])

    def test_pm_repair_handoff_contract_includes_branch_shapes(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(
            ledger,
            worker,
            packet_id,
            role_result_body("Worker reports that route redesign may be needed.", decision="block", blocking=True, recommended_resolution="needs PM"),
        )
        blocker_id = next(iter(ledger["active_blockers"]))
        pm_packet = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
        handoff_contract = ledger["packets"][pm_packet]["envelope"]["current_handoff_contract"]
        report_contract = handoff_contract["required_report_contract"]
        branch_shapes = report_contract["branch_valid_shapes"]

        self.assertIn("decision=redesign_route", branch_shapes)
        self.assertEqual(report_contract["minimal_valid_shape"]["target_blocker_id"], blocker_id)
        redesign_shape = branch_shapes["decision=redesign_route"]
        self.assertEqual(redesign_shape["decision"], "redesign_route")
        self.assertEqual(redesign_shape["target_blocker_id"], blocker_id)
        self.assertEqual(redesign_shape["route_plan"]["schema_version"], runtime.ROUTE_PLAN_SCHEMA_VERSION)
        self.assertEqual(redesign_shape["route_plan"]["nodes"][0]["node_id"], "repair-current-scope")
        self.assertIn("title", redesign_shape["route_plan"]["nodes"][0])
        self.assertNotIn("route_plan.nodes[].title when decision=redesign_route", report_contract["required_child_fields"])

    def test_pm_repair_redesign_route_reissue_names_branch_field_path(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(
            ledger,
            worker,
            packet_id,
            role_result_body("Worker reports that route redesign may be needed.", decision="block", blocking=True, recommended_resolution="needs PM"),
        )
        blocker_id = next(iter(ledger["active_blockers"]))
        pm_packet = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
        pm_lease = runtime.lease_agent(ledger, "pm", agent_id="pm-redesign-bad", packet_id=pm_packet)
        runtime.assign_packet(ledger, pm_packet, pm_lease)
        runtime.ack_lease(ledger, pm_lease, pm_packet)
        open_required_result_reads(ledger, pm_packet, pm_lease)

        result_id = runtime.submit_result(
            ledger,
            pm_lease,
            pm_packet,
            json.dumps(
                {
                    "decision": "redesign_route",
                    "reason": "Route needs redesign, but this body omits the node title.",
                    "target_blocker_id": blocker_id,
                    "next_action": "redesign_route",
                    "route_plan": {
                        "schema_version": runtime.ROUTE_PLAN_SCHEMA_VERSION,
                        "nodes": [{"node_id": "node-redesign"}],
                    },
                }
            ),
        )
        result = ledger["results"][result_id]
        fresh_pm_packet = runtime._ensure_pm_repair_decision_packet_for_blocker(ledger, blocker_id)
        fresh_body = json.loads(ledger["packets"][fresh_pm_packet]["body"])

        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertEqual(result["mechanical_contract_failure"]["failed_branch"], "decision=redesign_route")
        self.assertEqual(result["mechanical_contract_failure"]["failed_field_path"], "route_plan.nodes[].title")
        self.assertEqual(fresh_body["failed_branch"], "decision=redesign_route")
        self.assertEqual(fresh_body["failed_field_path"], "route_plan.nodes[].title")
        self.assertEqual(fresh_body["minimal_valid_shape"]["target_blocker_id"], blocker_id)
        self.assertEqual(fresh_body["branch_minimal_valid_shape"]["target_blocker_id"], blocker_id)
        self.assertEqual(fresh_body["branch_minimal_valid_shape"]["decision"], "redesign_route")
        self.assertIn("title", fresh_body["branch_minimal_valid_shape"]["route_plan"]["nodes"][0])

    def test_june3_same_node_empty_fresh_packet_regression_is_rejected(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        result_id = runtime.submit_result(
            ledger,
            worker,
            packet_id,
            role_result_body("Worker reports that PM repair is needed.", decision="block", blocking=True, recommended_resolution="needs repair"),
        )
        blocker_id = next(iter(ledger["active_blockers"]))
        blocker = ledger["active_blockers"][blocker_id]
        decision_id = "pm_repair_decision-june3"
        ledger["pm_repair_decisions"][decision_id] = {
            "decision_id": decision_id,
            "blocker_id": blocker_id,
            "packet_id": blocker["pm_repair_packet_id"],
            "result_id": result_id,
            "decision": "repair_current_scope",
            "reason": "Regression guard for empty fresh packet.",
            "created_at": runtime.now_iso(),
        }

        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "fresh repair packet id"):
            runtime._mark_blocker_repair_packet_open(
                ledger,
                blocker,
                decision_id=decision_id,
                fresh_packet_id="",
            )

        self.assertNotEqual(ledger["active_blockers"][blocker_id]["status"], "repair_packet_open")

    def test_pm_repair_decision_requires_structured_field_and_stop_pauses_route(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(
            ledger,
            worker,
            packet_id,
            role_result_body("Worker reports that PM must choose a summary-safe repair.", decision="block", blocking=True, recommended_resolution="needs PM"),
        )
        blocker_id = next(iter(ledger["active_blockers"]))
        pm_packet = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
        bad_pm_lease = runtime.lease_agent(ledger, "pm", agent_id="pm-bad", packet_id=pm_packet)
        runtime.assign_packet(ledger, pm_packet, bad_pm_lease)
        runtime.ack_lease(ledger, bad_pm_lease, pm_packet)
        open_required_result_reads(ledger, pm_packet, bad_pm_lease)

        bad_result = runtime.submit_result(
            ledger,
            bad_pm_lease,
            pm_packet,
            "This body says block and stop_for_user, but it has no structured decision field.",
        )

        self.assertEqual(ledger["results"][bad_result]["status"], "mechanical_contract_blocked")
        self.assertEqual(ledger["packets"][pm_packet]["status"], "superseded_after_repair")
        self.assertFalse(ledger["pm_repair_decisions"])
        self.assertEqual(
            ledger["results"][bad_result]["missing_required_fields"],
            ["decision", "reason", "target_blocker_id", "next_action"],
        )
        self.assertEqual(runtime.router_next_action(ledger).action_type, "dispatch_current_role")

        fresh_pm_packet = runtime._ensure_pm_repair_decision_packet_for_blocker(ledger, blocker_id)
        self.assertNotEqual(fresh_pm_packet, pm_packet)
        self.assertEqual(ledger["packets"][pm_packet]["status"], "superseded_after_repair")

        good_pm_lease = runtime.lease_agent(ledger, "pm", packet_id=fresh_pm_packet)
        runtime.assign_packet(ledger, fresh_pm_packet, good_pm_lease)
        runtime.ack_lease(ledger, good_pm_lease, fresh_pm_packet)
        open_required_result_reads(ledger, fresh_pm_packet, good_pm_lease)
        runtime.submit_result(
            ledger,
            good_pm_lease,
            fresh_pm_packet,
            pm_repair_decision_body(
                ledger,
                fresh_pm_packet,
                decision="stop_for_user",
                reason="PM needs the user to decide.",
            ),
        )

        self.assertEqual(ledger["active_blockers"][blocker_id]["status"], "stopped")
        self.assertEqual(runtime.router_next_action(ledger).action_type, "wait_for_resume")
        runtime.record_resume_request(ledger, "plain_resume")
        runtime.reconcile_resume_request(ledger, resume_source="plain_resume")
        self.assertEqual(ledger["active_blockers"][blocker_id]["status"], "stopped")

        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "explicit user request"):
            runtime.resolve_stopped_blocker(
                ledger,
                blocker_id,
                resolution="reissue_pm_repair_decision",
                reason="plain resume must not continue current repair",
            )
        self.assertEqual(ledger["active_blockers"][blocker_id]["status"], "stopped")

        recovery = runtime.resolve_stopped_blocker(
            ledger,
            blocker_id,
            resolution="reissue_pm_repair_decision",
            reason="user chose to continue current repair",
            user_requested=True,
        )

        self.assertEqual(ledger["active_blockers"][blocker_id]["status"], "active")
        self.assertNotEqual(recovery["fresh_packet_id"], fresh_pm_packet)
        self.assertEqual(ledger["packets"][recovery["fresh_packet_id"]]["envelope"]["packet_kind"], "pm_repair_decision")
        self.assertTrue(recovery["user_requested"])

    def test_pm_repair_decision_break_glass_routes_control_plane_without_user_wait(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(
            ledger,
            worker,
            packet_id,
            role_result_body(
                "Worker reports a FlowPilot control-plane blocker.",
                decision="block",
                blocking=True,
                recommended_resolution="PM should decide whether control-plane break-glass is required.",
            ),
        )
        blocker_id = next(iter(ledger["active_blockers"]))
        pm_packet = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
        pm_lease = runtime.lease_agent(ledger, "pm", agent_id="pm-break-glass", packet_id=pm_packet)
        runtime.assign_packet(ledger, pm_packet, pm_lease)
        runtime.ack_lease(ledger, pm_lease, pm_packet)
        open_required_result_reads(ledger, pm_packet, pm_lease)

        runtime.submit_result(
            ledger,
            pm_lease,
            pm_packet,
            pm_repair_decision_body(
                ledger,
                pm_packet,
                decision="break_glass",
                reason="PM requests Controller diagnosis for a FlowPilot control-plane blocker.",
            ),
        )

        blocker = ledger["active_blockers"][blocker_id]
        action = runtime.router_next_action(ledger)
        self.assertEqual(blocker["status"], "active")
        self.assertTrue(blocker["pm_break_glass_decision_id"])
        self.assertEqual(action.action_type, "control_plane_blocker")
        self.assertEqual(action.subject_id, blocker_id)
        self.assertEqual(action.responsibility, "controller")
        self.assertIn("PM requested Controller break-glass", action.reason)
        self.assertNotEqual(action.action_type, "wait_for_resume")

    def test_missing_required_information_stops_without_pm_repair_packet(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(
            ledger,
            worker,
            packet_id,
            role_result_body(
                "Worker reports that FlowPilot did not deliver the required material.",
                decision="block",
                blocking=True,
                blocker_class="missing_required_information",
                recommended_resolution="FlowPilot control-plane material delivery is contradictory.",
            ),
        )
        blocker_id = next(iter(ledger["active_blockers"]))
        blocker = ledger["active_blockers"][blocker_id]
        self.assertEqual(blocker["pm_repair_packet_id"], "")
        self.assertEqual(blocker["status"], "stopped")
        self.assertEqual(blocker["runtime_next_action"], "same_packet_block_or_stop_for_user")
        self.assertEqual(ledger["packets"][packet_id]["status"], "pm_stopped")
        action = runtime.router_next_action(ledger)
        self.assertEqual(action.action_type, "wait_for_resume")
        self.assertEqual(action.subject_id, blocker_id)
        self.assertFalse(
            any(
                transaction.get("blocker_id") == blocker_id
                for transaction in ledger.get("repair_transactions", {}).values()
                if isinstance(transaction, dict)
            )
        )
        self.assertTrue(
            any(
                event.get("event_type") == "semantic_blocker_requires_material_or_user"
                and event.get("payload", {}).get("blocker_id") == blocker_id
                for event in ledger["events"]
            )
        )

    def test_reattach_required_recheck_requires_user_request(self) -> None:
        ledger, _packet_id, blocker_id, _flowguard_packet, _review_packet, _pm_packet = (
            self._stopped_review_blocker_after_flowguard_failure()
        )

        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "explicit user request"):
            runtime.resolve_stopped_blocker(
                ledger,
                blocker_id,
                resolution="reattach_required_recheck",
                reason="plain resume is not user repair confirmation",
            )

        self.assertEqual(ledger["active_blockers"][blocker_id]["status"], "stopped")

    def test_reattach_required_recheck_freshens_flowguard_then_reviewer_before_clear(self) -> None:
        ledger, packet_id, blocker_id, old_flowguard_packet, old_review_packet, pm_packet = (
            self._stopped_review_blocker_after_flowguard_failure()
        )
        blocker = ledger["active_blockers"][blocker_id]

        self.assertEqual(blocker["status"], "stopped")
        self.assertEqual(ledger["packets"][packet_id]["status"], "pm_stopped")
        self.assertEqual(ledger["packets"][packet_id]["pm_stop_previous_status"], "review_blocked")

        recovery = runtime.resolve_stopped_blocker(
            ledger,
            blocker_id,
            resolution="reattach_required_recheck",
            reason="Controller repaired the FlowGuard evidence runner",
            user_requested=True,
        )

        fresh_flowguard_packet = recovery["fresh_packet_id"]
        self.assertEqual(recovery["recheck_kind"], "flowguard_check")
        self.assertNotEqual(fresh_flowguard_packet, old_flowguard_packet)
        self.assertEqual(ledger["active_blockers"][blocker_id]["status"], "awaiting_recheck")
        self.assertEqual(ledger["packets"][packet_id]["status"], "review_blocked")
        self.assertEqual(ledger["packets"][pm_packet]["status"], "superseded_after_repair")
        self.assertEqual(ledger["packets"][fresh_flowguard_packet]["repair_blocker_id"], blocker_id)
        self.assertEqual(ledger["packets"][fresh_flowguard_packet]["envelope"]["packet_kind"], "flowguard_check")
        fresh_flowguard_body = json.loads(ledger["packets"][fresh_flowguard_packet]["body"])
        self.assertEqual(ledger["packets"][fresh_flowguard_packet]["envelope"]["repair_blocker_id"], blocker_id)
        self.assertEqual(
            ledger["packets"][fresh_flowguard_packet]["envelope"]["current_handoff_contract"]["input_material_manifest"]["blocker_id"],
            blocker_id,
        )
        self.assertEqual(fresh_flowguard_body["recheck_for_blocker_id"], blocker_id)
        self.assertEqual(
            fresh_flowguard_body["current_handoff_contract"]["input_material_manifest"]["blocker_id"],
            blocker_id,
        )
        self.assertEqual(fresh_flowguard_body["generator_inputs"]["blocker_id"], blocker_id)
        self.assertEqual(fresh_flowguard_body["subject_context"]["blocker_id"], blocker_id)

        flowguard_lease = runtime.lease_agent(
            ledger,
            "flowguard_operator",
            packet_id=fresh_flowguard_packet,
        )
        runtime.assign_packet(ledger, fresh_flowguard_packet, flowguard_lease)
        runtime.ack_lease(ledger, flowguard_lease, fresh_flowguard_packet)
        open_required_result_reads(ledger, fresh_flowguard_packet, flowguard_lease)
        write_flowguard_evidence_artifact(ledger, fresh_flowguard_packet)
        fresh_flowguard_result_id = runtime.submit_result(
            ledger,
            flowguard_lease,
            fresh_flowguard_packet,
            flowguard_result_body(
                "Fresh FlowGuard evidence passes after reattachment.",
                **semantic_recheck_fields_from_packet(
                    ledger,
                    fresh_flowguard_packet,
                    blocker_id,
                ),
            ),
        )

        self.assertEqual(ledger["active_blockers"][blocker_id]["status"], "awaiting_recheck")
        self.assertEqual(ledger["results"][fresh_flowguard_result_id]["blocker_id"], blocker_id)
        fresh_review_packets = [
            packet
            for packet in ledger["packets"].values()
            if packet["packet_id"] != old_review_packet
            and packet["envelope"]["packet_kind"] == "review"
            and packet["envelope"]["subject_id"] == packet_id
            and packet["status"] == "open"
        ]
        self.assertEqual(len(fresh_review_packets), 1)
        fresh_review_packet = fresh_review_packets[0]["packet_id"]
        self.assertEqual(ledger["packets"][fresh_review_packet]["repair_blocker_id"], blocker_id)
        fresh_review_body = json.loads(ledger["packets"][fresh_review_packet]["body"])
        self.assertEqual(ledger["packets"][fresh_review_packet]["envelope"]["repair_blocker_id"], blocker_id)
        self.assertEqual(
            ledger["packets"][fresh_review_packet]["envelope"]["current_handoff_contract"]["input_material_manifest"]["blocker_id"],
            blocker_id,
        )
        self.assertEqual(fresh_review_body["recheck_for_blocker_id"], blocker_id)
        self.assertEqual(
            fresh_review_body["current_handoff_contract"]["input_material_manifest"]["blocker_id"],
            blocker_id,
        )
        self.assertEqual(fresh_review_body["subject_context"]["blocker_id"], blocker_id)
        self.assertEqual(
            fresh_review_body["flowguard_evidence_manifest"]["entries"][0]["blocker_id"],
            blocker_id,
        )

        review_lease = runtime.lease_agent(
            ledger,
            "reviewer",
            packet_id=fresh_review_packet,
        )
        runtime.assign_packet(ledger, fresh_review_packet, review_lease)
        runtime.ack_lease(ledger, review_lease, fresh_review_packet)
        open_required_result_reads(ledger, fresh_review_packet, review_lease)
        runtime.submit_result(
            ledger,
            review_lease,
            fresh_review_packet,
            review_result_body("Fresh review passes after reattachment."),
        )

        self.assertEqual(ledger["active_blockers"][blocker_id]["status"], "cleared")
        self.assertNotEqual(ledger["active_blockers"][blocker_id]["cleared_by_outcome_id"], "")

    def test_nested_pm_repair_decision_wrapper_is_rejected_and_reissued(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(
            ledger,
            worker,
            packet_id,
            role_result_body("Worker reports that PM must decide whether to stop.", decision="block", blocking=True, recommended_resolution="needs PM"),
        )
        blocker_id = next(iter(ledger["active_blockers"]))
        pm_packet = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
        pm_lease = runtime.lease_agent(ledger, "pm", agent_id="pm-wrapper", packet_id=pm_packet)
        runtime.assign_packet(ledger, pm_packet, pm_lease)
        runtime.ack_lease(ledger, pm_lease, pm_packet)
        open_required_result_reads(ledger, pm_packet, pm_lease)

        bad_result = runtime.submit_result(
            ledger,
            pm_lease,
            pm_packet,
            json.dumps({"repair_decision": {"decision": "same_node_repair", "reason": "legacy wrapper"}}),
        )

        self.assertEqual(ledger["results"][bad_result]["status"], "mechanical_contract_blocked")
        self.assertFalse(ledger["pm_repair_decisions"])
        fresh_pm_packet = runtime._ensure_pm_repair_decision_packet_for_blocker(ledger, blocker_id)

        self.assertNotEqual(fresh_pm_packet, pm_packet)
        self.assertEqual(ledger["packets"][pm_packet]["status"], "superseded_after_repair")
        body = json.loads(ledger["packets"][fresh_pm_packet]["body"])
        self.assertEqual(body["contract_family_id"], "pm_repair_decision.pm_repair_decision")
        self.assertIn("repair_decision", body["forbidden_fields_seen"])

    def test_pm_repair_decision_summary_is_not_reason_fallback(self) -> None:
        ledger, packet_id, worker = runtime_runner._base_ledger()
        runtime.ack_lease(ledger, worker, packet_id)
        runtime.submit_result(
            ledger,
            worker,
            packet_id,
            role_result_body("Worker reports that PM must handle the wrapper repair.", decision="block", blocking=True, recommended_resolution="needs PM"),
        )
        blocker_id = next(iter(ledger["active_blockers"]))
        pm_packet = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
        pm_lease = runtime.lease_agent(ledger, "pm", agent_id="pm-summary", packet_id=pm_packet)
        runtime.assign_packet(ledger, pm_packet, pm_lease)
        runtime.ack_lease(ledger, pm_lease, pm_packet)
        open_required_result_reads(ledger, pm_packet, pm_lease)

        bad_result = runtime.submit_result(
            ledger,
            pm_lease,
            pm_packet,
            json.dumps(
                {
                    "decision": "repair_current_scope",
                    "target_blocker_id": blocker_id,
                    "next_action": "repair_current_scope",
                    "summary": "legacy reason fallback must not be accepted",
                    "recommended_resolution": "same node repair",
                }
            ),
        )

        self.assertEqual(ledger["results"][bad_result]["status"], "mechanical_contract_blocked")
        self.assertEqual(ledger["results"][bad_result]["missing_required_fields"], ["reason"])
        self.assertEqual(ledger["results"][bad_result]["forbidden_fields_seen"], ["summary"])
        self.assertFalse(ledger["pm_repair_decisions"])


if __name__ == "__main__":
    unittest.main()
