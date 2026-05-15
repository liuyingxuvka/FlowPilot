"""FlowGuard model for FlowPilot cross-plane runtime friction.

Risk intent brief:
- Catch failures that only appear when one run is projected through several
  durable planes at once: router state, execution frontier, packet ledger,
  terminal lifecycle, route_state_snapshot, Cockpit adapter state, source
  layout policy, and the installed skill copy.
- Preserve Controller's envelope-only runtime boundary. The live audit reads
  JSON metadata and packet/result envelopes, but it does not open packet,
  result, report, or decision body files.
- Critical durable state: material-scan packet/result envelopes, run lifecycle
  record, terminal closure suite, execution frontier completed_nodes,
  route_state_snapshot node/checklist projection, Cockpit active tabs,
  router external-event taxonomy, local install sync policy, and standard
  six-role readiness or blocker state.
- Adversarial branches include terminal closure without a canonical lifecycle
  record, completed frontier nodes displayed as pending, completed checklists
  left pending in UI projections, material packets without explicit result
  write targets, role-blocker events outside EXTERNAL_EVENTS, Cockpit source
  layout rejected by the install audit after Cockpit became first-class, node
  completion idempotency scoped only by a global flag, and a standard six-role
  start that has neither readiness proof nor an early blocker.
- Hard invariant: every user-visible or automation-visible plane must derive
  status from the same authoritative run facts, and every repair strategy must
  close the exact failing plane without weakening Controller boundaries.
- Blindspot: this model proves runtime/control-plane consistency. It does not
  judge the product quality of a role's sealed report body.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


TERMINAL_STATUSES = frozenset(
    {
        "closed",
        "complete",
        "completed",
        "terminal",
        "stopped",
        "stopped_by_user",
        "cancelled",
        "cancelled_by_user",
        "protocol_dead_end",
    }
)
ACTIVE_STATUSES = frozenset({"running", "active", "in_progress", "current"})
DONE_ITEM_STATUSES = frozenset({"complete", "completed", "done", "passed", "closed"})
STANDARD_SIX_ROLES = frozenset(
    {
        "project_manager",
        "human_like_reviewer",
        "process_flowguard_officer",
        "product_flowguard_officer",
        "worker_a",
        "worker_b",
    }
)
BODY_PATH_NAMES = frozenset(
    {
        "packet_body.md",
        "result_body.md",
        "report_body.md",
        "decision_body.md",
    }
)


@dataclass(frozen=True)
class Tick:
    """One cross-plane reconciliation tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"
    step: int = 0

    controller_boundary_preserved: bool = False
    sealed_body_files_opened_by_controller: bool = False

    material_scan_packets_observed: bool = False
    material_output_contract_role_scoped: bool = True
    material_dispatch_write_target_explicit: bool = True
    material_legacy_packets_quarantined_or_migrated: bool = True

    terminal_closure_observed: bool = False
    run_lifecycle_record_written: bool = True
    router_frontier_lifecycle_terminal_consistent: bool = True
    terminal_control_blocker_cleared: bool = True
    heartbeat_inactive_after_terminal: bool = True

    completed_nodes_observed: bool = False
    route_snapshot_visible: bool = False
    route_snapshot_status_derived_from_frontier: bool = True
    route_snapshot_checklists_complete_for_completed_nodes: bool = True
    selected_status_separate_from_completion: bool = True

    cockpit_projection_visible: bool = False
    cockpit_status_derived_from_frontier: bool = True
    cockpit_checklists_complete_for_completed_nodes: bool = True
    cockpit_closed_runs_hidden_from_active_tabs: bool = True

    reviewer_block_events_observed: bool = False
    reviewer_block_events_registered: bool = True
    role_event_artifacts_scanned: bool = False
    gate_outcome_contracts_observed: bool = False
    gate_outcome_contracts_complete: bool = True

    node_completion_observed: bool = False
    node_completion_idempotency_scoped_to_active_node: bool = True

    cockpit_source_present_in_tree: bool = False
    install_audit_policy_accepts_first_class_cockpit: bool = True
    installed_skill_matches_repository_source: bool = True

    standard_six_roles_requested: bool = False
    role_liveness_ready_or_blocked: bool = True

    active_task_policy_observed: bool = False
    history_default_hidden: bool = True
    current_pointer_is_ui_focus_only: bool = True
    active_task_set_has_explicit_authority: bool = True

    minimal_repair_strategy_selected: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _inc(state: State, **changes: object) -> State:
    next_status = str(changes.pop("status", "running"))
    return replace(state, step=state.step + 1, status=next_status, **changes)


class CrossPlaneReconciliationStep:
    """One FlowPilot cross-plane reconciliation transition.

    Input x State -> Set(Output x State)
    reads: router_state, execution_frontier, packet ledger/envelopes,
      terminal closure suite, run lifecycle record, route_state_snapshot,
      Cockpit adapter output, external-event taxonomy, install sync policy
    writes: abstract proof facts only; this model never mutates production
      runtime files
    idempotency: reconciliation is keyed by run_id, route_version, active node,
      and packet/result envelope identity rather than a single global flag
    """

    name = "CrossPlaneReconciliationStep"
    input_description = "cross-plane runtime reconciliation tick"
    output_description = "one FlowPilot cross-plane consistency transition"
    reads = (
        "router_state",
        "execution_frontier",
        "packet_envelopes",
        "terminal_lifecycle",
        "route_state_snapshot",
        "cockpit_projection",
        "external_event_taxonomy",
        "install_sync_policy",
    )
    writes = ("abstract_consistency_fact",)
    idempotency = "run_id/route_version/active_node/packet identity scoped"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "complete":
        return

    if not state.controller_boundary_preserved:
        yield Transition(
            "controller_boundary_preserved_for_cross_plane_audit",
            _inc(state, controller_boundary_preserved=True),
        )
        return

    if not state.material_scan_packets_observed:
        yield Transition(
            "material_scan_envelopes_have_role_contracts_and_write_targets",
            _inc(
                state,
                material_scan_packets_observed=True,
                material_output_contract_role_scoped=True,
                material_dispatch_write_target_explicit=True,
                material_legacy_packets_quarantined_or_migrated=True,
            ),
        )
        return

    if not state.terminal_closure_observed:
        yield Transition(
            "terminal_closure_writes_single_lifecycle_authority",
            _inc(
                state,
                terminal_closure_observed=True,
                run_lifecycle_record_written=True,
                router_frontier_lifecycle_terminal_consistent=True,
                terminal_control_blocker_cleared=True,
                heartbeat_inactive_after_terminal=True,
            ),
        )
        return

    if not state.completed_nodes_observed:
        yield Transition(
            "route_snapshot_projects_completed_frontier_nodes",
            _inc(
                state,
                completed_nodes_observed=True,
                route_snapshot_visible=True,
                route_snapshot_status_derived_from_frontier=True,
                route_snapshot_checklists_complete_for_completed_nodes=True,
                selected_status_separate_from_completion=True,
            ),
        )
        return

    if not state.cockpit_projection_visible:
        yield Transition(
            "cockpit_projects_completed_nodes_and_hides_closed_runs",
            _inc(
                state,
                cockpit_projection_visible=True,
                cockpit_status_derived_from_frontier=True,
                cockpit_checklists_complete_for_completed_nodes=True,
                cockpit_closed_runs_hidden_from_active_tabs=True,
            ),
        )
        return

    if not state.reviewer_block_events_observed:
        yield Transition(
            "reviewer_block_events_registered_in_router_taxonomy",
            _inc(
                state,
                reviewer_block_events_observed=True,
                reviewer_block_events_registered=True,
            ),
        )
        return

    if not state.role_event_artifacts_scanned:
        yield Transition(
            "role_output_event_artifacts_scanned",
            _inc(state, role_event_artifacts_scanned=True),
        )
        return

    if not state.gate_outcome_contracts_observed:
        yield Transition(
            "gate_outcome_contracts_cover_non_pass_paths",
            _inc(
                state,
                gate_outcome_contracts_observed=True,
                gate_outcome_contracts_complete=True,
            ),
        )
        return

    if not state.node_completion_observed:
        yield Transition(
            "node_completion_idempotency_scoped_to_active_node",
            _inc(
                state,
                node_completion_observed=True,
                node_completion_idempotency_scoped_to_active_node=True,
            ),
        )
        return

    if not state.cockpit_source_present_in_tree:
        yield Transition(
            "install_policy_accepts_first_class_cockpit_source",
            _inc(
                state,
                cockpit_source_present_in_tree=True,
                install_audit_policy_accepts_first_class_cockpit=True,
                installed_skill_matches_repository_source=True,
            ),
        )
        return

    if not state.standard_six_roles_requested:
        yield Transition(
            "standard_six_roles_ready_or_blocked_before_route_work",
            _inc(
                state,
                standard_six_roles_requested=True,
                role_liveness_ready_or_blocked=True,
            ),
        )
        return

    if not state.active_task_policy_observed:
        yield Transition(
            "active_task_catalog_uses_focus_pointer_and_explicit_active_set",
            _inc(
                state,
                active_task_policy_observed=True,
                history_default_hidden=True,
                current_pointer_is_ui_focus_only=True,
                active_task_set_has_explicit_authority=True,
            ),
        )
        return

    if not state.minimal_repair_strategy_selected:
        yield Transition(
            "minimal_repair_strategy_satisfies_cross_plane_invariants",
            _inc(state, minimal_repair_strategy_selected=True, status="complete"),
        )


