"""StructureMesh catalog for the public test-tier facade and background owners."""

from __future__ import annotations

from flowguard import (
    EVIDENCE_CONFORMANCE_GREEN,
    ModuleStructureEvidence,
    PublicEntrypointEvidence,
    StructurePartitionItem,
)


TEST_TIER_PUBLIC_ENTRYPOINTS = (
    PublicEntrypointEvidence(
        "run_test_tier_cli",
        old_path="scripts/run_test_tier.py",
        new_path="scripts/run_test_tier.py",
        parity_evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        evidence_path="simulations/flowpilot_structure_maintenance_results.json",
        release_required=True,
    ),
    PublicEntrypointEvidence(
        "run_test_tier_import_api",
        old_path="scripts.run_test_tier",
        new_path="scripts.run_test_tier",
        parity_evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        evidence_path="simulations/flowpilot_structure_maintenance_results.json",
        release_required=True,
    ),
)


TEST_TIER_STRUCTURE_PARTITIONS = (
    StructurePartitionItem(
        "test_tier_cli_and_import_facade",
        item_type="public_entrypoint",
        owner_module_id="test_tier_facade",
        ownership="parent",
        old_path="scripts/run_test_tier.py",
        new_path="scripts/run_test_tier.py",
    ),
    StructurePartitionItem(
        "background_artifact_contract",
        item_type="function_cluster",
        owner_module_id="test_tier_background_artifacts",
        old_path="scripts/run_test_tier.py artifact helpers",
        new_path="scripts/test_tier/background.py",
    ),
    StructurePartitionItem(
        "background_child_exact_process_tree",
        item_type="function_cluster",
        owner_module_id="test_tier_background_child",
        old_path="scripts/run_test_tier.py run_background_child",
        new_path="scripts/test_tier/background_child.py",
    ),
    StructurePartitionItem(
        "background_child_process_identity_observation",
        item_type="state",
        owner_module_id="test_tier_background_child",
        old_path="run_test_tier.run_background_child process identity",
        new_path="background_child.run_background_child process identity",
    ),
    StructurePartitionItem(
        "background_child_receipt_writes",
        item_type="side_effect",
        owner_module_id="test_tier_background_child",
        old_path="run_test_tier.run_background_child artifact writes",
        new_path="background_child.run_background_child artifact writes",
    ),
    StructurePartitionItem(
        "background_supervisor_stage_scheduler",
        item_type="function_cluster",
        owner_module_id="test_tier_background_supervisor",
        old_path="scripts/run_test_tier.py run_background_supervisor",
        new_path="scripts/test_tier/background_supervisor.py",
    ),
    StructurePartitionItem(
        "background_supervisor_queue_state",
        item_type="state",
        owner_module_id="test_tier_background_supervisor",
        old_path="run_test_tier supervisor pending/running/completed queues",
        new_path="background_supervisor pending/running/completed queues",
    ),
    StructurePartitionItem(
        "background_supervisor_receipt_writes",
        item_type="side_effect",
        owner_module_id="test_tier_background_supervisor",
        old_path="run_test_tier supervisor artifact writes",
        new_path="background_supervisor supervisor artifact writes",
    ),
    StructurePartitionItem(
        "covered_source_fingerprint_authority",
        item_type="function_cluster",
        owner_module_id="test_tier_source_fingerprint",
        old_path="scripts/run_test_tier.py source fingerprint calls",
        new_path="scripts/test_tier/source_fingerprint.py",
    ),
    StructurePartitionItem(
        "background_receipt_verification",
        item_type="function_cluster",
        owner_module_id="test_tier_verification",
        old_path="scripts/run_test_tier.py background verification",
        new_path="scripts/test_tier/verification.py",
    ),
    StructurePartitionItem(
        "background_timeout_and_artifact_config",
        item_type="config",
        owner_module_id="test_tier_background_artifacts",
        old_path="scripts/run_test_tier.py background constants",
        new_path="scripts/test_tier/background.py background constants",
    ),
)


TEST_TIER_STRUCTURE_MODULES = (
    ModuleStructureEvidence(
        "test_tier_facade",
        path="scripts/run_test_tier.py",
        layer="parent",
        owns_functions=(
            "main",
            "run_foreground",
            "run_background_child",
            "run_background_supervisor",
        ),
        behavior_contracts=(
            "unchanged public CLI arguments",
            "unchanged scripts.run_test_tier import surface",
        ),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "test_tier_background_artifacts",
        path="scripts/test_tier/background.py",
        owns_functions=(
            "artifact_paths",
            "classify_background_artifact",
            "launch_background",
        ),
        owns_config=("background_timeout_and_artifact_config",),
        behavior_contracts=("stable background artifact schema",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
    ),
    ModuleStructureEvidence(
        "test_tier_background_child",
        path="scripts/test_tier/background_child.py",
        owns_functions=("run_background_child",),
        owns_state=("background_child_process_identity_observation",),
        owns_side_effects=("background_child_receipt_writes",),
        behavior_contracts=(
            "PID plus start-token identity",
            "descendant-zero terminal receipt",
            "same covered-source fingerprint",
        ),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "test_tier_background_supervisor",
        path="scripts/test_tier/background_supervisor.py",
        owns_functions=(
            "next_background_launch_index",
            "launch_background_supervisor",
            "run_background_supervisor",
        ),
        owns_state=("background_supervisor_queue_state",),
        owns_side_effects=("background_supervisor_receipt_writes",),
        behavior_contracts=(
            "background-stage ordering",
            "bounded parallelism",
            "supervisor same-fingerprint terminal result",
        ),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "test_tier_source_fingerprint",
        path="scripts/test_tier/source_fingerprint.py",
        owns_functions=("covered_source_files", "source_fingerprint"),
        behavior_contracts=("single covered-source fingerprint authority",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
    ),
    ModuleStructureEvidence(
        "test_tier_verification",
        path="scripts/test_tier/verification.py",
        owns_functions=("verify_background_tier",),
        behavior_contracts=("read-only terminal receipt verification",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
    ),
)
