"""Controller facade export manifest lifecycle shard."""

from __future__ import annotations

from typing import TypeAlias

ExportSpec: TypeAlias = tuple[str, str]
RegistryKey: TypeAlias = tuple[str, bool, bool]

OWNER_EXPORTS_CONTROLLER_LIFECYCLE: dict[RegistryKey, tuple[ExportSpec, ...]] = {('flowpilot_router_lifecycle_requests', True, False): (('_clear_active_control_blocker_for_terminal_lifecycle',
                                                         '_clear_active_control_blocker_for_terminal_lifecycle'),
                                                        ('_reconcile_terminal_lifecycle_authorities',
                                                         '_reconcile_terminal_lifecycle_authorities'),
                                                        ('_run_lifecycle_terminal_action',
                                                         '_run_lifecycle_terminal_action'),
                                                        ('_try_write_control_blocker_for_exception',
                                                         '_try_write_control_blocker_for_exception'),
                                                        ('_write_protocol_dead_end_lifecycle',
                                                         '_write_protocol_dead_end_lifecycle'),
                                                        ('_write_run_lifecycle_request',
                                                         '_write_run_lifecycle_request')),
 ('flowpilot_router_lifecycle_support', True, False): (('_lifecycle_record_path',
                                                        '_lifecycle_record_path'),
                                                       ('_reset_resume_cycle_for_wakeup',
                                                        '_reset_resume_cycle_for_wakeup'),
                                                       ('_write_host_heartbeat_binding',
                                                        '_write_host_heartbeat_binding'))}

__all__ = ["OWNER_EXPORTS_CONTROLLER_LIFECYCLE"]
