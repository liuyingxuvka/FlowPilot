"""Material external-event data for the FlowPilot router protocol."""

from __future__ import annotations

from typing import Any

MATERIAL_EXTERNAL_EVENT_DATA: dict[str, dict[str, Any]] = {'pm_registers_current_node_packet': {'flag': 'current_node_packet_registered',
                                       'requires_flag': 'node_acceptance_plan_reviewer_passed',
                                       'forbids_active_node_children': True,
                                       'summary': 'PM registered a current-node packet envelope for '
                                                  'router direct dispatch.'},
 'worker_current_node_result_returned': {'flag': 'current_node_worker_result_returned',
                                          'requires_flag': 'current_node_packet_relayed',
                                          'summary': 'Worker returned a current-node result '
                                                    'envelope.'},
 'pm_records_current_node_result_disposition': {'flag': 'current_node_result_disposition_recorded',
                                                'requires_flag': 'current_node_result_relayed_to_pm',
                                                'summary': 'PM recorded current-node worker result '
                                                           'disposition and released the formal '
                                                           'node-completion review package when '
                                                           'absorbed.'},
 'pm_writes_research_package': {'flag': 'research_package_written_by_pm',
                                'requires_flag': 'pm_research_package_card_delivered',
                                'summary': 'PM wrote a bounded research package for an ordinary '
                                           'evidence workstream.'},
 'research_capability_decision_recorded': {'flag': 'research_capability_decision_recorded',
                                           'requires_flag': 'research_package_written_by_pm',
                                           'summary': 'PM recorded research source/tool capability '
                                                      'and approval boundaries.'},
 'worker_research_report_returned': {'flag': 'worker_research_report_returned',
                                     'requires_flag': 'worker_research_report_card_delivered',
                                     'summary': 'Worker returned a bounded research report.'},
 'pm_records_research_result_disposition': {'flag': 'research_result_disposition_recorded',
                                            'requires_flag': 'research_result_relayed_to_pm',
                                            'summary': 'PM recorded research result disposition '
                                                       'and released a formal research '
                                                       'source-check package when absorbed.'},
 'reviewer_passes_research_direct_source_check': {'flag': 'research_review_passed',
                                                  'requires_flag': 'reviewer_research_check_card_delivered',
                                                  'summary': 'Reviewer passed direct-source or '
                                                             'experiment-output research check.'},
 'reviewer_blocks_research_direct_source_check': {'flag': 'research_review_blocked',
                                                  'requires_flag': 'reviewer_research_check_card_delivered',
                                                  'summary': 'Reviewer blocked direct-source or '
                                                             'experiment-output research check.'},
 'pm_absorbs_reviewed_research': {'flag': 'research_result_absorbed_by_pm',
                                  'requires_flag': 'pm_research_absorb_or_mutate_card_delivered',
                                  'summary': 'PM absorbed reviewer-approved research into the '
                                             'current workstream evidence basis.'},
 'pm_writes_product_function_architecture': {'flag': 'product_architecture_written_by_pm',
                                              'requires_flag': 'pm_product_architecture_card_delivered',
                                              'summary': 'PM wrote the product-function '
                                                         'architecture from current evidence.'},
 'reviewer_passes_product_architecture': {'flag': 'product_architecture_reviewer_passed',
                                          'requires_flag': 'reviewer_product_architecture_card_delivered',
                                          'summary': 'Reviewer passed the PM product-function '
                                                     'architecture challenge.'},
 'reviewer_blocks_product_architecture': {'flag': 'product_architecture_reviewer_blocked',
                                          'requires_flag': 'reviewer_product_architecture_card_delivered',
                                          'summary': 'Reviewer blocked the PM product-function '
                                                     'architecture challenge.'},
 'flowguard_operator_submits_product_behavior_model': {'flag': 'product_behavior_model_submitted',
                                                    'requires_flag': 'flowguard_operator_product_architecture_card_delivered',
                                                    'gate_id': 'product_behavior_model',
                                                    'terminal_gate_outcome': True,
                                                    'summary': 'FlowGuard operator '
                                                               'submitted the canonical product '
                                                               'behavior model.'},
 'pm_accepts_product_behavior_model': {'flag': 'pm_product_behavior_model_accepted',
                                       'requires_flag': 'pm_product_behavior_model_decision_card_delivered',
                                       'summary': 'PM accepted the FlowGuard product '
                                                  'behavior model as the product basis for review '
                                                  'and route planning.'},
 'pm_requests_product_behavior_model_rebuild': {'flag': 'pm_product_behavior_model_rebuild_requested',
                                                'requires_flag': 'pm_product_behavior_model_decision_card_delivered',
                                                'summary': 'PM rejected the current product '
                                                           'behavior model and requested product '
                                                           'architecture/model rebuild before '
                                                           'reviewer challenge.'},
 'flowguard_operator_blocks_product_behavior_model': {'flag': 'product_behavior_model_blocked',
                                                   'requires_flag': 'flowguard_operator_product_architecture_card_delivered',
                                                   'gate_id': 'product_behavior_model',
                                                   'terminal_gate_outcome': True,
                                                   'summary': 'FlowGuard operator blocked '
                                                              'the canonical product behavior '
                                                              'model.'},
 'pm_writes_root_acceptance_contract': {'flag': 'root_contract_written_by_pm',
                                        'requires_flag': 'pm_root_contract_card_delivered',
                                        'summary': 'PM wrote the root acceptance contract and '
                                                   'standard scenario pack draft.'},
 'reviewer_passes_root_acceptance_contract': {'flag': 'root_contract_reviewer_passed',
                                              'requires_flag': 'reviewer_root_contract_card_delivered',
                                              'summary': 'Reviewer passed the root acceptance '
                                                         'contract challenge.'},
 'reviewer_blocks_root_acceptance_contract': {'flag': 'root_contract_reviewer_blocked',
                                              'requires_flag': 'reviewer_root_contract_card_delivered',
                                              'summary': 'Reviewer blocked the root acceptance '
                                                         'contract challenge.'},
 'pm_freezes_root_acceptance_contract': {'flag': 'root_contract_frozen_by_pm',
                                         'requires_flag': 'root_contract_reviewer_passed',
                                         'summary': 'PM froze the reviewed root acceptance '
                                                    'contract as the completion floor.'},
 'pm_records_dependency_policy': {'flag': 'dependency_policy_recorded',
                                  'requires_flag': 'pm_dependency_policy_card_delivered',
                                  'summary': 'PM recorded dependency and installation policy.'},
 'pm_writes_capabilities_manifest': {'flag': 'capabilities_manifest_written',
                                     'requires_flag': 'dependency_policy_recorded',
                                     'summary': 'PM wrote route capabilities manifest from product '
                                                'architecture and root contract.'},
 'pm_writes_child_skill_selection': {'flag': 'pm_child_skill_selection_written',
                                     'requires_flag': 'pm_child_skill_selection_card_delivered',
                                     'summary': 'PM wrote child-skill selection from product '
                                                'needs, not raw availability.'},
 'pm_writes_child_skill_gate_manifest': {'flag': 'child_skill_gate_manifest_written',
                                         'requires_flag': 'pm_child_skill_gate_manifest_card_delivered',
                                         'summary': 'PM wrote the child-skill gate manifest.'},
 'reviewer_passes_child_skill_gate_manifest': {'flag': 'child_skill_manifest_reviewer_passed',
                                               'requires_flag': 'reviewer_child_skill_gate_manifest_card_delivered',
                                               'summary': 'Reviewer passed child-skill gate '
                                                          'manifest review.'},
 'reviewer_blocks_child_skill_gate_manifest': {'flag': 'child_skill_manifest_reviewer_blocked',
                                               'requires_flag': 'reviewer_child_skill_gate_manifest_card_delivered',
                                               'summary': 'Reviewer blocked child-skill gate '
                                                          'manifest review.'},
 'pm_approves_child_skill_manifest_for_route': {'flag': 'child_skill_manifest_pm_approved_for_route',
                                                'requires_flag': 'child_skill_manifest_reviewer_passed',
                                                'summary': 'PM approved the child-skill manifest '
                                                           'for route use.'},
 'capability_evidence_synced': {'flag': 'capability_evidence_synced',
                                'requires_flag': 'child_skill_manifest_pm_approved_for_route',
                                'router_internal_postcondition': True,
                                'internal_materializer': 'capability_evidence_sync',
                                'summary': 'Capability evidence was synced after PM child-skill '
                                           'approval.'},
 'pm_writes_implementation_intent': {'flag': 'pm_implementation_intent_written',
                                     'requires_flag': 'pm_implementation_intent_card_delivered',
                                     'summary': 'PM wrote the implementation-intent bridge that '
                                                'states how the accepted product should be '
                                                'realized before route skeleton drafting.'},
 'flowguard_operator_submits_target_realization_model': {'flag': 'target_realization_model_submitted',
                                                         'requires_flag': 'flowguard_operator_target_realization_model_card_delivered',
                                                         'gate_id': 'target_realization_model',
                                                         'terminal_gate_outcome': True,
                                                         'summary': 'FlowGuard operator submitted '
                                                                    'the canonical target '
                                                                    'realization model from PM '
                                                                    'implementation intent.'},
 'flowguard_operator_blocks_target_realization_model': {'flag': 'target_realization_model_blocked',
                                                        'requires_flag': 'flowguard_operator_target_realization_model_card_delivered',
                                                        'gate_id': 'target_realization_model',
                                                        'terminal_gate_outcome': True,
                                                        'summary': 'FlowGuard operator blocked the '
                                                                   'target realization model and '
                                                                   'requires PM intent or model '
                                                                   'repair.'},
 'pm_accepts_target_realization_model': {'flag': 'pm_target_realization_model_accepted',
                                         'requires_flag': 'pm_target_realization_model_decision_card_delivered',
                                         'summary': 'PM accepted the FlowGuard target realization '
                                                    'model as the bridge from product target to '
                                                    'route skeleton.'},
 'pm_requests_target_realization_model_rebuild': {'flag': 'pm_target_realization_model_rebuild_requested',
                                                  'requires_flag': 'pm_target_realization_model_decision_card_delivered',
                                                  'summary': 'PM rejected the current target '
                                                             'realization model and requested '
                                                             'implementation-intent or FlowGuard '
                                                             'model rebuild.'},
 'reviewer_passes_implementation_intent_challenge': {'flag': 'implementation_intent_reviewer_passed',
                                                     'requires_flag': 'reviewer_implementation_intent_card_delivered',
                                                     'summary': 'Reviewer passed the PM '
                                                                'implementation-intent and '
                                                                'FlowGuard target-realization '
                                                                'alignment challenge.'},
 'reviewer_blocks_implementation_intent_challenge': {'flag': 'implementation_intent_reviewer_blocked',
                                                     'requires_flag': 'reviewer_implementation_intent_card_delivered',
                                                     'summary': 'Reviewer blocked the PM '
                                                                'implementation-intent and '
                                                                'FlowGuard target-realization '
                                                                'alignment challenge.'}}

EXTERNAL_EVENTS = MATERIAL_EXTERNAL_EVENT_DATA

__all__ = ["EXTERNAL_EVENTS", "MATERIAL_EXTERNAL_EVENT_DATA"]
