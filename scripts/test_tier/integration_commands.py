"""Integration and release FlowPilot test-tier commands."""

from __future__ import annotations

from .command_builders import TierCommand, _py

INTEGRATION_COMMANDS = (
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
            "--force",
        ),
        description=(
            "Sole layered-full Meta owner; writes the stable run_meta_checks receipt "
            "that later consumers verify without relaunching."
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
            "--force",
        ),
        description=(
            "Sole layered-full Capability owner; writes the stable run_capability_checks "
            "receipt that later consumers verify without relaunching."
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
