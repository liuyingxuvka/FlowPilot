## ADDED Requirements

### Requirement: Resume rehydration postcondition is replayable from current-run evidence
FlowPilot SHALL replay valid current-run rehydration receipts and requested
responsibility rehydration reports into the existing `resume_roles_restored` postcondition
before materializing a control blocker for missing resume role restoration.

#### Scenario: Valid requested-responsibility report satisfies postcondition
- **WHEN** Router evaluates resume after heartbeat or manual wake
- **AND** a current-run responsibility rehydration report shows every currently
  required requested responsibility ready
- **AND** the report does not rely on timeout as active liveness proof
- **THEN** Router MUST set or preserve `resume_roles_restored=true`
- **AND** Router MUST NOT create a control blocker solely for the already
  satisfied rehydration action.

#### Scenario: Valid Controller receipt replays through Router-owned handler
- **WHEN** Controller has a done receipt for `rehydrate_role_agents`
- **AND** the matching current-run report satisfies the standard role evidence
- **THEN** Router MUST replay or fold that receipt through the existing
  Router-owned resume rehydration handler before evaluating PM resume work.

#### Scenario: Incomplete report still blocks
- **WHEN** the current-run rehydration evidence is missing a currently required
  responsibility, stale,
  ambiguous, or treats timeout as active liveness
- **THEN** Router MUST NOT set `resume_roles_restored`
- **AND** Router MUST surface a bounded blocker or PM escalation through the
  existing resume recovery lane.
