## ADDED Requirements

### Requirement: Full-flow fake AI replays cover startup through terminal closure
The system SHALL provide executable fake AI replay scenarios that drive a FlowPilot run across startup, Router/daemon control, PM dispatch, worker result submission, PM review or repair, background proof, and terminal closure.

#### Scenario: Happy-path full-flow replay
- **WHEN** fake AI packages follow the legal Router/daemon protocol from startup through closure
- **THEN** the replay MUST reach a clean terminal state with daemon state stopped or released, no dirty PM ledger, and final proof accepted.

#### Scenario: Full-flow replay uses real runtime boundaries
- **WHEN** a full-flow replay advances a run
- **THEN** it MUST use existing Router, packet runtime, role-output runtime, background proof, and terminal ledger helpers rather than a separate fake control framework.

### Requirement: Combined fake AI errors recover through the legal route
The system SHALL include fake AI replay scenarios where more than one bad package is injected before recovery.

#### Scenario: Worker package error then repaired package
- **WHEN** a worker submits a bad package and later submits a repaired package through the legal active-holder path
- **THEN** the first package MUST be rejected without completion, the repaired package MUST be accepted, and the run MUST continue.

#### Scenario: PM repair error then corrected repair
- **WHEN** PM repair is attempted with missing, stale, or unauthorized evidence and then corrected
- **THEN** the bad repair MUST not advance the route and the corrected repair MUST move the run to the next legal wait.

#### Scenario: Terminal overclaim then clean closure
- **WHEN** terminal closure is attempted before required ledgers/proofs are clean and later retried after cleanup
- **THEN** the first closure MUST be rejected and the later closure MUST be accepted only after the protected ledgers and proof artifacts are clean.

### Requirement: Parallel fake AI runs remain isolated
The system SHALL include fake AI replay scenarios where multiple runs or agents operate concurrently or attempt cross-run actions.

#### Scenario: Peer run stop does not mutate current run
- **WHEN** one fake AI action stops or mutates a peer run
- **THEN** the current run focus, daemon lock, packet ledger, and terminal status MUST remain unchanged.

#### Scenario: Duplicate or stale package cannot steal current authority
- **WHEN** a stale package, duplicate package, or wrong active-holder package is submitted while another run or agent is active
- **THEN** only the matching active authority may advance and all nonmatching submissions MUST be rejected or quarantined.

### Requirement: Background progress is not terminal proof
The system SHALL reject fake AI completion claims that rely on progress-only background artifacts.

#### Scenario: Progress-only proof blocks full-flow closure
- **WHEN** a fake AI submits background logs without final stdout, stderr, combined output, exit code, and meta artifacts
- **THEN** the run MUST not count the proof as passed and terminal closure MUST remain blocked.

#### Scenario: Final background proof can unblock closure
- **WHEN** final background artifacts exist and pass the expected checks
- **THEN** the replay MAY advance through the proof gate and continue to terminal closure.
