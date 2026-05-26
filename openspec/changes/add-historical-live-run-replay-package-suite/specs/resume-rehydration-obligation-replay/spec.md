## ADDED Requirements

### Requirement: Historical replay packages cover host role lifecycle recovery
The system SHALL include host/role lifecycle replay packages that require full
six-role liveness, memory, prompt, and PM resume-context evidence before normal
work resumes.

#### Scenario: Partial role rehydration blocks normal work
- **WHEN** a replay package omits a role, reports stale memory, treats unknown
  liveness as active, or rehydrates before resume state is loaded
- **THEN** the Router rejects the package or keeps a recoverable control
  blocker until the standard rehydration evidence is present
