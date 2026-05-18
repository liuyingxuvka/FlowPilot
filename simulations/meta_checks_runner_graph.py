"""Graph traversal helpers for the FlowPilot meta checks runner."""

from __future__ import annotations

import os
import sys
from collections import deque

import meta_model as model
from meta_checks_runner_contract import REQUIRED_LABELS, _state_id


GRAPH_STATE_LIMIT = 900_000


CHECK_STATE_LIMIT = 900_000


PROGRESS_STEPS = 10


MAX_INVARIANT_FAILURE_SAMPLES = 200


GRAPH_SHARD_DEPTH = 80


def _progress_enabled() -> bool:
    return os.environ.get("FLOWGUARD_PROGRESS") != "0"


class _GraphBuildProgress:
    def __init__(self, check_name: str, max_states: int, steps: int = PROGRESS_STEPS) -> None:
        self.check_name = check_name
        self.max_states = max(1, max_states)
        self.enabled = _progress_enabled()
        self.thresholds = self._thresholds(self.max_states, steps)
        self.index = 0
        if self.enabled:
            self._emit(
                "start",
                f"phase=reachable_graph states=0/{self.max_states} progress_steps={steps}",
            )

    @staticmethod
    def _thresholds(max_states: int, steps: int) -> tuple[tuple[int, int], ...]:
        by_threshold: dict[int, int] = {}
        for bucket in range(1, max(1, steps) + 1):
            threshold = max(1, (max_states * bucket + steps - 1) // steps)
            by_threshold[threshold] = int(bucket * 100 / steps)
        return tuple(sorted(by_threshold.items()))

    def _emit(self, event: str, detail: str) -> None:
        print(
            f"[flowpilot-flowguard] {event} check={self.check_name} {detail}",
            file=sys.stderr,
            flush=True,
        )

    def observe(self, state_count: int, edge_count: int) -> None:
        if not self.enabled:
            return
        while self.index < len(self.thresholds) and state_count >= self.thresholds[self.index][0]:
            _threshold, percent = self.thresholds[self.index]
            self._emit(
                "progress",
                f"{percent}% states={state_count}/{self.max_states} edges={edge_count}",
            )
            self.index += 1

    def complete(self, state_count: int, edge_count: int) -> None:
        if self.enabled:
            self._emit("complete", f"states={state_count} edges={edge_count}")


def _build_reachable_graph(
    max_states: int = 5000,
    *,
    initial_state: model.State | None = None,
    progress_name: str = "meta",
) -> dict:
    initial = initial_state or model.initial_state()
    queue: deque[model.State] = deque([initial])
    seen = {initial: 0}
    states = [initial]
    edges: list[list[int]] = [[]]
    labels: set[str] = set()
    edge_count = 0
    invariant_failures: list[dict] = []
    invariant_failure_count = 0
    terminal_counts = {"complete": 0, "blocked": 0}
    progress = _GraphBuildProgress(progress_name, max_states)

    while queue:
        state = queue.popleft()
        state_index = seen[state]
        if state.status in terminal_counts:
            terminal_counts[state.status] += 1
        for invariant in model.INVARIANTS:
            result = invariant.predicate(state, None)
            if not result.ok:
                invariant_failure_count += 1
                if len(invariant_failures) < MAX_INVARIANT_FAILURE_SAMPLES:
                    invariant_failures.append(
                        {
                            "invariant": invariant.name,
                            "state": _state_id(state),
                            "reason": result.message,
                        }
                    )

        for label, next_state in model.next_states(state):
            labels.add(label)
            edge_count += 1
            if next_state not in seen:
                seen[next_state] = len(states)
                states.append(next_state)
                edges.append([])
                if len(states) > max_states:
                    raise RuntimeError(f"state graph exceeded {max_states} states")
                queue.append(next_state)
                progress.observe(len(states), edge_count)
            edges[state_index].append(seen[next_state])

    progress.complete(len(states), edge_count)
    return {
        "states": states,
        "edges": edges,
        "labels": labels,
        "edge_count": edge_count,
        "invariant_failures": invariant_failures,
        "invariant_failure_count": invariant_failure_count,
        "terminal_counts": terminal_counts,
    }


def _graph_report_from_graph(graph: dict) -> dict:
    labels = graph["labels"]
    invariant_failures = graph["invariant_failures"]
    invariant_failure_count = graph["invariant_failure_count"]

    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    return {
        "ok": invariant_failure_count == 0 and not missing_labels,
        "state_count": len(graph["states"]),
        "edge_count": graph["edge_count"],
        "labels": sorted(labels),
        "missing_labels": missing_labels,
        "invariant_failures": invariant_failures,
        "invariant_failure_count": invariant_failure_count,
        "terminal_counts": graph["terminal_counts"],
    }


def explore_state_graph(max_states: int = 5000) -> dict:
    graph = _build_reachable_graph(max_states=max_states)
    return _graph_report_from_graph(graph)


def _reverse_reachable(edges: list[list[int]], starts: set[int]) -> set[int]:
    reverse: list[list[int]] = [[] for _ in edges]
    for source, outgoing in enumerate(edges):
        for target in outgoing:
            reverse[target].append(source)
    reachable = set(starts)
    queue: deque[int] = deque(starts)
    while queue:
        target = queue.popleft()
        for source in reverse[target]:
            if source not in reachable:
                reachable.add(source)
                queue.append(source)
    return reachable


def _check_progress(graph: dict, *, require_success: bool = True) -> dict:
    states: list[model.State] = graph["states"]
    edges: list[list[int]] = graph["edges"]
    success = {index for index, state in enumerate(states) if model.is_success(state)}
    terminal = {index for index, state in enumerate(states) if model.is_terminal(state)}
    can_reach_terminal = _reverse_reachable(edges, terminal)
    no_terminal_path = [
        _state_id(states[index])
        for index, state in enumerate(states)
        if not model.is_terminal(state) and index not in can_reach_terminal
    ]
    ok = (bool(success) or not require_success) and not no_terminal_path
    return {
        "ok": ok,
        "status": "OK" if ok else "VIOLATION",
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "success_state_count": len(success),
        "nonterminal_without_terminal_path_count": len(no_terminal_path),
        "nonterminal_without_terminal_path_samples": no_terminal_path[:20],
    }


def _tarjan_scc(edges: list[list[int]]) -> list[list[int]]:
    index = 0
    stack: list[int] = []
    on_stack: set[int] = set()
    indices: dict[int, int] = {}
    lowlinks: dict[int, int] = {}
    components: list[list[int]] = []

    def strongconnect(node: int) -> None:
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for target in edges[node]:
            if target not in indices:
                strongconnect(target)
                lowlinks[node] = min(lowlinks[node], lowlinks[target])
            elif target in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[target])

        if lowlinks[node] == indices[node]:
            component: list[int] = []
            while True:
                item = stack.pop()
                on_stack.remove(item)
                component.append(item)
                if item == node:
                    break
            components.append(component)

    for node in range(len(edges)):
        if node not in indices:
            strongconnect(node)
    return components


