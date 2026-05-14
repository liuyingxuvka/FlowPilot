## Context

FlowPilot now has a persistent Router daemon and a Controller action ledger.
The daemon loads the current run state, reconciles some file-backed evidence,
computes a next action, and writes daemon status. Controller executes host
actions and writes receipts. Roles submit reports and decisions through
file-backed runtime envelopes or mailbox files.

The second-layer gap is that these evidence paths were not all part of one
pre-compute barrier. A receipt could update only `controller_actions/*.json`
while `router_state.json.pending_action` still pointed at the completed action.
A role-output runtime submission could land in `role_output_ledger.json` and
canonical startup files while `router_state.json.flags` still said the event
was absent. On the next tick, Router returned stale pending work before it
looked at those durable facts.

## Goals

- Make durable evidence reconciliation happen before every next-action decision
  in daemon and manual next flows.
- Keep the fix narrow: use existing Router state, receipt, role-output, scoped
  event, and control-blocker mechanisms.
- Prevent repeated stale Controller actions after a `done` or `blocked`
  receipt.
- Accept already-submitted role-output runtime envelopes exactly once when they
  are valid and correspond to supported Router events.
- Turn incomplete stateful Controller receipts into an explicit repair blocker,
  not silent success.

## Non-Goals

- No replacement of the Controller foreground standby loop.
- No new role authority or Controller permission to read sealed bodies.
- No broad rewrite of every external event writer.
- No remote publish or release.

## Design

### Durable Reconciliation Barrier

Router performs a small barrier before it returns an existing pending action or
computes a new action:

1. Reconcile Controller receipt files into action ledger entries.
2. If the active pending action has a receipt:
   - `blocked` clears the pending action and creates a control blocker.
   - `done` clears stateless or already-applied actions.
   - `done` for a stateful action applies the required Router postcondition
     only when the receipt payload is complete enough.
   - incomplete stateful receipts clear the stale action and create a control
     blocker for PM/Controller repair.
3. Reconcile supported direct role-output ledger entries into canonical Router
   events before considering stale waits or role recovery actions.
4. If any durable evidence changed Router state, refresh derived views and save
   before computing the next action.

### Stateful Controller Receipt Boundary

Some Controller actions are not merely "I displayed or relayed this." For
`rehydrate_role_agents`, Router must write crew rehydration artifacts and set
resume/role recovery flags. A metadata-only receipt is therefore not enough to
mark Router postconditions complete.

The barrier accepts a complete rehydration payload through the existing
`_write_resume_role_rehydration_report` path. If the receipt is only a count or
summary, Router records a control blocker and stops repeating the stale
rehydration action.

### Direct Role-Output Reconciliation

The minimal supported role-output reconciliation starts with
`reviewer_reports_startup_facts`, because that is the live bug. Router reads
`role_output_ledger.json`, validates the role-output runtime receipt, loads the
body through the existing envelope-only loader, and either:

- writes the canonical startup fact report through the existing writer, or
- if the canonical artifact already exists, records the Router event/flag from
  the validated envelope metadata.

This path uses scoped event identity to remain idempotent.

### FlowGuard Coverage

The reconciliation model treats Controller receipts, role-output ledgers,
canonical artifacts, Router flags/events, pending actions, and stale daemon
snapshots as separate state. It fails known-bad states where:

- next action is computed before the reconciliation barrier;
- a completed Controller action is returned again;
- an incomplete stateful receipt is silently treated as success;
- a role-output ledger submission is left unconsumed;
- a canonical artifact exists while the Router flag remains false;
- a stale daemon snapshot overwrites newer durable evidence.

## Risks

- The first implementation only reconciles the startup fact role-output event
  from the role-output ledger. Other role-output event families still rely on
  the normal event entrypoint and existing packet/result reconciliation paths.
- Incomplete stateful receipts may now become visible blockers in runs that
  previously looped silently. That is intended: repeated stale work is worse
  than an explicit repair card.
