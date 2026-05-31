"""Runtime write gateway checks for FlowPilot control-plane state."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


FLOWPILOT_RUNTIME_GATEWAY_SCHEMA = "flowpilot.runtime_gateway.v1"

GATEWAY_ROUTER_JSON = "flowpilot.router_json_gateway"
GATEWAY_PACKET_RUNTIME = "flowpilot.packet_runtime_gateway"
GATEWAY_ROLE_OUTPUT = "flowpilot.role_output_gateway"
GATEWAY_CARD_RUNTIME = "flowpilot.card_runtime_gateway"
GATEWAY_BREAK_GLASS = "flowpilot.break_glass_gateway"
GATEWAY_USER_FLOW = "flowpilot.user_flow_gateway"

KNOWN_GATEWAY_IDS = {
    GATEWAY_ROUTER_JSON,
    GATEWAY_PACKET_RUNTIME,
    GATEWAY_ROLE_OUTPUT,
    GATEWAY_CARD_RUNTIME,
    GATEWAY_BREAK_GLASS,
    GATEWAY_USER_FLOW,
}


class RuntimeGatewayError(RuntimeError):
    """Raised when a critical FlowPilot state write bypasses its runtime gateway."""


@dataclass(frozen=True)
class RuntimeGatewayTarget:
    surface_id: str
    critical: bool
    allowed_gateway_ids: tuple[str, ...]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": FLOWPILOT_RUNTIME_GATEWAY_SCHEMA,
            "surface_id": self.surface_id,
            "critical": self.critical,
            "allowed_gateway_ids": list(self.allowed_gateway_ids),
            "reason": self.reason,
        }


CRITICAL_RUNTIME_SURFACES: dict[str, dict[str, Any]] = {
    "flowpilot_current_pointer": {
        "description": "Active-run current/index pointers under .flowpilot.",
        "paths": (".flowpilot/current.json", ".flowpilot/index.json"),
        "owner_gateway_ids": (GATEWAY_ROUTER_JSON,),
    },
    "flowpilot_run_state": {
        "description": "Per-run Router state and bootstrap state.",
        "paths": ("router_state.json", "startup/bootstrap_state.json"),
        "owner_gateway_ids": (GATEWAY_ROUTER_JSON,),
    },
    "flowpilot_execution_frontier": {
        "description": "Current route/node execution frontier.",
        "paths": ("execution_frontier.json",),
        "owner_gateway_ids": (GATEWAY_ROUTER_JSON,),
    },
    "flowpilot_route_and_capability_state": {
        "description": "Route, route mutation, and capability planning artifacts.",
        "paths": ("routes/**/flow.json", "capabilities.json", "route_mutations.json"),
        "owner_gateway_ids": (GATEWAY_ROUTER_JSON,),
    },
    "flowpilot_controller_action_state": {
        "description": "Controller action rows, receipts, and action ledgers.",
        "paths": ("runtime/controller_actions/*.json", "runtime/controller_receipts/*.json", "runtime/controller_action_ledger.json"),
        "owner_gateway_ids": (GATEWAY_ROUTER_JSON,),
    },
    "flowpilot_router_scheduler_state": {
        "description": "Router scheduler rows, ledgers, and ownership ledgers.",
        "paths": ("runtime/router_scheduler_ledger.json", "runtime/router_ownership_ledger.json"),
        "owner_gateway_ids": (GATEWAY_ROUTER_JSON,),
    },
    "flowpilot_daemon_state": {
        "description": "Router daemon lock, status, and event-log state.",
        "paths": ("runtime/router_daemon.lock", "runtime/router_daemon_status.json", "runtime/router_daemon_events.jsonl"),
        "owner_gateway_ids": (GATEWAY_ROUTER_JSON,),
    },
    "flowpilot_control_blocker_state": {
        "description": "Control blockers, repair transactions, repair decisions, and gate decisions.",
        "paths": ("control_blocks/**/*.json", "repair_transactions/**/*.json", "gate_decisions/**/*.json"),
        "owner_gateway_ids": (GATEWAY_ROUTER_JSON, GATEWAY_BREAK_GLASS),
    },
    "flowpilot_break_glass_state": {
        "description": "Controller break-glass incidents, patches, recovery transactions, and indexes.",
        "paths": ("controller_break_glass/**/*.json",),
        "owner_gateway_ids": (GATEWAY_BREAK_GLASS, GATEWAY_ROUTER_JSON),
    },
    "flowpilot_role_output_state": {
        "description": "Role-output ledgers, receipts, local output bodies, and status/session state.",
        "paths": ("role_outputs/**/*.json", "runtime/role_output_*.json", "runtime/role_outputs/**/*.json"),
        "owner_gateway_ids": (GATEWAY_ROLE_OUTPUT, GATEWAY_ROUTER_JSON),
    },
    "flowpilot_packet_state": {
        "description": "Packet/result envelopes, packet ledgers, active-holder leases, and packet runtime sessions.",
        "paths": ("packets/**/*.json", "packet_ledger.json", "material/**/*packet*.json", "research/**/*packet*.json"),
        "owner_gateway_ids": (GATEWAY_PACKET_RUNTIME, GATEWAY_ROUTER_JSON),
    },
    "flowpilot_card_state": {
        "description": "Card ledgers, card return ledgers, receipts, ACKs, and card envelopes.",
        "paths": (
            "card_ledger.json",
            "return_event_ledger.json",
            "cards/**/*.json",
            "mailbox/outbox/card_acks/**/*.json",
            "runtime_receipts/card_reads/**/*.json",
        ),
        "owner_gateway_ids": (GATEWAY_CARD_RUNTIME, GATEWAY_ROUTER_JSON),
    },
    "flowpilot_lifecycle_state": {
        "description": "Lifecycle stop, terminal reconciliation, closure, and continuation state.",
        "paths": ("lifecycle/**/*.json", "closure/**/*.json", "continuation/**/*.json"),
        "owner_gateway_ids": (GATEWAY_ROUTER_JSON,),
    },
    "flowpilot_runtime_event_log": {
        "description": "Append-only runtime JSONL event logs that affect replay or liveness.",
        "paths": ("**/*events.jsonl", "**/*ticks.jsonl", "**/*failures.jsonl"),
        "owner_gateway_ids": (GATEWAY_ROUTER_JSON, GATEWAY_PACKET_RUNTIME),
    },
    "flowpilot_generic_run_json_state": {
        "description": "Any other JSON control artifact under a FlowPilot run root.",
        "paths": (".flowpilot/runs/**/*.json",),
        "owner_gateway_ids": (
            GATEWAY_ROUTER_JSON,
            GATEWAY_PACKET_RUNTIME,
            GATEWAY_ROLE_OUTPUT,
            GATEWAY_CARD_RUNTIME,
            GATEWAY_BREAK_GLASS,
            GATEWAY_USER_FLOW,
        ),
    },
}

SURFACE_OWNER_GATEWAYS = {
    surface_id: tuple(definition["owner_gateway_ids"])
    for surface_id, definition in CRITICAL_RUNTIME_SURFACES.items()
}

ROLE_OUTPUT_BODY_FILENAME_PREFIXES = (
    "controller_boundary_confirmation",
    "current_node_result_review_pass",
    "flowguard_model_miss_report",
    "gate_decision",
    "material_sufficiency_report",
    "flowguard_operator_model_report",
    "pm_control_blocker_repair_decision",
    "pm_model_miss_triage_decision",
    "pm_package_result_disposition",
    "pm_parent_segment_decision",
    "pm_resume",
    "pm_startup_activation_approval",
    "pm_startup_protocol_dead_end",
    "pm_startup_repair_request",
    "pm_terminal_closure_decision",
    "reviewer_review_report",
    "startup_fact_report",
    "terminal_backward_replay_report",
)


def _lower_parts(path: Path) -> tuple[str, ...]:
    return tuple(part.lower() for part in path.parts)


def _joined(parts: tuple[str, ...]) -> str:
    return "/".join(parts)


def _target(surface_id: str, reason: str) -> RuntimeGatewayTarget:
    return RuntimeGatewayTarget(
        surface_id=surface_id,
        critical=True,
        allowed_gateway_ids=SURFACE_OWNER_GATEWAYS[surface_id],
        reason=reason,
    )


def _is_immediate_flowpilot_file(parts: tuple[str, ...], name: str) -> bool:
    if ".flowpilot" not in parts:
        return False
    idx = parts.index(".flowpilot")
    return idx + 1 < len(parts) and parts[idx + 1] == name and idx + 2 == len(parts)


def _is_role_output_body_file(name: str) -> bool:
    if not name.endswith(".json"):
        return False
    stem = name[:-5]
    return any(stem == prefix or stem.startswith(prefix + "-") or stem.startswith(prefix + "_") for prefix in ROLE_OUTPUT_BODY_FILENAME_PREFIXES)


def classify_runtime_state_surface(path: Path | str) -> RuntimeGatewayTarget:
    resolved = Path(path)
    parts = _lower_parts(resolved)
    joined = _joined(parts)
    name = resolved.name.lower()

    if _is_immediate_flowpilot_file(parts, name) and name in {"current.json", "index.json"}:
        return _target("flowpilot_current_pointer", "active-run pointer")
    if name in {"router_state.json", "bootstrap_state.json"}:
        return _target("flowpilot_run_state", "router/bootstrap run state")
    if name == "execution_frontier.json":
        return _target("flowpilot_execution_frontier", "execution frontier")
    if name in {"flow.json", "flow.draft.json", "capabilities.json", "route_mutations.json"} or "/routes/" in joined:
        return _target("flowpilot_route_and_capability_state", "route or capability state")
    if name == "controller_action_ledger.json" or "/controller_actions/" in joined or "/controller_receipts/" in joined:
        return _target("flowpilot_controller_action_state", "controller action state")
    if name in {"router_scheduler_ledger.json", "router_ownership_ledger.json"}:
        return _target("flowpilot_router_scheduler_state", "router scheduler state")
    if name in {"router_daemon.lock", "router_daemon_status.json", "router_daemon_events.jsonl"}:
        return _target("flowpilot_daemon_state", "router daemon state")
    if "/controller_break_glass/" in joined:
        return _target("flowpilot_break_glass_state", "controller break-glass state")
    if "/runtime_receipts/card_reads/" in joined:
        return _target("flowpilot_card_state", "card read receipt")
    if "/mailbox/outbox/card_acks/" in joined:
        return _target("flowpilot_card_state", "card ACK envelope")
    if _is_role_output_body_file(name):
        return _target("flowpilot_role_output_state", "role output body file")
    if "/control_blocks/" in joined or "/repair_transactions/" in joined or "/gate_decisions/" in joined:
        return _target("flowpilot_control_blocker_state", "control blocker or repair state")
    if "/role_outputs/" in joined or "role_output" in name:
        return _target("flowpilot_role_output_state", "role output runtime state")
    if "/packets/" in joined or name in {"packet_ledger.json", "packet_envelope.json", "result_envelope.json", "active_holder_lease.json", "active_holder_events.jsonl"}:
        return _target("flowpilot_packet_state", "packet runtime state")
    if "packet" in name and ("/material/" in joined or "/research/" in joined):
        return _target("flowpilot_packet_state", "packet index state")
    if name in {"card_ledger.json", "return_event_ledger.json"} or "/cards/" in joined or "/card_returns/" in joined:
        return _target("flowpilot_card_state", "card runtime state")
    if "/lifecycle/" in joined or "/closure/" in joined or "/continuation/" in joined:
        return _target("flowpilot_lifecycle_state", "lifecycle or closure state")
    if name.endswith(".jsonl") and ("event" in name or "tick" in name or "failure" in name):
        return _target("flowpilot_runtime_event_log", "runtime append-only event log")
    if ".flowpilot" in parts and "runs" in parts and name.endswith(".json"):
        return _target("flowpilot_generic_run_json_state", "generic run-scoped JSON state")
    return RuntimeGatewayTarget(
        surface_id="noncritical_or_unknown",
        critical=False,
        allowed_gateway_ids=(),
        reason="path is not a known critical FlowPilot runtime state surface",
    )


def assert_runtime_gateway_write(
    path: Path | str,
    gateway_id: str,
    *,
    operation: str = "write",
) -> RuntimeGatewayTarget:
    gateway_id = str(gateway_id or "")
    if gateway_id not in KNOWN_GATEWAY_IDS:
        raise RuntimeGatewayError(f"unknown FlowPilot runtime gateway {gateway_id!r} for {operation}: {path}")
    target = classify_runtime_state_surface(path)
    if target.critical and gateway_id not in target.allowed_gateway_ids:
        raise RuntimeGatewayError(
            "FlowPilot critical state write must use an owning runtime gateway: "
            f"surface={target.surface_id!r} gateway={gateway_id!r} "
            f"allowed={target.allowed_gateway_ids!r} operation={operation!r} path={path}"
        )
    return target


def runtime_gateway_surface_definitions() -> dict[str, dict[str, Any]]:
    return {
        surface_id: {
            **definition,
            "owner_gateway_ids": tuple(definition["owner_gateway_ids"]),
            "critical": True,
        }
        for surface_id, definition in CRITICAL_RUNTIME_SURFACES.items()
    }


__all__ = [
    "FLOWPILOT_RUNTIME_GATEWAY_SCHEMA",
    "GATEWAY_BREAK_GLASS",
    "GATEWAY_CARD_RUNTIME",
    "GATEWAY_PACKET_RUNTIME",
    "GATEWAY_ROLE_OUTPUT",
    "GATEWAY_ROUTER_JSON",
    "GATEWAY_USER_FLOW",
    "KNOWN_GATEWAY_IDS",
    "RuntimeGatewayError",
    "RuntimeGatewayTarget",
    "assert_runtime_gateway_write",
    "classify_runtime_state_surface",
    "runtime_gateway_surface_definitions",
]
