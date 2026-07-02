from __future__ import annotations

from tests.flowpilot_repair_test_helpers import runtime, seeded_ledger


def test_reviewer_flowguard_reads_only_match_current_subject_and_repair_blocker() -> None:
    ledger, blocker_id = seeded_ledger(blocker_class="evidence_gap")
    subject_packet_id = ledger["active_blockers"][blocker_id]["subject_packet_id"]
    target_result_id = ledger["active_blockers"][blocker_id]["target_result_id"]
    wrong_result_id = "result-wrong-flowguard"
    ledger["results"][wrong_result_id] = {
        "result_id": wrong_result_id,
        "packet_id": "packet-wrong-flowguard",
        "status": "accepted",
        "body": "{}",
        "envelope": {"body_hash": runtime.hash_text("{}")},
    }
    ledger["flowguard_work_orders"]["order-wrong"] = {
        "order_id": "order-wrong",
        "subject_id": "other-packet",
        "modeled_target": "development_process",
        "status": "complete",
        "decision": "pass",
        "proof_result_id": wrong_result_id,
        "producer_result_id": wrong_result_id,
        "source_generation": ledger["source_generation"],
        "proof_artifact": wrong_result_id,
        "blocker_id": blocker_id,
    }
    correct_result_id = "result-correct-flowguard"
    ledger["results"][correct_result_id] = {
        "result_id": correct_result_id,
        "packet_id": "packet-correct-flowguard",
        "status": "accepted",
        "body": "{}",
        "envelope": {"body_hash": runtime.hash_text("{}")},
    }
    ledger["flowguard_work_orders"]["order-correct"] = {
        "order_id": "order-correct",
        "subject_id": subject_packet_id,
        "modeled_target": "development_process",
        "status": "complete",
        "decision": "pass",
        "proof_result_id": correct_result_id,
        "producer_result_id": correct_result_id,
        "source_generation": ledger["source_generation"],
        "proof_artifact": correct_result_id,
        "blocker_id": blocker_id,
    }

    reads, manifest = runtime._flowguard_evidence_reads_for_review(
        ledger,
        subject_packet_id,
        repair_blocker_id=blocker_id,
    )

    assert [entry["flowguard_result_id"] for entry in manifest] == [correct_result_id]
    assert [read["result_id"] for read in reads] == [correct_result_id]
    assert target_result_id != correct_result_id
