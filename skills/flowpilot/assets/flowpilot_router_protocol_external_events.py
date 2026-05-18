"""External event catalog extracted from ``flowpilot_router_protocol_catalog.py``."""

from __future__ import annotations

from typing import Any, Iterable

import flowpilot_runtime_closure
import packet_runtime
import role_output_runtime

from flowpilot_router_protocol_schemas import *
from flowpilot_router_protocol_control_repair import *
from flowpilot_router_protocol_work_contracts import *
from flowpilot_router_protocol_decision_tables import *
from flowpilot_router_protocol_boot_cards import *

EXTERNAL_EVENTS: dict[str, dict[str, Any]] = {
    "user_requests_run_stop": {
        "flag": "run_stopped_by_user",
        "summary": "The user explicitly stopped the active FlowPilot run; no further route work is authorized.",
    },
    "user_requests_run_cancel": {
        "flag": "run_cancelled_by_user",
        "summary": "The user explicitly cancelled the active FlowPilot run; no further route work is authorized.",
    },
    "pm_first_decision_resets_controller": {
        "flag": "pm_controller_reset_decision_returned",
        "requires_flag": "pm_controller_reset_card_delivered",
        "summary": "Recovery-only PM reminder that Controller is only a relay and status-flow controller.",
    },
    "controller_role_confirmed_from_pm_reset": {
        "flag": "controller_role_confirmed",
        "requires_flag": "pm_controller_reset_decision_returned",
        "summary": "Controller acknowledged a recovery-only PM reset and remains relay-only.",
    },
    "heartbeat_or_manual_resume_requested": {
        "flag": "resume_reentry_requested",
        "summary": "A heartbeat or manual resume wakeup requested router-guided re-entry.",
    },
    "controller_reports_role_liveness_fault": {
        "flag": "role_recovery_requested",
        "summary": "Controller reported that a background role is missing, cancelled, unknown, timed out, or no longer addressable; unified role recovery must preempt normal work.",
    },
    "controller_reports_role_no_output": {
        "flag": "role_no_output_reissue_recorded",
        "summary": "Controller reported that the waited role is reachable or completed but Router still lacks the expected output; Router may reissue the same work before role recovery.",
    },
    "host_records_heartbeat_binding": {
        "flag": "continuation_binding_recorded",
        "summary": "Host recorded the active run heartbeat/manual-resume binding before startup fact review.",
    },
    "pm_resume_recovery_decision_returned": {
        "flag": "pm_resume_recovery_decision_returned",
        "requires_flag": "pm_resume_decision_card_delivered",
        "summary": "PM returned a resume recovery decision after Controller state re-entry.",
    },
    "reviewer_reports_startup_facts": {
        "flag": "startup_fact_reported",
        "requires_flag": "reviewer_startup_fact_check_card_delivered",
        "summary": "Reviewer reported independent startup facts for PM activation.",
    },
    "pm_approves_startup_activation": {
        "flag": "startup_activation_approved",
        "requires_flag": "pm_startup_activation_card_delivered",
        "summary": "PM approved opening work beyond startup from the reviewer startup fact report.",
    },
    "pm_requests_startup_repair": {
        "flag": "startup_repair_requested",
        "requires_flag": "pm_startup_activation_card_delivered",
        "summary": "PM returned a targeted startup repair request instead of opening work beyond startup.",
    },
    "pm_declares_startup_protocol_dead_end": {
        "flag": "startup_protocol_dead_end_declared",
        "requires_flag": "pm_startup_activation_card_delivered",
        "summary": "PM declared that the startup block has no legal repair path in the current protocol and stopped the run.",
    },
    "pm_issues_material_and_capability_scan_packets": {
        "flag": "pm_material_packets_issued",
        "requires_flag": "pm_material_scan_card_delivered",
        "summary": "PM issued bounded material/capability scan packets.",
    },
    "pm_registers_current_node_packet": {
        "flag": "current_node_packet_registered",
        "requires_flag": "node_acceptance_plan_reviewer_passed",
        "forbids_active_node_children": True,
        "summary": "PM registered a current-node packet envelope for router direct dispatch.",
    },
    "router_direct_material_scan_dispatch_recheck_passed": {
        "flag": "material_scan_direct_dispatch_recheck_passed",
        "requires_flag": "pm_control_blocker_repair_decision_recorded",
        "summary": "Router direct-dispatch repair recheck passed for material scan packets.",
    },
    "reviewer_allows_material_scan_dispatch": {
        "flag": "reviewer_dispatch_allowed",
        "requires_flag": "reviewer_dispatch_card_delivered",
        "legacy": True,
        "summary": "Legacy reviewer dispatch approval event retained for old run records only.",
    },
    "reviewer_blocks_material_scan_dispatch": {
        "flag": "material_scan_dispatch_blocked",
        "requires_flag": "reviewer_dispatch_card_delivered",
        "legacy": True,
        "summary": "Legacy reviewer dispatch block event retained for old run records only.",
    },
    "router_direct_material_scan_dispatch_recheck_blocked": {
        "flag": "material_scan_dispatch_recheck_blocked",
        "requires_flag": "pm_control_blocker_repair_decision_recorded",
        "summary": "Router direct-dispatch repair recheck blocked material scan packets.",
    },
    "router_protocol_blocker_material_scan_dispatch_recheck": {
        "flag": "material_scan_dispatch_recheck_protocol_blocked",
        "requires_flag": "pm_control_blocker_repair_decision_recorded",
        "summary": "Router direct-dispatch repair recheck found a protocol blocker.",
    },
    "reviewer_allows_current_node_dispatch": {
        "flag": "current_node_dispatch_allowed",
        "requires_flag": "reviewer_current_node_dispatch_card_delivered",
        "legacy": True,
        "summary": "Legacy current-node reviewer dispatch approval event retained for old run records only.",
    },
    "worker_scan_packet_bodies_delivered_after_dispatch": {
        "flag": "worker_packets_delivered",
        "requires_flag": "material_scan_packets_relayed",
        "summary": "Worker packet bodies were delivered after router direct dispatch.",
    },
    "worker_scan_results_returned": {
        "flag": "worker_scan_results_returned",
        "requires_flag": "worker_packets_delivered",
        "summary": "Worker scan results returned to the PM-first result path.",
    },
    "pm_records_material_scan_result_disposition": {
        "flag": "material_scan_result_disposition_recorded",
        "requires_flag": "material_scan_results_relayed_to_pm",
        "summary": "PM recorded material scan result disposition and released a formal material sufficiency package when absorbed.",
    },
    "worker_current_node_result_returned": {
        "flag": "current_node_worker_result_returned",
        "requires_flag": "current_node_packet_relayed",
        "summary": "Worker returned a current-node result envelope.",
    },
    "pm_records_current_node_result_disposition": {
        "flag": "current_node_result_disposition_recorded",
        "requires_flag": "current_node_result_relayed_to_pm",
        "summary": "PM recorded current-node worker result disposition and released the formal node-completion review package when absorbed.",
    },
    "reviewer_reports_material_sufficient": {
        "flag": "material_review_sufficient",
        "requires_flag": "reviewer_material_sufficiency_card_delivered",
        "summary": "Reviewer reported material sufficient.",
    },
    "reviewer_reports_material_insufficient": {
        "flag": "material_review_insufficient",
        "requires_flag": "reviewer_material_sufficiency_card_delivered",
        "summary": "Reviewer reported material insufficient.",
    },
    "pm_accepts_reviewed_material": {
        "flag": "material_accepted_by_pm",
        "requires_flag": "pm_material_absorb_or_research_card_delivered",
        "summary": "PM accepted reviewer-approved material.",
    },
    "pm_requests_research_after_material_insufficient": {
        "flag": "pm_research_requested",
        "requires_flag": "pm_material_absorb_or_research_card_delivered",
        "summary": "PM requested bounded research instead of accepting insufficient material.",
    },
    "pm_writes_research_package": {
        "flag": "research_package_written_by_pm",
        "requires_flag": "pm_research_package_card_delivered",
        "summary": "PM wrote a bounded research package after insufficient material.",
    },
    "research_capability_decision_recorded": {
        "flag": "research_capability_decision_recorded",
        "requires_flag": "research_package_written_by_pm",
        "summary": "PM recorded research source/tool capability and approval boundaries.",
    },
    "worker_research_report_returned": {
        "flag": "worker_research_report_returned",
        "requires_flag": "worker_research_report_card_delivered",
        "summary": "Worker returned a bounded research report.",
    },
    "pm_records_research_result_disposition": {
        "flag": "research_result_disposition_recorded",
        "requires_flag": "research_result_relayed_to_pm",
        "summary": "PM recorded research result disposition and released a formal research source-check package when absorbed.",
    },
    "reviewer_passes_research_direct_source_check": {
        "flag": "research_review_passed",
        "requires_flag": "reviewer_research_check_card_delivered",
        "summary": "Reviewer passed direct-source or experiment-output research check.",
    },
    "reviewer_blocks_research_direct_source_check": {
        "flag": "research_review_blocked",
        "requires_flag": "reviewer_research_check_card_delivered",
        "summary": "Reviewer blocked direct-source or experiment-output research check.",
    },
    "pm_absorbs_reviewed_research": {
        "flag": "research_result_absorbed_by_pm",
        "requires_flag": "pm_research_absorb_or_mutate_card_delivered",
        "summary": "PM absorbed reviewer-approved research into material understanding.",
    },
    "pm_writes_material_understanding": {
        "flag": "material_understanding_written_by_pm",
        "requires_flag": "pm_material_understanding_card_delivered",
        "summary": "PM wrote material understanding from reviewed material and approved research if required.",
    },
    "pm_writes_product_function_architecture": {
        "flag": "product_architecture_written_by_pm",
        "requires_flag": "pm_product_architecture_card_delivered",
        "summary": "PM wrote the product-function architecture from reviewed material.",
    },
    "reviewer_passes_product_architecture": {
        "flag": "product_architecture_reviewer_passed",
        "requires_flag": "reviewer_product_architecture_card_delivered",
        "summary": "Reviewer passed the PM product-function architecture challenge.",
    },
    "reviewer_blocks_product_architecture": {
        "flag": "product_architecture_reviewer_blocked",
        "requires_flag": "reviewer_product_architecture_card_delivered",
        "summary": "Reviewer blocked the PM product-function architecture challenge.",
    },
    "product_officer_passes_product_architecture_modelability": {
        "flag": "product_architecture_modelability_passed",
        "requires_flag": "product_officer_product_architecture_card_delivered",
        "gate_id": "product_behavior_model",
        "terminal_gate_outcome": True,
        "summary": "Compatibility alias: Product FlowGuard Officer submitted the product behavior model.",
    },
    "product_officer_submits_product_behavior_model": {
        "flag": "product_behavior_model_submitted",
        "requires_flag": "product_officer_product_architecture_card_delivered",
        "gate_id": "product_behavior_model",
        "terminal_gate_outcome": True,
        "summary": "Product FlowGuard Officer submitted the canonical product behavior model.",
    },
    "product_officer_model_report": {
        "flag": "legacy_product_officer_model_report_received",
        "requires_flag": "product_officer_product_architecture_card_delivered",
        "gate_id": "product_behavior_model",
        "legacy": True,
        "terminal_gate_outcome": False,
        "summary": "Legacy Product FlowGuard model-report status event retained only so old run artifacts remain registered in the event taxonomy.",
    },
    "pm_accepts_product_behavior_model": {
        "flag": "pm_product_behavior_model_accepted",
        "requires_flag": "pm_product_behavior_model_decision_card_delivered",
        "summary": "PM accepted the Product FlowGuard product behavior model as the product basis for review and route planning.",
    },
    "pm_requests_product_behavior_model_rebuild": {
        "flag": "pm_product_behavior_model_rebuild_requested",
        "requires_flag": "pm_product_behavior_model_decision_card_delivered",
        "summary": "PM rejected the current product behavior model and requested product architecture/model rebuild before reviewer challenge.",
    },
    "product_officer_blocks_product_architecture_modelability": {
        "flag": "product_architecture_modelability_blocked",
        "requires_flag": "product_officer_product_architecture_card_delivered",
        "gate_id": "product_behavior_model",
        "terminal_gate_outcome": True,
        "summary": "Compatibility alias: Product FlowGuard Officer blocked the product behavior model.",
    },
    "product_officer_blocks_product_behavior_model": {
        "flag": "product_behavior_model_blocked",
        "requires_flag": "product_officer_product_architecture_card_delivered",
        "gate_id": "product_behavior_model",
        "terminal_gate_outcome": True,
        "summary": "Product FlowGuard Officer blocked the canonical product behavior model.",
    },
    "pm_writes_root_acceptance_contract": {
        "flag": "root_contract_written_by_pm",
        "requires_flag": "pm_root_contract_card_delivered",
        "summary": "PM wrote the root acceptance contract and standard scenario pack draft.",
    },
    "reviewer_passes_root_acceptance_contract": {
        "flag": "root_contract_reviewer_passed",
        "requires_flag": "reviewer_root_contract_card_delivered",
        "summary": "Reviewer passed the root acceptance contract challenge.",
    },
    "reviewer_blocks_root_acceptance_contract": {
        "flag": "root_contract_reviewer_blocked",
        "requires_flag": "reviewer_root_contract_card_delivered",
        "summary": "Reviewer blocked the root acceptance contract challenge.",
    },
    "product_officer_passes_root_acceptance_contract_modelability": {
        "flag": "root_contract_modelability_passed",
        "requires_flag": "product_officer_root_contract_card_delivered",
        "legacy": True,
        "summary": "Product FlowGuard Officer passed root contract modelability.",
    },
    "product_officer_blocks_root_acceptance_contract_modelability": {
        "flag": "root_contract_modelability_blocked",
        "requires_flag": "product_officer_root_contract_card_delivered",
        "legacy": True,
        "summary": "Product FlowGuard Officer blocked root contract modelability.",
    },
    "pm_freezes_root_acceptance_contract": {
        "flag": "root_contract_frozen_by_pm",
        "requires_flag": "root_contract_reviewer_passed",
        "summary": "PM froze the reviewed root acceptance contract as the completion floor.",
    },
    "pm_records_dependency_policy": {
        "flag": "dependency_policy_recorded",
        "requires_flag": "pm_dependency_policy_card_delivered",
        "summary": "PM recorded dependency and installation policy.",
    },
    "pm_writes_capabilities_manifest": {
        "flag": "capabilities_manifest_written",
        "requires_flag": "dependency_policy_recorded",
        "summary": "PM wrote route capabilities manifest from product architecture and root contract.",
    },
    "pm_writes_child_skill_selection": {
        "flag": "pm_child_skill_selection_written",
        "requires_flag": "pm_child_skill_selection_card_delivered",
        "summary": "PM wrote child-skill selection from product needs, not raw availability.",
    },
    "pm_writes_child_skill_gate_manifest": {
        "flag": "child_skill_gate_manifest_written",
        "requires_flag": "pm_child_skill_gate_manifest_card_delivered",
        "summary": "PM wrote the child-skill gate manifest.",
    },
    "reviewer_passes_child_skill_gate_manifest": {
        "flag": "child_skill_manifest_reviewer_passed",
        "requires_flag": "reviewer_child_skill_gate_manifest_card_delivered",
        "summary": "Reviewer passed child-skill gate manifest review.",
    },
    "reviewer_blocks_child_skill_gate_manifest": {
        "flag": "child_skill_manifest_reviewer_blocked",
        "requires_flag": "reviewer_child_skill_gate_manifest_card_delivered",
        "summary": "Reviewer blocked child-skill gate manifest review.",
    },
    "process_officer_passes_child_skill_conformance_model": {
        "flag": "child_skill_process_officer_passed",
        "requires_flag": "process_officer_child_skill_card_delivered",
        "legacy": True,
        "summary": "Process FlowGuard Officer passed child-skill conformance model review.",
    },
    "process_officer_blocks_child_skill_conformance_model": {
        "flag": "child_skill_process_officer_blocked",
        "requires_flag": "process_officer_child_skill_card_delivered",
        "legacy": True,
        "summary": "Process FlowGuard Officer blocked child-skill conformance model review.",
    },
    "product_officer_passes_child_skill_product_fit": {
        "flag": "child_skill_product_officer_passed",
        "requires_flag": "product_officer_child_skill_card_delivered",
        "legacy": True,
        "summary": "Product FlowGuard Officer passed child-skill product fit review.",
    },
    "product_officer_blocks_child_skill_product_fit": {
        "flag": "child_skill_product_officer_blocked",
        "requires_flag": "product_officer_child_skill_card_delivered",
        "legacy": True,
        "summary": "Product FlowGuard Officer blocked child-skill product fit review.",
    },
    "pm_approves_child_skill_manifest_for_route": {
        "flag": "child_skill_manifest_pm_approved_for_route",
        "requires_flag": "child_skill_manifest_reviewer_passed",
        "summary": "PM approved the child-skill manifest for route use.",
    },
    "capability_evidence_synced": {
        "flag": "capability_evidence_synced",
        "requires_flag": "child_skill_manifest_pm_approved_for_route",
        "summary": "Capability evidence was synced after PM child-skill approval.",
    },
    "pm_writes_route_draft": {
        "flag": "route_draft_written_by_pm",
        "requires_flag": "pm_route_skeleton_card_delivered",
        "summary": "PM wrote the route draft from the frozen root contract.",
    },
    "process_officer_passes_route_check": {
        "flag": "process_officer_route_check_passed",
        "requires_flag": "process_officer_route_check_card_delivered",
        "gate_id": "process_route_model",
        "terminal_gate_outcome": True,
        "summary": "Compatibility alias: Process FlowGuard Officer submitted the process route model.",
    },
    "process_officer_submits_process_route_model": {
        "flag": "process_route_model_submitted",
        "requires_flag": "process_officer_route_check_card_delivered",
        "gate_id": "process_route_model",
        "terminal_gate_outcome": True,
        "summary": "Process FlowGuard Officer submitted the canonical process route model.",
    },
    "pm_accepts_process_route_model": {
        "flag": "pm_process_route_model_accepted",
        "requires_flag": "pm_process_route_model_decision_card_delivered",
        "summary": "PM accepted the Process FlowGuard serial route execution model before Reviewer route challenge.",
    },
    "pm_requests_process_route_model_rebuild": {
        "flag": "pm_process_route_model_rebuild_requested",
        "requires_flag": "pm_process_route_model_decision_card_delivered",
        "summary": "PM rejected the current process route model and requested route/model rebuild before route challenge.",
    },
    "process_officer_requires_route_repair": {
        "flag": "process_officer_route_repair_required",
        "requires_flag": "process_officer_route_check_card_delivered",
        "gate_id": "process_route_model",
        "terminal_gate_outcome": True,
        "summary": "Compatibility alias: Process FlowGuard Officer requested process route model repair.",
    },
    "process_officer_requests_process_route_model_repair": {
        "flag": "process_route_model_repair_required",
        "requires_flag": "process_officer_route_check_card_delivered",
        "gate_id": "process_route_model",
        "terminal_gate_outcome": True,
        "summary": "Process FlowGuard Officer requested repair of the canonical process route model.",
    },
    "process_officer_blocks_route_check": {
        "flag": "process_officer_route_check_blocked",
        "requires_flag": "process_officer_route_check_card_delivered",
        "gate_id": "process_route_model",
        "terminal_gate_outcome": True,
        "summary": "Compatibility alias: Process FlowGuard Officer blocked the process route model.",
    },
    "process_officer_blocks_process_route_model": {
        "flag": "process_route_model_blocked",
        "requires_flag": "process_officer_route_check_card_delivered",
        "gate_id": "process_route_model",
        "terminal_gate_outcome": True,
        "summary": "Process FlowGuard Officer blocked the canonical process route model.",
    },
    "product_officer_passes_route_check": {
        "flag": "product_officer_route_check_passed",
        "requires_flag": "product_officer_route_check_card_delivered",
        "legacy": True,
        "summary": "Compatibility event: Product FlowGuard Officer passed the legacy route product check.",
    },
    "product_officer_blocks_route_check": {
        "flag": "product_officer_route_check_blocked",
        "requires_flag": "product_officer_route_check_card_delivered",
        "legacy": True,
        "summary": "Compatibility event: Product FlowGuard Officer blocked the legacy route product check.",
    },
    "reviewer_passes_route_check": {
        "flag": "reviewer_route_check_passed",
        "requires_flag": "reviewer_route_check_card_delivered",
        "summary": "Reviewer passed the route challenge.",
    },
    "reviewer_blocks_route_check": {
        "flag": "reviewer_route_check_blocked",
        "requires_flag": "reviewer_route_check_card_delivered",
        "summary": "Reviewer blocked the route challenge.",
    },
    "pm_activates_reviewed_route": {
        "flag": "route_activated_by_pm",
        "requires_flag": "reviewer_route_check_passed",
        "summary": "PM activated route after Product Officer product model, Process Officer route model, and Reviewer route challenge.",
    },
    "pm_writes_node_acceptance_plan": {
        "flag": "node_acceptance_plan_written",
        "requires_flag": "pm_node_acceptance_plan_card_delivered",
        "summary": "PM wrote the active node acceptance plan before packet dispatch.",
    },
    "pm_revises_node_acceptance_plan": {
        "flag": "node_acceptance_plan_revised_by_pm",
        "requires_flag": "model_miss_triage_closed",
        "summary": "PM revised the active node acceptance plan as same-node repair after reviewer block.",
    },
    "reviewer_passes_node_acceptance_plan": {
        "flag": "node_acceptance_plan_reviewer_passed",
        "requires_flag": "reviewer_node_acceptance_plan_card_delivered",
        "summary": "Reviewer passed the active node acceptance plan.",
    },
    "reviewer_blocks_node_acceptance_plan": {
        "flag": "node_acceptance_plan_review_blocked",
        "requires_flag": "reviewer_node_acceptance_plan_card_delivered",
        "summary": "Reviewer blocked the active node acceptance plan before worker packet registration.",
    },
    "reviewer_blocks_current_node_dispatch": {
        "flag": "current_node_dispatch_blocked",
        "requires_flag": "reviewer_current_node_dispatch_card_delivered",
        "legacy": True,
        "summary": "Legacy current-node reviewer dispatch block event retained for old run records only.",
    },
    "current_node_reviewer_blocks_result": {
        "flag": "node_review_blocked",
        "requires_flag": "reviewer_worker_result_card_delivered",
        "summary": "Reviewer blocked current-node result.",
    },
    "current_node_reviewer_passes_result": {
        "flag": "node_reviewer_passed_result",
        "requires_flag": "reviewer_worker_result_card_delivered",
        "summary": "Reviewer passed current-node result.",
    },
    "pm_builds_parent_backward_targets": {
        "flag": "parent_backward_targets_built",
        "requires_flag": "pm_parent_backward_targets_card_delivered",
        "summary": "PM built local parent backward replay targets for the active node.",
    },
    "reviewer_passes_parent_backward_replay": {
        "flag": "parent_backward_replay_passed",
        "requires_flag": "reviewer_parent_backward_replay_card_delivered",
        "summary": "Reviewer passed local parent backward replay.",
    },
    "reviewer_blocks_parent_backward_replay": {
        "flag": "parent_backward_replay_blocked",
        "requires_flag": "reviewer_parent_backward_replay_card_delivered",
        "summary": "Reviewer blocked local parent backward replay.",
    },
    "pm_records_parent_segment_decision": {
        "flag": "parent_segment_decision_recorded",
        "requires_flag": "pm_parent_segment_decision_card_delivered",
        "summary": "PM recorded parent segment decision after local backward replay.",
    },
    "pm_mutates_route_after_review_block": {
        "flag": "route_mutated_by_pm",
        "requires_flag": "model_miss_triage_closed",
        "summary": "PM mutated the route and invalidated affected stale evidence after a reviewer block.",
    },
    "pm_records_model_miss_triage_decision": {
        "flag": "model_miss_triage_closed",
        "requires_flag": "pm_model_miss_triage_card_delivered",
        "summary": "PM recorded the model-miss triage decision that precedes normal repair.",
    },
    "pm_registers_role_work_request": {
        "flag": "pm_role_work_request_registered",
        "summary": "PM registered a bounded role-work request through the generic always-available PM channel.",
    },
    "role_work_result_returned": {
        "flag": "pm_role_work_result_returned",
        "summary": "The requested role returned a result envelope for a PM role-work request.",
    },
    "pm_records_role_work_result_decision": {
        "flag": "pm_role_work_result_absorbed",
        "summary": "PM recorded whether a role-work result was absorbed, canceled, or superseded.",
    },
    "pm_records_control_blocker_repair_decision": {
        "flag": "pm_control_blocker_repair_decision_recorded",
        "summary": "PM recorded a repair decision for a router materialized control blocker.",
    },
    "pm_records_control_blocker_followup_blocker": {
        "flag": "pm_control_blocker_followup_blocker_recorded",
        "requires_flag": "pm_control_blocker_repair_decision_recorded",
        "summary": "PM recorded that a control-blocker repair follow-up ended in a blocker that needs a new PM decision.",
    },
    "pm_records_control_blocker_protocol_blocker": {
        "flag": "pm_control_blocker_protocol_blocker_recorded",
        "requires_flag": "pm_control_blocker_repair_decision_recorded",
        "summary": "PM recorded that a control-blocker repair follow-up exposed a protocol blocker.",
    },
    "pm_records_parent_protocol_blocker": {
        "flag": "parent_protocol_blocker_recorded",
        "requires_flag": "pm_control_blocker_repair_decision_recorded",
        "summary": "PM recorded a parent/module repair protocol blocker after parent backward replay repair.",
    },
    "role_records_gate_decision": {
        "flag": "gate_decision_recorded",
        "summary": "A PM, reviewer, or FlowGuard officer recorded a mechanically valid GateDecision.",
    },
    "pm_completes_current_node_from_reviewed_result": {
        "flag": "node_completed_by_pm",
        "requires_flag": "node_reviewer_passed_result",
        "summary": "PM completed current node from reviewed result.",
    },
    "pm_completes_parent_node_from_backward_replay": {
        "flag": "node_completed_by_pm",
        "requires_flag": "parent_segment_decision_recorded",
        "summary": "PM completed a parent/module node after reviewer-passed backward replay and PM segment decision.",
    },
    "pm_records_evidence_quality_package": {
        "flag": "evidence_quality_package_written",
        "requires_flag": "pm_evidence_quality_package_card_delivered",
        "summary": "PM recorded evidence, generated-resource, UI/visual, and quality package ledgers.",
    },
    "reviewer_passes_evidence_quality_package": {
        "flag": "evidence_quality_reviewer_passed",
        "requires_flag": "reviewer_evidence_quality_card_delivered",
        "summary": "Reviewer passed the evidence quality package before final ledger work.",
    },
    "reviewer_blocks_evidence_quality_package": {
        "flag": "evidence_quality_reviewer_blocked",
        "requires_flag": "reviewer_evidence_quality_card_delivered",
        "summary": "Reviewer blocked the evidence quality package before final ledger work.",
    },
    "pm_records_final_route_wide_ledger_clean": {
        "flag": "final_ledger_built_clean",
        "requires_flag": "pm_final_ledger_card_delivered",
        "summary": "PM built a current-route final ledger with zero unresolved items.",
    },
    "reviewer_final_backward_replay_passed": {
        "flag": "final_backward_replay_passed",
        "requires_flag": "reviewer_final_backward_replay_card_delivered",
        "summary": "Reviewer passed final backward replay.",
    },
    "reviewer_blocks_final_backward_replay": {
        "flag": "final_backward_replay_blocked",
        "requires_flag": "reviewer_final_backward_replay_card_delivered",
        "summary": "Reviewer blocked final backward replay.",
    },
    "pm_approves_terminal_closure": {
        "flag": "pm_closure_approved",
        "requires_flag": "pm_closure_card_delivered",
        "summary": "PM approved terminal closure after clean final ledger and backward replay.",
    },
}

__all__ = (
    'EXTERNAL_EVENTS',
)
