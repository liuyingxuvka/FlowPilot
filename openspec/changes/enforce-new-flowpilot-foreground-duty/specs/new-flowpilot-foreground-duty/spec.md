## ADDED Requirements

### Requirement: New runtime exposes foreground duty
The new FlowPilot runtime SHALL expose a metadata-only `foreground_duty` for
the current run whenever startup, status, patrol, resume, packet assignment,
ACK, result submission, scoped closure, or terminal closure changes the legal
foreground behavior.

#### Scenario: Nonterminal run returns executable duty
- **WHEN** the current run is not terminal
- **THEN** the runtime MUST return a `foreground_duty` whose action is
  `process_next_action`, `wait_patrol`, `recover_or_reissue`, or
  `control_plane_blocker`
- **AND** it MUST report final foreground return as disallowed.

#### Scenario: Terminal run returns terminal duty
- **WHEN** final closure evidence is current and the lifecycle guard decision
  is `terminal_return`
- **THEN** the runtime MUST return a `foreground_duty` action of
  `terminal_return`
- **AND** it MUST report final foreground return as allowed.

### Requirement: Passive waiting becomes timed patrol duty
The new FlowPilot runtime SHALL turn every legal nonterminal wait into an
explicit timed patrol duty instead of returning a passive or empty wait.

#### Scenario: ACK wait becomes patrol duty
- **WHEN** a packet has an active lease and no ACK
- **THEN** the foreground duty MUST be `wait_patrol` or a recovery duty
- **AND** the duty MUST name the packet, wait reason, delay seconds, refresh
  command, and final-return preflight.

#### Scenario: Result wait becomes patrol duty
- **WHEN** a packet has an acknowledged active lease and no current result
- **THEN** the foreground duty MUST be `wait_patrol` or a recovery duty
- **AND** ACK-only liveness MUST NOT allow final return.

### Requirement: Final return requires hard preflight
The new FlowPilot runtime SHALL reject final answer, done claim, or Controller
shutdown unless the final-return preflight passes from current ledger state.

#### Scenario: Open next packet blocks final return
- **WHEN** a scoped closure has completed and a later packet is open
- **THEN** final-return preflight MUST fail
- **AND** the foreground duty MUST name the later packet as the next work or
  wait subject.

#### Scenario: Repeated nonterminal action blocks final return
- **WHEN** the lifecycle guard reports a repeated nonterminal action or
  `control_plane_stuck`
- **THEN** final-return preflight MUST fail
- **AND** the foreground duty MUST require recovery or blocker handling instead
  of terminal return.

#### Scenario: Terminal guard permits final return
- **WHEN** the lifecycle guard reports `controller_stop_allowed=true` and
  `decision=terminal_return`
- **THEN** final-return preflight MAY pass
- **AND** no nonterminal foreground duty may remain active.

### Requirement: Scoped closure re-enters duty derivation
The new FlowPilot runtime SHALL treat packet, phase, or stage closure as
scoped closure unless route-wide final closure evidence is present.

#### Scenario: Packet closure continues to discovery packet
- **WHEN** a closure officer accepts a packet-level closure and the router
  opens or exposes a discovery packet
- **THEN** the next foreground duty MUST process or wait on the discovery
  packet
- **AND** the Controller MUST NOT treat the closure officer result as project
  completion.

### Requirement: Foreground duty remains new-runtime only
The new FlowPilot foreground duty SHALL derive authority from the new runtime
ledger, lifecycle guard, dynamic leases, and router next action, without
requiring old Router daemon status, old Controller action ledger, or a
non-startup monitor UI.

#### Scenario: New runtime without legacy monitor still blocks stop
- **WHEN** a new runtime run has no `runtime/router_daemon_status.json` and no
  `runtime/controller_action_ledger.json`
- **THEN** foreground duty MUST still block final return for nonterminal state
- **AND** it MUST use the new ledger and lifecycle guard as authority.

### Requirement: Terminology separates display from authority
The new FlowPilot runtime and skill prompt SHALL distinguish status display,
startup display, lifecycle guard, foreground duty, and legacy monitor
authority.

#### Scenario: Status projection cannot authorize stop
- **WHEN** a public status projection says a scoped task is accepted or closed
- **THEN** the projection MUST NOT authorize final foreground return
- **AND** final return MUST still depend on the current foreground duty
  preflight.

#### Scenario: Legacy monitor wording is not new runtime authority
- **WHEN** the formal new runtime path is described to the foreground
  Controller
- **THEN** old Router daemon, old monitor UI, old kanban, and fixed-team
  wording MUST NOT be presented as required new-runtime authority.
