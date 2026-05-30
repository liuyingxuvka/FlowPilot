## ADDED Requirements

### Requirement: Fake rehearsals use the public new-runtime control surface
New FlowPilot fake AI rehearsals SHALL drive control-plane progression through the same public folding and wait-boundary surface that a foreground Controller uses, not only through direct private runtime helper calls.

#### Scenario: Public fold path reaches role boundary
- **WHEN** a fake rehearsal starts from a route frontier that needs a node task, FlowGuard packet, review packet, validation packet, or closure packet
- **THEN** the rehearsal MUST call the new-runtime fold path
- **AND** it MUST assert the returned boundary is role dispatch, role wait, terminal, or explicit recovery.

#### Scenario: Adversarial PM repair prose is rehearsed
- **WHEN** a fake rehearsal submits PM repair prose that includes a structured decision plus conflicting rationale words
- **THEN** the rehearsal MUST assert the structured decision wins
- **AND** the resulting blocker lifecycle MUST match that structured decision.