def _ok(message: str = "") -> InvariantResult:
    return InvariantResult(True, message)


def _fail(message: str) -> InvariantResult:
    return InvariantResult(False, message)


def controller_keeps_envelope_only_boundary(state: State, _trace: object) -> InvariantResult:
    if state.sealed_body_files_opened_by_controller:
        return _fail("Controller opened sealed body files during cross-plane reconciliation")
    return _ok()


def material_dispatch_contract_is_explicit(state: State, _trace: object) -> InvariantResult:
    if not state.material_scan_packets_observed:
        return _ok()
    missing: list[str] = []
    if not state.material_output_contract_role_scoped:
        missing.append("role-scoped output contract")
    if not state.material_dispatch_write_target_explicit:
        missing.append("explicit result write target")
    if not state.material_legacy_packets_quarantined_or_migrated:
        missing.append("legacy packet migration/quarantine")
    if missing:
        return _fail(
            "material-scan dispatch lacks "
            + ", ".join(missing)
        )
    return _ok()


def terminal_closure_has_single_authority(state: State, _trace: object) -> InvariantResult:
    if not state.terminal_closure_observed:
        return _ok()
    missing: list[str] = []
    if not state.run_lifecycle_record_written:
        missing.append("run_lifecycle.json")
    if not state.router_frontier_lifecycle_terminal_consistent:
        missing.append("router/frontier/lifecycle terminal agreement")
    if not state.terminal_control_blocker_cleared:
        missing.append("cleared active control blocker")
    if not state.heartbeat_inactive_after_terminal:
        missing.append("inactive heartbeat")
    if missing:
        return _fail("terminal closure is missing " + ", ".join(missing))
    return _ok()


def route_snapshot_uses_frontier_completion(state: State, _trace: object) -> InvariantResult:
    if not (state.completed_nodes_observed and state.route_snapshot_visible):
        return _ok()
    missing: list[str] = []
    if not state.route_snapshot_status_derived_from_frontier:
        missing.append("completed-node status from execution_frontier")
    if not state.route_snapshot_checklists_complete_for_completed_nodes:
        missing.append("completed-node checklist projection")
    if not state.selected_status_separate_from_completion:
        missing.append("selected/current state separated from completion")
    if missing:
        return _fail("route_state_snapshot is missing " + ", ".join(missing))
    return _ok()


def cockpit_uses_same_completion_projection(state: State, _trace: object) -> InvariantResult:
    if not state.cockpit_projection_visible:
        return _ok()
    missing: list[str] = []
    if not state.cockpit_status_derived_from_frontier:
        missing.append("node status from execution_frontier")
    if not state.cockpit_checklists_complete_for_completed_nodes:
        missing.append("completed-node checklist projection")
    if not state.cockpit_closed_runs_hidden_from_active_tabs:
        missing.append("closed runs hidden from active tabs")
    if missing:
        return _fail("Cockpit projection is missing " + ", ".join(missing))
    return _ok()


def reviewer_block_events_are_known(state: State, _trace: object) -> InvariantResult:
    if state.minimal_repair_strategy_selected and not state.role_event_artifacts_scanned:
        return _fail("role output event artifacts were not scanned during event taxonomy audit")
    if state.reviewer_block_events_observed and not state.reviewer_block_events_registered:
        return _fail("reviewer blocker events are outside EXTERNAL_EVENTS taxonomy")
    return _ok()


def gate_outcome_contracts_have_non_pass_paths(state: State, _trace: object) -> InvariantResult:
    if state.gate_outcome_contracts_observed and not state.gate_outcome_contracts_complete:
        return _fail("reviewer/officer gate outcome contracts have pass-only paths")
    return _ok()


def node_completion_is_idempotent_per_active_node(state: State, _trace: object) -> InvariantResult:
    if (
        state.node_completion_observed
        and not state.node_completion_idempotency_scoped_to_active_node
    ):
        return _fail("node completion idempotency is not scoped to the active node")
    return _ok()


def install_policy_matches_first_class_sources(state: State, _trace: object) -> InvariantResult:
    if not state.cockpit_source_present_in_tree:
        return _ok()
    if not state.install_audit_policy_accepts_first_class_cockpit:
        return _fail("install audit still rejects first-class flowpilot_cockpit source")
    if not state.installed_skill_matches_repository_source:
        return _fail("installed FlowPilot skill source differs from repository source")
    return _ok()


def standard_six_roles_have_liveness_gate(state: State, _trace: object) -> InvariantResult:
    if state.standard_six_roles_requested and not state.role_liveness_ready_or_blocked:
        return _fail("standard six roles have neither readiness proof nor an early blocker")
    return _ok()


def active_task_policy_hides_history(state: State, _trace: object) -> InvariantResult:
    if not state.active_task_policy_observed:
        return _ok()
    if not state.history_default_hidden:
        return _fail("completed, abandoned, or stale history is visible by default")
    if not state.current_pointer_is_ui_focus_only:
        return _fail("current pointer is not limited to UI focus/default target")
    if not state.active_task_set_has_explicit_authority:
        return _fail("active UI task set lacks explicit run-index authority")
    return _ok()


