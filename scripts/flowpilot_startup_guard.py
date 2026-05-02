"""Validate and optionally record the FlowPilot startup hard gate.

The guard is intentionally strict: a formal route may not proceed to child
skills, image generation, implementation, or chunk execution until the
canonical route, state, frontier, crew, role memory, and continuation evidence
all describe the same active nonterminal route.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_ROLES = (
    "project_manager",
    "human_like_reviewer",
    "process_flowguard_officer",
    "product_flowguard_officer",
    "worker_a",
    "worker_b",
)

TERMINAL_STATUSES = {
    "complete",
    "completed",
    "cancelled",
    "canceled",
    "stopped",
    "archived",
    "paused",
    "blocked",
    "terminal",
}

ACTIVE_CREW_STATUSES = {
    "active",
    "idle",
    "ready",
    "running",
    "restored",
    "recovered",
    "replaced",
    "replaced_from_memory",
    "memory_recovered",
    "memory_seeded",
    "live_unavailable_memory_seeded",
}

LIVE_SUBAGENT_READY_DECISIONS = {
    "live_agents_started",
    "live_agents_resumed",
    "live_agents_active",
}

SINGLE_AGENT_CONTINUITY_DECISIONS = {
    "single_agent_role_continuity_authorized",
    "single_agent_role_continuity_approved",
}


@dataclass
class Check:
    name: str
    ok: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        record: dict[str, Any] = {
            "name": self.name,
            "ok": self.ok,
            "message": self.message,
        }
        if self.details:
            record["details"] = self.details
        return record


class StartupGuard:
    def __init__(
        self,
        *,
        root: Path,
        route_id: str | None,
        require_recorded_pass: bool,
        record_pass: bool,
    ) -> None:
        self.root = root.resolve()
        self.flowpilot_root = self.root / ".flowpilot"
        self.route_id = route_id
        self.require_recorded_pass = require_recorded_pass
        self.record_pass = record_pass
        self.checks: list[Check] = []
        self.state: dict[str, Any] | None = None
        self.frontier: dict[str, Any] | None = None
        self.route: dict[str, Any] | None = None
        self.crew: dict[str, Any] | None = None

    def pass_(self, name: str, message: str, **details: Any) -> None:
        self.checks.append(Check(name=name, ok=True, message=message, details=details))

    def fail(self, name: str, message: str, **details: Any) -> None:
        self.checks.append(Check(name=name, ok=False, message=message, details=details))

    def load_json(self, path: Path, name: str) -> dict[str, Any] | None:
        if not path.exists():
            self.fail(name, "required JSON file is missing", path=str(path))
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - diagnostic path
            self.fail(name, "required JSON file did not parse", path=str(path), error=repr(exc))
            return None
        if not isinstance(value, dict):
            self.fail(name, "required JSON root must be an object", path=str(path))
            return None
        self.pass_(name, "required JSON file exists and parses", path=str(path))
        return value

    def resolve_project_path(self, value: str | None, fallback: Path) -> Path:
        if not value:
            return fallback
        path = Path(value)
        if path.is_absolute():
            return path
        return self.root / path

    def run(self) -> dict[str, Any]:
        self.state = self.load_json(self.flowpilot_root / "state.json", "state_json_present")
        if not self.state:
            return self.result()

        active_route = self.state.get("active_route")
        if self.route_id is None:
            self.route_id = active_route if isinstance(active_route, str) else None
        if not self.route_id:
            self.fail("route_id_resolved", "active route could not be resolved from state or --route-id")
            return self.result()
        if active_route != self.route_id:
            self.fail(
                "state_route_matches_requested_route",
                "state active_route does not match requested route",
                active_route=active_route,
                requested_route=self.route_id,
            )
        else:
            self.pass_("state_route_matches_requested_route", "state active_route matches requested route")

        self.check_state()
        self.check_frontier()
        self.check_route()
        self.check_crew()
        self.check_startup_activation()
        self.check_continuation()

        result = self.result()
        if self.record_pass and result["ok"]:
            evidence_path = self.write_pass_evidence(result)
            result["startup_guard_evidence_path"] = evidence_path
        return result

    def check_state(self) -> None:
        assert self.state is not None
        status = str(self.state.get("status", "")).lower()
        active_node = str(self.state.get("active_node", "")).lower()
        if status in TERMINAL_STATUSES:
            self.fail("state_nonterminal", "state status is terminal and cannot start a new formal route", status=status)
        else:
            self.pass_("state_nonterminal", "state status is nonterminal", status=status)

        if active_node in {"", "none", "null", "complete", "completed"}:
            self.fail("state_active_node_current", "state active_node is not an executable startup/current node", active_node=active_node)
        else:
            self.pass_("state_active_node_current", "state active_node names a current node", active_node=active_node)

        frontier_path = self.resolve_project_path(
            self.state.get("execution_frontier"),
            self.flowpilot_root / "execution_frontier.json",
        )
        if frontier_path.exists():
            self.pass_("state_frontier_pointer_exists", "state execution_frontier pointer exists", path=str(frontier_path))
        else:
            self.fail("state_frontier_pointer_exists", "state execution_frontier pointer is missing", path=str(frontier_path))

    def check_frontier(self) -> None:
        assert self.state is not None
        frontier_path = self.resolve_project_path(
            self.state.get("execution_frontier"),
            self.flowpilot_root / "execution_frontier.json",
        )
        self.frontier = self.load_json(frontier_path, "execution_frontier_present")
        if not self.frontier:
            return

        frontier_route = self.frontier.get("active_route")
        if frontier_route == self.route_id:
            self.pass_("frontier_route_matches_state", "frontier active_route matches state")
        else:
            self.fail(
                "frontier_route_matches_state",
                "frontier active_route does not match state",
                frontier_route=frontier_route,
                route_id=self.route_id,
            )

        for key in ("route_version", "frontier_version"):
            state_value = self.state.get(key)
            frontier_value = self.frontier.get(key)
            if state_value == frontier_value:
                self.pass_(f"frontier_{key}_matches_state", f"frontier {key} matches state", value=state_value)
            else:
                self.fail(
                    f"frontier_{key}_matches_state",
                    f"frontier {key} does not match state",
                    state_value=state_value,
                    frontier_value=frontier_value,
                )

        state_node = self.state.get("active_node")
        frontier_node = self.frontier.get("active_node")
        if state_node == frontier_node:
            self.pass_("frontier_active_node_matches_state", "frontier active_node matches state", active_node=state_node)
        else:
            self.fail(
                "frontier_active_node_matches_state",
                "frontier active_node does not match state",
                state_node=state_node,
                frontier_node=frontier_node,
            )

    def check_route(self) -> None:
        if not self.route_id:
            return
        route_path = self.flowpilot_root / "routes" / self.route_id / "flow.json"
        self.route = self.load_json(route_path, "route_flow_present")
        if not self.route:
            return

        if self.route.get("route_id") == self.route_id:
            self.pass_("route_id_matches_state", "route file id matches active route")
        else:
            self.fail(
                "route_id_matches_state",
                "route file id does not match active route",
                route_id=self.route.get("route_id"),
                active_route=self.route_id,
            )

        route_status = str(self.route.get("status", "")).lower()
        if route_status in TERMINAL_STATUSES:
            self.fail("route_nonterminal", "route file is terminal and cannot be startup-active", route_status=route_status)
        else:
            self.pass_("route_nonterminal", "route file is nonterminal", route_status=route_status)

        route_version = self.route.get("route_version")
        state_version = self.state.get("route_version") if self.state else None
        if route_version is None or route_version == state_version:
            self.pass_("route_version_matches_state", "route version matches state or is not versioned", route_version=route_version)
        else:
            self.fail(
                "route_version_matches_state",
                "route version does not match state",
                route_version=route_version,
                state_version=state_version,
            )

    def check_crew(self) -> None:
        assert self.state is not None
        crew_path = self.resolve_project_path(self.state.get("crew_ledger"), self.flowpilot_root / "crew_ledger.json")
        self.crew = self.load_json(crew_path, "crew_ledger_present")
        if not self.crew:
            return

        if self.crew.get("route_id") == self.route_id:
            self.pass_("crew_route_matches_state", "crew ledger route matches active route")
        else:
            self.fail(
                "crew_route_matches_state",
                "crew ledger route does not match active route",
                crew_route=self.crew.get("route_id"),
                active_route=self.route_id,
            )

        crew_status = str(self.crew.get("crew_status", "")).lower()
        if crew_status in TERMINAL_STATUSES:
            self.fail("crew_not_archived", "crew ledger is archived or terminal", crew_status=crew_status)
        else:
            self.pass_("crew_not_archived", "crew ledger is current", crew_status=crew_status)

        roles = self.crew.get("roles")
        if not isinstance(roles, list):
            self.fail("crew_roles_shape", "crew roles must be a list")
            return
        role_records = {
            str(role.get("role_key") or role.get("role") or ""): role
            for role in roles
            if isinstance(role, dict)
        }
        missing_roles = [role for role in REQUIRED_ROLES if role not in role_records]
        if missing_roles:
            self.fail("crew_required_roles_present", "crew ledger is missing required roles", missing_roles=missing_roles)
        else:
            self.pass_("crew_required_roles_present", "crew ledger contains all required roles", role_count=len(role_records))

        inactive_roles: list[dict[str, str]] = []
        memory_packets = 0
        for role_name in REQUIRED_ROLES:
            role = role_records.get(role_name)
            if not role:
                continue
            status = str(role.get("status", "")).lower()
            if status not in ACTIVE_CREW_STATUSES:
                inactive_roles.append({"role": role_name, "status": status})
            memory_path = self.resolve_project_path(
                role.get("memory_path"),
                self.flowpilot_root / "crew_memory" / f"{role_name}.json",
            )
            memory = self.load_json(memory_path, f"role_memory:{role_name}")
            if memory and memory.get("role") == role_name and memory.get("route_id") == self.route_id:
                memory_packets += 1
            elif memory:
                self.fail(
                    f"role_memory_current:{role_name}",
                    "role memory packet does not match current role and route",
                    packet_role=memory.get("role"),
                    packet_route=memory.get("route_id"),
                    expected_route=self.route_id,
                )
        if inactive_roles:
            self.fail("crew_roles_active", "one or more required crew roles are not active/current", inactive_roles=inactive_roles)
        else:
            self.pass_("crew_roles_active", "all required crew roles are active/current")

        if memory_packets == len(REQUIRED_ROLES):
            self.pass_("crew_role_memory_current", "all required role memory packets match the active route", memory_packets=memory_packets)
        else:
            self.fail(
                "crew_role_memory_current",
                "required role memory packets are missing or stale",
                memory_packets=memory_packets,
                required=len(REQUIRED_ROLES),
            )

    def check_startup_activation(self) -> None:
        state_activation = self.state.get("startup_activation") if self.state else None
        frontier_activation = self.frontier.get("startup_activation") if self.frontier else None
        for source, activation in (("state", state_activation), ("frontier", frontier_activation)):
            if not isinstance(activation, dict):
                self.fail(f"{source}_startup_activation_present", f"{source} startup_activation block is missing")
                continue
            if activation.get("hard_gate_required") is True:
                self.pass_(f"{source}_startup_activation_required", f"{source} requires the startup hard gate")
            else:
                self.fail(f"{source}_startup_activation_required", f"{source} does not require the startup hard gate")
            if activation.get("shadow_route_detected") is True:
                self.fail(f"{source}_shadow_route_clear", f"{source} reports a shadow route")
            else:
                self.pass_(f"{source}_shadow_route_clear", f"{source} does not report a shadow route")
            for flag in (
                "route_files_written",
                "canonical_state_written",
                "execution_frontier_written",
                "crew_ledger_current",
                "continuation_ready",
            ):
                if activation.get(flag) is True:
                    self.pass_(f"{source}_{flag}", f"{source} startup flag {flag} is true")
                else:
                    self.fail(f"{source}_{flag}", f"{source} startup flag {flag} is not true")
            packet_count = activation.get("role_memory_packets_current")
            if isinstance(packet_count, int) and packet_count >= len(REQUIRED_ROLES):
                self.pass_(f"{source}_role_memory_packet_count", f"{source} records enough role memory packets", count=packet_count)
            else:
                self.fail(
                    f"{source}_role_memory_packet_count",
                    f"{source} does not record enough role memory packets",
                    count=packet_count,
                    required=len(REQUIRED_ROLES),
                )
            self.check_live_subagent_startup(source, activation)
            if activation.get("work_beyond_startup_allowed") is True and activation.get("startup_guard_passed") is not True:
                self.fail(
                    f"{source}_work_allowed_requires_recorded_pass",
                    f"{source} allows work beyond startup without a recorded startup guard pass",
                )
            elif activation.get("work_beyond_startup_allowed") is True:
                self.pass_(f"{source}_work_allowed_requires_recorded_pass", f"{source} recorded guard pass before allowing work")
            if self.require_recorded_pass:
                if activation.get("startup_guard_passed") is True and activation.get("guard_route_id") == self.route_id:
                    self.pass_(f"{source}_recorded_guard_pass", f"{source} records a startup guard pass for this route")
                else:
                    self.fail(
                        f"{source}_recorded_guard_pass",
                        f"{source} lacks recorded startup guard pass for this route",
                        guard_route_id=activation.get("guard_route_id"),
                        route_id=self.route_id,
                    )

    def check_live_subagent_startup(self, source: str, activation: dict[str, Any]) -> None:
        startup = activation.get("live_subagent_startup")
        if not isinstance(startup, dict):
            self.fail(
                f"{source}_live_subagent_startup_present",
                f"{source} live_subagent_startup block is missing",
            )
            return

        if startup.get("required_by_default") is True:
            self.pass_(
                f"{source}_live_subagent_startup_required",
                f"{source} records live subagents as the default startup target",
            )
        else:
            self.fail(
                f"{source}_live_subagent_startup_required",
                f"{source} does not record live subagents as the default startup target",
            )

        decision = str(startup.get("decision", "")).lower()
        user_decision_recorded = startup.get("user_decision_recorded") is True
        live_agents_active = startup.get("live_agents_active")
        live_count = live_agents_active if isinstance(live_agents_active, int) else 0

        live_ready = (
            decision in LIVE_SUBAGENT_READY_DECISIONS
            and user_decision_recorded
            and startup.get("user_authorized_live_start") is True
            and startup.get("live_start_attempted") is True
            and live_count >= len(REQUIRED_ROLES)
        )
        fallback_authorized = (
            decision in SINGLE_AGENT_CONTINUITY_DECISIONS
            and user_decision_recorded
            and startup.get("single_agent_role_continuity_authorized") is True
        )

        if live_ready:
            self.pass_(
                f"{source}_live_subagent_startup_resolved",
                f"{source} records six live background agents as started or resumed",
                decision=decision,
                live_agents_active=live_count,
            )
            return
        if fallback_authorized:
            self.pass_(
                f"{source}_live_subagent_startup_resolved",
                f"{source} records explicit user authorization for single-agent role continuity",
                decision=decision,
            )
            return
        self.fail(
            f"{source}_live_subagent_startup_resolved",
            f"{source} has neither six live background agents nor explicit user-authorized single-agent role continuity",
            decision=decision,
            user_decision_recorded=user_decision_recorded,
            user_authorized_live_start=startup.get("user_authorized_live_start"),
            live_start_attempted=startup.get("live_start_attempted"),
            live_agents_active=live_agents_active,
            single_agent_role_continuity_authorized=startup.get("single_agent_role_continuity_authorized"),
            blocker=startup.get("blocker"),
        )

    def check_continuation(self) -> None:
        if not self.state or not self.frontier:
            return
        state_mode = self.state.get("continuation_mode")
        state_probe = self.state.get("host_continuation_probe") if isinstance(self.state.get("host_continuation_probe"), dict) else {}
        continuation = self.frontier.get("continuation")
        if not isinstance(continuation, dict):
            self.fail("frontier_continuation_present", "frontier continuation block is missing")
            return
        frontier_mode = continuation.get("mode")
        if state_mode == frontier_mode:
            self.pass_("continuation_mode_matches", "state and frontier continuation modes match", mode=frontier_mode)
        else:
            self.fail("continuation_mode_matches", "state and frontier continuation modes differ", state_mode=state_mode, frontier_mode=frontier_mode)

        if frontier_mode == "automated":
            launcher = self.frontier.get("heartbeat_launcher") if isinstance(self.frontier.get("heartbeat_launcher"), dict) else {}
            watchdog = self.frontier.get("watchdog") if isinstance(self.frontier.get("watchdog"), dict) else {}
            ok = (
                continuation.get("host_probe_done") is True
                and continuation.get("host_supports_real_wakeups") is True
                and continuation.get("automated_bundle_ready") is True
                and continuation.get("manual_resume_recorded") is False
                and state_probe.get("done") is True
                and state_probe.get("host_supports_real_wakeups") is True
                and launcher.get("status") == "active"
                and bool(launcher.get("automation_id"))
                and watchdog.get("paired_with_heartbeat") is True
                and watchdog.get("active") is True
            )
            if ok:
                self.pass_("continuation_ready", "automated heartbeat/watchdog/global continuation bundle is ready")
            else:
                self.fail(
                    "continuation_ready",
                    "automated continuation is incomplete",
                    continuation=continuation,
                    heartbeat_launcher=launcher,
                    watchdog=watchdog,
                    state_probe=state_probe,
                )
            return
        if frontier_mode == "manual-resume":
            no_automation = (
                continuation.get("host_probe_done") is True
                and continuation.get("host_supports_real_wakeups") is False
                and continuation.get("manual_resume_recorded") is True
                and continuation.get("automated_bundle_ready") is False
                and state_probe.get("done") is True
                and state_probe.get("host_supports_real_wakeups") is False
            )
            if no_automation:
                self.pass_("continuation_ready", "manual-resume continuation evidence is ready and no automation is claimed")
            else:
                self.fail(
                    "continuation_ready",
                    "manual-resume continuation evidence is incomplete or automation is claimed",
                    continuation=continuation,
                    state_probe=state_probe,
                )
            return
        self.fail("continuation_ready", "continuation mode is not ready", mode=frontier_mode)

    def result(self) -> dict[str, Any]:
        ok = all(check.ok for check in self.checks)
        return {
            "ok": ok,
            "route_id": self.route_id,
            "checked_at": now_utc(),
            "checks": [check.to_json() for check in self.checks],
            "errors": [check.to_json() for check in self.checks if not check.ok],
        }

    def write_pass_evidence(self, result: dict[str, Any]) -> str:
        assert self.state is not None
        assert self.frontier is not None
        evidence_dir = self.flowpilot_root / "startup_guard"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        latest_path = evidence_dir / "latest.json"
        evidence = dict(result)
        evidence["recorded_pass"] = True
        evidence["work_beyond_startup_allowed"] = True
        write_json(latest_path, evidence)

        rel_evidence = ".flowpilot/startup_guard/latest.json"
        for target in (self.state, self.frontier):
            activation = target.setdefault("startup_activation", {})
            activation.update(
                {
                    "startup_guard_passed": True,
                    "startup_guard_checked_at": evidence["checked_at"],
                    "startup_guard_evidence_path": rel_evidence,
                    "guard_route_id": self.route_id,
                    "work_beyond_startup_allowed": True,
                    "shadow_route_detected": False,
                }
            )
            target["updated_at"] = evidence["checked_at"]

        write_json(self.flowpilot_root / "state.json", self.state)
        frontier_path = self.resolve_project_path(
            self.state.get("execution_frontier"),
            self.flowpilot_root / "execution_frontier.json",
        )
        write_json(frontier_path, self.frontier)
        return rel_evidence


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Project root containing .flowpilot")
    parser.add_argument("--route-id", default=None, help="Expected active route id")
    parser.add_argument(
        "--require-recorded-pass",
        action="store_true",
        help="Require state/frontier startup_activation to already record a guard pass",
    )
    parser.add_argument(
        "--record-pass",
        action="store_true",
        help="When checks pass, write .flowpilot/startup_guard/latest.json and update state/frontier pass fields",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    guard = StartupGuard(
        root=Path(args.root),
        route_id=args.route_id,
        require_recorded_pass=args.require_recorded_pass,
        record_pass=args.record_pass,
    )
    result = guard.run()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        status = "PASS" if result["ok"] else "FAIL"
        print(f"FlowPilot startup guard: {status} ({result.get('route_id')})")
        for check in result["checks"]:
            prefix = "ok" if check["ok"] else "fail"
            print(f"- {prefix}: {check['name']} - {check['message']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
