"""FlowGuard projection for FlowPilot's current SkillGuard contract.

The model preserves FlowPilot as the only domain runtime.  It binds the
explicit opt-in boundary, PM route planning, complete substantive-role
workstreams, and independent closure evidence to one current contract without
creating a SkillGuard-owned execution route.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
from typing import Iterable

import flowguard
from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


FLOWGUARD_MODEL_MARKER = "flowguard-executable-model"
MODEL_ID = "flowpilot.skillguard_current_contract.v2"
PARENT_MODEL_ID = "flowpilot_complete_workstream_orchestration"


@dataclass(frozen=True)
class ContractInput:
    explicit_opt_in: bool = True
    complex_long_project: bool = True
    native_runtime_owner_current: bool = True
    native_route_bindings_current: bool = True
    native_check_bindings_current: bool = True
    local_skill_inventory_current: bool = True
    pm_route_plan_current: bool = True
    numbered_role_plan_current: bool = True
    delegated_outputs_integrated: bool = True
    verification_and_repair_current: bool = True
    numbered_completion_report_current: bool = True
    independent_flowguard_current: bool = True
    reviewer_and_pm_disposition_current: bool = True
    final_parent_receipts_current: bool = True
    parallel_skillguard_route: bool = False
    former_contract_authority_present: bool = False


@dataclass(frozen=True)
class ContractState:
    activation_bound: bool = False
    route_plan_bound: bool = False
    workstream_bound: bool = False
    closure_bound: bool = False


@dataclass(frozen=True)
class ContractStageReady:
    stage_id: str


@dataclass(frozen=True)
class ContractBlocked:
    reason: str


class BindActivationBoundary:
    """ContractInput x ContractState -> Set(Output x ContractState)."""

    name = "BindActivationBoundary"
    reads = (
        "explicit_opt_in",
        "complex_long_project",
        "native_runtime_owner_current",
        "native_route_bindings_current",
        "native_check_bindings_current",
        "parallel_skillguard_route",
        "former_contract_authority_present",
    )
    writes = ("activation_bound",)
    input_description = "current FlowPilot activation and authority facts"
    output_description = "bound activation boundary or a blocking reason"
    idempotency = "the same current authority facts produce the same boundary"

    def apply(
        self, input_obj: ContractInput, state: ContractState
    ) -> Iterable[FunctionResult]:
        gates = (
            (input_obj.explicit_opt_in, "explicit_opt_in_missing"),
            (input_obj.complex_long_project, "complex_long_project_boundary_missing"),
            (input_obj.native_runtime_owner_current, "native_runtime_owner_not_current"),
            (
                input_obj.native_route_bindings_current,
                "native_route_bindings_missing",
            ),
            (
                input_obj.native_check_bindings_current,
                "native_check_bindings_missing",
            ),
            (not input_obj.parallel_skillguard_route, "parallel_skillguard_route_forbidden"),
            (
                not input_obj.former_contract_authority_present,
                "former_contract_authority_forbidden",
            ),
        )
        failed = next((reason for passed, reason in gates if not passed), "")
        if failed:
            yield FunctionResult(ContractBlocked(failed), state, failed)
            return
        yield FunctionResult(
            ContractStageReady("activation"),
            replace(state, activation_bound=True),
            "activation_bound",
        )


class BindRoutePlan:
    """ContractInput x ContractState -> Set(Output x ContractState)."""

    name = "BindRoutePlan"
    reads = (
        "activation_bound",
        "local_skill_inventory_current",
        "pm_route_plan_current",
    )
    writes = ("route_plan_bound",)
    input_description = "activated project and PM planning facts"
    output_description = "bound PM route plan or a blocking reason"
    idempotency = "the same PM planning facts produce the same binding"

    def apply(
        self, input_obj: ContractInput, state: ContractState
    ) -> Iterable[FunctionResult]:
        gates = (
            (state.activation_bound, "activation_not_bound"),
            (input_obj.local_skill_inventory_current, "local_skill_inventory_missing"),
            (input_obj.pm_route_plan_current, "pm_route_plan_missing"),
        )
        failed = next((reason for passed, reason in gates if not passed), "")
        if failed:
            yield FunctionResult(ContractBlocked(failed), state, failed)
            return
        yield FunctionResult(
            ContractStageReady("route_plan"),
            replace(state, route_plan_bound=True),
            "route_plan_bound",
        )


class BindCompleteWorkstream:
    """ContractInput x ContractState -> Set(Output x ContractState)."""

    name = "BindCompleteWorkstream"
    reads = (
        "route_plan_bound",
        "numbered_role_plan_current",
        "delegated_outputs_integrated",
        "verification_and_repair_current",
        "numbered_completion_report_current",
    )
    writes = ("workstream_bound",)
    input_description = "one PM-bounded substantive role workstream"
    output_description = "bound complete workstream or a blocking reason"
    idempotency = "the same current role evidence produces the same binding"

    def apply(
        self, input_obj: ContractInput, state: ContractState
    ) -> Iterable[FunctionResult]:
        gates = (
            (state.route_plan_bound, "route_plan_not_bound"),
            (input_obj.numbered_role_plan_current, "numbered_role_plan_missing"),
            (input_obj.delegated_outputs_integrated, "delegated_outputs_not_integrated"),
            (
                input_obj.verification_and_repair_current,
                "verification_and_repair_not_current",
            ),
            (
                input_obj.numbered_completion_report_current,
                "numbered_completion_report_missing",
            ),
        )
        failed = next((reason for passed, reason in gates if not passed), "")
        if failed:
            yield FunctionResult(ContractBlocked(failed), state, failed)
            return
        yield FunctionResult(
            ContractStageReady("complete_workstream"),
            replace(state, workstream_bound=True),
            "complete_workstream_bound",
        )


class BindIndependentClosure:
    """ContractInput x ContractState -> Set(Output x ContractState)."""

    name = "BindIndependentClosure"
    reads = (
        "workstream_bound",
        "independent_flowguard_current",
        "reviewer_and_pm_disposition_current",
        "final_parent_receipts_current",
    )
    writes = ("closure_bound",)
    input_description = "integrated workstream and independent closure evidence"
    output_description = "bound closure evidence or a blocking reason"
    idempotency = "the same frozen receipts produce the same closure binding"

    def apply(
        self, input_obj: ContractInput, state: ContractState
    ) -> Iterable[FunctionResult]:
        gates = (
            (state.workstream_bound, "workstream_not_bound"),
            (input_obj.independent_flowguard_current, "independent_flowguard_missing"),
            (
                input_obj.reviewer_and_pm_disposition_current,
                "reviewer_or_pm_disposition_missing",
            ),
            (input_obj.final_parent_receipts_current, "final_parent_receipts_missing"),
        )
        failed = next((reason for passed, reason in gates if not passed), "")
        if failed:
            yield FunctionResult(ContractBlocked(failed), state, failed)
            return
        yield FunctionResult(
            ContractStageReady("closure"),
            replace(state, closure_bound=True),
            "independent_closure_bound",
        )


def singular_native_authority(
    state: ContractState, _trace: object
) -> InvariantResult:
    if (state.route_plan_bound or state.workstream_bound or state.closure_bound) and not state.activation_bound:
        return InvariantResult.fail("FlowPilot work escaped the current activation authority")
    return InvariantResult.pass_()


def monotonic_closure(state: ContractState, _trace: object) -> InvariantResult:
    if state.workstream_bound and not state.route_plan_bound:
        return InvariantResult.fail("role work escaped the PM route plan")
    if state.closure_bound and not state.workstream_bound:
        return InvariantResult.fail("closure escaped the complete workstream")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "singular_native_authority",
        "FlowPilot remains the sole domain runtime under one current activation authority.",
        singular_native_authority,
    ),
    Invariant(
        "monotonic_closure",
        "Planning, role execution, and independent closure remain monotonic.",
        monotonic_closure,
    ),
)


BLOCKS = (
    BindActivationBoundary(),
    BindRoutePlan(),
    BindCompleteWorkstream(),
    BindIndependentClosure(),
)


def build_workflow() -> Workflow:
    return Workflow(BLOCKS, name=MODEL_ID)


def _route_rows() -> tuple[tuple[str, str, str], ...]:
    return (
        ("route:flowpilot-opt-in", "flowpilot_explicit_opt_in", "step:flowpilot-opt-in"),
        ("route:flowpilot-route-plan", "flowpilot_pm_route_plan", "step:flowpilot-route-plan"),
        (
            "route:flowpilot-complete-workstream",
            "flowpilot_complete_role_workstream",
            "step:flowpilot-complete-workstream",
        ),
        (
            "route:flowpilot-independent-closure",
            "flowpilot_independent_closure",
            "step:flowpilot-independent-closure",
        ),
    )


def export_contract_model() -> dict[str, object]:
    rows = _route_rows()
    functions: list[dict[str, object]] = []
    routes: list[dict[str, object]] = []
    steps: list[dict[str, object]] = []
    for route_id, function_id, start_step_id in rows:
        suffix = route_id.removeprefix("route:")
        success_id = f"terminal:{suffix}:success"
        blocked_id = f"terminal:{suffix}:blocked"
        functions.append(
            {
                "function_id": function_id,
                "business_intent": route_id.replace("route:", "").replace("-", " "),
                "intent_patterns": [route_id, route_id.replace("-", " ")],
                "owner_id": "flowpilot_runtime_router",
                "route_ids": [route_id],
                "composable_with": [
                    candidate_function
                    for _, candidate_function, _ in rows
                    if candidate_function != function_id
                ],
            }
        )
        routes.append(
            {
                "route_id": route_id,
                "function_id": function_id,
                "owner_id": "flowpilot_runtime_router",
                "start_step_id": start_step_id,
                "step_ids": [start_step_id, success_id, blocked_id],
                "success_terminal_step_id": success_id,
                "blocked_terminal_step_id": blocked_id,
                "handoffs": [],
            }
        )
        steps.extend(
            (
                {
                    "step_id": start_step_id,
                    "route_id": route_id,
                    "owner_id": "flowpilot_runtime_router",
                    "action_kind": "native",
                    "prerequisite_step_ids": [],
                    "required": True,
                    "terminal_kind": "",
                },
                {
                    "step_id": success_id,
                    "route_id": route_id,
                    "owner_id": "flowpilot_runtime_router",
                    "action_kind": "terminal",
                    "prerequisite_step_ids": [start_step_id],
                    "required": True,
                    "terminal_kind": "success",
                },
                {
                    "step_id": blocked_id,
                    "route_id": route_id,
                    "owner_id": "flowpilot_runtime_router",
                    "action_kind": "terminal",
                    "prerequisite_step_ids": [],
                    "required": True,
                    "terminal_kind": "blocked",
                },
            )
        )
    obligations = (
        ("obligation:flowpilot-explicit-opt-in", "step:flowpilot-opt-in", "singular_native_authority"),
        ("obligation:flowpilot-complex-project-boundary", "step:flowpilot-opt-in", "singular_native_authority"),
        ("obligation:flowpilot-current-skillguard-authority", "step:flowpilot-opt-in", "singular_native_authority"),
        ("obligation:flowpilot-local-skill-inventory", "step:flowpilot-route-plan", "monotonic_closure"),
        ("obligation:flowpilot-pm-route-plan", "step:flowpilot-route-plan", "monotonic_closure"),
        ("obligation:flowpilot-numbered-role-plan", "step:flowpilot-complete-workstream", "monotonic_closure"),
        ("obligation:flowpilot-integrate-verify-repair", "step:flowpilot-complete-workstream", "monotonic_closure"),
        ("obligation:flowpilot-numbered-completion-report", "step:flowpilot-complete-workstream", "monotonic_closure"),
        ("obligation:flowpilot-independent-flowguard-review", "step:flowpilot-independent-closure", "monotonic_closure"),
        ("obligation:flowpilot-current-final-receipts", "step:flowpilot-independent-closure", "monotonic_closure"),
    )
    return {
        "schema_version": "skillguard.flowguard_model_export.v2",
        "flowguard_schema_version": str(flowguard.SCHEMA_VERSION),
        "model_id": MODEL_ID,
        "parent_model_id": PARENT_MODEL_ID,
        "functions": functions,
        "routes": routes,
        "steps": steps,
        "obligations": [
            {
                "obligation_id": obligation_id,
                "invariant_id": invariant_id,
                "owner_step_ids": [step_id],
                "required": True,
            }
            for obligation_id, step_id, invariant_id in obligations
        ],
        "invariant_ids": [row.name for row in INVARIANTS],
        "claim_boundary": (
            "This model projects FlowPilot's existing activation, PM planning, complete-role-workstream, "
            "and independent-closure authorities into the current SkillGuard contract. It does not "
            "execute FlowPilot, add a SkillGuard runtime route, prove arbitrary AI quality, or turn "
            "contract-depth mapping into execution-depth evidence."
        ),
    }


def _run(input_obj: ContractInput) -> tuple[ContractState, str]:
    state = ContractState()
    for block in BLOCKS:
        result = next(iter(block.apply(input_obj, state)))
        if isinstance(result.output, ContractBlocked):
            return state, result.output.reason
        state = result.new_state
    return state, ""


def main() -> int:
    good, blocker = _run(ContractInput())
    known_bad = {
        "missing_opt_in": ContractInput(explicit_opt_in=False),
        "ordinary_small_task": ContractInput(complex_long_project=False),
        "missing_native_route_bindings": ContractInput(
            native_route_bindings_current=False
        ),
        "missing_native_check_bindings": ContractInput(
            native_check_bindings_current=False
        ),
        "parallel_skillguard_route": ContractInput(parallel_skillguard_route=True),
        "former_contract_authority": ContractInput(former_contract_authority_present=True),
        "missing_skill_inventory": ContractInput(local_skill_inventory_current=False),
        "missing_numbered_plan": ContractInput(numbered_role_plan_current=False),
        "unintegrated_delegation": ContractInput(delegated_outputs_integrated=False),
        "missing_independent_flowguard": ContractInput(independent_flowguard_current=False),
        "stale_final_receipts": ContractInput(final_parent_receipts_current=False),
    }
    blocked = {name: _run(case)[1] for name, case in known_bad.items()}
    ok = good.closure_bound and not blocker and all(blocked.values())
    print(
        json.dumps(
            {
                "ok": ok,
                "model_id": MODEL_ID,
                "positive_closure_bound": good.closure_bound,
                "known_bad_blockers": blocked,
                "claim_boundary": export_contract_model()["claim_boundary"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
