## ADDED Requirements

### Requirement: User stop immediately fences daemon mode
FlowPilot SHALL make user-requested stop or cancel terminal before any further
daemon-owned nonterminal action can be produced.

#### Scenario: User requests run stop
- **WHEN** Router records `user_requests_run_stop`
- **THEN** Router MUST write terminal lifecycle state, terminal daemon status,
  and a terminal daemon lock/projection before returning from the stop request
- **AND** Router MUST cancel or supersede pending nonterminal Controller actions
  for the stopped run.

#### Scenario: Stop happens before terminal summary
- **WHEN** the terminal summary has not yet been written after a user stop
- **THEN** heartbeat/manual resume and Router daemon recovery MUST still treat
  the run as terminal
- **AND** they MUST NOT restart daemon mode, rehydrate roles, create heartbeat
  automations, or continue route work for that run.

### Requirement: Terminal cleanup preserves terminal actions only
FlowPilot SHALL separate terminal cleanup work from ordinary nonterminal work
when fencing a stopped run.

#### Scenario: Pending terminal cleanup action exists
- **WHEN** a run is terminal and a Router-authored terminal cleanup or terminal
  summary Controller action is pending
- **THEN** Controller MAY complete that terminal action
- **AND** Router MUST NOT expose unrelated startup, heartbeat, role, or route
  actions for the same run.
