"""Startup external-event data for the FlowPilot router protocol."""

from __future__ import annotations

from typing import Any

STARTUP_EXTERNAL_EVENT_DATA: dict[str, dict[str, Any]] = {'user_requests_run_stop': {'flag': 'run_stopped_by_user',
                            'summary': 'The user explicitly stopped the active FlowPilot run; no '
                                       'further route work is authorized.'},
 'user_requests_run_cancel': {'flag': 'run_cancelled_by_user',
                              'summary': 'The user explicitly cancelled the active FlowPilot run; '
                                         'no further route work is authorized.'},
 'pm_first_decision_resets_controller': {'flag': 'pm_controller_reset_decision_returned',
                                         'requires_flag': 'pm_controller_reset_card_delivered',
                                         'summary': 'Recovery-only PM reminder that Controller is '
                                                    'only a relay and status-flow controller.'},
 'controller_role_confirmed_from_pm_reset': {'flag': 'controller_role_confirmed',
                                             'requires_flag': 'pm_controller_reset_decision_returned',
                                             'summary': 'Controller acknowledged a recovery-only '
                                                        'PM reset and remains relay-only.'},
 'manual_resume_requested': {'flag': 'resume_reentry_requested',
                             'summary': 'A manual resume wakeup requested router-guided '
                                        're-entry.'},
 'controller_reports_role_liveness_fault': {'flag': 'role_recovery_requested',
                                            'summary': 'Controller reported that a role binding '
                                                       'is missing, cancelled, unknown, timed out, '
                                                       'or no longer addressable; unified role '
                                                       'recovery must preempt normal work.'},
 'controller_reports_role_no_output': {'flag': 'role_no_output_reissue_recorded',
                                       'summary': 'Controller reported that the waited role is '
                                                  'reachable or completed but Router still lacks '
                                                  'the expected output; Router may reissue the '
                                                  'same work before role recovery.'},
 'host_records_manual_resume_binding': {'flag': 'continuation_binding_recorded',
                                        'summary': 'Host recorded the active run manual-resume '
                                                   'binding before resume recovery.'},
 'pm_resume_recovery_decision_returned': {'flag': 'pm_resume_recovery_decision_returned',
                                          'requires_flag': 'pm_resume_decision_card_delivered',
                                          'summary': 'PM returned a resume recovery decision after '
                                                     'Controller state re-entry.'}}

EXTERNAL_EVENTS = STARTUP_EXTERNAL_EVENT_DATA

__all__ = ["EXTERNAL_EVENTS", "STARTUP_EXTERNAL_EVENT_DATA"]
