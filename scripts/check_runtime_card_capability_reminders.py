"""Check that runtime cards keep role capability reminders visible."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


ROLE_CHECKS = {
    "pm": {
        "role_work": r"pm_registers_role_work_request|role_work_request|ask another FlowPilot role",
        "allowed_events": r"allowed_external_events",
        "repair_choices": r"route mutation|reissue|quarantine|user stop|stop for user",
        "suggestion_ledger": r"PM suggestion|pm_suggestion|suggestion/blocker ledger",
    },
    "reviewer": {
        "no_direct_role_contact": r"Do not contact workers or officers directly|cannot.*contact.*direct",
        "pm_routes_needed_work": r"PM suggestion|PM to route|blocker",
        "finding_classes": r"hard blockers?.*future requirements?.*nonblocking notes?",
    },
    "officer": {
        "pm_routes_needed_work": r"structured blocker or PM suggestion|PM suggestion",
        "no_pm_decision": r"Do not approve routes or make PM decisions|PM still owns|PM owns",
    },
    "worker": {
        "packet_scope": r"packet scope|bounded scope|scope",
        "no_role_decision": r"PM|Reviewer|Officer",
        "self_check": r"Self-Check|self-check",
    },
}


def _has(text: str, pattern: str) -> bool:
    return bool(re.search(pattern, text, flags=re.I | re.S))


def _role_for_card(card: dict[str, Any]) -> str | None:
    audience = card.get("audience")
    kind = card.get("kind")
    card_id = card.get("id")
    if audience == "project_manager" and kind in {
        "phase",
        "event",
        "resume",
        "startup_gate",
        "duty",
        "phase_map",
    }:
        return "pm"
    if audience == "human_like_reviewer" and kind == "reviewer_gate":
        return "reviewer"
    if kind == "officer_gate":
        return "officer"
    if card_id in {"worker.research_report", "worker_a.core", "worker_b.core"}:
        return "worker"
    return None


def check(root: Path = ROOT) -> dict[str, Any]:
    base = root / "skills" / "flowpilot" / "assets" / "runtime_kit"
    manifest_path = base / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    issues: list[dict[str, Any]] = []
    checked = 0
    for card in manifest.get("cards", []):
        if not isinstance(card, dict):
            continue
        role = _role_for_card(card)
        if role is None:
            continue
        checked += 1
        card_path = base / str(card.get("path") or "")
        if not card_path.exists():
            issues.append(
                {"card_id": card.get("id"), "role": role, "missing_file": str(card_path)}
            )
            continue
        text = card_path.read_text(encoding="utf-8")
        missing = [
            name
            for name, pattern in ROLE_CHECKS[role].items()
            if not _has(text, pattern)
        ]
        if missing:
            issues.append(
                {
                    "card_id": card.get("id"),
                    "role": role,
                    "path": str(card_path.relative_to(root)),
                    "missing": missing,
                }
            )
    return {
        "ok": not issues,
        "checked_cards": checked,
        "issue_count": len(issues),
        "issues": issues,
    }


def main() -> int:
    result = check(ROOT)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
