"""Controller process-aside metadata helpers.

The aside is a short Controller-facing process/status note. It is deliberately
metadata, not report content, evidence, a decision, or a Router event source.
"""

from __future__ import annotations

from typing import Any


CONTROLLER_PROCESS_ASIDE_SCHEMA = "flowpilot.controller_process_aside.v1"
CONTROLLER_PROCESS_ASIDE_CONTRACT_SCHEMA = "flowpilot.controller_process_aside_contract.v1"
CONTROLLER_PROCESS_ASIDE_FIELD = "controller_aside"
CONTROLLER_PROCESS_ASIDE_MAX_LEN = 240
CONTROLLER_PROCESS_ASIDE_MAX_LINES = 3


def controller_process_aside_contract() -> dict[str, Any]:
    return {
        "schema_version": CONTROLLER_PROCESS_ASIDE_CONTRACT_SCHEMA,
        "field_name": CONTROLLER_PROCESS_ASIDE_FIELD,
        "optional": True,
        "target": "controller_only",
        "purpose": "brief_process_status_note",
        "max_chars": CONTROLLER_PROCESS_ASIDE_MAX_LEN,
        "max_non_empty_lines": CONTROLLER_PROCESS_ASIDE_MAX_LINES,
        "content_guidance": (
            "Use for short process/status context such as started, still working, "
            "submitted, mechanically blocked, retrying, or waiting for Router. "
            "Do not put formal work content, evidence, findings, recommendations, "
            "decisions, approvals, or report body details here."
        ),
        "authority_boundary": {
            "not_formal_evidence": True,
            "not_decision_or_approval": True,
            "does_not_satisfy_wait": True,
            "does_not_authorize_progress": True,
            "does_not_create_router_event": True,
            "worker_to_worker_visible": False,
            "router_semantic_inspection_allowed": False,
            "router_may_preserve_shape_only": True,
        },
    }


def validate_controller_aside_text(text: str | None) -> str | None:
    if text is None:
        return None
    lines = [line.strip() for line in str(text).strip().splitlines() if line.strip()]
    if not lines:
        return None
    if len(lines) > CONTROLLER_PROCESS_ASIDE_MAX_LINES:
        raise ValueError(
            f"controller_aside must use {CONTROLLER_PROCESS_ASIDE_MAX_LINES} non-empty lines or fewer"
        )
    normalized = "\n".join(lines)
    if len(normalized) > CONTROLLER_PROCESS_ASIDE_MAX_LEN:
        raise ValueError(
            f"controller_aside must be {CONTROLLER_PROCESS_ASIDE_MAX_LEN} characters or fewer"
        )
    return normalized


def build_controller_aside(
    text: str | None,
    *,
    from_role: str,
    source: str,
    to_role: str = "controller",
) -> dict[str, Any] | None:
    normalized = validate_controller_aside_text(text)
    if normalized is None:
        return None
    return {
        "schema_version": CONTROLLER_PROCESS_ASIDE_SCHEMA,
        "from_role": from_role,
        "to_role": to_role,
        "source": source,
        "text": normalized,
        "purpose": "brief_process_status_note",
        "visibility": "controller_only",
        "not_formal_evidence": True,
        "not_decision_or_approval": True,
        "does_not_satisfy_wait": True,
        "does_not_authorize_progress": True,
        "does_not_create_router_event": True,
        "worker_to_worker_visible": False,
        "router_semantic_inspection_allowed": False,
    }
