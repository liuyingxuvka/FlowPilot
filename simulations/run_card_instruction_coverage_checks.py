"""Run checks for FlowPilot card instruction coverage."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import card_instruction_coverage_model as model


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
RESULTS_PATH = ROOT / "card_instruction_coverage_results.json"


def explore_actual_cards() -> dict[str, object]:
    cards = model.collect_card_facts(PROJECT_ROOT)
    router_facts = model.collect_router_facts(PROJECT_ROOT)
    state = model.State()
    labels: list[str] = []
    states_seen = 1

    while state.status == "checking":
        transitions = tuple(model.next_safe_states(state, cards, router_facts))
        if len(transitions) != 1:
            return {
                "ok": False,
                "state_count": states_seen,
                "labels": labels,
                "failures": [f"expected exactly one deterministic coverage transition, got {len(transitions)}"],
                "checked_count": len(state.checked),
                "card_count": len(cards),
                "orphan_card_files": list(router_facts.orphan_card_files),
            }
        transition = transitions[0]
        labels.append(transition.label)
        state = transition.state
        states_seen += 1

    failures = list(state.failures) + list(model.invariant_failures(state))
    return {
        "ok": state.status == "complete" and not failures,
        "status": state.status,
        "state_count": states_seen,
        "labels": labels,
        "checked_count": len(state.checked),
        "card_count": len(cards),
        "active_card_count": len(router_facts.active_card_ids),
        "failures": failures,
        "orphan_card_files": list(router_facts.orphan_card_files),
        "router_sequence_manifest_errors": list(router_facts.sequence_manifest_errors),
        "external_card_flag_errors": list(router_facts.external_card_flag_errors),
        "live_context_errors": list(router_facts.live_context_errors),
    }


def check_hazards() -> dict[str, object]:
    results: dict[str, object] = {}
    ok = True
    for name, card in model.hazard_cards().items():
        failures = model.card_failures(card)
        detected = bool(failures)
        results[name] = {
            "detected": detected,
            "failures": list(failures),
            "card": asdict(card),
        }
        ok = ok and detected
    return {"ok": ok, "hazards": results}


def main() -> int:
    actual = explore_actual_cards()
    hazards = check_hazards()
    result = {
        "ok": bool(actual["ok"]) and bool(hazards["ok"]),
        "actual_card_graph": actual,
        "hazard_checks": hazards,
    }
    RESULTS_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