def _check_loops(graph: dict) -> dict:
    states: list[model.State] = graph["states"]
    edges: list[list[int]] = graph["edges"]
    stuck = [
        _state_id(states[index])
        for index, outgoing in enumerate(edges)
        if not model.is_terminal(states[index]) and not outgoing
    ]
    closed_nonterminal_components: list[list[str]] = []
    for component in _tarjan_scc(edges):
        members = set(component)
        if any(model.is_terminal(states[index]) for index in members):
            continue
        has_outgoing_to_other_component = any(
            target not in members
            for index in members
            for target in edges[index]
        )
        if not has_outgoing_to_other_component:
            closed_nonterminal_components.append(
                [_state_id(states[index]) for index in component[:5]]
            )
    ok = not stuck and not closed_nonterminal_components
    return {
        "ok": ok,
        "status": "OK" if ok else "VIOLATION",
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:20],
        "nonterminating_component_count": len(closed_nonterminal_components),
        "nonterminating_component_samples": closed_nonterminal_components[:20],
        "unreachable_success": not any(model.is_success(state) for state in states),
    }


def _prefix_shards(depth: int) -> tuple[list[model.State], set[str], list[dict], int, dict[str, int], int]:
    states = [model.initial_state()]
    labels: set[str] = set()
    invariant_failures: list[dict] = []
    invariant_failure_count = 0
    terminal_counts = {"complete": 0, "blocked": 0}
    edge_count = 0

    for _depth in range(depth):
        next_frontier: list[model.State] = []
        seen_next: set[model.State] = set()
        for state in states:
            if state.status in terminal_counts:
                terminal_counts[state.status] += 1
            for invariant in model.INVARIANTS:
                result = invariant.predicate(state, None)
                if not result.ok:
                    invariant_failure_count += 1
                    if len(invariant_failures) < MAX_INVARIANT_FAILURE_SAMPLES:
                        invariant_failures.append(
                            {
                                "invariant": invariant.name,
                                "state": _state_id(state),
                                "reason": result.message,
                            }
                        )
            outgoing = model.next_states(state)
            if not outgoing:
                if state not in seen_next:
                    seen_next.add(state)
                    next_frontier.append(state)
                continue
            for label, next_state in outgoing:
                labels.add(label)
                edge_count += 1
                if next_state not in seen_next:
                    seen_next.add(next_state)
                    next_frontier.append(next_state)
        states = next_frontier
        if not states:
            break

    return states, labels, invariant_failures, invariant_failure_count, terminal_counts, edge_count


