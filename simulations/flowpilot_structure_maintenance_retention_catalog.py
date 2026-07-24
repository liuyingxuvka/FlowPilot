"""StructureMesh catalog for the FlowPilot runtime-retention split."""

from __future__ import annotations

from flowguard import (
    EVIDENCE_CONFORMANCE_GREEN,
    ModuleStructureEvidence,
    PublicEntrypointEvidence,
    StructurePartitionItem,
)


RETENTION_FACADE_FUNCTIONS = (
    "_canonical_bytes",
    "build_plan",
    "_atomic_write_bytes",
    "write_plan",
    "_candidate_path",
    "_archive_path",
    "_create_verified_archive",
    "_updated_index",
    "_mark_cleanup",
    "_write_index",
    "_remove_archived_heavy_paths",
    "apply_plan",
    "_print_report",
    "main",
)

RETENTION_SCAN_FUNCTIONS = (
    "_tree_size",
    "_parse_timestamp",
    "_run_timestamp",
    "_index_entries",
    "_pid_is_live",
    "_payload_live_pid",
    "_lock_is_active",
    "_active_write_lock_paths",
    "_run_terminal_evidence",
    "_run_live_owner",
    "_run_open_work",
    "_validation_terminal_evidence",
    "_pinned",
    "_reference_sources",
    "_is_within",
    "_attach_references",
    "_record_protection_reasons",
    "_rank_eligible_records",
    "build_report",
)

RETENTION_COMMON_FUNCTIONS = (
    "RetentionPlanError",
    "_utc_now",
    "_project_relative",
    "_read_json_result",
    "_read_json",
    "_sha256_bytes",
    "_sha256_file",
    "_tree_fingerprint",
)


