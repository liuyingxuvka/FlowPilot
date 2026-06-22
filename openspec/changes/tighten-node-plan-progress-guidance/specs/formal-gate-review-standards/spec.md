## ADDED Requirements

### Requirement: PM node plans expose current executable check surfaces
FlowPilot SHALL instruct PM to make worker-ready node acceptance plans concrete
enough to identify the current executable check surface without adding new
runtime fields.

#### Scenario: PM writes a worker-ready node plan
- **WHEN** PM submits a `decision: "pass"` node acceptance plan for a leaf or
  repair node
- **THEN** the plan guidance MUST require PM to identify, when relevant, the
  current files, artifacts, behavior surface, checker, command, validation
  entrypoint, status vocabulary, and expected failure shape that make the node
  executable and reviewable
- **AND** the guidance MUST keep those details inside existing plan text,
  acceptance criteria, known risks, supporting notes, or acceptance-item
  projection rather than a new required field.

#### Scenario: Current check surface is unclear
- **WHEN** PM cannot make the current check surface concrete enough for one
  bounded worker outcome
- **THEN** PM guidance MUST frame that gap as evidence that the current node may
  be too broad, mixed, wrongly bounded, or under-split
- **AND** PM MUST consider the existing `redesign_route` path with a
  replacement parent or module and ordered child nodes when the current node is
  not worker-ready.

#### Scenario: Negative fixture or expected failure work is planned
- **WHEN** a node plan includes negative cases, bad fixtures, expected-failure
  examples, or status-vocabulary-sensitive checks
- **THEN** PM guidance MUST require the plan to state the expected failure
  shape or accepted status vocabulary at the level needed for Reviewer and
  Worker to avoid inventing the acceptance boundary.

### Requirement: Reviewer blocks abstract node acceptance plans
FlowPilot SHALL instruct Reviewer to block node acceptance plans that are not
concrete enough for worker dispatch while preserving the plan-stage boundary.

#### Scenario: PM plan leaves executable checks undefined
- **WHEN** Reviewer reviews a PM node acceptance plan before worker dispatch
- **AND** the plan uses generic wording such as "run validation" while the
  current node needs named checks, commands, status vocabulary, expected failure
  shapes, or a defined worker outcome
- **THEN** Reviewer MUST block the plan through the existing review report
  fields and recommend PM repair, node-boundary clarification, or existing
  route redesign.

#### Scenario: Reviewer stays inside plan-stage evidence boundary
- **WHEN** Reviewer blocks an abstract PM node plan
- **THEN** Reviewer MUST block because the plan itself is not executable or
  bounded enough
- **AND** Reviewer MUST NOT block solely because future Worker artifacts,
  post-result FlowGuard evidence, fresh result-stage checks, or final release
  evidence do not exist yet.
