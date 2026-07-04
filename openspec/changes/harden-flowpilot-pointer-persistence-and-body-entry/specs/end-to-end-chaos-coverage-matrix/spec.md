## ADDED Requirements

### Requirement: Pointer and body-entry faults have Cartesian coverage
FlowPilot SHALL include pointer persistence and `submit-result` body-entry
faults in the existing Cartesian/model coverage universe rather than covering
them only with hand-written example tests.

#### Scenario: Pointer fault matrix is generated
- **WHEN** the control-plane Cartesian model is generated
- **THEN** it MUST include current pointer state, index state, run candidate
  count, ledger readability, and writer-lock state axes
- **AND** each applicable combination MUST have an oracle of pass, recover,
  wait, block, or reject.

#### Scenario: Body-entry fault matrix is generated
- **WHEN** the current-contract or integration Cartesian model is generated
- **THEN** it MUST include body transport and body shape axes covering inline
  object, inline string, malformed inline JSON, inline non-object JSON,
  body-file object, body-file malformed JSON, body-file non-object JSON, and
  unreadable body-file cases.

#### Scenario: Inapplicable combinations are explicit
- **WHEN** a Cartesian combination is unreachable or out of scope
- **THEN** the generated evidence MUST include a skip reason rather than
  silently omitting the combination.
