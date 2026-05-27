## 1. Model And OpenSpec Guardrails

- [x] 1.1 Validate the OpenSpec change strictly before production edits.
- [x] 1.2 Add a focused FlowGuard model and runner for Controller break-glass eligibility, forbidden powers, required records, and final reporting.
- [x] 1.3 Add known-bad hazards for ordinary project bugs, available normal PM repair, sealed-body access, gate approval, route mutation, missing incident record, missing patch record, and missing final disclosure.

## 2. Prompt And Manifest Surfaces

- [x] 2.1 Add `cards/system/controller_break_glass_repair.md` with the full Controller emergency playbook, allowed conditions, forbidden actions, first checks, temporary repair rule, exit rule, and reporting rule.
- [x] 2.2 Register the playbook in `runtime_kit/manifest.json` as `controller.break_glass_repair`.
- [x] 2.3 Add a small Controller core-card entry that points to the playbook only when normal FlowPilot control flow itself is broken.

## 3. Repeated Controller Reminder Surfaces

- [x] 3.1 Add the short restrictive break-glass reminder to generated `controller_table_prompt` text.
- [x] 3.2 Add the reminder to `runtime/router_daemon_status.json` for active runs.
- [x] 3.3 Add the reminder to `controller-patrol-timer` nonterminal output.
- [x] 3.4 Add the reminder to `continuous_controller_standby` row or payload while preserving anti-exit semantics.

## 4. Run-Scoped Records And Documentation

- [x] 4.1 Add a small standalone Controller break-glass helper for creating incident and patch records without depending on the normal Router repair loop.
- [x] 4.2 Add incident and temporary patch templates under `templates/flowpilot/`.
- [x] 4.3 Update run/state templates and schema docs with `.flowpilot/runs/<run-id>/controller_break_glass/`.
- [x] 4.4 Add a design note documenting the break-glass lane, trigger examples, non-goals, and rollback/final-report obligations.
- [x] 4.5 Update HANDOFF, template README, and validation docs with the new development-mode emergency lane.

## 5. Tests And Validation Wiring

- [x] 5.1 Add prompt/manifest tests proving the playbook is registered and Controller-visible.
- [x] 5.2 Add runtime tests proving table prompt, daemon status, patrol timer output, and standby payload include the reminder and path.
- [x] 5.3 Add tests or install-check coverage proving ordinary project repair authority is not granted by break-glass records.
- [x] 5.4 Wire the new FlowGuard runner into appropriate install/check surfaces without running broad release-only checks by default.

## 6. Verification, Sync, And Local Git

- [x] 6.1 Run focused Python compile and unit/model tests for touched boundaries.
- [x] 6.2 Run OpenSpec validation for `controller-break-glass-repair`.
- [x] 6.3 Run install check and smoke check after focused tests pass.
- [x] 6.4 Run heavyweight model regressions in background artifacts when practical and inspect final exit/status artifacts before claiming them.
- [x] 6.5 Sync the local installed FlowPilot skill from repo-owned source.
- [x] 6.6 Stage and commit only this change's files, preserving unrelated parallel-agent work.
- [x] 6.7 Run KB postflight and record any reusable lesson.
