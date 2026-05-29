"""Controller wait receipt audit helpers.

The audit is metadata-only: it scans Controller-visible runtime ledgers,
status packets, envelopes, and router-authored notices to distinguish ordinary
waiting from stale control-plane conditions. It must not read sealed work
bodies or judge work quality.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flowpilot_router_io import read_json_if_exists
from flowpilot_router_controller_wait_audit_scanners import (
    _as_str_set,
    _current_wait_fingerprint,
    _expected_path_set,
    _has_wait,
    _scan_controller_actions,
    _scan_packets,
    _scan_return_ledger,
    _scan_role_outputs,
    _scan_run_events,
    _split_roles,
)


CONTROLLER_WAIT_RECEIPT_AUDIT_SCHEMA = "flowpilot.controller_wait_receipt_audit.v1"

NO_FORMAL_RETURN_SEEN = "no_formal_return_seen"
FORMAL_RETURN_READY = "formal_return_ready"
FORMAL_RETURN_SEEN_BUT_WAIT_NOT_RELEASED = "formal_return_seen_but_wait_not_released"
RESULT_ENVELOPE_SEEN_BUT_NO_NEXT_NOTICE = "result_envelope_seen_but_no_next_notice"
ASIDE_CLAIM_WITHOUT_FORMAL_RETURN = "aside_claim_without_formal_return"
FORMAL_RETURN_MALFORMED = "formal_return_malformed"
NOT_APPLICABLE = "not_applicable"

def controller_wait_receipt_audit(
    project_root: Path,
    run_root: Path,
    current_wait: dict[str, Any] | None,
    *,
    run_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    current_wait = current_wait if isinstance(current_wait, dict) else {}
    if not _has_wait(current_wait):
        return {
            "schema_version": CONTROLLER_WAIT_RECEIPT_AUDIT_SCHEMA,
            "classification": NOT_APPLICABLE,
            "current_wait_present": False,
            "checked_surfaces": [],
            "matched_paths": [],
            "metadata_only": True,
            "sealed_body_reads_allowed": False,
            "work_quality_judgment_allowed": False,
        }

    roles = set()
    for key in ("waiting_for_role", "target_role", "to_role"):
        roles.update(_split_roles(current_wait.get(key)))
    events = _as_str_set(current_wait.get("allowed_external_events"))
    paths = _expected_path_set(current_wait)
    packet_ids = _as_str_set(current_wait.get("packet_id"), current_wait.get("active_packet_id"))
    for path in paths:
        parts = Path(path.replace("\\", "/")).parts
        if "packets" in parts:
            idx = parts.index("packets")
            if len(parts) > idx + 1:
                packet_ids.add(parts[idx + 1])

    checked_surfaces = [
        "return_event_ledger",
        "role_output_ledger",
        "role_output_status",
        "packet_ledger",
        "packet_result_envelope",
        "controller_next_action_notice",
        "run_state.events",
        "controller_action_ledger",
    ]
    formal_matches: list[dict[str, Any]] = []
    result_matches: list[dict[str, Any]] = []
    notice_matches: list[dict[str, Any]] = []
    aside_matches: list[dict[str, Any]] = []

    return_matches, return_asides = _scan_return_ledger(run_root, roles=roles, events=events, paths=paths, packet_ids=packet_ids)
    role_matches, role_asides = _scan_role_outputs(run_root, roles=roles, events=events, paths=paths, packet_ids=packet_ids)
    packet_matches, packet_result_matches, packet_notice_matches, packet_asides = _scan_packets(project_root, run_root, roles=roles, events=events, paths=paths, packet_ids=packet_ids)
    state_matches = _scan_run_events(run_state or read_json_if_exists(run_root / "router_state.json"), roles=roles, events=events, paths=paths, packet_ids=packet_ids)
    controller_action_matches = _scan_controller_actions(run_root)

    formal_matches.extend(return_matches)
    formal_matches.extend(role_matches)
    formal_matches.extend(packet_matches)
    formal_matches.extend(state_matches)
    result_matches.extend(packet_result_matches)
    notice_matches.extend(packet_notice_matches)
    aside_matches.extend(return_asides)
    aside_matches.extend(role_asides)
    aside_matches.extend(packet_asides)

    malformed = [item for item in formal_matches + notice_matches if item.get("malformed")]
    formal_seen = bool(formal_matches)
    result_seen = bool(result_matches)
    notice_seen = bool(notice_matches)
    controller_action_ready = bool(controller_action_matches)
    aside_claim_seen = bool(aside_matches)

    if malformed:
        classification = FORMAL_RETURN_MALFORMED
    elif result_seen and not notice_seen and not controller_action_ready:
        classification = RESULT_ENVELOPE_SEEN_BUT_NO_NEXT_NOTICE
    elif formal_seen and (notice_seen or controller_action_ready):
        classification = FORMAL_RETURN_READY
    elif formal_seen:
        classification = FORMAL_RETURN_SEEN_BUT_WAIT_NOT_RELEASED
    elif aside_claim_seen:
        classification = ASIDE_CLAIM_WITHOUT_FORMAL_RETURN
    else:
        classification = NO_FORMAL_RETURN_SEEN

    control_plane_stuck = classification in {
        FORMAL_RETURN_SEEN_BUT_WAIT_NOT_RELEASED,
        RESULT_ENVELOPE_SEEN_BUT_NO_NEXT_NOTICE,
        FORMAL_RETURN_MALFORMED,
    }
    matched_paths = sorted(
        {
            str(item.get("path"))
            for item in formal_matches + notice_matches + aside_matches + controller_action_matches
            if item.get("path")
        }
    )
    return {
        "schema_version": CONTROLLER_WAIT_RECEIPT_AUDIT_SCHEMA,
        "classification": classification,
        "current_wait_present": True,
        "current_wait": _current_wait_fingerprint(current_wait),
        "expected_events": sorted(events),
        "expected_roles": sorted(roles),
        "expected_paths": sorted(paths),
        "expected_packet_ids": sorted(packet_ids),
        "checked_surfaces": checked_surfaces,
        "matched_paths": matched_paths,
        "metadata_only": True,
        "sealed_body_reads_allowed": False,
        "work_quality_judgment_allowed": False,
        "formal_return_seen": formal_seen,
        "formal_return_malformed": bool(malformed),
        "result_envelope_seen": result_seen,
        "next_action_notice_seen": notice_seen,
        "controller_action_ready": controller_action_ready,
        "aside_claim_seen": aside_claim_seen,
        "control_plane_stuck": control_plane_stuck,
        "controller_should_reenter_ledger": classification == FORMAL_RETURN_READY,
        "user_visible_message_required": control_plane_stuck,
        "authority_boundary": {
            "metadata_only": True,
            "sealed_body_reads_allowed": False,
            "work_quality_judgment_allowed": False,
            "controller_aside_satisfies_wait": False,
            "controller_approval_allowed": False,
        },
        "matches": {
            "formal": formal_matches[:10],
            "result_envelopes": result_matches[:10],
            "next_action_notices": notice_matches[:10],
            "controller_actions": controller_action_matches[:10],
            "aside_claims": aside_matches[:10],
            "malformed": malformed[:10],
        },
    }


__all__ = [
    "ASIDE_CLAIM_WITHOUT_FORMAL_RETURN",
    "CONTROLLER_WAIT_RECEIPT_AUDIT_SCHEMA",
    "FORMAL_RETURN_MALFORMED",
    "FORMAL_RETURN_READY",
    "FORMAL_RETURN_SEEN_BUT_WAIT_NOT_RELEASED",
    "NO_FORMAL_RETURN_SEEN",
    "NOT_APPLICABLE",
    "RESULT_ENVELOPE_SEEN_BUT_NO_NEXT_NOTICE",
    "controller_wait_receipt_audit",
]
