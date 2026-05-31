## 1. Model and Regression Grounding

- [x] 1.1 Add known-friction rows for the `run-20260527-212331` failure family: local PM receipt without Router event, rehydration postcondition replay miss, repeated same-family blockers, protocol-dead-end non-consumption, break-glass limbo, and heartbeat diagnostic-only wakeups.
- [x] 1.2 Extend FlowGuard model obligations so the bad cases are represented before implementation is claimed complete.
- [x] 1.3 Add or update focused model/test alignment rows that map each new obligation to ordinary tests and proof artifacts.

## 2. Fixed Router Event Role Output Hardening

- [x] 2.1 Detect output contracts with fixed `router_event` inside the existing role-output runtime.
- [x] 2.2 Reject local-only `submit-output` for fixed-router-event outputs with a clear message naming the Router-directed command.
- [x] 2.3 Preserve `submit-output-to-router` behavior and verify it records both receipt and Router event evidence.
- [x] 2.4 Update PM and role-output prompt/card guidance so formal fixed-event outputs require Router-directed submission.
- [x] 2.5 Add focused tests for local-only rejection and Router-directed success.

## 3. Resume Rehydration Postcondition Replay

- [x] 3.1 Add an idempotent Router reconcile helper that validates current-run requested-responsibility rehydration report evidence before blocker materialization.
- [x] 3.2 Fold valid done receipts for `rehydrate_role_agents` through existing Router-owned resume report handling.
- [x] 3.3 Set or preserve `resume_roles_restored`, `resume_role_agents_rehydrated`, and `crew_rehydration_report_written` only from valid current-run evidence.
- [x] 3.4 Add tests for valid requested-responsibility report replay, valid receipt/report replay, and incomplete report blocking.

## 4. Control Blocker Family Coalescing

- [x] 4.1 Add same-family lookup before writing a new control blocker.
- [x] 4.2 Reuse active same-family blockers instead of writing replacement artifacts.
- [x] 4.3 Preserve existing PM-pending same-family blockers without superseding them.
- [x] 4.4 Preserve terminal/protocol-dead-end same-family dispositions during heartbeat and manual resume.
- [x] 4.5 Add tests proving repeated same-family failures coalesce and distinct causes still materialize distinct blockers.

## 5. Protocol Dead-End Lifecycle

- [x] 5.1 Extend existing repair decision handling so PM `terminal_stop` plus `protocol_dead_end` writes durable blocker-family lifecycle evidence.
- [x] 5.2 Add specific run-state flags/status for generic control-blocker protocol dead-end without weakening startup-specific behavior.
- [x] 5.3 Ensure heartbeat/manual resume surfaces the terminal/protocol-repair boundary instead of reopening the same blocker family.
- [x] 5.4 Add tests for protocol-dead-end closure and post-terminal heartbeat suppression.

## 6. Break-Glass Closure and Recovery Transactions

- [x] 6.1 Require opened break-glass incidents to reference a recovery transaction, validated diagnostic closure, quarantine/weak-evidence disposition, or explicit blocked disposition.
- [x] 6.2 Add validation/disposition handling for patches with `permanent_fix_needed=true` and `not_run` validation rows.
- [x] 6.3 Update the Controller break-glass playbook and status projection to show the required closure path.
- [x] 6.4 Add tests for open incident limbo, permanent-fix disposition, and non-bypass of normal route gates.

## 7. Heartbeat, Daemon, and Status Projection

- [x] 7.1 Keep heartbeat/manual resume as attach/recover launcher and prevent it from claiming work-chain liveness without current daemon/action evidence.
- [x] 7.2 Update daemon/status projection to expose live attach, standby, waiting, terminal stopped, protocol-dead-end, and blocked-for-human/protocol states.
- [x] 7.3 Ensure stale heartbeat with live daemon attaches without starting a second writer.
- [x] 7.4 Add tests for terminal/protocol-dead-end reentry suppression and live-daemon attach behavior.

## 8. Historical Live-Run Replay and Validation

- [x] 8.1 Add compact historical fixtures derived from `run-20260527-212331` controller-visible metadata without sealed body reads.
- [x] 8.2 Add replay tests that prove local PM receipts without Router events do not close blockers.
- [x] 8.3 Add replay tests that prove repeated same-family blockers collapse to one active family state or terminal disposition.
- [x] 8.4 Add replay tests that prove break-glass limbo is reported as uncovered.
- [x] 8.5 Run focused unit tests, FlowGuard checks, router runtime tier checks, Meta and Capability model checks, install checks, smoke checks, and local install sync/audit.

## 9. All-Path Runtime Gateway Adoption

- [x] 9.1 Add a FlowPilot runtime gateway surface map that covers current/index pointers, run state, execution frontier, route/capability state, Controller action state, scheduler state, daemon state, control blockers, break-glass state, role-output state, packet state, card state, lifecycle state, runtime event logs, and generic run-scoped JSON state.
- [x] 9.2 Connect all feasible low-level production writer families to `assert_runtime_gateway_write`: Router JSON, packet runtime, role-output runtime, card runtime, Controller break-glass, daemon/event appenders, heartbeat ticks, direct-event quarantine, role-output replay quarantine, package-disposition split logs, and user-flow display evidence.
- [x] 9.3 Add a static writer inventory that scans `skills/flowpilot/assets` and fails if a critical direct write is outside an approved runtime gateway module with an assertion guard.
- [x] 9.4 Add a FlowGuard runtime-gateway adoption model/check that requires complete writer inventory evidence, gateway contracts, code-boundary IDs, step contract IDs, proof artifacts, and current writer observations for every critical state surface.
- [x] 9.5 Add focused tests proving wrong gateway ownership is blocked, gatewayed writers still write, the static inventory passes with no direct critical bypasses, and a synthetic direct bypass is blocked by FlowGuard.
- [x] 9.6 Generate `simulations/flowpilot_runtime_gateway_adoption_results.json` as current evidence for the all-path runtime gateway adoption gate.
