"""Known-bad StructureMesh/TestMesh hazards for FlowPilot maintenance."""

from __future__ import annotations

STRUCTURE_HAZARDS = (
    "missing_partition_owner",
    "duplicate_root_state_owner",
    "missing_facade",
    "removed_entrypoint",
    "stale_parity",
    "insufficient_release_evidence",
)

MODEL_STRUCTURE_HAZARDS = (
    "missing_model_partition_owner",
    "duplicate_model_state_owner",
    "missing_model_facade",
    "removed_model_entrypoint",
    "stale_model_parity",
    "insufficient_model_release_evidence",
)

TEST_TIER_STRUCTURE_HAZARDS = (
    "missing_test_tier_partition_owner",
    "duplicate_test_tier_state_owner",
    "missing_test_tier_facade",
    "removed_test_tier_entrypoint",
    "stale_test_tier_parity",
    "insufficient_test_tier_release_evidence",
)

TESTMESH_HAZARDS = (
    "missing_child_owner",
    "duplicate_state_owner",
    "hidden_skipped_tests",
    "stale_evidence",
    "timeout_suite",
    "progress_only_background",
    "missing_background_artifact",
    "unbounded_background_fanout",
    "release_required_stale",
)
