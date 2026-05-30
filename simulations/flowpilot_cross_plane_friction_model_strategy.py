"""Repair strategy table for the FlowPilot cross-plane friction model."""

from __future__ import annotations

REPAIR_ACTIONS = {
    "canonical_terminal_lifecycle": {
        "title": "Canonical terminal lifecycle transaction",
        "fixes": [
            "terminal_authority_mismatch",
            "terminal_control_blocker_not_cleared",
            "terminal_heartbeat_still_active",
        ],
        "scope": (
            "Terminal closure writer and reconcile_current_run only; no changes "
            "to role report content or route semantics."
        ),
        "proof_obligation": (
            "A closed closure suite implies lifecycle/run_lifecycle.json, "
            "router_state, current.json, index.json, execution_frontier, and "
            "route_state_snapshot all agree on terminal status."
        ),
    },
    "material_packet_contract_and_lineage": {
        "title": "Material packet envelope contract and lineage normalization",
        "fixes": [
            "material_dispatch_output_contract_mismatch",
            "material_dispatch_write_target_missing",
            "unsupported_material_packet_lineage_split",
        ],
        "scope": (
            "Material-scan packet creation and unsupported_historical migration/quarantine only; "
            "do not let Controller read sealed bodies."
        ),
        "proof_obligation": (
            "Every material-scan packet envelope has to_role-matched output_contract, "
            "an explicit expected result write target, and canonical replacement_for "
            "or supersedes lineage."
        ),
    },
    "frontier_based_route_projection": {
        "title": "Frontier-based route snapshot projection",
        "fixes": [
            "route_state_snapshot_status_mismatch",
            "route_state_snapshot_completed_checklists_pending",
            "selected_state_conflated_with_completed_state",
        ],
        "scope": (
            "Snapshot builder status overlay only; avoid changing flow.json as the "
            "authored route source."
        ),
        "proof_obligation": (
            "execution_frontier.completed_nodes projects completed status and "
            "completed checklists before raw flow.json status is displayed."
        ),
    },
    "cockpit_adapter_completion_projection": {
        "title": "Cockpit adapter completion and active-tab projection",
        "fixes": [
            "cockpit_completed_node_status_mismatch",
            "cockpit_completed_node_checklist_status_mismatch",
            "cockpit_closed_run_exposed_as_active_tab",
        ],
        "scope": (
            "CurrentRunAdapter projection only; no UI redesign or new product features."
        ),
        "proof_obligation": (
            "Cockpit uses the same completed-node overlay as route_state_snapshot "
            "and exposes active tabs only for active frontier statuses."
        ),
    },
    "reviewer_event_taxonomy_closure": {
        "title": "Reviewer blocker event taxonomy closure",
        "fixes": ["role_event_taxonomy_gap"],
        "scope": "EXTERNAL_EVENTS aliases/normalization and tests only.",
        "proof_obligation": (
            "Every emitted reviewer block event is accepted or normalized before "
            "router resolution."
        ),
    },
    "gate_outcome_contracts": {
        "title": "Gate outcome contracts for reviewer/officer gates",
        "fixes": ["gate_outcome_contract_pass_only"],
        "scope": "Gate outcome metadata, wait actions, and repair routing for role gates.",
        "proof_obligation": (
            "Every reviewer/officer gate has a routable pass outcome and a routable "
            "non-pass outcome that does not advance stale approvals."
        ),
    },
    "active_node_completion_idempotency": {
        "title": "Active-node-scoped completion idempotency",
        "fixes": ["node_completion_idempotency_global_only"],
        "scope": "Completion repeatability guard and focused router tests only.",
        "proof_obligation": (
            "A completed prior node cannot prevent the current active node from "
            "writing its own completion ledger."
        ),
    },
    "source_layout_policy_alignment": {
        "title": "Source layout and install audit alignment",
        "fixes": [
            "install_audit_layout_policy_conflict",
            "installed_skill_source_drift",
        ],
        "scope": "Install audit policy and install/sync verification only.",
        "proof_obligation": (
            "The audit either accepts flowpilot_cockpit as first-class source or "
            "it is moved out of source; installed skill hashes match repository source."
        ),
    },
    "six_role_readiness_gate": {
        "title": "Standard role-binding readiness gate",
        "fixes": ["six_role_liveness_unproven"],
        "scope": "Startup/resume readiness record or early blocker only.",
        "proof_obligation": (
            "A role-binding run cannot begin route work until all standard roles are "
            "ready or a router-visible blocker stops it."
        ),
    },
}


def minimal_repair_strategy(findings: list[dict[str, object]]) -> dict[str, object]:
    codes = {str(finding.get("code") or "") for finding in findings}
    actions: list[dict[str, object]] = []
    for action_id, action in REPAIR_ACTIONS.items():
        fixes = set(action["fixes"])
        if codes.intersection(fixes):
            actions.append({"id": action_id, **action})
    if not actions:
        actions.append(
            {
                "id": "no_current_findings",
                "title": "No repair required by current cross-plane scan",
                "fixes": [],
                "scope": "No production mutation.",
                "proof_obligation": "All cross-plane invariants already hold.",
            }
        )
    return {
        "principle": (
            "Patch only the failing projection or transaction boundary; keep "
            "Controller envelope-only and avoid product-content rewrites."
        ),
        "actions": actions,
        "overfix_guards": [
            "Do not replace FlowPilot's route model with a UI-only state model.",
            "Do not mark human-review final report notes as unfinished route nodes.",
            "Do not open sealed bodies in runtime Controller logic.",
            "Do not hide history by deleting it; hide it from active task catalogs.",
        ],
    }


__all__ = ["REPAIR_ACTIONS", "minimal_repair_strategy"]
