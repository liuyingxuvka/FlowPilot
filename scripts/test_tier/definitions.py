"""Tier command definitions for scripts.run_test_tier."""

from __future__ import annotations

from .command_builders import TierCommand, _py
from .fast_commands import FAST_COMMANDS, ROUTER_PARENT_COMMANDS
from .final_confidence_commands import FINAL_CONFIDENCE_COMMANDS
from .integration_commands import (
    EVIDENCE_CLOSURE_COMMANDS,
    INTEGRATION_COMMANDS,
    RELEASE_COMMANDS,
)
from .mta_evidence_commands import mta_evidence_commands
from .router_packet_route_commands import ROUTER_PACKET_COMMANDS, ROUTER_ROUTE_COMMANDS
from .router_startup_foreground_commands import ROUTER_FOREGROUND_COMMANDS, ROUTER_STARTUP_COMMANDS
from .router_terminal_commands import (
    ROUTER_PM_ROLE_WORK_COMMANDS,
    ROUTER_QUALITY_GATE_COMMANDS,
    ROUTER_TERMINAL_COMMANDS,
)


ALL_INTEGRATION_COMMANDS = tuple(
    command
    for command in INTEGRATION_COMMANDS
    if command.name != "refresh_flowguard_project_topology"
)


FORMAL_SUBMIT_FAST_COMMANDS = (
    TierCommand(
        name="complete_workstream_fake_ai_tests",
        command=_py("-m", "pytest", "tests/test_flowpilot_complete_workstream_fake_ai.py", "-q"),
        description="All declared workstream and resource profiles traverse the current public ACK/open/submit/review/repair path.",
        background_recommended=True,
    ),
    TierCommand(
        name="formal_ai_submit_fast_runner",
        command=_py(
            "simulations/run_flowpilot_ai_response_execution_closure_checks.py",
            "--mode",
            "fast",
            "--budget-seconds",
            "240",
            "--json-out",
            "tmp/test_results/formal_ai_submit_fast.json",
        ),
        description="Execution-backed pairwise formal AI result submission closure.",
        background_recommended=True,
    ),
    TierCommand(
        name="formal_ai_submit_fast_tests",
        command=_py("-m", "pytest", "tests/test_flowpilot_formal_ai_contract_execution.py", "-q"),
        description="Finite contract enumeration and real fast submit receipts.",
        background_recommended=True,
    ),
)


FORMAL_SUBMIT_ADVERSARIAL_COMMANDS = (
    TierCommand(
        name="complete_workstream_fake_ai_execution_receipts",
        command=_py(
            "simulations/run_flowpilot_complete_workstream_fake_ai_checks.py",
            "--json-out",
            "simulations/flowpilot_complete_workstream_fake_ai_results.json",
        ),
        description="Execution-backed finite profile receipts with declared/selected/executed/passed/failed/stale/not-run accounting.",
        long_running=True,
        release_only=True,
        background_recommended=True,
    ),
    TierCommand(
        name="formal_ai_submit_adversarial_runner",
        command=_py(
            "simulations/run_flowpilot_ai_response_execution_closure_checks.py",
            "--mode",
            "adversarial",
            "--budget-seconds",
            "3600",
            "--json-out",
            "tmp/test_results/formal_ai_submit_adversarial.json",
        ),
        description="Execution-backed pairwise, risk-mandatory, and critical three-way submit closure.",
        long_running=True,
        release_only=True,
        background_recommended=True,
    ),
    TierCommand(
        name="formal_ai_submit_adversarial_tests",
        command=_py("-m", "pytest", "tests/test_flowpilot_ai_response_execution_closure.py", "-q"),
        description="Adversarial execution receipts and false-green FlowGuard hazards.",
        long_running=True,
        release_only=True,
        background_recommended=True,
    ),
    TierCommand(
        name="formal_ai_submit_historical_regressions",
        command=_py(
            "-m",
            "pytest",
            "tests/test_flowpilot_historical_live_run_replay.py::FlowPilotHistoricalLiveRunReplayTests::test_run_20260707_databank_control_plane_miss_fixture_is_rejected",
            "tests/test_flowpilot_new_entrypoint.py::FlowPilotNewEntrypointTests::test_open_packet_submission_checklist_rejects_packet_body_as_contract_authority",
            "tests/test_flowpilot_contract_driven_fake_ai_open_packet.py::ContractDrivenFakeAIOpenPacketTests::test_reviewer_consumes_delivered_rule_without_static_flow_lookup",
            "tests/test_flowpilot_current_contract_cartesian_matrix.py::FlowPilotCurrentContractCartesianMatrixTests::test_daemon_replay_is_historical_negative_only",
            "-q",
        ),
        description="Pinned historical DataBank, checklist-authority, Reviewer-policy, and daemon-replay regressions.",
        long_running=True,
        release_only=True,
        background_recommended=True,
    ),
    TierCommand(
        name="fake_ai_runtime_replay_full",
        command=_py(
            "simulations/run_flowpilot_fake_ai_runtime_replay_checks.py",
            "--json-out",
            "simulations/flowpilot_fake_ai_runtime_replay_summary.json",
        ),
        description="Complete fake-AI runtime replay with explicit known-bad rejection evidence.",
        long_running=True,
        release_only=True,
        background_recommended=True,
    ),
    TierCommand(
        name="current_contract_cartesian_declaration",
        command=_py(
            "simulations/run_flowpilot_current_contract_cartesian_matrix_checks.py",
            "--declaration-only",
            "--json-out",
            "tmp/test_results/current_contract_cartesian_declaration.json",
        ),
        description=(
            "Declaration-only current-contract Cartesian registry and source-purity "
            "inventory used before the bootstrap proof manifest exists."
        ),
        long_running=True,
        release_only=True,
        background_recommended=True,
    ),
)


