"""Run layered FlowPilot test tiers.

The runner keeps routine validation small, lets router domains run as child
suites, and launches long integration/release regressions with stable
background artifacts when requested.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
import subprocess
import sys
import threading
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BACKGROUND_DIR = ROOT / "tmp" / "test_background"
DEFAULT_BACKGROUND_MAX_PARALLEL = 4
BACKGROUND_SUPERVISOR_POLL_SECONDS = 2.0
ARTIFACT_SUFFIXES = ("out", "err", "combined", "exit", "meta")


@dataclass(frozen=True, slots=True)
class TierCommand:
    name: str
    command: tuple[str, ...]
    description: str
    long_running: bool = False
    release_only: bool = False
    background_recommended: bool = False
    background_stage: int = 0


def _py(*args: str) -> tuple[str, ...]:
    return (sys.executable, *args)


def _pytest(name: str, *paths: str, description: str) -> TierCommand:
    return TierCommand(name=name, command=_py("-m", "pytest", *paths, "-q"), description=description)


def _unittest(name: str, *modules: str, description: str) -> TierCommand:
    return TierCommand(name=name, command=_py("-m", "unittest", "-v", *modules), description=description)


def _unittest_k(name: str, *modules: str, patterns: tuple[str, ...], description: str) -> TierCommand:
    pattern_args: list[str] = []
    for pattern in patterns:
        pattern_args.extend(("-k", pattern))
    return TierCommand(
        name=name,
        command=_py("-m", "unittest", "-v", *pattern_args, *modules),
        description=description,
    )


FAST_COMMANDS = (
    TierCommand(
        name="flowguard_test_tiering",
        command=_py(
            "simulations/run_flowpilot_test_tiering_checks.py",
            "--json-out",
            "simulations/flowpilot_test_tiering_results.json",
        ),
        description="FlowGuard TestMesh-style checks for test tier ownership and evidence.",
    ),
    TierCommand(
        name="flowguard_slow_test_contracts",
        command=_py(
            "simulations/run_flowpilot_slow_test_contract_checks.py",
            "--json-out",
            "simulations/flowpilot_slow_test_contract_results.json",
        ),
        description="FlowGuard TestMesh contract checks for semantic parent/child slow-test splits.",
    ),
    TierCommand(
        name="flowguard_model_test_alignment",
        command=_py(
            "simulations/run_flowpilot_model_test_alignment_checks.py",
            "--json-out",
            "simulations/flowpilot_model_test_alignment_results.json",
        ),
        description="FlowGuard Model-Test Alignment checks for model obligations and ordinary test evidence.",
    ),
    TierCommand(
        name="flowguard_controller_break_glass",
        command=_py(
            "simulations/run_flowpilot_controller_break_glass_checks.py",
            "--json-out",
            "simulations/flowpilot_controller_break_glass_results.json",
        ),
        description="FlowGuard checks for Controller emergency break-glass eligibility and forbidden powers.",
    ),
    _pytest(
        "test_tier_runner",
        "tests/test_flowpilot_test_tiers.py",
        description="Focused tests for tier command planning and background artifact contracts.",
    ),
    _pytest(
        "model_test_alignment_tests",
        "tests/test_flowpilot_model_test_alignment.py",
        description="Focused tests for FlowGuard Model-Test Alignment evidence and known-bad cases.",
    ),
    _pytest(
        "controller_break_glass_tests",
        "tests/test_flowpilot_controller_break_glass.py",
        description="Focused tests for Controller break-glass prompt, records, and runtime reminders.",
    ),
    _pytest(
        "flowguard_proof_tests",
        "tests/test_flowguard_result_proof.py",
        description="Proof reuse checks for slow Meta/Capability parents.",
    ),
    _pytest(
        "thin_parent_tests",
        "tests/test_flowpilot_thin_parent_checks.py",
        description="Thin-parent proof and hierarchy helper tests.",
    ),
    _pytest(
        "maintenance_tool_tests",
        "tests/test_flowpilot_maintenance_tools.py",
        description="Small maintenance-tool regression tests.",
    ),
    _pytest(
        "cli_entrypoint_tests",
        "tests/test_flowpilot_cli_entrypoints.py",
        description="Fast public CLI entrypoint smoke tests.",
    ),
)

ROUTER_PARENT_COMMANDS = (
    TierCommand(
        name="router_testmesh_parent",
        command=_py(
            "simulations/run_flowpilot_test_tiering_checks.py",
            "--json-out",
            "simulations/flowpilot_test_tiering_results.json",
        ),
        description="FlowGuard TestMesh parent check for router child-suite ownership and background evidence.",
    ),
)

ROUTER_STARTUP_COMMANDS = (
    _unittest(
        "router_startup_runtime_contracts",
        "tests.test_flowpilot_router_startup_runtime",
        description="Startup runtime contract and encoding slice.",
    ),
    _unittest(
        "router_bootstrap_cli",
        "tests.router_runtime.bootstrap_cli",
        description="Startup CLI and fresh-run command slice.",
    ),
    _unittest_k(
        "router_startup_bootstrap_core",
        "tests.router_runtime.startup_bootstrap",
        patterns=(
            "run_until",
            "scheduled_startup",
            "manual_startup",
            "formal_startup",
            "deterministic",
            "startup_daemon",
            "legacy_startup_daemon",
            "router_daemon_queues_visible_startup_rows_after_internal_audit",
            "load_controller_core",
            "daemon_folds",
            "partial_startup_role",
        ),
        description="Startup bootstrap core, daemon, and receipt-owner slice.",
    ),
    _unittest_k(
        "router_startup_bootstrap_reconciliation",
        "tests.router_runtime.startup_bootstrap",
        patterns=(
            "startup_reconciliation",
            "startup_missing_router",
            "startup_obligations",
            "startup_bootloader",
            "startup_async",
            "startup_reviewer_event_uses_current_scope_reconciliation",
        ),
        description="Startup reconciliation, bootloader, and async receipt slice.",
    ),
    _unittest_k(
        "router_startup_bootstrap_intake",
        "tests.router_runtime.startup_bootstrap",
        patterns=(
            "startup_intake",
            "startup_sequence",
            "startup_waits",
            "startup_banner",
            "user_intake",
            "legacy_startup_answer",
            "new_invocation",
            "record_startup_answers",
        ),
        description="Startup intake, user answer, and banner slice.",
    ),
    _unittest_k(
        "router_startup_bootstrap_review",
        "tests.router_runtime.startup_bootstrap",
        patterns=(
            "reviewer_startup",
            "startup_pre_review",
            "pm_startup",
            "startup_activation",
            "startup_review_join",
            "pm_can_approve_startup_findings",
        ),
        description="Startup reviewer, PM activation, and repair-decision slice.",
    ),
    _unittest_k(
        "router_startup_bootstrap_fact_heartbeat",
        "tests.router_runtime.startup_bootstrap",
        patterns=(
            "startup_fact",
            "record_event_accepts_runtime_envelope_ref",
            "heartbeat_startup",
            "cockpit_requested",
        ),
        description="Startup fact-report, heartbeat, and display fallback slice.",
    ),
    _unittest(
        "router_startup_daemon",
        "tests.router_runtime.startup_daemon",
        description="Persistent startup daemon slice.",
    ),
)

ROUTER_FOREGROUND_COMMANDS = (
    _unittest(
        "router_foreground",
        "tests.router_runtime.foreground",
        description="Foreground progress and display-sync slice.",
    ),
    _unittest(
        "router_controller",
        "tests.router_runtime.controller",
        description="Controller status and passive wait slice.",
    ),
    _unittest_k(
        "router_dispatch_gate_current_node_review",
        "tests.router_runtime.dispatch_gate",
        patterns=(
            "current_node_completion_waits_for_review_created_local_obligations",
            "current_node_parallel_batch_waits_for_all_results_before_review",
            "current_node_pre_review_reconciliation_blocks_reviewer_card",
            "current_node_reviewer_pass_event_waits_for_local_reconciliation",
            "future_node_pending_return_does_not_block_current_node_review",
        ),
        description="Dispatch-gate current-node review slice.",
    ),
    _unittest_k(
        "router_dispatch_gate_recipient_policy",
        "tests.router_runtime.dispatch_gate",
        patterns=(
            "dispatch_recipient_gate_allows_pm_after_user_intake_first_output",
            "dispatch_recipient_gate_allows_same_role_system_card_bundle",
            "dispatch_recipient_gate_allows_system_card_for_active_holder",
            "dispatch_recipient_gate_blocks_busy_packet_holder",
            "dispatch_recipient_gate_blocks_followup_when_role_wait_is_active",
            "dispatch_recipient_gate_blocks_independent_pm_dispatch_while_user_intake_output_pending",
            "dispatch_recipient_gate_blocks_new_output_card_when_pm_output_pending",
            "dispatch_recipient_gate_frees_worker_after_result_but_blocks_pm_disposition",
        ),
        description="Dispatch-gate recipient policy slice.",
    ),
    _unittest_k(
        "router_dispatch_gate_user_pm_control",
        "tests.router_runtime.dispatch_gate",
        patterns=(
            "no_legal_next_action_materializes_pm_decision_control_blocker",
            "router_hard_rejection_returns_control_plane_reissue_action",
            "user_intake_mail_declares_first_pm_output_obligation",
        ),
        description="Dispatch-gate PM/user-control slice.",
    ),
    _unittest_k(
        "router_foreground_controller_core",
        "tests.router_runtime.foreground_controller",
        patterns=(
            "controller_action_summary",
            "controller_next_action",
            "controller_route_memory",
            "passive_wait_projection",
            "router_daemon_tick",
            "foreground_next_waits_on_fresh_controller_action_write_lock",
            "foreground_next_waits_on_stale_lock",
        ),
        description="Foreground controller core scheduling and lock slice.",
    ),
    _unittest_k(
        "router_foreground_controller_standby",
        "tests.router_runtime.foreground_controller",
        patterns=(
            "foreground_controller_standby_default_waits_past_timeout_until_action",
            "foreground_controller_standby_does_not_compute_router_next",
            "foreground_controller_standby_keeps_alive_when_daemon_has_no_ready_action",
            "foreground_controller_standby_materializes_report_reminder_with_liveness_probe",
            "foreground_controller_standby_requests_liveness_check_on_stale_or_missing_daemon",
            "foreground_controller_standby_returns_ack_reminder_and_blocker_due",
            "foreground_controller_standby_returns_lost_role_blocker_required",
            "foreground_controller_standby_returns_no_output_reissue_required",
            "foreground_controller_standby_self_audits_controller_local_wait",
            "foreground_controller_standby_waits_on_live_daemon_role_wait",
            "controller_patrol_timer_allows_terminal_return_only_when_stopped",
            "controller_patrol_timer_continue_patrol_restarts_and_waits",
            "controller_patrol_timer_requests_liveness_check_after_delayed_daemon_heartbeat",
        ),
        description="Foreground standby and patrol timer slice.",
    ),
    _unittest_k(
        "router_foreground_controller_receipts",
        "tests.router_runtime.foreground_controller",
        patterns=(
            "completed_pending_controller_action_receipt",
            "controller_action_ledger_handles_multiple_receipts",
            "controller_boundary_done_receipt_reclaims_router_postcondition",
            "controller_boundary_duplicate_old_receipt_does_not_block_while_second_repair_pending",
            "controller_patrol_timer_wakes_on_controller_action_ledger",
            "foreground_controller_standby_wakes_on_controller_action_ledger",
            "missing_system_card_ack_after_controller_delivery_done",
            "missing_system_card_ack_wait_confirms",
            "reconciled_controller_action_backfills_receipt_done_scheduler_row",
            "router_daemon_card_ack_reconciles",
        ),
        description="Foreground Controller receipt and scheduler reconciliation slice.",
    ),
    _unittest_k(
        "router_foreground_controller_boundary",
        "tests.router_runtime.foreground_controller",
        patterns=(
            "child_skill_gates_block_raw_inventory_and_controller_approval",
            "controller_action_reconciliation_ignores_transient_temp_files",
            "controller_boundary_confirmation_records_envelope_only_event",
            "controller_boundary_done_receipt_missing_deliverable_schedules_repair",
            "controller_boundary_handwritten_artifact_without_runtime_evidence_schedules_repair",
            "controller_boundary_projection_reclaims_stale_flags_without_pending_action",
            "controller_boundary_valid_artifact_reclaims_before_repair",
            "role_output",
            "display_plan",
            "user_intake",
        ),
        description="Foreground Controller boundary, display, and card-delivery slice.",
    ),
    _unittest_k(
        "router_foreground_controller_repair",
        "tests.router_runtime.foreground_controller",
        patterns=(
            "controller_boundary_repair_action_resolves_original",
            "controller_boundary_repair_budget_escalates_after_two_failures",
            "controller_repair_work_packet_queues_bounded_controller_action",
        ),
        description="Foreground Controller repair and confirmation slice.",
    ),
)

ROUTER_PACKET_COMMANDS = (
    _unittest(
        "router_packet_runtime",
        "tests.test_flowpilot_packet_runtime",
        description="Packet runtime contract tests.",
    ),
    _unittest_k(
        "router_packets_material",
        "tests.router_runtime.packets",
        patterns=(
            "material_work_packet",
            "material_scan_accepts",
            "record_event_accepts_material",
            "record_event_rejects_manual_material",
            "material_scan_packet_and_result_relays",
            "material_scan_packet_body_event",
            "formal_work_packet_ack",
            "mail_delivery_receipt",
        ),
        description="Router material packet, scan, and ACK preflight slice.",
    ),
    _unittest_k(
        "router_packets_current_node_direct",
        "tests.router_runtime.packets",
        patterns=(
            "current_node_direct",
            "packet_and_result_accept_safe_envelope_aliases",
        ),
        description="Current-node direct relay and alias guard slice.",
    ),
    _unittest_k(
        "router_packets_current_node_dispatch",
        "tests.router_runtime.packets",
        patterns=(
            "current_node_packet_relay",
            "current_node_worker_packet",
            "unready_leaf",
        ),
        description="Current-node packet dispatch and readiness slice.",
    ),
    _unittest_k(
        "router_packets_current_node_result_audit",
        "tests.router_runtime.packets",
        patterns=(
            "current_node_completion",
            "router_packet_audit",
        ),
        description="Current-node result audit and reviewer-pass slice.",
    ),
    _unittest_k(
        "router_packets_current_node_result_decision",
        "tests.router_runtime.packets",
        patterns=(
            "current_node_result_relay",
            "current_node_result_decision",
            "pm_repair_decision_rejects_parent",
        ),
        description="Current-node result relay, decision, and PM repair slice.",
    ),
    _unittest_k(
        "router_packets_batch_and_grants",
        "tests.router_runtime.packets",
        patterns=(
            "material_scan_existing_results",
            "material_scan_partial_batch",
            "current_node_result_requires_write_grant",
            "current_node_packet_rejects_unresolved",
        ),
        description="Packet batch reconciliation and write-grant guard slice.",
    ),
    _unittest(
        "router_cards",
        "tests.router_runtime.cards",
        description="Router runtime card slice.",
    ),
    _unittest(
        "router_ack_return",
        "tests.router_runtime.ack_return",
        description="ACK and return-event router slice.",
    ),
)

ROUTER_ROUTE_COMMANDS = (
    _unittest(
        "router_boundaries",
        "tests.test_flowpilot_router_boundaries",
        description="Router public boundary and import-contract slice.",
    ),
    _unittest(
        "router_route_mutation_draft_activation",
        "tests.router_runtime.route_mutation_draft_activation",
        description="Route-mutation draft preservation and activation guard slice.",
    ),
    _unittest(
        "router_route_mutation_model_miss_triage",
        "tests.router_runtime.route_mutation_model_miss_triage",
        description="Route-mutation reviewer-block and model-miss triage slice.",
    ),
    _unittest(
        "router_route_mutation_acceptance_repair",
        "tests.router_runtime.route_mutation_acceptance_repair",
        description="Node acceptance-plan route-repair slice.",
    ),
    _unittest(
        "router_route_mutation_preconditions",
        "tests.router_runtime.route_mutation_preconditions",
        description="Route-mutation precondition and final-ledger guard slice.",
    ),
    _unittest(
        "router_route_mutation_transactions",
        "tests.router_runtime.route_mutation_transactions",
        description="Route-mutation repeated repair transaction slice.",
    ),
    _unittest(
        "router_route_mutation_topology",
        "tests.router_runtime.route_mutation_topology",
        description="Route-mutation topology strategy slice.",
    ),
    _unittest(
        "router_route_mutation_sibling_replacement",
        "tests.router_runtime.route_mutation_sibling_replacement",
        description="Route-mutation sibling replacement and stale-proof slice.",
    ),
    _unittest(
        "router_route_mutation_parent_backward",
        "tests.router_runtime.route_mutation_parent_backward",
        description="Route-mutation parent backward replay and repair slice.",
    ),
    _unittest(
        "router_route_mutation_contracts",
        "tests.test_flowpilot_router_runtime_route_mutation",
        description="Route-mutation contract tests.",
    ),
    _unittest(
        "router_user_flow_diagram",
        "tests.test_flowpilot_user_flow_diagram",
        description="User-flow diagram route display tests.",
    ),
)

ROUTER_TERMINAL_COMMANDS = (
    _unittest(
        "router_terminal",
        "tests.router_runtime.terminal",
        description="Terminal lifecycle router slice.",
    ),
    _unittest(
        "router_closure",
        "tests.router_runtime.closure",
        description="Terminal closure ledger router slice.",
    ),
    _unittest(
        "router_resume",
        "tests.router_runtime.resume",
        description="Resume and role-recovery router slice.",
    ),
    _unittest(
        "router_control_blockers",
        "tests.router_runtime.control_blockers",
        description="Control-blocker repair router slice.",
    ),
    _unittest(
        "router_pm_role_work",
        "tests.router_runtime.pm_role_work",
        description="PM role-work router slice.",
    ),
    _unittest(
        "router_quality_gates",
        "tests.router_runtime.quality_gates",
        description="Quality gate router slice.",
    ),
    _unittest(
        "router_material_modeling",
        "tests.router_runtime.material_modeling",
        description="Material intake and modeling router slice.",
    ),
)

INTEGRATION_COMMANDS = (
    TierCommand(
        name="check_install",
        command=_py("scripts/check_install.py", "--json"),
        description="Repository install contract check.",
    ),
    TierCommand(
        name="audit_local_install_sync",
        command=_py("scripts/audit_local_install_sync.py", "--json"),
        description="Local installed-skill freshness and source sync audit.",
    ),
    TierCommand(
        name="smoke_autopilot_fast",
        command=_py("scripts/smoke_autopilot.py", "--fast"),
        description="Smoke checks with reusable thin-parent slow-model proofs.",
        long_running=True,
        background_recommended=True,
    ),
    TierCommand(
        name="flowguard_coverage_sweep",
        command=_py("scripts/run_flowguard_coverage_sweep.py", "--timeout-seconds", "30"),
        description="Read-only FlowGuard coverage sweep.",
        long_running=True,
        background_recommended=True,
    ),
)

RELEASE_COMMANDS = (
    TierCommand(
        name="release_tooling",
        command=_py("simulations/run_release_tooling_checks.py"),
        description="Release-tooling FlowGuard checks.",
    ),
    TierCommand(
        name="meta_full",
        command=_py("simulations/run_meta_checks.py", "--full"),
        description="Layered full Meta parent regression.",
        release_only=True,
        long_running=True,
        background_recommended=True,
    ),
    TierCommand(
        name="capability_full",
        command=_py("simulations/run_capability_checks.py", "--full"),
        description="Layered full Capability parent regression.",
        release_only=True,
        long_running=True,
        background_recommended=True,
    ),
    TierCommand(
        name="public_release_check",
        command=_py("scripts/check_public_release.py", "--json", "--skip-url-check"),
        description="Public release boundary validation without URL probing.",
        release_only=True,
        long_running=True,
        background_recommended=True,
        background_stage=1,
    ),
)

LEGACY_FULL_COMMANDS = (
    TierCommand(
        name="meta_legacy_full",
        command=_py("simulations/run_meta_checks.py", "--legacy-full"),
        description="Legacy full Meta graph regression.",
        release_only=True,
        long_running=True,
        background_recommended=True,
    ),
    TierCommand(
        name="capability_legacy_full",
        command=_py("simulations/run_capability_checks.py", "--legacy-full"),
        description="Legacy full Capability graph regression.",
        release_only=True,
        long_running=True,
        background_recommended=True,
    ),
)


def commands_for_tier(tier: str) -> tuple[TierCommand, ...]:
    mapping: dict[str, tuple[TierCommand, ...]] = {
        "collect": (
            TierCommand(
                name="pytest_collect_tests",
                command=_py("-m", "pytest", "tests", "--collect-only", "-q"),
                description="Collect only from the real tests/ tree.",
            ),
        ),
        "fast": FAST_COMMANDS,
        "router-startup": ROUTER_STARTUP_COMMANDS,
        "router-foreground": ROUTER_FOREGROUND_COMMANDS,
        "router-packets": ROUTER_PACKET_COMMANDS,
        "router-route": ROUTER_ROUTE_COMMANDS,
        "router-terminal": ROUTER_TERMINAL_COMMANDS,
        "integration": INTEGRATION_COMMANDS,
        "release": RELEASE_COMMANDS,
        "legacy-full": LEGACY_FULL_COMMANDS,
    }
    if tier == "router":
        return (
            *ROUTER_PARENT_COMMANDS,
            *ROUTER_STARTUP_COMMANDS,
            *ROUTER_FOREGROUND_COMMANDS,
            *ROUTER_PACKET_COMMANDS,
            *ROUTER_ROUTE_COMMANDS,
            *ROUTER_TERMINAL_COMMANDS,
        )
    if tier == "all":
        return (
            *mapping["collect"],
            *FAST_COMMANDS,
            *commands_for_tier("router"),
            *INTEGRATION_COMMANDS,
        )
    return mapping[tier]


def tier_names() -> tuple[str, ...]:
    return (
        "collect",
        "fast",
        "router-startup",
        "router-foreground",
        "router-packets",
        "router-route",
        "router-terminal",
        "router",
        "integration",
        "release",
        "legacy-full",
        "all",
    )


def _safe_base(name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("._")
    return safe or "test_tier_command"


def artifact_paths(log_root: Path, name: str) -> dict[str, Path]:
    base = _safe_base(name)
    return {suffix: log_root / f"{base}.{suffix}.txt" for suffix in ARTIFACT_SUFFIXES if suffix != "meta"} | {
        "meta": log_root / f"{base}.meta.json"
    }


def clear_artifacts(paths: dict[str, Path]) -> None:
    for path in paths.values():
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        except PermissionError as exc:
            raise RuntimeError(
                f"background artifact is still locked by an active process: {path}"
            ) from exc


def background_supervisor_name(tier: str) -> str:
    return f"{tier}_background_supervisor"


def should_use_background_supervisor(command_count: int, max_parallel: int) -> bool:
    return max_parallel > 0 and command_count > max_parallel


def _artifact_paths_for_json(log_root: Path, name: str) -> dict[str, str]:
    return {
        key: str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)
        for key, path in artifact_paths(log_root, name).items()
    }


def command_to_json(command: TierCommand, *, background_dir: Path) -> dict[str, Any]:
    return {
        "name": command.name,
        "command": list(command.command),
        "description": command.description,
        "long_running": command.long_running,
        "release_only": command.release_only,
        "background_recommended": command.background_recommended,
        "background_stage": command.background_stage,
        "background_artifacts": _artifact_paths_for_json(background_dir, command.name),
    }


def plan_for_tier(tier: str, *, background_dir: Path) -> dict[str, Any]:
    commands = commands_for_tier(tier)
    return {
        "tier": tier,
        "command_count": len(commands),
        "commands": [command_to_json(command, background_dir=background_dir) for command in commands],
        "background_dir": str(
            background_dir.relative_to(ROOT) if background_dir.is_relative_to(ROOT) else background_dir
        ),
        "background_contract": [f"<name>.{suffix}.txt" for suffix in ARTIFACT_SUFFIXES if suffix != "meta"]
        + ["<name>.meta.json"],
        "release_obligation_visible": tier not in {"release", "legacy-full"},
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: MappingLike) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


MappingLike = dict[str, Any]


def _windows_hidden_process_flags() -> int:
    if os.name != "nt":
        return 0
    return (
        getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    )


def _windows_hidden_startupinfo() -> Any | None:
    if os.name != "nt":
        return None
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    return startupinfo


def _hidden_process_kwargs() -> dict[str, Any]:
    if os.name != "nt":
        return {}
    return {
        "creationflags": _windows_hidden_process_flags(),
        "startupinfo": _windows_hidden_startupinfo(),
    }


def _launch_background(command: TierCommand, *, log_root: Path) -> dict[str, Any]:
    log_root.mkdir(parents=True, exist_ok=True)
    paths = artifact_paths(log_root, command.name)
    clear_artifacts(paths)
    meta = {
        "name": command.name,
        "command": list(command.command),
        "cwd": str(ROOT),
        "status": "launching",
        "start_time": _utc_now(),
        "end_time": None,
        "exit_code": None,
        "proof_reused": None,
        "artifacts": {key: str(value) for key, value in paths.items()},
    }
    _write_json(paths["meta"], meta)
    child_args = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--background-child",
        "--name",
        command.name,
        "--command-json",
        json.dumps(list(command.command)),
        "--background-dir",
        str(log_root),
    ]
    proc = subprocess.Popen(
        child_args,
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        **_hidden_process_kwargs(),
    )
    meta["status"] = "running"
    meta["launcher_pid"] = os.getpid()
    meta["child_pid"] = proc.pid
    _write_json(paths["meta"], meta)
    return {
        "name": command.name,
        "status": "running",
        "child_pid": proc.pid,
        "artifacts": {key: str(value) for key, value in paths.items()},
    }


def launch_background(commands: Iterable[TierCommand], *, log_root: Path) -> list[dict[str, Any]]:
    return [_launch_background(command, log_root=log_root) for command in commands]


def _read_exit_code(path: Path) -> int | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return 1


def _read_background_meta(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing_meta"
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"invalid_meta:{type(exc).__name__}"
    if not isinstance(payload, dict):
        return None, "invalid_meta:not_object"
    return payload, None


def _artifact_has_progress(paths: MappingLike) -> bool:
    for key in ("out", "err", "combined"):
        path = paths.get(key)
        if not isinstance(path, Path) or not path.exists():
            continue
        try:
            if path.read_text(encoding="utf-8", errors="replace").strip():
                return True
        except OSError:
            continue
    return False


def _release_local_only_proof(
    *,
    command: TierCommand | None,
    tier: str,
    meta: MappingLike | None,
) -> bool:
    command_parts: list[str] = []
    if command is not None:
        command_parts.extend(command.command)
    if isinstance(meta, dict):
        meta_command = meta.get("command")
        if isinstance(meta_command, list):
            command_parts.extend(str(part) for part in meta_command)
        if meta.get("proof_scope") == "local_only" or meta.get("local_only") is True:
            return True
    command_text = " ".join(command_parts)
    return bool(
        "--skip-url-check" in command_parts
        or "--skip-url-check" in command_text
    )


def classify_background_artifact(
    log_root: Path,
    name: str,
    *,
    command: TierCommand | None = None,
    tier: str = "",
) -> dict[str, Any]:
    paths = artifact_paths(log_root, name)
    meta, meta_error = _read_background_meta(paths["meta"])
    exit_code = _read_exit_code(paths["exit"])
    progress_seen = _artifact_has_progress(paths)
    reasons: list[str] = []
    raw_status = str((meta or {}).get("status") or "")

    if meta_error:
        reasons.append(meta_error)
    if exit_code is None:
        reasons.append("missing_exit")

    if meta is not None and raw_status == "running" and exit_code is None:
        status = "running"
    elif exit_code is None and progress_seen:
        status = "progress_only"
    elif exit_code is None:
        status = "incomplete"
    elif meta is not None and raw_status == "running":
        status = "stale"
        reasons.append("running_meta_with_exit_artifact")
    elif exit_code != 0 or raw_status == "failed":
        status = "failed"
    elif meta is None:
        status = "incomplete"
    elif raw_status in {"passed", "pass"}:
        status = "passed"
    else:
        status = "incomplete"
        reasons.append(f"unexpected_meta_status:{raw_status or 'missing'}")

    local_only = _release_local_only_proof(command=command, tier=tier, meta=meta)
    if status == "passed" and local_only:
        status = "release_local_only"
        reasons.append("release_url_check_skipped_or_release_only_tier")

    return {
        "name": name,
        "status": status,
        "execution_status": "passed" if status in {"passed", "release_local_only"} else status,
        "ok": status in {"passed", "release_local_only"},
        "exit_code": exit_code,
        "meta_status": raw_status or None,
        "progress_seen": progress_seen,
        "proof_scope": "local_only" if local_only else "full",
        "reasons": reasons,
        "artifacts": {key: str(path) for key, path in paths.items()},
    }


def next_background_launch_index(
    pending: Sequence[TierCommand],
    running: Sequence[TierCommand],
) -> int | None:
    if not pending:
        return None
    if running:
        active_stage = min(command.background_stage for command in running)
    else:
        active_stage = min(command.background_stage for command in pending)
    for index, command in enumerate(pending):
        if command.background_stage == active_stage:
            return index
    return None


def _launch_background_supervisor(tier: str, *, log_root: Path, max_parallel: int) -> dict[str, Any]:
    log_root.mkdir(parents=True, exist_ok=True)
    name = background_supervisor_name(tier)
    paths = artifact_paths(log_root, name)
    clear_artifacts(paths)
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--background-supervisor",
        "--tier",
        tier,
        "--background-dir",
        str(log_root),
        "--background-max-parallel",
        str(max_parallel),
    ]
    meta = {
        "name": name,
        "tier": tier,
        "command": command,
        "cwd": str(ROOT),
        "status": "launching",
        "start_time": _utc_now(),
        "end_time": None,
        "exit_code": None,
        "proof_reused": None,
        "max_parallel": max_parallel,
        "artifacts": {key: str(value) for key, value in paths.items()},
    }
    _write_json(paths["meta"], meta)
    proc = subprocess.Popen(
        command,
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        **_hidden_process_kwargs(),
    )
    meta["status"] = "running"
    meta["launcher_pid"] = os.getpid()
    meta["child_pid"] = proc.pid
    _write_json(paths["meta"], meta)
    return {
        "name": name,
        "status": "running",
        "child_pid": proc.pid,
        "artifacts": {key: str(value) for key, value in paths.items()},
    }


def run_background_supervisor(
    tier: str,
    commands: Sequence[TierCommand],
    *,
    log_root: Path,
    max_parallel: int,
) -> int:
    name = background_supervisor_name(tier)
    paths = artifact_paths(log_root, name)
    log_root.mkdir(parents=True, exist_ok=True)
    meta: dict[str, Any] = {
        "name": name,
        "tier": tier,
        "cwd": str(ROOT),
        "status": "running",
        "start_time": _utc_now(),
        "end_time": None,
        "exit_code": None,
        "proof_reused": False,
        "max_parallel": max_parallel,
        "command_count": len(commands),
        "running": [],
        "completed": [],
        "artifacts": {key: str(value) for key, value in paths.items()},
    }
    _write_json(paths["meta"], meta)

    pending = list(commands)
    running: list[TierCommand] = []
    completed: list[dict[str, Any]] = []

    try:
        with paths["out"].open("w", encoding="utf-8", errors="replace") as out_file, paths["err"].open(
            "w", encoding="utf-8", errors="replace"
        ) as err_file, paths["combined"].open("w", encoding="utf-8", errors="replace") as combined_file:
            while pending or running:
                while pending and len(running) < max_parallel:
                    launch_index = next_background_launch_index(pending, running)
                    if launch_index is None:
                        break
                    command = pending.pop(launch_index)
                    launched = _launch_background(command, log_root=log_root)
                    running.append(command)
                    line = f"launched {command.name} pid={launched['child_pid']}\n"
                    out_file.write(line)
                    out_file.flush()
                    combined_file.write(f"[supervisor] {line}")
                    combined_file.flush()

                still_running: list[TierCommand] = []
                for command in running:
                    exit_path = artifact_paths(log_root, command.name)["exit"]
                    exit_code = _read_exit_code(exit_path)
                    if exit_code is None:
                        still_running.append(command)
                        continue
                    evidence = classify_background_artifact(
                        log_root,
                        command.name,
                        command=command,
                        tier=tier,
                    )
                    result = {
                        "name": command.name,
                        "exit_code": exit_code,
                        "ok": bool(evidence["ok"]),
                        "evidence_status": evidence["status"],
                        "proof_scope": evidence["proof_scope"],
                        "reasons": evidence["reasons"],
                    }
                    completed.append(result)
                    line = f"completed {command.name} exit={exit_code} evidence={evidence['status']}\n"
                    out_file.write(line)
                    out_file.flush()
                    combined_file.write(f"[supervisor] {line}")
                    combined_file.flush()
                    if not result["ok"]:
                        err_file.write(line)
                        err_file.flush()
                running = still_running

                meta["running"] = [command.name for command in running]
                meta["completed"] = completed
                _write_json(paths["meta"], meta)
                if pending or running:
                    time.sleep(BACKGROUND_SUPERVISOR_POLL_SECONDS)
    except Exception as exc:
        details = traceback.format_exc()
        paths["err"].write_text(details, encoding="utf-8", errors="replace")
        paths["combined"].write_text(f"[supervisor-error] {details}", encoding="utf-8", errors="replace")
        paths["exit"].write_text("1\n", encoding="utf-8")
        meta["status"] = "failed"
        meta["end_time"] = _utc_now()
        meta["exit_code"] = 1
        meta["error"] = str(exc)
        meta["running"] = [command.name for command in running]
        meta["completed"] = completed
        _write_json(paths["meta"], meta)
        return 1

    ok = all(item["ok"] for item in completed) and len(completed) == len(commands)
    exit_code = 0 if ok else 1
    paths["exit"].write_text(f"{exit_code}\n", encoding="utf-8")
    meta["status"] = "passed" if ok else "failed"
    meta["end_time"] = _utc_now()
    meta["exit_code"] = exit_code
    meta["completed"] = completed
    meta["running"] = []
    _write_json(paths["meta"], meta)
    return exit_code


def _stream_pipe(
    pipe: Any,
    stream_name: str,
    target: Any,
    combined: Any,
    lock: threading.Lock,
    flags: dict[str, bool],
) -> None:
    for line in iter(pipe.readline, ""):
        target.write(line)
        target.flush()
        if "proof_reused" in line or "proof reused" in line.lower():
            flags["proof_reused"] = True
        with lock:
            combined.write(f"[{stream_name}] {line}")
            combined.flush()
    pipe.close()


def run_background_child(name: str, command: Sequence[str], *, log_root: Path) -> int:
    paths = artifact_paths(log_root, name)
    log_root.mkdir(parents=True, exist_ok=True)
    meta = {
        "name": name,
        "command": list(command),
        "cwd": str(ROOT),
        "status": "running",
        "start_time": _utc_now(),
        "end_time": None,
        "exit_code": None,
        "proof_reused": False,
        "artifacts": {key: str(value) for key, value in paths.items()},
    }
    _write_json(paths["meta"], meta)
    flags = {"proof_reused": False}
    try:
        with paths["out"].open("w", encoding="utf-8", errors="replace") as out_file, paths[
            "err"
        ].open("w", encoding="utf-8", errors="replace") as err_file, paths["combined"].open(
            "w", encoding="utf-8", errors="replace"
        ) as combined_file:
            process = subprocess.Popen(
                list(command),
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                **_hidden_process_kwargs(),
            )
            assert process.stdout is not None
            assert process.stderr is not None
            lock = threading.Lock()
            out_thread = threading.Thread(
                target=_stream_pipe,
                args=(process.stdout, "stdout", out_file, combined_file, lock, flags),
                daemon=True,
            )
            err_thread = threading.Thread(
                target=_stream_pipe,
                args=(process.stderr, "stderr", err_file, combined_file, lock, flags),
                daemon=True,
            )
            out_thread.start()
            err_thread.start()
            returncode = process.wait()
            out_thread.join()
            err_thread.join()
    except Exception as exc:  # pragma: no cover - defensive background reporting
        paths["err"].write_text(f"background child failed before command exit: {exc}\n", encoding="utf-8")
        paths["combined"].write_text(
            f"[runner] background child failed before command exit: {exc}\n",
            encoding="utf-8",
        )
        returncode = 1

    paths["exit"].write_text(f"{returncode}\n", encoding="utf-8")
    meta["status"] = "passed" if returncode == 0 else "failed"
    meta["end_time"] = _utc_now()
    meta["exit_code"] = returncode
    meta["proof_reused"] = flags["proof_reused"]
    _write_json(paths["meta"], meta)
    return returncode


def run_foreground(commands: Iterable[TierCommand]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for command in commands:
        completed = subprocess.run(
            list(command.command),
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **_hidden_process_kwargs(),
        )
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)
        results.append(
            {
                "name": command.name,
                "command": list(command.command),
                "returncode": completed.returncode,
                "ok": completed.returncode == 0,
            }
        )
    return results


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", choices=tier_names(), default="fast")
    parser.add_argument("--dry-run", action="store_true", help="Plan commands without executing.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--background", action="store_true", help="Launch commands as detached jobs.")
    parser.add_argument("--background-dir", type=Path, default=DEFAULT_BACKGROUND_DIR)
    parser.add_argument(
        "--background-max-parallel",
        type=int,
        default=DEFAULT_BACKGROUND_MAX_PARALLEL,
        help="Maximum command runners started concurrently by the background supervisor.",
    )
    parser.add_argument("--list-tiers", action="store_true")
    parser.add_argument("--background-child", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--background-supervisor", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--name", default="", help=argparse.SUPPRESS)
    parser.add_argument("--command-json", default="", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.background_child:
        command = json.loads(args.command_json)
        if not isinstance(command, list) or not args.name:
            raise SystemExit("background child requires --name and command list")
        return run_background_child(args.name, [str(part) for part in command], log_root=args.background_dir)

    if args.background_supervisor:
        commands = commands_for_tier(args.tier)
        max_parallel = max(1, args.background_max_parallel)
        return run_background_supervisor(
            args.tier,
            commands,
            log_root=args.background_dir,
            max_parallel=max_parallel,
        )

    if args.list_tiers:
        payload = {"tiers": list(tier_names())}
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            for tier in tier_names():
                print(tier)
        return 0

    commands = commands_for_tier(args.tier)
    plan = plan_for_tier(args.tier, background_dir=args.background_dir)
    if args.dry_run:
        if args.json:
            print(json.dumps(plan, indent=2, sort_keys=True))
        else:
            for command in plan["commands"]:
                print(" ".join(command["command"]))
        return 0

    if args.background:
        max_parallel = max(1, args.background_max_parallel)
        if should_use_background_supervisor(len(commands), max_parallel):
            launched = [_launch_background_supervisor(args.tier, log_root=args.background_dir, max_parallel=max_parallel)]
            supervisor = launched[0]
        else:
            launched = launch_background(commands, log_root=args.background_dir)
            supervisor = None
        payload = {
            "ok": True,
            "tier": args.tier,
            "background_max_parallel": max_parallel,
            "launched": launched,
            "plan": plan,
            "supervisor": supervisor,
        }
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"Launched {len(launched)} background test command(s) under {args.background_dir}")
            for item in launched:
                print(f"- {item['name']}: pid={item['child_pid']}")
        return 0

    results = run_foreground(commands)
    ok = all(item["ok"] for item in results)
    payload = {"ok": ok, "tier": args.tier, "results": results, "plan": plan}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
