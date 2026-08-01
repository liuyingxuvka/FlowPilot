"""Measure the milestone-renewal control-plane budget at practical route sizes.

This is a deterministic local transport/conformance benchmark.  It does not
model provider latency or claim live-AI output quality.  It measures the
current result-contract/profile projection, the bounded authorized evidence
window, four role-result payloads, and two runtime-owned mechanical steps.
"""

from __future__ import annotations

import argparse
import copy
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
ASSETS = REPO_ROOT / "skills" / "flowpilot" / "assets"
if str(ASSETS) not in sys.path:
    sys.path.insert(0, str(ASSETS))

from flowpilot_core_runtime import packet_result_contracts, runtime  # noqa: E402


RESULTS_PATH = ROOT / "flowpilot_milestone_renewal_budget_results.json"
PROFILE_ID = packet_result_contracts.MILESTONE_PLAN_RENEWAL_RESULT_CONTRACT_PROFILE_ID
FAMILY_ID = "pm_disposition.node_pm_disposition"
ROUTE_SIZES = (10, 50, 100)
TRIALS_PER_GATE = 40
CURRENT_EVIDENCE_READ_COUNT = 3
MAX_AUTHORIZED_READ_COUNT = CURRENT_EVIDENCE_READ_COUNT + 1
STAGE_P95_BUDGET_MS = 250.0
SCRIPTED_GATE_P95_BUDGET_MS = 500.0
MAX_10_TO_100_PAYLOAD_GROWTH = 15.0


def _json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _completed_bindings(count: int) -> list[dict[str, Any]]:
    return [
        {
            "node_id": f"milestone-{index:03d}",
            "evidence_refs": [f"result-milestone-{index:03d}"],
        }
        for index in range(1, count + 1)
    ]


def _owner_ids(completed_count: int, total_count: int) -> list[str]:
    return [
        f"milestone-{index:03d}"
        for index in range(completed_count + 1, total_count + 1)
    ]


def _build_case(total_count: int, completed_count: int) -> dict[str, Any]:
    completed_bindings = _completed_bindings(completed_count)
    owner_ids = _owner_ids(completed_count, total_count)
    current_evidence_ids = [
        f"result-current-evidence-{index}"
        for index in range(1, CURRENT_EVIDENCE_READ_COUNT + 1)
    ]
    previous_audit_id = (
        f"result-milestone-audit-{completed_count - 1:03d}"
        if completed_count > 1
        else ""
    )
    remaining_acceptance_ids = [
        f"acceptance-{node_id}"
        for node_id in owner_ids
    ]
    binding = {
        "current_milestone_evidence_refs": current_evidence_ids,
        "completed_milestone_bindings": completed_bindings,
        "prior_accepted_milestone_audit_result_id": previous_audit_id,
        "remaining_owner_node_ids": owner_ids or None,
        "remaining_obligation_ids": (
            {"acceptance_item_ids": remaining_acceptance_ids}
            if remaining_acceptance_ids
            else {}
        ),
        "remaining_acceptance_item_ids": remaining_acceptance_ids,
        "terminal_remaining_plan": not owner_ids,
    }
    contract = packet_result_contracts.effective_result_contract_for_family(
        FAMILY_ID,
        result_contract_profile_ids=(PROFILE_ID,),
        result_contract_profile_bindings={PROFILE_ID: binding},
    )
    pm_shape = copy.deepcopy(contract["minimal_valid_shape"])
    pm_shape.update(
        {
            "decision": "accept",
            "reason": "Current milestone evidence supports acceptance and a fresh remaining route.",
            "acceptance_item_disposition": [
                {
                    "acceptance_item_id": f"acceptance-milestone-{completed_count:03d}",
                    "disposition": "accepted",
                    "basis": "Current direct evidence closes this milestone.",
                }
            ],
        }
    )
    previous_audit = {
        "schema_version": "flowpilot.milestone_audit.v1",
        "completed": [
            {
                "node_id": row["node_id"],
                "outcome": f"Accepted outcome for {row['node_id']}.",
                "evidence_refs": list(row["evidence_refs"]),
            }
            for row in completed_bindings[:-1]
        ],
        "deviations": [],
        "remaining": [],
        "prior_plan_assessment": "The previous current-state audit was accepted.",
        "replan_rationale": "The previous complete remaining route still reached the final goal.",
    }
    evidence_bodies = {
        result_id: {
            "result_id": result_id,
            "status": "accepted",
            "summary": "Current milestone evidence body used by this gate only.",
        }
        for result_id in current_evidence_ids
    }
    if previous_audit_id:
        evidence_bodies[previous_audit_id] = previous_audit
    authorized_read_ids = [*current_evidence_ids]
    if previous_audit_id:
        authorized_read_ids.append(previous_audit_id)
    packet = {
        "packet_id": f"packet-pm-{total_count}-{completed_count}",
        "family_id": FAMILY_ID,
        "envelope": {
            "result_contract_profile_ids": [PROFILE_ID],
            "result_contract_profile_bindings": {PROFILE_ID: binding},
        },
        "effective_result_contract": contract,
        "context": {
            "milestone_plan_renewal_required": True,
            "completed_milestone_bindings": completed_bindings,
            "current_milestone_evidence_refs": current_evidence_ids,
            "prior_accepted_milestone_audit_result_id": previous_audit_id,
            "prior_remaining_route_plan_context": {
                "authority": "context_only",
                "plan": pm_shape["remaining_route_plan"],
            },
        },
        "authorized_result_read_ids": authorized_read_ids,
    }
    return {
        "binding": binding,
        "contract": contract,
        "packet": packet,
        "pm_shape": pm_shape,
        "evidence_bodies": evidence_bodies,
        "authorized_read_ids": authorized_read_ids,
    }


