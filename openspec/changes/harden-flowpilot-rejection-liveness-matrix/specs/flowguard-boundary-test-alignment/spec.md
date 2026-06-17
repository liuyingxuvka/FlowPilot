## ADDED Requirements

### Requirement: Rejection liveness obligations bind to code and tests
FlowPilot SHALL map each rejection/liveness model obligation to the runtime or
contract code that owns the behavior and to executable test evidence before
claiming the matrix is covered.

#### Scenario: Model obligation has no owner code contract
- **WHEN** model-test alignment inspects a rejection/liveness obligation and no
  owner runtime, packet/result, model mesh, or test mesh code contract is
  registered
- **THEN** the alignment report MUST fail or mark the obligation as uncovered.

#### Scenario: Test proves only shape but not liveness
- **WHEN** a test row proves malformed shape rejection but does not prove
  actionable feedback, next-attempt semantic delta, or stable stuck absorption
- **THEN** model-test alignment MUST keep the liveness obligation uncovered.

