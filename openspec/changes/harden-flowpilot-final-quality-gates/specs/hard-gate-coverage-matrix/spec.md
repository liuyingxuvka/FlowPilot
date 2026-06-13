## ADDED Requirements

### Requirement: Final Quality Negative Cases Have Executable Coverage
The hard-gate coverage matrix SHALL include executable negative coverage for
blocked Reviewer evidence, stale or progress-only FlowGuard evidence, failed
validation evidence, old-route evidence, and incomplete terminal replay.

#### Scenario: Blocked evidence case lacks test coverage
- **WHEN** the hard-gate coverage matrix is generated after this change
- **AND** no executable test covers blocked review evidence being rejected by
  final gates
- **THEN** the matrix MUST report missing hard-gate coverage.

#### Scenario: Terminal replay parity case lacks test coverage
- **WHEN** the hard-gate coverage matrix is generated after this change
- **AND** no executable test covers missing or unexpected terminal replay
  segments being rejected
- **THEN** the matrix MUST report missing hard-gate coverage.
