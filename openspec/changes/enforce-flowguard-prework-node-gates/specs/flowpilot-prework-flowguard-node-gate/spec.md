## ADDED Requirements

### Requirement: Route nodes require pre-work FlowGuard before worker execution

FlowPilot SHALL require each current executable route node to have a current
accepted pre-work FlowGuard gate before issuing the node's worker task packet.

#### Scenario: PM node plan is accepted before FlowGuard pre-work gate

- **WHEN** a route node has a PM node design or node acceptance plan accepted
- **THEN** runtime MUST issue a FlowGuard pre-work packet for that node
- **AND** runtime MUST NOT issue the worker node task packet until that
  FlowGuard packet passes for the node's current repair generation.

#### Scenario: Direct worker task issuance is blocked before pre-work pass

- **WHEN** a caller asks runtime to issue a node worker packet
- **AND** the current node lacks an accepted current-generation pre-work
  FlowGuard report
- **THEN** runtime MUST reject worker packet issuance and expose the missing
  pre-work gate as the next required route action.

### Requirement: FlowGuard operator owns route selection inside the pre-work gate

The pre-work FlowGuard packet SHALL carry route-selection policy and candidate
FlowGuard routes, while the FlowGuard operator chooses the needed route or route
combination.

#### Scenario: FlowGuard can choose multiple satellite routes

- **WHEN** runtime issues a pre-work FlowGuard packet
- **THEN** the packet body MUST include the FlowGuard route scheduler rule,
  allowed route map, node modeled target, node acceptance criteria, and a field
  requiring the FlowGuard operator to record all selected routes
- **AND** the packet MUST NOT ask PM to decide whether FlowGuard is needed.

### Requirement: Pre-work FlowGuard artifacts are PM-visible repair material

FlowPilot SHALL make the pre-work FlowGuard model/report artifacts available to
PM for node design repair.

#### Scenario: Pre-work FlowGuard reports a problem

- **WHEN** pre-work FlowGuard returns a blocking result
- **THEN** runtime MUST record a FlowGuard blocker, create a PM repair decision
  packet, and preserve PM-visible report/model artifact references
- **AND** PM repair MUST be able to inspect the FlowGuard report before
  deciding how to repair the node design.

### Requirement: Node repair invalidates the previous pre-work pass

FlowPilot SHALL tie pre-work FlowGuard acceptance to the node's repair
generation.

#### Scenario: Same-node repair requires a fresh pre-work pass

- **WHEN** PM repairs a node after a worker, reviewer, validation, or pre-work
  FlowGuard blocker
- **THEN** the previous pre-work FlowGuard pass MUST NOT authorize a new worker
  packet
- **AND** runtime MUST require a fresh pre-work FlowGuard pass for the repaired
  node generation.

### Requirement: Post-result FlowGuard and Reviewer remain separate gates

FlowPilot SHALL keep post-result FlowGuard and independent Reviewer review after
worker execution.

#### Scenario: Worker result still needs post-result FlowGuard and Reviewer

- **WHEN** a worker node task result is submitted after pre-work FlowGuard pass
- **THEN** runtime MUST still issue the post-result FlowGuard packet for the
  worker result
- **AND** runtime MUST still issue an independent Reviewer packet only after the
  matching post-result FlowGuard report exists.
