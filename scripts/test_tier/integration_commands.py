"""Integration and release FlowPilot test-tier commands."""

from __future__ import annotations

from .command_builders import TierCommand, _py

PRECLOSURE_EVIDENCE_MANIFEST = (
    "tmp/test_results/flowpilot_acceptance_testmesh_preclosure_manifest.json"
)

INTEGRATION_COMMANDS = (
    TierCommand(
        name="packet_control_plane_model",
        command=_py("skills/flowpilot/assets/run_packet_control_plane_checks.py"),
        description="Current packet control-plane model and runner contract.",
        background_recommended=True,
    ),
    TierCommand(
        name="flowguard_route_authority_singularity",
        command=_py(
            "simulations/run_flowpilot_route_authority_singularity_checks.py",
            "--json-out",
            "simulations/flowpilot_route_authority_singularity_results.json",
        ),
        description="Current single-authority and no-fallback route model.",
        background_recommended=True,
    ),
    TierCommand(
        name="flowguard_rejection_liveness_matrix",
        command=_py(
            "simulations/run_flowpilot_rejection_liveness_matrix_checks.py",
            "--json-out",
            "simulations/flowpilot_rejection_liveness_matrix_results.json",
        ),
        description="Current rejection/liveness model matrix.",
        background_recommended=True,
    ),
    TierCommand(
        name="flowguard_terminal_supplemental_repair",
        command=_py(
            "simulations/run_flowpilot_terminal_supplemental_repair_checks.py",
        ),
        description="Current terminal supplemental-repair model.",
        background_recommended=True,
    ),
    TierCommand(
        name="refresh_flowguard_project_topology",
        command=_py("scripts/flowguard_project_topology.py", "build"),
        description=(
            "Refresh the generated project topology after model/result writers "
            "finish and before install freshness checks consume it."
        ),
        background_stage=1,
    ),
    TierCommand(
        name="check_install",
        command=_py("scripts/check_install.py", "--json"),
        description="Repository install contract check.",
        background_stage=2,
    ),
    TierCommand(
        name="audit_local_install_sync",
        command=_py("scripts/audit_local_install_sync.py", "--json"),
        description="Local installed-skill freshness and source sync audit.",
    ),
    TierCommand(
        name="smoke_flowpilot_fast",
        command=_py("scripts/smoke_flowpilot.py", "--fast"),
        description="Smoke checks with reusable thin-parent slow-model proofs.",
        long_running=True,
        background_recommended=True,
    ),
    TierCommand(
        name="flowguard_coverage_sweep",
        command=_py("scripts/run_flowguard_coverage_sweep.py", "--timeout-seconds", "300"),
        description="Read-only FlowGuard coverage sweep.",
        long_running=True,
        background_recommended=True,
    ),
)

RELEASE_COMMANDS = (
    TierCommand(
        name="acceptance_testmesh_contract_tests",
        command=_py("-m", "pytest", "tests/test_flowpilot_acceptance_testmesh.py", "-q"),
        description=(
            "Acceptance TestMesh compiler, final-receipt identity, background proof, "
            "and same-class missing-field rejection checks."
        ),
        release_only=True,
        long_running=True,
        background_recommended=True,
    ),
    TierCommand(
        name="flowpilot_skillguard_deep_contract",
        command=_py("scripts/refresh_flowpilot_skillguard_contract.py", "--check"),
        description="Current native-integrated SkillGuard target lock with no parallel FlowPilot route.",
        release_only=True,
    ),
    TierCommand(
        name="release_tooling",
        command=_py("simulations/run_release_tooling_checks.py"),
        description="Release-tooling FlowGuard checks.",
        release_only=True,
    ),
    TierCommand(
        name="meta_full",
        command=_py(
            "scripts/run_flowguard_background.py",
            "--name",
            "run_meta_checks",
            "--",
            "python",
            "simulations/run_meta_checks.py",
            "--full",
        ),
        description=(
            "Declared layered-full Meta owner; the impact plan executes it only "
            "when its exact applicability inputs changed, otherwise consumers use "
            "its current owner reuse ticket."
        ),
        release_only=True,
        long_running=True,
        background_recommended=True,
    ),
    TierCommand(
        name="capability_full",
        command=_py(
            "scripts/run_flowguard_background.py",
            "--name",
            "run_capability_checks",
            "--",
            "python",
            "simulations/run_capability_checks.py",
            "--full",
        ),
        description=(
            "Declared layered-full Capability owner; the impact plan executes it "
            "only when its exact applicability inputs changed, otherwise consumers "
            "use its current owner reuse ticket."
        ),
        release_only=True,
        long_running=True,
        background_recommended=True,
    ),
    TierCommand(
        name="public_release_check",
        command=_py("scripts/check_public_release.py", "--json", "--skip-validation"),
        description="Public release boundary validation with dependency URL probing; tier validation runs separately.",
        release_only=True,
        long_running=True,
        background_recommended=True,
        background_stage=2,
    ),
)

EVIDENCE_CLOSURE_COMMANDS = (
    TierCommand(
        name="contract_exhaustion_current_evidence",
        command=_py(
            "simulations/run_flowpilot_contract_exhaustion_mesh_checks.py",
            "--evidence-manifest",
            PRECLOSURE_EVIDENCE_MANIFEST,
            "--evidence-scope",
            "done",
            "--json-out",
            "simulations/flowpilot_contract_exhaustion_mesh_results.json",
        ),
        description="Strict contract-exhaustion consumer of the current preclosure owner evidence.",
        release_only=True,
        background_recommended=True,
        background_stage=1,
    ),
    TierCommand(
        name="current_contract_cartesian_current_evidence",
        command=_py(
            "simulations/run_flowpilot_current_contract_cartesian_matrix_checks.py",
            "--evidence-manifest",
            PRECLOSURE_EVIDENCE_MANIFEST,
            "--evidence-scope",
            "done",
            "--json-out",
            "simulations/flowpilot_current_contract_cartesian_matrix_results.json",
        ),
        description="Strict current-contract Cartesian consumer of the current preclosure owner evidence.",
        release_only=True,
        background_recommended=True,
        background_stage=1,
    ),
    TierCommand(
        name="model_test_alignment_current_evidence",
        command=_py(
            "simulations/run_flowpilot_model_test_alignment_checks.py",
            "--evidence-manifest",
            PRECLOSURE_EVIDENCE_MANIFEST,
            "--evidence-scope",
            "done",
            "--json-out",
            "simulations/flowpilot_model_test_alignment_results.json",
        ),
        description="Strict MTA consumer of the current preclosure owner evidence.",
        release_only=True,
        background_recommended=True,
        background_stage=1,
    ),
    TierCommand(
        name="acceptance_testmesh_current_evidence",
        command=_py(
            "simulations/run_flowpilot_acceptance_testmesh_checks.py",
            "--evidence-manifest",
            PRECLOSURE_EVIDENCE_MANIFEST,
            "--json-out",
            "simulations/flowpilot_acceptance_testmesh_results.json",
        ),
        description="Strict Acceptance TestMesh consumer of the current preclosure owner evidence.",
        release_only=True,
        background_recommended=True,
        background_stage=1,
    ),
    TierCommand(
        name="behavior_commitment_risk_current_evidence",
        command=_py(
            "simulations/run_flowpilot_053_ppa_maintenance_checks.py",
            "--json-out",
            "simulations/flowpilot_053_ppa_maintenance_results.json",
        ),
        description="BCL/PPA and risk evidence runs after the strict MTA owner in the same closure tier.",
        release_only=True,
        background_recommended=True,
        background_stage=2,
    ),
)
