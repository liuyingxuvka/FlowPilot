from __future__ import annotations

from tests.flowpilot_repair_test_helpers import runtime, seeded_ledger


def test_repair_depth_threshold_triggers_at_fifth_repair_node() -> None:
    for depth, expected in ((0, False), (1, False), (2, False), (4, False), (5, True), (6, True)):
        ledger, blocker_id = seeded_ledger(repair_depth=depth, blocker_class="evidence_gap")

        review = runtime._repair_loop_break_glass_review(ledger, ledger["active_blockers"][blocker_id])

        assert review["repair_depth"] == depth
        assert review["attempt_count"] == max(1, depth)
        assert review["threshold_exceeded"] is expected


def test_different_blocker_classes_in_same_repair_dossier_still_accumulate() -> None:
    ledger, _blocker_id = seeded_ledger(repair_depth=0, blocker_class="evidence_gap")
    classes = [
        "evidence_gap",
        "flowguard_failure",
        "route_decomposition",
        "local_artifact",
        "system_validation_failure",
    ]
    ledger["active_blockers"] = {}
    for index, blocker_class in enumerate(classes):
        blocker_id = f"blocker-{index}"
        ledger["active_blockers"][blocker_id] = {
            "blocker_id": blocker_id,
            "status": "active" if index == len(classes) - 1 else "retired_after_new_current_blocker",
            "route_node_id": "node-root",
            "blocker_class": blocker_class,
            "gate_kind": "review",
            "required_recheck_role": "reviewer",
            "packet_id": f"packet-{index}",
            "subject_packet_id": f"packet-{index}",
            "repair_target_packet_id": f"packet-{index}",
            "pm_repair_packet_id": f"pm-{index}",
            "pm_repair_decision_id": "",
        }

    review = runtime._repair_loop_break_glass_review(ledger, ledger["active_blockers"]["blocker-4"])

    assert review["attempt_count"] == 5
    assert review["threshold_exceeded"] is True
