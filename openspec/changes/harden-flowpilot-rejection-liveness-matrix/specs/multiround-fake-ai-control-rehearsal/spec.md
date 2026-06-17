## ADDED Requirements

### Requirement: Fake AI rehearsals include no-delta retry rows
FlowPilot SHALL include prepared fake AI rehearsal rows where malformed output
is rejected and the next fake AI attempt repeats the same payload or action
without a semantic delta.

#### Scenario: Same malformed payload is blocked
- **WHEN** a fake AI rehearsal submits a malformed payload and then resubmits
  the same payload after actionable rejection feedback
- **THEN** the rehearsal MUST classify the second attempt as no-delta retry
- **AND** it MUST require blocker, repair, stop, wait, or break-glass routing
  instead of ordinary progress.

#### Scenario: Corrected malformed payload advances
- **WHEN** the fake AI rehearsal resubmits the payload with the cited missing
  field, body, identity, owner, command, or evidence repaired
- **THEN** the rehearsal MAY advance through the current contract
- **AND** it MUST record the repaired cell id and evidence owner.

### Requirement: Fake AI malformed cells are contract-derived
Fake AI malformed-output rehearsals SHALL derive required payload cells from
current packet/result/report contracts where practical, rather than relying
only on static hand-picked fixtures.

#### Scenario: New contract field creates a cell
- **WHEN** a current contract family declares a required field or body/hash/path
  dependency that participates in control-plane progress
- **THEN** the fake AI matrix MUST include a missing or invalid cell for that
  requirement unless it is explicitly out of scope with rationale.

#### Scenario: Fake AI matrix covers corrected follow-up
- **WHEN** a fake AI malformed-output cell is included for a rejected payload
- **THEN** the rehearsal set MUST include the rejected payload, the same-payload
  no-delta retry, and a corrected retry when the current contract has a known
  minimal valid shape.
