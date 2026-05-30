"""FlowGuard-backed runtime gateway adoption checks for FlowPilot writes."""

from __future__ import annotations

import ast
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "skills" / "flowpilot" / "assets"
if str(ASSET_ROOT) not in sys.path:
    sys.path.insert(0, str(ASSET_ROOT))

from flowguard import (  # noqa: E402
    ADOPTION_LEVEL_RUNTIME_GATEWAY,
    RUNTIME_WRITE_DIRECT,
    RUNTIME_WRITE_GATEWAY,
    RuntimeGatewayAdoptionPlan,
    RuntimeGatewayContract,
    RuntimeStateSurface,
    RuntimeWriteObservation,
    review_runtime_gateway_adoption,
)
from flowpilot_runtime_gateway import (  # noqa: E402
    GATEWAY_BREAK_GLASS,
    GATEWAY_CARD_RUNTIME,
    GATEWAY_PACKET_RUNTIME,
    GATEWAY_ROLE_OUTPUT,
    GATEWAY_ROUTER_JSON,
    GATEWAY_USER_FLOW,
    runtime_gateway_surface_definitions,
)


INVENTORY_EVIDENCE_ID = "flowpilot_runtime_gateway_static_writer_inventory"
PROOF_ARTIFACT_ID = "tests.test_flowpilot_runtime_gateway_adoption"

APPROVED_GATEWAY_MODULES: dict[str, str] = {
    "card_runtime_io.py": GATEWAY_CARD_RUNTIME,
    "flowpilot_controller_break_glass.py": GATEWAY_BREAK_GLASS,
    "flowpilot_router_daemon_runtime.py": GATEWAY_ROUTER_JSON,
    "flowpilot_router_event_dispatcher.py": GATEWAY_ROUTER_JSON,
    "flowpilot_router_io_json.py": GATEWAY_ROUTER_JSON,
    "flowpilot_router_io_locks.py": GATEWAY_ROUTER_JSON,
    "flowpilot_router_lifecycle_requests_blockers.py": GATEWAY_ROUTER_JSON,
    "flowpilot_router_resume.py": GATEWAY_ROUTER_JSON,
    "flowpilot_router_role_output_bridge.py": GATEWAY_ROUTER_JSON,
    "flowpilot_router_role_output_bridge_events.py": GATEWAY_ROUTER_JSON,
    "flowpilot_router_role_output_bridge_events_replay.py": GATEWAY_ROUTER_JSON,
    "flowpilot_user_flow_source.py": GATEWAY_USER_FLOW,
    "packet_runtime_active_holder_core.py": GATEWAY_PACKET_RUNTIME,
    "packet_runtime_schema.py": GATEWAY_PACKET_RUNTIME,
    "role_output_runtime_schema_io.py": GATEWAY_ROLE_OUTPUT,
}

CRITICAL_WRITER_FUNCTION_NAMES = {
    "_acquire_router_daemon_lock",
    "_append_active_holder_event",
    "_append_router_daemon_event",
    "_quarantine_direct_scoped_event_conflict",
    "_record_json_write_lock_cleanup_failure",
    "_record_json_write_lock_takeover",
    "_record_package_disposition_authority_split",
    "_record_role_output_replay_quarantine",
    "_try_write_control_blocker_for_exception",
    "_write_bytes_atomic",
    "_write_json",
    "append_heartbeat_tick",
    "write_json",
    "write_json_atomic",
    "write_role_output_envelope",
    "write_text_atomic",
}

CRITICAL_SOURCE_TOKENS = (
    ".json",
    ".jsonl",
    "event_path",
    "failure_path",
    "frontier",
    "ledger_path",
    "lock_path",
    "quarantine",
    "state_path",
    "ticks_path",
)

NONCRITICAL_SOURCE_TOKENS = (
    "stderr_path.open",
    "stdout_path.open",
    ".md_path.write_text",
    ".mmd_path.write_text",
    "summary_markdown",
)


