"""Deterministic fake-host end-to-end rehearsal for ``flowpilot_new.py``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from . import cockpit, host, router, run_shell, runtime


StartRun = Callable[..., dict[str, Any]]

CURRENT_REPORT_FAKE_SUCCESS_FIELD_MARKERS = (
    "modeled_boundary",
    "pm_visible_summary",
    "current_evidence_refs",
    "acceptance_item_disposition",
)


def _route_plan_body() -> str:
    return json.dumps(
        {
            "schema_version": runtime.ROUTE_PLAN_SCHEMA_VERSION,
            "decision": "pass",
            "nodes": [
                {
                    "node_id": "node-001",
                    "title": "Implement target behavior",
                    "responsibility": "worker",
                    "modeled_target": "development_process",
                    "acceptance_criteria": [
                        "Target behavior is implemented in the bounded project scope.",
                        "Worker result references current changed files and evidence.",
                    ],
                    "acceptance_item_ids": ["acc-001"],
                },
                {
                    "node_id": "node-002",
                    "title": "Validate implementation evidence",
                    "responsibility": "worker",
                    "modeled_target": "model_test_alignment",
                    "acceptance_criteria": [
                        "FlowGuard and ordinary checks are current for the node.",
                        "Evidence is sufficient for independent review.",
                    ],
                    "acceptance_item_ids": ["acc-002", "acc-003"],
                },
                {
                    "node_id": "node-003",
                    "title": "Prepare final closure package",
                    "responsibility": "worker",
                    "modeled_target": "development_process",
                    "acceptance_criteria": [
                        "Final route-wide ledger can account for every effective node.",
                        "Closure evidence is body-free and reviewable from public status.",
                    ],
                    "acceptance_item_ids": [],
                },
            ],
        },
        sort_keys=True,
    )


def _terminal_supplemental_contract_for_packet(
    packet: dict[str, Any],
    ledger: dict[str, Any],
    *,
    route_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    envelope = packet.get("envelope", {}) if isinstance(packet.get("envelope"), dict) else {}
    blocker_id = str(envelope.get("subject_id") or "")
    blocker = ledger.get("active_blockers", {}).get(blocker_id)
    if not isinstance(blocker, dict):
        return {}
    supplemental_state = ledger.get("terminal_supplemental_repair", {})
    current_round = int(supplemental_state.get("current_round", 0) or 0) if isinstance(supplemental_state, dict) else 0
    contract = runtime._terminal_supplemental_repair_contract_minimal_shape(current_round + 1)
    contract["original_contract_hash"] = str(ledger.get("contract_hash") or "")
    contract["terminal_blocker_id"] = blocker_id
    contract["terminal_gap_report_result_id"] = str(blocker.get("result_id") or "")
    active_acceptance_ids = list(runtime._active_acceptance_item_ids(ledger))
    active_node_id = ""
    route_nodes = route_plan.get("nodes") if isinstance(route_plan, dict) else None
    if isinstance(route_nodes, list) and route_nodes:
        owner_node = next(
            (
                node
                for node in route_nodes
                if isinstance(node, dict) and not node.get("child_node_ids")
            ),
            route_nodes[-1] if isinstance(route_nodes[-1], dict) else {},
        )
        active_node_id = str(owner_node.get("node_id") or "")
        if isinstance(owner_node, dict):
            owner_node["acceptance_item_ids"] = active_acceptance_ids
    if not active_node_id:
        active_node_id = str(blocker.get("route_node_id") or "")
    if not active_node_id:
        active_node_id = next(
            (
                str(node_id)
                for node_id, node in ledger.get("route_nodes", {}).items()
                if isinstance(node, dict) and node.get("status") in {"active", "accepted"}
            ),
            "",
        )
    if contract.get("repair_items"):
        first_item = contract["repair_items"][0]
        first_item["owner_repair_node_id"] = active_node_id
        first_item["acceptance_item_ids"] = active_acceptance_ids[:1]
        first_item["original_goal_link"] = "Current high-standard terminal replay requirement."
        first_item["reviewer_gap"] = str(blocker.get("recommended_resolution") or "Terminal replay blocker.")
        first_item["required_repair"] = "Repair the delivered product and rerun terminal backward replay."
        contract_id = str(contract.get("contract_id") or "")
        repair_item_id = str(first_item.get("repair_item_id") or "")
        if isinstance(route_nodes, list):
            for node in route_nodes:
                if not isinstance(node, dict):
                    continue
                node["supplemental_repair_contract_ids"] = [contract_id]
                if str(node.get("node_id") or "") == active_node_id:
                    node["supplemental_repair_item_ids"] = [repair_item_id]
    return contract


def _body_for_packet(packet: dict[str, Any], ledger: dict[str, Any] | None = None) -> str:
    envelope = packet["envelope"]
    kind = envelope.get("packet_kind", "task")
    scope = envelope.get("route_scope", "")
    if kind == "task" and scope == "high_standard_contract":
        payload = runtime._packet_result_minimal_valid_shape(packet)
        payload["requirements"][0]["summary"] = "Deliver the requested FlowPilot work to a high standard."
        payload["requirements"][0]["source_user_intent"] = "sealed_startup_intake"
        payload["requirements"].append(
            {
                "requirement_id": "hsr-002",
                "classification": "high_standard_current",
                "summary": "Every node must have current evidence and review.",
                "source_user_intent": "sealed_startup_intake",
                "closure_rule": "Future owner nodes and terminal replay must close this item with current evidence.",
            }
        )
        payload["acceptance_item_registry"]["items"].append(
            {
                "acceptance_item_id": "acc-003",
                "source_type": "pm_high_standard",
                "source_requirement_ids": ["hsr-002"],
                "summary": "Every node must have current evidence and review.",
                "quality_floor": "high_quality_required",
                "future_evidence_rule": (
                    "Future node execution, FlowGuard report, Reviewer report, PM disposition, "
                    "and terminal replay must close this item."
                ),
                "status": "active",
            }
        )
        return json.dumps(payload)
    if kind == "task" and scope == "discovery":
        return json.dumps(
            {
                "decision": "pass",
                "material_sources": ["sealed_startup_intake", "current_repository"],
                "material_sufficiency": "sufficient_for_route_planning",
                "candidate_skill_inventory": ["flowguard-development-process-flow"],
            }
        )
    if kind == "task" and scope == "skill_standard":
        return json.dumps(
            {
                "decision": "pass",
                "obligations": [
                    {
                        "obligation_id": "skill-std-001",
                        "skill": "flowguard-development-process-flow",
                        "classification": "required",
                        "role_use": "flowguard_operator",
                        "use_context": "node_validation",
                        "evidence_rule": "FlowGuard operator produces current model/report evidence in its own packet.",
                    }
                ]
            }
        )
    if kind == "task" and scope == "planning":
        return _route_plan_body()
    if kind == "task" and scope == "node_acceptance_plan":
        node_id = envelope.get("route_node_id", "")
        try:
            packet_body = json.loads(packet.get("body") or "{}")
        except json.JSONDecodeError:
            packet_body = {}
        acceptance_item_ids = [
            str(item)
            for item in packet_body.get("acceptance_item_ids", [])
            if str(item)
        ] if isinstance(packet_body, dict) and isinstance(packet_body.get("acceptance_item_ids"), list) else []
        acceptance_item_projection = [
            {
                "acceptance_item_id": item_id,
                "status_for_this_node": "planned_for_current_node",
                "future_evidence_rule": "Current node evidence plus FlowGuard, Reviewer, PM disposition, and terminal replay closure.",
            }
            for item_id in acceptance_item_ids
        ]
        return json.dumps(
            {
                "decision": "pass",
                "node_context_package": {
                    "purpose": "Complete the current route node with bounded worker execution, FlowGuard checks, review, and validation.",
                    "acceptance_criteria": [
                        "worker result satisfies the node packet",
                        "plan-stage review checks current inputs without future-stage evidence",
                        "node-plan Reviewer, post-result FlowGuard, and final Reviewer evidence are current",
                        "reviewer independently challenges the node outcome",
                    ],
                    "relevant_references": ["route node contract", "high standard contract", "runtime ledger"],
                    "known_risks": ["existence-only evidence", "stale generation", "review without active inspection"],
                    "acceptance_item_projection": acceptance_item_projection,
                },
            }
        )
    if kind == "task" and scope == "parent_backward_replay":
        return json.dumps(
            {
                "pm_visible_summary": ["Parent backward replay composes current child results."],
                "parent_node_id": envelope.get("route_node_id", "") or "parent-node",
                "child_node_ids": ["child-node"],
                "child_evidence_refs": ["child-result"],
                "composition_decision": "pass",
                "blockers": [],
            }
        )
    family_id = runtime._packet_result_family_id(packet)
    if family_id == "review.terminal_backward_replay":
        payload = runtime._packet_result_minimal_valid_shape(packet)
        try:
            packet_body = json.loads(packet.get("body") or "{}")
        except json.JSONDecodeError:
            packet_body = {}
        segment_targets = packet_body.get("segment_targets") if isinstance(packet_body, dict) else []
        if isinstance(segment_targets, list) and segment_targets:
            payload["route_segment_replay"] = [
                {
                    "segment_id": str(target.get("segment_id") or f"segment-{index}"),
                    "segment_kind": str(target.get("segment_kind") or "route_segment"),
                    "status": "closed",
                    "basis": str(target.get("summary") or target.get("segment_id") or "current segment"),
                }
                for index, target in enumerate(segment_targets, start=1)
                if isinstance(target, dict)
            ]
            acceptance_rows = [
                {
                    "id": str(target.get("segment_id")).removeprefix("acceptance-item:"),
                    "status": "closed",
                    "basis": str(target.get("summary") or target.get("segment_id") or "current acceptance item"),
                }
                for target in segment_targets
                if isinstance(target, dict) and str(target.get("segment_id") or "").startswith("acceptance-item:")
            ]
            if acceptance_rows:
                payload["acceptance_item_closure"] = acceptance_rows
        return json.dumps(payload, sort_keys=True)
    if family_id.startswith("flowguard_check."):
        payload = runtime._packet_result_minimal_valid_shape(packet)
        payload.update(_semantic_recheck_payload_for_packet(packet))
        payload.update(_subject_artifact_consumption_payload_for_packet(packet))
        return json.dumps(payload, sort_keys=True)
    if family_id == "review.any_current_subject":
        return json.dumps(runtime._packet_result_minimal_valid_shape(packet), sort_keys=True)
    if family_id == "pm_repair_decision.pm_repair_decision":
        payload = runtime._packet_result_minimal_valid_shape(packet)
        packet_body: dict[str, Any] = {}
        if ledger is not None:
            try:
                packet_body = json.loads(packet.get("body") or "{}")
            except json.JSONDecodeError:
                packet_body = {}
        if isinstance(packet_body, dict) and isinstance(packet_body.get("minimal_valid_shape"), dict):
            payload = json.loads(json.dumps(packet_body["minimal_valid_shape"]))
        payload["reason"] = "fake PM repairs the current terminal blocker and requires a fresh replay"
        if ledger is not None and runtime._terminal_supplemental_repair_required(
            ledger,
            packet,
            str(payload.get("decision") or ""),
        ):
            route_plan = payload.get("route_plan") if isinstance(payload.get("route_plan"), dict) else None
            payload["supplemental_repair_contract"] = _terminal_supplemental_contract_for_packet(
                packet,
                ledger,
                route_plan=route_plan,
            )
        return json.dumps(payload, sort_keys=True)
    if family_id == "pm_flowguard_acceptance.pm_flowguard_acceptance":
        payload = runtime._packet_result_minimal_valid_shape(packet)
        try:
            packet_body = json.loads(packet.get("body") or "{}")
        except json.JSONDecodeError:
            packet_body = {}
        if isinstance(packet_body, dict) and packet_body.get("flowguard_result_id"):
            payload["accepted_flowguard_result_id"] = str(packet_body["flowguard_result_id"])
        payload["flowguard_absorption"] = "fake PM absorbed the current FlowGuard report before Reviewer review"
        return json.dumps(payload, sort_keys=True)
    if kind == "pm_disposition":
        payload = runtime._packet_result_minimal_valid_shape(packet)
        try:
            packet_body = json.loads(packet.get("body") or "{}")
        except json.JSONDecodeError:
            packet_body = {}
        if isinstance(packet_body, dict) and isinstance(packet_body.get("minimal_valid_shape"), dict):
            payload = dict(packet_body["minimal_valid_shape"])
        payload["reason"] = "fake PM accepts current node after absorbing current evidence"
        return json.dumps(payload, sort_keys=True)
    return json.dumps(
        {
            "decision": "pass",
            "pm_visible_summary": [f"fake {kind} result for packet {packet['packet_id']}"],
            "current_evidence_refs": [f"fake-current-evidence:{packet['packet_id']}"],
        },
        sort_keys=True,
    )


def _terminal_replay_block_body_for_packet(packet: dict[str, Any], ledger: dict[str, Any] | None = None) -> str:
    payload = json.loads(_body_for_packet(packet, ledger=ledger))
    blocker_text = "Delivered product signposting does not match the current accepted route."
    segments = payload.get("route_segment_replay")
    if isinstance(segments, list) and segments:
        first_segment = segments[0]
        if isinstance(first_segment, dict):
            first_segment["status"] = "blocked"
            first_segment["basis"] = blocker_text
    blocker = {
        "blocker_id": "terminal-blocker-delivered-product",
        "blocker_class": "terminal_closure",
        "recommended_resolution": "Repair delivered-product signposting and restart terminal replay.",
        "summary": blocker_text,
    }
    payload["passed"] = False
    payload["blockers"] = [blocker]
    payload["final_blockers"] = [
        {
            **blocker,
        }
    ]
    return json.dumps(payload, sort_keys=True)


def _fault_body_for_packet(packet: dict[str, Any], ledger: dict[str, Any] | None = None) -> str:
    family_id = runtime._packet_result_family_id(packet)
    if family_id == "task.high_standard_contract":
        return json.dumps(
            {
                "overall_contract": "old contract wrapper must be rejected",
                "contract_rows": [],
            },
            sort_keys=True,
        )
    if family_id == "task.skill_standard":
        return json.dumps(
            {
                "decision": "pass",
                "selected_skills": ["flowguard-development-process-flow"],
            },
            sort_keys=True,
        )
    if family_id == "task.node_acceptance_plan":
        return json.dumps(
            {
                "decision": "pass",
                "repair_policy": "repair_scope_replacement_default",
            },
            sort_keys=True,
        )
    if family_id == "pm_disposition.node_pm_disposition":
        return json.dumps(
            {
                "decision": "accept",
                "summary": "old PM disposition summary must be rejected as a reason alias",
            },
            sort_keys=True,
        )
    if family_id.startswith("flowguard_check.") or family_id in {
        "review.any_current_subject",
        "review.terminal_backward_replay",
    }:
        return json.dumps(
            {
                "decision": "pass",
                "pm_visible_summary": ["old generic result body must be rejected for this packet family"],
            },
            sort_keys=True,
        )
    return _body_for_packet(packet, ledger=ledger)


def _consistency_fault_body_for_packet(packet: dict[str, Any], ledger: dict[str, Any] | None = None) -> str:
    family_id = runtime._packet_result_family_id(packet)
    if family_id.startswith("flowguard_check."):
        payload = runtime._packet_result_minimal_valid_shape(packet)
        payload.update(_semantic_recheck_payload_for_packet(packet))
        payload.update(_subject_artifact_consumption_payload_for_packet(packet))
        payload["pm_visible_summary"] = [
            "current-shaped FlowGuard result must be rejected because hard child evidence blocks."
        ]
        payload["passed"] = True
        payload["evidence_consistency"] = {
            "self_check_passed": True,
            "child_reports_all_passed": False,
            "blocking_child_reports": [
                {
                    "report_path": "evidence/flowguard/current/model_test_alignment_report.json",
                    "decision": "missing_code_contract",
                }
            ],
            "hard_evidence_decision": "missing_code_contract",
        }
        return json.dumps(payload, sort_keys=True)
    return _fault_body_for_packet(packet, ledger=ledger)


def _semantic_recheck_payload_for_packet(packet: dict[str, Any]) -> dict[str, Any]:
    minimal_shape = runtime._packet_result_minimal_valid_shape(packet)
    semantic_shape = minimal_shape.get("semantic_recheck") if isinstance(minimal_shape, dict) else None
    if isinstance(semantic_shape, dict):
        return {"semantic_recheck": semantic_shape}
    try:
        packet_body = json.loads(packet.get("body") or "{}")
    except json.JSONDecodeError:
        packet_body = {}
    contract = packet_body.get("semantic_recheck_contract") if isinstance(packet_body, dict) else None
    if not isinstance(contract, dict) or contract.get("subject_bound_required") is not True:
        return {}
    return {
        "semantic_recheck": {
            "blocker_id": str(contract.get("blocker_id") or ""),
            "subject_result_consumed": True,
            "subject_bound_semantic_coverage": True,
            "coverage_boundary": "subject_bound_semantic",
            "consumed_authorized_result_read_ids": ["subject_result_for_flowguard_check"],
            "consumed_repair_obligation_ids": list(contract.get("must_consume_repair_obligation_ids") or []),
        }
    }


def _subject_artifact_consumption_payload_for_packet(packet: dict[str, Any]) -> dict[str, Any]:
    minimal_shape = runtime._packet_result_minimal_valid_shape(packet)
    consumed_shape = minimal_shape.get("subject_artifacts_consumed") if isinstance(minimal_shape, dict) else None
    if isinstance(consumed_shape, list):
        return {"subject_artifacts_consumed": consumed_shape}
    try:
        packet_body = json.loads(packet.get("body") or "{}")
    except json.JSONDecodeError:
        packet_body = {}
    raw_artifacts = packet_body.get("required_subject_artifacts") if isinstance(packet_body, dict) else None
    if not isinstance(raw_artifacts, list) or not raw_artifacts:
        return {}
    consumed: list[dict[str, str]] = []
    for raw_artifact in raw_artifacts:
        if not isinstance(raw_artifact, dict):
            continue
        artifact_id = str(raw_artifact.get("artifact_id") or "")
        if not artifact_id:
            continue
        consumed.append(
            {
                "artifact_id": artifact_id,
                "consumed": "yes",
            }
        )
    return {"subject_artifacts_consumed": consumed} if consumed else {}


def _write_flowguard_evidence_artifact_for_packet(
    ledger: dict[str, Any],
    packet: dict[str, Any],
    *,
    decision: str,
    mode: str = "valid",
) -> Path | None:
    path = runtime._flowguard_packet_evidence_artifact_path(ledger, packet)
    if path is None:
        return None
    if mode == "missing":
        return path
    if mode == "wrong_path":
        path = path.parent.parent / f"{packet['packet_id']}-wrong" / runtime._FLOWGUARD_FORMAL_ARTIFACT_ID
    path.parent.mkdir(parents=True, exist_ok=True)
    if mode == "invalid_json":
        path.write_text("{not: strict json", encoding="utf-8")
        return path
    report: dict[str, Any] = {
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
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def run_fake_e2e(
    root: Path,
    *,
    run_id: str | None,
    startup_text: str,
    start_run: StartRun,
    inject_contract_faults: bool = False,
    inject_consistency_faults: bool = False,
    inject_artifact_consistency_faults: bool = False,
    flowguard_artifact_fault_mode: str = "",
    inject_terminal_replay_blocker: bool = False,
    repair_terminal_replay_blocker: bool = False,
) -> dict[str, Any]:
    start_result = start_run(
        root,
        run_id=run_id,
        headless_startup_text=startup_text,
        require_formal_ui=False,
    )
    shell = run_shell.load_run_shell(root, run_id=start_result["run"]["run_id"])
    ledger = run_shell.load_run_ledger(shell)

    def complete_leased_packet(packet_id: str, *, agent_id: str, body: str) -> tuple[str, str]:
        packet = ledger["packets"][packet_id]
        responsibility = packet["envelope"]["responsibility"]
        lease_id = host.lease_responsibility(
            ledger,
            responsibility,
            host_kind="fake",
            agent_id=agent_id,
            packet_id=packet_id,
            scope="e2e",
        )
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)
        runtime.open_authorized_input_materials_for_role(ledger, packet_id, lease_id)
        result_id = host.submit_host_result(ledger, lease_id, packet_id, body)
        return lease_id, result_id

    completed_packets: list[dict[str, str]] = []
    folded_boundaries: list[dict[str, Any]] = []
    injected_fault_families: set[str] = set()
    injected_consistency_fault_families: set[str] = set()
    injected_artifact_consistency_fault_families: set[str] = set()
    injected_flowguard_artifact_fault_modes: list[dict[str, str]] = []
    injected_terminal_replay_blockers: list[dict[str, str]] = []
    mechanical_contract_blocks: list[dict[str, Any]] = []
    for index in range(80):
        boundary = runtime.run_until_wait(ledger)
        folded_boundaries.append(boundary)
        action_json = boundary["next_action"]
        action_type = str(action_json.get("action_type") or "")
        if action_type == "terminal_complete":
            break
        if action_type != "dispatch_current_role":
            raise runtime.BlackBoxRuntimeError(f"fake e2e cannot satisfy next action: {action_json}")
        packet_id = str(action_json.get("subject_id") or "")
        packet = ledger["packets"][packet_id]
        kind = packet["envelope"].get("packet_kind", "task")
        family_id = runtime._packet_result_family_id(packet)
        should_fault = inject_contract_faults and family_id in {
            "task.high_standard_contract",
            "task.skill_standard",
            "task.node_acceptance_plan",
            "flowguard_check.post_result",
            "review.any_current_subject",
            "review.terminal_backward_replay",
            "pm_flowguard_acceptance.pm_flowguard_acceptance",
            "pm_disposition.node_pm_disposition",
        } and family_id not in injected_fault_families
        should_consistency_fault = (
            inject_consistency_faults
            and family_id == "flowguard_check.post_result"
            and family_id not in injected_consistency_fault_families
        )
        should_artifact_consistency_fault = (
            (inject_artifact_consistency_faults or bool(flowguard_artifact_fault_mode))
            and family_id == "flowguard_check.post_result"
            and family_id not in injected_artifact_consistency_fault_families
        )
        should_terminal_replay_block = (
            inject_terminal_replay_blocker
            and family_id == "review.terminal_backward_replay"
            and not injected_terminal_replay_blockers
        )
        if should_terminal_replay_block:
            body = _terminal_replay_block_body_for_packet(packet, ledger=ledger)
        elif should_consistency_fault:
            body = _consistency_fault_body_for_packet(packet, ledger=ledger)
            injected_consistency_fault_families.add(family_id)
        elif should_artifact_consistency_fault:
            body = _body_for_packet(packet, ledger=ledger)
            injected_artifact_consistency_fault_families.add(family_id)
        elif should_fault:
            body = _fault_body_for_packet(packet, ledger=ledger)
            injected_fault_families.add(family_id)
        else:
            body = _body_for_packet(packet, ledger=ledger)
        if family_id.startswith("flowguard_check."):
            mode = "valid"
            artifact_decision = "pass"
            if should_artifact_consistency_fault:
                mode = flowguard_artifact_fault_mode or "blocked_decision"
                if mode == "blocked_decision":
                    artifact_decision = "missing_code_contract"
                elif mode == "wrong_decision":
                    artifact_decision = "__invalid_option__"
                else:
                    artifact_decision = "pass"
                injected_flowguard_artifact_fault_modes.append(
                    {
                        "packet_id": packet_id,
                        "mode": mode,
                    }
                )
            _write_flowguard_evidence_artifact_for_packet(
                ledger,
                packet,
                decision=artifact_decision,
                mode=mode,
            )
        lease_id, result_id = complete_leased_packet(
            packet_id,
            agent_id=f"fake-{kind}-{index}",
            body=body,
        )
        result = ledger["results"][result_id]
        if result.get("status") == "mechanical_contract_blocked":
            mechanical_contract_blocks.append(
                {
                    "packet_id": packet_id,
                    "result_id": result_id,
                    "contract_family_id": str(result.get("contract_family_id") or ""),
                    "missing_required_fields": list(result.get("missing_required_fields") or []),
                    "forbidden_fields_seen": list(result.get("forbidden_fields_seen") or []),
                    "quarantine_reason": str(result.get("quarantine_reason") or ""),
                }
            )
        completed_packets.append({"packet_id": packet_id, "packet_kind": kind, "lease_id": lease_id, "result_id": result_id})
        if should_terminal_replay_block:
            injected_terminal_replay_blockers.append(
                {
                    "packet_id": packet_id,
                    "result_id": result_id,
                    "status": str(result.get("status") or ""),
                }
            )
            if not repair_terminal_replay_blocker:
                break
    else:
        raise runtime.BlackBoxRuntimeError("fake e2e exceeded packet completion budget")

    closure = ledger.get("closure") or {"decision": "not_attempted"}
    run_shell.save_run_ledger(shell, ledger)
    return {
        "ok": closure["decision"] == "complete",
        "mode": "rehearsal",
        "run": shell.to_json(),
        "completed_packets": completed_packets,
        "mechanical_contract_blocks": mechanical_contract_blocks,
        "injected_fault_families": sorted(injected_fault_families),
        "injected_consistency_fault_families": sorted(injected_consistency_fault_families),
        "injected_artifact_consistency_fault_families": sorted(injected_artifact_consistency_fault_families),
        "injected_flowguard_artifact_fault_modes": injected_flowguard_artifact_fault_modes,
        "injected_terminal_replay_blockers": injected_terminal_replay_blockers,
        "active_blockers": runtime._copy_jsonable(ledger.get("active_blockers") or {}),
        "folded_boundaries": folded_boundaries,
        "accepted_node_ids": [
            node_id for node_id, node in ledger.get("route_nodes", {}).items() if node.get("status") == "accepted"
        ],
        "final_route_wide_gate_ledger": ledger.get("final_route_wide_gate_ledger"),
        "closure": closure,
        "next_action": router.router_next_action(ledger).to_json(),
        "lifecycle_guard": ledger.get("lifecycle_guard", {}),
        "foreground_duty": ledger.get("foreground_duty", {}),
        "final_return_preflight": runtime.final_return_preflight(
            ledger,
            guard=ledger.get("lifecycle_guard") if isinstance(ledger.get("lifecycle_guard"), dict) else None,
        ),
        "status": cockpit.render_status(ledger),
    }
