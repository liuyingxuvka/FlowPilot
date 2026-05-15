## 1. Model And Contract

- [x] 1.1 Add a focused FlowGuard model and runner for two-table async scheduling, startup current-scope reconciliation, barrier stops, and duplicate-row hazards.
- [x] 1.2 Run the focused FlowGuard scheduler checks and preserve the result artifact.
- [x] 1.3 Validate the OpenSpec change.

## 2. Router Runtime

- [ ] 2.1 Add a Router scheduler ledger with row ids, barrier classification, scope metadata, receipt state, and reconciliation state.
- [ ] 2.2 Keep Controller action ledger rows simple while linking them to Router scheduler rows.
- [ ] 2.3 Add deterministic daemon idempotency keys so retries do not duplicate queued Controller work.
- [ ] 2.4 Teach daemon ticks to reconcile receipts, apply Router-visible postconditions, and enqueue independent rows until a barrier.
- [ ] 2.5 Unify startup pre-review cleanup with the current-scope reconciliation action using `scope_kind=startup`.
- [ ] 2.6 Preserve PM startup activation's existing same-role ACK blocker without adding a second activation join.
- [x] 2.7 Add a stable `continuous_controller_standby` Controller row whenever a live daemon wait has no ordinary ready Controller row.
- [x] 2.8 Make foreground standby keep waiting through nonterminal timeouts by default and reserve bounded timeouts for diagnostics/tests.
- [x] 2.9 Sync standby row guidance into Controller prompt cards and install checks so the visible Codex plan remains in-progress during standby.

## 3. Tests And Validation

- [ ] 3.1 Add runtime tests for multi-row daemon enqueueing and the two-table split.
- [ ] 3.2 Add runtime tests for startup Reviewer gating through current-scope reconciliation.
- [ ] 3.3 Add runtime tests for stateful Controller receipt postcondition reconciliation, including controller boundary confirmation.
- [x] 3.4 Run focused router/runtime tests and focused FlowGuard checks; skip heavyweight meta/capability regressions by user request.
- [x] 3.5 Add focused model/runtime tests proving continuous standby rows are non-empty, plan-synced, and not completed after one check.

## 4. Sync And Finalize

- [x] 4.1 Sync the installed local FlowPilot skill version and audit local install freshness.
- [ ] 4.2 Review peer-agent changes and include compatible work in final staging.
- [ ] 4.3 Record FlowGuard adoption and KB postflight notes.
- [ ] 4.4 Commit the synchronized local git version.
