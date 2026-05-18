"""Runtime manifest and prompt contract checks."""

from __future__ import annotations

import json

from .common import ROOT


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
                        and "flowpilot_router.py" in card_text
                        and "runtime_context:" in card_text
                        and "router delivery envelope" in card_text
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
            "active health-and-continuation aid",
            "current_wait.wait_class",
            "ack",
            "three-minute reminder",
            "ten-minute blocker",
            "report_result",
            "fresh liveness check",
            "Do not trust an old \"alive\" status",
            "controller_local_action",
            "do not remind yourself",
            "controller_table_prompt",
            "top to bottom",
            "as long as FlowPilot is still running",
            "continuous_controller_standby",
            "active foreground duty",
            "sync the visible Codex plan",
            "finishable checklist item",
            "daemon-owned startup rows",
            "Router's scheduler ledger owns ordering",
            "return to top-to-bottom row processing",
            "must not mark the visible plan item done",
            "timeout_still_waiting",
            "diagnostic-only",
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
        router_source = (ROOT / "skills/flowpilot/assets/flowpilot_router.py").read_text(encoding="utf-8")
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
