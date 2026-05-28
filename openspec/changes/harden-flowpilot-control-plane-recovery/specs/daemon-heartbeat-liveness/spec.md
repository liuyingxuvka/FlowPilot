## ADDED Requirements

### Requirement: Heartbeat status exposes attach, standby, terminal, and protocol boundaries
FlowPilot SHALL use heartbeat/manual resume only as an attach or recovery
launcher while daemon and Controller status expose the real work boundary.

#### Scenario: Heartbeat does not prove live work chain
- **WHEN** heartbeat records a wake request
- **THEN** status MUST NOT classify the work chain as alive from old route
  state, old role ids, or wait-agent timeout
- **AND** status MUST identify heartbeat evidence as diagnostic unless the
  current daemon/action ledger proves a live boundary.

#### Scenario: Terminal or protocol-dead-end suppresses reentry loop
- **WHEN** run lifecycle is terminal, stopped by user, or protocol-dead-end
- **THEN** heartbeat/manual resume MUST expose that terminal boundary
- **AND** it MUST NOT reenter the failed resume or blocker family.

#### Scenario: Daemon alive after stale heartbeat attaches
- **WHEN** heartbeat age is stale but process and lock evidence show a live
  current-run daemon
- **THEN** Controller MUST attach to the existing daemon
- **AND** it MUST NOT start a second Router writer.
