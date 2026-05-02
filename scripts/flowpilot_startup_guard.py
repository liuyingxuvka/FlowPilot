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

VALID_RUN_MODES = {
    "full-auto",
    "autonomous",
    "guided",
    "strict-gated",
}

BACKGROUND_AGENT_ALLOW = {
    "allow",
    "allow_live_agents",
    "live_agents",
    "six_live_agents",
    "yes",
}

BACKGROUND_AGENT_SINGLE = {
    "single-agent",
    "single_agent",
    "single_agent_only",
    "manual",
    "deny",
    "no",
}

SCHEDULED_CONTINUATION_ALLOW = {
    "allow",
    "allow_heartbeat",
    "allow_scheduled",
    "automated",
    "heartbeat",
    "yes",
}

SCHEDULED_CONTINUATION_MANUAL = {
    "manual",
    "manual-resume",
    "manual_resume",
    "deny",
    "no",
}

VALID_ANSWER_SOURCES = {
    "user_reply",
    "user_reply_after_prompt",
}

INVALID_ANSWER_SOURCES = {
    "agent_inferred",
    "default",
    "prior_route",
    "single_message_invocation",
    "main_executor_inferred",
}

REVIEWER_REPORT_ONLY_AUTHORITY = "report_only_no_start_approval"

PM_START_GATE_OPEN_DECISIONS = {
    "open",
    "opened",
    "start_gate_open",
    "work_beyond_startup_allowed",
}

