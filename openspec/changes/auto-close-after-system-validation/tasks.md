## 1. Contracts And Modeling

- [x] 1.1 Add OpenSpec requirements for system-owned closure and system-validation failure repair routing.
- [x] 1.2 Update the FlowGuard validation/PM-gate model for system closure instead of Closure Officer packets.
- [x] 1.3 Update model-test alignment checks for system closure and failure-to-PM repair.

## 2. Runtime Implementation

- [x] 2.1 Add `system_closures` ledger records and events.
- [x] 2.2 Refactor closure side effects so they can run from a subject packet without a closure packet.
- [x] 2.3 Change ordinary reviewer pass to system-validate and then auto-close on pass.
- [x] 2.4 Change system validation failure to create a PM repair blocker.
- [x] 2.5 Remove validator and Closure Officer as dispatchable runtime roles.
- [x] 2.6 Remove validation and closure packet issuance/acceptance paths.

## 3. Tests And Rehearsals

- [x] 3.1 Update high-standard control-flow tests for no Closure Officer or validator packets.
- [x] 3.2 Add a focused test proving failed system validation routes to PM repair.
- [x] 3.3 Update PM high-risk gate tests so staged decisions apply after system closure.
- [x] 3.4 Update runtime check runners that previously completed closure packets.
- [x] 3.5 Update fake AI rehearsal to expect system validation/closure rather than validator or Closure Officer packets.

## 4. Validation And Sync

- [x] 4.1 Run strict OpenSpec validation.
- [x] 4.2 Run FlowGuard project audit and validation/PM-gate model checks.
- [x] 4.3 Run targeted pytest and affected runtime runners.
- [x] 4.4 Run fake AI work-packet rehearsal.
- [x] 4.5 Run background meta/capability checks and inspect completion artifacts.
- [x] 4.6 Run install sync/audit/check only after validation passes.
- [x] 4.7 Stage/commit the validated integrated local git version with the stop/host/orphan recovery change because both changes share the same runtime surface.
