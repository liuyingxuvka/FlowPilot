## 1. OpenSpec And FlowGuard Routing

- [x] 1.1 Create strict route-plan OpenSpec artifacts and validate them.
- [x] 1.2 Ground the implementation in current FlowGuard project records and choose focused runtime/closure validations.

## 2. Runtime Route Contract

- [x] 2.1 Replace prose and fallback materialization with strict `flowpilot.route_plan.v1` parsing.
- [x] 2.2 Preserve route node schema fields including required outputs, deliverable checks, validation checks, and source schema metadata.
- [x] 2.3 Reject numbered text, missing schema, empty nodes, missing node identity, and `route_nodes` compatibility input.

## 3. System-Owned Closure Checks

- [x] 3.1 Resolve route deliverable paths against the target project root or run root.
- [x] 3.2 Evaluate bounded deliverable check kinds during final route-wide ledger construction.
- [x] 3.3 Add deliverable rows to the final requirement evidence matrix and closure blockers.

## 4. Tests And Regression Evidence

- [x] 4.1 Update existing recursive/high-standard route tests to emit strict route plans.
- [x] 4.2 Add negative regressions for prose route plans and compatibility-field route plans.
- [x] 4.3 Add closure regressions for missing and passing route deliverable checks.
- [x] 4.4 Refresh focused runtime model/check output after tests pass.

## 5. Sync And Completion Evidence

- [x] 5.1 Run OpenSpec strict validation, focused pytest, focused runtime checks, topology check, and install checks.
- [x] 5.2 Sync the repository-owned FlowPilot skill into the installed local skill and audit sync.
- [x] 5.3 Record FlowGuard and KB postflight evidence without reverting peer-agent changes.
