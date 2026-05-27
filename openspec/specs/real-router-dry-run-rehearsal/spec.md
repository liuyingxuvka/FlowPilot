# real-router-dry-run-rehearsal Specification

## Purpose
TBD - created by archiving change add-real-router-dry-run-rehearsal. Update Purpose after archive.
## Requirements
### Requirement: Real Router Dry-Run Rehearsal Matrix

FlowPilot SHALL maintain a real-Router dry-run rehearsal matrix for prepared
fake AI work packages that names the full-flow phases, fake artifacts, real
Router/runtime entrypoints, ACK/receipt gates, allowed-event boundary,
expected standard state, evidence test, evidence freshness, and confidence
boundary for each rehearsal row.

#### Scenario: Matrix includes full-flow rehearsal rows

- **WHEN** the rehearsal matrix is generated
- **THEN** it includes rows for startup-to-terminal fake AI packages, CLI
  Router boundary use, compounded control-plane recovery, and proof-gate
  restoration
- **AND** each row identifies the real runtime entrypoints it exercises
- **AND** each row states that live AI semantic quality is not proven by the
  mechanical rehearsal.

#### Scenario: Matrix rejects overclaiming evidence

- **WHEN** a rehearsal row omits ACK/receipt gates, invents external events,
  uses direct state mutation, treats progress-only output as final proof, lacks
  a terminal standard state, or claims live AI semantic quality is proven
- **THEN** matrix validation reports a finding and the row is not accepted as
  passed rehearsal evidence.

### Requirement: Real Runtime Full-Flow Fake AI Rehearsal

FlowPilot SHALL provide an executable rehearsal that drives prepared fake AI
work artifacts through a real Router-controlled run from startup to terminal
closure without bypassing card, packet, role-output, proof, or lifecycle
runtime boundaries.

#### Scenario: Prepared fake AI packages reach closed standard state

- **GIVEN** a fresh FlowPilot project
- **WHEN** prepared PM, reviewer, officer, and worker artifacts are submitted
  through the real card, packet, role-output, and Router event surfaces
- **THEN** the run reaches terminal lifecycle closure
- **AND** the run contains card ACK/read receipts, packet active-holder
  receipts, role-output envelopes, reviewed result evidence, final ledger,
  terminal replay, final summary, and lifecycle closure artifacts.

#### Scenario: Public Router CLI participates in the rehearsal boundary

- **GIVEN** a fresh FlowPilot project
- **WHEN** the public Router CLI starts a run, reports state, returns the next
  action, applies Router actions, records a prepared fake role event, and runs
  until the next wait
- **THEN** those CLI calls return successful Router-owned results
- **AND** the resulting run state reflects the same pending wait boundary that
  the runtime API would observe.

### Requirement: Recovery and Proof Restoration Rehearsal

FlowPilot SHALL cover compounded control-plane recovery where a run can
experience daemon/resume ambiguity and background proof incompleteness yet
return to a legal standard state after final evidence arrives.

#### Scenario: Resume and proof gates restore standard state

- **GIVEN** an active run with startup completed
- **WHEN** a stale daemon owner is detected, duplicate resume events arrive,
  and background proof initially has only progress output
- **THEN** Router resume loads recovery evidence before normal PM work resumes
- **AND** duplicate resume is idempotent
- **AND** progress-only proof is rejected until final exit/meta/combined
  artifacts classify as passed.

### Requirement: FlowGuard Evidence Registration

FlowPilot SHALL register real-Router dry-run rehearsal evidence in the fast
test tier and FlowGuard Model-Test Alignment plan so the evidence cannot be
silently dropped from routine validation.

#### Scenario: Fast tier and model-test alignment see rehearsal evidence

- **WHEN** the fast tier command plan is inspected
- **THEN** it includes the rehearsal matrix, matrix tests, and runtime
  rehearsal tests
- **AND** model-test alignment includes a real-Router dry-run rehearsal
  obligation covered by happy, edge, and negative/failure evidence.
