"""Terminal external-event data for the FlowPilot router protocol."""

from __future__ import annotations

from typing import Any

TERMINAL_EXTERNAL_EVENT_DATA: dict[str, dict[str, Any]] = {'pm_records_evidence_quality_package': {'flag': 'evidence_quality_package_written',
                                         'requires_flag': 'pm_evidence_quality_package_card_delivered',
                                         'summary': 'PM recorded evidence, generated-resource, '
                                                    'UI/visual, and quality package ledgers.'},
 'reviewer_passes_evidence_quality_package': {'flag': 'evidence_quality_reviewer_passed',
                                              'requires_flag': 'reviewer_evidence_quality_card_delivered',
                                              'summary': 'Reviewer passed the evidence quality '
                                                         'package before final ledger work.'},
 'reviewer_blocks_evidence_quality_package': {'flag': 'evidence_quality_reviewer_blocked',
                                              'requires_flag': 'reviewer_evidence_quality_card_delivered',
                                              'summary': 'Reviewer blocked the evidence quality '
                                                         'package before final ledger work.'},
 'pm_records_final_route_wide_ledger_clean': {'flag': 'final_ledger_built_clean',
                                              'requires_flag': 'pm_final_ledger_card_delivered',
                                              'summary': 'PM built a current-route final ledger '
                                                         'with zero unresolved items.'},
 'reviewer_final_backward_replay_passed': {'flag': 'final_backward_replay_passed',
                                           'requires_flag': 'reviewer_final_backward_replay_card_delivered',
                                           'summary': 'Reviewer passed final backward replay.'},
 'reviewer_blocks_final_backward_replay': {'flag': 'final_backward_replay_blocked',
                                           'requires_flag': 'reviewer_final_backward_replay_card_delivered',
                                           'summary': 'Reviewer blocked final backward replay.'},
 'pm_approves_terminal_closure': {'flag': 'pm_closure_approved',
                                  'requires_flag': 'pm_closure_card_delivered',
                                  'summary': 'PM approved terminal closure after clean final '
                                             'ledger and backward replay.'}}

EXTERNAL_EVENTS = TERMINAL_EXTERNAL_EVENT_DATA

__all__ = ["EXTERNAL_EVENTS", "TERMINAL_EXTERNAL_EVENT_DATA"]