STARTUP_REVIEW_SCOPE = (
    "user_authorization_vs_state",
    "route_state_frontier_consistency",
    "old_route_and_asset_reuse_boundary",
    "heartbeat_watchdog_supervisor_evidence",
    "background_agent_role_evidence",
    "shadow_route_and_residual_state",
)


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
        write_review_report: bool,
    ) -> None:
        self.root = root.resolve()
        self.flowpilot_root = self.root / ".flowpilot"
        self.route_id = route_id
        self.require_recorded_pass = require_recorded_pass
        self.record_pass = record_pass
        self.write_review_report_requested = write_review_report
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
        if self.record_pass or self.require_recorded_pass:
            self.check_reviewer_report_and_pm_start_gate()

        result = self.result()
        if self.write_review_report_requested:
            report_path = self.write_review_report(result)
            result["startup_review_report_path"] = report_path
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

    def record_pm_start_gate(self, *, decision: str, review_report_path: str | None) -> dict[str, Any]:
        self.state = self.load_json(self.flowpilot_root / "state.json", "state_json_present")
        if not self.state:
            return self.result()
        active_route = self.state.get("active_route")
        if self.route_id is None:
            self.route_id = active_route if isinstance(active_route, str) else None
        if not self.route_id:
            self.fail("route_id_resolved", "active route could not be resolved from state or --route-id")
            return self.result()
        frontier_path = self.resolve_project_path(
            self.state.get("execution_frontier"),
            self.flowpilot_root / "execution_frontier.json",
        )
        self.frontier = self.load_json(frontier_path, "execution_frontier_present")
        if not self.frontier:
            return self.result()

        rel_report = review_report_path or ".flowpilot/startup_review/latest.json"
        report_path = self.resolve_project_path(rel_report, self.flowpilot_root / "startup_review" / "latest.json")
        report = self.load_json(report_path, "startup_review_report_file")
        if not report:
            return self.result()

        clean_report = (
            report.get("ok") is True
            and report.get("route_id") == self.route_id
            and report.get("reviewer_decision_authority") == REVIEWER_REPORT_ONLY_AUTHORITY
            and int(report.get("blocking_findings", -1)) == 0
        )
        decision = decision.lower()
        if decision in PM_START_GATE_OPEN_DECISIONS and clean_report:
            self.pass_("pm_can_open_start_gate", "PM may open the startup gate from the clean reviewer report")
        elif decision in PM_START_GATE_OPEN_DECISIONS:
            self.fail(
                "pm_can_open_start_gate",
                "PM cannot open startup from a blocked, stale, or wrong-authority reviewer report",
                report_ok=report.get("ok"),
                report_route_id=report.get("route_id"),
                blocking_findings=report.get("blocking_findings"),
                reviewer_decision_authority=report.get("reviewer_decision_authority"),
            )
            return self.result()
        elif decision in {"return_to_worker", "blocked"}:
            self.pass_("pm_records_non_open_decision", "PM recorded a non-open startup decision")
        else:
            self.fail("pm_start_gate_decision_valid", "PM start-gate decision is not recognized", decision=decision)
            return self.result()

        checked_at = now_utc()
        decision_dir = self.flowpilot_root / "startup_pm_gate"
        decision_dir.mkdir(parents=True, exist_ok=True)
        latest_path = decision_dir / "latest.json"
        rel_decision = ".flowpilot/startup_pm_gate/latest.json"
        opened = decision in PM_START_GATE_OPEN_DECISIONS
        gate_record = {
            "decision_type": "startup_pm_start_gate",
            "route_id": self.route_id,
            "decided_at": checked_at,
            "decision_owner": "project_manager",
            "decision": "open" if opened else decision,
            "based_on_review_report_path": rel_report,
            "worker_remediation_required": not opened,
            "remediation_items": report.get("errors", []) if not opened else [],
            "opened_at": checked_at if opened else None,
            "notes": "PM interpreted the human-like reviewer startup report.",
        }
        write_json(latest_path, gate_record)

        report_status = "ready_for_pm" if clean_report else "requires_worker_remediation"
        blocking_findings = int(report.get("blocking_findings", 0))
        for target in (self.state, self.frontier):
            activation = target.setdefault("startup_activation", {})
            activation["startup_preflight_review"] = {
                "required": True,
                "reviewer_role": "human_like_reviewer",
                "reviewer_decision_authority": REVIEWER_REPORT_ONLY_AUTHORITY,
                "report_path": rel_report,
                "report_status": report_status,
                "blocking_findings": blocking_findings,
                "checked_at": report.get("checked_at"),
                "review_iteration": activation.get("startup_preflight_review", {}).get("review_iteration", 1)
                if isinstance(activation.get("startup_preflight_review"), dict)
                else 1,
                "checked_user_authorization_vs_state": True,
                "checked_route_state_frontier_consistency": True,
                "checked_old_route_and_asset_reuse_boundary": True,
                "checked_heartbeat_watchdog_supervisor_evidence": True,
                "checked_background_agent_role_evidence": True,
                "checked_shadow_route_and_residual_state": True,
            }
            activation["pm_start_gate"] = {
                "required": True,
                "decision_owner": "project_manager",
                "decision": "open" if opened else decision,
                "decision_path": rel_decision,
                "based_on_review_report_path": rel_report,
                "worker_remediation_required": not opened,
                "review_iteration": activation["startup_preflight_review"]["review_iteration"],
                "opened_at": checked_at if opened else None,
            }
            target["updated_at"] = checked_at

        write_json(self.flowpilot_root / "state.json", self.state)
        write_json(frontier_path, self.frontier)
        result = self.result()
        result["pm_start_gate_decision_path"] = rel_decision
        return result

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
            self.check_startup_questions(source, activation)
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

    def check_reviewer_report_and_pm_start_gate(self) -> None:
        for source, activation in (
            ("state", self.state.get("startup_activation") if self.state else None),
            ("frontier", self.frontier.get("startup_activation") if self.frontier else None),
        ):
            if not isinstance(activation, dict):
                self.fail(
                    f"{source}_startup_review_activation_present",
                    f"{source} startup_activation block is missing before PM start gate check",
                )
                continue

            review = activation.get("startup_preflight_review")
            if not isinstance(review, dict):
                self.fail(
                    f"{source}_startup_review_present",
                    f"{source} startup_preflight_review block is missing",
                )
                continue

            if review.get("required") is True:
                self.pass_(f"{source}_startup_review_required", f"{source} requires startup preflight review")
            else:
                self.fail(f"{source}_startup_review_required", f"{source} does not require startup preflight review")

            if review.get("reviewer_role") == "human_like_reviewer":
                self.pass_(f"{source}_startup_review_role", f"{source} assigns review to the human-like reviewer")
            else:
                self.fail(
                    f"{source}_startup_review_role",
                    f"{source} startup review is not assigned to the human-like reviewer",
                    reviewer_role=review.get("reviewer_role"),
                )

            if review.get("reviewer_decision_authority") == REVIEWER_REPORT_ONLY_AUTHORITY:
                self.pass_(
                    f"{source}_startup_review_report_only",
                    f"{source} records reviewer as report-only, not start-gate approver",
                )
            else:
                self.fail(
                    f"{source}_startup_review_report_only",
                    f"{source} does not forbid reviewer start-gate approval",
                    authority=review.get("reviewer_decision_authority"),
                )

            report_path_value = review.get("report_path")
            report_path = self.resolve_project_path(
                report_path_value if isinstance(report_path_value, str) else None,
                self.flowpilot_root / "startup_review" / "latest.json",
            )
            report = self.load_json(report_path, f"{source}_startup_review_report_file")
            report_ok = False
            if report:
                report_ok = (
                    report.get("ok") is True
                    and report.get("route_id") == self.route_id
                    and report.get("reviewer_decision_authority") == REVIEWER_REPORT_ONLY_AUTHORITY
                    and int(report.get("blocking_findings", -1)) == 0
                )
                if report_ok:
                    self.pass_(f"{source}_startup_review_report_clean", f"{source} reviewer report has no startup blockers")
                else:
                    self.fail(
                        f"{source}_startup_review_report_clean",
                        f"{source} reviewer report still has startup blockers or wrong authority",
                        report_ok=report.get("ok"),
                        report_route_id=report.get("route_id"),
                        blocking_findings=report.get("blocking_findings"),
                        reviewer_decision_authority=report.get("reviewer_decision_authority"),
                    )

            checked_flags = (
                "checked_user_authorization_vs_state",
                "checked_route_state_frontier_consistency",
                "checked_old_route_and_asset_reuse_boundary",
                "checked_heartbeat_watchdog_supervisor_evidence",
                "checked_background_agent_role_evidence",
                "checked_shadow_route_and_residual_state",
            )
            missing_flags = [flag for flag in checked_flags if review.get(flag) is not True]
            if not missing_flags:
                self.pass_(f"{source}_startup_review_scope_checked", f"{source} reviewer scope flags are complete")
            else:
                self.fail(
                    f"{source}_startup_review_scope_checked",
                    f"{source} reviewer scope flags are incomplete",
                    missing_flags=missing_flags,
                )

            if review.get("report_status") == "ready_for_pm" and review.get("blocking_findings") == 0 and report_ok:
                self.pass_(f"{source}_startup_review_ready_for_pm", f"{source} reviewer report is ready for PM interpretation")
            else:
                self.fail(
                    f"{source}_startup_review_ready_for_pm",
                    f"{source} reviewer report is not ready for PM start-gate decision",
                    report_status=review.get("report_status"),
                    blocking_findings=review.get("blocking_findings"),
                )

            pm_gate = activation.get("pm_start_gate")
            if not isinstance(pm_gate, dict):
                self.fail(f"{source}_pm_start_gate_present", f"{source} pm_start_gate block is missing")
                continue
            if pm_gate.get("required") is True and pm_gate.get("decision_owner") == "project_manager":
                self.pass_(f"{source}_pm_start_gate_owner", f"{source} PM owns the startup gate")
            else:
                self.fail(
                    f"{source}_pm_start_gate_owner",
                    f"{source} startup gate is not owned by the project manager",
                    required=pm_gate.get("required"),
                    decision_owner=pm_gate.get("decision_owner"),
                )

            decision = str(pm_gate.get("decision", "")).lower()
            based_on = pm_gate.get("based_on_review_report_path")
            if decision in PM_START_GATE_OPEN_DECISIONS and based_on == report_path_value:
                self.pass_(
                    f"{source}_pm_start_gate_opened_from_report",
                    f"{source} PM opened the startup gate from the reviewer report",
                    decision=decision,
                )
            else:
                self.fail(
                    f"{source}_pm_start_gate_opened_from_report",
                    f"{source} PM has not opened the startup gate from the current reviewer report",
                    decision=decision,
                    based_on_review_report_path=based_on,
                    expected_report_path=report_path_value,
                )

            decision_path_value = pm_gate.get("decision_path")
            decision_path = self.resolve_project_path(
                decision_path_value if isinstance(decision_path_value, str) else None,
                self.flowpilot_root / "startup_pm_gate" / "latest.json",
            )
            if decision_path.exists():
                self.pass_(f"{source}_pm_start_gate_decision_file", f"{source} PM start-gate decision evidence exists", path=str(decision_path))
            else:
                self.fail(f"{source}_pm_start_gate_decision_file", f"{source} PM start-gate decision evidence is missing", path=str(decision_path))

            if pm_gate.get("worker_remediation_required") is False:
                self.pass_(f"{source}_pm_start_gate_no_open_remediation", f"{source} PM did not open the gate while remediation was required")
            else:
                self.fail(
                    f"{source}_pm_start_gate_no_open_remediation",
                    f"{source} PM start gate still records required worker remediation",
                )

    def startup_answer(self, activation: dict[str, Any] | None, key: str) -> str:
        if not isinstance(activation, dict):
            return ""
        questions = activation.get("startup_questions")
        if not isinstance(questions, dict):
            return ""
        answers = questions.get("answers")
        if not isinstance(answers, dict):
            return ""
        record = answers.get(key)
        if not isinstance(record, dict):
            return ""
        return str(record.get("answer", "")).strip().lower()

    def check_startup_questions(self, source: str, activation: dict[str, Any]) -> None:
        questions = activation.get("startup_questions")
        if not isinstance(questions, dict):
            self.fail(
                f"{source}_startup_questions_present",
                f"{source} startup_questions block is missing",
            )
            return

        if questions.get("required") is True:
            self.pass_(f"{source}_startup_questions_required", f"{source} requires the three-question startup gate")
        else:
            self.fail(f"{source}_startup_questions_required", f"{source} does not require the three-question startup gate")

        if questions.get("asked_before_banner") is True:
            self.pass_(f"{source}_startup_questions_asked_before_banner", f"{source} records questions before banner")
        else:
            self.fail(f"{source}_startup_questions_asked_before_banner", f"{source} does not record questions before banner")

        if questions.get("dialog_stopped_for_user_answers") is True:
            self.pass_(
                f"{source}_startup_questions_dialog_stopped",
                f"{source} records that the assistant stopped after asking startup questions",
            )
        else:
            self.fail(
                f"{source}_startup_questions_dialog_stopped",
                f"{source} does not record a stop-and-wait state after asking startup questions",
            )

        source_name = str(questions.get("answer_source", "")).lower()
        if source_name in VALID_ANSWER_SOURCES:
            self.pass_(f"{source}_startup_question_answer_source", f"{source} has an explicit user answer source", answer_source=source_name)
        elif source_name in INVALID_ANSWER_SOURCES:
            self.fail(f"{source}_startup_question_answer_source", f"{source} used an invalid inferred answer source", answer_source=source_name)
        else:
            self.fail(f"{source}_startup_question_answer_source", f"{source} lacks a valid explicit user answer source", answer_source=source_name)

        if questions.get("explicit_user_answer_recorded") is True:
            self.pass_(f"{source}_startup_questions_user_answer_recorded", f"{source} records explicit user answers")
        else:
            self.fail(f"{source}_startup_questions_user_answer_recorded", f"{source} lacks explicit user answers")

        if questions.get("answer_evidence_path"):
            self.pass_(f"{source}_startup_question_answer_evidence", f"{source} records answer evidence")
        else:
            self.fail(f"{source}_startup_question_answer_evidence", f"{source} lacks answer evidence")

        if questions.get("status") == "answered":
            self.pass_(f"{source}_startup_questions_answered_status", f"{source} marks the startup questions answered")
        else:
            self.fail(f"{source}_startup_questions_answered_status", f"{source} does not mark the startup questions answered", status=questions.get("status"))

        if questions.get("banner_emitted_after_answers") is True:
            self.pass_(f"{source}_startup_banner_after_answers", f"{source} records banner emitted after answers")
        else:
            self.fail(f"{source}_startup_banner_after_answers", f"{source} does not record banner after answers")

        run_mode = self.startup_answer(activation, "run_mode")
        if run_mode in VALID_RUN_MODES:
            self.pass_(f"{source}_startup_run_mode_answer", f"{source} has a valid run-mode answer", answer=run_mode)
        else:
            self.fail(f"{source}_startup_run_mode_answer", f"{source} lacks a valid run-mode answer", answer=run_mode)

        background_agents = self.startup_answer(activation, "background_agents")
        if background_agents in BACKGROUND_AGENT_ALLOW | BACKGROUND_AGENT_SINGLE:
            self.pass_(f"{source}_startup_background_agents_answer", f"{source} has a valid background-agent answer", answer=background_agents)
        else:
            self.fail(f"{source}_startup_background_agents_answer", f"{source} lacks a valid background-agent answer", answer=background_agents)

        scheduled = self.startup_answer(activation, "scheduled_continuation")
        if scheduled in SCHEDULED_CONTINUATION_ALLOW | SCHEDULED_CONTINUATION_MANUAL:
            self.pass_(f"{source}_startup_scheduled_continuation_answer", f"{source} has a valid scheduled-continuation answer", answer=scheduled)
        else:
            self.fail(f"{source}_startup_scheduled_continuation_answer", f"{source} lacks a valid scheduled-continuation answer", answer=scheduled)

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
        background_answer = self.startup_answer(activation, "background_agents")
        allow_live_agents = background_answer in BACKGROUND_AGENT_ALLOW
        use_single_agent = background_answer in BACKGROUND_AGENT_SINGLE

        live_ready = (
            decision in LIVE_SUBAGENT_READY_DECISIONS
            and user_decision_recorded
            and startup.get("user_authorized_live_start") is True
            and startup.get("live_start_attempted") is True
            and live_count >= len(REQUIRED_ROLES)
            and allow_live_agents
        )
        fallback_authorized = (
            decision in SINGLE_AGENT_CONTINUITY_DECISIONS
            and user_decision_recorded
            and startup.get("single_agent_role_continuity_authorized") is True
            and use_single_agent
        )

        if live_ready:
            self.pass_(
                f"{source}_live_subagent_startup_resolved",
                f"{source} records six live background agents as started or resumed",
                decision=decision,
                live_agents_active=live_count,
                startup_answer=background_answer,
            )
            return
        if fallback_authorized:
            self.pass_(
                f"{source}_live_subagent_startup_resolved",
                f"{source} records explicit user authorization for single-agent role continuity",
                decision=decision,
                startup_answer=background_answer,
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
            startup_background_agents_answer=background_answer,
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

        scheduled_answer = self.startup_answer(
            self.state.get("startup_activation") if isinstance(self.state.get("startup_activation"), dict) else None,
            "scheduled_continuation",
        )
        scheduled_allows_automation = scheduled_answer in SCHEDULED_CONTINUATION_ALLOW
        scheduled_manual = scheduled_answer in SCHEDULED_CONTINUATION_MANUAL

        if frontier_mode == "automated":
            if not scheduled_allows_automation:
                self.fail(
                    "continuation_matches_startup_answer",
                    "automated continuation conflicts with the startup scheduled-continuation answer",
                    scheduled_answer=scheduled_answer,
                )
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
            if not scheduled_manual:
                self.fail(
                    "continuation_matches_startup_answer",
                    "manual-resume continuation conflicts with the startup scheduled-continuation answer",
                    scheduled_answer=scheduled_answer,
                )
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

    def write_review_report(self, result: dict[str, Any]) -> str:
        assert self.state is not None
        assert self.frontier is not None
        evidence_dir = self.flowpilot_root / "startup_review"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        latest_path = evidence_dir / "latest.json"
        rel_report = ".flowpilot/startup_review/latest.json"
        blocking_findings = len(result["errors"])
        report = dict(result)
        report.update(
            {
                "report_type": "startup_preflight_review",
                "reviewer_role": "human_like_reviewer",
                "reviewer_decision_authority": REVIEWER_REPORT_ONLY_AUTHORITY,
                "scope": list(STARTUP_REVIEW_SCOPE),
                "blocking_findings": blocking_findings,
                "report_status": "ready_for_pm" if blocking_findings == 0 else "requires_worker_remediation",
                "pm_decision_authority": "project_manager",
            }
        )
        write_json(latest_path, report)

        now = report["checked_at"]
        for target in (self.state, self.frontier):
            activation = target.setdefault("startup_activation", {})
            previous_review = activation.get("startup_preflight_review")
            previous_iteration = 0
            if isinstance(previous_review, dict) and isinstance(previous_review.get("review_iteration"), int):
                previous_iteration = previous_review["review_iteration"]
            activation["startup_preflight_review"] = {
                "required": True,
                "reviewer_role": "human_like_reviewer",
                "reviewer_decision_authority": REVIEWER_REPORT_ONLY_AUTHORITY,
                "report_path": rel_report,
                "report_status": report["report_status"],
                "blocking_findings": blocking_findings,
                "checked_at": now,
                "review_iteration": previous_iteration + 1,
                "checked_user_authorization_vs_state": True,
                "checked_route_state_frontier_consistency": True,
                "checked_old_route_and_asset_reuse_boundary": True,
                "checked_heartbeat_watchdog_supervisor_evidence": True,
                "checked_background_agent_role_evidence": True,
                "checked_shadow_route_and_residual_state": True,
            }
            activation["pm_start_gate"] = {
                "required": True,
                "decision_owner": "project_manager",
                "decision": "pending",
                "decision_path": None,
                "based_on_review_report_path": None,
                "worker_remediation_required": blocking_findings != 0,
                "review_iteration": previous_iteration + 1,
                "opened_at": None,
            }
            target["updated_at"] = now

        write_json(self.flowpilot_root / "state.json", self.state)
        frontier_path = self.resolve_project_path(
            self.state.get("execution_frontier"),
            self.flowpilot_root / "execution_frontier.json",
        )
        write_json(frontier_path, self.frontier)
        return rel_report

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
        help="When checks and the PM start gate pass, write .flowpilot/startup_guard/latest.json and update state/frontier pass fields",
    )
    parser.add_argument(
        "--write-review-report",
        action="store_true",
        help="Write .flowpilot/startup_review/latest.json as the human-like reviewer startup report without opening the PM start gate",
    )
    parser.add_argument(
        "--record-pm-start-gate",
        choices=["open", "return_to_worker", "blocked"],
        default=None,
        help="Record the project manager startup-gate decision from a reviewer report",
    )
    parser.add_argument(
        "--review-report-path",
        default=None,
        help="Reviewer report path for --record-pm-start-gate; defaults to .flowpilot/startup_review/latest.json",
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
        write_review_report=args.write_review_report,
    )
    if args.record_pm_start_gate:
        result = guard.record_pm_start_gate(
            decision=args.record_pm_start_gate,
            review_report_path=args.review_report_path,
        )
    else:
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
