## ADDED Requirements

### Requirement: PM route plans materialize into executable route nodes

The new FlowPilot runtime SHALL treat the first PM planning result as a route
planning artifact, not as the whole project result. A valid PM planning result
MUST materialize an active route node set, node acceptance criteria, and an
execution frontier before project execution can continue.

#### Scenario: PM planning result does not close the project

- **WHEN** the PM planning packet result is accepted
- **THEN** the runtime MUST create or refresh route nodes and execution
  frontier state
- **AND** the next action MUST be route materialization, first-node packet
  issuance, repair, or block
- **AND** the next action MUST NOT be terminal completion solely because the
  PM planning packet's FlowGuard/review/validation/closure chain passed.

#### Scenario: Route draft has executable nodes

- **WHEN** route materialization succeeds
- **THEN** every effective node MUST have a `node_id`, responsibility,
  modeled target, acceptance criteria, status, and route version
- **AND** the execution frontier MUST identify the current node or a concrete
  blocker.

### Requirement: Route node work uses the symmetric packet lifecycle

The runtime SHALL execute each effective route node through current-run packets
using the same lease, ACK, result, FlowGuard, review, validation, and closure
side-effect discipline used by the foundation packet chain.

#### Scenario: First node packet is issued after planning

- **WHEN** the execution frontier has an incomplete current node with no open
  node task packet
- **THEN** the router MUST issue a `task` packet scoped to that node
- **AND** the packet envelope MUST name `route_node_id`,
  `required_flowguard_target`, responsibility, and route version.

#### Scenario: Node cannot advance from ACK only

- **WHEN** a node packet has a lease ACK but no valid result
- **THEN** the node MUST remain incomplete
- **AND** the router MUST wait for a result, replace an inactive lease, repair,
  expire, or block.

### Requirement: PM disposition gates node acceptance

The runtime SHALL require a PM disposition before marking a node accepted after
reviewed node work. PM disposition MUST distinguish accepted node work from
repair, route mutation, split, block, or stop decisions.

#### Scenario: Reviewed node awaits PM disposition

- **WHEN** a node task result has matching FlowGuard evidence, independent
  review, and current validation evidence
- **THEN** the node MUST move to `awaiting_pm_disposition`
- **AND** the router MUST NOT mark the node accepted until PM disposition is
  recorded.

#### Scenario: PM accepts node and frontier advances

- **WHEN** PM disposition for the current node is `accept`
- **THEN** the runtime MUST mark the node accepted, close its node ledger entry,
  and advance the frontier to the next effective node or final route-wide
  closure.

### Requirement: Route mutation invalidates affected node evidence

The runtime SHALL support route mutation from PM disposition, review failure,
validation failure, stale evidence, late output, or FlowGuard model-miss
evidence. A mutation MUST supersede affected packets/results/nodes and prevent
old evidence from closing the new route.

#### Scenario: Mutation supersedes current node

- **WHEN** PM disposition requests route mutation for a node
- **THEN** the runtime MUST write a route mutation record, mark affected node
  evidence stale or superseded, update the route version, and rewrite the
  execution frontier to a repair or replacement node.

#### Scenario: Late old-route result is quarantined

- **WHEN** a packet result from a superseded route version returns after a route
  mutation
- **THEN** the runtime MUST record it as non-authoritative or quarantined
- **AND** it MUST NOT satisfy node acceptance or final closure for the active
  route.

### Requirement: FlowGuard target is selected by route node

Each route node SHALL declare the modeled target required for its FlowGuard
work. The runtime MUST select the FlowGuard skill from that target and reject a
passing report for the wrong target.

#### Scenario: UI node requires UI flow target

- **WHEN** a route node declares `ui_interaction_flow`
- **THEN** its FlowGuard work order MUST select
  `flowguard-ui-flow-structure`
- **AND** a `development_process` report MUST NOT satisfy that node's
  FlowGuard gate.

### Requirement: Final closure uses a route-wide gate ledger

The runtime SHALL attempt terminal completion only after rebuilding a final
route-wide gate ledger from the current active route, effective nodes, packets,
FlowGuard reports, reviews, validation evidence, stale evidence, unresolved
resources, and residual risks.

#### Scenario: Missing node blocks final closure

- **WHEN** any effective route node is not accepted, explicitly superseded, or
  explicitly waived by PM with current evidence
- **THEN** final closure MUST be blocked with a missing-node or incomplete-node
  blocker.

#### Scenario: Route-wide ledger closes the project

- **WHEN** all effective nodes are accepted, all required FlowGuard targets
  have current passing reports, validation is fresh, all stale evidence is
  resolved, and the route-wide ledger unresolved count is zero
- **THEN** final closure MAY return terminal completion.

### Requirement: Fake AI rehearsal proves recursive traversal

Fake AI rehearsal SHALL exercise the public startup and CLI surface through a
multi-node route, including successful traversal and bad-case branches for
repair, mutation, stale evidence, wrong FlowGuard target, dead lease, and
missing-node closure.

#### Scenario: Normal fake project traverses multiple nodes

- **WHEN** deterministic fake agents complete a prepared multi-node project
  through the public CLI
- **THEN** the rehearsal MUST show at least three accepted route nodes before
  terminal completion
- **AND** public status MUST hide sealed startup and role result bodies.

#### Scenario: Missing node is detected by rehearsal

- **WHEN** deterministic fake agents complete the foundation packet chain but
  leave a route node incomplete
- **THEN** the rehearsal MUST observe blocked final closure
- **AND** the run MUST NOT report terminal completion.
