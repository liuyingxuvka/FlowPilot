## MODIFIED Requirements

### Requirement: Resume rehydration postcondition is replayable from current-run evidence

FlowPilot SHALL replay valid current-run rehydration receipts and requested-responsibility reports into the existing `resume_roles_restored` postcondition before materializing a control blocker for missing resume role restoration.

#### Scenario: Valid requested-responsibility report satisfies postcondition
- **WHEN** the runtime evaluates resume after heartbeat or manual wake
- **AND** a current-run rehydration report shows every currently required requested responsibility is ready, replaced, or explicitly blocked
- **AND** the report does not rely on timeout as active liveness proof
- **THEN** the runtime MUST set or preserve `resume_roles_restored=true`
- **AND** it MUST NOT require an unconditional six-role report.

#### Scenario: Incomplete report still blocks
- **WHEN** the current-run rehydration evidence is missing a currently required requested responsibility, stale, ambiguous, or treats timeout as active liveness
- **THEN** the runtime MUST NOT set `resume_roles_restored`
- **AND** it MUST surface a bounded blocker or PM escalation through the existing resume recovery lane.
