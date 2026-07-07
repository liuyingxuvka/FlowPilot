## ADDED Requirements

### Requirement: Current status projection derives from one authority path
FlowPilot SHALL derive public current status projections from the current run
ledger, lifecycle guard, foreground duty, final closure, and final-return
preflight only.

#### Scenario: Terminal completion projects consistently
- **GIVEN** the current run ledger has a complete final closure
- **AND** final-return preflight allows terminal return
- **WHEN** FlowPilot renders or saves current status projection
- **THEN** the public projection SHALL expose the current `run_id`, closure
  decision, controller stop permission, final return permission, and update time
- **AND** these values SHALL be derived from the current run authority path.

#### Scenario: Projection does not recover from old runs
- **GIVEN** a current projection field cannot be derived from the current run
  authority path
- **WHEN** FlowPilot renders status
- **THEN** FlowPilot SHALL NOT search newest historical runs, legacy pointer
  fields, old aliases, or prose artifacts to fill the value.

### Requirement: Current blockers exclude historical blocker rows
FlowPilot SHALL expose only current-effective blockers in public current
status, compact status, and current role-memory blocker rows.

#### Scenario: Cleared blocker is history only
- **GIVEN** a blocker row is cleared, retired, superseded, or attached to a
  noncurrent route node
- **WHEN** FlowPilot renders public current status or role memory
- **THEN** the blocker SHALL NOT appear as an active/current blocker
- **AND** it MAY remain available only as historical audit context.

#### Scenario: Awaiting PM decision remains visible
- **GIVEN** a blocker is currently awaiting the PM decision gate
- **WHEN** FlowPilot renders public current status
- **THEN** the blocker SHALL remain visible as current control work.

### Requirement: Node closure projection converges after PM disposition
FlowPilot SHALL converge node-closure projection rows when PM disposition
resolves a node.

#### Scenario: Accepted node closure is no longer awaiting
- **GIVEN** a node closure row is awaiting PM disposition
- **WHEN** PM records an accepting disposition for that node
- **THEN** the node closure row SHALL record the PM disposition id
- **AND** its status SHALL become accepted instead of awaiting.

#### Scenario: Non-accepting PM disposition closes the awaiting projection
- **GIVEN** a node closure row is awaiting PM disposition
- **WHEN** PM records repair, redesign, block, or stop disposition for that node
- **THEN** the node closure row SHALL record the PM disposition id
- **AND** its status SHALL match the PM disposition outcome instead of awaiting.

### Requirement: Repair dossier active pointer is current-only
FlowPilot SHALL NOT expose a cleared, retired, superseded, or noncurrent-route
blocker as the active blocker of a repair dossier.

#### Scenario: Cleared repair blocker is not active dossier pointer
- **GIVEN** a repair dossier was created for a blocker
- **AND** that blocker is no longer current-effective
- **WHEN** FlowPilot refreshes the dossier projection
- **THEN** the dossier SHALL retain lineage history
- **AND** its active blocker pointer SHALL be empty or explicitly noncurrent.

### Requirement: Current projection coverage is Cartesian
FlowPilot SHALL maintain model and test coverage across the finite product of
current authority state, blocker lifecycle, node-closure lifecycle,
repair-dossier lifecycle, and projection surfaces.

#### Scenario: Every projection cell is classified
- **WHEN** the current-status-projection FlowGuard model is checked
- **THEN** every declared Cartesian cell SHALL be classified as current,
  history-only, or rejected
- **AND** no cell SHALL pass by fallback, compatibility alias, missing-field
  default, or historical-run inference.
