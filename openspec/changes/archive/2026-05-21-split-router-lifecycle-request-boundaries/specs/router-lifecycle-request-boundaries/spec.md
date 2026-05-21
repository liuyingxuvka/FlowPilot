## ADDED Requirements

### Requirement: Lifecycle request owner keeps compatible exports
FlowPilot SHALL preserve the existing router lifecycle request export surface
while splitting the implementation into child owner modules.

#### Scenario: Existing private router exports remain callable
- **WHEN** callers access lifecycle request helpers through `flowpilot_router`
  or import `flowpilot_router_lifecycle_requests`
- **THEN** `_write_run_lifecycle_request`,
  `_write_protocol_dead_end_lifecycle`,
  `_reconcile_terminal_lifecycle_authorities`,
  `_clear_active_control_blocker_for_terminal_lifecycle`,
  `_run_lifecycle_terminal_action`, and
  `_try_write_control_blocker_for_exception` remain available
- **AND** they preserve their existing argument and return behavior.

#### Scenario: Parent facade binds child owners
- **WHEN** the router facade binds `flowpilot_router_lifecycle_requests`
- **THEN** every lifecycle-request child owner receives the same router binding
- **AND** legacy private helper lookups keep resolving through the retained
  facade.

### Requirement: Lifecycle split preserves terminal behavior
FlowPilot SHALL keep lifecycle request artifacts and terminal cleanup semantics
unchanged after the split.

#### Scenario: User stop or cancel still fences route work
- **WHEN** a user stop or cancel lifecycle request is written
- **THEN** run state becomes terminal
- **AND** nonterminal controller work is superseded
- **AND** the terminal fence and reconciliation artifacts are written with the
  same schemas and no further route work is authorized.

#### Scenario: Terminal reconciliation clears stale authorities
- **WHEN** terminal lifecycle reconciliation runs
- **THEN** continuation binding, crew ledger, packet ledger, execution frontier,
  and active control blocker state are reconciled as before
- **AND** cleanup receipts remain visible in the lifecycle record.

### Requirement: Lifecycle split is FlowGuard evidence backed
FlowPilot SHALL treat the lifecycle request split as a StructureMesh-governed
refactor with explicit parity evidence.

#### Scenario: Structure evidence covers lifecycle child modules
- **WHEN** FlowGuard structure-maintenance and router facade split checks run
- **THEN** the lifecycle request facade and child modules are represented in
  the model catalogs
- **AND** the checks pass before local install sync or local git completion is
  claimed.

#### Scenario: Unsafe lifecycle split remains blocked
- **WHEN** validation finds a missing compatibility export, changed lifecycle
  schema, missing child binding, or failed terminal/control-blocker parity test
- **THEN** the change is blocked
- **AND** the failed evidence is reported instead of being treated as a
  successful optimization.
