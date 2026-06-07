## 1. Preflight and Diagnostic Baseline

- [x] 1.1 Run predictive KB preflight for full diagnostic convergence.
- [x] 1.2 Read repository instructions and verify the real FlowGuard package.
- [x] 1.3 Inspect git status and preserve pre-existing dirty generated results.
- [x] 1.4 Create this total OpenSpec change.
- [x] 1.5 Regenerate and snapshot the current full diagnostic baseline.

## 2. External Contract Tests for Remaining Owner Modules

- [x] 2.1 Add controller/control/scheduler contract tests for `flowpilot_router_cli`, `flowpilot_router_control_transactions`, `flowpilot_router_controller_repair_schedule`, `flowpilot_router_controller_scheduler_receipts_pending`, `flowpilot_router_controller_scheduler_receipts_scheduled`, and `flowpilot_router_controller_scheduler_receipts_writes`.
- [x] 2.2 Add event/wait/repair contract tests for `flowpilot_router_event_identity`, `flowpilot_router_event_intake`, `flowpilot_router_events_repair`, `flowpilot_router_expected_waits`, `flowpilot_router_model_gate_state`, and `flowpilot_router_protocol_external_events`.
- [x] 2.3 Add facade-export contract tests for `flowpilot_router_facade_export_manifest_actions`, `flowpilot_router_facade_export_manifest_controller`, `flowpilot_router_facade_export_manifest_route`, `flowpilot_router_facade_export_manifest_startup`, `flowpilot_router_facade_export_manifest_terminal_work`, and `flowpilot_router_facade_exports`.
- [x] 2.4 Add lifecycle/startup/system-card contract tests for `flowpilot_router_lifecycle_requests`, `flowpilot_router_lifecycle_support`, `flowpilot_router_startup_bootloader`, `flowpilot_router_startup_closure`, `flowpilot_router_startup_display`, `flowpilot_router_startup_mechanical_boundary`, `flowpilot_router_startup_flow`, `flowpilot_router_startup_intake`, `flowpilot_router_startup_role_recovery`, `flowpilot_router_startup_support`, and `flowpilot_router_system_cards_delivery`.
- [x] 2.5 Add role/prompt/proof/terminal/work-packet contract tests for `flowpilot_router_internal_actions`, `flowpilot_router_payload_contracts`, `flowpilot_router_pm_role_followup`, `flowpilot_router_prompt_delivery`, `flowpilot_router_proof_validation`, `flowpilot_router_role_io_protocol`, `flowpilot_router_role_output_bridge`, `flowpilot_router_route_artifacts_evidence`, `flowpilot_router_route_completion_support`, `flowpilot_router_self_interrogation`, `flowpilot_router_terminal_ledger_closure`, `flowpilot_router_terminal_ledger_recovery`, `flowpilot_router_terminal_ledger_summary`, `flowpilot_router_work_packets_next_actions`, and `flowpilot_router_work_packets_pm_role_actions`.
- [x] 2.6 Add user-flow contract tests for `flowpilot_user_flow_markdown`, `flowpilot_user_flow_mermaid`, `flowpilot_user_flow_source`, `flowpilot_user_flow_stage`, and `flowpilot_user_flow_tree`.
- [x] 2.7 Add packet control-plane/reviewer contract tests for `packet_control_plane_model_invariants`, `packet_control_plane_model_transitions_dispatch_results`, `packet_control_plane_model_transitions_issue_resume`, `packet_control_plane_model_transitions_packet_relay`, `packet_control_plane_model_transitions_review_pm`, and `packet_runtime_reviewer`.
- [x] 2.8 Add matching source obligations, code contracts, and test evidence rows for every new contract test.
- [x] 2.9 Run the full model-test-code diagnostic and confirm `missing_test=0`.

## 3. StructureMesh Splits

- [x] 3.1 Split `scripts/run_test_tier.py` into focused tier definition/background artifact modules and a small CLI wrapper while preserving the command contract.
- [x] 3.2 Classify validation runners with explicit StructureMesh deferrals and child-module split plans for `run_capability_checks`, `run_meta_checks`, `run_flowpilot_model_test_alignment_checks`, `run_flowpilot_daemon_reconciliation_checks`, `run_flowpilot_model_hierarchy_checks`, `run_flowpilot_process_liveness_checks`, and `run_flowpilot_role_output_runtime_checks`, while preserving the current CLI facades.
- [x] 3.3 Classify remaining oversized compatibility facades as deferred StructureMesh work while preserving public import names and avoiding unsafe peer-agent overlap.
- [x] 3.4 Classify oversized owner modules that now have direct external-contract tests as explicit deferred StructureMesh debt unless the split was already low-risk and completed in this change.
- [x] 3.5 Re-run StructureMesh maintenance checks and update diagnostic split metadata.

## 4. Stale Evidence and Background Proof

- [x] 4.1 Repair or reclassify `public_release_check` so local-only URL-skipped evidence is not counted as public proof.
- [x] 4.2 Repair or reclassify `capability_legacy_full` and `meta_legacy_full` background evidence.
- [x] 4.3 Run final background tiers and inspect final artifacts, not progress text.

## 5. Final Validation, Sync, and Commit

- [x] 5.1 Run focused contract tests for every new test file.
- [x] 5.2 Run FlowGuard model-test alignment and StructureMesh maintenance checks.
- [x] 5.3 Run OpenSpec strict validation.
- [x] 5.4 Run fast/router/release/model background regressions as required and inspect final artifacts.
- [x] 5.5 Sync and audit the local installed FlowPilot skill.
- [x] 5.6 Update diagnostic docs and FlowGuard adoption log.
- [x] 5.7 Run KB postflight and record reusable lessons.
- [x] 5.8 Commit only scoped changes locally; do not push, tag, or publish without explicit user instruction.
