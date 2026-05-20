"""FlowGuard model for FlowPilot derived views and prompt boundary folding.

Risk intent:
- remaining lifecycle scans must ask the shared closure kernel before clearing
  waits or blockers;
- facade compatibility maps must be owned by registry modules or derived from
  registry rows instead of drifting as hand-written copies;
- role-output/process bindings must prefer contract-index runtime facts and
  make any Python fallback visible;
- prompt cards must share ACK, Router authority, runtime-output, and live
  context boundary policy instead of relying on manually duplicated wording;
- physical ledgers remain separate authority surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_SCENARIOS = (
    "closure_blockers_use_kernel",
    "registry_views_are_owner_derived",
    "output_bindings_are_registry_first",
    "prompt_cards_share_boundary_policy",
    "physical_ledgers_remain_separate",
)

NEGATIVE_SCENARIOS = (
    "local_status_list_clears_unknown_wait",
    "facade_hand_map_drifts_from_registry",
    "hidden_python_contract_fallback_grows",
    "manual_prompt_card_drift_weakens_boundary",
    "physical_ledger_merge_blurs_authority",
)

SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS


@dataclass(frozen=True)
class Tick:
    """One derived-view or prompt-boundary review tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | accepted | rejected
    scenario: str = "unset"

    closure_kernel_used_for_blockers: bool = False
    local_status_predicate_used_for_progress: bool = False
    unknown_closure_cleared_wait: bool = False
    identity_mismatch_cleared_wait: bool = False
    ack_closure_completed_semantic_work: bool = False

    registry_authority_present: bool = False
    owner_module_derives_view: bool = False
    facade_exports_compat_alias: bool = False
    facade_hand_map_owns_policy: bool = False
    derived_view_matches_registry: bool = False

    contract_index_runtime_binding_present: bool = False
    python_fallback_visible_and_bounded: bool = False
    hidden_python_contract_fallback: bool = False

    shared_prompt_policy_assets_present: bool = False
    card_manifest_policy_validated: bool = False
    card_manual_boundary_copy_only: bool = False
    prompt_boundary_contradiction: bool = False
    role_authority_expanded_by_prompt: bool = False

    physical_ledgers_separate: bool = True
    physical_ledger_merge: bool = False
    signed_artifact_rewritten: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _accepted(scenario: str, **changes: object) -> State:
    return replace(State(status="accepted", scenario=scenario), **changes)


def _rejected(scenario: str, **changes: object) -> State:
    return replace(State(status="rejected", scenario=scenario), **changes)


def scenario_state(scenario: str) -> State:
    if scenario == "closure_blockers_use_kernel":
        return _accepted(
            scenario,
            closure_kernel_used_for_blockers=True,
            local_status_predicate_used_for_progress=False,
            unknown_closure_cleared_wait=False,
            identity_mismatch_cleared_wait=False,
            ack_closure_completed_semantic_work=False,
        )
    if scenario == "registry_views_are_owner_derived":
        return _accepted(
            scenario,
            registry_authority_present=True,
            owner_module_derives_view=True,
            facade_exports_compat_alias=True,
            facade_hand_map_owns_policy=False,
            derived_view_matches_registry=True,
        )
    if scenario == "output_bindings_are_registry_first":
        return _accepted(
            scenario,
            contract_index_runtime_binding_present=True,
            python_fallback_visible_and_bounded=True,
            hidden_python_contract_fallback=False,
        )
    if scenario == "prompt_cards_share_boundary_policy":
        return _accepted(
            scenario,
            shared_prompt_policy_assets_present=True,
            card_manifest_policy_validated=True,
            card_manual_boundary_copy_only=False,
            prompt_boundary_contradiction=False,
            role_authority_expanded_by_prompt=False,
        )
    if scenario == "physical_ledgers_remain_separate":
        return _accepted(
            scenario,
            physical_ledgers_separate=True,
            physical_ledger_merge=False,
            signed_artifact_rewritten=False,
        )

    if scenario == "local_status_list_clears_unknown_wait":
        return _rejected(
            scenario,
            closure_kernel_used_for_blockers=False,
            local_status_predicate_used_for_progress=True,
            unknown_closure_cleared_wait=True,
        )
    if scenario == "facade_hand_map_drifts_from_registry":
        return _rejected(
            scenario,
            registry_authority_present=True,
            owner_module_derives_view=False,
            facade_exports_compat_alias=True,
            facade_hand_map_owns_policy=True,
            derived_view_matches_registry=False,
        )
    if scenario == "hidden_python_contract_fallback_grows":
        return _rejected(
            scenario,
            contract_index_runtime_binding_present=True,
            python_fallback_visible_and_bounded=False,
            hidden_python_contract_fallback=True,
        )
    if scenario == "manual_prompt_card_drift_weakens_boundary":
        return _rejected(
            scenario,
            shared_prompt_policy_assets_present=False,
            card_manifest_policy_validated=False,
            card_manual_boundary_copy_only=True,
            prompt_boundary_contradiction=True,
            role_authority_expanded_by_prompt=True,
        )
    if scenario == "physical_ledger_merge_blurs_authority":
        return _rejected(
            scenario,
            physical_ledgers_separate=False,
            physical_ledger_merge=True,
            signed_artifact_rewritten=True,
        )
    raise ValueError(f"unknown scenario: {scenario}")


