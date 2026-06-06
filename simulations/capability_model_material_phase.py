"""Phase helper extracted from :mod:`capability_model`."""

from __future__ import annotations

from typing import Iterable

if __package__:
    from . import capability_model as _model
else:
    import capability_model as _model

_REQUIRED_MODEL_NAMES = (
    "FunctionResult",
    "Iterable",
    "State",
    "_step",
)
for _name in _REQUIRED_MODEL_NAMES:
    globals()[_name] = getattr(_model, _name)
del _name

__all__ = ["apply_material_phase"]


def apply_material_phase(self, state: State) -> Iterable[FunctionResult]:
    if not state.material_sources_scanned:
        yield _step(
            state,
            label="material_sources_scanned",
            action="authorized worker scans user-provided and repository-local materials before capability route design",
            material_sources_scanned=True,
        )
        return

    if not state.material_source_summaries_written:
        yield _step(
            state,
            label="material_source_summaries_written",
            action="authorized worker writes purpose, contents, and current-state summaries for capability-relevant materials",
            material_source_summaries_written=True,
        )
        return

    if not state.material_source_quality_classified:
        yield _step(
            state,
            label="material_source_quality_classified",
            action="authorized worker classifies source authority, freshness, contradictions, missing context, and readiness",
            material_source_quality_classified=True,
        )
        return

    if not state.local_skill_inventory_written:
        yield _step(
            state,
            label="local_skill_inventory_written",
            action="authorized worker inventories locally available skills and host capabilities as candidate resources before the material packet is finalized",
            local_skill_inventory_written=True,
        )
        return

    if not state.local_skill_inventory_candidate_classified:
        yield _step(
            state,
            label="local_skill_inventory_candidate_classified",
            action="authorized worker classifies local skills as candidate-only resources without treating availability as PM approval to use them",
            local_skill_inventory_candidate_classified=True,
        )
        return

    if not state.material_intake_packet_written:
        yield _step(
            state,
            label="material_intake_packet_written",
            action="authorized worker writes the Material Intake Packet, including local skill inventory, before PM capability planning",
            material_intake_packet_written=True,
        )
        return

    if not state.material_reviewer_direct_source_probe_done:
        yield _step(
            state,
            label="material_reviewer_direct_source_probe_done",
            action="human-like reviewer opens or samples actual materials and tests whether the packet could be summary-only before sufficiency approval",
            material_reviewer_direct_source_probe_done=True,
        )
        return

    if not state.material_reviewer_sufficiency_checked:
        yield _step(
            state,
            label="material_reviewer_sufficiency_checked",
            action="human-like reviewer checks whether the material packet is clear and complete enough for PM capability planning",
            material_reviewer_sufficiency_checked=True,
        )
        return

    if not state.material_reviewer_sufficiency_approved:
        yield _step(
            state,
            label="material_reviewer_sufficiency_approved",
            action="human-like reviewer approves that the Material Intake Packet is PM-ready or blocks capability planning",
            material_reviewer_sufficiency_approved=True,
        )
        return

    if not state.pm_material_understanding_memo_written:
        yield _step(
            state,
            label="pm_material_understanding_memo_written",
            action="project manager writes a material understanding memo with source-claim matrix, open questions, and capability implications",
            pm_material_understanding_memo_written=True,
        )
        return

    if not state.pm_material_complexity_classified:
        yield _step(
            state,
            label="pm_material_complexity_classified",
            action="project manager classifies material complexity as simple, normal, or messy/raw before capability planning",
            pm_material_complexity_classified=True,
        )
        return

    if not state.pm_material_discovery_decision_recorded:
        yield _step(
            state,
            label="pm_material_discovery_decision_recorded",
            action="project manager records whether materials can feed capability routing directly or require a formal discovery, cleanup, modeling, or validation subtree",
            pm_material_discovery_decision_recorded=True,
        )
        return

    if not state.pm_material_research_decision_recorded:
        yield _step(
            state,
            label="pm_material_research_decision_not_required",
            action="project manager records that reviewed materials are sufficient and no formal research package is required before capability architecture",
            pm_material_research_decision_recorded=True,
            material_research_need="not_required",
        )
        yield _step(
            state,
            label="pm_material_research_decision_requires_package",
            action="project manager records a material gap that must become a formal research, mechanism-discovery, evidence-collection, or experiment package before capability architecture",
            pm_material_research_decision_recorded=True,
            material_research_need="required",
        )
        return

    if state.material_research_need == "required":
        if not state.pm_research_package_written:
            yield _step(
                state,
                label="pm_research_package_written",
                action="project manager writes a bounded research package with question, route impact, allowed sources, worker owner, evidence standard, reviewer checks, and stop conditions",
                pm_research_package_written=True,
            )
            return

        if not state.research_tool_capability_decision_recorded:
            yield _step(
                state,
                label="research_tool_capability_decision_recorded",
                action="project manager records whether local, browser, web search, account, or user-provided sources are available and routes missing capabilities to user clarification, repair, or block",
                research_tool_capability_decision_recorded=True,
            )
            return

        if not state.research_worker_report_returned:
            yield _step(
                state,
                label="research_worker_report_returned",
                action="assigned worker searches, inspects, experiments, or reconciles sources and returns a research package report with raw evidence pointers and limitations",
                research_worker_report_returned=True,
            )
            return

        if not state.research_reviewer_direct_source_check_done:
            yield _step(
                state,
                label="research_reviewer_direct_source_check_done",
                action="human-like reviewer directly checks original sources, search results, logs, screenshots, or experiment outputs instead of trusting the worker summary",
                research_reviewer_direct_source_check_done=True,
            )
            return

        if not state.research_reviewer_sufficiency_passed:
            if not state.research_reviewer_rework_required:
                yield _step(
                    state,
                    label="research_reviewer_sufficiency_passed",
                    action="human-like reviewer approves the research package as sufficient for PM capability decisions after direct source checks",
                    research_reviewer_sufficiency_passed=True,
                )
                yield _step(
                    state,
                    label="research_reviewer_rework_required",
                    action="human-like reviewer rejects the worker research output as shallow, unsupported, stale, contradictory, or missing required source checks",
                    research_reviewer_rework_required=True,
                )
                return

            if not state.research_worker_rework_completed:
                yield _step(
                    state,
                    label="research_worker_rework_completed",
                    action="assigned worker reruns or expands the research package according to reviewer blockers and returns corrected evidence",
                    research_worker_rework_completed=True,
                )
                return

            if not state.research_reviewer_recheck_done:
                yield _step(
                    state,
                    label="research_reviewer_recheck_done",
                    action="human-like reviewer rechecks the corrected research output against the original package and prior blockers",
                    research_reviewer_recheck_done=True,
                )
                return

            yield _step(
                state,
                label="research_reviewer_sufficiency_passed",
                action="human-like reviewer approves the reworked research package after direct source recheck",
                research_reviewer_sufficiency_passed=True,
                research_reviewer_rework_required=False,
                research_worker_rework_completed=False,
                research_reviewer_recheck_done=False,
            )
            return

        if not state.pm_research_result_absorbed_or_route_mutated:
            yield _step(
                state,
                label="pm_research_result_absorbed_or_route_mutated",
                action="project manager absorbs approved research into material understanding, capability architecture inputs, route mutation, or a blocked/user-clarification decision",
                pm_research_result_absorbed_or_route_mutated=True,
            )
            return

        yield _step(
            state,
            label="material_research_gap_closed",
            action="project manager marks the approved research gap closed after preserving absorption or route-mutation evidence so downstream planning no longer branches on stale research state",
            material_research_need="not_required",
            pm_research_package_written=False,
            research_tool_capability_decision_recorded=False,
            research_worker_report_returned=False,
            research_reviewer_direct_source_check_done=False,
            research_reviewer_rework_required=False,
            research_worker_rework_completed=False,
            research_reviewer_recheck_done=False,
            research_reviewer_sufficiency_passed=False,
            pm_research_result_absorbed_or_route_mutated=False,
        )
        return

    if not state.product_function_architecture_pm_synthesized:
        yield _step(
            state,
            label="product_function_architecture_pm_synthesized",
            action="project manager synthesizes interrogated capability ideas into a product-function architecture decision package before contract freeze",
            product_function_architecture_pm_synthesized=True,
        )
        return

    if not state.product_function_high_standard_posture_written:
        yield _step(
            state,
            label="product_function_high_standard_posture_written",
            action="project manager records that a FlowPilot invocation means an important project and sets the highest reasonably achievable worker standard, not the lowest viable route or a self-effort estimate",
            product_function_high_standard_posture_written=True,
        )
        return

    if not state.product_function_target_and_failure_bar_written:
        yield _step(
            state,
            label="product_function_target_and_failure_bar_written",
            action="project manager describes the strongest feasible product target and the rough, embarrassing, or placeholder results that must be rejected before completion",
            product_function_target_and_failure_bar_written=True,
        )
        return

    if not state.product_function_minimum_sufficient_complexity_review_written:
        yield _step(
            state,
            label="product_function_minimum_sufficient_complexity_review_written",
            action="project manager records the minimum sufficient complexity review for capability planning, rejecting features, surfaces, dependencies, or artifacts that do not change user outcome or proof strength",
            product_function_minimum_sufficient_complexity_review_written=True,
        )
        return

    if not state.product_function_semantic_fidelity_policy_written:
        yield _step(
            state,
            label="product_function_semantic_fidelity_policy_written",
            action="project manager maps user goals to material evidence and records that source gaps require discovery, staged delivery, or user clarification instead of silent semantic downgrade",
            product_function_semantic_fidelity_policy_written=True,
        )
        return

    if not state.product_function_user_task_map_written:
        yield _step(
            state,
            label="product_function_user_task_map_written",
            action="write target users, situations, jobs-to-be-done, and decision points before capability routing",
            product_function_user_task_map_written=True,
        )
        return

    if not state.product_function_capability_map_written:
        yield _step(
            state,
            label="product_function_capability_map_written",
            action="write must, should, optional, and rejected capability decisions before child-skill route discovery",
            product_function_capability_map_written=True,
        )
        return

    if not state.product_function_feature_decisions_written:
        yield _step(
            state,
            label="product_function_feature_decisions_written",
            action="bind each accepted capability to a user task and reject feature ideas that do not earn their place",
            product_function_feature_decisions_written=True,
        )
        return

    if not state.product_function_display_rationale_written:
        yield _step(
            state,
            label="product_function_display_rationale_written",
            action="record why each visible text, state, control, or status belongs in the product and what user decision it changes",
            product_function_display_rationale_written=True,
        )
        return

    if not state.product_function_gap_review_done:
        yield _step(
            state,
            label="product_function_missing_feature_review_done",
            action="review likely missing high-value capabilities before the route turns them into local implementation tasks",
            product_function_gap_review_done=True,
        )
        return

    if not state.product_function_negative_scope_written:
        yield _step(
            state,
            label="product_function_negative_scope_written",
            action="write non-goals and rejected displays to keep capability routing from adding accidental work",
            product_function_negative_scope_written=True,
        )
        return

    if not state.product_function_acceptance_matrix_written:
        yield _step(
            state,
            label="product_function_acceptance_matrix_written",
            action="write functional acceptance matrix with inputs, outputs, states, failure cases, and evidence for each core capability",
            product_function_acceptance_matrix_written=True,
        )
        return

    if not state.root_acceptance_thresholds_defined:
        yield _step(
            state,
            label="root_acceptance_thresholds_defined",
            action="project manager defines early hard acceptance thresholds for important capability requirements before contract freeze",
            root_acceptance_thresholds_defined=True,
        )
        return

    if not state.root_acceptance_proof_matrix_written:
        yield _step(
            state,
            label="root_acceptance_proof_matrix_written",
            action="project manager writes the root proof matrix mapping hard capability requirements to experiments, inspections, evidence, owners, and approvers",
            root_acceptance_proof_matrix_written=True,
        )
        return

    if not state.standard_scenario_pack_selected:
        yield _step(
            state,
            label="standard_scenario_pack_selected",
            action="project manager selects the standard scenario pack for terminal replay of happy paths, edge cases, regressions, lifecycle, and PM-risk scenarios",
            standard_scenario_pack_selected=True,
        )
        return

    if not state.product_architecture_flowguard_operator_adversarial_probe_done:
        yield _step(
            state,
            label="product_architecture_flowguard_operator_adversarial_probe_done",
            action="product-scope FlowGuard operator checks modelability, missing state fields, unsupported claims, and failure paths before approving the PM architecture",
            product_architecture_flowguard_operator_adversarial_probe_done=True,
        )
        return

    if not state.product_function_architecture_flowguard_operator_product_scope_approved:
        yield _step(
            state,
            label="product_function_architecture_flowguard_operator_product_scope_approved",
            action="product-scope FlowGuard operator approves that the PM product-function architecture can drive capability and child-skill routing",
            product_function_architecture_flowguard_operator_product_scope_approved=True,
        )
        return

    if not state.product_function_architecture_reviewer_challenged:
        if not state.product_architecture_reviewer_adversarial_probe_done:
            yield _step(
                state,
                label="product_architecture_reviewer_adversarial_probe_done",
                action="human-like reviewer attacks the PM product architecture against user tasks, inspected materials, missing features, unnecessary visible text, and weak failure states",
                product_architecture_reviewer_adversarial_probe_done=True,
            )
            return
        yield _step(
            state,
            label="product_function_architecture_reviewer_challenged",
            action="human-like reviewer challenges the pre-implementation product-function architecture for usefulness, missing expected functions, and unnecessary visible text",
            product_function_architecture_reviewer_challenged=True,
        )
        return

    if not state.product_architecture_self_interrogation_record_written:
        yield _step(
            state,
            label="product_architecture_self_interrogation_record_written",
            action="PM writes a durable product-architecture self-interrogation record after FlowGuard operator and reviewer challenge so capability doubts have a downstream destination",
            product_architecture_self_interrogation_record_written=True,
        )
        return

    if not state.product_architecture_self_interrogation_findings_dispositioned:
        yield _step(
            state,
            label="product_architecture_self_interrogation_findings_dispositioned",
            action="PM incorporates, defers, ledgers, rejects, or waives product-architecture self-interrogation findings before contract freeze",
            product_architecture_self_interrogation_findings_dispositioned=True,
        )
        return

    if not state.contract_frozen:
        yield _step(
            state,
            label="contract_frozen",
            action="freeze acceptance contract from the PM product-function architecture after startup and product-architecture self-interrogation findings are durably dispositioned",
            contract_frozen=True,
        )
        return