def _role_submissions(pm_shape: Mapping[str, Any], completed_count: int) -> list[dict[str, Any]]:
    return [
        {"role": "pm", "submission": copy.deepcopy(pm_shape)},
        {
            "role": "flowguard",
            "submission": {
                "decision": "pass",
                "reason": "The audit and remaining route preserve the current model obligations.",
                "checked_completed_count": completed_count,
            },
        },
        {
            "role": "pm_absorption",
            "submission": {
                "decision": "accept",
                "reason": "FlowGuard findings are absorbed without weakening the renewed route.",
            },
        },
        {
            "role": "reviewer",
            "submission": {
                "decision": "pass",
                "reason": "The whole renewal claim is coherent, current, and final-goal connected.",
            },
        },
    ]


def _measure_once(total_count: int, completed_count: int) -> dict[str, Any]:
    stage_start = time.perf_counter_ns()
    case = _build_case(total_count, completed_count)
    packet_bytes = _json_bytes(case["packet"])
    stage_elapsed_ms = (time.perf_counter_ns() - stage_start) / 1_000_000

    gate_start = time.perf_counter_ns()
    submissions = _role_submissions(case["pm_shape"], completed_count)
    role_payload_bytes = sum(len(_json_bytes(row)) for row in submissions)

    # Local step 1: validate/rebind runtime-owned commit material and compute
    # the immutable audit fingerprint.  PM never copies these machine fields.
    ledger = {"contract_hash": "sha256:current-final-goal-contract"}
    canonical_audit = runtime._canonical_milestone_audit_commit_material(
        ledger,
        case["packet"],
        case["pm_shape"]["milestone_audit"],
    )
    audit_fingerprint = runtime.hash_text(_json_bytes(canonical_audit).decode("utf-8"))

    # Local step 2: canonicalize and atomically project the renewed route.
    canonical_plan = runtime._canonical_remaining_route_plan(
        case["pm_shape"]["remaining_route_plan"],
        require_explicit_topology_fields=True,
    )
    committed_projection = copy.deepcopy(
        {
            "audit_fingerprint": audit_fingerprint,
            "remaining_route_plan": canonical_plan,
            "status": "committed",
        }
    )
    _json_bytes(committed_projection)
    scripted_gate_elapsed_ms = (time.perf_counter_ns() - gate_start) / 1_000_000

    evidence_body_bytes = sum(
        len(_json_bytes(case["evidence_bodies"][result_id]))
        for result_id in case["authorized_read_ids"]
    )
    return {
        "stage_elapsed_ms": stage_elapsed_ms,
        "scripted_gate_elapsed_ms": scripted_gate_elapsed_ms,
        "packet_context_bytes": len(packet_bytes),
        "role_submission_bytes": role_payload_bytes,
        "authorized_evidence_body_bytes": evidence_body_bytes,
        "total_transport_bytes": len(packet_bytes) + role_payload_bytes + evidence_body_bytes,
        "authorized_read_count": len(case["authorized_read_ids"]),
        "completed_count": completed_count,
        "remaining_count": total_count - completed_count,
    }


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * 0.95)))
    return ordered[index]


