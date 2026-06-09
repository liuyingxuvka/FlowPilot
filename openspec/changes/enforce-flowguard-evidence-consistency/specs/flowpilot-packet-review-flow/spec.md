## ADDED Requirements

### Requirement: FlowGuard evidence consistency gates Reviewer handoff
FlowPilot SHALL accept a FlowGuard result as Reviewer-ready only when the
current result body is mechanically consistent: top-level `passed` status,
contract self-check status, and any referenced machine-readable child hard
evidence status MUST agree.

#### Scenario: Consistent FlowGuard pass can release Reviewer packet
- **WHEN** a current FlowGuard result has `passed: true`
- **AND** required `contract_self_check` booleans are true
- **AND** child hard evidence statuses are pass/ok
- **THEN** runtime MAY record the FlowGuard work order as passed
- **AND** runtime MAY issue the next Reviewer packet when all other current gates pass.

#### Scenario: Failed self-check blocks Reviewer packet
- **WHEN** a current FlowGuard result has `passed: true`
- **AND** `contract_self_check.all_required_fields_present` or
  `contract_self_check.runtime_mechanical_validation_passed` is false
- **THEN** runtime MUST reject or block that result before work-order pass
  recording
- **AND** runtime MUST NOT issue a Reviewer packet from that result.

#### Scenario: Blocked child evidence blocks Reviewer packet
- **WHEN** a current FlowGuard result has `passed: true`
- **AND** any machine-readable child hard evidence report says blocked,
  revalidation required, missing code contract, or not ok
- **THEN** runtime MUST reject or block that result before work-order pass
  recording
- **AND** runtime MUST NOT issue a Reviewer packet from that result.

#### Scenario: FlowGuard block remains current-path recovery
- **WHEN** FlowGuard hard evidence is blocked
- **THEN** runtime MUST use the current packet/result block or reissue path
- **AND** runtime MUST NOT translate the result through old decision/summary
  formats or other compatibility fallback.
