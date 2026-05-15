## 1. Model Hardening Gate

- [x] 1.1 Add a focused FlowGuard model for Router-internal mechanical ownership.
- [x] 1.2 Add hazards for Router-internal actions leaking to Controller rows, Controller work packages swallowed by Router, role interactions bypassing Controller, sealed-body reads, missing external evidence marked done, repeated side effects, display projection claimed as user confirmation, host-boundary local consumption, and internal failure marked done.
- [x] 1.3 Add safe scenarios for local check consumption, internal wait reconciliation, local proof writing, display projection split, and preserved Controller work packages.
- [x] 1.4 Run the focused FlowGuard checks and confirm known-bad hazards fail while the safe plan passes.
- [x] 1.5 Record that Meta and Capability heavyweight simulations are skipped by user direction.

## 2. Router Ownership Classification

- [x] 2.1 Add a conservative Router-internal allowlist/classifier for local mechanical actions.
- [x] 2.2 Add tests that representative Router-internal actions are not written as Controller rows.
- [x] 2.3 Add tests that host-boundary and role-facing actions remain Controller work packages.

## 3. Internal Local Actions

- [x] 3.1 Move `check_prompt_manifest` and `check_packet_ledger` to Router-internal consumption.
- [ ] 3.2 Move safe ACK/check wait bookkeeping to Router-internal consumption without marking missing evidence as done.
- [x] 3.3 Move `write_startup_mechanical_audit` to Router-internal proof writing once prerequisites are satisfied.
- [x] 3.4 Clarify `sync_display_plan` ownership so startup waiting sync is an internal host-plan projection, while canonical route display still keeps its user-dialog confirmation gate.

## 4. Verification And Reconciliation

- [x] 4.1 Run focused runtime tests after each implementation slice.
- [x] 4.2 Rerun the focused FlowGuard ownership model after production edits.
- [x] 4.3 Run daemon reconciliation/startup-focused checks that own the touched boundary.
- [x] 4.4 Run install and smoke checks after all slices pass.

## 5. Sync And Completion

- [x] 5.1 Sync the installed local FlowPilot skill from the repository.
- [x] 5.2 Verify installed skill freshness and local git state.
- [x] 5.3 Update FlowGuard adoption logs with commands, skipped heavy checks, findings, and residual risk.
- [x] 5.4 Run KB postflight and record any reusable lesson or gap.
