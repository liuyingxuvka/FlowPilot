## 1. OpenSpec And FlowGuard Planning

- [x] 1.1 Record proposal, design, specs, and FlowGuard route snapshot for terminal supplemental repair.
- [x] 1.2 Validate the OpenSpec change in strict mode before implementation.
- [x] 1.3 Keep the implementation aligned with Existing Model Preflight, PlanDetailingCompiler, FieldLifecycleMesh, and DevelopmentProcessFlow ownership.

## 2. Runtime Contract And State

- [x] 2.1 Add current-contract `terminal_supplemental_repair` state with `current_round`, `max_rounds`, active contract, and exhausted terminal status.
- [x] 2.2 Add PM-authored `supplemental_repair_contracts` records that cite the frozen original contract and terminal Reviewer gap report.
- [x] 2.3 Require each supplemental repair item to identify its original-goal gap, owner repair node, acceptance item links, required evidence, status, and terminal disposition.
- [x] 2.4 Reject unsupported legacy aliases, missing-field defaults, prose-only repair intent, or direct Worker shortcuts for supplemental repair.

## 3. Route, Ledger, Replay, And Closure

- [x] 3.1 Project supplemental repair contracts into repair nodes/subnodes using existing route mutation and node gate mechanics.
- [x] 3.2 Include supplemental repair contracts and items in the final route-wide ledger and hard gate coverage matrix.
- [x] 3.3 Include supplemental contract and repair item segments in terminal backward replay targets.
- [x] 3.4 Block completion while supplemental repair items remain unresolved, unless the runtime has reached the hard `repair_rounds_exhausted` terminal stop.
- [x] 3.5 Enforce the three-round cap so round one and two can recheck, while round three unresolved stops without dispatching another Reviewer or PM repair packet.

## 4. Cards And Templates

- [x] 4.1 Update PM final ledger, closure, route repair, route skeleton, and node acceptance cards to write and consume supplemental repair contracts.
- [x] 4.2 Update Reviewer terminal replay and plan review cards to report structured terminal gaps and verify repair progress.
- [x] 4.3 Update FlowGuard operator cards to review supplemental repair reachability, stale evidence, loop risk, and hard-cap behavior.
- [x] 4.4 Update packet/result, route, node acceptance, and final ledger templates with explicit supplemental repair fields.

## 5. FlowGuard Models, Tests, And Evidence

- [x] 5.1 Add or update FlowGuard model coverage for supplemental repair contract creation, projection, closure, and three-round exhaustion.
- [x] 5.2 Add focused runtime negative tests for missing contract citation, missing repair item owner, missing evidence links, bypassed gates, unresolved closure, and post-exhaustion dispatch.
- [x] 5.3 Add fake E2E/current-contract rehearsal for terminal gap -> PM supplemental contract -> repair node -> replay -> completion, plus third-round exhaustion.
- [x] 5.4 Update model-test alignment and field lifecycle evidence rows for the new terminal supplemental fields and scenarios.

## 6. Validation, Install Sync, And Closure

- [x] 6.1 Run focused unit tests and new FlowGuard supplemental repair checks.
- [x] 6.2 Run affected runtime/high-standard/fake E2E/model-test/field contract regressions.
- [x] 6.3 Rebuild and check the FlowGuard project topology when model, test, code, or prompt ownership surfaces change.
- [x] 6.4 Sync the source tree into the installed FlowPilot skill and run install/audit checks.
- [x] 6.5 Update FlowGuard adoption notes and complete KB postflight.
- [x] 6.6 Mark OpenSpec tasks complete only after implementation and evidence are current.
