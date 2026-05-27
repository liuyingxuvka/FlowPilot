"""FlowGuard workflow-step contract projection for FlowPilot actions."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable

from flowguard import (
    Trace,
    TraceStep,
    WorkflowStepContract,
    review_step_contract_trace,
    step_contract_metadata,
)


MODEL_ID = "flowpilot_workflow_step_contracts"


@dataclass(frozen=True)
class Projection:
    """Projected FlowGuard contracts plus stable receipt ids for one action."""

    action_key: str
    contracts: tuple[WorkflowStepContract, ...]
    issued_receipt: str
    completion_receipt: str
    work_receipt: str | None = None
    ack_scope: str | None = None


def _slug(value: object, fallback: str = "step") -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9_.:-]+", "-", text).strip("-")
    return text or fallback


def action_contract_key(action: dict[str, Any]) -> str:
    """Return a stable key for a Router/Controller action contract."""

    action_type = _slug(action.get("action_type"), "action")
    label = _slug(
        action.get("controller_action_id")
        or action.get("idempotency_key")
        or action.get("label")
        or action.get("action_id"),
        "unnamed",
    )
    return f"{action_type}:{label}"


def _contract_value(action: dict[str, Any], key: str, default: Any = None) -> Any:
    contract = action.get("next_step_contract")
    if isinstance(contract, dict) and key in contract:
        return contract.get(key)
    return action.get(key, default)


def workflow_step_contracts_for_action(action: dict[str, Any]) -> Projection:
    """Project one FlowPilot action into FlowGuard workflow-step contracts."""

    key = action_contract_key(action)
    contract = action.get("next_step_contract")
    contract_payload = contract if isinstance(contract, dict) else {}
    action_type = str(action.get("action_type") or contract_payload.get("action_type") or "action")
    recipient = str(
        contract_payload.get("recipient_role")
        or action.get("to_role")
        or action.get("actor")
        or "unknown"
    )
    completion_command = str(_contract_value(action, "controller_completion_command", "apply"))
    completion_mode = str(_contract_value(action, "controller_completion_mode", "router_apply"))
    ack_only = bool(_contract_value(action, "ack_is_read_receipt_only", False))
    separate_work = bool(
        _contract_value(action, "target_work_completion_evidence_required_separately", False)
    )
    release_required = bool(action.get("release_required") or contract_payload.get("release_required"))
    issued_receipt = f"router_action_issued:{key}"
    if completion_command == "controller-receipt":
        completion_receipt = f"controller_receipt:{key}"
        completion_label = f"controller_receipt:{key}:done"
        claim_label = f"controller_row_complete:{key}"
        description = (
            f"Controller row for {action_type!r} must complete through a "
            "Controller receipt, not the normal Router apply path."
        )
    elif ack_only:
        scope = _slug(
            _contract_value(action, "ack_clearance_scope", recipient),
            f"{recipient}:ack",
        )
        completion_receipt = f"ack_settlement:{scope}"
        completion_label = f"ack_settlement:{scope}:done"
        claim_label = f"ack_settled:{scope}"
        description = (
            f"ACK clearance for {recipient!r} settles only the read-receipt wait."
        )
    elif bool(_contract_value(action, "apply_required", True)):
        completion_receipt = f"action_applied:{key}"
        completion_label = f"action_apply:{key}:done"
        claim_label = f"action_applied:{key}"
        description = f"Action {action_type!r} must be applied before progress is claimed."
    else:
        completion_receipt = f"router_controlled_wait:{key}"
        completion_label = f"router_wait:{key}:observed"
        claim_label = f"router_wait_observed:{key}"
        description = f"Action {action_type!r} is a Router-controlled wait/status row."

    metadata = {
        "action_type": action_type,
        "recipient_role": recipient,
        "controller_completion_command": completion_command,
        "controller_completion_mode": completion_mode,
        "apply_required": bool(_contract_value(action, "apply_required", True)),
        "router_pending_apply_required": bool(
            _contract_value(action, "router_pending_apply_required", False)
        ),
    }
    main_contract = WorkflowStepContract(
        step_id=f"flowpilot.next_step:{key}",
        completion_labels=(completion_label,),
        requires_receipts=(issued_receipt,),
        produces_receipts=(completion_receipt,),
        required_for_claims=(claim_label, "release" if release_required else "routine"),
        description=description,
        evidence_kind="workflow_step_contract",
        required_test_kinds=("happy_path", "negative_path"),
        artifact_ids=("next_step_contract",),
        code_contract_ids=("workflow_step_contracts.project_action",),
        release_required=release_required,
        metadata=metadata,
    )

    contracts: list[WorkflowStepContract] = [main_contract]
    work_receipt: str | None = None
    ack_scope: str | None = None
    if ack_only:
        ack_scope = _slug(_contract_value(action, "ack_clearance_scope", recipient), f"{recipient}:ack")
    if ack_only and separate_work:
        work_receipt = f"work_output:{key}"
        work_contract = WorkflowStepContract(
            step_id=f"flowpilot.target_work:{key}",
            completion_labels=(f"work_output:{key}:done",),
            requires_receipts=(completion_receipt,),
            produces_receipts=(work_receipt,),
            required_for_claims=(f"work_complete:{key}", "routine"),
            description=(
                f"Target work for {recipient!r} needs durable output evidence "
                "separate from ACK clearance."
            ),
            evidence_kind="workflow_step_contract",
            required_test_kinds=("edge_path", "negative_path"),
            artifact_ids=("target_work_output",),
            code_contract_ids=("workflow_step_contracts.project_action",),
            release_required=release_required,
            metadata={"action_type": action_type, "recipient_role": recipient, "ack_scope": ack_scope},
        )
        contracts.append(work_contract)

    return Projection(
        action_key=key,
        contracts=tuple(contracts),
        issued_receipt=issued_receipt,
        completion_receipt=completion_receipt,
        work_receipt=work_receipt,
        ack_scope=ack_scope,
    )


def workflow_step_contracts_for_actions(
    actions: Iterable[dict[str, Any]],
) -> tuple[WorkflowStepContract, ...]:
    contracts: list[WorkflowStepContract] = []
    for action in actions:
        contracts.extend(workflow_step_contracts_for_action(action).contracts)
    return tuple(contracts)


def trace_step(
    label: str,
    *,
    produced: tuple[str, ...] = (),
    invalidated: tuple[str, ...] = (),
    skipped: tuple[str, ...] = (),
    claims: tuple[str, ...] = (),
    reason: str = "",
) -> TraceStep:
    """Build a compact trace step for contract review tests."""

    return TraceStep(
        external_input="tick",
        function_name="FlowPilotWorkflowStepContractProjection",
        function_input={},
        function_output=label,
        old_state={},
        new_state={},
        label=label,
        reason=reason,
        metadata=step_contract_metadata(
            produced_receipts=produced,
            invalidated_receipts=invalidated,
            skipped_step_ids=skipped,
            claim_labels=claims,
        ),
    )


def review_trace(steps: tuple[TraceStep, ...], contracts: tuple[WorkflowStepContract, ...]):
    """Review a synthetic FlowPilot action trace against step contracts."""

    return review_step_contract_trace(Trace(steps=steps), contracts)
