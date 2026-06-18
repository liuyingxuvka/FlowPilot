## ADDED Requirements

### Requirement: Fake AI rehearsal executes runtime rejection and repair loops
FlowPilot SHALL provide executable fake-AI rehearsals that submit malformed or
contract-violating results through runtime-owned surfaces, verify precise
runtime rejection, consume the reissue or repair instruction, submit a corrected
second attempt, and return to the legal path.

#### Scenario: Corrected second attempt returns to the legal path
- **WHEN** fake AI submits a supported malformed body, missing field, wrong
  type, wrong finite option, forbidden alias, skipped required read, or
  incomplete active-id coverage result
- **THEN** runtime MUST reject the first attempt with actionable feedback and
  MUST accept the corrected second attempt when it satisfies the current
  reissue contract.

#### Scenario: Runtime feedback is precise enough for repair
- **WHEN** runtime rejects a fake-AI result in an executable rehearsal
- **THEN** the rejection or reissue MUST name the current packet/result family,
  offending field or material path, expected field or option set, and the
  minimal repair route needed for the second attempt.

### Requirement: Repeated same-family failures hit only the existing threshold
FlowPilot SHALL verify that one through four repeated same-family fake-AI
failures remain on normal repair or reissue paths, while the fifth same-family
failure uses the existing break-glass threshold.

#### Scenario: Attempts one through four do not glassbreak
- **WHEN** fake AI repeats the same unrepaired failure family for attempts one
  through four
- **THEN** runtime MUST keep the result on the normal rejection, reissue, or PM
  repair path and MUST NOT enter break-glass.

#### Scenario: Fifth same-family attempt glassbreaks
- **WHEN** fake AI repeats the same unrepaired failure family on the fifth
  attempt
- **THEN** runtime MUST classify the path as the existing break-glass threshold
  route and include the same-family lineage key in the evidence.
