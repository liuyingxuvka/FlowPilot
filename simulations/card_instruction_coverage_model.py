"""FlowGuard-style card instruction coverage model for FlowPilot.

This model checks the prompt-sufficiency failure class that plain route-state
models can miss: a router transition can be valid, while the card delivered to
the role does not tell that role what to do next or how to return to the
router-controlled flow.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable, NamedTuple

from flowguard import FunctionResult, InvariantResult


NEXT_STEP_SOURCE_FIELD = "next_step_source"
NEXT_STEP_ROUTER_FRAGMENT = "flowpilot_router.py"
LIVE_CONTEXT_SOURCE_FIELD = "runtime_context"
LIVE_CONTEXT_HELPER = "_live_card_delivery_context"
LIVE_CONTEXT_SCHEMA = "flowpilot.live_card_context.v1"
LIVE_CONTEXT_REQUIRED_TERMS = (
    "router delivery envelope",
    "current run",
    "current task",
    "current card",
    "current phase",
    "current node",
    "frontier",
    "user_request_path",
    "source paths",
    "do not continue from memory",
    "protocol blocker",
)
LIVE_CONTEXT_REQUIRED_FIELDS = (
    "run_id",
    "card_id",
    "to_role",
    "current_task",
    "current_stage",
    "current_phase",
    "current_node_id",
    "source_paths",
    "user_request_path",
    "execution_frontier",
    "prompt_delivery_ledger",
)
DIRECT_ROUTER_ACK_REQUIRED_TERMS = (
    "system-card acks go directly to router",
    "card check-in command",
    "router-directed return path",
)
STALE_CONTROLLER_ACK_PATTERNS = (
    re.compile(r"\breturn\s+(?:the\s+)?ack\s+to\s+controller\b", re.IGNORECASE),
    re.compile(r"\bsend\s+(?:the\s+)?ack\s+to\s+controller\b", re.IGNORECASE),
    re.compile(r"\bsubmit\s+(?:the\s+)?ack\s+to\s+controller\b", re.IGNORECASE),
    re.compile(r"\bgive\s+(?:the\s+)?ack\s+to\s+controller\b", re.IGNORECASE),
    re.compile(r"\back\s+returns?\s+to\s+controller\b", re.IGNORECASE),
    re.compile(r"\back\s+returned\s+to\s+controller\b", re.IGNORECASE),
    re.compile(r"\bcontroller\s+(?:must|should)\s+submit\s+(?:the\s+)?ack\b", re.IGNORECASE),
    re.compile(r"\bcontroller\s+submits\s+(?:the\s+)?ack\b", re.IGNORECASE),
    re.compile(r"\bcontroller\s+receives\s+(?:the\s+)?ack\b", re.IGNORECASE),
    re.compile(r"\bwaiting\s+for\s+the\s+runtime\s+ack\b", re.IGNORECASE),
)
STALE_CONTROLLER_ACK_LINE_PATTERNS = (
    re.compile(r"\brecord-event\b.*\bcard_ack\b", re.IGNORECASE),
    re.compile(r"\bcard_ack\b.*\brecord-event\b", re.IGNORECASE),
)
PACKET_BODY_DIRECT_ACK_TERMS = (
    "active-holder-ack",
    "directly to router",
    "do not send packet acks or packet completion reports to controller",
    "controller_next_action_notice.json",
)
PACKET_BODY_RESULT_TERMS = (
    "active-holder-submit-result",
    "active-holder-submit-existing-result",
)
RESULT_BODY_DIRECT_COMPLETION_TERMS = (
    "active-holder packet completion is submitted to router first",
    "not to controller",
    "active-holder lease",
)
PACKET_RUNTIME_DIRECT_ACK_TERMS = (
    "direct_router_ack_rule",
    "packet ack and packet completion report go directly to router",
    "controller_next_action_notice.json",
)
ROUTER_CHECKIN_POST_ACK_TERMS = (
    "ack is receipt only",
    "ack is not completion",
    "post-ack rule",
)
ROUTER_BUNDLE_POST_ACK_TERMS = (
    "bundle ack is receipt only",
    "per-member post-ack rules",
)
POST_ACK_RECEIPT_TERMS = (
    "ack is receipt only",
    "ack is not completion",
)
ROLE_CARD_POST_ACK_TERMS = (
    "after role-card ack",
    "wait for a phase card",
    "event card",
    "work packet",
    "router-authorized output contract",
)
WORK_CARD_POST_ACK_TERMS = (
    "after work-card ack",
    "continue the work assigned by this card",
    "formal output or blocker",
    "router-directed runtime path",
)
EVENT_CARD_POST_ACK_TERMS = (
    "after event-card ack",
    "process this event card",
    "router-authorized output event",
    "protocol blocker",
)
PACKET_POST_ACK_EXECUTION_TERMS = (
    "packet ack is receipt only",
    "ack is not completion",
    "after ack",
    "execute this packet body",
    "sealed result",
)
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
PM_MINIMUM_COMPLEXITY_REQUIRED_CARD_IDS = frozenset(
    {
        "pm.core",
        "pm.product_architecture",
        "pm.root_contract",
        "pm.child_skill_selection",
        "pm.route_skeleton",
        "pm.current_node_loop",
        "pm.node_acceptance_plan",
        "pm.review_repair",
        "pm.evidence_quality_package",
        "pm.final_ledger",
        "pm.closure",
    }
)
OUTPUT_CONTRACT_REQUIRED_CARD_IDS = frozenset(
    {
        "pm.core",
        "pm.output_contract_catalog",
        "pm.material_scan",
        "pm.research_package",
        "pm.current_node_loop",
        "pm.officer_request_report_loop",
        "pm.resume_decision",
        "pm.parent_segment_decision",
        "pm.closure",
        "pm.event.node_started",
        "worker_a.core",
        "worker_b.core",
        "worker.research_report",
        "reviewer.core",
        "reviewer.worker_result_review",
        "process_officer.core",
        "product_officer.core",
    }
)
PM_NOTE_GUIDANCE_REQUIRED_CARD_IDS = frozenset(
    {
        "pm.material_scan",
        "pm.research_package",
        "pm.current_node_loop",
        "pm.officer_request_report_loop",
        "worker_a.core",
        "worker_b.core",
        "worker.research_report",
        "process_officer.core",
        "product_officer.core",
    }
)
PM_CONTROL_BLOCKER_REPAIR_CARD_IDS = frozenset(
    {
        "pm.core",
        "pm.review_repair",
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
    direct_router_ack_guidance: bool
    post_ack_receipt_guidance: bool
    role_card_post_ack_wait_guidance: bool
    work_card_post_ack_execution_guidance: bool
    event_card_post_ack_authority_guidance: bool
    stale_controller_ack_guidance: bool
    controller_router_notice_guidance: bool
    live_context_guidance: bool
    action_guidance: bool
    pm_history_context_guidance: bool
    pm_minimum_complexity_guidance: bool
    output_contract_guidance: bool
    pm_note_guidance: bool
    pm_control_blocker_repair_guidance: bool


@dataclass(frozen=True)
class RouterFacts:
    active_card_ids: tuple[str, ...]
    active_role_by_card: tuple[tuple[str, str], ...]
    external_card_flag_errors: tuple[str, ...]
    sequence_manifest_errors: tuple[str, ...]
    live_context_errors: tuple[str, ...]
    card_checkin_post_ack_guidance: bool
    bundle_checkin_post_ack_guidance: bool
    orphan_card_files: tuple[str, ...]


@dataclass(frozen=True)
class PacketPromptFacts:
    packet_body_direct_ack_guidance: bool
    packet_body_result_submission_guidance: bool
    packet_body_forbids_controller_ack: bool
    packet_body_names_router_notice: bool
    packet_body_post_ack_execution_guidance: bool
    result_body_direct_completion_guidance: bool
    packet_runtime_direct_ack_identity_guidance: bool
    packet_runtime_post_ack_execution_guidance: bool
    stale_controller_ack_guidance: bool


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


def _has_pm_minimum_complexity_guidance(card_id: str, role: str, text: str) -> bool:
    if role != "project_manager" or card_id not in PM_MINIMUM_COMPLEXITY_REQUIRED_CARD_IDS:
        return True
    lower = text.lower()
    return (
        "minimum sufficient complexity" in lower
        and (
            "fewer" in lower
            or "smallest" in lower
            or "less state" in lower
            or "lower maintenance" in lower
            or "simpler" in lower
            or "unnecessary" in lower
            or "unused" in lower
        )
    )


def _has_output_contract_guidance(card_id: str, text: str) -> bool:
    if card_id not in OUTPUT_CONTRACT_REQUIRED_CARD_IDS:
        return True
    lower = text.lower()
    has_packet_contract = "output_contract" in lower and ("packet" in lower or "envelope" in lower)
    if card_id in {
        "pm.core",
        "pm.output_contract_catalog",
        "reviewer.core",
        "process_officer.core",
        "product_officer.core",
    }:
        has_gate_decision_contract = (
            "flowpilot.output_contract.gate_decision.v1" in lower
            and "gate_decision_version" in lower
            and "semantic" in lower
        )
        return has_packet_contract and "contract self-check" in lower and has_gate_decision_contract
    if card_id.startswith("pm.") and card_id not in {"pm.core", "pm.output_contract_catalog"}:
        return has_packet_contract
    return has_packet_contract and "contract self-check" in lower


def _has_pm_note_guidance(card_id: str, text: str) -> bool:
    if card_id not in PM_NOTE_GUIDANCE_REQUIRED_CARD_IDS:
        return True
    lower = text.lower()
    return (
        "pm note" in lower
        and "in-scope quality choice" in lower
        and "pm consideration" in lower
        and "decision-support" in lower
        and ("scope expansion" in lower or "expanding the packet" in lower)
    )


def _has_pm_control_blocker_repair_guidance(card_id: str, role: str, text: str) -> bool:
    if role != "project_manager" or card_id not in PM_CONTROL_BLOCKER_REPAIR_CARD_IDS:
        return True
    lower = text.lower()
    required_terms = (
        "control_blocker",
        "pm_repair_decision_required",
        "fatal_protocol_violation",
        "pm_records_control_blocker_repair_decision",
        "flowpilot.output_contract.pm_control_blocker_repair_decision.v1",
        "repair transaction",
    )
    return all(term in lower for term in required_terms)


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


def _has_live_context_guidance(identity: dict[str, str], text: str) -> bool:
    lower = f"{identity.get(LIVE_CONTEXT_SOURCE_FIELD, '')}\n{text}".lower()
    return all(term in lower for term in LIVE_CONTEXT_REQUIRED_TERMS)


def _has_direct_router_ack_guidance(identity: dict[str, str], text: str) -> bool:
    lower = (
        f"{identity.get('required_return', '')}\n"
        f"{identity.get(NEXT_STEP_SOURCE_FIELD, '')}\n"
        f"{text}"
    ).lower()
    return all(term in lower for term in DIRECT_ROUTER_ACK_REQUIRED_TERMS)


def _post_ack_text(identity: dict[str, str], text: str) -> str:
    return (
        f"{identity.get('required_return', '')}\n"
        f"{identity.get('post_ack', '')}\n"
        f"{identity.get(NEXT_STEP_SOURCE_FIELD, '')}\n"
        f"{text}"
    )


def _has_post_ack_receipt_guidance(identity: dict[str, str], text: str) -> bool:
    return _has_terms(_post_ack_text(identity, text), POST_ACK_RECEIPT_TERMS)


def _card_post_ack_profile(card_id: str, kind: str, path: str) -> str:
    del card_id
    normalized_path = path.replace("\\", "/")
    if kind == "role_core":
        return "role"
    if kind == "event" or normalized_path.startswith("cards/events/"):
        return "event"
    return "work"


def _has_role_card_post_ack_wait_guidance(
    card_id: str,
    kind: str,
    path: str,
    identity: dict[str, str],
    text: str,
) -> bool:
    if _card_post_ack_profile(card_id, kind, path) != "role":
        return True
    return _has_terms(_post_ack_text(identity, text), ROLE_CARD_POST_ACK_TERMS)


def _has_work_card_post_ack_execution_guidance(
    card_id: str,
    kind: str,
    path: str,
    identity: dict[str, str],
    text: str,
) -> bool:
    if _card_post_ack_profile(card_id, kind, path) != "work":
        return True
    return _has_terms(_post_ack_text(identity, text), WORK_CARD_POST_ACK_TERMS)


def _has_event_card_post_ack_authority_guidance(
    card_id: str,
    kind: str,
    path: str,
    identity: dict[str, str],
    text: str,
) -> bool:
    if _card_post_ack_profile(card_id, kind, path) != "event":
        return True
    return _has_terms(_post_ack_text(identity, text), EVENT_CARD_POST_ACK_TERMS)


def _has_stale_controller_ack_guidance(text: str) -> bool:
    if any(pattern.search(text) for pattern in STALE_CONTROLLER_ACK_PATTERNS):
        return True
    return any(
        pattern.search(line)
        for line in text.splitlines()
        for pattern in STALE_CONTROLLER_ACK_LINE_PATTERNS
    )


def _has_controller_router_notice_guidance(role: str, text: str) -> bool:
    if role != "controller":
        return True
    lower = text.lower()
    return (
        "active-holder" in lower
        and "controller_next_action_notice.json" in lower
        and "wait" in lower
        and "router" in lower
    )


def _has_terms(text: str, terms: tuple[str, ...]) -> bool:
    lower = re.sub(r"\s+", " ", text.lower())
    return all(term in lower for term in terms)


def _manifest_entries(project_root: Path) -> list[dict[str, Any]]:
    manifest_path = project_root / "skills" / "flowpilot" / "assets" / "runtime_kit" / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    cards = payload.get("cards")
    if not isinstance(cards, list):
        raise RuntimeError("runtime manifest must contain a cards list")
    return [card for card in cards if isinstance(card, dict)]


def collect_router_facts(project_root: Path) -> RouterFacts:
    router = _load_router(project_root)
    router_source = (
        project_root / "skills" / "flowpilot" / "assets" / "flowpilot_router.py"
    ).read_text(encoding="utf-8")
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
        if bool(event.get("legacy")):
            continue
        requires = str(event.get("requires_flag", ""))
        if requires.endswith("_card_delivered") and requires not in card_delivery_flags:
            external_card_flag_errors.append(f"{event_name} requires unknown delivered-card flag: {requires}")

    live_context_errors: list[str] = []
    if LIVE_CONTEXT_HELPER not in router_source or LIVE_CONTEXT_SCHEMA not in router_source:
        live_context_errors.append("router does not build live card delivery context")
    if '"delivery_context"' not in router_source:
        live_context_errors.append("system card delivery action/ledger omits delivery_context")
    for field in LIVE_CONTEXT_REQUIRED_FIELDS:
        if field not in router_source:
            live_context_errors.append(f"live card delivery context omits {field}")

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
        live_context_errors=tuple(live_context_errors),
        card_checkin_post_ack_guidance=_has_terms(router_source, ROUTER_CHECKIN_POST_ACK_TERMS),
        bundle_checkin_post_ack_guidance=_has_terms(router_source, ROUTER_BUNDLE_POST_ACK_TERMS),
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
                direct_router_ack_guidance=_has_direct_router_ack_guidance(identity, text),
                post_ack_receipt_guidance=_has_post_ack_receipt_guidance(identity, text),
                role_card_post_ack_wait_guidance=_has_role_card_post_ack_wait_guidance(
                    card_id,
                    str(entry.get("kind", "")),
                    path,
                    identity,
                    text,
                ),
                work_card_post_ack_execution_guidance=_has_work_card_post_ack_execution_guidance(
                    card_id,
                    str(entry.get("kind", "")),
                    path,
                    identity,
                    text,
                ),
                event_card_post_ack_authority_guidance=_has_event_card_post_ack_authority_guidance(
                    card_id,
                    str(entry.get("kind", "")),
                    path,
                    identity,
                    text,
                ),
                stale_controller_ack_guidance=_has_stale_controller_ack_guidance(text),
                controller_router_notice_guidance=_has_controller_router_notice_guidance(expected_role, text),
                live_context_guidance=_has_live_context_guidance(identity, text),
                action_guidance=_has_action_guidance(expected_role, text),
                pm_history_context_guidance=_has_pm_history_context_guidance(card_id, expected_role, text),
                pm_minimum_complexity_guidance=_has_pm_minimum_complexity_guidance(card_id, expected_role, text),
                output_contract_guidance=_has_output_contract_guidance(card_id, text),
                pm_note_guidance=_has_pm_note_guidance(card_id, text),
                pm_control_blocker_repair_guidance=_has_pm_control_blocker_repair_guidance(card_id, expected_role, text),
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
                direct_router_ack_guidance=_has_direct_router_ack_guidance(identity, text),
                post_ack_receipt_guidance=_has_post_ack_receipt_guidance(identity, text),
                role_card_post_ack_wait_guidance=_has_role_card_post_ack_wait_guidance(
                    f"unmanifested:{rel}",
                    "unmanifested",
                    rel,
                    identity,
                    text,
                ),
                work_card_post_ack_execution_guidance=_has_work_card_post_ack_execution_guidance(
                    f"unmanifested:{rel}",
                    "unmanifested",
                    rel,
                    identity,
                    text,
                ),
                event_card_post_ack_authority_guidance=_has_event_card_post_ack_authority_guidance(
                    f"unmanifested:{rel}",
                    "unmanifested",
                    rel,
                    identity,
                    text,
                ),
                stale_controller_ack_guidance=_has_stale_controller_ack_guidance(text),
                controller_router_notice_guidance=_has_controller_router_notice_guidance(role, text),
                live_context_guidance=_has_live_context_guidance(identity, text),
                action_guidance=_has_action_guidance(role, text),
                pm_history_context_guidance=_has_pm_history_context_guidance(f"unmanifested:{rel}", role, text),
                pm_minimum_complexity_guidance=_has_pm_minimum_complexity_guidance(f"unmanifested:{rel}", role, text),
                output_contract_guidance=_has_output_contract_guidance(f"unmanifested:{rel}", text),
                pm_note_guidance=_has_pm_note_guidance(f"unmanifested:{rel}", text),
                pm_control_blocker_repair_guidance=_has_pm_control_blocker_repair_guidance(f"unmanifested:{rel}", role, text),
            )
        )
    return tuple(sorted(facts, key=lambda card: card.card_id))


def collect_packet_prompt_facts(project_root: Path) -> PacketPromptFacts:
    packet_body = (project_root / "templates" / "flowpilot" / "packets" / "packet_body.template.md").read_text(
        encoding="utf-8"
    )
    result_body = (project_root / "templates" / "flowpilot" / "packets" / "result_body.template.md").read_text(
        encoding="utf-8"
    )
    packet_runtime = (project_root / "skills" / "flowpilot" / "assets" / "packet_runtime.py").read_text(
        encoding="utf-8"
    )
    combined = "\n".join((packet_body, result_body, packet_runtime))
    normalized_packet_body = re.sub(r"\s+", " ", packet_body.lower())
    return PacketPromptFacts(
        packet_body_direct_ack_guidance=_has_terms(packet_body, PACKET_BODY_DIRECT_ACK_TERMS),
        packet_body_result_submission_guidance=_has_terms(packet_body, PACKET_BODY_RESULT_TERMS),
        packet_body_forbids_controller_ack="do not send packet acks or packet completion reports to controller"
        in normalized_packet_body,
        packet_body_names_router_notice="controller_next_action_notice.json" in packet_body,
        packet_body_post_ack_execution_guidance=_has_terms(packet_body, PACKET_POST_ACK_EXECUTION_TERMS),
        result_body_direct_completion_guidance=_has_terms(result_body, RESULT_BODY_DIRECT_COMPLETION_TERMS),
        packet_runtime_direct_ack_identity_guidance=_has_terms(packet_runtime, PACKET_RUNTIME_DIRECT_ACK_TERMS),
        packet_runtime_post_ack_execution_guidance=_has_terms(packet_runtime, PACKET_POST_ACK_EXECUTION_TERMS),
        stale_controller_ack_guidance=_has_stale_controller_ack_guidance(combined),
    )


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
    if not card.direct_router_ack_guidance:
        failures.append(f"{card.card_id}: missing direct Router system-card ACK guidance")
    if not card.post_ack_receipt_guidance:
        failures.append(f"{card.card_id}: missing ACK-is-receipt-only post-ACK guidance")
    if not card.role_card_post_ack_wait_guidance:
        failures.append(f"{card.card_id}: role card does not say to wait for authorized task/event/packet work after ACK")
    if not card.work_card_post_ack_execution_guidance:
        failures.append(f"{card.card_id}: work card does not say to continue assigned work after ACK")
    if not card.event_card_post_ack_authority_guidance:
        failures.append(f"{card.card_id}: event card does not bind post-ACK processing to Router-authorized event handling")
    if card.stale_controller_ack_guidance:
        failures.append(f"{card.card_id}: stale prompt still teaches Controller-routed ACK handling")
    if not card.controller_router_notice_guidance:
        failures.append(f"{card.card_id}: Controller card does not teach waiting for Router next-action notice")
    if not card.live_context_guidance:
        failures.append(f"{card.card_id}: missing live router delivery context guidance")
    if not card.action_guidance:
        failures.append(f"{card.card_id}: card body lacks role-appropriate action guidance")
    if not card.pm_history_context_guidance:
        failures.append(f"{card.card_id}: missing PM prior path context guidance")
    if not card.pm_minimum_complexity_guidance:
        failures.append(f"{card.card_id}: missing PM minimum sufficient complexity guidance")
    if not card.output_contract_guidance:
        failures.append(f"{card.card_id}: missing output_contract and Contract Self-Check guidance")
    if not card.pm_note_guidance:
        failures.append(f"{card.card_id}: missing worker/officer PM Note soft guidance")
    if not card.pm_control_blocker_repair_guidance:
        failures.append(f"{card.card_id}: missing PM control-blocker repair guidance for fatal and repair-decision lanes")
    return tuple(failures)


def packet_prompt_failures(packet_prompts: PacketPromptFacts) -> tuple[str, ...]:
    failures: list[str] = []
    if not packet_prompts.packet_body_direct_ack_guidance:
        failures.append("packet body template does not teach direct Router packet ACK")
    if not packet_prompts.packet_body_result_submission_guidance:
        failures.append("packet body template does not teach direct Router packet result submission")
    if not packet_prompts.packet_body_forbids_controller_ack:
        failures.append("packet body template does not forbid Controller-routed packet ACK/completion")
    if not packet_prompts.packet_body_names_router_notice:
        failures.append("packet body template does not name controller_next_action_notice.json")
    if not packet_prompts.packet_body_post_ack_execution_guidance:
        failures.append("packet body template does not teach ACK-is-receipt-only post-ACK execution")
    if not packet_prompts.result_body_direct_completion_guidance:
        failures.append("result body template does not teach active-holder completion direct to Router")
    if not packet_prompts.packet_runtime_direct_ack_identity_guidance:
        failures.append("packet runtime identity boundary does not include direct Router ACK rule")
    if not packet_prompts.packet_runtime_post_ack_execution_guidance:
        failures.append("packet runtime identity boundary does not teach post-ACK packet execution")
    if packet_prompts.stale_controller_ack_guidance:
        failures.append("packet prompt surface still teaches Controller-routed ACK handling")
    return tuple(failures)


def next_safe_states(
    state: State,
    cards: tuple[CardFacts, ...],
    router_facts: RouterFacts,
    packet_prompts: PacketPromptFacts | None = None,
) -> Iterable[Transition]:
    if state.status != "checking":
        return
    if state.index == 0:
        router_failures_list = list(
            router_facts.sequence_manifest_errors
            + router_facts.external_card_flag_errors
            + router_facts.live_context_errors
        )
        if not router_facts.card_checkin_post_ack_guidance:
            router_failures_list.append("router card check-in instruction lacks ACK-is-receipt-only post-ACK guidance")
        if not router_facts.bundle_checkin_post_ack_guidance:
            router_failures_list.append("router bundle check-in instruction lacks per-member post-ACK guidance")
        router_failures = tuple(router_failures_list)
        if router_failures:
            yield Transition("router_instruction_contract_failed", replace(state, status="blocked", failures=router_failures))
            return
        if packet_prompts is not None:
            packet_failures = packet_prompt_failures(packet_prompts)
            if packet_failures:
                yield Transition(
                    "packet_prompt_direct_router_ack_contract_failed",
                    replace(state, status="blocked", failures=packet_failures),
                )
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
        direct_router_ack_guidance=True,
        post_ack_receipt_guidance=True,
        role_card_post_ack_wait_guidance=True,
        work_card_post_ack_execution_guidance=True,
        event_card_post_ack_authority_guidance=True,
        stale_controller_ack_guidance=False,
        controller_router_notice_guidance=True,
        live_context_guidance=True,
        action_guidance=True,
        pm_history_context_guidance=True,
        pm_minimum_complexity_guidance=True,
        output_contract_guidance=True,
        pm_note_guidance=True,
        pm_control_blocker_repair_guidance=True,
    )
    return {
        "missing_identity_boundary": replace(good, identity_boundary=False),
        "wrong_recipient_role": replace(good, recipient_role_matches=False),
        "missing_required_return": replace(good, required_return=False),
        "missing_envelope_only_return": replace(good, envelope_only_return=False),
        "missing_chat_body_suppression": replace(good, chat_body_suppression=False),
        "missing_next_step_source": replace(good, next_step_source=False, next_step_mentions_router=False),
        "next_step_without_router": replace(good, next_step_mentions_router=False),
        "missing_direct_router_ack_guidance": replace(good, direct_router_ack_guidance=False),
        "missing_post_ack_receipt_guidance": replace(good, post_ack_receipt_guidance=False),
        "role_card_starts_work_after_ack": replace(
            good,
            card_id="pm.core",
            kind="role_core",
            role_card_post_ack_wait_guidance=False,
        ),
        "work_card_stops_after_ack": replace(
            good,
            card_id="pm.product_architecture",
            kind="phase",
            work_card_post_ack_execution_guidance=False,
        ),
        "event_card_ack_replaces_disposition": replace(
            good,
            card_id="pm.event.reviewer_report",
            kind="event",
            event_card_post_ack_authority_guidance=False,
        ),
        "stale_controller_ack_guidance": replace(good, stale_controller_ack_guidance=True),
        "missing_controller_router_notice_guidance": replace(
            good,
            card_id="controller.core",
            role="controller",
            controller_router_notice_guidance=False,
        ),
        "missing_live_context_guidance": replace(good, live_context_guidance=False),
        "missing_action_guidance": replace(good, action_guidance=False),
        "missing_pm_history_context_guidance": replace(
            good,
            card_id="pm.route_skeleton",
            pm_history_context_guidance=False,
        ),
        "missing_pm_minimum_complexity_guidance": replace(
            good,
            card_id="pm.route_skeleton",
            pm_minimum_complexity_guidance=False,
        ),
        "active_card_unmanifested": replace(good, manifest_registered=False),
        "missing_output_contract_guidance": replace(
            good,
            card_id="pm.output_contract_catalog",
            output_contract_guidance=False,
        ),
        "missing_pm_note_guidance": replace(
            good,
            card_id="worker_a.core",
            pm_note_guidance=False,
        ),
        "missing_pm_control_blocker_repair_guidance": replace(
            good,
            card_id="pm.review_repair",
            pm_control_blocker_repair_guidance=False,
        ),
    }


def hazard_packet_prompts() -> dict[str, PacketPromptFacts]:
    good = PacketPromptFacts(
        packet_body_direct_ack_guidance=True,
        packet_body_result_submission_guidance=True,
        packet_body_forbids_controller_ack=True,
        packet_body_names_router_notice=True,
        packet_body_post_ack_execution_guidance=True,
        result_body_direct_completion_guidance=True,
        packet_runtime_direct_ack_identity_guidance=True,
        packet_runtime_post_ack_execution_guidance=True,
        stale_controller_ack_guidance=False,
    )
    return {
        "missing_packet_direct_router_ack_guidance": replace(good, packet_body_direct_ack_guidance=False),
        "missing_packet_result_submission_guidance": replace(good, packet_body_result_submission_guidance=False),
        "missing_packet_controller_ack_forbid": replace(good, packet_body_forbids_controller_ack=False),
        "missing_packet_router_notice_guidance": replace(good, packet_body_names_router_notice=False),
        "missing_packet_post_ack_execution_guidance": replace(good, packet_body_post_ack_execution_guidance=False),
        "missing_result_direct_completion_guidance": replace(good, result_body_direct_completion_guidance=False),
        "missing_packet_runtime_direct_ack_identity_guidance": replace(
            good,
            packet_runtime_direct_ack_identity_guidance=False,
        ),
        "missing_packet_runtime_post_ack_execution_guidance": replace(
            good,
            packet_runtime_post_ack_execution_guidance=False,
        ),
        "stale_packet_controller_ack_guidance": replace(good, stale_controller_ack_guidance=True),
    }
