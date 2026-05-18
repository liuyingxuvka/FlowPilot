"""Static protocol tables shared by FlowPilot router runtime boundaries."""

from __future__ import annotations


RUN_TERMINAL_STATUSES = {"stopped_by_user", "cancelled_by_user", "protocol_dead_end", "completed", "closed", "stopped"}

MAIL_SEQUENCE: tuple[dict[str, str], ...] = (
    {
        "flag": "user_intake_delivered_to_pm",
        "label": "user_intake_delivered_to_pm",
        "mail_id": "user_intake",
        "to_role": "project_manager",
        "requires_flag": "startup_activation_approved",
    },
)


def terminal_statuses() -> frozenset[str]:
    return frozenset(RUN_TERMINAL_STATUSES)


def mail_sequence_entry(mail_id: str) -> dict[str, str] | None:
    for entry in MAIL_SEQUENCE:
        if entry.get("mail_id") == mail_id:
            return dict(entry)
    return None
