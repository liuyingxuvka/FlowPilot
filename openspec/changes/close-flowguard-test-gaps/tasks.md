## 1. Preflight And Scope

- [x] 1.1 Run predictive KB, coordination, git, OpenSpec, and real FlowGuard preflight.
- [x] 1.2 Use the full coverage inventory as the source of truth.
- [x] 1.3 Validate the OpenSpec change strictly.

## 2. Test Gap Plan

- [x] 2.1 Enumerate all current gap groups and runners from the inventory.
- [x] 2.2 Assign every gap group to `runner-exec`, `result-contract`, `scoped-boundary`, or `failure-sentinel`.
- [x] 2.3 Persist the machine-readable closure plan.

## 3. Ordinary Test Coverage

- [x] 3.1 Add ordinary tests for all abstract-without-test-reference runners.
- [x] 3.2 Add scoped-boundary tests for missing/scoped replay adapter runners.
- [x] 3.3 Add failure-sentinel tests for not-OK and unparsed runners.
- [x] 3.4 Add tests that prevent skipped/scoped evidence from being counted as pass evidence.

## 4. Unified Validation

- [x] 4.1 Run syntax checks for new artifacts.
- [x] 4.2 Run the new focused coverage-gap test suite.
- [x] 4.3 Rebuild the full coverage inventory.
- [x] 4.4 Run FlowGuard model-test alignment.
- [x] 4.5 Run OpenSpec strict validation.

## 5. Records

- [x] 5.1 Record FlowGuard adoption evidence.
- [x] 5.2 Run KB postflight.
- [x] 5.3 Report which tests passed and which real issues remain.