INVARIANTS = (
    Invariant(
        name="controller_keeps_envelope_only_boundary",
        description="Cross-plane reconciliation does not open sealed bodies.",
        predicate=controller_keeps_envelope_only_boundary,
    ),
    Invariant(
        name="material_dispatch_contract_is_explicit",
        description="Material-scan dispatch carries role contract, write target, and legacy policy.",
        predicate=material_dispatch_contract_is_explicit,
    ),
    Invariant(
        name="terminal_closure_has_single_authority",
        description="Terminal closure reconciles lifecycle, router, frontier, blocker, and heartbeat authorities.",
        predicate=terminal_closure_has_single_authority,
    ),
    Invariant(
        name="route_snapshot_uses_frontier_completion",
        description="route_state_snapshot derives completed node and checklist status from frontier completion.",
        predicate=route_snapshot_uses_frontier_completion,
    ),
    Invariant(
        name="cockpit_uses_same_completion_projection",
        description="Cockpit uses the same completed-node projection and hides closed runs from active tabs.",
        predicate=cockpit_uses_same_completion_projection,
    ),
    Invariant(
        name="reviewer_block_events_are_known",
        description="Reviewer blocker events are registered in router EXTERNAL_EVENTS.",
        predicate=reviewer_block_events_are_known,
    ),
    Invariant(
        name="gate_outcome_contracts_have_non_pass_paths",
        description="Reviewer/officer gate outcome contracts include a non-pass repair route.",
        predicate=gate_outcome_contracts_have_non_pass_paths,
    ),
    Invariant(
        name="node_completion_is_idempotent_per_active_node",
        description="Node completion repeatability is scoped to the active node, not a global done flag.",
        predicate=node_completion_is_idempotent_per_active_node,
    ),
    Invariant(
        name="install_policy_matches_first_class_sources",
        description="Install audit policy matches first-class Cockpit source and installed skill source.",
        predicate=install_policy_matches_first_class_sources,
    ),
    Invariant(
        name="standard_six_roles_have_liveness_gate",
        description="Standard six-role runs prove readiness or stop at an early blocker.",
        predicate=standard_six_roles_have_liveness_gate,
    ),
    Invariant(
        name="active_task_policy_hides_history",
        description="Active task catalog hides completed, abandoned, and stale history by default.",
        predicate=active_task_policy_hides_history,
    ),
)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(str(result.message))
    return failures


def _safe_base(**changes: object) -> State:
    return replace(
        State(
            status="complete",
            step=10,
            controller_boundary_preserved=True,
            material_scan_packets_observed=True,
            terminal_closure_observed=True,
            completed_nodes_observed=True,
            route_snapshot_visible=True,
            cockpit_projection_visible=True,
            reviewer_block_events_observed=True,
            role_event_artifacts_scanned=True,
            gate_outcome_contracts_observed=True,
            node_completion_observed=True,
            cockpit_source_present_in_tree=True,
            standard_six_roles_requested=True,
            active_task_policy_observed=True,
            minimal_repair_strategy_selected=True,
        ),
        **changes,
    )


def repair_solution_state() -> State:
    return _safe_base()


def hazard_states() -> dict[str, State]:
    return {
        "controller_reads_sealed_body_during_audit": _safe_base(
            sealed_body_files_opened_by_controller=True,
        ),
        "material_dispatch_output_contract_role_drift": _safe_base(
            material_output_contract_role_scoped=False,
        ),
        "material_dispatch_write_target_missing": _safe_base(
            material_dispatch_write_target_explicit=False,
        ),
        "legacy_material_packets_left_unmigrated": _safe_base(
            material_legacy_packets_quarantined_or_migrated=False,
        ),
        "terminal_closure_missing_run_lifecycle": _safe_base(
            run_lifecycle_record_written=False,
        ),
        "terminal_authority_mismatch": _safe_base(
            router_frontier_lifecycle_terminal_consistent=False,
        ),
        "terminal_control_blocker_not_cleared": _safe_base(
            terminal_control_blocker_cleared=False,
        ),
        "terminal_heartbeat_still_active": _safe_base(
            heartbeat_inactive_after_terminal=False,
        ),
        "route_state_snapshot_status_mismatch": _safe_base(
            route_snapshot_status_derived_from_frontier=False,
        ),
        "route_state_snapshot_completed_checklists_pending": _safe_base(
            route_snapshot_checklists_complete_for_completed_nodes=False,
        ),
        "selected_state_conflated_with_completed_state": _safe_base(
            selected_status_separate_from_completion=False,
        ),
        "cockpit_status_mismatch": _safe_base(
            cockpit_status_derived_from_frontier=False,
        ),
        "cockpit_completed_checklists_pending": _safe_base(
            cockpit_checklists_complete_for_completed_nodes=False,
        ),
        "cockpit_closed_run_exposed_as_active_tab": _safe_base(
            cockpit_closed_runs_hidden_from_active_tabs=False,
        ),
        "reviewer_block_event_taxonomy_gap": _safe_base(
            reviewer_block_events_registered=False,
        ),
        "role_output_event_artifact_scan_missing": _safe_base(
            role_event_artifacts_scanned=False,
        ),
        "reviewer_officer_gate_outcome_pass_only": _safe_base(
            gate_outcome_contracts_complete=False,
        ),
        "node_completion_idempotency_global_only": _safe_base(
            node_completion_idempotency_scoped_to_active_node=False,
        ),
        "install_audit_layout_policy_conflict": _safe_base(
            install_audit_policy_accepts_first_class_cockpit=False,
        ),
        "installed_skill_source_drift": _safe_base(
            installed_skill_matches_repository_source=False,
        ),
        "six_role_liveness_unproven": _safe_base(
            role_liveness_ready_or_blocked=False,
        ),
        "active_history_visible_by_default": _safe_base(
            history_default_hidden=False,
        ),
        "current_pointer_used_as_daemon_authority": _safe_base(
            current_pointer_is_ui_focus_only=False,
        ),
        "active_task_set_missing_explicit_authority": _safe_base(
            active_task_set_has_explicit_authority=False,
        ),
    }


def build_workflow() -> Workflow:
    return Workflow((CrossPlaneReconciliationStep(),), name="flowpilot_cross_plane_friction")


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status == "complete"


def is_success(state: State) -> bool:
    return state.status == "complete" and not invariant_failures(state)


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 20


