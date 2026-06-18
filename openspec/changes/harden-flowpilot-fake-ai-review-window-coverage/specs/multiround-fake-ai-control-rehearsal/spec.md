## ADDED Requirements

### Requirement: Rehearsals use responder-level mistake profiles
Multi-round fake AI rehearsals SHALL generate bad submissions, partial repairs,
corrected retries, and repeated same-family failures through the
contract-driven fake AI responder rather than separate hand-written payload
families.

#### Scenario: Bad first response repairs on second response
- **WHEN** a rehearsal asks the fake AI responder to submit a malformed or incomplete current-contract result
- **THEN** runtime MUST reject and reissue with precise repair metadata
- **AND** the same responder MUST be able to consume the reissue contract and generate a corrected second result.

#### Scenario: Partial repair exposes hidden projection gap
- **WHEN** a responder submits a partial repair that fixes only previously visible fields
- **THEN** the rehearsal MUST fail if runtime later exposes an additional validator rule that was not present in the first packet contract.

### Requirement: Rehearsals distinguish repairable format errors from threshold escalation
Multi-round fake AI rehearsals SHALL test format rejection and GlassBreak
threshold behavior as separate dimensions.

#### Scenario: Format error is rejected before threshold logic
- **WHEN** fake AI submits a malformed body for a family that requires a strict JSON object
- **THEN** runtime MUST reject it with format-specific repair guidance
- **AND** no accepted result, reviewer pass, PM disposition, or route mutation may be created from that body.

#### Scenario: Fifth same-family no-delta failure escalates
- **WHEN** fake AI repeats the same unrepaired root failure five times for the same current blocker family
- **THEN** FlowPilot MUST trigger the configured break-glass or equivalent escalation path
- **AND** the first four attempts MUST remain on ordinary reissue or repair paths.
