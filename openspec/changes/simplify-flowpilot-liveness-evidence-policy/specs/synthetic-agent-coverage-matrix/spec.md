# synthetic-agent-coverage-matrix Spec Delta

## MODIFIED Requirements

### Requirement: Synthetic agent coverage matrix covers current control-plane wait failures
The synthetic/fake-agent rehearsal matrix SHALL cover the Cartesian
ACK/progress/evidence-age/current-result/legacy-field combinations for the
current liveness evidence policy.

#### Scenario: Cartesian liveness matrix is generated
- **WHEN** the fake-agent matrix is built for background-role wait behavior
- **THEN** it includes ACK state, result state, progress state, legacy pollution
  state, evidence-age bucket, and reminder-history dimensions
- **AND** every generated case has an explicit expected runtime decision.

#### Scenario: Reminder then progress recovers
- **WHEN** a fake agent receives the strong progress reminder after stale
  evidence
- **THEN** a valid same-lease same-packet progress response returns the wait to
  patrol/grace
- **AND** it does not satisfy the final output obligation.

#### Scenario: Legacy liveness payload is rejected
- **WHEN** a fake agent submits `timeout_unknown`, host-liveness timeout, or
  bounded-wait timeout as the response to a current progress reminder
- **THEN** runtime rejects the payload as unsupported
- **AND** the case remains in the proper wait/reminder/replacement path based
  only on ACK/progress evidence age.