def _read_json(path: Path) -> tuple[Any, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, f"missing: {path}"
    except json.JSONDecodeError as exc:
        return None, f"invalid_json: {path}: {exc}"
    except OSError as exc:
        return None, f"unreadable: {path}: {exc}"


def _rel(project_root: Path, path: Path) -> str:
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return path.as_posix()


def _finding(
    *,
    code: str,
    severity: str,
    summary: str,
    matched_invariant: str,
    evidence: dict[str, object],
    minimal_fix: str,
) -> dict[str, object]:
    return {
        "code": code,
        "severity": severity,
        "summary": summary,
        "matched_invariant": matched_invariant,
        "evidence": evidence,
        "minimal_fix": minimal_fix,
    }


def _resolve_run_root(project_root: Path, run_id: str | None = None) -> tuple[str | None, Path | None, list[dict[str, object]]]:
    findings: list[dict[str, object]] = []
    if run_id:
        run_root = project_root / ".flowpilot" / "runs" / run_id
        if run_root.exists():
            return run_id, run_root, findings
        findings.append(
            _finding(
                code="requested_run_missing",
                severity="error",
                summary="Requested FlowPilot run root does not exist.",
                matched_invariant="active_task_policy_hides_history",
                evidence={"run_id": run_id, "path": _rel(project_root, run_root)},
                minimal_fix="Use a valid run_id or restore the missing run directory.",
            )
        )
        return run_id, run_root, findings

    current_path = project_root / ".flowpilot" / "current.json"
    current, current_error = _read_json(current_path)
    if isinstance(current, dict):
        current_run_id = str(current.get("current_run_id") or current.get("active_run_id") or "")
        current_run_root = str(
            current.get("current_run_root")
            or current.get("active_run_root")
            or ""
        )
        if current_run_id and current_run_root:
            return current_run_id, project_root / current_run_root, findings
        if current_run_id:
            return current_run_id, project_root / ".flowpilot" / "runs" / current_run_id, findings
    elif current_error:
        findings.append(
            _finding(
                code="current_pointer_unreadable",
                severity="warning",
                summary="current.json could not be read; falling back to newest run directory.",
                matched_invariant="active_task_policy_hides_history",
                evidence={"path": _rel(project_root, current_path), "error": current_error},
                minimal_fix="Rewrite current.json with current_run_id and current_run_root.",
            )
        )

    runs_root = project_root / ".flowpilot" / "runs"
    run_dirs = sorted(
        [path for path in runs_root.glob("run-*") if path.is_dir()],
        key=lambda path: path.name,
    )
    if not run_dirs:
        return None, None, findings
    return run_dirs[-1].name, run_dirs[-1], findings


def _terminal(value: Any) -> bool:
    return str(value or "").lower() in TERMINAL_STATUSES


def _status(value: Any) -> str:
    return str(value or "").lower()


def _iter_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                yield item


def _node_id(node: dict[str, Any]) -> str:
    return str(node.get("node_id") or node.get("id") or "")


def _checklist_items(node: dict[str, Any]) -> list[dict[str, Any]]:
    return list(_iter_dicts(node.get("checklist")))


def _done_status(value: Any) -> bool:
    return _status(value) in DONE_ITEM_STATUSES


def _load_router_external_events(router_path: Path) -> dict[str, dict[str, Any]]:
    try:
        tree = ast.parse(router_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, SyntaxError, OSError):
        return {}
    for node in ast.walk(tree):
        target_is_external_events = False
        value: ast.AST | None = None
        if isinstance(node, ast.AnnAssign):
            target_is_external_events = (
                isinstance(node.target, ast.Name)
                and node.target.id == "EXTERNAL_EVENTS"
            )
            value = node.value
        elif isinstance(node, ast.Assign):
            target_is_external_events = any(
                isinstance(target, ast.Name) and target.id == "EXTERNAL_EVENTS"
                for target in node.targets
            )
            value = node.value
        if not target_is_external_events or not isinstance(value, ast.Dict):
            continue
        events: dict[str, dict[str, Any]] = {}
        for key, item in zip(value.keys, value.values):
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                try:
                    meta = ast.literal_eval(item)
                except (ValueError, SyntaxError):
                    meta = {}
                events[key.value] = meta if isinstance(meta, dict) else {}
        return events
    return {}


def _load_router_event_names(router_path: Path) -> set[str]:
    return set(_load_router_external_events(router_path))


def _collect_events(value: Any) -> set[str]:
    events: set[str] = set()

    def walk(item: Any) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                normalized = str(key)
                if normalized in {
                    "event",
                    "event_name",
                    "originating_event",
                    "resolved_by_event",
                    "pm_repair_rerun_target",
                } and isinstance(child, str):
                    events.add(child)
                elif normalized in {
                    "allowed_resolution_events",
                    "allowed_external_events",
                } and isinstance(child, list):
                    events.update(str(event) for event in child if isinstance(event, str))
                else:
                    walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)

    walk(value)
    return events


def _material_packets(packet_ledger: Any, run_root: Path) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    if isinstance(packet_ledger, dict):
        for packet in _iter_dicts(packet_ledger.get("packets")):
            packet_id = str(packet.get("packet_id") or "")
            packet_type = str(packet.get("packet_type") or packet.get("packet_envelope", {}).get("packet_type") or "")
            if packet_type == "material_scan" or packet_id.startswith("material-scan"):
                packets.append(packet)
    packet_root = run_root / "packets"
    for envelope_path in packet_root.glob("material-scan*/packet_envelope.json"):
        envelope, _error = _read_json(envelope_path)
        if not isinstance(envelope, dict):
            continue
        packet_id = str(envelope.get("packet_id") or envelope_path.parent.name)
        if any(str(packet.get("packet_id") or "") == packet_id for packet in packets):
            continue
        packets.append(
            {
                "packet_id": packet_id,
                "packet_type": envelope.get("packet_type"),
                "packet_envelope": envelope,
                "packet_envelope_path": _rel(run_root.parent.parent.parent, envelope_path),
            }
        )
    return packets


def _has_explicit_result_write_target(packet: dict[str, Any], envelope: dict[str, Any]) -> bool:
    metadata = envelope.get("metadata") if isinstance(envelope.get("metadata"), dict) else {}
    output_contract = envelope.get("output_contract")
    if not isinstance(output_contract, dict):
        output_contract = packet.get("output_contract") if isinstance(packet.get("output_contract"), dict) else {}
    candidates = (
        envelope.get("expected_result_body_path"),
        envelope.get("result_body_path"),
        metadata.get("expected_result_body_path") if isinstance(metadata, dict) else None,
        metadata.get("write_target_path") if isinstance(metadata, dict) else None,
        output_contract.get("expected_result_body_path") if isinstance(output_contract, dict) else None,
        output_contract.get("write_target_path") if isinstance(output_contract, dict) else None,
    )
    return any(isinstance(value, str) and value.strip() for value in candidates)


