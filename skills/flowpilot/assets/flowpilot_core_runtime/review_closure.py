"""Review and closure facade for complete-system callers."""

from __future__ import annotations

from typing import Any

from . import runtime


def review_result(
    ledger: dict[str, Any],
    result_id: str,
    reviewer_lease_id: str,
    *,
    decision: str = "accept",
    checks_evidence: bool = True,
    scope_restatement: str = "",
    failure_hypotheses: list[str] | None = None,
    direct_evidence_ids: list[str] | None = None,
    waivers: list[str] | None = None,
    pm_routing_decision: str = "",
) -> str:
    review_id = runtime.review_result(
        ledger,
        result_id,
        reviewer_lease_id,
        decision=decision,
        checks_evidence=checks_evidence,
        direct_evidence_ids=direct_evidence_ids,
        waivers=waivers,
        pm_routing_decision=pm_routing_decision,
    )
    review = ledger["reviews"][review_id]
    review["scope_restatement"] = scope_restatement
    review["failure_hypotheses"] = list(failure_hypotheses or [])
    if decision == "block" and pm_routing_decision:
        review["route_invalidating_issue"] = pm_routing_decision in {"mutate_route", "split_route", "repair_route", "block_route"}
    return review_id


def attempt_final_closure(ledger: dict[str, Any], validation_evidence_id: str) -> dict[str, Any]:
    closure = runtime.attempt_final_closure(ledger, validation_evidence_id)
    gate = ledger.get("cutover_gate")
    if isinstance(gate, dict) and gate.get("decision") == "blocked":
        closure["decision"] = "blocked"
        closure.setdefault("blockers", []).append("cutover_gate_blocked")
        ledger["closure"] = closure
    return closure
