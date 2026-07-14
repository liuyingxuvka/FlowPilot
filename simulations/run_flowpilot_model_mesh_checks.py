"""Executable FlowGuard checks for the FlowPilot model mesh."""

from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Mapping, Sequence

from flowguard import (
    CompositeHandoffAcceptance,
    DevelopmentProcessPlan,
    FreshnessRule,
    ModelContractCoverageReceipt,
    ProcessArtifact,
    ProcessEvidence,
    ValidationRequirement,
    review_development_process_flow,
)
from flowguard.explorer import Explorer

try:  # pragma: no cover - direct-script fallback below.
    from . import flowpilot_model_mesh_model as model
except ImportError:  # pragma: no cover
    import flowpilot_model_mesh_model as model


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.compile_flowpilot_acceptance_testmesh_evidence import source_fingerprint
from simulations.flowpilot_evidence_truth import (
    derived_owner_proof,
    proof_bundle_report,
    read_json_object,
)


CONTRACT_COVERAGE_RESULT_SPECS = (
    (
        "receipt.ai_response_execution_closure",
        "flowpilot_ai_response_execution_closure",
        Path("tmp/test_results/formal_ai_submit_adversarial.json"),
        "ok",
    ),
    (
        "receipt.contract_exhaustion_mesh",
        "flowpilot_contract_exhaustion_mesh",
        Path("simulations/flowpilot_contract_exhaustion_mesh_results.json"),
        "ok",
    ),
    (
        "receipt.current_contract_cartesian",
        "flowpilot_current_contract_cartesian_matrix",
        Path("simulations/flowpilot_current_contract_cartesian_matrix_results.json"),
        "ok",
    ),
    (
        "receipt.fake_ai_runtime_replay",
        "flowpilot_fake_ai_runtime_replay",
        Path("simulations/flowpilot_fake_ai_runtime_replay_summary.json"),
        "ok",
    ),
    (
        "receipt.field_contract_lifecycle",
        "flowpilot_field_contracts",
        Path("simulations/flowpilot_field_contract_results.json"),
        "ok",
    ),
    (
        "receipt.model_test_alignment",
        "flowpilot_model_test_alignment",
        Path("simulations/flowpilot_model_test_alignment_results.json"),
        "alignment_ok",
    ),
    (
        "receipt.behavior_commitment_risk",
        "flowpilot_053_ppa_maintenance",
        Path("simulations/flowpilot_053_ppa_maintenance_results.json"),
        "ok",
    ),
    (
        "receipt.complete_workstream_orchestration",
        "flowpilot_complete_workstream_orchestration",
        Path("simulations/flowpilot_complete_workstream_orchestration_results.json"),
        "ok",
    ),
    (
        "receipt.ordinary_resource_discovery",
        "flowpilot_ordinary_resource_discovery",
        Path("simulations/flowpilot_ordinary_resource_discovery_results.json"),
        "ok",
    ),
    (
        "receipt.complete_workstream_fake_ai_execution",
        "flowpilot_complete_workstream_fake_ai_execution",
        Path("simulations/flowpilot_complete_workstream_fake_ai_results.json"),
        "ok",
    ),
    (
        "receipt.skillguard_current_contract",
        "flowpilot_skillguard_current_contract",
        Path("simulations/flowpilot_skillguard_current_contract_results.json"),
        "ok",
    ),
)