def _material_packet_findings(
    *,
    project_root: Path,
    run_root: Path,
    packet_ledger: Any,
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    packets = _material_packets(packet_ledger, run_root)
    role_drift: list[dict[str, object]] = []
    missing_write_targets: list[str] = []
    lineage_split: list[str] = []
    for packet in packets:
        envelope = packet.get("packet_envelope") if isinstance(packet.get("packet_envelope"), dict) else {}
        packet_id = str(packet.get("packet_id") or envelope.get("packet_id") or "")
        to_role = str(envelope.get("to_role") or packet.get("assigned_worker_role") or "")
        output_contract = envelope.get("output_contract")
        if not isinstance(output_contract, dict):
            output_contract = packet.get("output_contract") if isinstance(packet.get("output_contract"), dict) else {}
        recipient_role = str(output_contract.get("recipient_role") or "")
        contract_id = str(output_contract.get("contract_id") or packet.get("output_contract_id") or "")
        if not to_role or recipient_role != to_role or "worker_material_scan" not in contract_id:
            role_drift.append(
                {
                    "packet_id": packet_id,
                    "to_role": to_role,
                    "recipient_role": recipient_role,
                    "contract_id": contract_id,
                }
            )
        if not _has_explicit_result_write_target(packet, envelope):
            missing_write_targets.append(packet_id)
        metadata = envelope.get("metadata") if isinstance(envelope.get("metadata"), dict) else {}
        metadata_replacement = metadata.get("replacement_for") if isinstance(metadata, dict) else None
        top_replacement = envelope.get("replacement_for") or packet.get("replacement_for")
        if metadata_replacement and not top_replacement:
            lineage_split.append(packet_id)

    if role_drift:
        findings.append(
            _finding(
                code="material_dispatch_output_contract_mismatch",
                severity="error",
                summary="Material-scan packet contract is not explicitly scoped to the packet recipient role.",
                matched_invariant="material_dispatch_contract_is_explicit",
                evidence={"packets": role_drift[:8], "count": len(role_drift)},
                minimal_fix=(
                    "Write packet_envelope.output_contract with contract_id "
                    "flowpilot.output_contract.worker_material_scan_result.v1 "
                    "and recipient_role equal to to_role for every material-scan packet."
                ),
            )
        )
    if missing_write_targets:
        findings.append(
            _finding(
                code="material_dispatch_write_target_missing",
                severity="error",
                summary="Material-scan dispatch lacks an explicit envelope-level result write target.",
                matched_invariant="material_dispatch_contract_is_explicit",
                evidence={
                    "packet_ids": missing_write_targets[:12],
                    "count": len(missing_write_targets),
                    "body_files_opened": False,
                },
                minimal_fix=(
                    "Add an envelope-level expected_result_body_path or write_target_path "
                    "when PM creates each material-scan packet, and keep result_envelope."
                    "result_body_path as the completion receipt."
                ),
            )
        )
    if lineage_split:
        findings.append(
            _finding(
                code="legacy_material_packet_lineage_split",
                severity="warning",
                summary="Repair material packets record replacement lineage only in metadata, not in the canonical field.",
                matched_invariant="material_dispatch_contract_is_explicit",
                evidence={"packet_ids": lineage_split[:12], "count": len(lineage_split)},
                minimal_fix=(
                    "Normalize repair packet creation so top-level replacement_for/supersedes "
                    "matches metadata.replacement_for, then quarantine superseded packet ids."
                ),
            )
        )
    return findings


def _audit_terminal(
    *,
    project_root: Path,
    run_root: Path,
    router_state: Any,
    frontier: Any,
    closure: Any,
    lifecycle: Any,
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    closure_is_terminal = isinstance(closure, dict) and _terminal(closure.get("status"))
    if not closure_is_terminal:
        return findings

    router_status = router_state.get("status") if isinstance(router_state, dict) else None
    frontier_status = frontier.get("status") if isinstance(frontier, dict) else None
    lifecycle_status = lifecycle.get("status") if isinstance(lifecycle, dict) else None
    lifecycle_path = run_root / "lifecycle" / "run_lifecycle.json"
    if not isinstance(lifecycle, dict):
        findings.append(
            _finding(
                code="terminal_authority_mismatch",
                severity="error",
                summary="Terminal closure suite is closed, but canonical lifecycle/run_lifecycle.json is missing.",
                matched_invariant="terminal_closure_has_single_authority",
                evidence={
                    "closure_path": _rel(project_root, run_root / "closure" / "terminal_closure_suite.json"),
                    "missing_lifecycle_path": _rel(project_root, lifecycle_path),
                    "router_status": router_status,
                    "frontier_status": frontier_status,
                },
                minimal_fix=(
                    "Make terminal closure and reconcile_current_run always write "
                    "lifecycle/run_lifecycle.json in the same transaction as router_state, "
                    "current.json, index.json, execution_frontier, and route_state_snapshot."
                ),
            )
        )
    elif not (_terminal(router_status) and _terminal(frontier_status) and _terminal(lifecycle_status)):
        findings.append(
            _finding(
                code="terminal_authority_mismatch",
                severity="error",
                summary="Terminal status disagrees across closure, router, frontier, or lifecycle authority.",
                matched_invariant="terminal_closure_has_single_authority",
                evidence={
                    "closure_status": closure.get("status"),
                    "router_status": router_status,
                    "frontier_status": frontier_status,
                    "lifecycle_status": lifecycle_status,
                },
                minimal_fix=(
                    "Use one terminal lifecycle writer to set all visible authorities "
                    "to a terminal status and record the source event."
                ),
            )
        )
    if isinstance(router_state, dict) and router_state.get("active_control_blocker"):
        findings.append(
            _finding(
                code="terminal_control_blocker_not_cleared",
                severity="error",
                summary="A terminal run still exposes an active control blocker.",
                matched_invariant="terminal_closure_has_single_authority",
                evidence={"active_control_blocker": router_state.get("active_control_blocker")},
                minimal_fix=(
                    "Clear active_control_blocker during terminal lifecycle reconciliation "
                    "after the closure suite has been accepted."
                ),
            )
        )
    lifecycle_obj = closure.get("lifecycle") if isinstance(closure.get("lifecycle"), dict) else {}
    if lifecycle_obj.get("heartbeat_active") is True:
        findings.append(
            _finding(
                code="terminal_heartbeat_still_active",
                severity="error",
                summary="Terminal closure records heartbeat_active=true.",
                matched_invariant="terminal_closure_has_single_authority",
                evidence={"closure_lifecycle": lifecycle_obj},
                minimal_fix="Set heartbeat_active=false in terminal closure and delete/update stale heartbeats.",
            )
        )
    return findings


def _audit_route_snapshot(
    *,
    frontier: Any,
    snapshot: Any,
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    if not isinstance(frontier, dict) or not isinstance(snapshot, dict):
        return findings
    completed = {str(item) for item in frontier.get("completed_nodes") or []}
    if not completed:
        return findings
    route = snapshot.get("route") if isinstance(snapshot.get("route"), dict) else {}
    nodes = list(_iter_dicts(route.get("nodes")))
    if not nodes:
        return findings
    status_mismatches: list[dict[str, object]] = []
    checklist_mismatches: list[dict[str, object]] = []
    selected_conflations: list[dict[str, object]] = []
    for node in nodes:
        node_id = _node_id(node)
        if node_id not in completed:
            continue
        node_status = _status(node.get("status"))
        is_complete = node.get("is_complete")
        if node_status != "completed" or is_complete is not True:
            status_mismatches.append(
                {
                    "node_id": node_id,
                    "status": node.get("status"),
                    "is_complete": is_complete,
                }
            )
        pending_items = [
            str(item.get("id") or item.get("label") or "")
            for item in _checklist_items(node)
            if not _done_status(item.get("status"))
        ]
        if pending_items:
            checklist_mismatches.append(
                {
                    "node_id": node_id,
                    "pending_checklist_count": len(pending_items),
                    "sample": pending_items[:8],
                }
            )
        if node.get("is_active") is True or node_status in ACTIVE_STATUSES:
            selected_conflations.append(
                {
                    "node_id": node_id,
                    "status": node.get("status"),
                    "is_active": node.get("is_active"),
                }
            )
    if status_mismatches:
        findings.append(
            _finding(
                code="route_state_snapshot_status_mismatch",
                severity="error",
                summary="Completed frontier nodes are displayed as pending/current in route_state_snapshot.",
                matched_invariant="route_snapshot_uses_frontier_completion",
                evidence={"nodes": status_mismatches[:12], "count": len(status_mismatches)},
                minimal_fix=(
                    "Build route_state_snapshot.route.nodes by overlaying "
                    "execution_frontier.completed_nodes before raw flow.json status, "
                    "and set is_complete=true for completed nodes."
                ),
            )
        )
    if checklist_mismatches:
        findings.append(
            _finding(
                code="route_state_snapshot_completed_checklists_pending",
                severity="error",
                summary="Completed route nodes still have pending checklist items in route_state_snapshot.",
                matched_invariant="route_snapshot_uses_frontier_completion",
                evidence={"nodes": checklist_mismatches[:12], "count": len(checklist_mismatches)},
                minimal_fix=(
                    "When a major node is in execution_frontier.completed_nodes, "
                    "project all of its checklist items as completed unless the item "
                    "has an explicit terminal failed/blocked status."
                ),
            )
        )
    if selected_conflations:
        findings.append(
            _finding(
                code="selected_state_conflated_with_completed_state",
                severity="warning",
                summary="A completed node is still marked active/current in the route snapshot.",
                matched_invariant="route_snapshot_uses_frontier_completion",
                evidence={"nodes": selected_conflations[:12], "count": len(selected_conflations)},
                minimal_fix=(
                    "Treat selected/current as a separate UI overlay. If a run is terminal, "
                    "do not mark the completed active_node_id as in_progress."
                ),
            )
        )
    return findings


def _load_cockpit_adapter(project_root: Path) -> Any | None:
    adapter_path = project_root / "flowpilot_cockpit" / "source_adapter.py"
    if not adapter_path.exists():
        return None
    module_name = "_flowpilot_cockpit_source_adapter_for_audit"
    spec = importlib.util.spec_from_file_location(module_name, adapter_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    old_module = sys.modules.get(module_name)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        if old_module is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = old_module
    return getattr(module, "CurrentRunAdapter", None)


def _audit_cockpit_projection(
    *,
    project_root: Path,
    run_id: str,
    frontier: Any,
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    adapter_cls = _load_cockpit_adapter(project_root)
    if adapter_cls is None:
        return findings
    try:
        snapshot = adapter_cls(project_root, run_id).load()
    except Exception as exc:  # pragma: no cover - diagnostic audit path
        findings.append(
            _finding(
                code="cockpit_adapter_unloadable",
                severity="warning",
                summary="Cockpit source adapter exists but could not load the current run.",
                matched_invariant="cockpit_uses_same_completion_projection",
                evidence={"error": repr(exc)},
                minimal_fix="Keep Cockpit source adapter importable and able to load metadata-only run snapshots.",
            )
        )
        return findings
    completed = set()
    if isinstance(frontier, dict):
        completed = {str(item) for item in frontier.get("completed_nodes") or []}
    checklist_mismatches: list[dict[str, object]] = []
    status_mismatches: list[dict[str, object]] = []
    for node in getattr(snapshot, "nodes", []):
        node_id = str(getattr(node, "node_id", ""))
        if node_id not in completed:
            continue
        if str(getattr(node, "status", "")) != "completed":
            status_mismatches.append({"node_id": node_id, "status": getattr(node, "status", "")})
        pending = [
            str(getattr(item, "item_id", ""))
            for item in getattr(node, "checklist", [])
            if not _done_status(getattr(item, "status", ""))
        ]
        if pending:
            checklist_mismatches.append(
                {
                    "node_id": node_id,
                    "pending_checklist_count": len(pending),
                    "sample": pending[:8],
                }
            )
    if status_mismatches:
        findings.append(
            _finding(
                code="cockpit_completed_node_status_mismatch",
                severity="error",
                summary="Cockpit does not project every completed frontier node as completed.",
                matched_invariant="cockpit_uses_same_completion_projection",
                evidence={"nodes": status_mismatches[:12], "count": len(status_mismatches)},
                minimal_fix=(
                    "Apply execution_frontier.completed_nodes before display_plan or raw "
                    "flow.json status inside CurrentRunAdapter."
                ),
            )
        )
    if checklist_mismatches:
        findings.append(
            _finding(
                code="cockpit_completed_node_checklist_status_mismatch",
                severity="error",
                summary="Cockpit shows pending checklist items under completed nodes.",
                matched_invariant="cockpit_uses_same_completion_projection",
                evidence={"nodes": checklist_mismatches[:12], "count": len(checklist_mismatches)},
                minimal_fix=(
                    "When CurrentRunAdapter marks a node completed from frontier, "
                    "also mark that node's checklist items completed in the UI model."
                ),
            )
        )
    frontier_status = _status(getattr(snapshot, "frontier_status", ""))
    active_tasks = list(getattr(snapshot, "active_tasks", []))
    if frontier_status not in ACTIVE_STATUSES and active_tasks:
        findings.append(
            _finding(
                code="cockpit_closed_run_exposed_as_active_tab",
                severity="error",
                summary="Cockpit exposes a closed/non-active run as an active task tab.",
                matched_invariant="cockpit_uses_same_completion_projection",
                evidence={
                    "frontier_status": getattr(snapshot, "frontier_status", ""),
                    "active_task_count": len(active_tasks),
                    "run_id": run_id,
                },
                minimal_fix=(
                    "Compute active tasks from an active frontier status, not from "
                    "the mere presence of active_node_id in a closed run."
                ),
            )
        )
    try:
        sealed_check = adapter_cls(project_root, run_id).validate_no_sealed_body_reads()
    except Exception:
        sealed_check = {}
    if isinstance(sealed_check, dict) and sealed_check.get("metadata_only") is not True:
        findings.append(
            _finding(
                code="cockpit_sealed_body_boundary_unclear",
                severity="warning",
                summary="Cockpit sealed-body validation did not prove metadata-only access.",
                matched_invariant="controller_keeps_envelope_only_boundary",
                evidence={"validation": sealed_check},
                minimal_fix="Keep Cockpit body paths as metadata and expose a metadata_only validation result.",
            )
        )
    return findings


def _audit_event_taxonomy(
    *,
    project_root: Path,
    router_state: Any,
    run_root: Path,
) -> list[dict[str, object]]:
    router_events = _load_router_event_names(project_root / "skills" / "flowpilot" / "assets" / "flowpilot_router.py")
    if not router_events:
        return []
    observed = _collect_events(router_state)
    unknown_from_files: set[str] = set()
    for path in (run_root / "control_blocks").glob("*.json"):
        data, _error = _read_json(path)
        if isinstance(data, dict):
            observed.update(_collect_events(data))
            error_code = str(data.get("error_code") or "")
            if error_code.startswith("unknown_external_event_"):
                unknown_from_files.add(error_code.removeprefix("unknown_external_event_"))
    event_artifact_roots = (
        run_root / "mailbox" / "outbox" / "events",
        run_root / "role_output_status",
    )
    for root in event_artifact_roots:
        for path in root.glob("*.json"):
            data, _error = _read_json(path)
            if isinstance(data, dict):
                observed.update(_collect_events(data))
    candidate_events = {
        event
        for event in observed
        if event.startswith(
            (
                "reviewer_blocks",
                "current_node_reviewer_blocks",
                "process_officer_blocks",
                "product_officer_blocks",
            )
        )
    }.union(unknown_from_files)
    unknown = sorted(
        event
        for event in candidate_events
        if event
        and event not in router_events
        and not event.startswith("pm_records_control_blocker_repair_decision")
    )
    if not unknown:
        return []
    return [
        _finding(
            code="role_event_taxonomy_gap",
            severity="error",
            summary="Run artifacts contain reviewer blocker events not registered in router EXTERNAL_EVENTS.",
            matched_invariant="reviewer_block_events_are_known",
            evidence={"events": unknown[:20], "count": len(unknown)},
            minimal_fix=(
                "Register the reviewer block events as first-class EXTERNAL_EVENTS "
                "or normalize them to existing canonical blocker events before routing."
            ),
        )
    ]


ROLE_GATE_EVENT_PREFIXES = (
    "reviewer_",
    "current_node_reviewer_",
    "process_officer_",
    "product_officer_",
)
ROLE_GATE_PASS_MARKERS = (
    "passes",
    "passed",
    "approves",
    "allows",
    "sufficient",
)
ROLE_GATE_NON_PASS_MARKERS = (
    "blocks",
    "blocked",
    "insufficient",
    "requires_repair",
    "requests_repair",
    "protocol_dead_end",
    "repair_required",
)
STRUCTURED_REPORT_GATES = {
    "reviewer_startup_fact_check_card_delivered",
}


def _event_class(event_name: str) -> str:
    if any(marker in event_name for marker in ROLE_GATE_NON_PASS_MARKERS):
        return "non_pass"
    if any(marker in event_name for marker in ROLE_GATE_PASS_MARKERS):
        return "pass"
    return "other"


def _audit_gate_outcome_contracts(project_root: Path) -> list[dict[str, object]]:
    events = _load_router_external_events(project_root / "skills" / "flowpilot" / "assets" / "flowpilot_router.py")
    groups: dict[str, list[str]] = {}
    for event_name, meta in events.items():
        if bool(meta.get("legacy")):
            continue
        required_flag = str(meta.get("requires_flag") or "")
        if not required_flag:
            continue
        groups.setdefault(required_flag, []).append(event_name)

    pass_only: list[dict[str, object]] = []
    for required_flag, event_names in sorted(groups.items()):
        role_events = [
            event_name
            for event_name in event_names
            if event_name.startswith(ROLE_GATE_EVENT_PREFIXES)
        ]
        if not role_events or required_flag in STRUCTURED_REPORT_GATES:
            continue
        classes = {_event_class(event_name) for event_name in role_events}
        if "pass" in classes and "non_pass" not in classes:
            pass_only.append(
                {
                    "requires_flag": required_flag,
                    "events": sorted(role_events),
                    "expected": "pass plus non-pass repair outcome",
                }
            )

    if not pass_only:
        return []
    return [
        _finding(
            code="gate_outcome_contract_pass_only",
            severity="error",
            summary="Reviewer/officer gate event groups have pass outcomes without non-pass repair outcomes.",
            matched_invariant="gate_outcome_contracts_have_non_pass_paths",
            evidence={"groups": pass_only[:40], "count": len(pass_only)},
            minimal_fix=(
                "Add a Gate Outcome Contract for each role gate so pass, block, "
                "repair, and controlled-stop outcomes are all routable."
            ),
        )
    ]


def _audit_source_policy(project_root: Path) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    audit_path = project_root / "scripts" / "audit_local_install_sync.py"
    audit_text = audit_path.read_text(encoding="utf-8") if audit_path.exists() else ""
    cockpit_present = (project_root / "flowpilot_cockpit").exists()
    if cockpit_present and (
        "legacy_cockpit_source_absent_from_main_tree" in audit_text
        or '"flowpilot_cockpit"' in audit_text
        and "LEGACY_COCKPIT_SOURCE_PATHS" in audit_text
    ):
        findings.append(
            _finding(
                code="install_audit_layout_policy_conflict",
                severity="error",
                summary="Install sync audit still rejects flowpilot_cockpit even though Cockpit source exists in-tree.",
                matched_invariant="install_policy_matches_first_class_sources",
                evidence={
                    "cockpit_source_present": True,
                    "audit_path": _rel(project_root, audit_path),
                },
                minimal_fix=(
                    "Choose a single source-layout policy: either make flowpilot_cockpit "
                    "a first-class package checked by install audit, or move it to a "
                    "generated/ignored location. Do not keep an audit that expects it absent."
                ),
            )
        )
    repo_router = project_root / "skills" / "flowpilot" / "assets" / "flowpilot_router.py"
    installed_router = Path.home() / ".codex" / "skills" / "flowpilot" / "assets" / "flowpilot_router.py"
    if repo_router.exists() and installed_router.exists():
        try:
            if repo_router.read_bytes() != installed_router.read_bytes():
                findings.append(
                    _finding(
                        code="installed_skill_source_drift",
                        severity="error",
                        summary="Installed FlowPilot router differs from repository router.",
                        matched_invariant="install_policy_matches_first_class_sources",
                        evidence={
                            "repo_router": _rel(project_root, repo_router),
                            "installed_router": installed_router.as_posix(),
                        },
                        minimal_fix=(
                            "Run the official install/sync script after source changes and "
                            "make audit_local_install_sync verify the installed router hash."
                        ),
                    )
                )
        except OSError:
            pass
    return findings


def _audit_router_source(project_root: Path) -> list[dict[str, object]]:
    router_path = project_root / "skills" / "flowpilot" / "assets" / "flowpilot_router.py"
    if not router_path.exists():
        return []
    text = router_path.read_text(encoding="utf-8")
    findings: list[dict[str, object]] = []
    if "_active_node_completion_write_missing" not in text:
        findings.append(
            _finding(
                code="node_completion_idempotency_global_only",
                severity="error",
                summary="Router source lacks active-node-scoped completion idempotency helper.",
                matched_invariant="node_completion_is_idempotent_per_active_node",
                evidence={"path": _rel(project_root, router_path)},
                minimal_fix=(
                    "Gate repeated node completion by the active node completion ledger "
                    "instead of only the global node_completed_by_pm flag."
                ),
            )
        )
    return findings


def _audit_role_liveness(*, router_state: Any) -> list[dict[str, object]]:
    if not isinstance(router_state, dict):
        return []
    flags = router_state.get("flags") if isinstance(router_state.get("flags"), dict) else {}
    requested = bool(flags.get("resume_roles_restored") or flags.get("resume_roles_requested"))
    if not requested:
        return []
    ready = bool(flags.get("resume_role_agents_rehydrated") or flags.get("resume_roles_restored"))
    blocked = bool(router_state.get("active_control_blocker"))
    if ready or blocked:
        return []
    return [
        _finding(
            code="six_role_liveness_unproven",
            severity="error",
            summary="Standard six-role support was requested without readiness proof or an early blocker.",
            matched_invariant="standard_six_roles_have_liveness_gate",
            evidence={"requested": requested, "ready": ready, "blocked": blocked},
            minimal_fix=(
                "At startup/resume, write a role readiness record for the six standard roles "
                "or stop route work behind a router-visible blocker."
            ),
        )
    ]


def audit_live_run(project_root: str | Path = ".", run_id: str | None = None) -> dict[str, object]:
    """Project a live .flowpilot run into the cross-plane invariants.

    This audit is read-only and metadata-only for sealed packets. It does not
    open packet_body.md, result_body.md, report_body.md, or decision_body.md.
    """

    root = Path(project_root).resolve()
    resolved_run_id, run_root, findings = _resolve_run_root(root, run_id)
    if run_root is None or resolved_run_id is None:
        return {
            "ok": True,
            "skipped": True,
            "skip_reason": "skipped_with_reason: no FlowPilot run root found",
            "findings": findings,
            "projected_invariant_failures": [],
            "body_files_opened": False,
        }

    router_state, _router_error = _read_json(run_root / "router_state.json")
    frontier, _frontier_error = _read_json(run_root / "execution_frontier.json")
    snapshot, _snapshot_error = _read_json(run_root / "route_state_snapshot.json")
    packet_ledger, _packet_error = _read_json(run_root / "packet_ledger.json")
    closure, _closure_error = _read_json(run_root / "closure" / "terminal_closure_suite.json")
    lifecycle, _lifecycle_error = _read_json(run_root / "lifecycle" / "run_lifecycle.json")

    findings.extend(
        _material_packet_findings(
            project_root=root,
            run_root=run_root,
            packet_ledger=packet_ledger,
        )
    )
    findings.extend(
        _audit_terminal(
            project_root=root,
            run_root=run_root,
            router_state=router_state,
            frontier=frontier,
            closure=closure,
            lifecycle=lifecycle,
        )
    )
    findings.extend(_audit_route_snapshot(frontier=frontier, snapshot=snapshot))
    findings.extend(
        _audit_cockpit_projection(
            project_root=root,
            run_id=resolved_run_id,
            frontier=frontier,
        )
    )
    findings.extend(
        _audit_event_taxonomy(
            project_root=root,
            router_state=router_state,
            run_root=run_root,
        )
    )
    findings.extend(_audit_gate_outcome_contracts(root))
    findings.extend(_audit_source_policy(root))
    findings.extend(_audit_router_source(root))
    findings.extend(_audit_role_liveness(router_state=router_state))

    projected_state = state_from_findings(findings)
    return {
        "ok": not findings,
        "skipped": False,
        "run_id": resolved_run_id,
        "run_root": _rel(root, run_root),
        "findings": findings,
        "finding_count": len(findings),
        "projected_invariant_failures": invariant_failures(projected_state),
        "body_files_opened": False,
        "sealed_body_names_blocked": sorted(BODY_PATH_NAMES),
    }


def state_from_findings(findings: list[dict[str, object]]) -> State:
    state = _safe_base()
    codes = {str(finding.get("code") or "") for finding in findings}
    if "material_dispatch_output_contract_mismatch" in codes:
        state = replace(state, material_output_contract_role_scoped=False)
    if "material_dispatch_write_target_missing" in codes:
        state = replace(state, material_dispatch_write_target_explicit=False)
    if "legacy_material_packet_lineage_split" in codes:
        state = replace(state, material_legacy_packets_quarantined_or_migrated=False)
    if "terminal_authority_mismatch" in codes:
        state = replace(
            state,
            run_lifecycle_record_written=False,
            router_frontier_lifecycle_terminal_consistent=False,
        )
    if "terminal_control_blocker_not_cleared" in codes:
        state = replace(state, terminal_control_blocker_cleared=False)
    if "terminal_heartbeat_still_active" in codes:
        state = replace(state, heartbeat_inactive_after_terminal=False)
    if "route_state_snapshot_status_mismatch" in codes:
        state = replace(state, route_snapshot_status_derived_from_frontier=False)
    if "route_state_snapshot_completed_checklists_pending" in codes:
        state = replace(state, route_snapshot_checklists_complete_for_completed_nodes=False)
    if "selected_state_conflated_with_completed_state" in codes:
        state = replace(state, selected_status_separate_from_completion=False)
    if "cockpit_completed_node_status_mismatch" in codes:
        state = replace(state, cockpit_status_derived_from_frontier=False)
    if "cockpit_completed_node_checklist_status_mismatch" in codes:
        state = replace(state, cockpit_checklists_complete_for_completed_nodes=False)
    if "cockpit_closed_run_exposed_as_active_tab" in codes:
        state = replace(state, cockpit_closed_runs_hidden_from_active_tabs=False)
    if "role_event_taxonomy_gap" in codes:
        state = replace(state, reviewer_block_events_registered=False)
    if "role_output_event_artifact_scan_missing" in codes:
        state = replace(state, role_event_artifacts_scanned=False)
    if "gate_outcome_contract_pass_only" in codes:
        state = replace(state, gate_outcome_contracts_complete=False)
    if "node_completion_idempotency_global_only" in codes:
        state = replace(state, node_completion_idempotency_scoped_to_active_node=False)
    if "install_audit_layout_policy_conflict" in codes:
        state = replace(state, install_audit_policy_accepts_first_class_cockpit=False)
    if "installed_skill_source_drift" in codes:
        state = replace(state, installed_skill_matches_repository_source=False)
    if "six_role_liveness_unproven" in codes:
        state = replace(state, role_liveness_ready_or_blocked=False)
    return state


REPAIR_ACTIONS = {
    "canonical_terminal_lifecycle": {
        "title": "Canonical terminal lifecycle transaction",
        "fixes": [
            "terminal_authority_mismatch",
            "terminal_control_blocker_not_cleared",
            "terminal_heartbeat_still_active",
        ],
        "scope": (
            "Terminal closure writer and reconcile_current_run only; no changes "
            "to role report content or route semantics."
        ),
        "proof_obligation": (
            "A closed closure suite implies lifecycle/run_lifecycle.json, "
            "router_state, current.json, index.json, execution_frontier, and "
            "route_state_snapshot all agree on terminal status."
        ),
    },
    "material_packet_contract_and_lineage": {
        "title": "Material packet envelope contract and lineage normalization",
        "fixes": [
            "material_dispatch_output_contract_mismatch",
            "material_dispatch_write_target_missing",
            "legacy_material_packet_lineage_split",
        ],
        "scope": (
            "Material-scan packet creation and legacy migration/quarantine only; "
            "do not let Controller read sealed bodies."
        ),
        "proof_obligation": (
            "Every material-scan packet envelope has to_role-matched output_contract, "
            "an explicit expected result write target, and canonical replacement_for "
            "or supersedes lineage."
        ),
    },
    "frontier_based_route_projection": {
        "title": "Frontier-based route snapshot projection",
        "fixes": [
            "route_state_snapshot_status_mismatch",
            "route_state_snapshot_completed_checklists_pending",
            "selected_state_conflated_with_completed_state",
        ],
        "scope": (
            "Snapshot builder status overlay only; avoid changing flow.json as the "
            "authored route source."
        ),
        "proof_obligation": (
            "execution_frontier.completed_nodes projects completed status and "
            "completed checklists before raw flow.json status is displayed."
        ),
    },
    "cockpit_adapter_completion_projection": {
        "title": "Cockpit adapter completion and active-tab projection",
        "fixes": [
            "cockpit_completed_node_status_mismatch",
            "cockpit_completed_node_checklist_status_mismatch",
            "cockpit_closed_run_exposed_as_active_tab",
        ],
        "scope": (
            "CurrentRunAdapter projection only; no UI redesign or new product features."
        ),
        "proof_obligation": (
            "Cockpit uses the same completed-node overlay as route_state_snapshot "
            "and exposes active tabs only for active frontier statuses."
        ),
    },
    "reviewer_event_taxonomy_closure": {
        "title": "Reviewer blocker event taxonomy closure",
        "fixes": ["role_event_taxonomy_gap"],
        "scope": "EXTERNAL_EVENTS aliases/normalization and tests only.",
        "proof_obligation": (
            "Every emitted reviewer block event is accepted or normalized before "
            "router resolution."
        ),
    },
    "gate_outcome_contracts": {
        "title": "Gate outcome contracts for reviewer/officer gates",
        "fixes": ["gate_outcome_contract_pass_only"],
        "scope": "Gate outcome metadata, wait actions, and repair routing for role gates.",
        "proof_obligation": (
            "Every reviewer/officer gate has a routable pass outcome and a routable "
            "non-pass outcome that does not advance stale approvals."
        ),
    },
    "active_node_completion_idempotency": {
        "title": "Active-node-scoped completion idempotency",
        "fixes": ["node_completion_idempotency_global_only"],
        "scope": "Completion repeatability guard and focused router tests only.",
        "proof_obligation": (
            "A completed prior node cannot prevent the current active node from "
            "writing its own completion ledger."
        ),
    },
    "source_layout_policy_alignment": {
        "title": "Source layout and install audit alignment",
        "fixes": [
            "install_audit_layout_policy_conflict",
            "installed_skill_source_drift",
        ],
        "scope": "Install audit policy and install/sync verification only.",
        "proof_obligation": (
            "The audit either accepts flowpilot_cockpit as first-class source or "
            "it is moved out of source; installed skill hashes match repository source."
        ),
    },
    "six_role_readiness_gate": {
        "title": "Standard six-role readiness gate",
        "fixes": ["six_role_liveness_unproven"],
        "scope": "Startup/resume readiness record or early blocker only.",
        "proof_obligation": (
            "A six-role run cannot begin route work until all standard roles are "
            "ready or a router-visible blocker stops it."
        ),
    },
}


def minimal_repair_strategy(findings: list[dict[str, object]]) -> dict[str, object]:
    codes = {str(finding.get("code") or "") for finding in findings}
    actions: list[dict[str, object]] = []
    for action_id, action in REPAIR_ACTIONS.items():
        fixes = set(action["fixes"])
        if codes.intersection(fixes):
            actions.append({"id": action_id, **action})
    if not actions:
        actions.append(
            {
                "id": "no_current_findings",
                "title": "No repair required by current cross-plane scan",
                "fixes": [],
                "scope": "No production mutation.",
                "proof_obligation": "All cross-plane invariants already hold.",
            }
        )
    return {
        "principle": (
            "Patch only the failing projection or transaction boundary; keep "
            "Controller envelope-only and avoid product-content rewrites."
        ),
        "actions": actions,
        "overfix_guards": [
            "Do not replace FlowPilot's route model with a UI-only state model.",
            "Do not mark human-review final report notes as unfinished route nodes.",
            "Do not open sealed bodies in runtime Controller logic.",
            "Do not hide history by deleting it; hide it from active task catalogs.",
        ],
    }


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "Action",
    "State",
    "Tick",
    "Transition",
    "audit_live_run",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "minimal_repair_strategy",
    "next_safe_states",
    "next_states",
    "repair_solution_state",
    "state_from_findings",
]
