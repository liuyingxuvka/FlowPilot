"""Data models used by the native FlowPilot cockpit."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class RunSummary:
    run_id: str
    title: str
    status: str
    active_route_id: str | None
    run_root: Path
    created_at: str | None = None
    selected: bool = False
    tab_title: str | None = None
    visible: bool = True
    hidden: bool = False
    is_current: bool = False
    source_health: str = "unknown"
    source_findings: tuple[str, ...] = ()


@dataclass(frozen=True)
class NodeSummary:
    node_id: str
    title: str
    status: str
    required_gates: tuple[str, ...] = ()
    summary: str = ""
    updated_at: str | None = None


@dataclass(frozen=True)
class EventSummary:
    time_label: str
    level: str
    source: str
    event: str
    detail: str = ""


@dataclass(frozen=True)
class CockpitSnapshot:
    workspace_root: Path
    flowpilot_root: Path
    active_run_id: str | None
    active_route_id: str | None
    selected_run_id: str | None
    selected_route_id: str | None
    active_node_id: str | None
    route_status: str
    route_version: int | None
    updated_at: str | None
    runs: tuple[RunSummary, ...]
    nodes: tuple[NodeSummary, ...]
    events: tuple[EventSummary, ...]
    evidence: tuple[EventSummary, ...]
    source_health: str
    source_findings: tuple[str, ...] = ()
    watched_paths: tuple[Path, ...] = field(default_factory=tuple)

    @property
    def selected_run(self) -> RunSummary | None:
        for run in self.runs:
            if run.run_id == self.selected_run_id:
                return run
        return None

    @property
    def active_node(self) -> NodeSummary | None:
        if not self.nodes:
            return None
        for node in self.nodes:
            if node.node_id == self.active_node_id:
                return node
        for node in self.nodes:
            if node.status in {"running", "active", "in_progress"}:
                return node
        return self.nodes[0]


STATUS_SEVERITY = {
    "blocked": 4,
    "failed": 4,
    "error": 4,
    "degraded": 3,
    "warning": 3,
    "running": 2,
    "active": 2,
    "in_progress": 2,
    "complete": 1,
    "completed": 1,
    "succeeded": 1,
    "delivered": 1,
    "pass": 1,
    "pending": 0,
    "new": 0,
    "unknown": 0,
}


def normalize_status(value: object, default: str = "unknown") -> str:
    raw = str(value or default).strip().lower().replace("-", "_").replace(" ", "_")
    if raw == "in-progress":
        return "in_progress"
    return raw or default


def status_health(statuses: list[str], findings: list[str]) -> str:
    if findings:
        return "degraded"
    if any(STATUS_SEVERITY.get(status, 0) >= 4 for status in statuses):
        return "blocked"
    if any(status in {"degraded", "warning"} for status in statuses):
        return "degraded"
    return "ok"
