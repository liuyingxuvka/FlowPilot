## 1. Model And Contract Boundary

- [x] 1.1 Update the event-idempotency FlowGuard model and source audit so PM package dispositions dedupe by semantic package identity and detect body conflicts.
- [x] 1.2 Update the control-plane friction/live-audit model so duplicate same-package PM dispositions and missing per-packet outcomes are same-class findings.
- [x] 1.3 Update PM package result disposition payload contracts and runtime contract registry entries to document per-packet outcomes and body-conflict semantics.

## 2. Runtime Semantics

- [x] 2.1 Change shared scoped-event policy for material, research, and current-node PM package dispositions so `body_hash` is conflict evidence, not a dedupe field.
- [x] 2.2 Add shared scoped-event conflict detection before already-recorded replay or run-wide flag short-circuit.
- [x] 2.3 Add PM package disposition writer guards for existing same-batch dispositions and normalize per-packet outcomes against actual batch membership.
- [x] 2.4 Persist packet outcomes in the canonical disposition and batch summary, and prevent absorbed release when any packet outcome is not accepted.

## 3. Cross-Package Coverage

- [x] 3.1 Add material-scan tests for conflicting second disposition, idempotent same-body replay, mixed packet outcomes, and absorbed contradiction rejection.
- [x] 3.2 Add research and current-node tests proving the shared conflict policy applies beyond material-scan.
- [x] 3.3 Extend synthetic/fake AI replay coverage so a duplicate PM package disposition with a different body is rejected.
- [x] 3.4 Update model-test alignment expectations so this same-class obligation is tied to runtime tests.

## 4. Verification And Sync

- [x] 4.1 Run focused unit/runtime tests for PM package disposition semantics.
- [x] 4.2 Run FlowGuard event-idempotency and control-plane friction checks.
- [x] 4.3 Run background Meta and Capability regressions with the documented `tmp/flowguard_background/` artifact contract and inspect completion artifacts.
- [x] 4.4 Sync repository-owned installed FlowPilot skill from this checkout and run install sync/audit checks.
- [x] 4.5 Record FlowGuard adoption and predictive KB postflight notes, then prepare local git history.
