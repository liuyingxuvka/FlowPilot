## ADDED Requirements

### Requirement: Route Structural Convergence Is Planned Up Front

FlowPilot route planning SHALL include a route-wide structural convergence
review that names expected cleanup, disallowed fallback or compatibility
surfaces, allowed current-runtime recovery, and intentionally retained
maintenance layers before work packets are issued.

#### Scenario: PM route skeleton names structural convergence

- **WHEN** the PM creates or revises a FlowPilot route skeleton
- **THEN** the route artifact SHALL include a structural convergence review
- **AND** that review SHALL name cleanup targets, fallback-like paths that must
  be rejected or removed, and any owned maintenance layer that is allowed to
  remain
- **AND** it SHALL identify the validation evidence needed before completion.

#### Scenario: Current-runtime recovery is allowed only with ownership

- **WHEN** a route needs a recovery path for failed, missing, or malformed
  current work
- **THEN** the recovery path SHALL name the current route, current node or
  packet, owner, blocking state, required repair command, and validation
  evidence
- **AND** it SHALL NOT silently translate old artifacts or stale fields into
  current completion evidence.

### Requirement: Node Work Captures Structure Hygiene

FlowPilot node acceptance plans, work packets, and worker results SHALL capture
the structure-hygiene expectation and the observed structure-hygiene delta for
that node.

#### Scenario: Node plan declares the expected hygiene outcome

- **WHEN** a node acceptance plan is prepared
- **THEN** it SHALL include the node's structure-hygiene expectation
- **AND** the expectation SHALL say whether the node must remove, reject,
  preserve-as-negative-evidence, or intentionally retain an owned maintenance
  surface.

#### Scenario: Worker result reports the actual hygiene delta

- **WHEN** a worker returns a node result
- **THEN** the result SHALL report the actual structure-hygiene delta
- **AND** it SHALL list introduced, removed, rejected, or retained
  fallback-like paths
- **AND** any retained path SHALL include owner, reason, validation evidence,
  and sunset or next-disposition criteria.

### Requirement: Final Closure Blocks Unresolved Structure Debt

The system SHALL block done claims during FlowPilot final evidence packaging,
route-wide gate ledger creation, and terminal closure when structural debt,
fallback-like paths, stale generated artifacts, or unclear maintenance layers
remain unresolved.

#### Scenario: Final ledger disposes of all structure debt

- **WHEN** the PM builds the final route-wide ledger
- **THEN** the ledger SHALL include structure-debt dispositions
- **AND** every fallback-like path, compatibility branch, duplicate adapter,
  stale generated artifact, or intentionally retained maintenance surface SHALL
  be marked removed, rejected, retained-as-negative-evidence, owned-current
  maintenance, or blocked
- **AND** blocked or unowned entries SHALL prevent final completion.

#### Scenario: Terminal closure rejects old-path completion

- **WHEN** terminal closure is evaluated
- **THEN** FlowPilot SHALL NOT count stale artifacts, old route fields,
  compatibility wrappers, newest-run fallbacks, or repo-root fallbacks as
  completion evidence
- **AND** it SHALL require current structured evidence for the active route.

### Requirement: FlowGuard Checks Cover Structural Convergence Hazards

The FlowGuard planning-quality model SHALL include negative scenarios and tests
for missing structural convergence review, missing node hygiene expectation,
missing packet/result hygiene delta, unowned recovery retention, repair paths
that retain compatibility branches, and final ledgers with unresolved
structure debt.

#### Scenario: Model rejects missing or unresolved structure hygiene

- **WHEN** a planning-quality scenario omits structural convergence evidence or
  leaves unowned fallback-like paths unresolved
- **THEN** the executable model SHALL classify the route as failed
- **AND** the reported hazard SHALL identify the missing or unresolved
  structural convergence obligation.
