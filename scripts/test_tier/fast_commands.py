"""Fast and parent FlowPilot test-tier commands."""

from __future__ import annotations

from .command_builders import TierCommand, _py, _pytest, _pytest_k

SYNTHETIC_AGENT_TRACE_REPLAY_PATH = "tests/test_flowpilot_synthetic_agent_trace_replay.py"
E2E_SYNTHETIC_CHAOS_REPLAY_PATH = "tests/test_flowpilot_e2e_synthetic_chaos_replay.py"
SHADOW_LAUNCHER_CHAOS_REPLAY_PATH = "tests/test_flowpilot_shadow_launcher_chaos_replay.py"

SYNTHETIC_AGENT_TRACE_REPAIR_SHARDS = (
    _pytest_k(
        "synthetic_agent_trace_reissue_retry_tests",
        SYNTHETIC_AGENT_TRACE_REPLAY_PATH,
        "test_control_blocker_reissue_retry_budget_escalates_to_pm_fake_reviewer_package",
        description="Single-scenario synthetic trace shard for reissue retry escalation.",
    ),
    _pytest_k(
        "synthetic_agent_trace_pm_repair_accept_tests",
        SYNTHETIC_AGENT_TRACE_REPLAY_PATH,
        "test_pm_repair_decision_accepts_registered_target_fake_pm_package",
        description="Single-scenario synthetic trace shard for valid PM repair target acceptance.",
    ),
    _pytest_k(
        "synthetic_agent_trace_pm_repair_reject_tests",
        SYNTHETIC_AGENT_TRACE_REPLAY_PATH,
        "test_pm_repair_decision_rejects_invalid_targets_fake_pm_package",
        description="Single-scenario synthetic trace shard for invalid PM repair target rejection.",
    ),
    _pytest_k(
        "synthetic_agent_trace_fatal_waiver_tests",
        SYNTHETIC_AGENT_TRACE_REPLAY_PATH,
        "test_fatal_control_blocker_rejects_pm_ordinary_waiver_fake_package",
        description="Single-scenario synthetic trace shard for fatal blocker waiver rejection.",
    ),
    _pytest_k(
        "synthetic_agent_trace_resume_preempt_tests",
        SYNTHETIC_AGENT_TRACE_REPLAY_PATH,
        "test_resume_active_blocker_and_ambiguous_state_preempt_fake_package",
        description="Single-scenario synthetic trace shard for resume blocker preemption.",
    ),
    _pytest_k(
        "synthetic_agent_trace_stale_sibling_tests",
        SYNTHETIC_AGENT_TRACE_REPLAY_PATH,
        "test_route_mutation_stale_sibling_proof_fake_package",
        description="Single-scenario synthetic trace shard for stale sibling proof rejection.",
    ),
)