DPF_EXACT_EVIDENCE_IDS = (
    "evidence.bcl.flowpilot_053_behavior_commitments",
    "evidence.dcar.current_contract_cartesian",
    "evidence.mta.packet_result_family",
    "evidence.testmesh.acceptance_execution",
    "evidence.modelmesh.ai_response_parent",
    "evidence.risk.flowpilot_053_risk_evidence",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _coverage_case_ids(payload: Mapping[str, Any], model_id: str) -> tuple[str, ...]:
    if model_id == "flowpilot_ai_response_execution_closure":
        closure = payload.get("execution_closure") if isinstance(payload.get("execution_closure"), Mapping) else payload
        static = closure.get("static_mechanical_universe") if isinstance(closure, Mapping) else {}
        receipts = closure.get("receipts") if isinstance(closure, Mapping) else []
        ids = [str(item) for item in (static.get("case_ids") if isinstance(static, Mapping) else []) or []]
        ids.extend(
            str(row.get("case_id") or "")
            for row in receipts or []
            if isinstance(row, Mapping) and row.get("execution_status") in {"passed", "failed"}
        )
        return tuple(sorted({item for item in ids if item}))
    if model_id == "flowpilot_complete_workstream_fake_ai_execution":
        receipts = payload.get("profile_receipts") or []
        return tuple(
            sorted(
                {
                    f"profile:{row.get('profile_id')}"
                    for row in receipts
                    if isinstance(row, Mapping)
                    and row.get("profile_id")
                    and row.get("execution_status") in {"passed", "failed"}
                }
            )
        )
    return (f"case:{model_id}",)


def _contract_coverage_receipt_report(
    *,
    project_root: Path,
    evidence_manifest: Mapping[str, Any],
    result_path_overrides: Mapping[str, Path] | None = None,
    claim_scope: str = "release",
) -> dict[str, Any]:
    expected_source = source_fingerprint()
    manifest_source = str(evidence_manifest.get("source_fingerprint") or "")
    source_current = bool(manifest_source) and manifest_source == expected_source
    bundle = proof_bundle_report(
        evidence_manifest,
        expected_source_fingerprint=expected_source,
        required_scope=claim_scope,
    )
    nonpassing_proofs = list(bundle.get("failures") or ())
    proof_gate_ok = bool(bundle.get("ok"))
    overrides = result_path_overrides or {}
    child_receipts: list[ModelContractCoverageReceipt] = []
    result_rows: list[dict[str, Any]] = []
    for receipt_id, model_id, relative_path, ok_field in CONTRACT_COVERAGE_RESULT_SPECS:
        path = overrides.get(model_id, project_root / relative_path)
        payload: dict[str, Any] = {}
        parse_error = ""
        payload, parse_error = read_json_object(path)
        proof, reuse_ticket, reuse_gaps = derived_owner_proof(
            bundle,
            owner_id=f"modelmesh:{model_id}",
            covered_obligation_ids=(f"model-receipt:{model_id}",),
        )
        passed = bool(payload.get(ok_field)) and not parse_error and proof is not None and reuse_ticket is not None and not reuse_gaps
        current = passed and source_current and proof_gate_ok
        case_ids = _coverage_case_ids(payload, model_id)
        missing = () if passed else (f"case:{model_id}",)
        receipt = ModelContractCoverageReceipt(
            receipt_id=receipt_id,
            model_id=model_id,
            parent_model_id="flowpilot_model_mesh",
            status="covered" if current else "blocked",
            confidence="full" if current else "blocked",
            current=current,
            covered_case_ids=case_ids if passed else (),
            shard_ids=(f"shard:{model_id}",),
            interaction_group_ids=("ai_response_contract_evidence_mesh",),
            missing_case_ids=missing,
            blocked_case_ids=missing,
            finding_codes=tuple(
                code
                for code, active in (
                    ("model_result_missing_or_failed", not passed),
                    ("source_fingerprint_stale", not source_current),
                    ("proof_manifest_nonpassing", not proof_gate_ok),
                    ("proof_reuse_ticket_invalid", bool(reuse_gaps)),
                )
                if active
            ),
            metadata={
                "result_path": str(path),
                "result_sha256": _sha256(path) if path.is_file() else "",
                "ok_field": ok_field,
                "parse_error": parse_error,
                "source_fingerprint": manifest_source,
                "proof_artifact": proof.to_dict() if proof else None,
                "reuse_ticket": reuse_ticket.to_dict() if reuse_ticket else None,
            },
        )
        child_receipts.append(receipt)
        result_rows.append(receipt.to_dict())
    required_ids = tuple(receipt.receipt_id for receipt in child_receipts)
    consumed_ids = tuple(receipt.receipt_id for receipt in child_receipts if receipt.current and receipt.status == "covered")
    missing_receipts = tuple(sorted(set(required_ids) - set(consumed_ids)))
    parent_current = not missing_receipts and source_current and proof_gate_ok
    parent_receipt = ModelContractCoverageReceipt(
        receipt_id="receipt.flowpilot_ai_response_parent_mesh",
        model_id="flowpilot_model_mesh",
        status="covered" if parent_current else "blocked",
        confidence="full" if parent_current else "blocked",
        current=parent_current,
        covered_case_ids=tuple(
            sorted({case_id for receipt in child_receipts for case_id in receipt.covered_case_ids})
        ),
        shard_ids=tuple(receipt.shard_ids[0] for receipt in child_receipts),
        interaction_group_ids=("ai_response_contract_evidence_mesh",),
        required_child_receipt_ids=required_ids,
        consumed_child_receipt_ids=consumed_ids,
        blocked_case_ids=missing_receipts,
        finding_codes=("required_child_receipt_missing",) if missing_receipts else (),
        metadata={
            "affected_sibling_dispositions": {
                "flowpilot_current_contract_cartesian_matrix": "consumed_current_negative_source_purity",
                "flowpilot_fake_ai_runtime_replay": "consumed_current_runtime_replay",
                "flowpilot_field_contracts": "consumed_current_field_lifecycle",
                "flowpilot_complete_workstream_orchestration": "consumed_current_role_workstream_boundary",
                "flowpilot_ordinary_resource_discovery": "consumed_current_capability_inventory_and_material_contraction",
                "flowpilot_complete_workstream_fake_ai_execution": "consumed_current_execution_backed_workstream_and_resource_profiles",
                "flowpilot_skillguard_current_contract": "consumed_current_native_integrated_contract_projection",
            }
        },
    )
    composite = CompositeHandoffAcceptance(
        acceptance_id="handoff.ai_response_contract_to_release_mesh",
        case_id="case:ai_response_contract_evidence_mesh",
        route_ids=(
            "flowguard-contract-exhaustion-mesh",
            "flowguard-model-test-alignment",
            "flowguard-test-mesh",
            "flowguard-model-mesh",
        ),
        description="Contract exhaustion, execution receipts, TestMesh proof, MTA, and ModelMesh must all accept the same current source fingerprint.",
        metadata={"required_child_receipt_ids": list(required_ids)},
    )
    dpf = _development_process_report(
        claim_scope=claim_scope,
        source_fingerprint_value=manifest_source,
        bundle=bundle,
        parent_receipt=parent_receipt,
        child_receipts=child_receipts,
    )
    return {
        "ok": parent_current and dpf["ok"],
        "source_fingerprint_current": source_current,
        "expected_source_fingerprint": expected_source,
        "manifest_source_fingerprint": manifest_source,
        "proof_gate_ok": proof_gate_ok,
        "nonpassing_proofs": nonpassing_proofs,
        "child_receipts": result_rows,
        "parent_receipt": parent_receipt.to_dict(),
        "composite_handoff_acceptance": composite.to_dict(),
        "missing_child_receipt_ids": list(missing_receipts),
        "development_process_flow": dpf,
    }


def _development_process_report(
    *,
    claim_scope: str,
    source_fingerprint_value: str,
    bundle: Mapping[str, Any],
    parent_receipt: ModelContractCoverageReceipt,
    child_receipts: Sequence[ModelContractCoverageReceipt],
) -> dict[str, Any]:
    proof_by_id = {
        evidence_id: derived_owner_proof(
            bundle,
            owner_id=evidence_id,
            covered_obligation_ids=(evidence_id, "requirement.flowpilot.evidence_mesh"),
        )
        for evidence_id in DPF_EXACT_EVIDENCE_IDS
    }
    evidence = []
    for evidence_id in DPF_EXACT_EVIDENCE_IDS:
        proof, ticket, gaps = proof_by_id[evidence_id]
        evidence.append(
            ProcessEvidence(
                evidence_id=evidence_id,
                evidence_kind="route_report",
                producer_route=evidence_id.split(".")[1],
                status="passed" if proof is not None and ticket is not None and not gaps and parent_receipt.current else "not_run",
                covers_artifacts=("artifact.flowpilot.current_source",),
                covered_versions={"artifact.flowpilot.current_source": source_fingerprint_value},
                validation_requirement_ids=("requirement.flowpilot.evidence_mesh",),
                command=proof.command if proof else "",
                result_path=proof.result_path if proof else "",
                proof_artifact=proof,
                release_required=True,
                stale_reasons=tuple(gaps),
            )
        )
    plan = DevelopmentProcessPlan(
        process_id="flowpilot_evidence_mesh_release_closure",
        artifacts=(
            ProcessArtifact(
                artifact_id="artifact.flowpilot.current_source",
                artifact_type="source_tree",
                current_version=source_fingerprint_value,
                path="skills/flowpilot; simulations; tests",
                owner="FlowPilot",
            ),
        ),
        evidence=tuple(evidence),
        validation_requirements=(
            ValidationRequirement(
                requirement_id="requirement.flowpilot.evidence_mesh",
                required_artifact_ids=("artifact.flowpilot.current_source",),
                evidence_ids=DPF_EXACT_EVIDENCE_IDS,
                scope=claim_scope,
                release_required=True,
                v_model_pair=True,
                description="BCL/DCAR/MTA/TestMesh/ModelMesh/Risk exact current evidence ids are all required.",
            ),
        ),
        freshness_rules=(
            FreshnessRule(
                rule_id="freshness.flowpilot.evidence_mesh.source",
                upstream_artifact_id="artifact.flowpilot.current_source",
                invalidates_evidence_kinds=("route_report",),
                description="Any source change stales every exact evidence-mesh id.",
            ),
        ),
        decision_scope=claim_scope,
        require_proof_artifacts=True,
        release_deferred_allowed=False,
    )
    report = review_development_process_flow(plan)
    return {
        "ok": report.ok and parent_receipt.current and all(receipt.current for receipt in child_receipts),
        "claim_scope": claim_scope,
        "exact_evidence_ids": list(DPF_EXACT_EVIDENCE_IDS),
        "freshness_rule_ids": ["freshness.flowpilot.evidence_mesh.source"],
        "plan": plan.to_dict(),
        "report": report.to_dict(),
    }


REQUIRED_LABELS = {
    "select_valid_live_can_continue",
    "accept_valid_live_can_continue",
    "select_valid_conformance_can_continue",
    "accept_valid_conformance_can_continue",
    "select_valid_blocked_current_state",
    "accept_valid_blocked_current_state",
    "select_valid_missing_conformance_boundary",
    "accept_valid_missing_conformance_boundary",
    "select_abstract_green_used_to_continue",
    "reject_abstract_green_used_to_continue",
    "select_skipped_live_audit_used_to_continue",
    "reject_skipped_live_audit_used_to_continue",
    "select_stale_run_result_used",
    "reject_stale_run_result_used",
    "select_unregistered_model_authoritative",
    "reject_unregistered_model_authoritative",
    "select_hidden_active_blocker",
    "reject_hidden_active_blocker",
    "select_current_authority_mismatch",
    "reject_current_authority_mismatch",
    "select_collapsed_repair_outcomes",
    "reject_collapsed_repair_outcomes",
    "select_parent_repair_leaf_event",
    "reject_parent_repair_leaf_event",
    "select_packet_role_origin_unchecked",
    "reject_packet_role_origin_unchecked",
    "select_known_hazard_without_live_projection",
    "reject_known_hazard_without_live_projection",
    "select_sealed_body_opened_by_mesh",
    "reject_sealed_body_opened_by_mesh",
    "select_coverage_parse_errors_ignored",
    "reject_coverage_parse_errors_ignored",
    "select_install_requires_safe_continue",
    "reject_install_requires_safe_continue",
    "select_installed_skill_stale_accepted",
    "reject_installed_skill_stale_accepted",
    "select_missing_conformance_claims_runtime",
    "reject_missing_conformance_claims_runtime",
    "select_control_transaction_registry_missing",
    "reject_control_transaction_registry_missing",
    "select_control_transaction_partial_commit_accepted",
    "reject_control_transaction_partial_commit_accepted",
    "select_parent_child_lifecycle_conformance_missed",
    "reject_parent_child_lifecycle_conformance_missed",
    "select_parent_child_lifecycle_replay_skipped",
    "reject_parent_child_lifecycle_replay_skipped",
    "select_legal_next_action_policy_missing",
    "reject_legal_next_action_policy_missing",
    "select_legal_next_action_projection_missing",
    "reject_legal_next_action_projection_missing",
    "select_legal_next_action_conformance_failed",
    "reject_legal_next_action_conformance_failed",
    "select_route_authority_model_missing",
    "reject_route_authority_model_missing",
    "select_route_authority_projection_missing",
    "reject_route_authority_projection_missing",
    "select_route_authority_owner_conflict",
    "reject_route_authority_owner_conflict",
    "select_route_authority_wrong_path_accepted",
    "reject_route_authority_wrong_path_accepted",
    "select_route_authority_repair_feedback_missing",
    "reject_route_authority_repair_feedback_missing",
    "select_route_authority_fallback_accepted",
    "reject_route_authority_fallback_accepted",
    "select_route_authority_no_delta_repeat_accepted",
    "reject_route_authority_no_delta_repeat_accepted",
    "select_repeated_lifecycle_action_not_absorbed",
    "reject_repeated_lifecycle_action_not_absorbed",
    "select_lifecycle_guard_stuck_claimed_safe",
    "reject_lifecycle_guard_stuck_claimed_safe",
}

HAZARD_EXPECTED_FAILURES = {
    "abstract_green_used_to_continue": {
        "evidence_tier_below_required_runtime_confidence",
        "current_state_not_classified",
    },
    "skipped_live_audit_used_to_continue": {
        "live_required_but_audit_skipped",
        "current_state_not_classified",
    },
    "stale_run_result_used": {"stale_or_foreign_model_result_cannot_authorize_continue"},
    "unregistered_model_authoritative": {"unregistered_model_result_cannot_authorize_continue"},
    "hidden_active_blocker": {"active_blocker_cannot_be_safe_to_continue"},
    "current_authority_mismatch": {"current_authorities_disagree"},
    "collapsed_repair_outcomes": {"repair_outcome_events_collapsed"},
    "parent_repair_leaf_event": {"repair_event_not_compatible_with_active_node"},
    "packet_role_origin_unchecked": {"packet_authority_not_verified_before_acceptance"},
    "known_hazard_without_live_projection": {"known_hazard_lacks_live_projection"},
    "sealed_body_opened_by_mesh": {"mesh_must_not_open_sealed_bodies"},
    "coverage_parse_errors_ignored": {"coverage_parse_errors_must_block_green_result"},
    "install_requires_safe_continue": {"install_check_must_accept_classified_blocked_state"},
    "installed_skill_stale_accepted": {"installed_skill_not_synced_with_repo_model"},
    "missing_conformance_claims_runtime": {
        "evidence_tier_below_required_runtime_confidence",
        "missing_conformance_adapter_cannot_claim_runtime_conformance",
    },
    "control_transaction_registry_missing": {"control_transaction_registry_not_authoritative"},
    "control_transaction_partial_commit_accepted": {"control_transaction_commit_scope_incomplete"},
    "parent_child_lifecycle_conformance_missed": {"parent_child_lifecycle_conformance_failed"},
    "parent_child_lifecycle_replay_skipped": {"parent_child_lifecycle_conformance_replay_missing"},
    "legal_next_action_policy_missing": {
        "legal_next_action_policy_not_registered",
        "legal_next_action_projection_missing",
        "legal_next_action_conformance_failed",
    },
    "legal_next_action_projection_missing": {"legal_next_action_projection_missing"},
    "legal_next_action_conformance_failed": {"legal_next_action_conformance_failed"},
    "route_authority_model_missing": {
        "route_authority_singularity_model_not_registered",
        "route_authority_projection_missing",
        "route_authority_conformance_failed",
    },
    "route_authority_projection_missing": {"route_authority_projection_missing"},
    "route_authority_owner_conflict": {"route_authority_owner_conflict"},
    "route_authority_wrong_path_accepted": {"route_authority_wrong_path_not_rejected"},
    "route_authority_repair_feedback_missing": {"route_authority_repair_feedback_missing"},
    "route_authority_fallback_accepted": {"route_authority_fallback_not_rejected"},
    "route_authority_no_delta_repeat_accepted": {"route_authority_no_delta_repeat_not_absorbed"},
    "repeated_lifecycle_action_not_absorbed": {"repeated_lifecycle_action_must_block_mesh_green"},
    "lifecycle_guard_stuck_claimed_safe": {"lifecycle_guard_stuck_must_block_mesh_green"},
}


def _empty_report(ok: bool = True) -> Dict[str, Any]:
    return {
        "ok": ok,
        "labels_seen": [],
        "missing_labels": sorted(REQUIRED_LABELS),
        "violations": [],
    }


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|scenario={state.scenario}|decision={state.decision}|"
        f"tier={state.evidence_tier}->{state.required_tier}|"
        f"live_skip={state.live_audit_skipped}|conformance_skip={state.conformance_skipped}|"
        f"blocker={state.active_blocker_present},{state.safe_to_continue_claimed}|"
        f"auth={state.current_authorities_agree}|repair={state.collapsed_repair_outcome_events},"
        f"{state.repair_event_node_compatible}|packet={state.role_origin_checked},"
        f"{state.completed_agent_id_belongs_to_role}|sealed={state.sealed_body_opened_by_mesh}|"
        f"parse={state.coverage_parse_errors_ignored}|install={state.install_requires_safe_to_continue}|"
        f"sync={state.installed_skill_matches_repo},{state.local_sync_required}|"
        f"ctr={state.control_transaction_registry_registered},{state.control_transaction_registry_valid},"
        f"{state.control_transaction_commit_scope_complete}|parent_child="
        f"{state.parent_child_lifecycle_conformant},{state.parent_child_lifecycle_replayed}|legal="
        f"{state.legal_next_action_policy_registered},{state.legal_next_action_projected},"
        f"{state.legal_next_action_conformant}|route_auth="
        f"{state.route_authority_singularity_registered},{state.route_authority_projected},"
        f"{state.route_authority_conformant},{state.route_authority_owner_unique},"
        f"{state.route_authority_wrong_path_rejected},{state.route_authority_repair_feedback_present},"
        f"{state.route_authority_fallback_rejected},{state.route_authority_no_delta_repeat_absorbed}|"
        f"repeat={state.repeated_lifecycle_action_absorbed}|stuck={state.lifecycle_guard_control_plane_stuck}"
    )


