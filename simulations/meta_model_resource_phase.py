"""Phase helper extracted from :mod:`meta_model`."""

from __future__ import annotations

from typing import Iterable

if __package__:
    from . import meta_model as _model
else:
    import meta_model as _model

_REQUIRED_MODEL_NAMES = (
    "FunctionResult",
    "Iterable",
    "State",
    "_step",
)
for _name in _REQUIRED_MODEL_NAMES:
    globals()[_name] = getattr(_model, _name)
del _name

__all__ = ["apply_resource_phase"]


def apply_resource_phase(self, state: State) -> Iterable[FunctionResult]:
    if not state.startup_self_interrogation_pm_ratified:
        yield _step(
            state,
            label="startup_self_interrogation_pm_ratified",
            action="project manager ratifies startup self-interrogation scope, risk layers, question count, decision set, and PM disposition of durable findings before route/model gates",
            startup_self_interrogation_pm_ratified=True,
            startup_self_interrogation_findings_dispositioned=True,
            active_node="ordinary_resource_discovery",
        )
        return

    if not state.ordinary_resource_discovery_child_registered:
        yield _step(
            state,
            label="ordinary_resource_discovery_child_registered",
            action="register the existing focused FlowGuard child that owns mandatory shallow local skill inventory, PM candidate selection, and ordinary evidence-work behavior",
            ordinary_resource_discovery_child_registered=True,
            active_node="check_ordinary_resource_discovery_child",
        )
        return
    if not state.ordinary_resource_discovery_child_passed:
        yield _step(
            state,
            label="ordinary_resource_discovery_child_passed",
            action="run the focused ordinary-resource-discovery FlowGuard model across both no-extra-work and ordinary-work branches without a special material gate",
            ordinary_resource_discovery_child_passed=True,
            active_node="verify_ordinary_resource_discovery_evidence_freshness",
        )
        return

    if not state.ordinary_resource_discovery_evidence_current:
        yield _step(
            state,
            label="ordinary_resource_discovery_evidence_current",
            action="bind the child model result to current source and focused Runtime/fake-AI evidence before product architecture begins",
            ordinary_resource_discovery_evidence_current=True,
            active_node="product_function_architecture",
        )
        return

    if not state.control_plane_resource_boundedness_child_registered:
        yield _step(
            state,
            label="control_plane_resource_boundedness_child_registered",
            action="register the focused FlowGuard child that owns no-change writes, idempotent control effects, bounded progress/evidence, and fail-closed retention",
            control_plane_resource_boundedness_child_registered=True,
            active_node="check_control_plane_resource_boundedness_child",
        )
        return
    if not state.control_plane_resource_boundedness_child_passed:
        yield _step(
            state,
            label="control_plane_resource_boundedness_child_passed",
            action="run the focused control-plane resource-boundedness scenario and known-bad matrix",
            control_plane_resource_boundedness_child_passed=True,
            active_node="verify_control_plane_resource_boundedness_evidence",
        )
        return
    if not state.control_plane_resource_boundedness_evidence_current:
        yield _step(
            state,
            label="control_plane_resource_boundedness_evidence_current",
            action="bind the resource-boundedness child result to current runtime, validation, and retention owners",
            control_plane_resource_boundedness_evidence_current=True,
            active_node="product_function_architecture",
        )
        return

    if not state.product_function_architecture_pm_synthesized:
        yield _step(
            state,
            label="product_function_architecture_pm_synthesized",
            action="project manager synthesizes interrogated ideas into a product-function architecture decision package before contract freeze",
            product_function_architecture_pm_synthesized=True,
            active_node="write_product_function_high_standard_posture",
        )
        return

    if not state.product_function_high_standard_posture_written:
        yield _step(
            state,
            label="product_function_high_standard_posture_written",
            action="project manager records that a FlowPilot invocation means an important project and sets the highest reasonably achievable worker standard, not the lowest viable route or a self-effort estimate",
            product_function_high_standard_posture_written=True,
            active_node="write_product_function_target_and_failure_bar",
        )
        return

    if not state.product_function_target_and_failure_bar_written:
        yield _step(
            state,
            label="product_function_target_and_failure_bar_written",
            action="project manager describes the strongest feasible product target and the rough, embarrassing, or placeholder results that must be rejected before completion",
            product_function_target_and_failure_bar_written=True,
            active_node="write_product_function_minimum_sufficient_complexity_review",
        )
        return

    if not state.product_function_minimum_sufficient_complexity_review_written:
        yield _step(
            state,
            label="product_function_minimum_sufficient_complexity_review_written",
            action="project manager records the minimum sufficient complexity review, rejecting features, surfaces, dependencies, or artifacts that do not change user outcome or proof strength",
            product_function_minimum_sufficient_complexity_review_written=True,
            active_node="write_product_function_semantic_fidelity_policy",
        )
        return

    if not state.product_function_semantic_fidelity_policy_written:
        yield _step(
            state,
            label="product_function_semantic_fidelity_policy_written",
            action="project manager maps user goals to material evidence and records that source gaps require discovery, staged delivery, or user clarification instead of silent semantic downgrade",
            product_function_semantic_fidelity_policy_written=True,
            active_node="write_product_function_user_task_map",
        )
        return

    if not state.product_function_user_task_map_written:
        yield _step(
            state,
            label="product_function_user_task_map_written",
            action="write the target users, situations, jobs-to-be-done, and decision points that the product must serve",
            product_function_user_task_map_written=True,
            active_node="write_product_function_capability_map",
        )
        return

    if not state.product_function_capability_map_written:
        yield _step(
            state,
            label="product_function_capability_map_written",
            action="write the must, should, optional, and rejected product capabilities before route generation",
            product_function_capability_map_written=True,
            active_node="write_product_function_feature_decisions",
        )
        return

    if not state.product_function_feature_decisions_written:
        yield _step(
            state,
            label="product_function_feature_decisions_written",
            action="record feature necessity decisions that bind each accepted feature to a user task and reject features without product value",
            product_function_feature_decisions_written=True,
            active_node="write_product_function_display_rationale",
        )
        return

    if not state.product_function_display_rationale_written:
        yield _step(
            state,
            label="product_function_display_rationale_written",
            action="record why each visible text, state, control, card, or status should be shown and what user decision it changes",
            product_function_display_rationale_written=True,
            active_node="review_product_function_gaps",
        )
        return

    if not state.product_function_gap_review_done:
        yield _step(
            state,
            label="product_function_missing_feature_review_done",
            action="review likely missing high-value functions before implementation turns the route into local tasks",
            product_function_gap_review_done=True,
            active_node="write_product_function_negative_scope",
        )
        return

    if not state.product_function_negative_scope_written:
        yield _step(
            state,
            label="product_function_negative_scope_written",
            action="write explicit non-goals and rejected displays so the route does not grow accidental features",
            product_function_negative_scope_written=True,
            active_node="write_product_function_acceptance_matrix",
        )
        return

    if not state.product_function_acceptance_matrix_written:
        yield _step(
            state,
            label="product_function_acceptance_matrix_written",
            action="write a functional acceptance matrix covering inputs, outputs, states, failure cases, and required evidence for each core capability",
            product_function_acceptance_matrix_written=True,
            active_node="define_root_acceptance_thresholds",
        )
        return

    if not state.root_acceptance_thresholds_defined:
        yield _step(
            state,
            label="root_acceptance_thresholds_defined",
            action="project manager defines early hard acceptance thresholds for the important root requirements before contract freeze",
            root_acceptance_thresholds_defined=True,
            active_node="write_root_acceptance_proof_matrix",
        )
        return

    if not state.root_acceptance_proof_matrix_written:
        yield _step(
            state,
            label="root_acceptance_proof_matrix_written",
            action="project manager writes the root proof matrix mapping each hard requirement to minimum experiment, inspection, evidence, owner, and approver",
            root_acceptance_proof_matrix_written=True,
            active_node="select_standard_scenario_pack",
        )
        return

    if not state.standard_scenario_pack_selected:
        yield _step(
            state,
            label="standard_scenario_pack_selected",
            action="project manager selects the standard scenario pack for terminal replay of happy paths, edge cases, regressions, lifecycle, and PM-risk scenarios",
            standard_scenario_pack_selected=True,
            active_node="flowguard_operator_product_scope_probe_product_function_architecture",
        )
        return

    if not state.product_architecture_flowguard_operator_adversarial_probe_done:
        yield _step(
            state,
            label="product_architecture_flowguard_operator_adversarial_probe_done",
            action="product-scope FlowGuard operator checks modelability, missing state fields, unsupported claims, and failure paths before approving the PM architecture",
            product_architecture_flowguard_operator_adversarial_probe_done=True,
            active_node="approve_product_function_architecture",
        )
        return

    if not state.product_function_architecture_flowguard_operator_product_scope_approved:
        yield _step(
            state,
            label="product_function_architecture_flowguard_operator_product_scope_approved",
            action="product-scope FlowGuard operator approves that the PM product-function architecture is modelable and strong enough to freeze the contract from",
            product_function_architecture_flowguard_operator_product_scope_approved=True,
            active_node="reviewer_probe_product_function_architecture",
        )
        return

    if not state.product_architecture_reviewer_adversarial_probe_done:
        yield _step(
            state,
            label="product_architecture_reviewer_adversarial_probe_done",
            action="human-like reviewer attacks the PM product architecture against user tasks, inspected materials, missing features, unnecessary visible text, and weak failure states",
            product_architecture_reviewer_adversarial_probe_done=True,
            active_node="challenge_product_function_architecture",
        )
        return

    if not state.product_function_architecture_reviewer_challenged:
        yield _step(
            state,
            label="product_function_architecture_reviewer_challenged",
            action="human-like reviewer challenges the pre-implementation product-function architecture for usefulness, missing expected functions, and unnecessary visible text",
            product_function_architecture_reviewer_challenged=True,
            active_node="freeze_contract",
        )
        return

    if not state.product_architecture_self_interrogation_record_written:
        yield _step(
            state,
            label="product_architecture_self_interrogation_record_written",
            action="PM writes a durable product-architecture self-interrogation record after FlowGuard operator and reviewer challenge so architecture doubts have a downstream destination",
            product_architecture_self_interrogation_record_written=True,
            active_node="freeze_contract",
        )
        return

    if not state.product_architecture_self_interrogation_findings_dispositioned:
        yield _step(
            state,
            label="product_architecture_self_interrogation_findings_dispositioned",
            action="PM incorporates, defers, ledgers, rejects, or waives product-architecture self-interrogation findings before root contract freeze",
            product_architecture_self_interrogation_findings_dispositioned=True,
            active_node="freeze_contract",
        )
        return

    if not state.contract_frozen:
        yield _step(
            state,
            label="contract_frozen",
            action="freeze high-ambition acceptance floor from the PM product-function architecture after startup and product-architecture self-interrogation findings are durably dispositioned",
            contract_frozen=True,
            active_node="record_dependency_plan",
        )
        return

    if not state.dependency_plan_recorded:
        yield _step(
            state,
            label="dependency_plan_recorded",
            action="record dependency inventory and defer non-current installs",
            dependency_plan_recorded=True,
            future_installs_deferred=True,
            active_node="create_initial_route",
        )
        return

    if not state.continuation_probe_done:
        yield _step(
            state,
            label="manual_resume_binding_capability_supported",
            action="probe manual resume binding capability and record current host-kind continuation evidence",
            continuation_probe_done=True,
            continuation_host_kind_recorded=True,
            continuation_evidence_written=True,
            manual_resume_binding_supported=True,
            active_node="configure_manual_resume_binding",
        )
        yield _step(
            state,
            label="manual_resume_boundary_recorded",
            action="probe manual resume binding capability, record host-kind evidence, and record manual-resume boundary when patrol is unavailable",
            continuation_probe_done=True,
            continuation_host_kind_recorded=True,
            continuation_evidence_written=True,
            manual_resume_boundary_recorded=True,
            active_node="design_flowguard_route",
        )
        return
