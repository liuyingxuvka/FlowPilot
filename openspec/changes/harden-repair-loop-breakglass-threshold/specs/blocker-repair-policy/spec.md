# blocker-repair-policy Delta

## ADDED Requirements

### Requirement: Same-family repair loops enter break-glass after five attempts
FlowPilot SHALL stop issuing ordinary PM repair packets for a blocker family
after more than five same-family repair attempts and SHALL route the current
run to Controller break-glass evaluation.

#### Scenario: Under threshold uses normal repair
- **GIVEN** a same-family repair chain has five or fewer attempts
- **WHEN** the next semantic blocker needs a PM repair decision
- **THEN** FlowPilot may issue the ordinary PM repair packet through the current
  blocker repair policy.

#### Scenario: Over threshold enters break-glass
- **GIVEN** a same-family repair chain has more than five attempts
- **WHEN** the next semantic blocker would receive another ordinary PM repair
  packet
- **THEN** FlowPilot MUST NOT issue that ordinary PM repair packet
- **AND** FlowPilot MUST expose a control-plane break-glass duty with the
  family key, attempt count, threshold, and involved blocker ids.

#### Scenario: Mechanical progress is not enough
- **GIVEN** each repair iteration creates a new packet, route version, or repair
  node
- **WHEN** the normalized repair family and missing-information class remain
  the same
- **THEN** FlowPilot still counts the iterations as the same repair family for
  threshold purposes.
