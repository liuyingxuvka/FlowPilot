"""Run FlowGuard workflow-step contract checks for FlowPilot next-step actions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from flowpilot_workflow_step_contracts import (
    MODEL_ID,
    Projection,
    review_trace,
    trace_step,
    workflow_step_contracts_for_action,
)


RESULTS_PATH = Path(__file__).resolve().with_name("flowpilot_workflow_step_contract_results.json")


def _controller_receipt_action() -> dict[str, Any]:
    return {
        "action_type": "deliver_controller_row",
        "label": "controller-row-1",
        "actor": "controller",
        "apply_required": False,
        "next_step_contract": {
            "schema_version": "flowpilot.next_step_contract.v1",
            "action_type": "deliver_controller_row",
            "recipient_role": "controller",
            "apply_required": False,
            "router_pending_apply_required": True,
            "controller_completion_command": "controller-receipt",
            "controller_completion_mode": "controller_action_ledger_receipt",
            "controller_receipt_required": True,
        },
    }


def _ack_only_action() -> dict[str, Any]:
    return {
        "action_type": "await_role_decision",
        "label": "pm-output-wait",
        "actor": "project_manager",
        "to_role": "project_manager",
        "next_step_contract": {
            "schema_version": "flowpilot.next_step_contract.v1",
            "action_type": "await_role_decision",
            "recipient_role": "project_manager",
            "apply_required": False,
            "ack_clearance_scope": "pm-output-wait",
            "ack_is_read_receipt_only": True,
            "target_work_completion_evidence_required_separately": True,
        },
    }


def _finding_codes(report: Any) -> list[str]:
    return sorted({finding.code for finding in report.findings})


def _controller_receipt_report() -> dict[str, Any]:
    projection = workflow_step_contracts_for_action(_controller_receipt_action())
    contract = projection.contracts[0]
    ok_trace = review_trace(
        (
            trace_step("router_action_issued", produced=(projection.issued_receipt,)),
            trace_step(contract.completion_labels[0]),
            trace_step("controller_row_claim", claims=(contract.required_for_claims[0],)),
        ),
        projection.contracts,
    )
    missing_prereq = review_trace((trace_step(contract.completion_labels[0]),), projection.contracts)
    forbidden_skip = review_trace(
        (trace_step("skip_without_reason", skipped=(contract.step_id,)),),
        projection.contracts,
    )
    return {
        "ok": ok_trace.ok and not missing_prereq.ok and not forbidden_skip.ok,
        "projected_contracts": [item.to_dict() for item in projection.contracts],
        "positive": ok_trace.to_dict(),
        "known_bad_missing_prerequisite": missing_prereq.to_dict(),
        "known_bad_forbidden_skip": forbidden_skip.to_dict(),
        "known_bad_codes": {
            "missing_prerequisite": _finding_codes(missing_prereq),
            "forbidden_skip": _finding_codes(forbidden_skip),
        },
    }


def _ack_separation_report() -> dict[str, Any]:
    projection: Projection = workflow_step_contracts_for_action(_ack_only_action())
    ack_contract, work_contract = projection.contracts
    ok_trace = review_trace(
        (
            trace_step("router_action_issued", produced=(projection.issued_receipt,)),
            trace_step(ack_contract.completion_labels[0]),
            trace_step(work_contract.completion_labels[0]),
            trace_step("work_complete_claim", claims=(work_contract.required_for_claims[0],)),
        ),
        projection.contracts,
    )
    ack_only_claim = review_trace(
        (
            trace_step("router_action_issued", produced=(projection.issued_receipt,)),
            trace_step(ack_contract.completion_labels[0]),
            trace_step("premature_work_complete_claim", claims=(work_contract.required_for_claims[0],)),
        ),
        projection.contracts,
    )
    stale_ack = review_trace(
        (
            trace_step("router_action_issued", produced=(projection.issued_receipt,)),
            trace_step(ack_contract.completion_labels[0]),
            trace_step("invalidate_ack", invalidated=(projection.completion_receipt,)),
            trace_step(work_contract.completion_labels[0]),
        ),
        projection.contracts,
    )
    return {
        "ok": ok_trace.ok and not ack_only_claim.ok and not stale_ack.ok,
        "projected_contracts": [item.to_dict() for item in projection.contracts],
        "positive": ok_trace.to_dict(),
        "known_bad_ack_only_as_work": ack_only_claim.to_dict(),
        "known_bad_stale_ack": stale_ack.to_dict(),
        "known_bad_codes": {
            "ack_only_as_work": _finding_codes(ack_only_claim),
            "stale_ack": _finding_codes(stale_ack),
        },
    }


def build_report() -> dict[str, Any]:
    controller = _controller_receipt_report()
    ack = _ack_separation_report()
    return {
        "ok": bool(controller["ok"] and ack["ok"]),
        "result_type": "flowpilot_workflow_step_contracts",
        "model_id": MODEL_ID,
        "reports": {
            "controller_receipt": controller,
            "ack_separation": ack,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = build_report()
    output = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(output, encoding="utf-8")
    if args.json:
        print(output, end="")
    else:
        print(f"[flowpilot-workflow-step-contracts] ok={report['ok']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
