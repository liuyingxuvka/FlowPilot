## Why

The `run-20260527-212331` audit exposed a real FlowPilot control-plane miss:
roles were rehydrated and PM wrote repeated repair decisions, but Router did
not durably consume the decisive evidence, so the same blocker family repeated
hundreds of times and heartbeat became the visible continuation mechanism.

This change hardens the existing FlowPilot workflow rather than introducing a
parallel control system. The repair must make the current Router, Controller
action ledger, role-output runtime, control-blocker policy, break-glass lane,
daemon heartbeat, and known-friction gates converge on one durable state.

## What Changes

- Fixed-router-event role outputs must be either submitted through Router or
  rejected with an explicit local-only status; a local receipt alone must never
  look like a consumed Router decision.
- Resume role rehydration receipts and reports must be replayable into the
  existing `resume_roles_restored` postcondition without generating duplicate
  blockers when all six roles are ready.
- Control blockers must coalesce by existing attempt family; repeated failures
  for the same family must update or preserve the active family state instead
  of creating unbounded replacement blockers.
- PM `terminal_stop` and `protocol_dead_end` repair decisions must close the
  active blocker through the existing repair transaction and lifecycle path,
  and later heartbeat/manual resume must not reopen the same failed family.
- Controller break-glass incidents must leave the current diagnostic-only
  limbo: an opened incident must either create a recovery transaction, close
  with validation/disposition, or explicitly block for human/protocol repair.
- Heartbeat/manual resume must stay a recovery launcher, not a proof of a live
  work chain; daemon/controller status must expose the real attach, standby,
  terminal, blocked, or protocol-dead-end boundary.
- Status projections must distinguish local receipt, Router event recording,
  state mutation, postcondition satisfaction, blocker closure, terminal
  lifecycle writing, and current validation evidence.
- The historical failure from `run-20260527-212331` must become a regression
  fixture in the existing known-friction and FlowGuard model/test gates.
- Every feasible FlowPilot production path that can write critical runtime
  state must be connected to a FlowGuard runtime gateway. A partial dangerous
  subset is not enough; new direct writes must either be routed through an
  approved gateway or fail the static inventory and FlowGuard adoption check.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `role-output-transaction-boundaries`: require fixed-router-event formal
  outputs to reach Router or fail as local-only.
- `resume-rehydration-obligation-replay`: require rehydration report/receipt
  replay to satisfy `resume_roles_restored` idempotently.
- `blocker-repair-policy`: require same-family blocker coalescing and durable
  terminal/protocol-dead-end outcomes.
- `controller-break-glass-repair`: require recovery transaction, closure, or
  explicit blocked disposition for opened incidents.
- `daemon-heartbeat-liveness`: preserve heartbeat as attach/recover launcher
  while exposing the true standby/terminal/protocol-dead-end status.
- `known-friction-regression-gates`: add a live-run replay family for local
  receipt without Router event, rehydration postcondition replay, repeated
  blocker generation, protocol dead-end non-consumption, and break-glass limbo.
- `runtime-gateway-adoption`: require all critical production writer paths to
  be inventoried, gateway-owned, and checked with FlowGuard runtime gateway
  adoption evidence.

## Impact

- Affected runtime modules include `role_output_runtime*`,
  `flowpilot_runtime_role_output_commands.py`, Router resume/recovery helpers,
  Router control-blocker repair helpers, Router lifecycle/status projection,
  daemon heartbeat/status helpers, and Controller break-glass helpers.
- Affected prompt/cards include PM control-blocker repair guidance, role-output
  catalog guidance, Controller heartbeat/resume guidance, Controller action
  ledger/standby guidance, and Controller break-glass repair guidance.
- Affected evidence includes FlowGuard model checks, known-friction regression
  rows, router runtime tests, runtime gateway static inventory checks, install
  checks, local install sync, and maintenance/adoption logs.