RETENTION_STRUCTURE_MODULES = (
    ModuleStructureEvidence(
        module_id="retention_cli_facade",
        path="scripts/flowpilot_runtime_retention.py",
        layer="facade",
        extracted_from="scripts/flowpilot_runtime_retention.py",
        owns_functions=RETENTION_FACADE_FUNCTIONS,
        owns_state=(
            "retention_frozen_plan",
            "retention_archive_receipt",
        ),
        owns_side_effects=(
            "write_frozen_retention_plan",
            "write_verified_archive",
            "write_retained_index",
            "remove_archived_heavy_paths",
            "emit_json_report",
        ),
        behavior_contracts=(
            "read-only scan is the default command",
            "apply requires an exact frozen plan fingerprint",
            "archive verification precedes index update and heavy-path removal",
            "public CLI and import facade remain stable",
        ),
        dependencies=(
            "retention_scan_owner",
            "retention_common_kernel",
        ),
        facade_retained=True,
        behavior_parity_current=True,
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        module_id="retention_scan_owner",
        path="scripts/flowpilot_runtime_retention_lib/scan.py",
        layer="read_only_inventory_owner",
        extracted_from="scripts/flowpilot_runtime_retention.py",
        owns_functions=RETENTION_SCAN_FUNCTIONS,
        owns_state=(
            "retention_candidate_inventory",
            "retention_protection_reasons",
        ),
        behavior_contracts=(
            "scan never mutates retained runtime evidence",
            "current live referenced pinned and open-work records are protected",
            "eligibility ordering is deterministic",
        ),
        dependencies=("retention_common_kernel",),
        behavior_parity_current=True,
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        module_id="retention_common_kernel",
        path="scripts/flowpilot_runtime_retention_lib/common.py",
        layer="pure_common_kernel",
        extracted_from="scripts/flowpilot_runtime_retention.py",
        owns_functions=RETENTION_COMMON_FUNCTIONS,
        owns_config=(
            "retention_schema_versions",
            "retention_reference_max_bytes",
            "retention_heavy_path_inventory",
        ),
        behavior_contracts=(
            "canonical JSON and SHA-256 identities",
            "project-relative path normalization",
            "shared immutable schema and inventory constants",
        ),
        behavior_parity_current=True,
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
)


RETENTION_STRUCTURE_PARTITIONS = (
    StructurePartitionItem(
        "retention_cli_and_import_facade",
        item_type="public_entrypoint",
        owner_module_id="retention_cli_facade",
        ownership="parent",
        public_surface=True,
        old_path="scripts/flowpilot_runtime_retention.py",
        new_path="scripts/flowpilot_runtime_retention.py",
    ),
    *tuple(
        StructurePartitionItem(
            function_name,
            item_type="function",
            owner_module_id="retention_cli_facade",
            old_path=f"scripts/flowpilot_runtime_retention.py::{function_name}",
            new_path=f"scripts/flowpilot_runtime_retention.py::{function_name}",
        )
        for function_name in RETENTION_FACADE_FUNCTIONS
    ),
    *tuple(
        StructurePartitionItem(
            function_name,
            item_type="function",
            owner_module_id="retention_scan_owner",
            old_path=f"scripts/flowpilot_runtime_retention.py::{function_name}",
            new_path=(
                "scripts/flowpilot_runtime_retention_lib/scan.py::"
                f"{function_name}"
            ),
        )
        for function_name in RETENTION_SCAN_FUNCTIONS
    ),
    *tuple(
        StructurePartitionItem(
            function_name,
            item_type="class" if function_name == "RetentionPlanError" else "function",
            owner_module_id="retention_common_kernel",
            old_path=f"scripts/flowpilot_runtime_retention.py::{function_name}",
            new_path=(
                "scripts/flowpilot_runtime_retention_lib/common.py::"
                f"{function_name}"
            ),
        )
        for function_name in RETENTION_COMMON_FUNCTIONS
    ),
    StructurePartitionItem(
        "retention_frozen_plan",
        item_type="state",
        owner_module_id="retention_cli_facade",
    ),
    StructurePartitionItem(
        "retention_archive_receipt",
        item_type="state",
        owner_module_id="retention_cli_facade",
    ),
    StructurePartitionItem(
        "retention_candidate_inventory",
        item_type="state",
        owner_module_id="retention_scan_owner",
    ),
    StructurePartitionItem(
        "retention_protection_reasons",
        item_type="state",
        owner_module_id="retention_scan_owner",
    ),
    StructurePartitionItem(
        "write_frozen_retention_plan",
        item_type="side_effect",
        owner_module_id="retention_cli_facade",
    ),
    StructurePartitionItem(
        "write_verified_archive",
        item_type="side_effect",
        owner_module_id="retention_cli_facade",
    ),
    StructurePartitionItem(
        "write_retained_index",
        item_type="side_effect",
        owner_module_id="retention_cli_facade",
    ),
    StructurePartitionItem(
        "remove_archived_heavy_paths",
        item_type="side_effect",
        owner_module_id="retention_cli_facade",
    ),
    StructurePartitionItem(
        "emit_json_report",
        item_type="side_effect",
        owner_module_id="retention_cli_facade",
    ),
    StructurePartitionItem(
        "retention_schema_versions",
        item_type="config",
        owner_module_id="retention_common_kernel",
    ),
    StructurePartitionItem(
        "retention_reference_max_bytes",
        item_type="config",
        owner_module_id="retention_common_kernel",
    ),
    StructurePartitionItem(
        "retention_heavy_path_inventory",
        item_type="config",
        owner_module_id="retention_common_kernel",
    ),
)


RETENTION_PUBLIC_ENTRYPOINTS = (
    PublicEntrypointEvidence(
        entrypoint_id="flowpilot_runtime_retention_cli",
        entrypoint_type="cli",
        old_path="scripts/flowpilot_runtime_retention.py",
        new_path="scripts/flowpilot_runtime_retention.py",
        compatibility_preserved=True,
        facade_available=True,
        parity_evidence_current=True,
        parity_evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
        evidence_path="tests/test_flowpilot_maintenance_tools.py",
    ),
    PublicEntrypointEvidence(
        entrypoint_id="flowpilot_runtime_retention_import_api",
        entrypoint_type="python_import",
        old_path="scripts.flowpilot_runtime_retention",
        new_path="scripts.flowpilot_runtime_retention",
        compatibility_preserved=True,
        facade_available=True,
        parity_evidence_current=True,
        parity_evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
        evidence_path="tests/test_flowpilot_maintenance_tools.py",
    ),
)


RETENTION_STRUCTURE_HAZARDS = (
    "missing_retention_partition_owner",
    "duplicate_retention_state_owner",
    "missing_retention_facade",
    "removed_retention_entrypoint",
    "retention_dependency_cycle",
    "stale_retention_parity",
    "insufficient_retention_release_evidence",
)
