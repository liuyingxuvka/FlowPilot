## ADDED Requirements

### Requirement: Fake AI responder includes review-window behavior profiles
FlowPilot SHALL extend the existing contract-driven fake AI responder with
review-window-aware profiles generated from the emitted packet contract and
review-window completeness row.

#### Scenario: Shallow Reviewer pass is detected
- **WHEN** fake Reviewer output passes mechanically but omits required
  challenge work or required material reads declared by the review window
- **THEN** the rehearsal MUST classify the output as an invalid shallow pass
- **AND** the path MUST block or request repair instead of advancing the gate.

#### Scenario: Reviewer asks for future-stage material
- **WHEN** fake Reviewer output demands material forbidden by
  `review_window.forbidden_future_stage_demands`
- **THEN** the rehearsal MUST classify the output as a review-window boundary
  violation
- **AND** the path MUST return a repairable block or PM-visible correction.

#### Scenario: Reviewer self-repair is rejected
- **WHEN** fake Reviewer output attempts to repair the reviewed artifact instead
  of blocking or requesting PM repair
- **THEN** the rehearsal MUST reject the behavior as outside Reviewer authority
- **AND** the reviewed gate MUST NOT be advanced from the self-repair.

### Requirement: Review-window retry behavior is threshold-covered
FlowPilot SHALL test repeated same-family review-window failures with the
existing retry and break-glass threshold semantics.

#### Scenario: Attempts one through four stay normal
- **WHEN** fake AI repeats the same review-window failure fewer than five times
- **THEN** Runtime MUST keep the failure on the normal reissue or repair path
- **AND** the path MUST NOT trigger break-glass.

#### Scenario: Fifth same-family failure triggers threshold path
- **WHEN** fake AI repeats the same review-window failure for the fifth time
- **THEN** Runtime MUST trigger the existing break-glass threshold path
- **AND** the break-glass evidence MUST remain recovery evidence, not a gate
  pass.
