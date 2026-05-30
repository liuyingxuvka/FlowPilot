"""Canonical maintenance registry for FlowPilot maintenance reports."""

from __future__ import annotations

import json
from typing import Any, Literal, NamedTuple, Sequence


SurfaceKind = Literal["runtime_facade", "script_entrypoint", "model_facade"]


class MaintenanceSurface(NamedTuple):
    surface_id: str
    path: str
    kind: SurfaceKind
    owner: str
    public_role: str
    evidence_family: str
    install_required: bool = True


THRESHOLDS = {
    "runtime_owner_module_lines": 450,
    "runtime_facade_lines": 700,
    "script_entry_lines": 450,
    "test_file_watch_lines": 900,
    "model_file_watch_lines": 1600,
}

MAINTENANCE_SURFACES: tuple[MaintenanceSurface, ...] = (
    MaintenanceSurface(
        surface_id="runtime-facade:flowpilot-router",
        path="skills/flowpilot/assets/flowpilot_router.py",
        kind="runtime_facade",
        owner="router_facade",
        public_role="public_router_entrypoint",
        evidence_family="router_facade_parity",
    ),
    MaintenanceSurface(
        surface_id="runtime-facade:flowpilot-paths",
        path="skills/flowpilot/assets/flowpilot_paths.py",
        kind="runtime_facade",
        owner="runtime_path_contracts",
        public_role="public_paths_entrypoint",
        evidence_family="runtime_path_contracts",
    ),
    MaintenanceSurface(
        surface_id="runtime-facade:flowpilot-packets",
        path="skills/flowpilot/assets/flowpilot_packets.py",
        kind="runtime_facade",
        owner="packet_runtime_cli",
        public_role="public_packet_cli_entrypoint",
        evidence_family="packet_runtime_architecture",
        install_required=False,
    ),
    MaintenanceSurface(
        surface_id="runtime-facade:flowpilot-outputs",
        path="skills/flowpilot/assets/flowpilot_outputs.py",
        kind="runtime_facade",
        owner="role_output_cli",
        public_role="public_role_output_cli_entrypoint",
        evidence_family="role_output_runtime_architecture",
        install_required=False,
    ),
    MaintenanceSurface(
        surface_id="runtime-facade:flowpilot-runtime",
        path="skills/flowpilot/assets/flowpilot_runtime.py",
        kind="runtime_facade",
        owner="runtime_cli",
        public_role="public_runtime_cli_entrypoint",
        evidence_family="runtime_cli_contract",
    ),
    MaintenanceSurface(
        surface_id="script-entrypoint:check-install",
        path="scripts/check_install.py",
        kind="script_entrypoint",
        owner="local_install_sync",
        public_role="install_check_cli",
        evidence_family="local_install_sync",
    ),
    MaintenanceSurface(
        surface_id="script-entrypoint:install-flowpilot",
        path="scripts/install_flowpilot.py",
        kind="script_entrypoint",
        owner="local_install_sync",
        public_role="install_cli",
        evidence_family="local_install_sync",
    ),
    MaintenanceSurface(
        surface_id="script-entrypoint:run-test-tier",
        path="scripts/run_test_tier.py",
        kind="script_entrypoint",
        owner="test_tier_runner",
        public_role="test_tier_cli",
        evidence_family="test_tier_runner",
    ),
    MaintenanceSurface(
        surface_id="script-entrypoint:smoke-autopilot",
        path="scripts/smoke_autopilot.py",
        kind="script_entrypoint",
        owner="smoke_fast_validation",
        public_role="smoke_cli",
        evidence_family="smoke_fast_validation",
    ),
    MaintenanceSurface(
        surface_id="script-entrypoint:audit-local-install-sync",
        path="scripts/audit_local_install_sync.py",
        kind="script_entrypoint",
        owner="local_install_sync",
        public_role="install_freshness_audit_cli",
        evidence_family="local_install_sync",
    ),
    MaintenanceSurface(
        surface_id="script-entrypoint:run-flowguard-coverage-sweep",
        path="scripts/run_flowguard_coverage_sweep.py",
        kind="script_entrypoint",
        owner="coverage_sweep_runner",
        public_role="coverage_sweep_cli",
        evidence_family="coverage_sweep_runner",
    ),
    MaintenanceSurface(
        surface_id="script-entrypoint:flowguard-project-topology",
        path="scripts/flowguard_project_topology.py",
        kind="script_entrypoint",
        owner="project_topology_orientation",
        public_role="project_topology_cli",
        evidence_family="project_topology_orientation",
    ),
    MaintenanceSurface(
        surface_id="script-entrypoint:flowpilot-maintenance-map",
        path="scripts/flowpilot_maintenance_map.py",
        kind="script_entrypoint",
        owner="maintenance_map_cli",
        public_role="maintenance_map_cli",
        evidence_family="maintenance_map_cli",
    ),
    MaintenanceSurface(
        surface_id="model-facade:capability-model",
        path="simulations/capability_model.py",
        kind="model_facade",
        owner="flowpilot_capability_model",
        public_role="capability_parent_model_entrypoint",
        evidence_family="capability_model_checks",
    ),
    MaintenanceSurface(
        surface_id="model-facade:meta-model",
        path="simulations/meta_model.py",
        kind="model_facade",
        owner="flowpilot_meta_model",
        public_role="meta_parent_model_entrypoint",
        evidence_family="meta_model_checks",
    ),
    MaintenanceSurface(
        surface_id="model-facade:structure-maintenance",
        path="simulations/flowpilot_structure_maintenance_model.py",
        kind="model_facade",
        owner="flowpilot_structure_maintenance",
        public_role="structure_maintenance_model_entrypoint",
        evidence_family="structuremesh_checks",
    ),
    MaintenanceSurface(
        surface_id="model-facade:router-facade-split",
        path="simulations/flowpilot_router_facade_split_model.py",
        kind="model_facade",
        owner="flowpilot_router_facade_split",
        public_role="router_facade_split_model_entrypoint",
        evidence_family="router_facade_split_checks",
    ),
    MaintenanceSurface(
        surface_id="model-facade:model-test-source-contracts",
        path="simulations/flowpilot_model_test_alignment_source_contracts.py",
        kind="model_facade",
        owner="flowpilot_model_test_alignment",
        public_role="source_contract_alignment_entrypoint",
        evidence_family="model_test_alignment_checks",
    ),
    MaintenanceSurface(
        surface_id="model-facade:project-topology-orientation",
        path="simulations/flowpilot_project_topology_orientation_model.py",
        kind="model_facade",
        owner="project_topology_orientation",
        public_role="project_topology_orientation_model_entrypoint",
        evidence_family="project_topology_orientation_checks",
    ),
)