def _walk_graph() -> Dict[str, Any]:
    labels_seen = set()
    violations: List[Dict[str, Any]] = []
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    states: List[model.State] = [initial]
    index = {initial: 0}
    edges: List[List[tuple[str, int]]] = []

    while queue:
        state = queue.popleft()
        source = index[state]
        while len(edges) <= source:
            edges.append([])
        failures = model.invariant_failures(state)
        if failures:
            violations.append({"state": _state_id(state), "failures": failures})
        for transition in model.next_safe_states(state):
            labels_seen.add(transition.label)
            if transition.state not in index:
                index[transition.state] = len(states)
                states.append(transition.state)
                queue.append(transition.state)
            edges[source].append((transition.label, index[transition.state]))

    missing_labels = sorted(REQUIRED_LABELS - labels_seen)
    return {
        "ok": not missing_labels and not violations,
        "states": states,
        "edges": edges,
        "state_count": len(states),
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "labels_seen": sorted(labels_seen),
        "missing_labels": missing_labels,
        "violations": violations,
    }


def _progress_report(graph: Mapping[str, Any]) -> Dict[str, Any]:
    states: List[model.State] = graph["states"]
    edges: List[List[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    can_reach_terminal = set(terminal)
    changed = True
    while changed:
        changed = False
        for idx, outgoing in enumerate(edges):
            if idx not in can_reach_terminal and any(target in can_reach_terminal for _label, target in outgoing):
                can_reach_terminal.add(idx)
                changed = True
    stuck = [
        _state_id(state)
        for idx, state in enumerate(states)
        if idx not in terminal and not edges[idx]
    ]
    cannot_reach_terminal = [
        _state_id(state)
        for idx, state in enumerate(states)
        if idx not in can_reach_terminal
    ]
    return {
        "ok": not stuck and not cannot_reach_terminal and 0 in can_reach_terminal,
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:10],
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "cannot_reach_terminal_samples": cannot_reach_terminal[:10],
    }


def _flowguard_report() -> Dict[str, Any]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=lambda _input, state, _trace: model.is_terminal(state),
        success_predicate=lambda state, _trace: model.is_success(state),
        required_labels=REQUIRED_LABELS,
    ).explore()
    return {
        "ok": report.ok,
        "summary": report.summary,
        "violation_count": len(report.violations),
        "dead_branch_count": len(report.dead_branches),
        "exception_branch_count": len(report.exception_branches),
        "reachability_failure_count": len(report.reachability_failures),
        "reachability_failures": [failure.message for failure in report.reachability_failures],
    }