SYNTHETIC_AGENT_TRACE_SYSTEM_STORY_SHARDS = (
    _pytest_k(
        "synthetic_agent_trace_envelope_authority_tests",
        SYNTHETIC_AGENT_TRACE_REPLAY_PATH,
        "test_pm_package_disposition_envelope_authority_fake_package",
        description="Single-scenario synthetic trace shard for PM envelope authority.",
    ),
    _pytest_k(
        "synthetic_agent_trace_controller_budget_tests",
        SYNTHETIC_AGENT_TRACE_REPLAY_PATH,
        "test_controller_boundary_repair_budget_escalates_fake_package",
        description="Single-scenario synthetic trace shard for controller repair budget escalation.",
    ),
    _pytest_k(
        "synthetic_agent_trace_material_repair_tests",
        SYNTHETIC_AGENT_TRACE_REPLAY_PATH,
        "test_material_repair_generation_blocks_stale_flags_fake_package",
        description="Single-scenario synthetic trace shard for stale material repair flags.",
    ),
    _pytest_k(
        "synthetic_agent_trace_dirty_terminal_tests",
        SYNTHETIC_AGENT_TRACE_REPLAY_PATH,
        "test_dirty_terminal_ledgers_block_completion_fake_package",
        description="Single-scenario synthetic trace shard for dirty terminal ledgers.",
    ),
    _pytest_k(
        "synthetic_agent_trace_bad_repair_envelope_tests",
        SYNTHETIC_AGENT_TRACE_REPLAY_PATH,
        "test_system_story_valid_repair_envelope_bad_content_is_rejected",
        description="Single-scenario system-story shard for bad repair envelope content.",
    ),
    _pytest_k(
        "synthetic_agent_trace_stacked_blockers_tests",
        SYNTHETIC_AGENT_TRACE_REPLAY_PATH,
        "test_system_story_stacked_blockers_preempt_and_preserve_dirty_ledger",
        description="Single-scenario system-story shard for stacked blocker preemption.",
    ),
    _pytest_k(
        "synthetic_agent_trace_failed_repair_loop_tests",
        SYNTHETIC_AGENT_TRACE_REPLAY_PATH,
        "test_system_story_failed_pm_repair_loop_registers_followup_blocker",
        description="Single-scenario system-story shard for failed PM repair loop follow-up.",
    ),
    _pytest_k(
        "synthetic_agent_trace_stale_run_state_tests",
        SYNTHETIC_AGENT_TRACE_REPLAY_PATH,
        "test_system_story_stale_run_state_save_cannot_clear_active_blocker",
        description="Single-scenario system-story shard for stale run-state save rejection.",
    ),
    _pytest_k(
        "synthetic_agent_trace_parallel_stop_tests",
        SYNTHETIC_AGENT_TRACE_REPLAY_PATH,
        "test_system_story_parallel_run_stop_does_not_touch_peer_authority",
        description="Single-scenario system-story shard for peer-safe parallel stop.",
    ),
    _pytest_k(
        "synthetic_agent_trace_terminal_total_gate_tests",
        SYNTHETIC_AGENT_TRACE_REPLAY_PATH,
        "test_system_story_terminal_total_gate_rejects_multiple_dirty_sources",
        description="Single-scenario system-story shard for terminal total gate rejection.",
    ),
)

E2E_SYNTHETIC_CHAOS_REPLAY_REPAIR_SHARDS = (
    _pytest_k(
        "e2e_synthetic_chaos_golden_lifecycle_tests",
        E2E_SYNTHETIC_CHAOS_REPLAY_PATH,
        "test_e2e_golden_fake_ai_run_reaches_clean_terminal_lifecycle",
        description="Single-scenario end-to-end replay shard for clean terminal lifecycle.",
    ),
    _pytest_k(
        "e2e_synthetic_chaos_worker_repair_tests",
        E2E_SYNTHETIC_CHAOS_REPLAY_PATH,
        "test_e2e_worker_bad_package_then_repair_continues_to_terminal",
        description="Single-scenario end-to-end replay shard for worker repair continuation.",
    ),
    _pytest_k(
        "e2e_synthetic_chaos_pm_repair_tests",
        E2E_SYNTHETIC_CHAOS_REPLAY_PATH,
        "test_e2e_pm_repair_bad_package_then_corrected_repair_restores_legal_wait",
        description="Single-scenario end-to-end replay shard for corrected PM repair wait.",
    ),
)

E2E_SYNTHETIC_CHAOS_REPLAY_PROOF_SHARDS = (
    _pytest_k(
        "e2e_synthetic_chaos_no_producer_tests",
        E2E_SYNTHETIC_CHAOS_REPLAY_PATH,
        "test_e2e_no_producer_pm_repair_then_packet_reissue_exposes_producer_evidence",
        description="Single-scenario end-to-end replay shard for no-producer repair gate.",
    ),
    _pytest_k(
        "e2e_synthetic_chaos_background_proof_tests",
        E2E_SYNTHETIC_CHAOS_REPLAY_PATH,
        "test_e2e_background_progress_only_then_final_artifacts_controls_proof_gate",
        description="Single-scenario end-to-end replay shard for background proof gate.",
    ),
    _pytest_k(
        "e2e_synthetic_chaos_parallel_stop_tests",
        E2E_SYNTHETIC_CHAOS_REPLAY_PATH,
        "test_e2e_parallel_run_peer_stop_does_not_mutate_current_run",
        description="Single-scenario end-to-end replay shard for peer-safe stop isolation.",
    ),
    _pytest_k(
        "e2e_synthetic_chaos_terminal_retry_tests",
        E2E_SYNTHETIC_CHAOS_REPLAY_PATH,
        "test_e2e_terminal_overclaim_then_clean_retry_closes_run",
        description="Single-scenario end-to-end replay shard for terminal overclaim retry closure.",
    ),
)

