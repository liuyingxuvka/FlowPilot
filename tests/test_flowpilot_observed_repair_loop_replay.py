from __future__ import annotations

from tests.flowpilot_repair_test_helpers import runtime, seeded_ledger


def test_observed_repair_v2_to_v39_loop_breaks_before_another_ordinary_repair() -> None:
    ledger, blocker_id = seeded_ledger(repair_depth=39, blocker_class="evidence_gap")

    review = runtime._repair_loop_break_glass_review(ledger, ledger["active_blockers"][blocker_id])
    packet_id = runtime._ensure_pm_repair_decision_packet_for_blocker(ledger, blocker_id)

    assert review["repair_depth"] == 39
    assert review["threshold_exceeded"] is True
    assert packet_id == ""
    assert ledger["active_blockers"][blocker_id]["pm_repair_packet_id"] == ""
    assert any(event["event_type"] == "repair_loop_break_glass_required" for event in ledger["events"])
