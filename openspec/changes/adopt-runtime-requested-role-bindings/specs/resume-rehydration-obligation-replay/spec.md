## MODIFIED Requirements

### Requirement: Resume rehydration SHALL run Router obligation replay before default PM resume

Router SHALL run metadata-only obligation replay before delivering a PM resume
decision card after heartbeat or manual resume restores or replaces current
runtime-required role bindings, unless current-run memory or resume state is
missing.

#### Scenario: Heartbeat resume replays mechanical obligations

- **WHEN** `heartbeat_or_manual_resume_requested` has been recorded
- **AND** `load_resume_state` has loaded current-run state and daemon evidence
- **AND** `rehydrate_role_agents` reports that the runtime-required role
  bindings are ready with current-run memory or common context
- **THEN** Router scans current-run outstanding waits for the restored roles before delivering `pm.resume_decision`

#### Scenario: Manual resume shares the same replay path

- **WHEN** a manual resume wake follows the same state load and
  runtime-required role-binding rehydration path
- **THEN** Router uses the same obligation replay rules as heartbeat resume

### Requirement: Historical replay packages cover host role lifecycle recovery
The system SHALL include host/role lifecycle replay packages that require
current runtime-required role liveness, memory, prompt, and PM resume-context
evidence before normal work resumes.

#### Scenario: Partial role rehydration blocks normal work
- **WHEN** a replay package omits a runtime-required role, reports stale memory,
  treats unknown liveness as active, or rehydrates before resume state is
  loaded
- **THEN** the Router rejects the package or keeps a recoverable control
  blocker until the required rehydration evidence is present
