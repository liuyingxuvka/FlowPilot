## MODIFIED Requirements

### Requirement: Resume rehydration SHALL run Router obligation replay before default PM resume

Router SHALL run metadata-only obligation replay before delivering a PM resume
decision card after current manual resume restores or replaces current
runtime-required role bindings, unless current-run memory or resume state is
missing.

#### Scenario: Manual resume replays mechanical obligations

- **WHEN** `manual_resume_requested` has been recorded
- **AND** `load_resume_state` has loaded current-run state and daemon evidence
- **AND** `rehydrate_role_bindings` reports that the runtime-required role
  bindings are ready with current-run memory, common context, and current
  liveness preflight
- **THEN** Router scans current-run outstanding waits for the restored roles before delivering `pm.resume_decision`

#### Scenario: Current resume has one replay path

- **WHEN** a manual resume wake follows the same state load and
  runtime-required role-binding rehydration path
- **THEN** Router uses the same obligation replay rules for current resume
  recovery
- **AND** Router MUST NOT use heartbeat events or historical role evidence to
  satisfy resume replay.

### Requirement: Current replay packages cover host role lifecycle recovery
The system SHALL include host/role lifecycle replay packages that require
current runtime-required role liveness, memory, prompt, and PM resume-context
evidence before normal work resumes.

#### Scenario: Partial role rehydration blocks normal work
- **WHEN** a replay package omits a runtime-required role, reports stale memory,
  treats unknown liveness as active, or rehydrates before resume state is
  loaded
- **THEN** the Router rejects the package or keeps a recoverable control
  blocker until the required rehydration evidence is present
