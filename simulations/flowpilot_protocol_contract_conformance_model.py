"""FlowGuard model for concrete FlowPilot protocol/contract conformance.

This model covers the failure class that the broader startup and output
contract models intentionally abstract away: concrete JSON paths, event names,
file-backed path/hash lifecycle, and host display receipts must line up across
cards, the contract registry, and router validation.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_FIXED_PROTOCOL = "valid_fixed_protocol"
STARTUP_FACT_JSONPATH_MISMATCH = "startup_fact_jsonpath_mismatch"
CONTROL_BLOCKER_AMBIGUOUS_EVENT = "control_blocker_ambiguous_event"
CONTROL_BLOCKER_WEAK_DECISION_CONTRACT = "control_blocker_weak_decision_contract"
STARTUP_FACT_HASH_ALIAS = "startup_fact_hash_alias"
COCKPIT_MISSING_HOST_RECEIPT = "cockpit_missing_host_receipt"

NEGATIVE_SCENARIOS = (
    STARTUP_FACT_JSONPATH_MISMATCH,
    CONTROL_BLOCKER_AMBIGUOUS_EVENT,
    CONTROL_BLOCKER_WEAK_DECISION_CONTRACT,
    STARTUP_FACT_HASH_ALIAS,
    COCKPIT_MISSING_HOST_RECEIPT,
)
SCENARIOS = (VALID_FIXED_PROTOCOL, *NEGATIVE_SCENARIOS)

STARTUP_FACT_CONTRACT_ID = "flowpilot.output_contract.startup_fact_report.v1"
PM_CONTROL_BLOCKER_CONTRACT_ID = "flowpilot.output_contract.pm_control_blocker_repair_decision.v1"
REVIEWER_IDS_PATH = "external_fact_review.reviewer_checked_requirement_ids"
TOP_LEVEL_REVIEWER_IDS_PATH = "reviewer_checked_requirement_ids"
PM_CONTROL_BLOCKER_EVENT = "pm_records_control_blocker_repair_decision"
PM_STARTUP_REPAIR_EVENT = "pm_requests_startup_repair"

PM_CONTROL_BLOCKER_REQUIRED_FIELDS = frozenset(
    {
        "decided_by_role",
        "blocker_id",
        "decision",
        "prior_path_context_review",
        "repair_action",
        "rerun_target",
        "blockers",
        "contract_self_check",
    }
)


@dataclass(frozen=True)
class Tick:
    """One protocol conformance tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | rejected
    scenario: str = "unset"

    startup_contract_paths: frozenset[str] = field(default_factory=frozenset)
    startup_card_example_paths: frozenset[str] = field(default_factory=frozenset)
    startup_card_prose_paths: frozenset[str] = field(default_factory=frozenset)
    startup_router_validator_paths: frozenset[str] = field(default_factory=frozenset)
    startup_router_canonical_paths: frozenset[str] = field(default_factory=frozenset)

    pm_control_blocker_allowed_events: frozenset[str] = field(default_factory=frozenset)
    pm_control_blocker_card_events: frozenset[str] = field(default_factory=frozenset)
    pm_startup_repair_requires_activation_card: bool = True
    control_blocker_action_delivers_review_repair_card: bool = False

    pm_control_blocker_contract_fields: frozenset[str] = field(default_factory=frozenset)
    pm_control_blocker_router_fields: frozenset[str] = field(default_factory=frozenset)
    pm_control_blocker_card_fields: frozenset[str] = field(default_factory=frozenset)

    router_rewrites_startup_fact_canonical: bool = True
    startup_role_may_submit_to_canonical_path: bool = True
    router_blocks_startup_fact_canonical_alias: bool = False

    display_requested_cockpit: bool = False
    display_has_host_receipt: bool = False
    display_has_explicit_fallback: bool = False

    router_decision: str = "none"  # none | accept | reject
    router_rejection_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


class ProtocolConformanceStep:
    """Model one concrete FlowPilot protocol conformance transition.

    Input x State -> Set(Output x State)
    reads: card JSON paths, contract fields, router validators, event
    preconditions, path/hash alias rules, and display receipt facts.
    writes: one scenario selection or terminal protocol decision.
    idempotency: repeated ticks do not duplicate scenario facts or terminal
    decisions.
    """

    name = "ProtocolConformanceStep"
    reads = (
        "card_jsonpaths",
        "contract_registry_fields",
        "router_validator_fields",
        "event_preconditions",
        "file_backed_hash_lifecycle",
        "display_receipts",
    )
    writes = ("scenario_facts", "terminal_protocol_decision")
    input_description = "protocol conformance tick"
    output_description = "one abstract protocol conformance action"
    idempotency = "repeat ticks leave scenario and terminal decision unchanged"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def initial_state() -> State:
    return State()


