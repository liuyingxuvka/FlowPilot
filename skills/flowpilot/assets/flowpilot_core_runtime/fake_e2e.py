"""Deterministic fake-host end-to-end rehearsal for ``flowpilot_new.py``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from . import cockpit, host, router, run_shell, runtime


StartRun = Callable[..., dict[str, Any]]


def _route_plan_body() -> str:
    return json.dumps(
        {
            "schema_version": runtime.ROUTE_PLAN_SCHEMA_VERSION,
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
                },
            ],
        },
        sort_keys=True,
    )


def _body_for_packet(packet: dict[str, Any]) -> str:
    envelope = packet["envelope"]
    kind = envelope.get("packet_kind", "task")
    scope = envelope.get("route_scope", "")
    if kind == "task" and scope == "high_standard_contract":
        return json.dumps(
            {
                "requirements": [
                    {
                        "requirement_id": "hsr-001",
                        "classification": "hard_current",
                        "summary": "Deliver the requested FlowPilot work to a high standard.",
                        "closure_blocking": True,
                    },
                    {
                        "requirement_id": "hsr-002",
                        "classification": "high_standard_current",
                        "summary": "Every node must have current evidence and review.",
                        "closure_blocking": True,
                    },
                ]
            }
        )
    if kind == "task" and scope == "discovery":
        return json.dumps(
            {
                "material_sources": ["sealed_startup_intake", "current_repository"],
                "material_sufficiency": "sufficient_for_route_planning",
                "local_skill_inventory": ["flowguard-development-process-flow"],
                "candidate_only_skill_policy": True,
            }
        )
    if kind == "task" and scope == "skill_standard":
        return json.dumps(
            {
                "obligations": [
                    {
                        "obligation_id": "skill-std-001",
                        "skill": "flowguard-development-process-flow",
                        "classification": "required",
                        "role_use": "flowguard_operator",
                        "use_context": "node_validation",
                        "evidence_required": "current-run FlowGuard work order",
                        "closure_blocking": True,
                    }
                ]
            }
        )
    if kind == "task" and scope == "planning":
        return _route_plan_body()
    if kind == "task" and scope == "node_acceptance_plan":
        node_id = envelope.get("route_node_id", "")
        return json.dumps(
            {
                "route_node_id": node_id,
                "proof_obligations": ["implementation evidence", "FlowGuard evidence", "review", "validation"],
                "repair_policy": "same_node_repair_default",
                "low_quality_success_risks": ["existence-only evidence", "missing skill evidence"],
                "node_context_package": {
                    "node_id": node_id,
                    "purpose": "Complete the current route node with bounded worker execution, FlowGuard checks, review, and validation.",
                    "acceptance_criteria": [
                        "worker result satisfies the node packet",
                        "pre-work and post-result FlowGuard evidence are current",
                        "reviewer independently challenges the node outcome",
                    ],
                    "relevant_references": ["route node contract", "high standard contract", "runtime ledger"],
                    "evidence_targets": ["worker result body", "FlowGuard report", "reviewer report", "validation output"],
                    "inspection_targets": ["changed files", "command output", "model artifacts", "runtime ledger"],
                    "known_risks": ["existence-only evidence", "stale generation", "review without active inspection"],
                    "flowguard_targets": ["development-process route", "model-test alignment where applicable"],
                    "reviewer_starting_points": ["worker result", "node context package", "FlowGuard reports", "validation evidence"],
                },
            }
        )
    if kind == "task" and scope == "parent_backward_replay":
        return json.dumps(
            {
                "route_node_id": envelope.get("route_node_id", ""),
                "decision": "pass",
                "composition_checked": True,
            }
        )
    if kind == "pm_disposition":
        return json.dumps({"decision": "accept", "reason": "fake PM accepts current node"})
    return f"SEALED_RESULT_BODY: fake {kind} result for packet {packet['packet_id']}"


def run_fake_e2e(
    root: Path,
    *,
    run_id: str | None,
    startup_text: str,
    start_run: StartRun,
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
        result_id = host.submit_host_result(ledger, lease_id, packet_id, body)
        return lease_id, result_id

    completed_packets: list[dict[str, str]] = []
    folded_boundaries: list[dict[str, Any]] = []
    for index in range(80):
        boundary = runtime.run_until_wait(ledger)
        folded_boundaries.append(boundary)
        action_json = boundary["next_action"]
        action_type = str(action_json.get("action_type") or "")
        if action_type == "terminal_complete":
            break
        if action_type != "lease_agent":
            raise runtime.BlackBoxRuntimeError(f"fake e2e cannot satisfy next action: {action_json}")
        packet_id = str(action_json.get("subject_id") or "")
        packet = ledger["packets"][packet_id]
        kind = packet["envelope"].get("packet_kind", "task")
        lease_id, result_id = complete_leased_packet(
            packet_id,
            agent_id=f"fake-{kind}-{index}",
            body=_body_for_packet(packet),
        )
        completed_packets.append({"packet_id": packet_id, "packet_kind": kind, "lease_id": lease_id, "result_id": result_id})
    else:
        raise runtime.BlackBoxRuntimeError("fake e2e exceeded packet completion budget")

    closure = ledger.get("closure") or {"decision": "not_attempted"}
    run_shell.save_run_ledger(shell, ledger)
    return {
        "ok": closure["decision"] == "complete",
        "mode": "rehearsal",
        "run": shell.to_json(),
        "completed_packets": completed_packets,
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
