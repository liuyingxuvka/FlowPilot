## ADDED Requirements

### Requirement: Fast process model preserves Router control mechanics
FlowPilot SHALL provide a fast middle-layer FlowGuard model that abstracts
product content while preserving Router tick settlement, legal wait/event
authority, blocker lanes, retry bounds, PM repair returns, route mutation
freshness, and terminal ledger convergence.

#### Scenario: Safe graph converges
- **WHEN** the process liveness model explores the safe Router process graph
- **THEN** every reachable nonterminal state can reach either completion or a controlled blocked state

#### Scenario: Known bad control outcomes fail
- **WHEN** the process liveness model evaluates known bad hazards for stale settlement, wrong wait events, blocker loops, stale route evidence, or premature completion
- **THEN** each hazard is rejected by at least one explicit invariant

### Requirement: Process model preserves per-node review coverage
FlowPilot SHALL model route progress so final route closure is impossible until
every route node has been reached, reviewer-passed, completion-ledgered, and
included in the route-wide scan.

#### Scenario: Final ledger waits for every node
- **WHEN** the process liveness model explores a route with multiple abstract nodes
- **THEN** the route scan, final ledger, completion projection, and completion state are reachable only after all nodes have reviewer pass and completion coverage

#### Scenario: Skipped node hazards fail
- **WHEN** the process liveness model evaluates a state that advances to a later node, final route scan, final ledger, or completion before earlier nodes are reviewed and completed
- **THEN** the state is rejected by an explicit invariant

### Requirement: Process model classifies blocker lanes
FlowPilot SHALL model blocker type before lane selection so local-fix,
route-scope, and fatal-protocol blockers cannot silently take the wrong route.

#### Scenario: Local fix blocker does not jump to PM
- **WHEN** a small local/reconciliation blocker appears before the local retry budget is exhausted
- **THEN** the model rejects PM repair routing and route mutation routing for that blocker

#### Scenario: Route-scope and fatal blockers keep separate lanes
- **WHEN** a route-scope blocker or fatal protocol blocker appears
- **THEN** the model rejects routing the route-scope blocker to local reissue and rejects routing the fatal blocker to ordinary repair

### Requirement: Process projection reports current-run risks without overclaiming
The process liveness runner SHALL inspect current FlowPilot run metadata and
report process-level risks without opening sealed packet or result bodies and
without claiming concrete runtime conformance.

#### Scenario: Current run is stopped or blocked
- **WHEN** the active `.flowpilot/current.json` points to a stopped, blocked, or missing current run
- **THEN** the runner reports that status as process projection evidence rather than treating it as a model pass

#### Scenario: Current run has stale or unresolved control evidence
- **WHEN** current-run metadata indicates active blockers, stale frontier, unresolved ledger items, or incomplete terminal evidence
- **THEN** the runner reports actionable process findings with the relevant metadata paths
