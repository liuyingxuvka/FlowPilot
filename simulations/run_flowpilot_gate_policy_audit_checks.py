"""Run checks for the FlowPilot gate-policy audit model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

from flowguard import Explorer

import flowpilot_gate_policy_audit_model as model


REQUIRED_LABELS = (
    "small_task_stays_outside_formal_flowpilot",
    "complex_task_enters_formal_flowpilot",
    "startup_questions_record_wait_without_side_effects",
    "pm_writes_gate_policy_catalog",
    "pm_classifies_product_state_risk",
    "pm_classifies_visual_quality_risk",
    "pm_classifies_mixed_product_visual_risk",
    "pm_classifies_documentation_only_risk",
    "product_flowguard_runs_for_product_state_risk",
    "reviewer_walkthrough_runs_for_visual_quality_risk",
    "product_flowguard_runs_for_mixed_risk",
    "reviewer_walkthrough_runs_for_mixed_risk",
    "light_review_runs_for_documentation_only_risk",
    "pm_records_no_blocking_issue",
    "pm_routes_local_defect_to_local_repair",
    "pm_routes_invalidating_finding_to_route_mutation",
    "local_repair_completed_without_route_mutation",
    "route_mutation_invalidates_stale_evidence",
    "pm_records_low_composition_risk_and_waives_parent_replay",
    "pm_records_high_composition_risk_and_requires_parent_replay",
    "parent_backward_replay_runs_for_high_composition_risk",
    "pm_records_no_generated_resource_scope",
    "pm_excludes_temporary_diagnostic_resource_from_completion_gate",
    "pm_disposes_delivery_evidence_resource",
    "stage_advance_uses_transactional_state_refresh",
    "final_review_passes_after_policy_gates",
    "completion_records_without_advisory_blocker",
)


HAZARD_EXPECTED_FAILURES = {
    "small_task_enters_formal_flowpilot": "formal FlowPilot was started for a small or nonformal task",
    "formal_flowpilot_without_six_roles": "formal FlowPilot started without the standard six-role crew",
    "startup_text_invalidated_without_side_effect": "startup boundary treated side-effect-free explanatory text as a protocol violation",
    "startup_side_effects_before_answers": "startup wait boundary allowed startup side effects before answers",
    "completion_without_quality_decision": "completion recorded before mandatory quality-risk decision",
    "product_state_without_product_flowguard": "product-state risk completed without Product FlowGuard",
    "visual_quality_flowguard_only": "visual-quality risk used FlowGuard as the only quality proof",
    "mixed_quality_without_reviewer": "mixed product/visual risk completed without both FlowGuard and reviewer walkthrough",
    "documentation_only_forced_product_flowguard": "documentation-only risk was forced through Product FlowGuard",
    "quality_not_needed_without_reason": "quality gate was skipped without a recorded reason",
    "advisory_blocks_completion": "advisory or nonblocking record blocked completion",
    "local_defect_forces_route_mutation": "local defect forced structural route mutation",
    "route_invalidating_finding_gets_local_repair": "route-invalidating finding was treated as local repair only",
    "route_mutation_without_stale_invalidation": "route mutation did not invalidate stale evidence",
    "low_risk_parent_replay_hard_blocker": "low-composition-risk parent replay was a structural hard blocker",
    "diagnostic_resource_blocks_completion": "temporary diagnostic resource blocked completion",
    "delivery_resource_unresolved_at_completion": "delivery evidence resource was unresolved at completion",
    "no_benefit_hard_gate_required": "hard gate had no modeled safety delta",
    "stage_advance_without_transactional_refresh": "stage advanced without transactional frontier/display/ledger/blocker-index refresh",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|scale={state.task_scale}|formal={state.formal_flowpilot_started},"
        f"six={state.six_role_crew_started}|startup={state.startup_questions_asked},"
        f"side_effect={state.startup_side_effects_before_answers},"
        f"text_invalid={state.startup_boundary_invalidated_for_text}|risk={state.risk_type},"
        f"method={state.selected_quality_method},decision={state.quality_risk_decision_done},"
        f"pfg={state.product_flowguard_done},reviewer={state.reviewer_walkthrough_done},"
        f"light={state.light_review_done},reason={state.not_needed_reason_recorded}|"
        f"advisory_block={state.advisory_blocks_completion}|issue={state.issue_type},"
        f"repair={state.repair_strategy},local={state.local_repair_done},"
        f"mutation={state.route_mutation_done},stale={state.stale_evidence_invalidated}|"
        f"parent={state.parent_has_children},{state.composition_risk},{state.parent_replay_policy},"
        f"replay={state.parent_replay_done},waived={state.parent_replay_waived_with_reason},"
        f"blocked_by_parent={state.completion_blocked_by_parent_replay}|"
        f"resource={state.generated_resource_scope},disposed={state.generated_resource_disposed},"
        f"diag_excluded={state.generated_resource_excluded_as_diagnostic},"
        f"resource_block={state.generated_resource_blocks_completion}|"
        f"no_benefit={state.no_benefit_hard_gate_required},{state.hard_gate_safety_delta}|"
        f"stage={state.stage_advanced},frontier={state.frontier_updated},"
        f"display={state.display_updated},ledger={state.ledger_updated},"
        f"blocker={state.blocker_index_updated}|complete={state.completion_recorded}"
    )


def _build_graph() -> dict[str, object]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    states: list[model.State] = [initial]
    index = {initial: 0}
    edges: list[list[tuple[str, int]]] = []
    labels: set[str] = set()
    invariant_failures: list[dict[str, object]] = []

    while queue:
        state = queue.popleft()
        source = index[state]
        while len(edges) <= source:
            edges.append([])
        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append({"state": _state_id(state), "failures": failures})
        for label, new_state in model.next_states(state):
            labels.add(label)
            if new_state not in index:
                index[new_state] = len(states)
                states.append(new_state)
                queue.append(new_state)
            edges[source].append((label, index[new_state]))

    return {
        "states": states,
        "edges": edges,
        "labels": labels,
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "invariant_failures": invariant_failures,
    }


def _safe_graph_report(graph: dict[str, object]) -> dict[str, object]:
    labels = set(graph["labels"])
    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    states: list[model.State] = graph["states"]
    return {
        "ok": not graph["invariant_failures"]
        and not missing_labels
        and any(model.is_success(state) and state.task_scale == "small" for state in states)
        and any(model.is_success(state) and state.task_scale == "complex" for state in states),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "missing_labels": missing_labels,
        "invariant_failures": graph["invariant_failures"],
        "complete_state_count": sum(1 for state in states if state.status == "complete"),
    }


def _progress_report(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    can_reach_terminal = set(terminal)
    changed = True
    while changed:
        changed = False
        for idx, outgoing in enumerate(edges):
            if idx not in can_reach_terminal and any(target in can_reach_terminal for _label, target in outgoing):
                can_reach_terminal.add(idx)
                changed = True
    stuck = [
        _state_id(state)
        for idx, state in enumerate(states)
        if idx not in terminal and not edges[idx]
    ]
    cannot_reach_terminal = [
        _state_id(state)
        for idx, state in enumerate(states)
        if idx not in can_reach_terminal
    ]
    return {
        "ok": not stuck and not cannot_reach_terminal and 0 in can_reach_terminal,
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:10],
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "cannot_reach_terminal_samples": cannot_reach_terminal[:10],
    }


def _flowguard_report() -> dict[str, object]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=lambda _input, state, _trace: model.is_terminal(state),
        success_predicate=lambda state, _trace: model.is_success(state),
        required_labels=REQUIRED_LABELS,
    ).explore()
    return {
        "ok": report.ok,
        "summary": report.summary,
        "violation_count": len(report.violations),
        "dead_branch_count": len(report.dead_branches),
        "exception_branch_count": len(report.exception_branches),
        "reachability_failure_count": len(report.reachability_failures),
        "reachability_failures": [failure.message for failure in report.reachability_failures],
    }


def _hazard_report() -> dict[str, object]:
    hazards: dict[str, object] = {}
    ok = True
    for name, state in model.hazard_states().items():
        failures = model.invariant_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": failures,
            "state": state.__dict__,
        }
        ok = ok and detected
    return {"ok": ok, "hazards": hazards}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _contains_all(text: str, needles: tuple[str, ...]) -> bool:
    lower = text.lower()
    return all(needle.lower() in lower for needle in needles)


def _live_source_audit(project_root: Path | None) -> dict[str, object]:
    if project_root is None:
        return {
            "ok": True,
            "skipped": True,
            "skip_reason": "skipped_with_reason: --skip-live-source-audit was provided",
            "findings": [],
        }

    root = project_root
    handoff = _read_text(root / "HANDOFF.md")
    meta_model = _read_text(root / "simulations" / "meta_model.py")
    capability_model = _read_text(root / "simulations" / "capability_model.py")
    final_ledger_card = _read_text(
        root / "skills" / "flowpilot" / "assets" / "runtime_kit" / "cards" / "phases" / "pm_final_ledger.md"
    )
    closure_card = _read_text(
        root / "skills" / "flowpilot" / "assets" / "runtime_kit" / "cards" / "phases" / "pm_closure.md"
    )

    findings: list[dict[str, object]] = []

    if (
        "nonblocking FlowPilot skill improvement" in handoff
        and (
            "pm_completion_decision_recorded and not state.flowpilot_skill_improvement_report_written" in meta_model
            or "pm_completion_decision_recorded and not state.flowpilot_skill_improvement_report_written" in capability_model
            or "PM completion decision recorded before the nonblocking FlowPilot skill improvement report" in meta_model
            or "PM completion decision recorded before the nonblocking FlowPilot skill improvement report" in capability_model
        )
    ):
        findings.append(
            {
                "code": "advisory_record_modeled_as_completion_blocker",
                "severity": "error",
                "matched_invariant": "advisory_records_do_not_block_completion",
                "summary": "Source text says skill-improvement observations are nonblocking, while models require the report before PM completion.",
                "evidence": {
                    "policy_source": "HANDOFF.md",
                    "model_sources": ["simulations/meta_model.py", "simulations/capability_model.py"],
                },
            }
        )

    if (
        "Every effective route node with children now requires local parent backward" in handoff
        and "risk" not in _read_text(
            root / "skills" / "flowpilot" / "assets" / "runtime_kit" / "cards" / "phases" / "pm_parent_backward_targets.md"
        ).lower()
    ):
        findings.append(
            {
                "code": "parent_replay_structural_trigger_lacks_risk_carveout",
                "severity": "warning",
                "matched_invariant": "parent_replay_is_risk_based_or_justified",
                "summary": "Parent replay is described as a structural trigger; the active card does not clearly expose a low-composition-risk waiver path.",
                "evidence": {
                    "policy_source": "HANDOFF.md",
                    "card_source": "skills/flowpilot/assets/runtime_kit/cards/phases/pm_parent_backward_targets.md",
                },
            }
        )

    if (
        "Blocking review failures now force structural route mutation" in handoff
        and not _contains_all(handoff, ("local defect", "local repair"))
    ):
        findings.append(
            {
                "code": "review_block_policy_lacks_local_defect_branch",
                "severity": "warning",
                "matched_invariant": "repair_escalation_matches_issue_type",
                "summary": "Blocking review failures are described as forcing structural route mutation without an obvious local-defect repair branch in the handoff text.",
                "evidence": {"policy_source": "HANDOFF.md"},
            }
        )

    final_resource_text = (handoff + "\n" + final_ledger_card + "\n" + closure_card).lower()
    if "generated resource" in final_resource_text and "diagnostic" not in final_resource_text:
        findings.append(
            {
                "code": "generated_resource_policy_missing_diagnostic_carveout",
                "severity": "warning",
                "matched_invariant": "generated_resource_policy_is_scope_aware",
                "summary": "Generated-resource closure policy is broad and does not clearly separate temporary diagnostics from delivery evidence.",
                "evidence": {
                    "policy_sources": [
                        "HANDOFF.md",
                        "skills/flowpilot/assets/runtime_kit/cards/phases/pm_final_ledger.md",
                        "skills/flowpilot/assets/runtime_kit/cards/phases/pm_closure.md",
                    ]
                },
            }
        )

    control_plane_results = root / "simulations" / "flowpilot_control_plane_friction_results.json"
    if control_plane_results.exists():
        try:
            payload = json.loads(control_plane_results.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        live_run_audit = payload.get("live_run_audit") if isinstance(payload, dict) else None
        if isinstance(live_run_audit, dict) and not live_run_audit.get("ok", True):
            findings.append(
                {
                    "code": "existing_control_plane_live_audit_reports_state_friction",
                    "severity": "warning",
                    "matched_invariant": "state_updates_are_transactional",
                    "summary": "The existing control-plane friction result records live-run audit findings, which are state-friction signals for this audit model.",
                    "evidence": {
                        "result_path": "simulations/flowpilot_control_plane_friction_results.json",
                        "error_count": live_run_audit.get("error_count"),
                        "warning_count": live_run_audit.get("warning_count"),
                        "finding_codes": [
                            item.get("code")
                            for item in live_run_audit.get("findings", [])
                            if isinstance(item, dict)
                        ],
                    },
                }
            )

    return {
        "ok": not any(finding["severity"] == "error" for finding in findings),
        "skipped": False,
        "finding_count": len(findings),
        "error_count": sum(1 for finding in findings if finding["severity"] == "error"),
        "warning_count": sum(1 for finding in findings if finding["severity"] == "warning"),
        "findings": findings,
    }


def _scenario_metrics(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    complete_complex = [
        state
        for state in states
        if state.status == "complete" and state.task_scale == "complex"
    ]
    small_complete = [
        state
        for state in states
        if state.status == "complete" and state.task_scale == "small"
    ]
    high_risk_steps = [
        state.handoff_steps
        for state in complete_complex
        if state.risk_type == model.RISK_MIXED_PRODUCT_VISUAL and state.composition_risk == "high"
    ]
    low_risk_steps = [
        state.handoff_steps
        for state in complete_complex
        if state.risk_type == model.RISK_DOCUMENTATION_ONLY and state.composition_risk == "low"
    ]
    return {
        "small_task_formal_flowpilot_avoided": bool(small_complete),
        "complex_formal_paths_completed": len(complete_complex),
        "min_high_risk_complex_handoffs": min(high_risk_steps) if high_risk_steps else None,
        "min_low_risk_complex_handoffs": min(low_risk_steps) if low_risk_steps else None,
        "risk_adaptive_handoff_delta": (
            None
            if not high_risk_steps or not low_risk_steps
            else min(high_risk_steps) - min(low_risk_steps)
        ),
    }


def run_checks(*, json_out_requested: bool = False, live_root: Path | None = Path(".")) -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    explorer = _flowguard_report()
    hazards = _hazard_report()
    live_source_audit = _live_source_audit(live_root)
    metrics = _scenario_metrics(graph)
    skipped_checks = {
        "production_mutation": (
            "skipped_with_reason: this audit is read-only and does not modify FlowPilot runtime, "
            "router, cards, or protocol code"
        )
    }
    if not json_out_requested:
        skipped_checks["default_results_file"] = "skipped_with_reason: no --json-out path was provided"
    if live_source_audit.get("skipped"):
        skipped_checks["live_source_audit"] = live_source_audit.get("skip_reason")
    return {
        "ok": bool(safe_graph["ok"])
        and bool(progress["ok"])
        and bool(explorer["ok"])
        and bool(hazards["ok"])
        and bool(live_source_audit["ok"]),
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "scenario_metrics": metrics,
        "live_source_audit": live_source_audit,
        "skipped_checks": skipped_checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, help="Optional path for writing JSON result payload.")
    parser.add_argument(
        "--live-root",
        type=Path,
        default=Path("."),
        help="Project root used for read-only source audit.",
    )
    parser.add_argument("--skip-live-source-audit", action="store_true")
    args = parser.parse_args()

    result = run_checks(
        json_out_requested=bool(args.json_out),
        live_root=None if args.skip_live_source_audit else args.live_root,
    )
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
