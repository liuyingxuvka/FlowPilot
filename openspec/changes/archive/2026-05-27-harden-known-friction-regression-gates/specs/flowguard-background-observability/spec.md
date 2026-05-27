## ADDED Requirements

### Requirement: Known-friction validation rejects progress-only evidence
FlowPilot SHALL reject progress-only, path-only, skipped, timed-out, or
model-only background evidence when validating known-friction regression gates.

#### Scenario: Background check is still running
- **WHEN** a long model or daemon check has stdout/stderr progress but no final
  exit artifact and metadata completion status
- **THEN** FlowPilot MUST report the check as in progress and MUST NOT count it
  as passed.

#### Scenario: Background check timed out
- **WHEN** a background or daemon check times out before producing a successful
  final artifact set
- **THEN** FlowPilot MUST report the timeout as a validation gap for any
  affected known-friction gate.

#### Scenario: Proof reuse is claimed
- **WHEN** a long check reuses proof evidence
- **THEN** FlowPilot MUST report whether the proof was valid for the final
  source artifact versions before counting the result as passed.
