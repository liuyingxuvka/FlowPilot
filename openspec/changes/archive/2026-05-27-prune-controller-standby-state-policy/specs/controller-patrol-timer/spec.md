## ADDED Requirements

### Requirement: Patrol timer remains downstream of standby policy

The Controller patrol timer SHALL derive its user-facing result from the
foreground standby state and stop-preflight policy, without creating a second
progress or stop authority.

#### Scenario: Patrol result follows standby state

- **WHEN** standby returns pending Controller work, terminal return, daemon
  liveness check, live daemon watching, or another nonterminal duty
- **THEN** patrol timer returns the corresponding Controller instruction and
  preserves final-answer preflight.

#### Scenario: Patrol timer does not override stop authority

- **WHEN** standby final-answer preflight is false
- **THEN** patrol timer also reports final-answer disallowed unless the result
  is terminal return with `controller_stop_allowed=true`.
