"""FlowGuard model-maturation closure model for FlowPilot.

This model records the post-evidence signals that must be resolved before
FlowPilot can promote model, test, mesh, or background evidence to a broad
confidence claim.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable

from flowguard import (
    MATURITY_ACTION_ADD_CODE_BOUNDARY_OBSERVATION,
    MATURITY_ACTION_ADD_MODEL_OBLIGATION,
    MATURITY_ACTION_ADD_STATE_FIELD,
    MATURITY_ACTION_ADD_TRANSITION_CASE,
    MATURITY_ACTION_DOWNGRADE_CLAIM,
    MATURITY_ACTION_REATTACH_PARENT_MODEL,
    MATURITY_ACTION_REFRESH_EVIDENCE,
    MATURITY_ACTION_SPLIT_CHILD_MODEL,
    MODEL_MATURATION_DECISION_CURRENT,
    MODEL_MATURATION_SIGNAL_CHILD_REATTACHMENT_MISSING,
    MODEL_MATURATION_SIGNAL_MISSING_CODE_BOUNDARY_OBSERVATION,
    MODEL_MATURATION_SIGNAL_MISSING_MODEL_OBLIGATION,
    MODEL_MATURATION_SIGNAL_OVERSIZED_MODEL,
    MODEL_MATURATION_SIGNAL_PROGRESS_ONLY_EVIDENCE,
    MODEL_MATURATION_SIGNAL_STALE_EVIDENCE,
    MODEL_MATURATION_SIGNAL_STATE_TOO_COARSE,
    ModelMaturationPlan,
    ModelMaturationSignal,
    review_model_maturation_loop,
)

try:  # pragma: no cover - direct-script fallback below.
    from .run_flowpilot_model_mesh_checks import _unified_repair_contract_report
except ImportError:  # pragma: no cover
    from run_flowpilot_model_mesh_checks import _unified_repair_contract_report


ROOT = Path(__file__).resolve().parents[1]
PLAN_ID = "flowpilot-model-maturation-routine-closure"
MODEL_ID = "flowpilot_model_maturation_closure"
RESULT_PATH = "simulations/flowpilot_model_maturation_results.json"


@dataclass(frozen=True)
class EvidenceGate:
    signal_id: str
    signal_type: str
    source_route: str
    model_id: str
    risk_id: str
    description: str
    sources: tuple[str, ...]
    result: str = ""
    required_actions: tuple[str, ...] = ()
    require_json_ok: bool = True
    require_unified_repair_conformance: bool = False
    blocks_model_maturation: bool = False


def _path(relpath: str) -> Path:
    return ROOT / relpath


def _read_json(relpath: str) -> dict[str, Any]:
    try:
        return json.loads(_path(relpath).read_text(encoding="utf-8"))
    except Exception as exc:
        return {"ok": False, "read_error": repr(exc)}


def _existing_sources_current(sources: Iterable[str], result: str = "") -> tuple[bool, dict[str, Any]]:
    source_paths = [_path(relpath) for relpath in sources]
    missing_sources = [
        str(path.relative_to(ROOT)) for path in source_paths if not path.exists()
    ]
    result_path = _path(result) if result else None
    result_missing = bool(result_path and not result_path.exists())
    max_source_mtime = max(
        (path.stat().st_mtime for path in source_paths if path.exists()),
        default=0.0,
    )
    result_mtime = result_path.stat().st_mtime if result_path and result_path.exists() else 0.0
    current = not missing_sources and not result_missing
    if result_path is not None:
        current = current and result_mtime >= max_source_mtime
    return current, {
        "sources": [str(path.relative_to(ROOT)) for path in source_paths],
        "missing_sources": missing_sources,
        "result": result,
        "result_missing": result_missing,
        "max_source_mtime": max_source_mtime,
        "result_mtime": result_mtime,
    }


def _json_ok(relpath: str) -> tuple[bool, dict[str, Any]]:
    payload = _read_json(relpath)
    ok = payload.get("ok") is True
    return ok, {
        "result": relpath,
        "ok": ok,
        "decision": payload.get("decision", ""),
        "confidence": payload.get("confidence", ""),
        "result_type": payload.get("result_type", ""),
    }


def _gate_signal(gate: EvidenceGate) -> ModelMaturationSignal:
    current, freshness = _existing_sources_current(gate.sources, gate.result)
    json_current = True
    json_meta: dict[str, Any] = {}
    if gate.result and gate.require_json_ok:
        json_current, json_meta = _json_ok(gate.result)
    contract_current = True
    contract_meta: dict[str, Any] = {}
    if gate.result and gate.require_unified_repair_conformance:
        contract_meta = _unified_repair_contract_report(
            project_root=ROOT,
            payload=_read_json(gate.result),
        )
        contract_current = bool(contract_meta["ok"])
    resolved = current and json_current and contract_current
    return ModelMaturationSignal(
        signal_id=gate.signal_id,
        signal_type=gate.signal_type,
        source_route=gate.source_route,
        model_id=gate.model_id,
        risk_id=gate.risk_id,
        evidence_id=gate.result,
        description=gate.description,
        resolved=resolved,
        current=current,
        suggested_actions=gate.required_actions,
        metadata={
            "freshness": freshness,
            "json": json_meta,
            "unified_repair_contract": contract_meta or None,
        },
    )


def evidence_gates() -> tuple[EvidenceGate, ...]:
    change_root = "openspec/changes/adopt-flowguard-model-maturation"
    return (
        EvidenceGate(
            signal_id="maturation_gate_registered",
            signal_type=MODEL_MATURATION_SIGNAL_MISSING_MODEL_OBLIGATION,
            source_route="flowguard_model_maturation_closure",
            model_id=MODEL_ID,
            risk_id="missing_final_maturation_gate",
            description="FlowPilot must register a focused model maturation closure gate.",
            sources=(
                "simulations/flowpilot_model_maturation_model.py",
                "simulations/run_flowpilot_model_maturation_checks.py",
                f"{change_root}/specs/flowguard-model-maturation-closure/spec.md",
            ),
            required_actions=(MATURITY_ACTION_ADD_MODEL_OBLIGATION,),
            require_json_ok=False,
        ),
        EvidenceGate(
            signal_id="ack_settlement_vs_output_completion",
            signal_type=MODEL_MATURATION_SIGNAL_STATE_TOO_COARSE,
            source_route="wait_reconciliation",
            model_id="flowpilot_role_output_runtime",
            risk_id="ack_only_closure_false_positive",
            description="ACK wait settlement must remain separate from durable role-output completion.",
            sources=(
                "simulations/flowpilot_role_output_runtime_model.py",
                "simulations/run_flowpilot_role_output_runtime_checks.py",
                f"{change_root}/specs/wait-reconciliation/spec.md",
            ),
            result="simulations/flowpilot_role_output_runtime_results.json",
            required_actions=(
                MATURITY_ACTION_ADD_STATE_FIELD,
                MATURITY_ACTION_ADD_TRANSITION_CASE,
            ),
        ),
        EvidenceGate(
            signal_id="route_replacement_disposes_old_packets",
            signal_type=MODEL_MATURATION_SIGNAL_CHILD_REATTACHMENT_MISSING,
            source_route="route_repair_replacement_policy",
            model_id="flowpilot_route_mutation_activation",
            risk_id="old_active_packet_survives_replacement",
            description="Replacement route activation must dispose old active packets and reattach parent evidence.",
            sources=(
                "simulations/flowpilot_route_mutation_activation_model.py",
                "simulations/run_flowpilot_route_mutation_activation_checks.py",
                f"{change_root}/specs/route-repair-replacement-policy/spec.md",
            ),
            result="simulations/flowpilot_route_mutation_activation_results.json",
            required_actions=(
                MATURITY_ACTION_REATTACH_PARENT_MODEL,
                MATURITY_ACTION_ADD_TRANSITION_CASE,
            ),
        ),
        EvidenceGate(
            signal_id="prompt_assets_are_contract_inputs",
            signal_type=MODEL_MATURATION_SIGNAL_MISSING_CODE_BOUNDARY_OBSERVATION,
            source_route="flowpilot_prompt_boundary_policy",
            model_id="flowpilot_prompt_boundary",
            risk_id="prompt_asset_drift_not_seen_by_code_scan",
            description="Prompt assets and manifests must be model-visible contract inputs.",
            sources=(
                "simulations/flowpilot_prompt_boundary_model.py",
                "simulations/run_flowpilot_prompt_boundary_checks.py",
                "skills/flowpilot/assets/runtime_kit/prompts/manifest.json",
                f"{change_root}/specs/flowpilot-prompt-boundary-policy/spec.md",
            ),
            result="simulations/flowpilot_prompt_boundary_results.json",
            required_actions=(
                MATURITY_ACTION_ADD_CODE_BOUNDARY_OBSERVATION,
                MATURITY_ACTION_ADD_MODEL_OBLIGATION,
            ),
        ),
        EvidenceGate(
            signal_id="protocol_contract_conformance_fresh",
            signal_type=MODEL_MATURATION_SIGNAL_STALE_EVIDENCE,
            source_route="existing_model_preflight",
            model_id="flowpilot_protocol_contract_conformance",
            risk_id="protocol_contract_result_stale",
            description="Protocol contract conformance result must be current for the model and checker.",
            sources=(
                "simulations/flowpilot_protocol_contract_conformance_model.py",
                "simulations/run_protocol_contract_conformance_checks.py",
            ),
            result="simulations/protocol_contract_conformance_results.json",
            required_actions=(MATURITY_ACTION_REFRESH_EVIDENCE,),
        ),
        EvidenceGate(
            signal_id="singleton_identity_authority_current",
            signal_type=MODEL_MATURATION_SIGNAL_MISSING_MODEL_OBLIGATION,
            source_route="singleton_identity_authority",
            model_id="flowpilot_singleton_identity_authority",
            risk_id="singleton_duplicate_authority_gap",
            description="Singleton-vs-plural authority gaps must be model-visible before broad confidence.",
            sources=(
                "docs/flowpilot_singleton_identity_authority.md",
                "simulations/flowpilot_singleton_identity_model.py",
                "simulations/run_flowpilot_singleton_identity_checks.py",
                "tests/test_flowpilot_singleton_identity.py",
            ),
            result="simulations/flowpilot_singleton_identity_results.json",
            required_actions=(
                MATURITY_ACTION_ADD_MODEL_OBLIGATION,
                MATURITY_ACTION_ADD_CODE_BOUNDARY_OBSERVATION,
                MATURITY_ACTION_REFRESH_EVIDENCE,
            ),
        ),
        EvidenceGate(
            signal_id="startup_control_evidence_fresh",
            signal_type=MODEL_MATURATION_SIGNAL_STALE_EVIDENCE,
            source_route="development_process_flow",
            model_id="flowpilot_startup_control",
            risk_id="startup_control_result_stale",
            description="Startup-control evidence must be current after model or checker edits.",
            sources=(
                "simulations/flowpilot_startup_control_model.py",
                "simulations/run_flowpilot_startup_control_checks.py",
            ),
            result="simulations/flowpilot_startup_control_results.json",
            required_actions=(MATURITY_ACTION_REFRESH_EVIDENCE,),
        ),
        EvidenceGate(
            signal_id="dispatch_recipient_gate_evidence_fresh",
            signal_type=MODEL_MATURATION_SIGNAL_STALE_EVIDENCE,
            source_route="development_process_flow",
            model_id="flowpilot_dispatch_recipient_gate",
            risk_id="dispatch_recipient_result_stale",
            description="Dispatch-recipient gate evidence must be current after model or checker edits.",
            sources=(
                "simulations/flowpilot_dispatch_recipient_gate_model.py",
                "simulations/run_flowpilot_dispatch_recipient_gate_checks.py",
            ),
            result="simulations/flowpilot_dispatch_recipient_gate_results.json",
            required_actions=(MATURITY_ACTION_REFRESH_EVIDENCE,),
        ),
        EvidenceGate(
            signal_id="oversized_parent_child_maturity_visible",
            signal_type=MODEL_MATURATION_SIGNAL_OVERSIZED_MODEL,
            source_route="model_mesh",
            model_id="meta_capability_model_hierarchy",
            risk_id="large_parent_ok_masks_child_gap",
            description="Oversized parent models must expose child maturation and thin/full evidence status.",
            sources=(
                "simulations/flowpilot_model_hierarchy_model.py",
                "simulations/run_flowpilot_model_hierarchy_checks.py",
                "simulations/meta_thin_parent_results.json",
                "simulations/capability_thin_parent_results.json",
                f"{change_root}/specs/flowguard-model-hierarchy/spec.md",
            ),
            result="simulations/flowpilot_model_hierarchy_results.json",
            required_actions=(
                MATURITY_ACTION_SPLIT_CHILD_MODEL,
                MATURITY_ACTION_ADD_MODEL_OBLIGATION,
            ),
        ),
        EvidenceGate(
            signal_id="background_evidence_final_artifact_bound",
            signal_type=MODEL_MATURATION_SIGNAL_PROGRESS_ONLY_EVIDENCE,
            source_route="test_mesh",
            model_id="flowpilot_background_observability",
            risk_id="background_liveness_mistaken_for_completion",
            description="Background progress must not count as completion without final artifacts.",
            sources=(
                "simulations/flowpilot_test_tiering_model.py",
                "simulations/run_flowpilot_test_tiering_checks.py",
                f"{change_root}/specs/flowguard-background-observability/spec.md",
            ),
            result="simulations/flowpilot_test_tiering_results.json",
            required_actions=(
                MATURITY_ACTION_REFRESH_EVIDENCE,
                MATURITY_ACTION_ADD_MODEL_OBLIGATION,
                MATURITY_ACTION_DOWNGRADE_CLAIM,
            ),
        ),
        EvidenceGate(
            signal_id="unified_repair_runtime_test_conformance_current",
            signal_type=MODEL_MATURATION_SIGNAL_MISSING_CODE_BOUNDARY_OBSERVATION,
            source_route="flowguard_model_mesh",
            model_id="flowpilot_unified_repair_integrity",
            risk_id="unified_repair_model_exists_without_runtime_test_conformance",
            description=(
                "The unified repair model must not mature until its exact current "
                "runtime and native-test conformance evidence is present and no "
                "required conformance check is skipped."
            ),
            sources=(
                "simulations/flowpilot_unified_repair_integrity_model.py",
                "simulations/run_flowpilot_unified_repair_integrity_checks.py",
                "skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                "tests/test_flowpilot_core_runtime.py",
                "tests/test_flowpilot_high_standard_control_flow.py",
                "tests/test_flowpilot_complete_system_runtime.py",
                "tests/test_flowpilot_terminal_ledger_source_entries.py",
                "tests/router_runtime/route_mutation_transactions.py",
                "tests/router_runtime/route_mutation_parent_backward.py",
                "tests/router_runtime/route_mutation_sibling_replacement.py",
            ),
            result="simulations/flowpilot_unified_repair_integrity_results.json",
            required_actions=(
                MATURITY_ACTION_ADD_CODE_BOUNDARY_OBSERVATION,
                MATURITY_ACTION_REFRESH_EVIDENCE,
                MATURITY_ACTION_DOWNGRADE_CLAIM,
            ),
            require_unified_repair_conformance=True,
            blocks_model_maturation=True,
        ),
    )


def current_signals() -> tuple[ModelMaturationSignal, ...]:
    return tuple(_gate_signal(gate) for gate in evidence_gates())


def current_plan() -> ModelMaturationPlan:
    return ModelMaturationPlan(
        plan_id=PLAN_ID,
        model_id=MODEL_ID,
        risk_id="coarse_or_stale_flowpilot_model_confidence",
        signals=current_signals(),
        claim_scope="routine FlowPilot maintenance and local install confidence",
        require_full_closure=True,
        allow_scoped_claim=True,
    )


def current_report_dict() -> dict[str, Any]:
    plan = current_plan()
    report = review_model_maturation_loop(plan)
    gate_by_id = {gate.signal_id: gate for gate in evidence_gates()}
    blocking_signal_ids = [
        signal.signal_id
        for signal in plan.signals
        if gate_by_id[signal.signal_id].blocks_model_maturation
        and not signal.resolved
    ]
    payload = report.to_dict()
    payload["full_closure_ok"] = report.decision == MODEL_MATURATION_DECISION_CURRENT
    payload["signal_count"] = len(plan.signals)
    payload["hard_gate_ok"] = not blocking_signal_ids
    payload["blocking_signal_ids"] = blocking_signal_ids
    return payload


def known_bad_cases() -> tuple[dict[str, Any], ...]:
    return (
        {
            "name": "ack_only_closure",
            "signal_type": MODEL_MATURATION_SIGNAL_STATE_TOO_COARSE,
            "expected_actions": {
                MATURITY_ACTION_ADD_STATE_FIELD,
                MATURITY_ACTION_ADD_TRANSITION_CASE,
            },
        },
        {
            "name": "undisposed_replacement_packet",
            "signal_type": MODEL_MATURATION_SIGNAL_CHILD_REATTACHMENT_MISSING,
            "expected_actions": {
                MATURITY_ACTION_REATTACH_PARENT_MODEL,
                MATURITY_ACTION_ADD_TRANSITION_CASE,
            },
        },
        {
            "name": "prompt_contract_gap",
            "signal_type": MODEL_MATURATION_SIGNAL_MISSING_CODE_BOUNDARY_OBSERVATION,
            "expected_actions": {
                MATURITY_ACTION_ADD_CODE_BOUNDARY_OBSERVATION,
            },
        },
        {
            "name": "stale_evidence",
            "signal_type": MODEL_MATURATION_SIGNAL_STALE_EVIDENCE,
            "expected_actions": {MATURITY_ACTION_REFRESH_EVIDENCE},
        },
        {
            "name": "oversized_parent_masks_child_gap",
            "signal_type": MODEL_MATURATION_SIGNAL_OVERSIZED_MODEL,
            "expected_actions": {MATURITY_ACTION_SPLIT_CHILD_MODEL},
        },
        {
            "name": "progress_only_background_evidence",
            "signal_type": MODEL_MATURATION_SIGNAL_PROGRESS_ONLY_EVIDENCE,
            "expected_actions": {MATURITY_ACTION_REFRESH_EVIDENCE},
        },
        {
            "name": "singleton_duplicate_authority_gap",
            "signal_type": MODEL_MATURATION_SIGNAL_MISSING_MODEL_OBLIGATION,
            "expected_actions": {
                MATURITY_ACTION_ADD_MODEL_OBLIGATION,
                MATURITY_ACTION_ADD_CODE_BOUNDARY_OBSERVATION,
            },
        },
        {
            "name": "unified_repair_conformance_open",
            "signal_type": MODEL_MATURATION_SIGNAL_MISSING_CODE_BOUNDARY_OBSERVATION,
            "expected_actions": {
                MATURITY_ACTION_ADD_CODE_BOUNDARY_OBSERVATION,
                MATURITY_ACTION_REFRESH_EVIDENCE,
                MATURITY_ACTION_DOWNGRADE_CLAIM,
            },
        },
    )


def known_bad_report(case: dict[str, Any]) -> dict[str, Any]:
    signal = ModelMaturationSignal(
        signal_id=f"known_bad_{case['name']}",
        signal_type=str(case["signal_type"]),
        source_route="known_bad_maturation_sanity",
        model_id=MODEL_ID,
        risk_id=str(case["name"]),
        description=f"Known-bad maturation signal for {case['name']}",
        resolved=False,
        suggested_actions=tuple(case["expected_actions"]),
    )
    plan = ModelMaturationPlan(
        plan_id=f"known-bad-{case['name']}",
        model_id=MODEL_ID,
        risk_id=str(case["name"]),
        signals=(signal,),
        claim_scope="known-bad sanity",
        require_full_closure=True,
        allow_scoped_claim=True,
    )
    report = review_model_maturation_loop(plan)
    actions = set(report.recommended_actions)
    expected = set(case["expected_actions"])
    return {
        "name": case["name"],
        "ok": (not report.decision == MODEL_MATURATION_DECISION_CURRENT)
        and expected.issubset(actions),
        "expected_actions": sorted(expected),
        "actual_actions": sorted(actions),
        "decision": report.decision,
        "finding_count": len(report.findings),
    }


def build_report() -> dict[str, Any]:
    current = current_report_dict()
    known_bad = [known_bad_report(case) for case in known_bad_cases()]
    known_bad_ok = all(item["ok"] for item in known_bad)
    full_closure_ok = current["full_closure_ok"]
    hard_gate_ok = current["hard_gate_ok"]
    return {
        "ok": bool(current["ok"] and known_bad_ok and hard_gate_ok),
        "decision": (
            "model_maturation_scoped_claim"
            if hard_gate_ok
            else "current_runtime_gap"
        ),
        "result_type": "flowpilot_model_maturation",
        "claim_scope": "routine FlowPilot maintenance and local install confidence",
        "full_closure_ok": full_closure_ok,
        "hard_gate_ok": hard_gate_ok,
        "blocking_signal_ids": current["blocking_signal_ids"],
        "known_bad_ok": known_bad_ok,
        "current": current,
        "known_bad_sanity_checks": known_bad,
    }