FORMAL_TIER_CONTRACTS = {
    "formal-submit-fast": {
        "budget_seconds": 240,
        "hidden_skip_allowed": False,
        "required_final_artifact_suffixes": ("out", "err", "combined", "exit", "meta"),
        "recommended_windows_parallel_workers": 2,
        "failure_policy": "any_failed_timeout_incomplete_or_progress_only_child_blocks_parent",
    },
    "formal-submit-adversarial": {
        "budget_seconds": 3600,
        "hidden_skip_allowed": False,
        "required_final_artifact_suffixes": ("out", "err", "combined", "exit", "meta"),
        "recommended_windows_parallel_workers": 2,
        "failure_policy": "any_failed_timeout_incomplete_or_progress_only_child_blocks_parent",
    },
}


def formal_tier_contract(tier: str) -> dict[str, object]:
    return dict(FORMAL_TIER_CONTRACTS[tier])

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
        "router-pm-role-work": ROUTER_PM_ROLE_WORK_COMMANDS,
        "router-quality-gates": ROUTER_QUALITY_GATE_COMMANDS,
        "router-terminal": ROUTER_TERMINAL_COMMANDS,
        "integration": INTEGRATION_COMMANDS,
        "release": RELEASE_COMMANDS,
        "evidence-closure": EVIDENCE_CLOSURE_COMMANDS,
        "final-confidence": FINAL_CONFIDENCE_COMMANDS,
        "formal-submit-fast": FORMAL_SUBMIT_FAST_COMMANDS,
        "formal-submit-adversarial": FORMAL_SUBMIT_ADVERSARIAL_COMMANDS,
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
        base_commands = (
            *mapping["collect"],
            *FAST_COMMANDS,
            *FORMAL_SUBMIT_FAST_COMMANDS,
            *commands_for_tier("router"),
            # FAST_COMMANDS already owns the sole all-tier topology build.
            # Reusing the integration refresh here would create a second
            # writer for the same generated topology artifacts.
            *ALL_INTEGRATION_COMMANDS,
        )
        return (
            *base_commands,
            *mta_evidence_commands(base_commands),
        )
    if tier == "release":
        return mapping["release"]
    return mapping[tier]


def tier_names() -> tuple[str, ...]:
    return (
        "collect",
        "fast",
        "router-startup",
        "router-foreground",
        "router-packets",
        "router-route",
        "router-pm-role-work",
        "router-quality-gates",
        "router-terminal",
        "router",
        "integration",
        "release",
        "evidence-closure",
        "final-confidence",
        "formal-submit-fast",
        "formal-submit-adversarial",
        "all",
    )
