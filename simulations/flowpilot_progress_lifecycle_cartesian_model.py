"""FlowPilot progress_fraction lifecycle Cartesian coverage model.

This model declares the finite boundary for the public progress projection:
node lifecycle status, route topology, active node_order projection, route node
kind, control-plane noise, and repair generation. The oracle is intentionally
small: progress counts non-removed route_nodes plus the display-only initial
planning node, and control-plane records never affect numerator or denominator.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any, Iterable, NamedTuple

from flowguard import (
    ContractAxis,
    ContractCoverageShard,
    ContractExhaustionPlan,
    ContractInteractionGroup,
    FunctionResult,
    Invariant,
    InvariantResult,
    Workflow,
)


MODEL_ID = "flowpilot_progress_lifecycle_cartesian"
INTERACTION_GROUP_ID = "progress_lifecycle_full_product"
FLOWGUARD_NATIVE_RECEIPT_ID = f"contract_coverage:{MODEL_ID}"
MAX_SEQUENCE_LENGTH = 2

NODE_STATUSES = (
    "pending",
    "running",
    "awaiting_pm_disposition",
    "awaiting_children",
    "accepted",
    "waived",
    "blocked",
    "stopped",
    "superseded",
    "cancelled",
    "canceled",
)
ENDED_STATUSES = ("accepted", "waived", "blocked", "stopped")
REMOVED_STATUSES = ("superseded", "cancelled", "canceled")

ROUTE_TOPOLOGIES = (
    "no_route_nodes",
    "stable_active_route",
    "supplemental_materialization_short_node_order",
    "ordinary_node_addition",
    "parallel_node_addition",
    "child_node_expansion",
    "node_internal_replan_no_new_node",
    "repair_replacement_supersedes_old",
    "branch_then_continue",
    "full_route_rewrite_supersedes_old",
)

NODE_ORDER_PROJECTIONS = (
    "complete_effective_order",
    "short_active_only",
    "missing_effective_node",
    "includes_superseded_node",
    "duplicates_effective_node",
)

NODE_KINDS = ("leaf", "parent", "module", "repair")
CONTROL_PLANE_NOISE = (
    "none",
    "packet_activity",
    "lease_ack_progress",
    "patrol_role_receipt",
    "sealed_body_payload",
)
REPAIR_GENERATIONS = ("zero", "positive")

AXIS_VALUES = {
    "node_status": NODE_STATUSES,
    "route_topology": ROUTE_TOPOLOGIES,
    "node_order_projection": NODE_ORDER_PROJECTIONS,
    "node_kind": NODE_KINDS,
    "control_plane_noise": CONTROL_PLANE_NOISE,
    "repair_generation": REPAIR_GENERATIONS,
}

VALID_CARTESIAN_RECEIPT = "valid_progress_lifecycle_cartesian_receipt"
NODE_ORDER_ABSENCE_REMOVES_NODE = "node_order_absence_removes_effective_node"
CONTROL_NOISE_CHANGES_PROGRESS = "control_noise_changes_progress"
REMOVED_NODE_REMAINS_PENDING = "removed_node_remains_pending"
PACKET_PROJECTION_USED = "packet_projection_used"

VALID_SCENARIOS = (VALID_CARTESIAN_RECEIPT,)
NEGATIVE_SCENARIOS = (
    NODE_ORDER_ABSENCE_REMOVES_NODE,
    CONTROL_NOISE_CHANGES_PROGRESS,
    REMOVED_NODE_REMAINS_PENDING,
    PACKET_PROJECTION_USED,
)
SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS


def _sanitize(value: str) -> str:
    return value.replace("_", "-")


def _repair_generation_value(repair_generation: str) -> int:
    return 2 if repair_generation == "positive" else 0


def _combination_order(
    *,
    node_status: str,
    route_topology: str,
    node_order_projection: str,
    node_kind: str,
    control_plane_noise: str,
    repair_generation: str,
) -> int:
    return (
        (
            (
                (
                    (
                        NODE_STATUSES.index(node_status) * len(ROUTE_TOPOLOGIES)
                        + ROUTE_TOPOLOGIES.index(route_topology)
                    )
                    * len(NODE_ORDER_PROJECTIONS)
                    + NODE_ORDER_PROJECTIONS.index(node_order_projection)
                )
                * len(NODE_KINDS)
                + NODE_KINDS.index(node_kind)
            )
            * len(CONTROL_PLANE_NOISE)
            + CONTROL_PLANE_NOISE.index(control_plane_noise)
        )
        * len(REPAIR_GENERATIONS)
        + REPAIR_GENERATIONS.index(repair_generation)
        + 1
    )


def _combination_case_id(cell: MappingLike) -> str:
    order = _combination_order(
        node_status=str(cell["node_status"]),
        route_topology=str(cell["route_topology"]),
        node_order_projection=str(cell["node_order_projection"]),
        node_kind=str(cell["node_kind"]),
        control_plane_noise=str(cell["control_plane_noise"]),
        repair_generation=str(cell["repair_generation"]),
    )
    return f"cartesian:{MODEL_ID}:{INTERACTION_GROUP_ID}:{order}"


MappingLike = dict[str, Any]


def _coverage_shard_id(cell: MappingLike) -> str:
    return (
        f"progress_shard:{MODEL_ID}:"
        f"{_sanitize(str(cell['route_topology']))}:"
        f"{_sanitize(str(cell['node_status']))}"
    )


def route_nodes_for_cell(cell: MappingLike) -> tuple[MappingLike, ...]:
    status = str(cell["node_status"])
    kind = str(cell["node_kind"])
    repair_generation = _repair_generation_value(str(cell["repair_generation"]))
    topology = str(cell["route_topology"])
    subject = {
        "node_id": "node-subject",
        "status": status,
        "node_kind": kind,
        "repair_generation": repair_generation,
    }
    continuation = {
        "node_id": "node-continuation",
        "status": "accepted",
        "node_kind": "leaf",
        "repair_generation": 0,
    }
    added = {
        "node_id": "node-added",
        "status": "running",
        "node_kind": "leaf",
        "repair_generation": 0,
    }
    old_superseded = {
        "node_id": "node-old-superseded",
        "status": "superseded",
        "node_kind": "leaf",
        "repair_generation": 5,
    }
    if topology == "no_route_nodes":
        return ()
    if topology == "stable_active_route":
        return (subject, continuation)
    if topology == "supplemental_materialization_short_node_order":
        return (
            {"node_id": "node-prior-accepted", "status": "accepted", "node_kind": "leaf", "repair_generation": 0},
            subject,
            {"node_id": "node-supplemental", "status": "running", "node_kind": "leaf", "repair_generation": 0},
        )
    if topology == "ordinary_node_addition":
        return (subject, added)
    if topology == "parallel_node_addition":
        return (subject, added, {"node_id": "node-parallel", "status": "pending", "node_kind": "leaf", "repair_generation": 0})
    if topology == "child_node_expansion":
        parent = {"node_id": "node-parent", "status": "awaiting_children", "node_kind": "parent", "repair_generation": 0}
        child = dict(subject, node_id="node-child", parent_node_id="node-parent")
        return (parent, child)
    if topology == "node_internal_replan_no_new_node":
        return (subject, continuation)
    if topology == "repair_replacement_supersedes_old":
        replacement = dict(subject, node_id="node-repair-replacement", node_kind="repair")
        return (old_superseded, replacement, continuation)
    if topology == "branch_then_continue":
        detour = dict(subject, node_id="node-detour")
        return (detour, continuation)
    if topology == "full_route_rewrite_supersedes_old":
        rewritten = dict(subject, node_id="node-rewrite-current")
        return (
            old_superseded,
            {"node_id": "node-old-accepted-superseded", "status": "superseded", "node_kind": "leaf", "repair_generation": 0},
            rewritten,
            continuation,
        )
    raise ValueError(f"unknown route topology: {topology}")


def _effective_node_ids(nodes: Iterable[MappingLike]) -> list[str]:
    return [
        str(node["node_id"])
        for node in nodes
        if str(node.get("status") or "").lower() not in REMOVED_STATUSES
    ]


def node_order_for_cell(cell: MappingLike, nodes: tuple[MappingLike, ...]) -> tuple[str, ...]:
    projection = str(cell["node_order_projection"])
    effective = _effective_node_ids(nodes)
    removed = [
        str(node["node_id"])
        for node in nodes
        if str(node.get("status") or "").lower() in REMOVED_STATUSES
    ]
    if projection == "complete_effective_order":
        return tuple(effective)
    if projection == "short_active_only":
        return tuple(effective[-1:])
    if projection == "missing_effective_node":
        return tuple(effective[1:])
    if projection == "includes_superseded_node":
        return tuple(effective + removed[:1])
    if projection == "duplicates_effective_node":
        return tuple(effective + effective[:1])
    raise ValueError(f"unknown node_order projection: {projection}")


def expected_progress(cell: MappingLike) -> dict[str, Any]:
    nodes = route_nodes_for_cell(cell)
    effective_nodes = [
        node
        for node in nodes
        if str(node.get("status") or "").lower() not in REMOVED_STATUSES
    ]
    if not effective_nodes:
        return {
            "display": "0/1",
            "ended_nodes": 0,
            "expanded_nodes": 1,
            "source": "initial_planning_node",
            "repair_generations": 0,
            "includes_repair_generations": False,
        }
    ended_nodes = 1 + sum(1 for node in effective_nodes if str(node.get("status") or "").lower() in ENDED_STATUSES)
    repair_generations = sum(int(node.get("repair_generation", 0) or 0) for node in effective_nodes)
    expanded_nodes = 1 + len(effective_nodes)
    return {
        "display": f"{ended_nodes}/{expanded_nodes}",
        "ended_nodes": ended_nodes,
        "expanded_nodes": expanded_nodes,
        "source": "route_nodes_lifecycle_with_initial_planning_node",
        "repair_generations": repair_generations,
        "includes_repair_generations": repair_generations > 0,
    }


def _cell(
    *,
    node_status: str,
    route_topology: str,
    node_order_projection: str,
    node_kind: str,
    control_plane_noise: str,
    repair_generation: str,
) -> MappingLike:
    cell: MappingLike = {
        "cell_id": ".".join(
            _sanitize(value)
            for value in (
                node_status,
                route_topology,
                node_order_projection,
                node_kind,
                control_plane_noise,
                repair_generation,
            )
        ),
        "model_id": MODEL_ID,
        "node_status": node_status,
        "route_topology": route_topology,
        "node_order_projection": node_order_projection,
        "node_kind": node_kind,
        "control_plane_noise": control_plane_noise,
        "repair_generation": repair_generation,
        "contract_axis_case_ids": (
            f"node_status:{node_status}",
            f"route_topology:{route_topology}",
            f"node_order_projection:{node_order_projection}",
            f"node_kind:{node_kind}",
            f"control_plane_noise:{control_plane_noise}",
            f"repair_generation:{repair_generation}",
        ),
        "coverage_receipt_id": FLOWGUARD_NATIVE_RECEIPT_ID,
        "required_evidence_owner": "progress_lifecycle_runtime_matrix",
        "validation_command": "python -m pytest tests/test_flowpilot_progress_lifecycle_cartesian.py -q",
    }
    cell["contract_combination_case_id"] = _combination_case_id(cell)
    cell["coverage_shard_id"] = _coverage_shard_id(cell)
    cell["expected_progress"] = expected_progress(cell)
    return cell


def iter_required_cells() -> Iterable[MappingLike]:
    for node_status, route_topology, node_order_projection, node_kind, control_plane_noise, repair_generation in product(
        NODE_STATUSES,
        ROUTE_TOPOLOGIES,
        NODE_ORDER_PROJECTIONS,
        NODE_KINDS,
        CONTROL_PLANE_NOISE,
        REPAIR_GENERATIONS,
    ):
        yield _cell(
            node_status=node_status,
            route_topology=route_topology,
            node_order_projection=node_order_projection,
            node_kind=node_kind,
            control_plane_noise=control_plane_noise,
            repair_generation=repair_generation,
        )


def required_cell_count() -> int:
    total = 1
    for values in AXIS_VALUES.values():
        total *= len(values)
    return total


def matrix_counts() -> dict[str, Any]:
    return {
        "full_product_count": required_cell_count(),
        "axis_counts": {axis: len(values) for axis, values in AXIS_VALUES.items()},
    }


def axis_value_coverage() -> dict[str, dict[str, Any]]:
    observed = {axis: set() for axis in AXIS_VALUES}
    for cell in iter_required_cells():
        for axis in AXIS_VALUES:
            observed[axis].add(str(cell[axis]))
    return {
        axis: {
            "expected": list(values),
            "observed": sorted(observed[axis]),
            "missing": sorted(set(values) - observed[axis]),
        }
        for axis, values in AXIS_VALUES.items()
    }


def build_flowguard_coverage_shards() -> tuple[ContractCoverageShard, ...]:
    grouped: dict[str, list[MappingLike]] = {}
    for cell in iter_required_cells():
        grouped.setdefault(str(cell["coverage_shard_id"]), []).append(cell)
    shards: list[ContractCoverageShard] = []
    for shard_id, cells in sorted(grouped.items()):
        first = cells[0]
        shards.append(
            ContractCoverageShard(
                shard_id=shard_id,
                model_id=MODEL_ID,
                interaction_group_id=INTERACTION_GROUP_ID,
                case_ids=tuple(str(cell["contract_combination_case_id"]) for cell in cells),
                complete=True,
                total_combinations=len(cells),
                generated_count=len(cells),
                skipped_count=0,
                status="covered",
                metadata={
                    "route_topology": str(first["route_topology"]),
                    "node_status": str(first["node_status"]),
                },
            )
        )
    return tuple(shards)


def build_flowguard_contract_exhaustion_plan() -> ContractExhaustionPlan:
    axes = tuple(
        ContractAxis(
            axis_id=axis,
            model_id=MODEL_ID,
            values=tuple(values),
            description=f"FlowPilot progress_fraction finite axis: {axis}.",
        )
        for axis, values in AXIS_VALUES.items()
    )
    interaction = ContractInteractionGroup(
        group_id=INTERACTION_GROUP_ID,
        model_id=MODEL_ID,
        axis_ids=tuple(AXIS_VALUES),
        required_routes=("model_test_alignment", "test_mesh"),
        max_combinations=required_cell_count(),
        oracle_status="progress_projection_matches_lifecycle_oracle",
        description="Full declared FlowPilot progress lifecycle Cartesian product.",
    )
    return ContractExhaustionPlan(
        plan_id=f"{MODEL_ID}.native_cartesian",
        model_id=MODEL_ID,
        model_level="leaf",
        axes=axes,
        interaction_groups=(interaction,),
        coverage_shards=build_flowguard_coverage_shards(),
        claim_scope="routine",
        required_route_ids=("model_test_alignment", "test_mesh"),
        require_model_coverage_receipt=True,
        cartesian_case_limit=required_cell_count(),
        metadata={
            "full_product_count": required_cell_count(),
            "removed_statuses": REMOVED_STATUSES,
            "ended_statuses": ENDED_STATUSES,
        },
    )


@dataclass(frozen=True)
class Tick:
    """One abstract progress lifecycle coverage tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"
    scenario: str = "unset"
    full_product_declared: bool = False
    runtime_matrix_passed: bool = False
    node_order_projection_independent: bool = False
    control_noise_independent: bool = False
    removed_status_excluded: bool = False
    packet_projection_used: bool = False
    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