@dataclass(frozen=True)
class StaticWriteFinding:
    code: str
    path: str
    line: int
    symbol: str
    message: str
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "path": self.path,
            "line": self.line,
            "symbol": self.symbol,
            "message": self.message,
            "source": self.source,
        }


@dataclass(frozen=True)
class StaticWriteSite:
    path: Path
    line: int
    symbol: str
    source: str
    critical: bool
    gateway_id: str | None
    approved: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path.relative_to(ROOT)),
            "line": self.line,
            "symbol": self.symbol,
            "source": self.source,
            "critical": self.critical,
            "gateway_id": self.gateway_id,
            "approved": self.approved,
        }


def _call_name(func: ast.AST) -> str:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        parent = _call_name(func.value)
        return f"{parent}.{func.attr}" if parent else func.attr
    return ""


def _constant_string(node: ast.AST | None) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return ""


def _open_writes(call: ast.Call) -> bool:
    name = _call_name(call.func)
    if not name.endswith(".open") and name != "open":
        return False
    mode = ""
    if name.endswith(".open") and call.args:
        mode = _constant_string(call.args[0])
    elif len(call.args) >= 2:
        mode = _constant_string(call.args[1])
    for keyword in call.keywords:
        if keyword.arg == "mode":
            mode = _constant_string(keyword.value)
    if not mode:
        mode = "r"
    return any(flag in mode for flag in ("w", "a", "x", "+"))


def _is_direct_write_call(call: ast.Call) -> bool:
    name = _call_name(call.func)
    if name.endswith((".write_text", ".write_bytes")):
        return True
    if name == "os.open":
        return True
    return _open_writes(call)


class _WriteVisitor(ast.NodeVisitor):
    def __init__(self, path: Path, source_text: str) -> None:
        self.path = path
        self.source_text = source_text
        self.stack: list[str] = []
        self.sites: list[StaticWriteSite] = []
        self.gateway_id = APPROVED_GATEWAY_MODULES.get(path.name)
        self.has_gateway_assertion = "assert_runtime_gateway_write" in source_text

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        if _is_direct_write_call(node):
            source = (ast.get_source_segment(self.source_text, node) or "").strip()
            symbol = ".".join(self.stack) if self.stack else "<module>"
            critical = _critical_write_site(symbol, source)
            approved = bool(self.gateway_id and self.has_gateway_assertion)
            self.sites.append(
                StaticWriteSite(
                    path=self.path,
                    line=int(getattr(node, "lineno", 0) or 0),
                    symbol=symbol,
                    source=source,
                    critical=critical,
                    gateway_id=self.gateway_id,
                    approved=approved,
                )
            )
        self.generic_visit(node)


def _critical_write_site(symbol: str, source: str) -> bool:
    normalized = source.replace("\\", "/").lower()
    if any(token in normalized for token in NONCRITICAL_SOURCE_TOKENS):
        return False
    if symbol.split(".")[-1] in CRITICAL_WRITER_FUNCTION_NAMES:
        return True
    return any(token in normalized for token in CRITICAL_SOURCE_TOKENS)