def _graph_for_output(graph: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        key: value
        for key, value in graph.items()
        if key not in {"states", "edges"}
    } | {
        "terminal_state_count": sum(1 for state in graph["states"] if model.is_terminal(state)),
        "accepted_state_count": sum(1 for state in graph["states"] if state.status == "accepted"),
        "rejected_state_count": sum(1 for state in graph["states"] if state.status == "rejected"),
    }


def _terminal_state_for(name: str) -> model.State:
    selected = None
    for transition in model.next_safe_states(model.initial_state()):
        if transition.label == f"select_{name}":
            selected = transition.state
            break
    if selected is None:
        raise AssertionError(f"scenario was not selectable: {name}")
    terminals = list(model.next_safe_states(selected))
    if len(terminals) != 1:
        raise AssertionError(f"scenario did not have exactly one terminal transition: {name}")
    return terminals[0].state


def _contract_refinement_report() -> Dict[str, Any]:
    valid: List[str] = []
    rejected: List[str] = []
    bad_accepts: List[Dict[str, Any]] = []
    bad_rejects: List[Dict[str, Any]] = []

    for name, scenario in model.SCENARIOS.items():
        failures = model.mesh_failures(scenario)
        transition_state = _terminal_state_for(name)
        if transition_state.status == "accepted":
            valid.append(name)
            if failures:
                bad_accepts.append({"scenario": name, "failures": failures})
        else:
            rejected.append(name)
            if not failures:
                bad_rejects.append({"scenario": name})

    return {
        "ok": not bad_accepts and not bad_rejects,
        "accepted_scenarios": sorted(valid),
        "rejected_scenarios": sorted(rejected),
        "bad_accepts": bad_accepts,
        "bad_rejects": bad_rejects,
    }


