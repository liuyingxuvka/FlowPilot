## ADDED Requirements

### Requirement: Prompt tightening stays inside current FlowPilot surfaces
FlowPilot SHALL keep node-plan and progress-reporting prompt repairs inside
existing role, packet, route, and status surfaces.

#### Scenario: Node-plan guidance is strengthened
- **WHEN** FlowPilot prompt cards add guidance for executable node plans,
  check surfaces, status vocabulary, expected failure shapes, or node-boundary
  redesign decisions
- **THEN** the guidance MUST reuse existing PM node acceptance, Reviewer node
  plan review, route redesign, and review report surfaces
- **AND** the guidance MUST NOT add node plan fields, route fields, packet
  fields, compatibility aliases, fallback prose parsing, new ledgers, or
  artifact-specific special cases.

#### Scenario: Progress guidance is strengthened
- **WHEN** FlowPilot prompt cards add guidance for more consistent node-fraction
  status reporting
- **THEN** the guidance MUST reuse runtime-owned `progress_fraction.display` and
  existing Controller status surfaces
- **AND** the guidance MUST NOT change progress calculation ownership or require
  Controller to read sealed bodies, derive its own progress, or report internal
  patrol noise.

#### Scenario: Document timing issue appears in a live run
- **WHEN** a live run exposes an artifact timing problem such as an early
  document, package, example, release note, or validation summary consuming a
  later unfinished output
- **THEN** FlowPilot prompt guidance MUST treat it as the generic
  producer-before-consumer and node-boundary problem already owned by route and
  node planning
- **AND** the repair MUST NOT create a README-specific or public-document-only
  rule.