def _run_sharded_graph_checks() -> tuple[dict, dict, dict]:
    (
        shards,
        labels,
        invariant_failures,
        invariant_failure_count,
        terminal_counts,
        edge_count,
    ) = _prefix_shards(GRAPH_SHARD_DEPTH)
    total_state_count = 0
    success_state_count = 0
    nonterminal_without_terminal_path_count = 0
    nonterminal_without_terminal_path_samples: list[str] = []
    stuck_state_count = 0
    stuck_state_samples: list[str] = []
    nonterminating_component_count = 0
    nonterminating_component_samples: list[list[str]] = []

    for index, shard_state in enumerate(shards, start=1):
        graph = _build_reachable_graph(
            max_states=GRAPH_STATE_LIMIT,
            initial_state=shard_state,
            progress_name=f"meta-shard-{index}/{len(shards)}",
        )
        labels.update(graph["labels"])
        edge_count += graph["edge_count"]
        total_state_count += len(graph["states"])
        invariant_failure_count += graph["invariant_failure_count"]
        for failure in graph["invariant_failures"]:
            if len(invariant_failures) < MAX_INVARIANT_FAILURE_SAMPLES:
                invariant_failures.append(failure)
        for key, count in graph["terminal_counts"].items():
            terminal_counts[key] = terminal_counts.get(key, 0) + count

        progress = _check_progress(graph, require_success=False)
        success_state_count += progress["success_state_count"]
        nonterminal_without_terminal_path_count += progress["nonterminal_without_terminal_path_count"]
        for sample in progress["nonterminal_without_terminal_path_samples"]:
            if len(nonterminal_without_terminal_path_samples) < 20:
                nonterminal_without_terminal_path_samples.append(sample)

        loop = _check_loops(graph)
        stuck_state_count += loop["stuck_state_count"]
        for sample in loop["stuck_state_samples"]:
            if len(stuck_state_samples) < 20:
                stuck_state_samples.append(sample)
        nonterminating_component_count += loop["nonterminating_component_count"]
        for sample in loop["nonterminating_component_samples"]:
            if len(nonterminating_component_samples) < 20:
                nonterminating_component_samples.append(sample)

    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    graph_report = {
        "ok": invariant_failure_count == 0 and not missing_labels,
        "sharded": True,
        "shard_depth": GRAPH_SHARD_DEPTH,
        "shard_count": len(shards),
        "state_count": total_state_count,
        "edge_count": edge_count,
        "labels": sorted(labels),
        "missing_labels": missing_labels,
        "invariant_failures": invariant_failures,
        "invariant_failure_count": invariant_failure_count,
        "terminal_counts": terminal_counts,
    }
    progress_ok = success_state_count > 0 and nonterminal_without_terminal_path_count == 0
    progress_report = {
        "ok": progress_ok,
        "status": "OK" if progress_ok else "VIOLATION",
        "state_count": total_state_count,
        "edge_count": edge_count,
        "success_state_count": success_state_count,
        "nonterminal_without_terminal_path_count": nonterminal_without_terminal_path_count,
        "nonterminal_without_terminal_path_samples": nonterminal_without_terminal_path_samples,
    }
    loop_ok = stuck_state_count == 0 and nonterminating_component_count == 0
    loop_report = {
        "ok": loop_ok,
        "status": "OK" if loop_ok else "VIOLATION",
        "state_count": total_state_count,
        "edge_count": edge_count,
        "stuck_state_count": stuck_state_count,
        "stuck_state_samples": stuck_state_samples,
        "nonterminating_component_count": nonterminating_component_count,
        "nonterminating_component_samples": nonterminating_component_samples,
        "unreachable_success": success_state_count == 0,
    }
    return graph_report, progress_report, loop_report