def _hazard_report() -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    ok = True
    for name, state in model.hazard_states().items():
        failures = set(model.mesh_failures(state))
        expected = HAZARD_EXPECTED_FAILURES[name]
        missing = sorted(expected - failures)
        unexpected_empty = not failures
        if missing or unexpected_empty:
            ok = False
        rows.append(
            {
                "scenario": name,
                "expected_failures": sorted(expected),
                "observed_failures": sorted(failures),
                "missing_expected_failures": missing,
                "ok": not missing and not unexpected_empty,
            }
        )
    return {"ok": ok, "hazards": rows}


def _coverage_report() -> Dict[str, Any]:
    graph = _walk_graph()
    required_negative_count = len(model.NEGATIVE_SCENARIOS)
    reject_labels = [
        label
        for label in graph["labels_seen"]
        if label.startswith("reject_") and label.removeprefix("reject_") in model.NEGATIVE_SCENARIOS
    ]
    return {
        "ok": graph["ok"] and len(reject_labels) == required_negative_count,
        "graph": _graph_for_output(graph),
        "required_negative_count": required_negative_count,
        "negative_reject_labels_seen": sorted(reject_labels),
    }


def build_report(
    project_root: Path,
    run_id: str | None,
    include_live_audit: bool,
    evidence_manifest: Mapping[str, Any] | None = None,
    claim_scope: str = "release",
) -> Dict[str, Any]:
    graph = _walk_graph()
    progress = _progress_report(graph)
    flowguard = _flowguard_report()
    contract = _contract_refinement_report()
    hazards = _hazard_report()
    coverage = _coverage_report()
    live_projection = None
    if include_live_audit:
        live_projection = model.project_live_run(project_root=project_root, run_id=run_id)
    contract_coverage_receipts = None
    if evidence_manifest is not None:
        contract_coverage_receipts = _contract_coverage_receipt_report(
            project_root=project_root,
            evidence_manifest=evidence_manifest,
            claim_scope=claim_scope,
        )

    sections = [graph, progress, flowguard, contract, hazards, coverage]
    if live_projection is not None:
        sections.append(live_projection)
    if contract_coverage_receipts is not None:
        sections.append(contract_coverage_receipts)

    return {
        "schema_version": 1,
        "model": "flowpilot_model_mesh",
        "ok": all(section.get("ok", False) for section in sections),
        "graph": _graph_for_output(graph),
        "progress": progress,
        "flowguard_explorer": flowguard,
        "contract_refinement": contract,
        "hazard_review": hazards,
        "coverage": coverage,
        "live_run_projection": live_projection,
        "contract_coverage_receipts": contract_coverage_receipts,
    }


def _write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".", help="Repository root for live run projection.")
    parser.add_argument("--run-id", default=None, help="FlowPilot run id to project; defaults to current run.")
    parser.add_argument("--json-out", default=None, help="Write a JSON report to this path.")
    parser.add_argument("--skip-live-audit", action="store_true", help="Skip metadata-only current run projection.")
    parser.add_argument("--evidence-manifest", type=Path, help="Current TestMesh proof manifest used to close child coverage receipts.")
    parser.add_argument("--claim-scope", choices=("routine", "done", "release", "publish"), default="release")
    args = parser.parse_args(argv)

    evidence_manifest = None
    if args.evidence_manifest:
        evidence_manifest, manifest_error = read_json_object(args.evidence_manifest)
        if manifest_error:
            raise SystemExit(manifest_error)
        if not isinstance(evidence_manifest, Mapping):
            raise SystemExit("evidence manifest must be a JSON object")

    report = build_report(
        project_root=Path(args.project_root),
        run_id=args.run_id,
        include_live_audit=not args.skip_live_audit,
        evidence_manifest=evidence_manifest,
        claim_scope=args.claim_scope,
    )
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.json_out:
        _write_json(Path(args.json_out), report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
