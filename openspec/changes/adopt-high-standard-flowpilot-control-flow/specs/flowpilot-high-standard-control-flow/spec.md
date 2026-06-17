# flowpilot-high-standard-control-flow Specification

## Purpose

Define the mandatory high-standard control-flow gates for the new black-box
FlowPilot runtime. This capability preserves the necessary old FlowPilot
protections while avoiding old router authority, fixed crews, and UI-heavy
monitoring.

## ADDED Requirements

### Requirement: PM high-standard contract gates route planning
FlowPilot SHALL require an accepted PM high-standard contract before a PM route
planning result can materialize executable route nodes.

#### Scenario: PM planning is blocked before high-standard contract
- **WHEN** the startup intake is recorded and a formal run begins
- **AND** no accepted high-standard contract exists
- **THEN** the next legal runtime action is to issue or complete the
  high-standard contract gate
- **AND** PM route planning cannot close the project or materialize route
  nodes.

#### Scenario: High-standard contract distinguishes blocking and nonblocking standards
- **WHEN** PM writes the high-standard contract
- **THEN** it SHALL classify expectations as hard current requirements,
  high-standard current requirements, current optional improvements, future
  suggestions, or rejected expansions
- **AND** only hard/current rows become closure-blocking requirements.

### Requirement: Current discovery gates precede route planning
FlowPilot SHALL require current-run material discovery and local skill
inventory before route planning can close.

#### Scenario: Material discovery is required
- **WHEN** PM attempts route planning before accepted material discovery
- **THEN** FlowPilot SHALL block route materialization and require current-run
  material discovery evidence.

#### Scenario: Skill inventory is candidate-only
- **WHEN** local skills are discovered
- **THEN** the inventory SHALL be treated as candidate input only
- **AND** no raw skill availability row can satisfy a selected skill standard
  or final closure obligation by itself.

### Requirement: Selected skills create explicit standard obligations
FlowPilot SHALL require PM to convert selected child or process-support skills
into skill standard obligations before route nodes can rely on those skills.

#### Scenario: Selected skill has evidence obligations
- **WHEN** PM selects a skill as required or conditional
- **THEN** FlowPilot SHALL record a skill standard contract row with role use,
  use context, required evidence, reviewer or officer check, and waiver
  authority.

#### Scenario: Manifest-only skill evidence blocks
- **WHEN** a node or final closure cites a selected skill but has no current
  evidence row for that skill standard
- **THEN** FlowPilot SHALL block the node or final closure instead of accepting
  self-attestation.

### Requirement: Node acceptance plan gates node execution
FlowPilot SHALL require an accepted node acceptance plan before issuing a task
packet for a route node.

#### Scenario: Node task waits for acceptance plan
- **WHEN** the execution frontier has an active node
- **AND** that node has no accepted node acceptance plan
- **THEN** the next legal runtime action is a node acceptance plan packet
- **AND** a worker task packet is not legal for that node.

#### Scenario: Accepted plan binds proof obligations
- **WHEN** a node acceptance plan is accepted
- **THEN** it SHALL bind the node to high-standard requirement ids,
  acceptance criteria, selected skill standard obligations, evidence
  obligations, low-quality-success risks, and repair policy.

### Requirement: Node rejection defaults to same-node repair
FlowPilot SHALL treat ordinary quality, evidence, test, or skill-use gaps as
same-node repair unless PM explicitly selects structural route mutation.

#### Scenario: PM repair keeps node active
- **WHEN** PM disposition for a node is `repair`
- **THEN** FlowPilot SHALL keep the same route node active, increment the node
  repair generation, stale the previous node task evidence, and require a new
  node task packet under the same node.

#### Scenario: Route mutation is structural
- **WHEN** PM disposition is `mutate_route`
- **THEN** FlowPilot SHALL create a new route version, supersede affected
  evidence, and rewrite the execution frontier.

### Requirement: Parent backward replay gates parent/module closure
FlowPilot SHALL require current parent backward replay before accepting a
parent or module node that has effective children. Any authority waiver must
use the formal authority-waiver path and must not create a separate
low-risk/high-risk parent replay branch.

#### Scenario: Parent cannot close from child acceptance alone
- **WHEN** all children of a parent node are accepted
- **AND** the parent node itself has no accepted backward replay or waiver
- **THEN** FlowPilot SHALL block parent acceptance and require parent backward
  replay.

### Requirement: Final closure requires a requirement-evidence matrix
FlowPilot SHALL require a clean final requirement-evidence matrix before
terminal completion.

#### Scenario: Missing requirement evidence blocks closure
- **WHEN** the final route-wide ledger is otherwise clean
- **AND** any hard/current high-standard requirement, selected skill standard,
  node acceptance obligation, FlowGuard target, review, validation, or PM
  disposition lacks current evidence
- **THEN** final closure SHALL be blocked.

#### Scenario: Clean matrix allows closure
- **WHEN** every effective route node is accepted or waived
- **AND** every hard/current requirement and selected skill obligation has
  current evidence
- **AND** FlowGuard, review, validation, PM disposition, parent replay, and
  material discovery gates are current
- **THEN** FlowPilot MAY complete terminal closure.