def _valid_state() -> State:
    startup_paths = frozenset(
        {
            "reviewed_by_role",
            "passed",
            "external_fact_review",
            "external_fact_review.reviewed_by_role",
            "external_fact_review.direct_evidence_paths_checked",
            "external_fact_review.used_router_mechanical_audit",
            "external_fact_review.router_mechanical_audit_hash",
            "external_fact_review.self_attested_ai_claims_accepted_as_proof",
            REVIEWER_IDS_PATH,
            "findings",
            "blockers",
            "residual_risks",
            "contract_self_check",
        }
    )
    return State(
        status="running",
        scenario=VALID_FIXED_PROTOCOL,
        startup_contract_paths=startup_paths,
        startup_card_example_paths=startup_paths,
        startup_card_prose_paths=frozenset({REVIEWER_IDS_PATH}),
        startup_router_validator_paths=frozenset({REVIEWER_IDS_PATH}),
        startup_router_canonical_paths=frozenset({REVIEWER_IDS_PATH}),
        pm_control_blocker_allowed_events=frozenset({PM_CONTROL_BLOCKER_EVENT}),
        pm_control_blocker_card_events=frozenset({PM_CONTROL_BLOCKER_EVENT}),
        pm_control_blocker_contract_fields=PM_CONTROL_BLOCKER_REQUIRED_FIELDS,
        pm_control_blocker_router_fields=PM_CONTROL_BLOCKER_REQUIRED_FIELDS,
        pm_control_blocker_card_fields=PM_CONTROL_BLOCKER_REQUIRED_FIELDS,
        router_rewrites_startup_fact_canonical=True,
        startup_role_may_submit_to_canonical_path=False,
        router_blocks_startup_fact_canonical_alias=True,
        display_requested_cockpit=True,
        display_has_host_receipt=True,
        display_has_explicit_fallback=False,
    )


def _scenario_state(scenario: str) -> State:
    state = _valid_state()
    state = replace(state, scenario=scenario)
    if scenario == STARTUP_FACT_JSONPATH_MISMATCH:
        return replace(
            state,
            startup_contract_paths=(state.startup_contract_paths - frozenset({REVIEWER_IDS_PATH}))
            | frozenset({TOP_LEVEL_REVIEWER_IDS_PATH}),
            startup_card_example_paths=(state.startup_card_example_paths - frozenset({REVIEWER_IDS_PATH}))
            | frozenset({TOP_LEVEL_REVIEWER_IDS_PATH}),
        )
    if scenario == CONTROL_BLOCKER_AMBIGUOUS_EVENT:
        return replace(
            state,
            pm_control_blocker_allowed_events=frozenset({PM_CONTROL_BLOCKER_EVENT, PM_STARTUP_REPAIR_EVENT}),
            pm_control_blocker_card_events=frozenset({PM_STARTUP_REPAIR_EVENT}),
            control_blocker_action_delivers_review_repair_card=False,
        )
    if scenario == CONTROL_BLOCKER_WEAK_DECISION_CONTRACT:
        weak_fields = frozenset({"decided_by_role", "blocker_id", "decision"})
        return replace(
            state,
            pm_control_blocker_contract_fields=weak_fields,
            pm_control_blocker_router_fields=weak_fields,
        )
    if scenario == STARTUP_FACT_HASH_ALIAS:
        return replace(
            state,
            startup_role_may_submit_to_canonical_path=True,
            router_blocks_startup_fact_canonical_alias=False,
        )
    if scenario == COCKPIT_MISSING_HOST_RECEIPT:
        return replace(
            state,
            display_requested_cockpit=True,
            display_has_host_receipt=False,
            display_has_explicit_fallback=False,
        )
    return state


def _jsonpath_failures(state: State) -> list[str]:
    failures: list[str] = []
    router_paths = state.startup_router_validator_paths | state.startup_router_canonical_paths
    if REVIEWER_IDS_PATH not in router_paths:
        failures.append("startup fact router validator does not require nested reviewer_checked_requirement_ids")
    sources = {
        "startup fact output contract": state.startup_contract_paths,
        "startup fact card example": state.startup_card_example_paths,
        "startup fact card prose": state.startup_card_prose_paths,
    }
    for name, paths in sources.items():
        if REVIEWER_IDS_PATH not in paths:
            failures.append(f"{name} does not expose router-required {REVIEWER_IDS_PATH}")
        if TOP_LEVEL_REVIEWER_IDS_PATH in paths and REVIEWER_IDS_PATH not in paths:
            failures.append(f"{name} exposes top-level reviewer_checked_requirement_ids instead of nested path")
    return failures


