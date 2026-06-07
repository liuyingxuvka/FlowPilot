"""Information-flow alignment source marker and symbol checks."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from flowguard import ModelTestAlignmentPlan, audit_python_code_contracts

from flowpilot_model_test_alignment_common import ROOT, _finding_counts
from flowpilot_information_flow_alignment_obligations import (
    OBL_BLOCKER_PAYLOAD,
    OBL_BREAK_GLASS,
    OBL_CLOSURE_STOP,
    OBL_RECHECK_FOLLOWUP,
    OBL_REOPEN_HISTORY,
    OBL_REQUIRED_REPAIR,
    OBL_RESUME_CURRENT,
    OBL_ROLE_ASSIGNMENT,
    OBL_ROUTE_MUTATION,
    OBL_WORKER_DELTA,
)


MARKER_REQUIREMENTS: tuple[Mapping[str, Any], ...] = (
    {
        "requirement_id": "runtime.pm_blocker_details",
        "path": "skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
        "markers": (
            "pm_visible_summary",
            "recent_role_report_summary",
            "authorized_result_reads",
            "required_repair",
            "recommended_resolution",
        ),
        "covers": (OBL_BLOCKER_PAYLOAD, OBL_REQUIRED_REPAIR),
    },
    {
        "requirement_id": "runtime.pm_body_open_receipt",
        "path": (
            "skills/flowpilot/assets/"
            "flowpilot_router_work_packets_pm_role_writes_decisions_role_result.py"
        ),
        "markers": (
            "result_body_opened_by_role",
            "body_hash_verified",
            "PM result disposition requires project_manager to open result body",
        ),
        "covers": (OBL_BLOCKER_PAYLOAD, OBL_REQUIRED_REPAIR),
    },
    {
        "requirement_id": "card.pm_review_repair_work_packet_minimums",
        "path": "skills/flowpilot/assets/runtime_kit/cards/phases/pm_review_repair.md",
        "markers": (
            "Reviewer `blocking_findings[].required_repair`",
            "work_packet.allowed_reads",
            "work_packet.allowed_writes",
            "work_packet.forbidden_actions",
            "work_packet.success_evidence",
            "fresh packet generation",
            "invalidate stale evidence",
        ),
        "covers": (OBL_REQUIRED_REPAIR, OBL_WORKER_DELTA, OBL_ROUTE_MUTATION),
    },
    {
        "requirement_id": "card.role_outputs_pm_visible_summary",
        "path": "skills/flowpilot/assets/runtime_kit/prompts/packets/output_contract_section.md",
        "markers": (
            "pm_visible_summary",
            "runtime relays it to PM and does not synthesize it",
        ),
        "covers": (OBL_BLOCKER_PAYLOAD,),
    },
    {
        "requirement_id": "prompt.open_packet_delivers_authorized_materials",
        "path": "skills/flowpilot/assets/runtime_kit/prompts/packets/packet_identity_boundary.md",
        "markers": (
            "authorized_result_reads",
            "flowpilot_new.py open-packet",
            "assigned role receives",
            "Do not ask Controller to relay them",
            "do not run a separate open-result step in the normal packet path",
        ),
        "covers": (OBL_BLOCKER_PAYLOAD, OBL_REQUIRED_REPAIR),
    },
    {
        "requirement_id": "role.open_packet_materials_guidance",
        "path": "skills/flowpilot/assets/runtime_kit/cards/roles/project_manager.md",
        "markers": (
            "authorized input",
            "flowpilot_new.py open-packet",
            "delivered result/report body",
            "do not decide from the summary alone",
        ),
        "covers": (OBL_BLOCKER_PAYLOAD, OBL_REQUIRED_REPAIR),
    },
    {
        "requirement_id": "card.resume_current_authority",
        "path": "skills/flowpilot/assets/runtime_kit/cards/system/controller_resume_reentry.md",
        "markers": (
            "current runtime ledger",
            "stale",
            "control-plane stuck status",
            "bounded `wait_agent`",
        ),
        "covers": (OBL_RESUME_CURRENT, OBL_REOPEN_HISTORY),
    },
    {
        "requirement_id": "prompt.lifecycle_resume_current_runtime",
        "path": "skills/flowpilot/assets/runtime_kit/prompts/startup/lifecycle_resume.md",
        "markers": (
            "flowpilot_new.py resume --reason manual_resume",
            "lifecycle guard",
            "foreground duty",
            "currently requested responsibility",
            "do not restore a fixed role set or prewarm all roles",
        ),
        "covers": (OBL_RESUME_CURRENT, OBL_ROLE_ASSIGNMENT),
    },
    {
        "requirement_id": "card.pm_resume_prior_path_context",
        "path": "skills/flowpilot/assets/runtime_kit/cards/phases/pm_resume_decision.md",
        "markers": (
            "prior_path_context_review",
            "current run",
            "stale_evidence_considered",
            "continue the current packet loop",
            "resolve-stopped-blocker",
        ),
        "covers": (OBL_RESUME_CURRENT, OBL_REOPEN_HISTORY),
    },
    {
        "requirement_id": "card.break_glass_scope_and_reintegration",
        "path": "skills/flowpilot/assets/runtime_kit/cards/system/controller_break_glass_repair.md",
        "markers": (
            "FlowPilot control-plane",
            "normal retry, PM repair, or role",
            "forbidden actions acknowledged",
            "PM/Reviewer/FlowGuard operator",
            "specific FlowPilot packet id",
        ),
        "covers": (OBL_BREAK_GLASS,),
    },
    {
        "requirement_id": "runtime.break_glass_bounded_records",
        "path": "skills/flowpilot/assets/flowpilot_controller_break_glass.py",
        "markers": (
            "allowed_reads",
            "allowed_writes",
            "forbidden_actions_acknowledged",
            "validation_evidence",
            "related_recovery_transaction_ids",
        ),
        "covers": (OBL_BREAK_GLASS,),
    },
    {
        "requirement_id": "runtime.role_assignment_current_packet_binding",
        "path": "skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
        "markers": (
            "def resolve_role_assignment",
            "assignment responsibility does not match packet",
            "role_assignments",
            "def lease_agent",
            "role_assignment_committed",
        ),
        "covers": (OBL_ROLE_ASSIGNMENT,),
    },
    {
        "requirement_id": "test.lifecycle_resume_no_role_prewarm",
        "path": "tests/test_flowpilot_new_entrypoint.py",
        "markers": (
            "test_manual_resume_uses_lifecycle_guard_without_heartbeat_or_role_prewarm",
            "role_assignments",
            "dispatch_current_role",
            "heartbeat",
        ),
        "covers": (OBL_RESUME_CURRENT, OBL_ROLE_ASSIGNMENT),
    },
    {
        "requirement_id": "test.followup_blocker_visible",
        "path": "tests/router_runtime/control_blockers.py",
        "markers": (
            "test_repair_transaction_recheck_blocker_registers_followup_blocker",
            "test_repair_transaction_protocol_blocker_registers_followup_blocker",
            "followup_blocker_id",
            "pm_records_control_blocker_followup_blocker",
        ),
        "covers": (OBL_RECHECK_FOLLOWUP,),
    },
    {
        "requirement_id": "test.route_mutation_stale_replay",
        "path": "tests/flowpilot_route_mutation_contracts.py",
        "markers": (
            "pending_route_mutation",
            "stale_evidence_ledger.json",
            "replay_scope_node_id",
            "candidate_route_version",
            "node_acceptance_plan_review_block",
        ),
        "covers": (OBL_ROUTE_MUTATION,),
    },
    {
        "requirement_id": "test.terminal_stop_quarantine",
        "path": "tests/router_runtime/terminal.py",
        "markers": (
            "test_user_stop_quarantines_active_repair_and_historical_control_plane_artifacts",
            "terminal_lifecycle_quarantined",
            "terminal_fence",
            "terminal_stopped",
            "terminal_next_step_cleared",
        ),
        "covers": (OBL_CLOSURE_STOP,),
    },
    {
        "requirement_id": "test.historical_not_current",
        "path": "tests/test_flowpilot_historical_live_run_replay.py",
        "markers": (
            "reject_stale_or_incomplete_evidence",
            "current_run_id",
            "terminal_ledger_not_closed",
            "progress_only",
        ),
        "covers": (OBL_REOPEN_HISTORY, OBL_CLOSURE_STOP),
    },
)


def _read_required_sources(paths: Sequence[str]) -> dict[str, str]:
    return {path: (ROOT / path).read_text(encoding="utf-8") for path in sorted(set(paths))}


def _marker_report() -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    for requirement in MARKER_REQUIREMENTS:
        path = str(requirement["path"])
        markers = tuple(str(item) for item in requirement["markers"])
        target = ROOT / path
        if not target.exists():
            missing = list(markers)
            text = ""
        else:
            text = target.read_text(encoding="utf-8")
            missing = [marker for marker in markers if marker not in text]
        check = {
            "requirement_id": requirement["requirement_id"],
            "path": path,
            "ok": not missing,
            "missing_markers": missing,
            "covers": list(requirement["covers"]),
        }
        checks.append(check)
        for marker in missing:
            findings.append(
                {
                    "severity": "high",
                    "code": "missing_information_flow_marker",
                    "requirement_id": requirement["requirement_id"],
                    "path": path,
                    "marker": marker,
                    "message": (
                        f"{requirement['requirement_id']} lacks required "
                        f"information-flow marker {marker!r}"
                    ),
                    "covered_obligations": list(requirement["covers"]),
                }
            )
    return {
        "ok": not findings,
        "check_count": len(checks),
        "checks": checks,
        "findings": findings,
        "finding_counts": _finding_counts(findings),
    }


def _code_symbol_report(plan: ModelTestAlignmentPlan) -> dict[str, Any]:
    paths = [contract.path for contract in plan.code_contracts]
    sources = _read_required_sources(paths)
    evidence = audit_python_code_contracts(plan.code_contracts, sources)
    findings: list[dict[str, Any]] = []
    for item in evidence:
        if item.found and not item.parse_error:
            continue
        findings.append(
            {
                "severity": "critical",
                "code": "missing_code_contract_symbol",
                "code_contract_id": item.code_contract_id,
                "path": item.path,
                "symbol": item.symbol,
                "parse_error": item.parse_error,
                "message": (
                    f"Code contract {item.code_contract_id} does not resolve "
                    f"symbol {item.symbol!r} in {item.path}"
                ),
            }
        )
    return {
        "ok": not findings,
        "contract_count": len(plan.code_contracts),
        "evidence": [item.to_dict() for item in evidence],
        "findings": findings,
        "finding_counts": _finding_counts(findings),
    }
