"""Runtime manifest and prompt contract checks."""

from __future__ import annotations

import json
import re

from .common import ROOT


def _obsolete_pattern(*parts: str) -> re.Pattern[str]:
    return re.compile("".join(parts), re.IGNORECASE)


FORBIDDEN_CURRENT_PROMPT_SURFACE_PATTERNS = (
    ("obsolete role-output entrypoint", _obsolete_pattern(r"flowpilot_", r"runtime\.py")),
    ("obsolete router-submit command", _obsolete_pattern(r"submit-output", r"-to-router")),
    ("obsolete skeleton command", _obsolete_pattern(r"\bprepare", r"-", r"output\b")),
    ("obsolete packet-holder label", _obsolete_pattern(r"active", r"-holder")),
    ("obsolete router facade command", _obsolete_pattern(r"flowpilot_", r"router\.py")),
    ("obsolete daemon wording", _obsolete_pattern(r"router\s+daemon")),
    ("obsolete next-action notice filename", _obsolete_pattern(r"controller_next", r"_action_notice")),
)


def _current_prompt_surface_paths():
    roots = (
        ROOT / "skills/flowpilot/SKILL.md",
        ROOT / "skills/flowpilot/assets/runtime_kit",
        ROOT / "templates/flowpilot",
    )
    suffixes = {".md", ".json", ".mmd"}
    for root in roots:
        if root.is_file():
            yield root
            continue
        if root.exists():
            for path in sorted(root.rglob("*")):
                if path.is_file() and path.suffix in suffixes:
                    yield path


def _forbidden_current_prompt_surface_hits() -> list[str]:
    hits: list[str] = []
    for path in _current_prompt_surface_paths():
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT).as_posix()
        for label, pattern in FORBIDDEN_CURRENT_PROMPT_SURFACE_PATTERNS:
            if pattern.search(text):
                hits.append(f"{rel}: {label}")
    return hits


