"""FlowGuard work-order facade for complete-system callers."""

from __future__ import annotations

from typing import Any

from . import runtime


def create_work_order(ledger: dict[str, Any], modeled_target: str, risk_type: str, subject_id: str) -> str:
    return runtime.create_flowguard_work_order(ledger, modeled_target, risk_type, subject_id)


def complete_work_order(
    ledger: dict[str, Any],
    order_id: str,
    *,
    decision: str = "pass",
    evidence_id: str = "flowguard-report",
    proof_artifact: str = "",
    progress_only: bool = False,
    skipped_checks: list[str] | None = None,
    confidence_boundary: str = "scoped",
) -> None:
    runtime.complete_flowguard_work_order(
        ledger,
        order_id,
        decision=decision,
        evidence_id=evidence_id,
        progress_only=progress_only,
        skipped_checks=skipped_checks,
    )
    order = ledger["flowguard_work_orders"][order_id]
    order["proof_artifact"] = proof_artifact or evidence_id
    order["confidence_boundary"] = confidence_boundary
