## ADDED Requirements

### Requirement: Route review preserves startup and product quality floor
FlowPilot SHALL require route and formal gate review prompts to catch a route
that satisfies structure but loses the startup/product high-quality posture.

#### Scenario: Route draft is structurally valid but shallow
- **WHEN** PM submits a route draft that names nodes and gates but lacks a
  concrete user-useful outcome, proof of depth, or acceptance-item projection
- **THEN** Reviewer guidance MUST treat the draft as a quality-floor loss and
  block or return it for PM repair through existing review fields.

#### Scenario: Node plan omits the hard part
- **WHEN** PM writes a node acceptance plan for work that has a task-specific
  hard part
- **THEN** the node prompt/template MUST require PM to name that hard part or
  explain why the node truly has no local hard part.

#### Scenario: Packet carries current quality floor to worker
- **WHEN** PM issues an executable work packet
- **THEN** the packet prompt MUST tell the addressed role to complete the
  current assignment as high-quality current-run work inside the packet
  boundary
- **AND** Reviewer and result prompts MUST preserve acceptance-item and proof
  of depth evidence using existing fields.
