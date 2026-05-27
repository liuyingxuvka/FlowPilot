## 1. Scope And Preflight

- [x] 1.1 Run predictive KB, git/coordination, OpenSpec, and real FlowGuard preflight.
- [x] 1.2 Confirm this is an inventory pass, not a bulk test-generation or production-code change.

## 2. Inventory Generation

- [x] 2.1 Run the existing read-only FlowGuard coverage sweep and persist the result.
- [x] 2.2 Add or refine a full-model inventory artifact if the sweep is too runner-centric for model-test planning.
- [x] 2.3 Enumerate all check runners and classify persisted result status, skipped checks, and ordinary-test reference strength.

## 3. Model-Test Gap Analysis

- [x] 3.1 Cross-check current model-test alignment result with the full runner inventory.
- [x] 3.2 Identify gap groups that require ordinary boundary tests versus model mesh, test mesh, or structure work.
- [x] 3.3 Produce a human-readable prioritized report.

## 4. Validation And Records

- [x] 4.1 Run focused validation for the inventory artifact.
- [x] 4.2 Run OpenSpec strict validation for this change.
- [x] 4.3 Record FlowGuard adoption evidence and KB postflight notes.
