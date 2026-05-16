# router-ready-preemption Specification

## Purpose
TBD - created by archiving change preempt-controller-stale-role-waits. Update Purpose after archive.
## Requirements
### Requirement: Controller foreground waits are preempted by Router-ready evidence

The FlowPilot Controller SHALL check Router status, `next`, or
`run-until-wait` immediately after router-authored card, bundle, packet, or
result relay actions before waiting on a role chat response or subagent
foreground completion.

#### Scenario: Direct card ACK exists after relay
- **WHEN** Controller has relayed a router-authored system card and the expected direct Router ACK file exists or the return ledger is resolved
- **THEN** Controller MUST return to Router status/`next`/`run-until-wait` before any foreground role wait

#### Scenario: Active-holder result notice exists
- **WHEN** an active-holder packet result has written `controller_next_action_notice.json`
- **THEN** Controller MUST consume the router-authored next-action notice or call Router before waiting on the holder role

#### Scenario: Router pending action already exists
- **WHEN** Router state already contains a pending controller action
- **THEN** Controller MUST apply or inspect that router action rather than starting or continuing a role/subagent wait

### Requirement: Foreground liveness waits remain recovery-only

The FlowPilot Controller SHALL use bounded `wait_agent` checks only when Router
explicitly requests role liveness or recovery preflight, and a timeout result
MUST be recorded as `timeout_unknown` rather than active continuity.

#### Scenario: Ordinary role work is pending
- **WHEN** Router exposes `await_card_return_event` or `await_role_decision` for ordinary role output
- **THEN** Controller MUST record the controlled wait and stop or resume through heartbeat/manual continuation instead of waiting in the foreground for an arbitrary role response

#### Scenario: Router requests liveness preflight
- **WHEN** Router returns a role-rehydration or role-recovery action requiring host liveness checks
- **THEN** Controller MAY perform the bounded liveness wait and MUST classify timeout as `timeout_unknown`

### Requirement: Router-ready preemption preserves authority boundaries

Router-ready preemption SHALL NOT allow Controller to read sealed packet,
result, report, or decision bodies, and SHALL NOT allow Controller to approve
PM, reviewer, officer, route, or completion gates.

#### Scenario: Next action is available after result return
- **WHEN** Router-ready evidence indicates a worker result can be relayed to PM
- **THEN** Controller MUST relay only router-authorized envelope metadata and MUST NOT inspect the result body or mark the node complete

#### Scenario: Safe internal folding reaches a real boundary
- **WHEN** `run-until-wait` encounters a user, host, role, payload, card, packet, ledger, or final-replay boundary
- **THEN** it MUST stop and return that boundary action rather than applying a semantic decision