class ProgressLifecycleCartesianStep:
    """Model progress matrix closure.

    Input x State -> Set(Output x State)
    reads: declared axes, runtime matrix result, node_order/noise invariants,
    removed-status handling, packet projection flag
    writes: terminal coverage decision
    """

    name = "ProgressLifecycleCartesianStep"
    input_description = "FlowPilot progress lifecycle Cartesian coverage tick"
    output_description = "one progress-lifecycle coverage transition"
    reads = (
        "full_product_declared",
        "runtime_matrix_passed",
        "node_order_projection_independent",
        "control_noise_independent",
        "removed_status_excluded",
        "packet_projection_used",
    )
    writes = ("terminal_progress_lifecycle_coverage_decision",)
    idempotency = "monotonic coverage evidence evaluation"

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
    return State(
        status="running",
        scenario=VALID_CARTESIAN_RECEIPT,
        full_product_declared=True,
        runtime_matrix_passed=True,
        node_order_projection_independent=True,
        control_noise_independent=True,
        removed_status_excluded=True,
        packet_projection_used=False,
    )


def hazard_states() -> dict[str, State]:
    base = _valid_state()
    return {
        NODE_ORDER_ABSENCE_REMOVES_NODE: State(
            status="running",
            scenario=NODE_ORDER_ABSENCE_REMOVES_NODE,
            full_product_declared=True,
            runtime_matrix_passed=False,
            node_order_projection_independent=False,
            control_noise_independent=True,
            removed_status_excluded=True,
            packet_projection_used=False,
        ),
        CONTROL_NOISE_CHANGES_PROGRESS: State(
            status="running",
            scenario=CONTROL_NOISE_CHANGES_PROGRESS,
            full_product_declared=True,
            runtime_matrix_passed=False,
            node_order_projection_independent=True,
            control_noise_independent=False,
            removed_status_excluded=True,
            packet_projection_used=False,
        ),
        REMOVED_NODE_REMAINS_PENDING: State(
            status="running",
            scenario=REMOVED_NODE_REMAINS_PENDING,
            full_product_declared=True,
            runtime_matrix_passed=False,
            node_order_projection_independent=True,
            control_noise_independent=True,
            removed_status_excluded=False,
            packet_projection_used=False,
        ),
        PACKET_PROJECTION_USED: State(
            status="running",
            scenario=PACKET_PROJECTION_USED,
            full_product_declared=True,
            runtime_matrix_passed=False,
            node_order_projection_independent=True,
            control_noise_independent=True,
            removed_status_excluded=True,
            packet_projection_used=True,
        ),
    }