def derived_view_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.local_status_predicate_used_for_progress:
        failures.append("progress decision used local status predicate instead of closure kernel")
    if state.unknown_closure_cleared_wait:
        failures.append("unknown closure classification cleared a wait")
    if state.identity_mismatch_cleared_wait:
        failures.append("identity-mismatched row cleared a wait")
    if state.ack_closure_completed_semantic_work:
        failures.append("ACK closure completed semantic work")
    if state.registry_authority_present and not state.owner_module_derives_view:
        failures.append("registry authority did not own derived view")
    if state.facade_hand_map_owns_policy:
        failures.append("Router facade owned hand-written policy map")
    if state.registry_authority_present and not state.derived_view_matches_registry:
        failures.append("derived view drifted from registry")
    if state.hidden_python_contract_fallback:
        failures.append("hidden Python contract fallback grew outside registry visibility")
    if state.card_manual_boundary_copy_only:
        failures.append("card boundary policy relied only on manual copied text")
    if state.prompt_boundary_contradiction:
        failures.append("prompt boundary contradicted shared policy")
    if state.role_authority_expanded_by_prompt:
        failures.append("prompt expanded role authority")
    if state.physical_ledger_merge:
        failures.append("physical ledger merge blurred authority boundaries")
    if state.signed_artifact_rewritten:
        failures.append("signed artifact was rewritten during derived-view folding")
    return failures


def accepts_only_safe_derived_views(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted":
        failures = derived_view_failures(state)
        if failures:
            return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="derived_view_prompt_boundary_safety",
        description=(
            "Derived views use registry/closure authorities, prompts share common "
            "boundary policy, and physical ledgers stay separate."
        ),
        predicate=accepts_only_safe_derived_views,
    ),
)


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return
    if state.scenario == "unset":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", replace(State(), scenario=scenario))
        return
    candidate = scenario_state(state.scenario)
    failures = derived_view_failures(candidate)
    if not failures and state.scenario in VALID_SCENARIOS:
        yield Transition(f"accept_{state.scenario}", candidate)
    else:
        yield Transition(f"reject_{state.scenario}", candidate)


class DerivedViewPromptBoundaryStep:
    """Model one derived-view or prompt-boundary fold.

    Input x State -> Set(Output x State)
    reads: closure classification, lifecycle records, registry rows, facade
    exports, contract-index bindings, prompt-policy assets, card manifest rows,
    and physical ledger authority boundaries
    writes: derived compatibility views, progress/blocker decisions,
    prompt-policy validation evidence, and bounded fallback visibility records
    idempotency: derived views are recomputed from authority rows and prompt
    validation is keyed by manifest card id plus prompt-policy asset hash
    """

    name = "DerivedViewPromptBoundaryStep"
    input_description = "one derived-view or prompt-policy review tick"
    output_description = "accepted safe fold or rejected drift hazard"
    reads = (
        "closure_kernel",
        "lifecycle_records",
        "runtime_kit_registries",
        "router_facade_exports",
        "contract_index",
        "prompt_policy_assets",
        "card_manifest",
        "physical_ledgers",
    )
    writes = (
        "derived_compatibility_views",
        "blocker_wait_decisions",
        "prompt_policy_validation",
        "fallback_visibility_records",
    )
    idempotency = "registry row id / card id / prompt policy asset hash"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(Action(transition.label), transition.state, transition.label)


def build_workflow() -> Workflow:
    return Workflow((DerivedViewPromptBoundaryStep(),), name="flowpilot_derived_view_prompt_boundary")


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def hazard_states() -> dict[str, State]:
    return {scenario: scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and state.scenario in VALID_SCENARIOS


def terminal_predicate(_input_obj: Tick, state: State, _trace) -> bool:
    return is_terminal(state)


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 2


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "NEGATIVE_SCENARIOS",
    "SCENARIOS",
    "VALID_SCENARIOS",
    "Action",
    "State",
    "Tick",
    "Transition",
    "build_workflow",
    "derived_view_failures",
    "hazard_states",
    "initial_state",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "terminal_predicate",
]
