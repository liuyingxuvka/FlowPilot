# route-producer-consumer-ordering Specification

## ADDED Requirements

### Requirement: Route plans preserve producer-before-consumer ordering

FlowPilot SHALL require PM route plans to keep every node's required inputs,
claimed outputs, acceptance criteria, deliverable checks, and validation checks
consistent with route order.

#### Scenario: Consumer node follows producer node

- **GIVEN** a route contains a producer node that creates a CLI, fixture,
  example, test result, validation result, release artifact, report input, or
  other node-owned output
- **AND** a later consumer node cites, summarizes, validates, packages,
  documents, or otherwise depends on that output
- **WHEN** PM drafts or mutates the route
- **THEN** the producer node SHALL appear before the consumer node unless the
  dependency is already satisfied by current external material or by the same
  node's owned work.

#### Scenario: Future-node dependency blocks route viability

- **GIVEN** a route node's artifact, acceptance criteria, deliverable checks,
  or validation checks depend on output that is only produced by a later
  unfinished node
- **WHEN** FlowGuard operator performs the route-process check
- **THEN** the route-process report SHALL treat the route as not viable as
  drafted
- **AND** the report SHALL use the existing repair/block outcome and
  `recommended_resolution` surface to tell PM that route order or node scope
  must be corrected.

### Requirement: Route review independently challenges dependency order

FlowPilot SHALL require Reviewer route challenge to inspect whether PM and
FlowGuard operator preserved producer-before-consumer ordering.

#### Scenario: Reviewer catches inverted dependency

- **GIVEN** a reviewed route places a consumer artifact before the unfinished
  node that produces the evidence or output it consumes
- **WHEN** Reviewer performs route challenge
- **THEN** Reviewer SHALL block route approval through the existing review
  result fields
- **AND** Reviewer SHALL recommend PM route repair without becoming the route
  author.

### Requirement: Node entry rejects future-node dependency without demanding future evidence

FlowPilot SHALL require current-node acceptance review to distinguish current
inputs from future-node outputs.

#### Scenario: Current node needs future output

- **GIVEN** PM submits a node acceptance plan for the current node
- **AND** executing that node as planned requires output from a later
  unfinished route node
- **WHEN** Reviewer reviews the node acceptance plan
- **THEN** Reviewer SHALL block worker dispatch and recommend PM route
  correction through the existing node-plan review surface.

#### Scenario: Current bounded slice does not need future output

- **GIVEN** PM submits a node acceptance plan whose artifact is scoped to
  current available material and does not cite future-node output as completed
  evidence
- **WHEN** Reviewer reviews the node acceptance plan
- **THEN** Reviewer SHALL NOT block solely because future route nodes have not
  produced their later-stage artifacts.