SHADOW_LAUNCHER_CHAOS_REPLAY_SHARDS = (
    _pytest_k(
        "shadow_launcher_shadow_start_tests",
        SHADOW_LAUNCHER_CHAOS_REPLAY_PATH,
        "test_installed_launcher_shadow_start_reaches_releasable_standard_state",
        description="Single-scenario shadow launcher replay shard for installed start lifecycle.",
    ),
    _pytest_k(
        "shadow_launcher_crash_recovery_tests",
        SHADOW_LAUNCHER_CHAOS_REPLAY_PATH,
        "test_crash_recovery_bundle_handles_dead_daemon_duplicate_resume_and_progress_only_proof",
        description="Single-scenario shadow launcher replay shard for crash recovery and progress-only proof.",
    ),
    _pytest_k(
        "shadow_launcher_peer_conflict_tests",
        SHADOW_LAUNCHER_CHAOS_REPLAY_PATH,
        "test_peer_conflict_keeps_current_run_authority_and_rejects_stale_peer_proof",
        description="Single-scenario shadow launcher replay shard for peer conflict authority.",
    ),
    _pytest_k(
        "shadow_launcher_current_assets_tests",
        SHADOW_LAUNCHER_CHAOS_REPLAY_PATH,
        "test_current_pointer_and_installed_assets_resolve_to_current_standard_state",
        description="Single-scenario shadow launcher replay shard for current pointer and installed assets.",
    ),
    _pytest_k(
        "shadow_launcher_malformed_package_tests",
        SHADOW_LAUNCHER_CHAOS_REPLAY_PATH,
        "test_malformed_fake_ai_package_generator_rejects_finite_bad_classes",
        description="Single-scenario shadow launcher replay shard for malformed fake AI package rejection.",
    ),
    _pytest_k(
        "shadow_launcher_bounded_soak_tests",
        SHADOW_LAUNCHER_CHAOS_REPLAY_PATH,
        "test_bounded_soak_repeats_startup_recovery_and_cleanup_without_residue",
        description="Single-scenario shadow launcher replay shard for bounded startup/recovery soak.",
    ),
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
        name="flowguard_packet_result_family_parity",
        command=_py(
            "simulations/run_flowpilot_packet_result_family_parity_checks.py",
            "--json-out",
            "simulations/flowpilot_packet_result_family_parity_results.json",
        ),
        description="FlowGuard obligation-family parity checks for packet-result durable-envelope reconciliation.",
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
        name="flowguard_project_topology_orientation",
        command=_py(
            "simulations/run_flowpilot_project_topology_orientation_checks.py",
            "--json-out",
            "simulations/flowpilot_project_topology_orientation_results.json",
        ),
        description="FlowGuard checks for project topology orientation, freshness, role boundaries, and evidence overclaim hazards.",
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
        description="End-to-end synthetic chaos matrix for daemon-driven fake AI full-flow replays, including no-producer PM repair recovery.",
    ),
    TierCommand(
        name="real_router_dry_run_rehearsal_matrix",
        command=_py(
            "simulations/flowpilot_real_router_dry_run_rehearsal_matrix.py",
            "--json-out",
            "simulations/flowpilot_real_router_dry_run_rehearsal_matrix_results.json",
        ),
        description="Real Router dry-run rehearsal matrix for prepared fake AI packages through public runtime boundaries, including producer-proof repair waits.",
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
        name="historical_live_run_replay_matrix",
        command=_py(
            "simulations/flowpilot_historical_live_run_replay_matrix.py",
            "--json-out",
            "simulations/flowpilot_historical_live_run_replay_matrix_results.json",
        ),
        description="Historical live-run replay package matrix for control-plane, relay, install, projection, and filesystem edge cases.",
    ),
    TierCommand(
        name="known_friction_regression_matrix",
        command=_py(
            "simulations/flowpilot_known_friction_regression_matrix.py",
            "--json-out",
            "simulations/flowpilot_known_friction_regression_matrix_results.json",
        ),
        description="Known-friction parent gate for worker contracts, PM repair atomicity, blocker continuation, status, ACK, stop lifecycle, child replay, install, and background evidence boundaries.",
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
    TierCommand(
        name="flowguard_project_topology_build",
        command=_py("scripts/flowguard_project_topology.py", "build"),
        description="Regenerate FlowGuard project topology orientation artifacts from current model, test, code, and evidence sources.",
    ),
    TierCommand(
        name="flowguard_project_topology_check",
        command=_py("scripts/flowguard_project_topology.py", "check"),
        description="Check FlowGuard project topology artifacts for freshness, required layers, and orientation-only boundary text.",
    ),
    _pytest(
        "project_topology_tests",
        "tests/test_flowguard_project_topology.py",
        description="Focused tests for FlowGuard project topology generation, stale detection, and required layers.",
    ),
    _pytest(
        "test_tier_runner",
        "tests/test_flowpilot_test_tiers.py",
        description="Focused tests for tier command planning and background artifact contracts.",
    ),
    _pytest_k(
        "synthetic_agent_trace_core_tests",
        SYNTHETIC_AGENT_TRACE_REPLAY_PATH,
        (
            "test_happy_path_worker_trace_reaches_pm_disposition "
            "or test_fake_ai_pm_package_trace_catches_same_package_conflicting_decisions "
            "or test_ack_only_trace_keeps_semantic_work_open "
            "or test_trace_rejects_sealed_body_wrong_identity_and_stale_hash "
            "or test_raw_worker_result_cannot_skip_pm_disposition_to_reviewer_pass "
            "or test_fixture_evidence_is_disclosed_but_not_live_completion_evidence "
            "or test_background_progress_only_trace_is_not_pass_evidence"
        ),
        description="Core synthetic trace replay tests for fake role actions through packet/runtime APIs.",
    ),
    *SYNTHETIC_AGENT_TRACE_REPAIR_SHARDS,
    *SYNTHETIC_AGENT_TRACE_SYSTEM_STORY_SHARDS,
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
    *E2E_SYNTHETIC_CHAOS_REPLAY_REPAIR_SHARDS,
    *E2E_SYNTHETIC_CHAOS_REPLAY_PROOF_SHARDS,
    _pytest(
        "real_router_dry_run_rehearsal_matrix_tests",
        "tests/test_flowpilot_real_router_dry_run_rehearsal_matrix.py",
        description="Focused tests for real Router rehearsal rows and known-bad overclaim rejection.",
    ),
    _pytest(
        "real_router_dry_run_rehearsal_tests",
        "tests/test_flowpilot_real_router_dry_run_rehearsal.py",
        description="Runtime rehearsals for prepared fake AI packages through real Router, CLI, repair producer proof, recovery, proof, and terminal gates.",
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
    *SHADOW_LAUNCHER_CHAOS_REPLAY_SHARDS,
    _pytest(
        "historical_live_run_replay_matrix_tests",
        "tests/test_flowpilot_historical_live_run_replay_matrix.py",
        description="Focused tests for historical live-run replay package rows and known-bad matrix rejection.",
    ),
    _pytest(
        "historical_live_run_replay_tests",
        "tests/test_flowpilot_historical_live_run_replay.py",
        description="Runtime historical live-run replay packages through real Router, packet/runtime, resume, proof, install, projection, and filesystem gates.",
    ),
    _pytest(
        "known_friction_regression_matrix_tests",
        "tests/test_flowpilot_known_friction_regression_matrix.py",
        description="Focused tests for six accepted known-friction parent rows, global gates, and known-bad overclaim rejection.",
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
