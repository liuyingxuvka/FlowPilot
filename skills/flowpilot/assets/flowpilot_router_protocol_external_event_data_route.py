"""Route external-event data for the FlowPilot router protocol."""

from __future__ import annotations

from typing import Any

ROUTE_EXTERNAL_EVENT_DATA: dict[str, dict[str, Any]] = {'pm_writes_route_draft': {'flag': 'route_draft_written_by_pm',
                           'requires_flag': 'pm_route_skeleton_card_delivered',
                           'summary': 'PM wrote the route draft from the frozen root contract.'},
 'process_officer_passes_route_check': {'flag': 'process_officer_route_check_passed',
                                        'requires_flag': 'process_officer_route_check_card_delivered',
                                        'gate_id': 'process_route_model',
                                        'terminal_gate_outcome': True,
                                        'summary': 'Compatibility alias: Process FlowGuard Officer '
                                                   'submitted the process route model.'},
 'process_officer_submits_process_route_model': {'flag': 'process_route_model_submitted',
                                                 'requires_flag': 'process_officer_route_check_card_delivered',
                                                 'gate_id': 'process_route_model',
                                                 'terminal_gate_outcome': True,
                                                 'summary': 'Process FlowGuard Officer submitted '
                                                            'the canonical process route model.'},
 'pm_accepts_process_route_model': {'flag': 'pm_process_route_model_accepted',
                                    'requires_flag': 'pm_process_route_model_decision_card_delivered',
                                    'summary': 'PM accepted the Process FlowGuard serial route '
                                               'execution model before Reviewer route challenge.'},
 'pm_requests_process_route_model_rebuild': {'flag': 'pm_process_route_model_rebuild_requested',
                                             'requires_flag': 'pm_process_route_model_decision_card_delivered',
                                             'summary': 'PM rejected the current process route '
                                                        'model and requested route/model rebuild '
                                                        'before route challenge.'},
 'process_officer_requires_route_repair': {'flag': 'process_officer_route_repair_required',
                                           'requires_flag': 'process_officer_route_check_card_delivered',
                                           'gate_id': 'process_route_model',
                                           'terminal_gate_outcome': True,
                                           'summary': 'Compatibility alias: Process FlowGuard '
                                                      'Officer requested process route model '
                                                      'repair.'},
 'process_officer_requests_process_route_model_repair': {'flag': 'process_route_model_repair_required',
                                                         'requires_flag': 'process_officer_route_check_card_delivered',
                                                         'gate_id': 'process_route_model',
                                                         'terminal_gate_outcome': True,
                                                         'summary': 'Process FlowGuard Officer '
                                                                    'requested repair of the '
                                                                    'canonical process route '
                                                                    'model.'},
 'process_officer_blocks_route_check': {'flag': 'process_officer_route_check_blocked',
                                        'requires_flag': 'process_officer_route_check_card_delivered',
                                        'gate_id': 'process_route_model',
                                        'terminal_gate_outcome': True,
                                        'summary': 'Compatibility alias: Process FlowGuard Officer '
                                                   'blocked the process route model.'},
 'process_officer_blocks_process_route_model': {'flag': 'process_route_model_blocked',
                                                'requires_flag': 'process_officer_route_check_card_delivered',
                                                'gate_id': 'process_route_model',
                                                'terminal_gate_outcome': True,
                                                'summary': 'Process FlowGuard Officer blocked the '
                                                           'canonical process route model.'},
 'product_officer_passes_route_check': {'flag': 'product_officer_route_check_passed',
                                        'requires_flag': 'product_officer_route_check_card_delivered',
                                        'legacy': True,
                                        'summary': 'Compatibility event: Product FlowGuard Officer '
                                                   'passed the legacy route product check.'},
 'product_officer_blocks_route_check': {'flag': 'product_officer_route_check_blocked',
                                        'requires_flag': 'product_officer_route_check_card_delivered',
                                        'legacy': True,
                                        'summary': 'Compatibility event: Product FlowGuard Officer '
                                                   'blocked the legacy route product check.'},
 'reviewer_passes_route_check': {'flag': 'reviewer_route_check_passed',
                                 'requires_flag': 'reviewer_route_check_card_delivered',
                                 'summary': 'Reviewer passed the route challenge.'},
 'reviewer_blocks_route_check': {'flag': 'reviewer_route_check_blocked',
                                 'requires_flag': 'reviewer_route_check_card_delivered',
                                 'summary': 'Reviewer blocked the route challenge.'},
 'pm_activates_reviewed_route': {'flag': 'route_activated_by_pm',
                                 'requires_flag': 'reviewer_route_check_passed',
                                 'summary': 'PM activated route after Product Officer product '
                                            'model, Process Officer route model, and Reviewer '
                                            'route challenge.'},
 'pm_writes_node_acceptance_plan': {'flag': 'node_acceptance_plan_written',
                                    'requires_flag': 'pm_node_acceptance_plan_card_delivered',
                                    'summary': 'PM wrote the active node acceptance plan before '
                                               'packet dispatch.'},
 'pm_revises_node_acceptance_plan': {'flag': 'node_acceptance_plan_revised_by_pm',
                                     'requires_flag': 'model_miss_triage_closed',
                                     'summary': 'PM revised the active node acceptance plan as '
                                                'same-node repair after reviewer block.'},
 'reviewer_passes_node_acceptance_plan': {'flag': 'node_acceptance_plan_reviewer_passed',
                                          'requires_flag': 'reviewer_node_acceptance_plan_card_delivered',
                                          'summary': 'Reviewer passed the active node acceptance '
                                                     'plan.'},
 'reviewer_blocks_node_acceptance_plan': {'flag': 'node_acceptance_plan_review_blocked',
                                          'requires_flag': 'reviewer_node_acceptance_plan_card_delivered',
                                          'summary': 'Reviewer blocked the active node acceptance '
                                                     'plan before worker packet registration.'},
 'reviewer_blocks_current_node_dispatch': {'flag': 'current_node_dispatch_blocked',
                                           'requires_flag': 'reviewer_current_node_dispatch_card_delivered',
                                           'legacy': True,
                                           'summary': 'Legacy current-node reviewer dispatch block '
                                                      'event retained for old run records only.'},
 'current_node_reviewer_blocks_result': {'flag': 'node_review_blocked',
                                         'requires_flag': 'reviewer_worker_result_card_delivered',
                                         'summary': 'Reviewer blocked current-node result.'},
 'current_node_reviewer_passes_result': {'flag': 'node_reviewer_passed_result',
                                         'requires_flag': 'reviewer_worker_result_card_delivered',
                                         'summary': 'Reviewer passed current-node result.'},
 'pm_builds_parent_backward_targets': {'flag': 'parent_backward_targets_built',
                                       'requires_flag': 'pm_parent_backward_targets_card_delivered',
                                       'summary': 'PM built local parent backward replay targets '
                                                  'for the active node.'},
 'reviewer_passes_parent_backward_replay': {'flag': 'parent_backward_replay_passed',
                                            'requires_flag': 'reviewer_parent_backward_replay_card_delivered',
                                            'summary': 'Reviewer passed local parent backward '
                                                       'replay.'},
 'reviewer_blocks_parent_backward_replay': {'flag': 'parent_backward_replay_blocked',
                                            'requires_flag': 'reviewer_parent_backward_replay_card_delivered',
                                            'summary': 'Reviewer blocked local parent backward '
                                                       'replay.'},
 'pm_records_parent_segment_decision': {'flag': 'parent_segment_decision_recorded',
                                        'requires_flag': 'pm_parent_segment_decision_card_delivered',
                                        'summary': 'PM recorded parent segment decision after '
                                                   'local backward replay.'},
 'pm_mutates_route_after_review_block': {'flag': 'route_mutated_by_pm',
                                         'requires_flag': 'model_miss_triage_closed',
                                         'summary': 'PM mutated the route and invalidated affected '
                                                    'stale evidence after a reviewer block.'},
 'pm_records_model_miss_triage_decision': {'flag': 'model_miss_triage_closed',
                                           'requires_flag': 'pm_model_miss_triage_card_delivered',
                                           'summary': 'PM recorded the model-miss triage decision '
                                                      'that precedes normal repair.'},
 'pm_registers_role_work_request': {'flag': 'pm_role_work_request_registered',
                                    'summary': 'PM registered a bounded role-work request through '
                                               'the generic always-available PM channel.'},
 'role_work_result_returned': {'flag': 'pm_role_work_result_returned',
                               'summary': 'The requested role returned a result envelope for a PM '
                                          'role-work request.'},
 'pm_records_role_work_result_decision': {'flag': 'pm_role_work_result_absorbed',
                                          'summary': 'PM recorded whether a role-work result was '
                                                     'absorbed, canceled, or superseded.'},
 'pm_records_control_blocker_repair_decision': {'flag': 'pm_control_blocker_repair_decision_recorded',
                                                'summary': 'PM recorded a repair decision for a '
                                                           'router materialized control blocker.'},
 'pm_records_control_blocker_followup_blocker': {'flag': 'pm_control_blocker_followup_blocker_recorded',
                                                 'requires_flag': 'pm_control_blocker_repair_decision_recorded',
                                                 'summary': 'PM recorded that a control-blocker '
                                                            'repair follow-up ended in a blocker '
                                                            'that needs a new PM decision.'},
 'pm_records_control_blocker_protocol_blocker': {'flag': 'pm_control_blocker_protocol_blocker_recorded',
                                                 'requires_flag': 'pm_control_blocker_repair_decision_recorded',
                                                 'summary': 'PM recorded that a control-blocker '
                                                            'repair follow-up exposed a protocol '
                                                            'blocker.'},
 'pm_records_parent_protocol_blocker': {'flag': 'parent_protocol_blocker_recorded',
                                        'requires_flag': 'pm_control_blocker_repair_decision_recorded',
                                        'summary': 'PM recorded a parent/module repair protocol '
                                                   'blocker after parent backward replay repair.'},
 'role_records_gate_decision': {'flag': 'gate_decision_recorded',
                                'summary': 'A PM, reviewer, or FlowGuard officer recorded a '
                                           'mechanically valid GateDecision.'},
 'pm_completes_current_node_from_reviewed_result': {'flag': 'node_completed_by_pm',
                                                    'requires_flag': 'node_reviewer_passed_result',
                                                    'summary': 'PM completed current node from '
                                                               'reviewed result.'},
 'pm_completes_parent_node_from_backward_replay': {'flag': 'node_completed_by_pm',
                                                   'requires_flag': 'parent_segment_decision_recorded',
                                                   'summary': 'PM completed a parent/module node '
                                                              'after reviewer-passed backward '
                                                              'replay and PM segment decision.'}}

EXTERNAL_EVENTS = ROUTE_EXTERNAL_EVENT_DATA

__all__ = ["EXTERNAL_EVENTS", "ROUTE_EXTERNAL_EVENT_DATA"]
