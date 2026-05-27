# hard-gate-red-team-pack Specification

## Purpose
TBD - created by archiving change add-hard-gate-red-team-pack. Update Purpose after archive.
## Requirements
### Requirement: Hard-gate red-team packages reject unauthorized AI inputs
The system SHALL provide executable red-team packages for AI-facing runtime entrypoints where unauthorized, stale, mismatched, malformed, or progress-only inputs are rejected or converted into an explicit blocker before protected state can advance.

#### Scenario: Unauthorized current wait event
- **WHEN** an AI submits a Router event that is not in the current pending action's `allowed_external_events`
- **THEN** the event MUST be rejected or quarantined without satisfying the wait, clearing the pending action, or advancing route state.

#### Scenario: Role-output authority mismatch
- **WHEN** an AI submits a role-output envelope with a router-supplied event name that is not authorized by the current Router wait state
- **THEN** the role-output runtime MUST reject it before Router event submission and preserve current wait state.

#### Scenario: Packet identity mismatch
- **WHEN** an AI submits a packet or result envelope whose body path, hash, packet id, node id, role, or run authority does not match the active ledger record
- **THEN** the system MUST reject it or record a control blocker without recording the packet/result as completed.

#### Scenario: Progress-only proof overclaim
- **WHEN** an AI submits background progress metadata as if it were completed proof
- **THEN** the system MUST reject the proof package unless final stdout/stderr/combined/exit/meta artifacts prove completion.

#### Scenario: Terminal overclaim
- **WHEN** an AI submits terminal closure while any protected ledger remains dirty or unproven
- **THEN** terminal closure MUST be rejected and the run MUST remain non-closed.

### Requirement: Rejected red-team packages preserve protected state
Every hard-gate red-team package SHALL assert the protected state that must remain unchanged or enter a named blocker state after rejection.

#### Scenario: Rejection preserves pending action
- **WHEN** a bad package is submitted against a pending wait
- **THEN** the test MUST assert that the pending action or active control blocker remains current unless the expected outcome explicitly creates a replacement blocker.

#### Scenario: Rejection preserves terminal status
- **WHEN** a terminal bad package is rejected
- **THEN** the test MUST assert that run status is not closed and terminal closure artifacts are not promoted as clean completion proof.

#### Scenario: Rejection records recovery route
- **WHEN** a bad package is converted into a blocker
- **THEN** the blocker MUST name the recovery route as PM repair, reissue, human confirmation, or protocol dead-end.