def coverage_failures(state: State) -> list[str]:
    failures: list[str] = []
    if not state.full_product_declared:
        failures.append("progress lifecycle Cartesian product was not declared")
    if not state.runtime_matrix_passed:
        failures.append("runtime progress output diverged from lifecycle oracle")
    if not state.node_order_projection_independent:
        failures.append("active node_order projection changed progress counts")
    if not state.control_noise_independent:
        failures.append("control-plane packet lease patrol or sealed-body noise changed progress counts")
    if not state.removed_status_excluded:
        failures.append("formally removed route node remained visible as pending or active progress")
    if state.packet_projection_used:
        failures.append("packet projection was used for progress_fraction")
    return failures


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if state.status == "new":
        transitions = [Transition(f"select_{VALID_CARTESIAN_RECEIPT}", _valid_state())]
        transitions.extend(Transition(f"select_{name}", hazard) for name, hazard in hazard_states().items())
        return tuple(transitions)
    if state.status == "running":
        failures = coverage_failures(state)
        if failures:
            return (
                Transition(
                    f"reject_{state.scenario}",
                    State(**{**state.__dict__, "status": "rejected", "terminal_reason": "; ".join(failures)}),
                ),
            )
        return (
            Transition(
                f"accept_{state.scenario}",
                State(**{**state.__dict__, "status": "accepted", "terminal_reason": "progress lifecycle matrix accepted"}),
            ),
        )
    return ()


