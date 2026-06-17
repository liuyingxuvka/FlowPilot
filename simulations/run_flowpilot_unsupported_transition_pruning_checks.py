"""Run FlowGuard checks for FlowPilot unsupported-transition pruning."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, deque
from pathlib import Path

from flowguard.explorer import Explorer

import flowpilot_unsupported_transition_pruning_model as model


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
RESULTS_PATH = ROOT / "flowpilot_unsupported_transition_pruning_results.json"

SCAN_PATHS = (
    "skills/flowpilot/assets",
    "scripts",
    "tests",
    "simulations",
    "openspec/specs",
    "openspec/changes/converge-new-only-maintenance-cleanup",
)

INCLUDED_SUFFIXES = {".py", ".md", ".json"}
EXCLUDED_DIRS = {"__pycache__", ".pytest_cache", "tmp"}
EXCLUDED_FILE_SUFFIXES = ("_results.json", "_checks_results.json")

TERM_RE = re.compile(
    r"\b(compatib\w*|unsupported_historical|unsupported|alias(?:es)?|fallback|old)\b",
    re.IGNORECASE,
)

ACCEPTANCE_RE = re.compile(
    r"accepted alias|accepted aliases|accepts? .*alias|alias(?:es)? .*accept|"
    r"old inputs? .*accepted|accepted .*old|unsupported_historical .*accepted|accepted .*unsupported_historical|"
    r"unsupported .*accepted|accepted .*unsupported|canonicali[sz]ed unsupported|"
    r"migrated unsupported|unsupported_historical aliases|unsupported_historical-only alias|"
    r"preserve .*old import path|remains? compatible|remain compatible|"
    r"unsupported_historical facade|unsupported_historical entrypoint|unsupported_historical exports?|"
    r"unsupported_historical layer|unsupported_historical entrypoint|unsupported_historical import surface|unsupported_historical full",
    re.IGNORECASE,
)

REJECTION_RE = re.compile(
    r"reject|unsupported|not valid|not accepted|must not|shall not|cannot|"
    r"forbid|absence|hazard|expected_failure|detected|quarantine|audit-only|"
    r"negative",
    re.IGNORECASE,
)

SAFETY_FALLBACK_RE = re.compile(
    r"single-agent|manual-resume|scheduled-continuation|cockpit|chat-display|"
    r"continuous_controller_standby|continuous standby|break-glass|"
    r"no_live_agent_id|controller_relay_no_live_agent|startup capability",
    re.IGNORECASE,
)

PUBLIC_FACADE_RE = re.compile(
    r"unsupported_historical facade|public entrypoint|public entrypoints|unsupported_historical entrypoint|"
    r"unsupported_historical exports?|import path|unsupported_historical import surface|"
    r"original module remains importable|facade remains|facade preserves",
    re.IGNORECASE,
)

RUNTIME_ACCEPTANCE_SYMBOL_RE = re.compile(
    r"GATE_CONTRACT_ALIASES|normalize_envelope_aliases|_alias_specs|"
    r"compat_output_alias|unsupported_historical_.*accepted|accepted_.*unsupported_historical",
    re.IGNORECASE,
)


def _iter_files() -> list[Path]:
    files: list[Path] = []
    for rel in SCAN_PATHS:
        root = PROJECT_ROOT / rel
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in EXCLUDED_DIRS for part in path.parts):
                continue
            if path.suffix.lower() not in INCLUDED_SUFFIXES:
                continue
            if path.name.endswith(EXCLUDED_FILE_SUFFIXES):
                continue
            files.append(path)
    return sorted(files)


def _surface_for(path: Path) -> str:
    rel = path.relative_to(PROJECT_ROOT).as_posix()
    if rel.startswith("skills/flowpilot/assets/runtime_kit/cards/"):
        return "runtime_card"
    if rel.startswith("skills/flowpilot/assets/runtime_kit/prompts/"):
        return "runtime_prompt"
    if rel.startswith("skills/flowpilot/assets/"):
        return "runtime_code"
    if rel.startswith("openspec/specs/"):
        return "active_spec"
    if rel.startswith("openspec/changes/"):
        return "change_context"
    if rel.startswith("tests/"):
        return "test"
    if rel.startswith("simulations/"):
        return "flowguard_model"
    if rel.startswith("scripts/"):
        return "maintenance_script"
    return "other"


def _candidate_from_line(path: Path, line_no: int, text: str) -> model.Candidate | None:
    if not TERM_RE.search(text):
        return None

    rel = path.relative_to(PROJECT_ROOT).as_posix()
    lower = text.lower()
    surface = _surface_for(path)
    teaches_acceptance = bool(ACCEPTANCE_RE.search(text))
    rejects_old_path = bool(REJECTION_RE.search(text))
    is_test_or_model_evidence = surface in {"test", "flowguard_model", "maintenance_script"} or rejects_old_path
    is_active_prompt_or_card = surface in {"runtime_prompt", "runtime_card"}
    is_active_spec = surface == "active_spec"
    is_change_context = surface == "change_context"
    is_current_recovery_branch = "fallback" in lower and bool(SAFETY_FALLBACK_RE.search(text)) and not (
        "unsupported_historical" in lower or "unsupported" in lower or "alias" in lower or "compatib" in lower or "old" in lower
    )
    is_public_facade_boundary = bool(PUBLIC_FACADE_RE.search(text))
    is_runtime_acceptance_code = surface == "runtime_code" and (
        teaches_acceptance or bool(RUNTIME_ACCEPTANCE_SYMBOL_RE.search(text))
    )

    return model.Candidate(
        candidate_id=f"{rel}:{line_no}",
        path=rel,
        line=line_no,
        text=text.strip(),
        surface=surface,
        has_unsupported_historical_term="unsupported_historical" in lower,
        has_historical_term="historical" in lower,
        has_unsupported_term="unsupported" in lower,
        has_alias_term="alias" in lower,
        has_fallback_term="fallback" in lower,
        has_old_term="old" in lower,
        teaches_acceptance=teaches_acceptance,
        rejects_old_path=rejects_old_path,
        is_runtime_acceptance_code=is_runtime_acceptance_code,
        is_active_prompt_or_card=is_active_prompt_or_card,
        is_active_spec=is_active_spec,
        is_change_context=is_change_context,
        is_test_or_model_evidence=is_test_or_model_evidence,
        is_current_recovery_branch=is_current_recovery_branch,
        is_public_facade_boundary=is_public_facade_boundary,
        is_historical_doc=False,
    )


def collect_candidates() -> tuple[model.Candidate, ...]:
    candidates: list[model.Candidate] = []
    for path in _iter_files():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
        for line_no, text in enumerate(lines, start=1):
            candidate = _candidate_from_line(path, line_no, text)
            if candidate is not None:
                candidates.append(candidate)
    return tuple(candidates)


def _state_id(state: model.State) -> str:
    return (
        f"candidate={state.candidate_id}|status={state.status}|action={state.action}|"
        f"delete={state.delete_required},rewrite={state.rewrite_required},"
        f"negative={state.kept_negative_evidence},recovery={state.kept_current_recovery_branch},"
        f"structuremesh={state.structuremesh_gate_required},manual={state.manual_review_required}"
    )


def _classify_candidates(candidates: tuple[model.Candidate, ...]) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    counts: Counter[str] = Counter()
    invariant_failures: list[dict[str, object]] = []
    labels: set[str] = set()

    for candidate in candidates:
        transitions = model.next_states(candidate, model.initial_state())
        if not transitions:
            rows.append(
                {
                    "candidate_id": candidate.candidate_id,
                    "path": candidate.path,
                    "line": candidate.line,
                    "surface": candidate.surface,
                    "action": "unclassified",
                    "text": candidate.text[:240],
                }
            )
            counts["unclassified"] += 1
            continue
        transition = transitions[0]
        labels.add(transition.label)
        state = transition.state
        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append({"state": _state_id(state), "failures": failures})
        counts[state.action] += 1
        rows.append(
            {
                "candidate_id": candidate.candidate_id,
                "path": candidate.path,
                "line": candidate.line,
                "surface": candidate.surface,
                "action": state.action,
                "delete_required": state.delete_required,
                "rewrite_required": state.rewrite_required,
                "structuremesh_gate_required": state.structuremesh_gate_required,
                "text": candidate.text[:240],
            }
        )

    return {
        "ok": not invariant_failures and "unclassified" not in counts,
        "candidate_count": len(candidates),
        "counts": dict(sorted(counts.items())),
        "labels": sorted(labels),
        "invariant_failures": invariant_failures,
        "candidates": rows,
    }


def _build_graph(candidates: tuple[model.Candidate, ...]) -> dict[str, object]:
    initial = model.initial_state()
    inputs = candidates or (
        model.Candidate(
            candidate_id="synthetic:no_candidates",
            path="synthetic",
            line=0,
            text="no unsupported_historical candidates",
            surface="synthetic",
        ),
    )
    queue: deque[model.State] = deque([initial])
    seen: list[model.State] = [initial]
    index = {initial: 0}
    labels: set[str] = set()
    edges: list[list[tuple[str, int]]] = []
    invariant_failures: list[dict[str, object]] = []

    while queue:
        state = queue.popleft()
        source_index = index[state]
        while len(edges) <= source_index:
            edges.append([])

        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append({"state": _state_id(state), "failures": failures})

        for candidate in inputs:
            for transition in model.next_states(candidate, state):
                labels.add(transition.label)
                if transition.state not in index:
                    index[transition.state] = len(seen)
                    seen.append(transition.state)
                    queue.append(transition.state)
                edges[source_index].append((transition.label, index[transition.state]))

    return {
        "states": seen,
        "edges": edges,
        "labels": labels,
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "invariant_failures": invariant_failures,
    }


def _graph_report(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    terminals = [state for state in states if model.is_terminal(state)]
    return {
        "ok": not graph["invariant_failures"] and bool(terminals),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "labels": sorted(graph["labels"]),
        "terminal_count": len(terminals),
        "invariant_failure_count": len(graph["invariant_failures"]),
        "invariant_failures": graph["invariant_failures"][:10],
    }


def _progress_report(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    can_reach_terminal = set(terminal)
    changed = True
    while changed:
        changed = False
        for source, outgoing in enumerate(edges):
            targets = [target for _label, target in outgoing]
            if source not in can_reach_terminal and any(target in can_reach_terminal for target in targets):
                can_reach_terminal.add(source)
                changed = True
    stuck = [
        _state_id(state)
        for idx, state in enumerate(states)
        if idx not in terminal and not edges[idx]
    ]
    return {
        "ok": 0 in can_reach_terminal and not stuck,
        "initial_can_reach_terminal": 0 in can_reach_terminal,
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:10],
    }


def _flowguard_report(candidates: tuple[model.Candidate, ...]) -> dict[str, object]:
    inputs = candidates or (
        model.Candidate(
            candidate_id="synthetic:no_candidates",
            path="synthetic",
            line=0,
            text="no unsupported_historical candidates",
            surface="synthetic",
        ),
    )
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=inputs,
        invariants=model.INVARIANTS,
        max_sequence_length=1,
        terminal_predicate=lambda _input, state, _trace: model.is_terminal(state),
        success_predicate=lambda state, _trace: model.is_success(state),
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
        detected = bool(failures)
        hazards[name] = {
            "detected": detected,
            "failures": failures,
            "state": state.__dict__,
        }
        ok = ok and detected
    return {"ok": ok, "hazards": hazards}


def run_checks() -> dict[str, object]:
    candidates = collect_candidates()
    classifications = _classify_candidates(candidates)
    graph = _build_graph(candidates)
    graph_report = _graph_report(graph)
    progress = _progress_report(graph)
    flowguard = _flowguard_report(candidates)
    hazards = _hazard_report()
    counts = classifications["counts"]
    immediate_cleanup_count = int(counts.get(model.DELETE_RUNTIME_ACCEPTANCE_BRANCH, 0)) + int(
        counts.get(model.REWRITE_ACTIVE_PROMPT_OR_SPEC, 0)
    )
    return {
        "ok": (
            bool(classifications["ok"])
            and bool(graph_report["ok"])
            and bool(progress["ok"])
            and bool(flowguard["ok"])
            and bool(hazards["ok"])
            and immediate_cleanup_count == 0
        ),
        "model": "flowpilot_unsupported_transition_pruning",
        "immediate_cleanup_count": immediate_cleanup_count,
        "checks": {
            "classification": classifications,
            "safe_graph": graph_report,
            "progress": progress,
            "flowguard_explorer": flowguard,
            "hazards": hazards,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", default=str(RESULTS_PATH))
    args = parser.parse_args()
    report = run_checks()
    out = Path(args.json_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
