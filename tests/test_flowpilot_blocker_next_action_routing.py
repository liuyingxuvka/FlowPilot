from __future__ import annotations

import json

from tests.flowpilot_repair_test_helpers import runtime, seeded_ledger


def test_missing_required_information_stops_instead_of_opening_pm_repair_route() -> None:
    ledger, blocker_id = seeded_ledger(blocker_class="missing_required_information")

    packet_id = runtime._ensure_pm_repair_decision_packet_for_blocker(ledger, blocker_id)
    blocker = ledger["active_blockers"][blocker_id]

    assert packet_id == ""
    assert blocker["pm_repair_packet_id"] == ""
    assert blocker["status"] == "stopped"
    assert blocker["runtime_next_action"] == "same_packet_block_or_stop_for_user"


def test_missing_matching_flowguard_routes_to_flowguard_packet_not_pm_plan() -> None:
    ledger, blocker_id = seeded_ledger(blocker_class="missing_matching_flowguard_report")

    packet_id = runtime._ensure_pm_repair_decision_packet_for_blocker(ledger, blocker_id)
    blocker = ledger["active_blockers"][blocker_id]
    packet = ledger["packets"][packet_id]

    assert packet["envelope"]["packet_kind"] == "flowguard_check"
    assert packet["envelope"]["repair_blocker_id"] == blocker_id
    assert blocker["pm_repair_packet_id"] == ""
    assert blocker["flowguard_repair_packet_id"] == packet_id


def test_pm_decision_contract_rejects_known_hard_route_blocker_as_ordinary_repair() -> None:
    ledger, blocker_id = seeded_ledger(blocker_class="missing_matching_flowguard_report")
    packet_id = runtime.issue_task_packet(
        ledger,
        "pm",
        "Legacy PM repair packet",
        json.dumps(
            {
                "schema_version": "black_box_flowpilot.pm_repair_decision_packet.v1",
                "blocker_id": blocker_id,
            },
            sort_keys=True,
        ),
        packet_kind="pm_repair_decision",
        subject_id=blocker_id,
        route_scope="pm_repair_decision",
        repair_blocker_id=blocker_id,
    )
    result = {
        "body": json.dumps(
            {
                "decision": "repair_current_scope",
                "reason": "Wrongly repair through PM plan.",
                "target_blocker_id": blocker_id,
                "next_action": "repair_current_scope",
            },
            sort_keys=True,
        )
    }

    check = runtime._pm_repair_decision_result_violation(ledger["packets"][packet_id], result, ledger)

    assert not check.ok
    assert "issue_matching_flowguard_packet" in check.blocked_reason
