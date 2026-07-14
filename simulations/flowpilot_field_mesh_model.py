"""FlowGuard parent model for the FlowPilot field-contract mesh.

The model consumes a generated field inventory. It does not manually maintain
legacy aliases. Every observed field must be assigned to a child field family
and importance tier; critical current fields must bind to code validators; and
historical fields may appear only outside production code as negative evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_field_mesh"

FIELD_CHILD_MODELS = {
    "startup_fields": "Startup intake, startup answers, and startup mechanical audit fields.",
    "packet_result_fields": "Packet, result, envelope, body, output contract, and relay fields.",
    "router_action_fields": "Router, controller action, state, flag, event, and scheduler fields.",
    "review_gate_fields": "Reviewer, PM, gate, blocker, decision, approval, and repair fields.",
    "background_collaboration_fields": "Background or parallel agent, role binding, liveness, and agent-id fields.",
    "continuation_terminal_fields": "Manual resume, continuation, closure, terminal, and completion fields.",
    "model_evidence_fields": "FlowGuard, model, proof, evidence, hash, source path, and artifact fields.",
    "prompt_card_fields": "Prompt, card, instruction, contract prose, and runtime kit fields.",
    "test_harness_fields": "Test-only fixtures, fake packages, and rehearsal harness fields.",
    "supporting_runtime_fields": "Supporting current runtime fields not owned by a narrower child model.",
}

IMPORTANCE_TIERS = {
    "critical_transition": "Field directly gates a FlowPilot state transition or hard stop.",
    "state_contract": "Field records route, run, state, status, action, event, or schema identity.",
    "evidence_contract": "Field records path, hash, proof, receipt, source, or validation evidence.",
    "supporting": "Field supports a current contract but does not directly advance a gate.",
}

FIELD_LIFECYCLE_STATES = {
    "current": "Current-contract field that may be read or written by its named owner.",
    "mechanical_runtime_owned": "Runtime/Router-owned mechanical validity field.",
    "pm_decision_owned": "PM-owned disposition or repair decision field.",
    "reviewer_quality_owned": "Reviewer-owned semantic quality field.",
    "flowguard_process_owned": "FlowGuard-operator-owned process/model/state field.",
    "terminal_monotonic": "Runtime-owned state field whose terminal values cannot be reactivated by later input.",
    "append_only_audit": "Runtime-owned history field that may append audit evidence without changing current authority.",
    "single_authority_pointer": "Runtime-owned pointer field with one writer and one commit point.",
    "pending_until_commit": "Runtime-owned pending field that must clear or terminally dispose after commit/block.",
    "derived_projection": "Display or summary field derived from an authority predicate, not independently authoritative.",
    "retired": "Removed from current runtime and manifest surfaces.",
    "forbidden_legacy": "Old field, event, output type, or card that current runtime must reject.",
}


# These fields govern the maintenance-time projection from FlowPilot's source
# contract into SkillGuard and the global router.  They are deliberately kept
# out of the product-runtime field catalog: the repository contract maintainer
# writes them, the public compiler and router consume them, and missing or
# guessed values must block selection instead of creating another runtime path.
MAINTENANCE_AUTHORITY_FIELD_CONTRACTS = (
    {
        "field": "skillguard.contract_source.native_route_bindings[]",
        "child_model": "model_evidence_fields",
        "importance": "critical_transition",
        "owner": "flowpilot_skillguard_contract_source",
        "writers": ("flowpilot_contract_maintainer",),
        "readers": (
            "skillguard_v2_public_compiler",
            "skillguard_global_router",
            "flowpilot_skillguard_contract_model",
        ),
        "projections": (
            "skills/flowpilot/.skillguard/compiled-contract.json",
            ".codex/.skillguard/global-router/global_registry.json",
        ),
        "lifecycle": "current",
        "exact_set_source": "flowpilot_skillguard_contract_model.export_contract.routes",
        "missing_disposition": "global_skill_selection_blocked",
        "default_allowed": False,
        "fallback_allowed": False,
    },
    {
        "field": "skillguard.contract_source.native_check_bindings[]",
        "child_model": "model_evidence_fields",
        "importance": "critical_transition",
        "owner": "flowpilot_skillguard_contract_source",
        "writers": ("flowpilot_contract_maintainer",),
        "readers": (
            "skillguard_v2_public_compiler",
            "skillguard_global_router",
            "flowpilot_skillguard_contract_model",
        ),
        "projections": (
            "skills/flowpilot/.skillguard/compiled-contract.json",
            "skills/flowpilot/.skillguard/check-manifest.json",
            ".codex/.skillguard/global-router/global_registry.json",
        ),
        "lifecycle": "current",
        "exact_set_source": "skills/flowpilot/.skillguard/contract-source.json.checks",
        "missing_disposition": "global_skill_selection_blocked",
        "default_allowed": False,
        "fallback_allowed": False,
    },
)
REQUIRED_MAINTENANCE_AUTHORITY_FIELD_CONTRACT_COUNT = len(
    MAINTENANCE_AUTHORITY_FIELD_CONTRACTS
)


@dataclass(frozen=True)
class Tick:
    pass


@dataclass(frozen=True)
class Action:
    label: str


@dataclass(frozen=True)
class State:
    status: str = "running"
    observed_field_count: int = 0
    classified_field_count: int = 0
    child_model_count: int = 0
    importance_tier_count: int = 0
    lifecycle_status_count: int = 0
    critical_contract_count: int = 0
    critical_contracts_bound_to_code: int = 0
    unclassified_field_count: int = 0
    unassigned_importance_count: int = 0
    production_legacy_reference_count: int = 0
    prompt_legacy_reference_count: int = 0
    stale_fixed_role_gate_reference_count: int = 0
    maintenance_authority_contract_count: int = 0
    maintenance_authority_contracts_current: int = 0
    maintenance_authority_finding_count: int = 0
    full_inventory_written: bool = False
    child_partition_summary_written: bool = False
    classification: str = ""


class Transition(NamedTuple):
    label: str
    state: State


def mesh_ready(state: State) -> bool:
    return (
        state.status == "running"
        and state.observed_field_count > 0
        and state.classified_field_count == state.observed_field_count
        and state.child_model_count == len(FIELD_CHILD_MODELS)
        and state.importance_tier_count == len(IMPORTANCE_TIERS)
        and state.lifecycle_status_count == len(FIELD_LIFECYCLE_STATES)
        and state.critical_contract_count > 0
        and state.critical_contracts_bound_to_code == state.critical_contract_count
        and state.unclassified_field_count == 0
        and state.unassigned_importance_count == 0
        and state.production_legacy_reference_count == 0
        and state.prompt_legacy_reference_count == 0
        and state.stale_fixed_role_gate_reference_count == 0
        and state.maintenance_authority_contract_count
        == REQUIRED_MAINTENANCE_AUTHORITY_FIELD_CONTRACT_COUNT
        and state.maintenance_authority_contracts_current
        == state.maintenance_authority_contract_count
        and state.maintenance_authority_finding_count == 0
        and state.full_inventory_written
        and state.child_partition_summary_written
    )


def _block_label(state: State) -> str:
    if state.observed_field_count <= 0:
        return "block_no_observed_fields"
    if state.unclassified_field_count or state.classified_field_count != state.observed_field_count:
        return "block_unclassified_fields"
    if state.unassigned_importance_count or state.importance_tier_count != len(IMPORTANCE_TIERS):
        return "block_unassigned_importance_tiers"
    if state.lifecycle_status_count != len(FIELD_LIFECYCLE_STATES):
        return "block_missing_field_lifecycle_statuses"
    if state.child_model_count != len(FIELD_CHILD_MODELS):
        return "block_missing_child_field_models"
    if state.critical_contracts_bound_to_code != state.critical_contract_count:
        return "block_unbound_critical_field_contracts"
    if state.production_legacy_reference_count:
        return "block_production_legacy_field_references"
    if state.prompt_legacy_reference_count:
        return "block_prompt_legacy_field_references"
    if state.stale_fixed_role_gate_reference_count:
        return "block_stale_fixed_role_field_gates"
    if (
        state.maintenance_authority_contract_count
        != REQUIRED_MAINTENANCE_AUTHORITY_FIELD_CONTRACT_COUNT
    ):
        return "block_missing_maintenance_authority_field_contracts"
    if (
        state.maintenance_authority_contracts_current
        != state.maintenance_authority_contract_count
        or state.maintenance_authority_finding_count
    ):
        return "block_stale_maintenance_authority_field_projection"
    if not state.full_inventory_written:
        return "block_missing_full_field_inventory"
    if not state.child_partition_summary_written:
        return "block_missing_child_partition_summary"
    return "block_field_mesh_incomplete"


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status != "running":
        return
    if mesh_ready(state):
        yield Transition("accept_field_mesh", replace(state, status="complete", classification="accepted"))
        return
    label = _block_label(state)
    yield Transition(label, replace(state, status="blocked", classification=label))


def is_terminal(state: State) -> bool:
    return state.status in {"complete", "blocked"}


def is_success(state: State) -> bool:
    return is_terminal(state)


def hard_check_failures(state: State, trace: object | None = None) -> list[str]:
    del trace
    failures: list[str] = []
    if state.status == "complete" and not mesh_ready(replace(state, status="running")):
        failures.append("field mesh accepted without full current field coverage")
    if state.status == "blocked" and mesh_ready(replace(state, status="running")):
        failures.append("field mesh blocked even though coverage was complete")
    return failures


def hard_invariant(state: State, trace: object) -> InvariantResult:
    failures = hard_check_failures(state, trace)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "flowpilot_field_mesh_gate",
        "All observed fields must attach to a child model, importance tier, code binding, and current/negative disposition.",
        hard_invariant,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 2


class FlowPilotFieldMeshStep:
    name = "FlowPilotFieldMeshStep"
    reads = (
        "generated_field_inventory",
        "field_child_partitions",
        "field_lifecycle_statuses",
        "critical_code_bindings",
        "maintenance_authority_field_contracts",
    )
    writes = ("field_mesh_acceptance_or_block",)
    input_description = "generated field mesh metrics"
    output_description = "accepted field mesh or explicit block"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def build_workflow() -> Workflow:
    return Workflow((FlowPilotFieldMeshStep(),), name=MODEL_ID)
