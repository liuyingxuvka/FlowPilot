# control-plane-failure-canary Specification

## Purpose
TBD - created by archiving change add-control-plane-failure-canary. Update Purpose after archive.
## Requirements
### Requirement: Control-plane canary rows are finite and evidence-bound
The system SHALL maintain a finite control-plane failure canary matrix where each row declares the failure injection, control-plane surface, protected invariant, recovery route, standard final state, evidence role, executable evidence owner, and bounded confidence text.

#### Scenario: Complete canary row is accepted
- **WHEN** a canary row declares all required fields and references runnable evidence
- **THEN** the matrix accepts the row and includes it in the generated result JSON

#### Scenario: Missing recovery route is rejected
- **WHEN** a canary row omits the recovery route or protected invariant
- **THEN** the matrix rejects the row as incomplete confidence evidence

### Requirement: Canary runtime replay covers realistic isolated control failures
The system SHALL include executable tests for isolated lock, persistence, launcher/daemon, heartbeat/resume, peer-run authority, and terminal-fence failure scenarios without mutating live user state.

#### Scenario: File or task lock conflict routes to standard recovery
- **WHEN** a lock conflict or stale lock condition prevents ordinary continuation
- **THEN** the canary evidence proves the system waits, records a recoverable blocker, or retries through the legal recovery path without advancing stale work

#### Scenario: Half-written or corrupt artifact is not trusted
- **WHEN** a control-plane artifact is missing, half-written, or cannot be decoded
- **THEN** the canary evidence proves the system blocks or rehydrates before continuation rather than treating the artifact as proof

#### Scenario: Dead launcher or daemon enters resume recovery
- **WHEN** launcher or daemon liveness is stale or dead
- **THEN** the canary evidence proves the system enters liveness recovery, restart, or control-blocker handling before normal work resumes

#### Scenario: Duplicate heartbeat does not double-advance work
- **WHEN** two heartbeat or resume attempts target the same current run state
- **THEN** the canary evidence proves the duplicate wakeup is idempotent and does not create duplicate completion, duplicate blocker, or cross-run authority

#### Scenario: Peer-run stop does not mutate current run
- **WHEN** a stop, stale authority, or terminal fence targets a peer run
- **THEN** the canary evidence proves the current run remains protected and only the addressed run changes state

### Requirement: Canary validation is part of routine confidence
The system SHALL register the canary matrix and runtime replay tests in the fast tier and model-test alignment evidence so future changes cannot silently drop control-plane failure coverage.

#### Scenario: Fast tier includes canary commands
- **WHEN** the fast test tier is inspected
- **THEN** it includes the control-plane failure matrix and runtime canary replay tests

#### Scenario: Model-test alignment exposes canary obligations
- **WHEN** model-test alignment checks are generated
- **THEN** control-plane canary evidence appears under the owning FlowPilot model family with current passing evidence

### Requirement: Canary confidence remains scoped
The system SHALL report that the canary proves modeled control-plane recovery paths only, and SHALL NOT claim proof for every operating-system, hardware, antivirus, scheduler, or future unknown failure.

#### Scenario: Result JSON includes confidence boundary
- **WHEN** the canary matrix result JSON is generated
- **THEN** it states the supported confidence boundary and the excluded unmodeled failure classes
