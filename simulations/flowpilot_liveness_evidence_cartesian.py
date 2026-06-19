"""Cartesian liveness-evidence matrix for FlowPilot background roles."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from itertools import product
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
if str(ASSETS) not in sys.path:
    sys.path.insert(0, str(ASSETS))

from flowpilot_core_runtime import packets, runtime  # noqa: E402


MODEL_ID = "flowpilot_liveness_evidence_cartesian"

ROLES = ("pm", "worker", "reviewer", "flowguard_operator")
ACK_STATES = ("no_ack", "fresh_ack", "stale_ack")
RESULT_STATES = ("no_result", "valid_final_result", "invalid_final_result")
PROGRESS_STATES = (
    "none",
    "same_lease_fresh",
    "same_lease_stale_10_30",
    "same_lease_stale_30_plus",
    "wrong_lease",
    "wrong_packet",
    "after_accepted_result",
)
LEGACY_POLLUTION_STATES = (
    "none",
    "timeout_unknown",
    "host_liveness_timeout",
    "bounded_wait_timeout",
    "last_liveness_only",
)
TIME_BUCKETS = ("0_5", "exact_5", "5_10", "exact_10", "10_30", "exact_30", "30_plus")
REMINDER_HISTORY_STATES = ("none", "ack_reminder", "progress_reminder", "repeated_progress_reminder")

TIME_BUCKET_SECONDS = {
    "0_5": 240,
    "exact_5": 300,
    "5_10": 420,
    "exact_10": 600,
    "10_30": 1200,
    "exact_30": 1800,
    "30_plus": 2400,
}
PROGRESS_STATE_SECONDS = {
    "same_lease_fresh": 240,
    "same_lease_stale_10_30": 1200,
    "same_lease_stale_30_plus": 2400,
}


@dataclass(frozen=True)
class LivenessCase:
    role: str
    ack_state: str
    result_state: str
    progress_state: str
    legacy_pollution: str
    time_bucket: str
    reminder_history: str

    @property
    def case_id(self) -> str:
        return ".".join(
            (
                self.role,
                self.ack_state,
                self.result_state,
                self.progress_state,
                self.legacy_pollution,
                self.time_bucket,
                self.reminder_history,
            )
        )


def iter_cases() -> Iterable[LivenessCase]:
    for values in product(
        ROLES,
        ACK_STATES,
        RESULT_STATES,
        PROGRESS_STATES,
        LEGACY_POLLUTION_STATES,
        TIME_BUCKETS,
        REMINDER_HISTORY_STATES,
    ):
        yield LivenessCase(*values)


def required_case_count() -> int:
    return (
        len(ROLES)
        * len(ACK_STATES)
        * len(RESULT_STATES)
        * len(PROGRESS_STATES)
        * len(LEGACY_POLLUTION_STATES)
        * len(TIME_BUCKETS)
        * len(REMINDER_HISTORY_STATES)
    )


def _bucket_seconds(bucket: str) -> int:
    return TIME_BUCKET_SECONDS[bucket]


def _timestamp_age(seconds: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat()


def expected_wait_reaction(case: LivenessCase) -> dict[str, Any]:
    if case.result_state == "valid_final_result":
        return {
            "reaction": "final_result_wins",
            "decision": "not_waiting",
            "state": "final_result_accepted",
            "runtime_executable": False,
            "legacy_pollution_ignored": case.legacy_pollution != "none",
        }
    if case.result_state == "invalid_final_result":
        return {
            "reaction": "mechanical_result_block",
            "decision": "recover_packet",
            "state": "mechanical_contract_blocked",
            "runtime_executable": False,
            "legacy_pollution_ignored": case.legacy_pollution != "none",
        }
    if case.progress_state == "after_accepted_result":
        return {
            "reaction": "invalid_setup",
            "decision": "not_applicable",
            "state": "progress_after_accepted_result_requires_valid_final_result",
            "runtime_executable": False,
            "legacy_pollution_ignored": case.legacy_pollution != "none",
        }
    if case.ack_state == "no_ack":
        elapsed = _bucket_seconds(case.time_bucket)
        if elapsed >= 600:
            return {
                "reaction": "replace_missing_ack",
                "decision": "reissue_or_replace_lease",
                "state": "ack_replacement_due",
                "runtime_executable": True,
                "legacy_pollution_ignored": case.legacy_pollution != "none",
            }
        if elapsed >= 300:
            return {
                "reaction": "remind_missing_ack",
                "decision": "wait_for_ack",
                "state": "ack_reminder_due",
                "runtime_executable": True,
                "legacy_pollution_ignored": case.legacy_pollution != "none",
            }
        return {
            "reaction": "wait_missing_ack",
            "decision": "wait_for_ack",
            "state": "wait_patrol",
            "runtime_executable": True,
            "legacy_pollution_ignored": case.legacy_pollution != "none",
        }

    if case.progress_state in PROGRESS_STATE_SECONDS:
        elapsed = PROGRESS_STATE_SECONDS[case.progress_state]
    else:
        elapsed = _bucket_seconds(case.time_bucket)
    if elapsed >= 1800:
        return {
            "reaction": "replace_stale_progress",
            "decision": "reissue_or_replace_lease",
            "state": "progress_replacement_due",
            "runtime_executable": True,
            "legacy_pollution_ignored": case.legacy_pollution != "none",
        }
    if elapsed >= 600:
        return {
            "reaction": "remind_stale_progress",
            "decision": "wait_for_result",
            "state": "progress_reminder_due",
            "runtime_executable": True,
            "legacy_pollution_ignored": case.legacy_pollution != "none",
        }
    return {
        "reaction": "wait_fresh_evidence",
        "decision": "wait_for_result",
        "state": "grace_wait",
        "runtime_executable": True,
        "legacy_pollution_ignored": case.legacy_pollution != "none",
    }


def _inject_legacy_pollution(ledger: dict[str, Any], lease_id: str, packet_id: str, pollution: str) -> None:
    lease = ledger["leases"][lease_id]
    if pollution == "none":
        return
    if pollution == "timeout_unknown":
        lease["liveness_status"] = "timeout_unknown"
        lease["liveness_checked_at"] = _timestamp_age(60)
    elif pollution == "host_liveness_timeout":
        lease["host_liveness_history"] = [{"status": "timeout_unknown", "checked_at": _timestamp_age(60)}]
        ledger["host_liveness_reports"] = {
            "host-liveness-legacy": {
                "packet_id": packet_id,
                "lease_id": lease_id,
                "status": "timeout_unknown",
            }
        }
    elif pollution == "bounded_wait_timeout":
        ledger["lifecycle_guard_config"]["bounded_wait_result"] = "timeout_unknown"
        ledger["lifecycle_guard_config"]["result_liveness_seconds"] = 0
    elif pollution == "last_liveness_only":
        lease["last_liveness_status"] = "lost"


def _other_role(role: str) -> str:
    return "reviewer" if role != "reviewer" else "worker"


def materialize_runtime_case(case: LivenessCase) -> dict[str, Any]:
    if not expected_wait_reaction(case)["runtime_executable"]:
        raise ValueError(f"case is not runtime-executable: {case.case_id}")
    ledger = runtime.new_ledger("Liveness evidence matrix", "All waits use ACK/progress evidence only.")
    ledger["startup_intake"] = {
        "schema_version": "black_box_flowpilot.startup_intake.v1",
        "status": "accepted",
        "startup_answers": {
            runtime.BACKGROUND_COLLABORATION_ACK_FIELD: True,
        },
    }
    runtime.create_route(ledger, "Route", ["Exercise liveness wait"])
    packet_id = packets.issue_packet(ledger, case.role, "Exercise liveness wait", "SEALED_TASK_BODY")
    lease_id = runtime.lease_agent(ledger, case.role, agent_id=f"{case.role}-agent")
    runtime.assign_packet(ledger, packet_id, lease_id)
    ledger["leases"][lease_id]["created_at"] = _timestamp_age(_bucket_seconds(case.time_bucket))

    if case.ack_state != "no_ack":
        runtime.ack_lease(ledger, lease_id, packet_id)
        ledger["leases"][lease_id]["ack_received_at"] = _timestamp_age(_bucket_seconds(case.time_bucket))

    if case.progress_state in PROGRESS_STATE_SECONDS:
        runtime.record_progress(ledger, lease_id, packet_id, "still_working")
        ledger["leases"][lease_id]["last_progress_at"] = _timestamp_age(PROGRESS_STATE_SECONDS[case.progress_state])
    elif case.progress_state == "wrong_lease":
        wrong_lease_id = f"{lease_id}-wrong"
        ledger["leases"][wrong_lease_id] = {
            "lease_id": wrong_lease_id,
            "packet_id": f"{packet_id}-wrong",
            "responsibility": _other_role(case.role),
            "agent_id": "wrong-agent",
            "status": "closed",
            "ack_received": True,
            "ack_received_at": _timestamp_age(60),
            "last_progress_at": _timestamp_age(60),
            "progress_count": 1,
        }
    elif case.progress_state == "wrong_packet":
        wrong_packet = f"{packet_id}-wrong"
        lease = ledger["leases"][lease_id]
        lease["wrong_packet_progress_evidence"] = {
            "packet_id": wrong_packet,
            "status": "still_working",
            "recorded_at": _timestamp_age(60),
        }

    _inject_legacy_pollution(ledger, lease_id, packet_id, case.legacy_pollution)
    guard = runtime.preview_lifecycle_guard(ledger, trigger="synthetic_liveness_cartesian")
    wait_recovery = guard.get("wait_recovery", {}) if isinstance(guard.get("wait_recovery"), dict) else {}
    return {
        "case_id": case.case_id,
        "decision": guard.get("decision"),
        "state": wait_recovery.get("state"),
        "replacement_eligible": wait_recovery.get("replacement_eligible"),
        "legacy_pollution": case.legacy_pollution,
        "wait_recovery": wait_recovery,
    }


def build_rows() -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for case in iter_cases():
        expected = expected_wait_reaction(case)
        rows.append(
            {
                "case_id": case.case_id,
                "model_id": MODEL_ID,
                "role": case.role,
                "ack_state": case.ack_state,
                "result_state": case.result_state,
                "progress_state": case.progress_state,
                "legacy_pollution": case.legacy_pollution,
                "time_bucket": case.time_bucket,
                "reminder_history": case.reminder_history,
                "expected_reaction": expected["reaction"],
                "expected_decision": expected["decision"],
                "expected_state": expected["state"],
                "runtime_executable": expected["runtime_executable"],
                "legacy_pollution_ignored": expected["legacy_pollution_ignored"],
                "coverage_shard_id": (
                    f"{MODEL_ID}:{case.role}:{case.ack_state}:{case.result_state}:"
                    f"{case.progress_state}:{case.legacy_pollution}"
                ),
            }
        )
    return tuple(rows)


def build_report() -> dict[str, Any]:
    rows = build_rows()
    by_reaction: dict[str, int] = {}
    for row in rows:
        by_reaction[row["expected_reaction"]] = by_reaction.get(row["expected_reaction"], 0) + 1
    return {
        "ok": len(rows) == required_case_count() and all(row["expected_reaction"] for row in rows),
        "model_id": MODEL_ID,
        "required_case_count": required_case_count(),
        "row_count": len(rows),
        "dimensions": {
            "roles": list(ROLES),
            "ack_states": list(ACK_STATES),
            "result_states": list(RESULT_STATES),
            "progress_states": list(PROGRESS_STATES),
            "legacy_pollution_states": list(LEGACY_POLLUTION_STATES),
            "time_buckets": list(TIME_BUCKETS),
            "reminder_history_states": list(REMINDER_HISTORY_STATES),
        },
        "by_reaction": dict(sorted(by_reaction.items())),
        "runtime_executable_count": sum(1 for row in rows if row["runtime_executable"]),
        "legacy_pollution_case_count": sum(1 for row in rows if row["legacy_pollution"] != "none"),
        "rows": rows,
    }
