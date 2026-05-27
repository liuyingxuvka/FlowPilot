## ADDED Requirements

### Requirement: Singleton Authority Matrix
FlowPilot SHALL maintain an install-visible singleton authority matrix that classifies each audited object family by legal plurality, singleton scope, canonical owner, identity key, generation or version key, replay behavior, conflict behavior, and old-object disposition.

#### Scenario: Intended plurality is not treated as a duplicate
- **WHEN** the matrix classifies runs or Flow blocks as intentionally plural
- **THEN** the audit reports them as legal plurality only when run-targeted authority remains explicit
- **AND** it does not require a global singleton current run or global singleton active Flow block

#### Scenario: Singleton object lacks an identity key
- **WHEN** an audited object family is classified as singleton-scoped
- **AND** the matrix does not name a scope and identity key
- **THEN** FlowPilot reports an authority gap before broad singleton confidence can be claimed

### Requirement: Singleton Conflict Model
FlowPilot SHALL include a focused FlowGuard model/checker that rejects duplicate singleton authority hazards across daemon writers, active packet holders, PM package dispositions, route replacements, material progress generations, ACK/output waits, and final closure evidence.

#### Scenario: Conflicting singleton transition is modeled
- **WHEN** a modeled transition creates a second authority in the same singleton scope without authorized replay, repair, reissue, supersession, quarantine, or stale disposition
- **THEN** the checker reports the transition as a detected hazard

#### Scenario: Legal replay remains idempotent
- **WHEN** a duplicate observation has the same scope, identity key, generation/version, and body or proof hash required for idempotent replay
- **THEN** the checker treats it as replayed evidence rather than a second side effect

### Requirement: Live Singleton State Audit
FlowPilot SHALL provide a read-only audit for current `.flowpilot` live state that classifies singleton surfaces as safe, risky, or evidence-insufficient without mutating active runs.

#### Scenario: Active run has multiple current packet authorities
- **WHEN** the live audit observes two active packet authorities in the same run and route/frontier scope
- **THEN** it reports a risk with the conflicting packet ids and the missing disposition

#### Scenario: Live run evidence is insufficient
- **WHEN** required ledgers, lock files, result artifacts, or frontier files are missing or unparsable
- **THEN** the audit reports evidence-insufficient instead of passing the singleton surface

### Requirement: Singleton Evidence Gates Broad Confidence
FlowPilot SHALL feed singleton authority gaps, risky live-state findings, stale result artifacts, and progress-only background evidence into model maturation and final confidence boundaries.

#### Scenario: Singleton gap scopes confidence
- **WHEN** singleton authority evidence contains an unresolved gap or stale proof
- **THEN** broad maintenance, install, or full-model confidence is reported as scoped until the gap is resolved or explicitly waived by the owning route

#### Scenario: Singleton evidence is current
- **WHEN** singleton authority matrix, model results, live audit, targeted tests, and install checks are current and pass for the bounded scope
- **THEN** FlowPilot may include singleton duplicate safety in the bounded confidence claim
