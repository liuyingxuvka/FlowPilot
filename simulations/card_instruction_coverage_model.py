"""FlowGuard-style card instruction coverage model for FlowPilot.

This model checks the prompt-sufficiency failure class that plain route-state
models can miss: a router transition can be valid, while the card delivered to
the role does not tell that role what to do next or how to return to the
router-controlled flow.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable, NamedTuple

from flowguard import FunctionResult, InvariantResult


NEXT_STEP_SOURCE_FIELD = "next_step_source"
NEXT_STEP_ROUTER_FRAGMENT = "flowpilot_router.py"
PM_HISTORY_CONTEXT_REQUIRED_CARD_IDS = frozenset(
    {
        "pm.prior_path_context",
        "pm.route_skeleton",
        "pm.resume_decision",
        "pm.current_node_loop",
        "pm.node_acceptance_plan",
        "pm.review_repair",
        "pm.parent_segment_decision",
        "pm.evidence_quality_package",
        "pm.final_ledger",
        "pm.closure",
    }
)

ACTION_TERMS_BY_ROLE: dict[str, tuple[str, ...]] = {
    "bootloader": ("display", "return", "router", "do not infer"),
    "controller": ("router", "relay", "record", "check", "load", "call"),
    "project_manager": (
        "write",
        "record",
        "decide",
        "issue",
        "request",
        "build",
        "freeze",
        "activate",
        "complete",
        "choose",
        "verify",
        "mutate",
        "stop",
        "return",
    ),
    "human_like_reviewer": ("review", "check", "verify", "pass", "block", "return"),
    "process_flowguard_officer": ("model", "review", "check", "pass", "report", "return"),
    "product_flowguard_officer": ("model", "review", "check", "pass", "report", "return"),
    "worker_a": ("execute", "work", "return", "report", "result"),
    "worker_b": ("execute", "work", "return", "report", "result"),
}


@dataclass(frozen=True)
class CardFacts:
    card_id: str
    path: str
    role: str
    kind: str
    manifest_registered: bool
    router_active: bool
    identity_boundary: bool
    recipient_role_matches: bool
    required_return: bool
    envelope_only_return: bool
    chat_body_suppression: bool
    next_step_source: bool
    next_step_mentions_router: bool
    action_guidance: bool
    pm_history_context_guidance: bool


@dataclass(frozen=True)
class RouterFacts:
    active_card_ids: tuple[str, ...]
    active_role_by_card: tuple[tuple[str, str], ...]
    external_card_flag_errors: tuple[str, ...]
    sequence_manifest_errors: tuple[str, ...]
    orphan_card_files: tuple[str, ...]


@dataclass(frozen=True)
class State:
    status: str = "checking"  # checking | blocked | complete
    index: int = 0
    checked: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()


class Transition(NamedTuple):
    label: str
    state: State


def _load_router(project_root: Path) -> Any:
    assets_root = project_root / "skills" / "flowpilot" / "assets"
    router_path = assets_root / "flowpilot_router.py"
    sys.path.insert(0, str(assets_root))
    spec = importlib.util.spec_from_file_location("flowpilot_router_for_card_instruction_coverage", router_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load router module from {router_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _parse_identity_block(text: str) -> dict[str, str]:
    if "FLOWPILOT_IDENTITY_BOUNDARY_V1" not in text:
        return {}
    start = text.index("FLOWPILOT_IDENTITY_BOUNDARY_V1")
    end = text.find("-->", start)
    if end < 0:
        return {}
    block = text[start:end]
    fields: dict[str, str] = {}
    for raw_line in block.splitlines()[1:]:
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def _has_action_guidance(role: str, text: str) -> bool:
    terms = ACTION_TERMS_BY_ROLE.get(role, ("return", "record", "check"))
    lower = text.lower()
    return any(term in lower for term in terms)


def _has_pm_history_context_guidance(card_id: str, role: str, text: str) -> bool:
    if role != "project_manager" or card_id not in PM_HISTORY_CONTEXT_REQUIRED_CARD_IDS:
        return True
    lower = text.lower()
    has_context_pointer = "prior path context" in lower or "route-memory" in lower or "route_memory" in lower
    has_history_scope = "completed" in lower and "superseded" in lower and "stale" in lower
    return has_context_pointer and has_history_scope


def _has_envelope_only_return(identity: dict[str, str], text: str) -> bool:
    lower = f"{identity.get('required_return', '')}\n{text}".lower()
    return "envelope" in lower and "controller" in lower and "path" in lower and "hash" in lower


def _has_chat_body_suppression(identity: dict[str, str], text: str) -> bool:
    lower = f"{identity.get('required_return', '')}\n{text}".lower()
    return (
        "do not include" in lower
        and "chat" in lower
        and (
            "body" in lower
            or "blockers" in lower
            or "evidence details" in lower
            or "result-body content" in lower
        )
    )


def _manifest_entries(project_root: Path) -> list[dict[str, Any]]:
    manifest_path = project_root / "skills" / "flowpilot" / "assets" / "runtime_kit" / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    cards = payload.get("cards")
    if not isinstance(cards, list):
        raise RuntimeError("runtime manifest must contain a cards list")
    return [card for card in cards if isinstance(card, dict)]


def collect_router_facts(project_root: Path) -> RouterFacts:
    router = _load_router(project_root)
    manifest_by_id = {str(card["id"]): card for card in _manifest_entries(project_root)}
    active_roles: dict[str, str] = {}

    for boot_action in router.BOOT_ACTIONS:
        card_id = boot_action.get("card_id")
        if card_id:
            active_roles[str(card_id)] = str(manifest_by_id.get(str(card_id), {}).get("audience", boot_action.get("actor", "")))

    for item in router.SYSTEM_CARD_SEQUENCE:
        card_id = str(item["card_id"])
        active_roles[card_id] = str(item["to_role"])

    for card in manifest_by_id.values():
        if card.get("kind") == "role_core":
            active_roles[str(card["id"])] = str(card["audience"])

    sequence_manifest_errors: list[str] = []
    for card_id, role in sorted(active_roles.items()):
        manifest = manifest_by_id.get(card_id)
        if manifest is None:
            sequence_manifest_errors.append(f"active router card is missing from manifest: {card_id}")
            continue
        audience = str(manifest.get("audience", ""))
        if audience != role:
            sequence_manifest_errors.append(f"active router card role mismatch: {card_id} router={role} manifest={audience}")

    card_delivery_flags = {str(item["flag"]) for item in router.SYSTEM_CARD_SEQUENCE}
    external_card_flag_errors: list[str] = []
    for event_name, event in sorted(router.EXTERNAL_EVENTS.items()):
        requires = str(event.get("requires_flag", ""))
        if requires.endswith("_card_delivered") and requires not in card_delivery_flags:
            external_card_flag_errors.append(f"{event_name} requires unknown delivered-card flag: {requires}")

    runtime_root = project_root / "skills" / "flowpilot" / "assets" / "runtime_kit"
    manifest_paths = {str(card["path"]).replace("/", "\\") for card in manifest_by_id.values()}
    orphan_files = []
    for path in sorted((runtime_root / "cards").rglob("*.md")):
        rel = str(path.relative_to(runtime_root)).replace("/", "\\")
        if rel not in manifest_paths:
            orphan_files.append(rel)

    return RouterFacts(
        active_card_ids=tuple(sorted(active_roles)),
        active_role_by_card=tuple(sorted(active_roles.items())),
        external_card_flag_errors=tuple(external_card_flag_errors),
        sequence_manifest_errors=tuple(sequence_manifest_errors),
        orphan_card_files=tuple(orphan_files),
    )


def collect_card_facts(project_root: Path) -> tuple[CardFacts, ...]:
    runtime_root = project_root / "skills" / "flowpilot" / "assets" / "runtime_kit"
    router_facts = collect_router_facts(project_root)
    active_roles = dict(router_facts.active_role_by_card)
    facts: list[CardFacts] = []

    for entry in _manifest_entries(project_root):
        card_id = str(entry.get("id", ""))
        role = str(entry.get("audience", ""))
        path = str(entry.get("path", ""))
        text = (runtime_root / path).read_text(encoding="utf-8")
        identity = _parse_identity_block(text)
        expected_role = active_roles.get(card_id, role)
        facts.append(
            CardFacts(
                card_id=card_id,
                path=path,
                role=role,
                kind=str(entry.get("kind", "")),
                manifest_registered=True,
                router_active=card_id in active_roles,
                identity_boundary=bool(identity),
                recipient_role_matches=identity.get("recipient_role") == expected_role,
                required_return=bool(identity.get("required_return")),
                envelope_only_return=_has_envelope_only_return(identity, text),
                chat_body_suppression=_has_chat_body_suppression(identity, text),
                next_step_source=bool(identity.get(NEXT_STEP_SOURCE_FIELD)),
                next_step_mentions_router=NEXT_STEP_ROUTER_FRAGMENT in identity.get(NEXT_STEP_SOURCE_FIELD, ""),
                action_guidance=_has_action_guidance(expected_role, text),
                pm_history_context_guidance=_has_pm_history_context_guidance(card_id, expected_role, text),
            )
        )

    manifest_paths = {str(card.path).replace("/", "\\") for card in facts}
    for path in sorted((runtime_root / "cards").rglob("*.md")):
        rel = str(path.relative_to(runtime_root)).replace("/", "\\")
        if rel in manifest_paths:
            continue
        text = path.read_text(encoding="utf-8")
        identity = _parse_identity_block(text)
        role = identity.get("recipient_role", "unknown")
        facts.append(
            CardFacts(
                card_id=f"unmanifested:{rel}",
                path=rel,
                role=role,
                kind="unmanifested",
                manifest_registered=False,
                router_active=False,
                identity_boundary=bool(identity),
                recipient_role_matches=bool(identity.get("recipient_role")),
                required_return=bool(identity.get("required_return")),
                envelope_only_return=_has_envelope_only_return(identity, text),
                chat_body_suppression=_has_chat_body_suppression(identity, text),
                next_step_source=bool(identity.get(NEXT_STEP_SOURCE_FIELD)),
                next_step_mentions_router=NEXT_STEP_ROUTER_FRAGMENT in identity.get(NEXT_STEP_SOURCE_FIELD, ""),
                action_guidance=_has_action_guidance(role, text),
                pm_history_context_guidance=_has_pm_history_context_guidance(f"unmanifested:{rel}", role, text),
            )
        )
    return tuple(sorted(facts, key=lambda card: card.card_id))


def card_failures(card: CardFacts) -> tuple[str, ...]:
    failures: list[str] = []
    if card.router_active and not card.manifest_registered:
        failures.append(f"{card.card_id}: active router card is not manifest registered")
    if not card.identity_boundary:
        failures.append(f"{card.card_id}: missing FLOWPILOT_IDENTITY_BOUNDARY_V1")
    if not card.recipient_role_matches:
        failures.append(f"{card.card_id}: recipient_role does not match router/manifest audience")
    if not card.required_return:
        failures.append(f"{card.card_id}: missing required_return")
    if not card.envelope_only_return:
        failures.append(f"{card.card_id}: missing envelope-only role return rule")
    if not card.chat_body_suppression:
        failures.append(f"{card.card_id}: missing chat body suppression rule")
    if not card.next_step_source:
        failures.append(f"{card.card_id}: missing next_step_source")
    if not card.next_step_mentions_router:
        failures.append(f"{card.card_id}: next_step_source does not name flowpilot_router.py")
    if not card.action_guidance:
        failures.append(f"{card.card_id}: card body lacks role-appropriate action guidance")
    if not card.pm_history_context_guidance:
        failures.append(f"{card.card_id}: missing PM prior path context guidance")
    return tuple(failures)


def next_safe_states(state: State, cards: tuple[CardFacts, ...], router_facts: RouterFacts) -> Iterable[Transition]:
    if state.status != "checking":
        return
    if state.index == 0:
        router_failures = tuple(router_facts.sequence_manifest_errors + router_facts.external_card_flag_errors)
        if router_failures:
            yield Transition("router_instruction_contract_failed", replace(state, status="blocked", failures=router_failures))
            return
    if state.index >= len(cards):
        yield Transition("card_instruction_coverage_complete", replace(state, status="complete"))
        return
    card = cards[state.index]
    failures = card_failures(card)
    if failures:
        yield Transition(f"card_instruction_failed:{card.card_id}", replace(state, status="blocked", failures=failures))
        return
    yield Transition(
        f"card_instruction_checked:{card.card_id}",
        replace(state, index=state.index + 1, checked=state.checked + (card.card_id,)),
    )


def invariant_failures(state: State) -> tuple[str, ...]:
    failures: list[str] = []
    if state.status == "complete" and state.failures:
        failures.append("card instruction coverage completed with failures")
    if state.status == "checking" and state.failures:
        failures.append("checking state contains failures without blocking")
    return tuple(failures)


def invariant_result(state: State) -> InvariantResult:
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


def apply_step(state: State, cards: tuple[CardFacts, ...], router_facts: RouterFacts) -> Iterable[FunctionResult]:
    for transition in next_safe_states(state, cards, router_facts):
        yield FunctionResult(
            output=transition.label,
            new_state=transition.state,
            label=transition.label,
        )


def hazard_cards() -> dict[str, CardFacts]:
    good = CardFacts(
        card_id="hazard.good",
        path="cards/hazard/good.md",
        role="project_manager",
        kind="phase",
        manifest_registered=True,
        router_active=True,
        identity_boundary=True,
        recipient_role_matches=True,
        required_return=True,
        envelope_only_return=True,
        chat_body_suppression=True,
        next_step_source=True,
        next_step_mentions_router=True,
        action_guidance=True,
        pm_history_context_guidance=True,
    )
    return {
        "missing_identity_boundary": replace(good, identity_boundary=False),
        "wrong_recipient_role": replace(good, recipient_role_matches=False),
        "missing_required_return": replace(good, required_return=False),
        "missing_envelope_only_return": replace(good, envelope_only_return=False),
        "missing_chat_body_suppression": replace(good, chat_body_suppression=False),
        "missing_next_step_source": replace(good, next_step_source=False, next_step_mentions_router=False),
        "next_step_without_router": replace(good, next_step_mentions_router=False),
        "missing_action_guidance": replace(good, action_guidance=False),
        "missing_pm_history_context_guidance": replace(
            good,
            card_id="pm.route_skeleton",
            pm_history_context_guidance=False,
        ),
        "active_card_unmanifested": replace(good, manifest_registered=False),
    }
