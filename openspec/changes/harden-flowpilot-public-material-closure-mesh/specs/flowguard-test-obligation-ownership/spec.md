# flowguard-test-obligation-ownership Specification

## ADDED Requirements

### Requirement: New obligations map to FlowGuard models and tests

Every material-boundary, blocker-closure, FlowGuard work-order, Reviewer quality, identity, final projection, terminal coverage, and break-glass obligation introduced by this change SHALL map to a FlowGuard model/check and an executable test or explicitly scoped manual evidence.

#### Scenario: Model-test alignment is run
- **WHEN** the model-test alignment checker evaluates this change family
- **THEN** each obligation MUST have a current code/test evidence row or a documented scoped gap that blocks broad completion claims.

### Requirement: Background checks are liveness until exit artifacts prove completion

Long-running FlowGuard/model regressions MAY run in background, but their result MUST NOT be used as pass evidence until exit/meta/log artifacts prove completion and exit code.

#### Scenario: Background model check is still running
- **WHEN** only progress output exists
- **THEN** completion MUST NOT be claimed for obligations covered by that check.