CURRENT_MAINTENANCE_DECISIONS = (
    "Runtime owner modules are under the StructureMesh line threshold; do not split runtime again without a matching model block and external contract test.",
    "Test-tier command definitions are split into stable command-group modules while scripts/test_tier/definitions.py remains the public entrypoint.",
    "Router facade split, structure-maintenance, and source-contract alignment models keep their current public import paths while large catalogs move into helper modules.",
    "Large router-runtime tests stay as watchlist items in this pass; split them only by externally visible contract family and after fixture ownership is clear.",
    "Remaining large install and defect scripts stay as watchlist items because they are behavior-bearing command surfaces, not pure catalog moves.",
)


def maintenance_surfaces(kind: SurfaceKind | None = None) -> tuple[MaintenanceSurface, ...]:
    if kind is None:
        return MAINTENANCE_SURFACES
    return tuple(surface for surface in MAINTENANCE_SURFACES if surface.kind == kind)


def surface_paths(kind: SurfaceKind) -> tuple[str, ...]:
    return tuple(surface.path for surface in maintenance_surfaces(kind))


def install_required_surface_paths() -> tuple[str, ...]:
    return tuple(surface.path for surface in MAINTENANCE_SURFACES if surface.install_required)


def check() -> dict[str, Any]:
    return {
        "ok": True,
        "surface_count": len(MAINTENANCE_SURFACES),
        "install_required_surface_count": len(install_required_surface_paths()),
        "thresholds": dict(THRESHOLDS),
        "surface_kinds": {
            kind: len(maintenance_surfaces(kind))
            for kind in ("runtime_facade", "script_entrypoint", "model_facade")
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    _ = argv
    print(json.dumps(check(), indent=2, sort_keys=True))
    return 0


RUNTIME_FACADES = surface_paths("runtime_facade")
SCRIPT_ENTRYPOINTS = surface_paths("script_entrypoint")
MODEL_FACADES = surface_paths("model_facade")


__all__ = (
    "MaintenanceSurface",
    "THRESHOLDS",
    "MAINTENANCE_SURFACES",
    "CURRENT_MAINTENANCE_DECISIONS",
    "maintenance_surfaces",
    "surface_paths",
    "install_required_surface_paths",
    "RUNTIME_FACADES",
    "SCRIPT_ENTRYPOINTS",
    "MODEL_FACADES",
    "check",
    "main",
)


if __name__ == "__main__":
    raise SystemExit(main())