def invariant_failures(state: State) -> list[str]:
    if state.status in {"accepted", "rejected"}:
        return []
    if state.scenario == VALID_CARTESIAN_RECEIPT:
        return coverage_failures(state)
    return []


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and state.scenario == VALID_CARTESIAN_RECEIPT


def expected_failures_by_hazard() -> dict[str, list[str]]:
    return {name: coverage_failures(state) for name, state in hazard_states().items()}


def accepted_states_are_safe(state: State, _trace: object) -> InvariantResult:
    if state.status == "accepted":
        failures = coverage_failures(state)
        if failures:
            return InvariantResult.fail("; ".join(failures))
    if state.status == "rejected" and not coverage_failures(state):
        return InvariantResult.fail("safe progress lifecycle Cartesian state was rejected")
    return InvariantResult.pass_()


EXTERNAL_INPUTS = (Tick(),)
INVARIANTS = (
    Invariant(
        "accepted_states_are_safe",
        "Accepted progress lifecycle Cartesian states cannot miss product coverage, depend on node_order, depend on control-plane noise, retain removed nodes, or use packet projection.",
        accepted_states_are_safe,
    ),
)


def build_workflow() -> Workflow:
    return Workflow((ProgressLifecycleCartesianStep(),), name=MODEL_ID)
