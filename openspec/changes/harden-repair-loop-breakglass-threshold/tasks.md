## 1. OpenSpec And FlowGuard Framing

- [x] 1.1 Validate this OpenSpec change before implementation.
- [x] 1.2 Preserve the no-compatibility and no-broad-new-field constraints.
- [x] 1.3 Record the single-threshold rule as the intended acceptance boundary.

## 2. Runtime

- [x] 2.1 Add normalized same-family repair loop computation from existing ledger fields.
- [x] 2.2 Block ordinary PM repair packet issuance when attempts exceed five.
- [x] 2.3 Project a control-plane break-glass duty with threshold evidence.
- [x] 2.4 Preserve under-threshold ordinary PM repair behavior.

## 3. Prompts And Cards

- [x] 3.1 Update PM repair guidance for the hard threshold.
- [x] 3.2 Update Controller and break-glass guidance for threshold-triggered diagnosis.
- [x] 3.3 Update FlowGuard Operator guidance to distinguish mechanical progress from semantic progress.

## 4. FlowGuard Models And Alignment

- [x] 4.1 Extend project-control information-flow coverage for threshold-triggered break-glass.
- [x] 4.2 Extend blocker-repair information-flow coverage for long same-family repair loops.
- [x] 4.3 Extend Controller break-glass coverage for threshold false alarm and real control fault cases.
- [x] 4.4 Update model-test alignment obligations for runtime and test coverage.

## 5. Tests And Evidence

- [x] 5.1 Add runtime tests for under-threshold PM repair issuance.
- [x] 5.2 Add runtime tests for over-threshold break-glass duty.
- [x] 5.3 Add runtime tests for normalized repair-node family counting.
- [x] 5.4 Add card coverage tests for the new guidance.
- [x] 5.5 Run focused FlowGuard and runtime/card tests.

## 6. Sync And Local Version

- [x] 6.1 Rebuild/check topology after model, card, runtime, and test changes.
- [x] 6.2 Sync repository-owned FlowPilot files to the installed local skill.
- [x] 6.3 Verify local install sync and install checks.
- [x] 6.4 Commit local Git changes without reverting peer-agent work.