def scan_static_write_sites(asset_root: Path = ASSET_ROOT) -> tuple[list[StaticWriteSite], list[StaticWriteFinding]]:
    sites: list[StaticWriteSite] = []
    findings: list[StaticWriteFinding] = []
    for path in sorted(asset_root.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
        visitor = _WriteVisitor(path, text)
        visitor.visit(tree)
        sites.extend(visitor.sites)
    for site in sites:
        if not site.critical:
            continue
        if site.approved:
            continue
        findings.append(
            StaticWriteFinding(
                code="critical_direct_write_without_runtime_gateway",
                path=str(site.path.relative_to(ROOT)),
                line=site.line,
                symbol=site.symbol,
                message="Critical FlowPilot state write is not inside an approved runtime gateway module with an assertion guard.",
                source=site.source,
            )
        )
    return sites, findings


def _managed_surfaces_for_gateway(gateway_id: str, surfaces: dict[str, dict[str, Any]]) -> tuple[str, ...]:
    return tuple(
        surface_id
        for surface_id, definition in surfaces.items()
        if gateway_id in tuple(definition["owner_gateway_ids"])
    )


def _surface_records(surfaces: dict[str, dict[str, Any]]) -> tuple[RuntimeStateSurface, ...]:
    return tuple(
        RuntimeStateSurface(
            surface_id=surface_id,
            description=str(definition["description"]),
            paths=tuple(definition["paths"]),
            critical=True,
            owner_gateway_ids=tuple(definition["owner_gateway_ids"]),
            metadata={"inventory_evidence_id": INVENTORY_EVIDENCE_ID},
        )
        for surface_id, definition in surfaces.items()
    )


def _gateway_records(surfaces: dict[str, dict[str, Any]]) -> tuple[RuntimeGatewayContract, ...]:
    labels = {
        GATEWAY_ROUTER_JSON: "Router-owned JSON gateway for run, route, controller, scheduler, daemon, lifecycle, and repair state.",
        GATEWAY_PACKET_RUNTIME: "Packet runtime gateway for packet envelopes, bodies, ledgers, sessions, leases, and holder events.",
        GATEWAY_ROLE_OUTPUT: "Role-output runtime gateway for local output receipts, ledgers, statuses, and sessions.",
        GATEWAY_CARD_RUNTIME: "Card runtime gateway for card ledgers, ACKs, receipts, and return events.",
        GATEWAY_BREAK_GLASS: "Break-glass gateway for incidents, patches, recovery transactions, and blocker ledgers.",
        GATEWAY_USER_FLOW: "User-flow display evidence gateway for route-sign display artifacts.",
    }
    return tuple(
        RuntimeGatewayContract(
            gateway_id=gateway_id,
            managed_surface_ids=_managed_surfaces_for_gateway(gateway_id, surfaces),
            description=description,
            requires_atomic_commit=True,
            requires_replay_observation=True,
            requires_step_contract_binding=True,
            requires_code_boundary_binding=True,
            requires_proof_artifact=True,
            step_contract_ids=("harden-flowpilot-control-plane-recovery.runtime_gateway_adoption",),
            code_boundary_ids=(f"skills.flowpilot.assets.{module[:-3]}" for module, owner in APPROVED_GATEWAY_MODULES.items() if owner == gateway_id),
            metadata={"approved_module_count": sum(1 for owner in APPROVED_GATEWAY_MODULES.values() if owner == gateway_id)},
        )
        for gateway_id, description in labels.items()
    )


def _gateway_observations(surfaces: dict[str, dict[str, Any]]) -> list[RuntimeWriteObservation]:
    observations: list[RuntimeWriteObservation] = []
    for gateway_id in (
        GATEWAY_ROUTER_JSON,
        GATEWAY_PACKET_RUNTIME,
        GATEWAY_ROLE_OUTPUT,
        GATEWAY_CARD_RUNTIME,
        GATEWAY_BREAK_GLASS,
        GATEWAY_USER_FLOW,
    ):
        module_boundaries = tuple(
            f"skills.flowpilot.assets.{module[:-3]}"
            for module, owner in APPROVED_GATEWAY_MODULES.items()
            if owner == gateway_id
        )
        for surface_id in _managed_surfaces_for_gateway(gateway_id, surfaces):
            observations.append(
                RuntimeWriteObservation(
                    observation_id=f"{gateway_id}:{surface_id}",
                    surface_id=surface_id,
                    path=";".join(surfaces[surface_id]["paths"]),
                    symbol=gateway_id,
                    write_kind=RUNTIME_WRITE_GATEWAY,
                    gateway_id=gateway_id,
                    action_id="flowpilot-runtime-gateway-adoption",
                    step_contract_ids=("harden-flowpilot-control-plane-recovery.runtime_gateway_adoption",),
                    code_boundary_ids=module_boundaries,
                    proof_artifact_ids=(PROOF_ARTIFACT_ID, INVENTORY_EVIDENCE_ID),
                    current=True,
                    result_status="passed",
                    metadata={"inventory": "static_writer_scan"},
                )
            )
    return observations


def _direct_violation_observations(findings: Iterable[StaticWriteFinding]) -> list[RuntimeWriteObservation]:
    observations: list[RuntimeWriteObservation] = []
    for index, finding in enumerate(findings, start=1):
        observations.append(
            RuntimeWriteObservation(
                observation_id=f"direct-write-violation-{index}",
                surface_id="flowpilot_generic_run_json_state",
                path=finding.path,
                symbol=finding.symbol,
                write_kind=RUNTIME_WRITE_DIRECT,
                result_status="failed",
                current=True,
                unsupported_historical_bypass_reason=finding.message,
                metadata=finding.to_dict(),
            )
        )
    return observations


def build_runtime_gateway_adoption_plan(
    findings: Sequence[StaticWriteFinding] | None = None,
) -> RuntimeGatewayAdoptionPlan:
    surfaces = runtime_gateway_surface_definitions()
    findings = list(findings or [])
    observations = _gateway_observations(surfaces) + _direct_violation_observations(findings)
    return RuntimeGatewayAdoptionPlan(
        "flowpilot",
        target_level=ADOPTION_LEVEL_RUNTIME_GATEWAY,
        state_surfaces=_surface_records(surfaces),
        gateways=_gateway_records(surfaces),
        write_observations=tuple(observations),
        complete_inventory_evidence_ids=(INVENTORY_EVIDENCE_ID,),
        require_complete_inventory=True,
        require_observed_writer_for_critical_surfaces=True,
        metadata={
            "source_root": str(ASSET_ROOT.relative_to(ROOT)),
            "approved_gateway_modules": APPROVED_GATEWAY_MODULES,
        },
    )


def build_report() -> dict[str, Any]:
    sites, static_findings = scan_static_write_sites()
    flowguard_report = review_runtime_gateway_adoption(
        build_runtime_gateway_adoption_plan(static_findings)
    )
    critical_sites = [site for site in sites if site.critical]
    gatewayed_sites = [site for site in critical_sites if site.approved]
    return {
        "ok": flowguard_report.ok and not static_findings,
        "result_type": "flowpilot_runtime_gateway_adoption",
        "coverage_boundary": (
            "All direct production write sites in skills/flowpilot/assets are statically inventoried. "
            "Critical state writes must be inside approved runtime gateway modules that call "
            "assert_runtime_gateway_write, then FlowGuard runtime-gateway adoption checks require "
            "current gateway observations for every declared critical state surface."
        ),
        "static_inventory_evidence_id": INVENTORY_EVIDENCE_ID,
        "static_write_site_count": len(sites),
        "critical_write_site_count": len(critical_sites),
        "gatewayed_critical_write_site_count": len(gatewayed_sites),
        "static_findings": [finding.to_dict() for finding in static_findings],
        "flowguard_report": flowguard_report.to_dict(),
        "approved_gateway_modules": APPROVED_GATEWAY_MODULES,
        "critical_write_sites": [site.to_dict() for site in critical_sites],
    }


def known_bad_cases() -> list[dict[str, Any]]:
    direct_observation = StaticWriteFinding(
        code="critical_direct_write_without_runtime_gateway",
        path="skills/flowpilot/assets/example_direct_writer.py",
        line=10,
        symbol="write_json",
        message="Synthetic direct write bypasses runtime gateway.",
        source="path.write_text(json.dumps(payload), encoding='utf-8')",
    )
    report = review_runtime_gateway_adoption(
        build_runtime_gateway_adoption_plan([direct_observation])
    )
    return [
        {
            "name": "direct_writer_bypasses_runtime_gateway",
            "report": report.to_dict(),
            "expected_codes": [
                "writer_observation_not_passing",
                "declared_unsupported_historical_gateway_bypass",
                "direct_state_write_bypasses_gateway",
            ],
        }
    ]


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    report = build_report()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
