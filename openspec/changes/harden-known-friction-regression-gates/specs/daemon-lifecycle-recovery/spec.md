## ADDED Requirements

### Requirement: Controlled stop reconciles all run-lifecycle authorities
FlowPilot SHALL treat a user stop as a single lifecycle boundary across
current-run pointers, daemon status, heartbeat/manual-resume evidence,
Controller actions, and role-agent continuation authority.

#### Scenario: User stops current run
- **WHEN** the user requests the current FlowPilot run to stop
- **THEN** FlowPilot MUST mark the run lifecycle as stopped or terminal, stop
  daemon active ticking, suppress heartbeat/manual resume restart, supersede or
  cancel nonterminal Controller actions, and prevent role-agent continuation
  for that run.

#### Scenario: Current pointer is stale after stop
- **WHEN** `.flowpilot/current.json` still points at a stopped run
- **THEN** the pointer status MUST be reconciled to a stopped or terminal state
  before any status report or resume path can treat the run as active.

#### Scenario: Resume after stop
- **WHEN** heartbeat/manual resume observes a stopped run
- **THEN** it MUST NOT restart the daemon, rehydrate roles, or continue route
  work unless the user starts a new formal FlowPilot run.