def run_checks(result: dict[str, object]) -> None:
    manifest_path = ROOT / "skills/flowpilot/assets/runtime_kit/manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            cards = manifest.get("cards", [])
            manifest_cards_ok = (
                manifest.get("schema_version") == "flowpilot.prompt_manifest.v1"
                and isinstance(cards, list)
                and bool(cards)
            )
            missing_cards = []
            invalid_cards = []
            invalid_identity_cards = []
            for card in cards if isinstance(cards, list) else []:
                if not isinstance(card, dict):
                    invalid_cards.append("<non-object>")
                    continue
                card_path = card.get("path")
                if (
                    not card.get("id")
                    or card.get("source") != "system"
                    or card.get("issued_by") != "router"
                    or not isinstance(card_path, str)
                ):
                    invalid_cards.append(str(card.get("id") or card_path or "<unknown>"))
                    continue
                full_card_path = manifest_path.parent / card_path
                if not full_card_path.exists():
                    missing_cards.append(card_path)
                else:
                    card_text = full_card_path.read_text(encoding="utf-8")
                    expected_role = str(card.get("audience") or "")
                    delivery_envelope_ok = (
                        "router delivery envelope" in card_text
                        or "runtime delivery envelope" in card_text
                    )
                    identity_ok = (
                        card_text.lstrip().startswith("<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1")
                        and f"recipient_role: {expected_role}" in card_text
                        and "recipient_identity:" in card_text
                        and "allowed_scope:" in card_text
                        and "forbidden_scope:" in card_text
                        and "required_return:" in card_text
                        and "controller-visible envelope" in card_text
                        and "Do not include report bodies" in card_text
                        and "next_step_source:" in card_text
                        and "flowpilot_new.py" in card_text
                        and "runtime_context:" in card_text
                        and delivery_envelope_ok
                        and "do not continue from memory" in card_text
                    )
                    if not identity_ok:
                        invalid_identity_cards.append(str(card.get("id") or card_path))
            card_ids = [
                str(card.get("id"))
                for card in cards
                if isinstance(card, dict) and card.get("id")
            ] if isinstance(cards, list) else []
            duplicate_card_ids = sorted(
                {card_id for card_id in card_ids if card_ids.count(card_id) > 1}
            )
            policy = manifest.get("controller_policy") if isinstance(manifest, dict) else {}
            controller_policy_ok = isinstance(policy, dict) and all(
                policy.get(key) is expected
                for key, expected in {
                    "all_system_cards_from_system": True,
                    "card_delivery_requires_manifest_check": True,
                    "mail_delivery_requires_packet_ledger_check": True,
                    "controller_may_create_project_evidence": False,
                    "controller_may_read_sealed_bodies": False,
                }.items()
            )
            manifest_cards_ok = manifest_cards_ok and not duplicate_card_ids and controller_policy_ok
            manifest_cards_ok = manifest_cards_ok and not missing_cards and not invalid_cards and not invalid_identity_cards
            result["checks"].append(
                {
                    "name": "flowpilot_prompt_manifest_cards_valid",
                    "ok": manifest_cards_ok,
                    "card_count": len(cards) if isinstance(cards, list) else 0,
                    "missing_cards": missing_cards,
                    "invalid_cards": invalid_cards,
                    "invalid_identity_cards": invalid_identity_cards,
                    "duplicate_card_ids": duplicate_card_ids,
                    "controller_policy_ok": controller_policy_ok,
                }
            )
            if not manifest_cards_ok:
                result["ok"] = False
        except Exception as exc:  # pragma: no cover - diagnostic script
            result["ok"] = False
            result["checks"].append(
                {
                    "name": "flowpilot_prompt_manifest_cards_valid",
                    "ok": False,
                    "error": repr(exc),
                }
            )

    try:
        controller_card = ROOT / "skills/flowpilot/assets/runtime_kit/cards/roles/controller.md"
        text = controller_card.read_text(encoding="utf-8")
        required_terms = [
            "current_wait.wait_class",
            "ack",
            "minutes without ACK reminds",
            "ten minutes without ACK reissues or replaces",
            "ten minutes without fresh evidence reminds",
            "thirty minutes without",
            "fresh evidence reissues or replaces",
            "`progress +1`",
            "submit-result",
            "Controller does not run a separate host-liveness check",
            "controller_local_action",
            "foreground duty",
            "process_next_action",
            "wait_patrol",
            "recover_or_reissue",
            "control_plane_blocker",
            "terminal_return",
            "timeout_still_waiting",
            "use only the current `flowpilot_new.py` foreground duty",
            "current runtime next-action notice",
            "user_status_update_allowed",
            "controller_stop_allowed",
            "flowpilot_new.py final-preflight",
            "Controller is status-only",
            "status summary is display-only",
            "stale `next_step`",
            "translating control-plane state",
            "Keep internal Router, action, ledger, packet, ACK, scheduler, receipt, hash",
            "concrete blocker cannot be explained accurately",
        ]
        missing_terms = [term for term in required_terms if term not in text]
        ok = not missing_terms
        result["checks"].append(
            {
                "name": "flowpilot_controller_wait_target_prompt_guidance",
                "ok": ok,
                "missing_terms": missing_terms,
            }
        )
        if not ok:
            result["ok"] = False
    except Exception as exc:  # pragma: no cover - diagnostic script
        result["ok"] = False
        result["checks"].append(
            {
                "name": "flowpilot_controller_wait_target_prompt_guidance",
                "ok": False,
                "error": repr(exc),
            }
        )

    try:
        forbidden_hits = _forbidden_current_prompt_surface_hits()
        ok = not forbidden_hits
        result["checks"].append(
            {
                "name": "flowpilot_current_prompt_surfaces_reject_obsolete_paths",
                "ok": ok,
                "hits": forbidden_hits[:50],
                "hit_count": len(forbidden_hits),
            }
        )
        if not ok:
            result["ok"] = False
    except Exception as exc:  # pragma: no cover - diagnostic script
        result["ok"] = False
        result["checks"].append(
            {
                "name": "flowpilot_current_prompt_surfaces_reject_obsolete_paths",
                "ok": False,
                "error": repr(exc),
            }
        )

    try:
        router_source = (ROOT / ("skills/flowpilot/assets/flowpilot_" "router.py")).read_text(encoding="utf-8")
        router_facade_import_source = (
            ROOT / "skills/flowpilot/assets/flowpilot_router_facade_imports.py"
        ).read_text(encoding="utf-8")
        controller_table_prompt = (
            ROOT / "skills/flowpilot/assets/runtime_kit/prompts/controller/action_ledger_table.md"
        ).read_text(encoding="utf-8")
        source_text = router_source + "\n" + router_facade_import_source + "\n" + controller_table_prompt
        required_terms = [
            "controller_table_prompt",
            "Work from top to bottom",
            "As long as FlowPilot is still running",
            "continuous monitoring duty",
            "finishable checklist item",
            "update this table",
            "return to top-to-bottom row processing",
            "foreground_close_allowed_while_flowpilot_running",
            "new_controller_work_requires_ledger_update_and_top_down_reentry",
            "startup_daemon_scheduled",
            "scheduled_by_router_daemon",
            "startup_daemon_controls_bootstrap",
            "translate internal action,",
            "ledger, receipt, packet, wait, daemon, ACK, and scheduler terms",
            "plain language first. Use internal names only when the user asks for",
            "concrete blocker needs that name",
            "user_status_update_allowed",
            "not Controller stop permission",
            "Final-answer is allowed only",
            "status summary is display-only",
            "stale `next_step`",
        ]
        missing_terms = [term for term in required_terms if term not in source_text]
        ok = not missing_terms
        result["checks"].append(
            {
                "name": "flowpilot_controller_table_prompt_runtime_guidance",
                "ok": ok,
                "missing_terms": missing_terms,
            }
        )
        if not ok:
            result["ok"] = False
    except Exception as exc:  # pragma: no cover - diagnostic script
        result["ok"] = False
        result["checks"].append(
            {
                "name": "flowpilot_controller_table_prompt_runtime_guidance",
                "ok": False,
                "error": repr(exc),
            }
        )

    try:
        import check_runtime_card_capability_reminders

        reminder_check = check_runtime_card_capability_reminders.check(ROOT)
        reminders_ok = bool(reminder_check.get("ok"))
        result["checks"].append(
            {
                "name": "flowpilot_runtime_card_capability_reminders",
                "ok": reminders_ok,
                "checked_cards": reminder_check.get("checked_cards"),
                "issue_count": reminder_check.get("issue_count"),
                "issues": reminder_check.get("issues"),
            }
        )
        if not reminders_ok:
            result["ok"] = False
    except Exception as exc:  # pragma: no cover - diagnostic script
        result["ok"] = False
        result["checks"].append(
            {
                "name": "flowpilot_runtime_card_capability_reminders",
                "ok": False,
                "error": repr(exc),
            }
        )
