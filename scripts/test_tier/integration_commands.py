"""Integration and release FlowPilot test-tier commands."""

from __future__ import annotations

from .command_builders import TierCommand, _py

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
        name="smoke_flowpilot_fast",
        command=_py("scripts/smoke_flowpilot.py", "--fast"),
        description="Smoke checks with reusable thin-parent slow-model proofs.",
        long_running=True,
        background_recommended=True,
    ),
    TierCommand(
        name="flowguard_coverage_sweep",
        command=_py("scripts/run_flowguard_coverage_sweep.py", "--timeout-seconds", "60"),
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
        command=_py("scripts/check_public_release.py", "--json", "--skip-validation"),
        description="Public release boundary validation with dependency URL probing; tier validation runs separately.",
        release_only=True,
        long_running=True,
        background_recommended=True,
        background_stage=1,
    ),
)
