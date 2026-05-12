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

USER_PERSPECTIVE_CARD_CHECKS = {
    "skills/flowpilot/assets/runtime_kit/cards/roles/human_like_reviewer.md": (
        r"final-user intent",
        r"product usefulness",
        r"Existence evidence is not enough",
    ),
    "skills/flowpilot/assets/runtime_kit/cards/roles/project_manager.md": (
        r"final-user intent and product usefulness self-check",
        r"decision-support",
    ),
    "skills/flowpilot/assets/runtime_kit/cards/reviewer/worker_result_review.md": (
        r"final-user usefulness",
        r"file existence",
    ),
    "skills/flowpilot/assets/runtime_kit/cards/reviewer/parent_backward_replay.md": (
        r"parent-level user-facing outcome",
    ),
    "skills/flowpilot/assets/runtime_kit/cards/reviewer/final_backward_replay.md": (
        r"not merely a clean ledger",
        r"hard user-intent failures",
    ),
    "skills/flowpilot/assets/runtime_kit/cards/reviewer/evidence_quality_review.md": (
        r"user-facing quality",
        r"file existence",
    ),
    "skills/flowpilot/assets/runtime_kit/cards/reviewer/product_architecture_challenge.md": (
        r"final product usefulness",
        r"PM decision-support",
    ),
    "skills/flowpilot/assets/runtime_kit/cards/reviewer/node_acceptance_plan_review.md": (
        r"final-user usefulness",
        r"evidence",
    ),
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_product_architecture.md": (
        r"final-user intent and product usefulness assumptions",
    ),
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_node_acceptance_plan.md": (
        r"final-user intent and product usefulness self-check",
        r"nonessential improvement",
    ),
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_route_skeleton.md": (
        r"PM user-intent self-check",
        r"product usefulness failures",
    ),
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_final_ledger.md": (
        r"final-user intent and delivered-product usefulness claims",
    ),
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_closure.md": (
        r"final_user_outcome_replay",
        r"unverifiable user-facing quality claim",
    ),
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
    for relative_path, patterns in USER_PERSPECTIVE_CARD_CHECKS.items():
        card_path = root / relative_path
        if not card_path.exists():
            issues.append(
                {
                    "card_id": "user_perspective_propagation",
                    "role": "targeted",
                    "missing_file": str(card_path),
                }
            )
            continue
        text = card_path.read_text(encoding="utf-8")
        missing = [
            pattern
            for pattern in patterns
            if not _has(text, pattern)
        ]
        if missing:
            issues.append(
                {
                    "card_id": "user_perspective_propagation",
                    "role": "targeted",
                    "path": relative_path,
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
