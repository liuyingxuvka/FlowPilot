## 1. Controller Ledger Prompt

- [ ] 1.1 Add a compact `controller_table_prompt` object to generated `runtime/controller_action_ledger.json` before the action rows.
- [ ] 1.2 Include table-local reminders for top-to-bottom row order, receipt writing, row completion, foreground attachment, and Controller authority limits.
- [ ] 1.3 Add install/runtime assertions that the prompt remains compact and contains the required duty terms.

## 2. Continuous Standby Semantics

- [ ] 2.1 Update `continuous_controller_standby` row/payload text so it is a continuous monitoring duty, not a finishable checklist item.
- [ ] 2.2 Keep standby visible plan status `in_progress` while FlowPilot is running.
- [ ] 2.3 Ensure new Controller work returns the foreground Controller to top-to-bottom ledger row processing.

## 3. Verification

- [ ] 3.1 Extend focused FlowGuard/runtime checks for ledger prompt and standby semantics.
- [ ] 3.2 Run focused Router runtime tests and install checks.
- [ ] 3.3 Sync the local installed FlowPilot skill.
- [ ] 3.4 Skip heavyweight meta/capability model regressions unless explicitly requested.
