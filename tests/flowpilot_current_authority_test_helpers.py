from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from typing import Any


REFERENCE_SCHEMA_VERSION = "black_box_flowpilot.current_authority_reference.v1"


def _project_root(ledger: dict[str, Any]) -> Path:
    raw_root = str(ledger.get("project_root") or ledger.get("run_root") or "").strip()
    if not raw_root:
        raw_root = tempfile.mkdtemp(prefix="flowpilot-current-authority-test-")
    root = Path(raw_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    ledger["project_root"] = root.as_posix()
    return root


def raw_current_authority_references(
    ledger: dict[str, Any],
    *,
    include_repair: bool = False,
    fixture_id: str = "current-node",
) -> list[dict[str, str]]:
    root = _project_root(ledger)
    authority_root = root / ".flowpilot" / "test-current-authorities" / fixture_id
    authority_root.mkdir(parents=True, exist_ok=True)
    specs = [
        ("acceptance_authority", "acceptance.md", "Current test acceptance authority.\n"),
        ("route_authority", "route.md", "Current test route authority.\n"),
    ]
    if include_repair:
        specs.append(("repair_authority", "repair.md", "Current test repair authority.\n"))
    references: list[dict[str, str]] = []
    for reference_kind, filename, content in specs:
        path = authority_root / filename
        path.write_text(content, encoding="utf-8")
        references.append(
            {
                "reference_kind": reference_kind,
                "authority_id": f"{fixture_id}-{reference_kind}",
                "owner": "pm",
                "path": path.relative_to(root).as_posix(),
                "fingerprint": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
                "consumer_scope": "current_route_node",
            }
        )
    return references


def normalized_current_authority_references(
    ledger: dict[str, Any],
    *,
    node_id: str,
    source_packet_id: str,
    source_result_id: str,
    include_repair: bool = False,
    fixture_id: str = "current-node",
) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    for raw_reference in raw_current_authority_references(
        ledger,
        include_repair=include_repair,
        fixture_id=fixture_id,
    ):
        references.append(
            {
                "schema_version": REFERENCE_SCHEMA_VERSION,
                **raw_reference,
                "run_id": str(ledger.get("project_id") or ""),
                "route_version": ledger.get("active_route_version"),
                "node_id": node_id,
                "packet_id": source_packet_id,
                "result_id": source_result_id,
                "source_generation": int(ledger.get("source_generation", 0) or 0),
            }
        )
    return references