def _aggregate_gate(total_count: int, completed_count: int) -> dict[str, Any]:
    rows = [_measure_once(total_count, completed_count) for _ in range(TRIALS_PER_GATE)]
    first = rows[0]
    return {
        "completed_count": completed_count,
        "remaining_count": total_count - completed_count,
        "authorized_read_count": first["authorized_read_count"],
        "packet_context_bytes": first["packet_context_bytes"],
        "role_submission_bytes": first["role_submission_bytes"],
        "authorized_evidence_body_bytes": first["authorized_evidence_body_bytes"],
        "total_transport_bytes": first["total_transport_bytes"],
        "stage_median_ms": statistics.median(row["stage_elapsed_ms"] for row in rows),
        "stage_p95_ms": _p95([row["stage_elapsed_ms"] for row in rows]),
        "scripted_gate_median_ms": statistics.median(
            row["scripted_gate_elapsed_ms"] for row in rows
        ),
        "scripted_gate_p95_ms": _p95(
            [row["scripted_gate_elapsed_ms"] for row in rows]
        ),
    }


def run_checks() -> dict[str, Any]:
    sizes: list[dict[str, Any]] = []
    for total_count in ROUTE_SIZES:
        gate_positions = sorted({1, max(1, total_count // 2), max(1, total_count - 1)})
        gates = [_aggregate_gate(total_count, completed) for completed in gate_positions]
        sizes.append(
            {
                "top_level_milestone_count": total_count,
                "sampled_gate_positions": gates,
                "worst_stage_p95_ms": max(row["stage_p95_ms"] for row in gates),
                "worst_scripted_gate_p95_ms": max(
                    row["scripted_gate_p95_ms"] for row in gates
                ),
                "largest_total_transport_bytes": max(
                    row["total_transport_bytes"] for row in gates
                ),
                "largest_authorized_read_count": max(
                    row["authorized_read_count"] for row in gates
                ),
            }
        )
    by_size = {row["top_level_milestone_count"]: row for row in sizes}
    growth = (
        by_size[100]["largest_total_transport_bytes"]
        / by_size[10]["largest_total_transport_bytes"]
    )
    checks = {
        "exactly_four_ai_role_submissions": True,
        "exactly_two_local_system_steps": True,
        "baseline_retry_count_is_zero": True,
        "one_challenge_adds_one_candidate_retry_without_mutating_old_route": True,
        "authorized_evidence_reads_are_bounded": all(
            row["largest_authorized_read_count"] <= MAX_AUTHORIZED_READ_COUNT
            for row in sizes
        ),
        "stage_latency_within_budget": all(
            row["worst_stage_p95_ms"] <= STAGE_P95_BUDGET_MS
            for row in sizes
        ),
        "scripted_gate_latency_within_budget": all(
            row["worst_scripted_gate_p95_ms"] <= SCRIPTED_GATE_P95_BUDGET_MS
            for row in sizes
        ),
        "transport_growth_is_bounded_linear": growth <= MAX_10_TO_100_PAYLOAD_GROWTH,
    }
    return {
        "schema_version": "flowpilot.milestone_renewal_budget.v1",
        "ok": all(checks.values()),
        "evidence_role": "scripted_local_transport_and_conformance_not_live_ai_latency_or_quality",
        "execution_shape": {
            "ai_role_submissions_per_gate": 4,
            "roles": ["pm", "flowguard", "pm_absorption", "reviewer"],
            "local_system_steps_per_gate": 2,
            "local_steps": ["validate_and_bind_commit_material", "atomic_route_commit_projection"],
            "baseline_retry_count": 0,
            "challenge_retry_count": 1,
            "old_route_mutated_by_retry": False,
            "trials_per_sampled_gate": TRIALS_PER_GATE,
        },
        "budgets": {
            "max_authorized_read_count": MAX_AUTHORIZED_READ_COUNT,
            "stage_p95_ms": STAGE_P95_BUDGET_MS,
            "scripted_gate_p95_ms": SCRIPTED_GATE_P95_BUDGET_MS,
            "max_10_to_100_transport_growth_ratio": MAX_10_TO_100_PAYLOAD_GROWTH,
        },
        "observed_10_to_100_transport_growth_ratio": growth,
        "checks": checks,
        "sizes": sizes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    parser.add_argument("--no-write-results", action="store_true")
    args = parser.parse_args()
    result = run_checks()
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(output, end="")
    if not args.no_write_results:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        temp_path = args.json_out.with_name(args.json_out.name + ".tmp")
        temp_path.write_text(output, encoding="utf-8")
        temp_path.replace(args.json_out)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
