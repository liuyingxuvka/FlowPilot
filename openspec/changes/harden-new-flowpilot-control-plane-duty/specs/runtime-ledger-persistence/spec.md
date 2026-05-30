## ADDED Requirements

### Requirement: New runtime status projection is read-only
New FlowPilot runtime status projection SHALL NOT mutate canonical lifecycle evidence when it is requested only for display.

#### Scenario: Status render preserves lifecycle histories
- **WHEN** a new runtime ledger is loaded and status projection is requested
- **THEN** the runtime MUST NOT append `lifecycle_guard_history`
- **AND** it MUST NOT append `foreground_duty_history`
- **AND** it MUST NOT write new lifecycle guard events.

#### Scenario: Stateful command persists refreshed duty
- **WHEN** a stateful command such as patrol, resume, lease-agent, ack, progress, submit-result, or repair-accepted-packet updates the ledger
- **THEN** the runtime MAY persist refreshed lifecycle guard and foreground duty snapshots
- **AND** the persisted trigger MUST name the stateful command.
