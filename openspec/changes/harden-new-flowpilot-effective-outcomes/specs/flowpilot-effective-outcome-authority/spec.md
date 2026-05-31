## ADDED Requirements

### Requirement: Declared outcomes are the only semantic authority

The new FlowPilot runtime SHALL derive packet pass/block/fail semantics from
structured outcome fields or explicit outcome declaration lines, not from
arbitrary words found elsewhere in the result body.

#### Scenario: Declared pass survives historical failure wording

- **WHEN** a result declares `Status: PASS`
- **AND** the explanatory body mentions an old failed check, a blocked prior
  packet, or function-block modeling terminology
- **THEN** the runtime MUST record the packet outcome as pass
- **AND** it MUST NOT create a semantic blocker from those contextual words.

#### Scenario: Declared block remains blocking

- **WHEN** a result declares `Decision: block`, `Status: failed`, or an
  equivalent recognized non-pass outcome field
- **THEN** the runtime MUST record a non-pass packet outcome
- **AND** it MUST route the result through the existing semantic blocker and PM
  repair path.

#### Scenario: Narrative-only non-pass wording is not authority

- **WHEN** a result body has no recognized outcome field and no recognized
  declaration line
- **AND** the body merely contains words such as `failed`, `block`, or
  `needs more evidence`
- **THEN** those words MUST NOT create a semantic blocker by themselves.

### Requirement: Semantic blocker routing uses a current-effective view

The runtime SHALL distinguish the historical blocker ledger from the current
blocker view used by routing, status projection, and closure.

#### Scenario: Accepted route node does not project stale blockers

- **WHEN** a blocker is still recorded in an active-like status
- **AND** the route node it targets is accepted, waived, or superseded
- **THEN** runtime status and next-action selection MUST NOT treat that blocker
  as current.

#### Scenario: Current unresolved work still blocks

- **WHEN** a blocker is active-like
- **AND** its target node or target packet is still unresolved current work
- **THEN** runtime status, next-action selection, and closure MUST continue to
  treat that blocker as current.

### Requirement: Same-gate repair pass clears the effective blocker chain

The runtime SHALL clear current semantic blockers after a newer pass from the
same gate class and required recheck role for the same repair chain or route
node.

#### Scenario: Repair pass clears old failed packet from current closure

- **WHEN** a blocked packet is repaired by a fresh same-gate pass
- **THEN** the matching semantic blocker MUST be marked cleared
- **AND** the old blocked packet MUST remain historical audit data rather than
  unresolved final-closure work.

### Requirement: Final ledgers check current effective packets

Final route-wide and closure ledgers SHALL require only current effective
packets to be accepted or legally non-current.

#### Scenario: Historical blocked packets under accepted nodes do not block final closure

- **WHEN** a packet row belongs to an accepted, waived, or superseded route node
- **AND** that packet row is old blocked history rather than current work
- **THEN** final route-wide ledger construction MUST NOT emit
  `packet_not_accepted` for that historical packet.

#### Scenario: Active-node open packet still blocks final closure

- **WHEN** a packet row belongs to a current unresolved route node
- **AND** the packet is not accepted or legally non-current
- **THEN** final route-wide ledger construction MUST emit
  `packet_not_accepted` for that packet.
