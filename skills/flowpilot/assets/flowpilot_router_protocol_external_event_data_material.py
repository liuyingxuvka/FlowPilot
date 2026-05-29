"""Material external-event data for the FlowPilot router protocol."""

from __future__ import annotations

from typing import Any

MATERIAL_EXTERNAL_EVENT_DATA: dict[str, dict[str, Any]] = {'pm_issues_material_and_capability_scan_packets': {'flag': 'pm_material_packets_issued',
                                                    'requires_flag': 'pm_material_scan_card_delivered',
                                                    'summary': 'PM issued bounded '
                                                               'material/capability scan packets.'},
 'pm_registers_current_node_packet': {'flag': 'current_node_packet_registered',
                                      'requires_flag': 'node_acceptance_plan_reviewer_passed',
                                      'forbids_active_node_children': True,
                                      'summary': 'PM registered a current-node packet envelope for '
                                                 'router direct dispatch.'},
 'router_direct_material_scan_dispatch_recheck_passed': {'flag': 'material_scan_direct_dispatch_recheck_passed',
                                                         'requires_flag': 'pm_control_blocker_repair_decision_recorded',
                                                         'summary': 'Router direct-dispatch repair '
                                                                    'recheck passed for material '
                                                                    'scan packets.'},
 'router_direct_material_scan_dispatch_recheck_blocked': {'flag': 'material_scan_dispatch_recheck_blocked',
                                                          'requires_flag': 'pm_control_blocker_repair_decision_recorded',
                                                          'summary': 'Router direct-dispatch '
                                                                     'repair recheck blocked '
                                                                     'material scan packets.'},
 'router_protocol_blocker_material_scan_dispatch_recheck': {'flag': 'material_scan_dispatch_recheck_protocol_blocked',
                                                            'requires_flag': 'pm_control_blocker_repair_decision_recorded',
                                                            'summary': 'Router direct-dispatch '
                                                                       'repair recheck found a '
                                                                       'protocol blocker.'},
 'worker_scan_packet_bodies_delivered_after_dispatch': {'flag': 'worker_packets_delivered',
                                                        'requires_flag': 'material_scan_packets_relayed',
                                                        'summary': 'Worker packet bodies were '
                                                                   'delivered after router direct '
                                                                   'dispatch.'},
 'worker_scan_results_returned': {'flag': 'worker_scan_results_returned',
                                  'requires_flag': 'worker_packets_delivered',
                                  'summary': 'Worker scan results returned to the PM-first result '
                                             'path.'},
 'pm_records_material_scan_result_disposition': {'flag': 'material_scan_result_disposition_recorded',
                                                 'requires_flag': 'material_scan_results_relayed_to_pm',
                                                 'summary': 'PM recorded material scan result '
                                                            'disposition and released a formal '
                                                            'material sufficiency package when '
                                                            'absorbed.'},
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
 'reviewer_reports_material_sufficient': {'flag': 'material_review_sufficient',
                                          'requires_flag': 'reviewer_material_sufficiency_card_delivered',
                                          'summary': 'Reviewer reported material sufficient.'},
 'reviewer_reports_material_insufficient': {'flag': 'material_review_insufficient',
                                            'requires_flag': 'reviewer_material_sufficiency_card_delivered',
                                            'summary': 'Reviewer reported material insufficient.'},
 'pm_accepts_reviewed_material': {'flag': 'material_accepted_by_pm',
                                  'requires_flag': 'pm_material_absorb_or_research_card_delivered',
                                  'summary': 'PM accepted reviewer-approved material.'},
 'pm_requests_research_after_material_insufficient': {'flag': 'pm_research_requested',
                                                      'requires_flag': 'pm_material_absorb_or_research_card_delivered',
                                                      'summary': 'PM requested bounded research '
                                                                 'instead of accepting '
                                                                 'insufficient material.'},
 'pm_writes_research_package': {'flag': 'research_package_written_by_pm',
                                'requires_flag': 'pm_research_package_card_delivered',
                                'summary': 'PM wrote a bounded research package after insufficient '
                                           'material.'},
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
                                  'summary': 'PM absorbed reviewer-approved research into material '
                                             'understanding.'},
 'pm_writes_material_understanding': {'flag': 'material_understanding_written_by_pm',
                                      'requires_flag': 'pm_material_understanding_card_delivered',
                                      'summary': 'PM wrote material understanding from reviewed '
                                                 'material and approved research if required.'},
 'pm_writes_product_function_architecture': {'flag': 'product_architecture_written_by_pm',
                                             'requires_flag': 'pm_product_architecture_card_delivered',
                                             'summary': 'PM wrote the product-function '
                                                        'architecture from reviewed material.'},
 'reviewer_passes_product_architecture': {'flag': 'product_architecture_reviewer_passed',
                                          'requires_flag': 'reviewer_product_architecture_card_delivered',
                                          'summary': 'Reviewer passed the PM product-function '
                                                     'architecture challenge.'},
 'reviewer_blocks_product_architecture': {'flag': 'product_architecture_reviewer_blocked',
                                          'requires_flag': 'reviewer_product_architecture_card_delivered',
                                          'summary': 'Reviewer blocked the PM product-function '
                                                     'architecture challenge.'},
 'product_officer_submits_product_behavior_model': {'flag': 'product_behavior_model_submitted',
                                                    'requires_flag': 'product_officer_product_architecture_card_delivered',
                                                    'gate_id': 'product_behavior_model',
                                                    'terminal_gate_outcome': True,
                                                    'summary': 'Product FlowGuard Officer '
                                                               'submitted the canonical product '
                                                               'behavior model.'},
 'pm_accepts_product_behavior_model': {'flag': 'pm_product_behavior_model_accepted',
                                       'requires_flag': 'pm_product_behavior_model_decision_card_delivered',
                                       'summary': 'PM accepted the Product FlowGuard product '
                                                  'behavior model as the product basis for review '
                                                  'and route planning.'},
 'pm_requests_product_behavior_model_rebuild': {'flag': 'pm_product_behavior_model_rebuild_requested',
                                                'requires_flag': 'pm_product_behavior_model_decision_card_delivered',
                                                'summary': 'PM rejected the current product '
                                                           'behavior model and requested product '
                                                           'architecture/model rebuild before '
                                                           'reviewer challenge.'},
 'product_officer_blocks_product_behavior_model': {'flag': 'product_behavior_model_blocked',
                                                   'requires_flag': 'product_officer_product_architecture_card_delivered',
                                                   'gate_id': 'product_behavior_model',
                                                   'terminal_gate_outcome': True,
                                                   'summary': 'Product FlowGuard Officer blocked '
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
                                           'approval.'}}

EXTERNAL_EVENTS = MATERIAL_EXTERNAL_EVENT_DATA

__all__ = ["EXTERNAL_EVENTS", "MATERIAL_EXTERNAL_EVENT_DATA"]
