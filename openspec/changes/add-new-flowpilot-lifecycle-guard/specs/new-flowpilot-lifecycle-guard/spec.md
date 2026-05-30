## ADDED Requirements

### Requirement: New runtime exposes lifecycle guard snapshots
The new FlowPilot runtime SHALL persist a metadata-only lifecycle guard
snapshot for the current run whenever startup, status, patrol, resume, packet
assignment, ACK, result submission, or closure changes the legal next action.

#### Scenario: Nonterminal status names guard action
- **WHEN** the new runtime has an unfinished current run
- **THEN** the public status MUST include a lifecycle guard snapshot with
  `controller_stop_allowed` false
- **AND** the snapshot MUST name the next guard action without exposing sealed
  packet bodies or sealed result bodies.

#### Scenario: Terminal status allows final return
- **WHEN** the new runtime has completed final closure and the router action is
  `terminal_complete`
- **THEN** the lifecycle guard snapshot MUST set `controller_stop_allowed` true
- **AND** the guard decision MUST be `terminal_return`.

### Requirement: Nonterminal Controller stop is blocked
The new FlowPilot runtime SHALL reject a final foreground stop claim unless the
current lifecycle guard snapshot allows Controller stop.

#### Scenario: Next action is not terminal
- **WHEN** the current router action is `lease_agent`, `wait_for_ack`,
  `wait_for_result`, `issue_node_task_packet`, `close_project`, or any other
  nonterminal action
- **THEN** the lifecycle guard MUST keep `controller_stop_allowed` false
- **AND** a completion claim based only on knowing the next action MUST NOT be
  accepted as terminal completion.

### Requirement: Resume rehydrates current-run authority
Manual resume and heartbeat resume SHALL load the current run shell, ledger,
packet ledger, leases, event count, and next action before deciding whether to
continue, wait, recover, or return terminal completion.

#### Scenario: Manual resume from waiting state
- **WHEN** a manual resume is requested while a packet is waiting for ACK or
  result
- **THEN** the runtime MUST record a resume guard snapshot tied to the current
  run id and event count
- **AND** the decision MUST be derived from ledger state rather than chat
  history.

### Requirement: Wait patrol classifies liveness and recovery boundaries
The lifecycle guard SHALL classify packet waits into live wait, overdue ACK,
overdue result, inactive lease, stale result, repeated unchanged action, or
control-plane stuck before any recovery can be claimed.

#### Scenario: ACK wait stays nonterminal
- **WHEN** an assigned packet has an active lease without ACK
- **THEN** the lifecycle guard MUST return a nonterminal `wait_for_ack` or
  overdue-ACK recovery decision
- **AND** the run MUST NOT advance to terminal completion.

#### Scenario: Result wait stays nonterminal
- **WHEN** an acknowledged packet has no current result
- **THEN** the lifecycle guard MUST return a nonterminal `wait_for_result` or
  overdue-result recovery decision
- **AND** ACK-only liveness MUST NOT satisfy the packet result obligation.

#### Scenario: Inactive lease requests recovery
- **WHEN** a packet is assigned to a lease that is closed, expired, superseded,
  or missing
- **THEN** the lifecycle guard MUST classify the state as lease replacement or
  recovery instead of waiting forever.

#### Scenario: Repeated action exposes stuck control plane
- **WHEN** the same nonterminal next action repeats beyond the configured guard
  threshold without a new ledger event
- **THEN** the lifecycle guard MUST classify the condition as
  `control_plane_stuck`
- **AND** the snapshot MUST preserve the repeated action key.

### Requirement: Stale or late results are quarantined
The new runtime SHALL NOT accept a result as current when its packet, lease,
route version, source generation, or event ordering no longer matches current
run authority.

#### Scenario: Late result after route mutation
- **WHEN** a result arrives for a packet that was quarantined or superseded by a
  route mutation
- **THEN** the runtime MUST reject or quarantine that result
- **AND** the lifecycle guard MUST keep the run nonterminal until a current
  packet has current evidence.

#### Scenario: Result from inactive lease
- **WHEN** a result is submitted from a lease that is no longer active for the
  packet
- **THEN** the runtime MUST reject the result as stale or inactive-lease output
- **AND** it MUST NOT close the packet from that result.

### Requirement: Lifecycle guard does not restore retired surfaces
The lifecycle guard SHALL work without requiring the old monitor UI, old Router
authority, old side commands, or a fixed six-person topology.

#### Scenario: New runtime guard runs through public new entrypoint
- **WHEN** a fake or live run invokes the new runtime status, patrol, or resume
  command
- **THEN** the command MUST use the current-run ledger and dynamic lease state
- **AND** it MUST NOT require a non-startup monitor UI or old router state as
  authority.