def _control_blocker_event_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.pm_control_blocker_allowed_events != frozenset({PM_CONTROL_BLOCKER_EVENT}):
        failures.append("PM control-blocker lane does not narrow allowed_resolution_events to pm_records_control_blocker_repair_decision")
    if (
        PM_CONTROL_BLOCKER_EVENT not in state.pm_control_blocker_card_events
        and not state.control_blocker_action_delivers_review_repair_card
    ):
        failures.append("PM control-blocker guidance does not name the legal repair-decision event")
    if (
        PM_STARTUP_REPAIR_EVENT in state.pm_control_blocker_allowed_events
        and state.pm_startup_repair_requires_activation_card
    ):
        failures.append("PM control-blocker lane allows startup repair event whose startup activation card precondition may be unsatisfied")
    return failures


def _control_blocker_contract_failures(state: State) -> list[str]:
    failures: list[str] = []
    missing_contract = PM_CONTROL_BLOCKER_REQUIRED_FIELDS - state.pm_control_blocker_contract_fields
    missing_router = PM_CONTROL_BLOCKER_REQUIRED_FIELDS - state.pm_control_blocker_router_fields
    missing_card = PM_CONTROL_BLOCKER_REQUIRED_FIELDS - state.pm_control_blocker_card_fields
    if missing_contract:
        failures.append("PM control-blocker output contract omits required fields: " + ", ".join(sorted(missing_contract)))
    if missing_router:
        failures.append("router control-blocker decision validator omits required fields: " + ", ".join(sorted(missing_router)))
    if missing_card:
        failures.append("PM control-blocker card omits required fields: " + ", ".join(sorted(missing_card)))
    return failures


def _hash_lifecycle_failures(state: State) -> list[str]:
    if (
        state.router_rewrites_startup_fact_canonical
        and state.startup_role_may_submit_to_canonical_path
        and not state.router_blocks_startup_fact_canonical_alias
    ):
        return [
            "startup fact role submission can alias router canonical report path before router rewrites the canonical file"
        ]
    return []


def _display_receipt_failures(state: State) -> list[str]:
    if state.display_requested_cockpit and not (
        state.display_has_host_receipt or state.display_has_explicit_fallback
    ):
        return ["cockpit requested without host receipt or explicit fallback receipt"]
    return []


def protocol_failures(state: State) -> list[str]:
    failures: list[str] = []
    failures.extend(_jsonpath_failures(state))
    failures.extend(_control_blocker_event_failures(state))
    failures.extend(_control_blocker_contract_failures(state))
    failures.extend(_hash_lifecycle_failures(state))
    failures.extend(_display_receipt_failures(state))
    return failures


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return

    if state.status == "new":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", _scenario_state(scenario))
        return

    failures = protocol_failures(state)
    if failures:
        reason = failures[0]
        yield Transition(
            f"router_rejects_{state.scenario}",
            replace(
                state,
                status="rejected",
                router_decision="reject",
                router_rejection_reason=reason,
            ),
        )
        return

    yield Transition(
        "router_accepts_conformant_protocol",
        replace(state, status="accepted", router_decision="accept"),
    )


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return is_terminal(state)


