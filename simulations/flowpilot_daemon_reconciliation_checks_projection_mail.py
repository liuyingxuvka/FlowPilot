"""Mail-delivery live-projection findings for daemon reconciliation checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flowpilot_daemon_reconciliation_checks_projection_common import (
    MISSING_POSTCONDITION_BLOCKER_SOURCE,
    PROJECT_ROOT,
    _controller_boundary_receipt_status,
    _read_json,
)

def _mail_delivery_projection_findings(
    run_root: Path,
    row_by_id: dict[str, dict[str, Any]],
    actions: list[dict[str, Any]],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    router_state_path = run_root / "router_state.json"
    packet_ledger_path = run_root / "packet_ledger.json"
    role_output_ledger_path = run_root / "role_output_ledger.json"
    router_state = _read_json(router_state_path) if router_state_path.exists() else {}
    packet_ledger = _read_json(packet_ledger_path) if packet_ledger_path.exists() else {}
    role_output_ledger = _read_json(role_output_ledger_path) if role_output_ledger_path.exists() else {}
    flags = router_state.get("flags") if isinstance(router_state.get("flags"), dict) else {}
    mail_entries = packet_ledger.get("mail") if isinstance(packet_ledger.get("mail"), list) else []
    packets = packet_ledger.get("packets") if isinstance(packet_ledger.get("packets"), list) else []
    role_outputs = role_output_ledger.get("outputs") if isinstance(role_output_ledger.get("outputs"), list) else []

    repair_decisions_by_blocker: dict[str, list[dict[str, Any]]] = {}
    for output in role_outputs:
        if not isinstance(output, dict):
            continue
        if output.get("output_type") != "pm_control_blocker_repair_decision":
            continue
        body_path = output.get("body_path")
        if not isinstance(body_path, str):
            continue
        path = PROJECT_ROOT / body_path
        if not path.exists():
            continue
        try:
            decision = _read_json(path)
        except Exception:  # pragma: no cover - defensive live-run audit
            continue
        blocker_id = str(decision.get("blocker_id") or "")
        if blocker_id:
            repair_decisions_by_blocker.setdefault(blocker_id, []).append(
                {
                    "body_path": body_path,
                    "decision": decision.get("decision"),
                    "recovery_option": decision.get("recovery_option"),
                    "return_gate": decision.get("return_gate"),
                    "rerun_target": decision.get("rerun_target"),
                }
            )

    action_by_id = {str(action.get("action_id")): action for action in actions if action.get("action_id")}
    for action in actions:
        if action.get("action_type") != "deliver_mail":
            continue
        nested = action.get("action") if isinstance(action.get("action"), dict) else {}
        mail_id = str(action.get("mail_id") or nested.get("mail_id") or "")
        to_role = str(action.get("to_role") or nested.get("to_role") or "")
        completion = action.get("completion_class") if isinstance(action.get("completion_class"), dict) else {}
        postcondition = str(
            completion.get("postcondition")
            or action.get("postcondition")
            or nested.get("postcondition")
            or ""
        )
        row = row_by_id.get(str(action.get("router_scheduler_row_id")))
        row_reconciliation = row.get("reconciliation", {}) if row else {}
        if not isinstance(row_reconciliation, dict):
            row_reconciliation = {}
        action_reconciliation = action.get("router_reconciliation", {})
        if not isinstance(action_reconciliation, dict):
            action_reconciliation = {}
        receipt = _controller_boundary_receipt_status(run_root, action, row)
        mail_folded = any(
            isinstance(entry, dict)
            and str(entry.get("mail_id") or "") == mail_id
            and (not to_role or str(entry.get("to_role") or "") == to_role)
            for entry in mail_entries
        )
        flag_synced = bool(postcondition and flags.get(postcondition) is True)
        packet = next(
            (
                item for item in packets
                if isinstance(item, dict) and str(item.get("packet_id") or "") == mail_id
            ),
            {},
        )
        action_done = action.get("status") == "done"
        action_blocked = action.get("router_reconciliation_status") == "blocked"
        action_reconciled = action.get("router_reconciliation_status") == "reconciled"
        row_state = row.get("router_state") if row else None
        apply_result = action_reconciliation.get("apply_result")
        if not isinstance(apply_result, dict):
            apply_result = {}
        nested_apply = apply_result.get("apply_result")
        if not isinstance(nested_apply, dict):
            nested_apply = {}
        unsupported_reason = (
            nested_apply.get("reason") == "unsupported_stateful_controller_receipt"
            or apply_result.get("reason") == "unsupported_stateful_controller_receipt"
        )
        evidence = {
            "action_id": action.get("action_id"),
            "router_scheduler_row_id": action.get("router_scheduler_row_id"),
            "row_state": row_state,
            "receipt": receipt,
            "mail_id": mail_id,
            "to_role": to_role,
            "postcondition": postcondition,
            "mail_folded": mail_folded,
            "flag_synced": flag_synced,
            "packet_holder": packet.get("active_packet_holder"),
            "packet_status": packet.get("active_packet_status"),
            "router_reconciliation_status": action.get("router_reconciliation_status"),
            "router_reconciliation_reason": action_reconciliation.get("reason"),
            "router_reconciliation_apply_reason": nested_apply.get("reason") or apply_result.get("reason"),
        }
        if action_done and receipt.get("done") and action_blocked and unsupported_reason:
            findings.append(
                {
                    "id": "mail_delivery_receipt_unfolded_to_packet_ledger",
                    "action_type": "deliver_mail",
                    **evidence,
                }
            )
        if action_reconciled and (not mail_folded or not flag_synced):
            findings.append(
                {
                    "id": "mail_delivery_reconciled_without_packet_ledger_fold",
                    "action_type": "deliver_mail",
                    **evidence,
                }
            )

    control_block_dir = run_root / "control_blocks"
    if control_block_dir.exists():
        repair_transactions = router_state.get("repair_transactions")
        repair_transaction_count = len(repair_transactions) if isinstance(repair_transactions, list) else 0
        active_repair_transaction = router_state.get("active_repair_transaction")
        flags_pm_decision = bool(flags.get("pm_control_blocker_repair_decision_recorded") is True)
        for path in sorted(control_block_dir.glob("*.json")):
            if path.name.endswith(".sealed_repair_packet.json") or path.name == "blocker_repair_policy_snapshot.json":
                continue
            blocker = _read_json(path)
            if blocker.get("source") != MISSING_POSTCONDITION_BLOCKER_SOURCE:
                continue
            if blocker.get("originating_action_type") != "deliver_mail":
                continue
            blocker_id = str(blocker.get("blocker_id") or "")
            decisions = repair_decisions_by_blocker.get(blocker_id, [])
            if decisions and not flags_pm_decision and not active_repair_transaction and repair_transaction_count == 0:
                origin_action = action_by_id.get(str(blocker.get("originating_controller_action_id") or ""))
                findings.append(
                    {
                        "id": "mail_delivery_pm_repair_decision_unconsumed",
                        "action_type": "deliver_mail",
                        "blocker_id": blocker_id,
                        "originating_controller_action_id": blocker.get("originating_controller_action_id"),
                        "originating_postcondition": blocker.get("originating_postcondition"),
                        "handling_lane": blocker.get("handling_lane"),
                        "direct_retry_attempts_used": blocker.get("direct_retry_attempts_used"),
                        "direct_retry_budget": blocker.get("direct_retry_budget"),
                        "direct_retry_budget_exhausted": blocker.get("direct_retry_budget_exhausted"),
                        "pm_decisions": decisions,
                        "pm_decision_flag": flags.get("pm_control_blocker_repair_decision_recorded"),
                        "active_repair_transaction": active_repair_transaction,
                        "repair_transaction_count": repair_transaction_count,
                        "origin_action_reconciliation_status": origin_action.get("router_reconciliation_status") if origin_action else None,
                    }
                )

    return findings
