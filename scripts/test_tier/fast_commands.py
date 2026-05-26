"""Fast and parent FlowPilot test-tier commands."""

from __future__ import annotations

from .command_builders import TierCommand, _py, _pytest

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
        name="synthetic_agent_coverage_matrix",
        command=_py(
            "simulations/flowpilot_synthetic_agent_coverage_matrix.py",
            "--json-out",
            "simulations/flowpilot_synthetic_agent_coverage_matrix_results.json",
        ),
        description="Coverage matrix gate for synthetic AI traces, ordinary branch evidence, and full diagnostic blockers.",
    ),
    TierCommand(
        name="hard_gate_red_team_matrix",
        command=_py(
            "simulations/flowpilot_hard_gate_red_team_matrix.py",
            "--json-out",
            "simulations/flowpilot_hard_gate_red_team_matrix_results.json",
        ),
        description="Hard-gate red-team matrix for fake AI packages, state invariants, and recovery routes.",
    ),
    TierCommand(
        name="e2e_synthetic_chaos_matrix",
        command=_py(
            "simulations/flowpilot_e2e_synthetic_chaos_matrix.py",
            "--json-out",
            "simulations/flowpilot_e2e_synthetic_chaos_matrix_results.json",
        ),
        description="End-to-end synthetic chaos matrix for daemon-driven fake AI full-flow replays.",
    ),
    TierCommand(
        name="real_router_dry_run_rehearsal_matrix",
        command=_py(
            "simulations/flowpilot_real_router_dry_run_rehearsal_matrix.py",
            "--json-out",
            "simulations/flowpilot_real_router_dry_run_rehearsal_matrix_results.json",
        ),
        description="Real Router dry-run rehearsal matrix for prepared fake AI packages through public runtime boundaries.",
    ),
    TierCommand(
        name="control_plane_failure_canary_matrix",
        command=_py(
            "simulations/flowpilot_control_plane_failure_canary_matrix.py",
            "--json-out",
            "simulations/flowpilot_control_plane_failure_canary_matrix_results.json",
        ),
        description="Control-plane canary matrix for locks, daemon liveness, resume, authority, fences, and proof artifacts.",
    ),
    TierCommand(
        name="shadow_launcher_chaos_matrix",
        command=_py(
            "simulations/flowpilot_shadow_launcher_chaos_matrix.py",
            "--json-out",
            "simulations/flowpilot_shadow_launcher_chaos_matrix_results.json",
        ),
        description="Shadow launcher chaos matrix for installed launcher, recovery, peer conflict, migration, bad packages, and bounded soak.",
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
        "synthetic_agent_trace_replay_tests",
        "tests/test_flowpilot_synthetic_agent_trace_replay.py",
        description="Synthetic agent trace replay tests for fake role actions through real packet/runtime APIs.",
    ),
    _pytest(
        "hard_gate_red_team_matrix_tests",
        "tests/test_flowpilot_hard_gate_red_team_matrix.py",
        description="Focused tests for hard-gate red-team coverage rows and known-bad matrix rejection.",
    ),
    _pytest(
        "hard_gate_red_team_replay_tests",
        "tests/test_flowpilot_hard_gate_red_team_replay.py",
        description="Runtime red-team replays for fake AI packages rejected without protected state mutation.",
    ),
    _pytest(
        "e2e_synthetic_chaos_matrix_tests",
        "tests/test_flowpilot_e2e_synthetic_chaos_matrix.py",
        description="Focused tests for full-flow synthetic chaos coverage rows and known-bad matrix rejection.",
    ),
    _pytest(
        "e2e_synthetic_chaos_replay_tests",
        "tests/test_flowpilot_e2e_synthetic_chaos_replay.py",
        description="End-to-end fake AI replays across Router daemon, recovery, proof, isolation, and closure gates.",
    ),
    _pytest(
        "real_router_dry_run_rehearsal_matrix_tests",
        "tests/test_flowpilot_real_router_dry_run_rehearsal_matrix.py",
        description="Focused tests for real Router rehearsal rows and known-bad overclaim rejection.",
    ),
    _pytest(
        "real_router_dry_run_rehearsal_tests",
        "tests/test_flowpilot_real_router_dry_run_rehearsal.py",
        description="Runtime rehearsals for prepared fake AI packages through real Router, CLI, recovery, proof, and terminal gates.",
    ),
    _pytest(
        "control_plane_failure_canary_matrix_tests",
        "tests/test_flowpilot_control_plane_failure_canary_matrix.py",
        description="Focused tests for bounded control-plane failure canary rows and known-bad rejection.",
    ),
    _pytest(
        "control_plane_failure_canary_replay_tests",
        "tests/test_flowpilot_control_plane_failure_canary_replay.py",
        description="Runtime control-plane canaries for locks, daemon liveness, duplicate resume, peer stops, fences, and proof gates.",
    ),
    _pytest(
        "shadow_launcher_chaos_matrix_tests",
        "tests/test_flowpilot_shadow_launcher_chaos_matrix.py",
        description="Focused tests for installed-launcher shadow chaos rows and known-bad matrix rejection.",
    ),
    _pytest(
        "shadow_launcher_chaos_replay_tests",
        "tests/test_flowpilot_shadow_launcher_chaos_replay.py",
        description="Runtime shadow chaos replays through installed launcher copy, real Router, daemon recovery, peer isolation, malformed packages, and cleanup loops.",
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
