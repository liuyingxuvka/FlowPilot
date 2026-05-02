"""Generate FlowPilot's single user-facing flow diagram.

The diagram is a display artifact for chat and Cockpit UI surfaces. It is not a
source of execution truth; route and frontier JSON remain authoritative.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flowpilot_paths import resolve_flowpilot_paths


STAGES = (
    ("intake", "Goal & materials"),
    ("product", "Product understanding"),
    ("modeling", "FlowGuard modeling"),
    ("route", "Route & current node"),
    ("execution", "Execution & child skills"),
    ("verification", "Verification"),
    ("completion", "Final review"),
    ("repair", "Repair / route change"),
)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize(text: Any) -> str:
    return str(text or "").lower().replace("_", "-")


def _stage_from_text(text: str, *, completed: bool, route_mutation_pending: bool) -> str:
    if completed:
        return "completion"
    if route_mutation_pending or "route-mutation" in text or "repair" in text:
        return "repair"
    if any(token in text for token in ("verify", "qa", "review", "checkpoint", "test")):
        return "verification"
    if any(token in text for token in ("implement", "execution", "child-skill", "concept", "asset")):
        return "execution"
    if any(token in text for token in ("flowguard", "model", "strict-gate")):
        return "modeling"
    if any(token in text for token in ("route", "frontier", "node", "architecture")):
        return "route"
    if any(token in text for token in ("product", "function", "contract", "acceptance")):
        return "product"
    return "intake"


def classify_current_stage(frontier: dict[str, Any], route: dict[str, Any]) -> str:
    active_node = frontier.get("active_node") or route.get("active_node")
    status = _normalize(frontier.get("status") or route.get("status"))
    route_mutation = frontier.get("route_mutation") or {}
    route_mutation_pending = bool(route_mutation.get("pending"))
    text = " ".join(
        _normalize(value)
        for value in (
            active_node,
            frontier.get("current_subnode"),
            frontier.get("next_gate"),
            frontier.get("current_chunk"),
            frontier.get("next_chunk"),
            route_mutation.get("reason"),
        )
    )
    completed = active_node == "complete" or status in {"complete", "completed"}
    return _stage_from_text(text, completed=completed, route_mutation_pending=route_mutation_pending)


def _escape_label(text: str) -> str:
    return text.replace('"', "&quot;")


def build_mermaid(
    *,
    frontier: dict[str, Any],
    route: dict[str, Any],
    current_stage: str,
) -> str:
    active_route = frontier.get("active_route") or route.get("route_id") or "unknown route"
    active_node = frontier.get("active_node") or route.get("active_node") or "unknown node"
    route_version = frontier.get("route_version") or route.get("route_version") or "unknown"

    lines = [
        "flowchart LR",
        f"  %% FlowPilot user flow. Source: route={active_route}, version={route_version}, node={active_node}",
    ]
    for key, label in STAGES:
        detail = ""
        if key == current_stage:
            detail = f"<br/>Now: {_escape_label(str(active_node))}"
        lines.append(f'  {key}["{_escape_label(label)}{detail}"]')

    lines.extend(
        [
            "  intake --> product",
            "  product --> modeling",
            "  modeling --> route",
            "  route --> execution",
            "  execution --> verification",
            "  verification --> completion",
            '  verification -- "needs change" --> repair',
            "  repair --> modeling",
            "",
            "  classDef active fill:#e6fbff,stroke:#00bcd4,stroke-width:3px,color:#0f172a;",
            "  classDef normal fill:#f8fafc,stroke:#cbd5e1,color:#334155;",
            "  classDef repair fill:#fff7ed,stroke:#fb923c,color:#7c2d12;",
            "  class intake,product,modeling,route,execution,verification,completion normal;",
            "  class repair repair;",
            f"  class {current_stage} active;",
        ]
    )
    return "\n".join(lines)


def build_markdown(source: str, *, generated_at: str, current_stage: str) -> str:
    return "\n".join(
        [
            "# FlowPilot User Flow Diagram",
            "",
            "This is the single user-facing progress diagram for chat and Cockpit UI.",
            "Route and frontier JSON remain the source of truth.",
            "",
            f"- generated_at: `{generated_at}`",
            f"- current_stage: `{current_stage}`",
            "",
            "```mermaid",
            source,
            "```",
            "",
        ]
    )


def generate(root: Path, *, write: bool) -> dict[str, Any]:
    paths = resolve_flowpilot_paths(root)
    frontier_path = Path(paths["frontier_path"])
    frontier = _load_json(frontier_path)
    active_route = frontier.get("active_route") or _load_json(Path(paths["state_path"])).get("active_route")
    route_path = Path(paths["routes_root"]) / str(active_route or "route-001") / "flow.json"
    route = _load_json(route_path)
    current_stage = classify_current_stage(frontier, route)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    source = build_mermaid(frontier=frontier, route=route, current_stage=current_stage)
    markdown = build_markdown(source, generated_at=generated_at, current_stage=current_stage)

    diagram_dir = Path(paths["diagrams_dir"])
    mmd_path = diagram_dir / "user-flow-diagram.mmd"
    md_path = diagram_dir / "user-flow-diagram.md"
    if write:
        diagram_dir.mkdir(parents=True, exist_ok=True)
        mmd_path.write_text(source + "\n", encoding="utf-8")
        md_path.write_text(markdown, encoding="utf-8")

    return {
        "ok": True,
        "write": write,
        "current_stage": current_stage,
        "layout": paths["layout"],
        "run_id": paths["run_id"],
        "run_root": str(paths["run_root"]),
        "active_route": active_route,
        "active_node": frontier.get("active_node") or route.get("active_node"),
        "source_route_path": str(route_path),
        "source_frontier_path": str(frontier_path),
        "mermaid_path": str(mmd_path),
        "markdown_preview_path": str(md_path),
        "mermaid": source,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Project root containing .flowpilot")
    parser.add_argument("--write", action="store_true", help="Write active-run diagrams/user-flow-diagram.*")
    parser.add_argument("--json", action="store_true", help="Print JSON metadata instead of Mermaid source")
    args = parser.parse_args()

    payload = generate(Path(args.root).resolve(), write=args.write)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(payload["mermaid"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