def accepted_protocol_conforms(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    failures = protocol_failures(state)
    if failures:
        return InvariantResult.fail(failures[0])
    return InvariantResult.pass_()


def negative_scenarios_are_rejected(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.scenario in NEGATIVE_SCENARIOS:
        return InvariantResult.fail(f"router accepted negative protocol scenario {state.scenario}")
    if state.status == "rejected" and state.scenario == VALID_FIXED_PROTOCOL:
        return InvariantResult.fail(f"router rejected valid protocol scenario: {state.router_rejection_reason}")
    return InvariantResult.pass_()


def terminal_decisions_are_explicit(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.router_decision != "accept":
        return InvariantResult.fail("accepted terminal state lacks accept decision")
    if state.status == "rejected" and (
        state.router_decision != "reject" or not state.router_rejection_reason
    ):
        return InvariantResult.fail("rejected terminal state lacks explicit rejection reason")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="accepted_protocol_conforms",
        description="Accepted protocol states must align concrete cards, contracts, router validators, path/hash lifecycle, and display receipts.",
        predicate=accepted_protocol_conforms,
    ),
    Invariant(
        name="negative_scenarios_are_rejected",
        description="Known-bad protocol scenarios must be rejected while the fixed protocol is accepted.",
        predicate=negative_scenarios_are_rejected,
    ),
    Invariant(
        name="terminal_decisions_are_explicit",
        description="Terminal protocol states must carry an explicit router accept/reject decision.",
        predicate=terminal_decisions_are_explicit,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 3


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def build_workflow() -> Workflow:
    return Workflow((ProtocolConformanceStep(),), name="flowpilot_protocol_contract_conformance")


def terminal_predicate(_input_obj, state: State, _trace) -> bool:
    return is_terminal(state)


def hazard_states() -> dict[str, State]:
    return {
        scenario: replace(_scenario_state(scenario), status="accepted", router_decision="accept")
        for scenario in NEGATIVE_SCENARIOS
    }


def _load_router(project_root: Path) -> Any:
    assets_root = project_root / "skills" / "flowpilot" / "assets"
    router_path = assets_root / "flowpilot_router.py"
    sys.path.insert(0, str(assets_root))
    spec = importlib.util.spec_from_file_location(
        "flowpilot_router_for_protocol_contract_conformance", router_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load router module from {router_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _contract_fields(project_root: Path, contract_id: str) -> frozenset[str]:
    contract_path = project_root / "skills" / "flowpilot" / "assets" / "runtime_kit" / "contracts" / "contract_index.json"
    payload = json.loads(contract_path.read_text(encoding="utf-8"))
    for contract in payload.get("contracts", []):
        if isinstance(contract, dict) and contract.get("contract_id") == contract_id:
            return frozenset(str(field) for field in contract.get("required_body_fields", []))
    raise RuntimeError(f"missing contract {contract_id}")


def _flatten_json_paths(value: Any, prefix: str = "") -> set[str]:
    paths: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            paths.add(path)
            paths.update(_flatten_json_paths(child, path))
    return paths


def _first_json_block_paths(text: str) -> frozenset[str]:
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if not match:
        return frozenset()
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return frozenset()
    return frozenset(_flatten_json_paths(payload))


def _startup_card_prose_paths(text: str) -> frozenset[str]:
    marker = "Your report body must include `external_fact_review` with:"
    if marker not in text:
        return frozenset()
    section = text.split(marker, 1)[1].split("## Report Contract", 1)[0]
    paths: set[str] = set()
    if "reviewer_checked_requirement_ids" in section:
        paths.add(REVIEWER_IDS_PATH)
    return frozenset(paths)


def _function_segment(source: str, function_name: str) -> str:
    match = re.search(rf"^def {re.escape(function_name)}\(.*?(?=^def |\Z)", source, re.DOTALL | re.MULTILINE)
    return match.group(0) if match else ""


def _startup_router_validator_paths(router_source: str) -> frozenset[str]:
    segment = _function_segment(router_source, "_validate_startup_external_fact_review")
    paths = {"external_fact_review"}
    for field_name in re.findall(r'review\.get\("([^"]+)"\)', segment):
        paths.add(f"external_fact_review.{field_name}")
    return frozenset(paths)


def _startup_router_canonical_paths(router_source: str) -> frozenset[str]:
    segment = _function_segment(router_source, "_validate_startup_external_fact_review")
    if f'"{TOP_LEVEL_REVIEWER_IDS_PATH}"' in segment:
        return frozenset({REVIEWER_IDS_PATH})
    return frozenset()


def _pm_control_blocker_router_fields(router_source: str) -> frozenset[str]:
    segment = _function_segment(router_source, "_write_control_blocker_repair_decision")
    fields = set(re.findall(r'decision\.get\("([^"]+)"\)', segment))
    if 'decision["decision"]' in segment or "decision['decision']" in segment:
        fields.add("decision")
    return frozenset(fields)


def _pm_control_blocker_card_events(*texts: str) -> frozenset[str]:
    events = set()
    combined = "\n".join(texts)
    if PM_CONTROL_BLOCKER_EVENT in combined:
        events.add(PM_CONTROL_BLOCKER_EVENT)
    if PM_STARTUP_REPAIR_EVENT in combined:
        events.add(PM_STARTUP_REPAIR_EVENT)
    return frozenset(events)


def _pm_control_blocker_allowed_events(router: Any) -> frozenset[str]:
    policy = router._control_blocker_policy(  # noqa: SLF001 - source conformance probe
        "pm_repair_decision_required",
        responsible_role="project_manager",
        event="reviewer_reports_startup_facts",
    )
    raw = policy.get("allowed_resolution_events")
    if not isinstance(raw, list):
        return frozenset()
    return frozenset(str(item) for item in raw)


def _router_rewrites_startup_fact_canonical(router_source: str) -> bool:
    segment = _function_segment(router_source, "_write_startup_fact_report")
    return 'run_root / "startup" / "startup_fact_report.json"' in segment and "write_json(" in segment


def _router_blocks_startup_fact_canonical_alias(router_source: str) -> bool:
    segment = _function_segment(router_source, "_write_startup_fact_report")
    return "canonical startup_fact_report.json" in segment and "report_path" in segment


def _startup_role_may_submit_to_canonical_path(card_text: str) -> bool:
    lower = card_text.lower()
    asks_for_startup_fact_report_file = "startup fact report file" in lower
    separates_submission = (
        "startup fact report submission" in lower
        or "raw submission" in lower
        or "must not be the router canonical" in lower
    )
    return asks_for_startup_fact_report_file and not separates_submission


def collect_source_state(project_root: Path) -> State:
    router = _load_router(project_root)
    router_path = project_root / "skills" / "flowpilot" / "assets" / "flowpilot_router.py"
    router_source = router_path.read_text(encoding="utf-8")
    runtime_root = project_root / "skills" / "flowpilot" / "assets" / "runtime_kit"
    startup_card_text = (runtime_root / "cards" / "reviewer" / "startup_fact_check.md").read_text(encoding="utf-8")
    pm_core_text = (runtime_root / "cards" / "roles" / "project_manager.md").read_text(encoding="utf-8")
    pm_startup_text = (runtime_root / "cards" / "phases" / "pm_startup_activation.md").read_text(encoding="utf-8")
    pm_repair_text = (runtime_root / "cards" / "phases" / "pm_review_repair.md").read_text(encoding="utf-8")

    pm_startup_repair_requires_activation = (
        router.EXTERNAL_EVENTS.get(PM_STARTUP_REPAIR_EVENT, {}).get("requires_flag")
        == "pm_startup_activation_card_delivered"
    )

    return State(
        status="accepted",
        scenario="current_source",
        startup_contract_paths=_contract_fields(project_root, STARTUP_FACT_CONTRACT_ID),
        startup_card_example_paths=_first_json_block_paths(startup_card_text),
        startup_card_prose_paths=_startup_card_prose_paths(startup_card_text),
        startup_router_validator_paths=_startup_router_validator_paths(router_source),
        startup_router_canonical_paths=_startup_router_canonical_paths(router_source),
        pm_control_blocker_allowed_events=_pm_control_blocker_allowed_events(router),
        pm_control_blocker_card_events=_pm_control_blocker_card_events(
            pm_core_text,
            pm_startup_text,
            pm_repair_text,
        ),
        pm_startup_repair_requires_activation_card=pm_startup_repair_requires_activation,
        control_blocker_action_delivers_review_repair_card="card_id=\"pm.review_repair\"" in router_source
        or '"card_id": "pm.review_repair"' in router_source,
        pm_control_blocker_contract_fields=_contract_fields(project_root, PM_CONTROL_BLOCKER_CONTRACT_ID),
        pm_control_blocker_router_fields=_pm_control_blocker_router_fields(router_source),
        pm_control_blocker_card_fields=_first_json_block_paths(pm_repair_text),
        router_rewrites_startup_fact_canonical=_router_rewrites_startup_fact_canonical(router_source),
        startup_role_may_submit_to_canonical_path=_startup_role_may_submit_to_canonical_path(startup_card_text),
        router_blocks_startup_fact_canonical_alias=_router_blocks_startup_fact_canonical_alias(router_source),
        display_requested_cockpit=False,
        display_has_host_receipt=True,
    )


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "NEGATIVE_SCENARIOS",
    "PM_CONTROL_BLOCKER_EVENT",
    "PM_CONTROL_BLOCKER_REQUIRED_FIELDS",
    "SCENARIOS",
    "VALID_FIXED_PROTOCOL",
    "Action",
    "State",
    "Tick",
    "Transition",
    "build_workflow",
    "collect_source_state",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "protocol_failures",
    "terminal_predicate",
]
