## Context

`unify-blocker-repair-policy` made blocker handling explicit: a policy row
decides the first handler, retry budget, PM escalation, allowed recovery
options, return policy, and hard stops. The missing layer is consumption of a
PM repair decision after escalation. The current Router can record a PM
decision, commit a repair transaction, and wait for a success event even when
no Router handler, Controller task, role reissue, or existing producer can
create that event.

The live failure mode is a PM decision that is understandable to a human but
not executable by Router. The Router must reject that decision before commit or
turn it into a concrete queued action.

## Goals / Non-Goals

**Goals:**

- Make `repair_transaction.plan_kind` the Router execution selector.
- Keep `recovery_option` and `repair_action` as policy/explanation metadata.
- Validate each plan kind through plan-specific required fields and producer
  checks.
- Queue a concrete action or mark a real terminal state before committing a
  repair transaction.
- Give PM clear plan-kind selection guidance.
- Give Controller a bounded repair work packet path for fixes that need AI
  repair within strict authority limits.
- Preserve existing `packet_reissue` behavior and concurrent mail receipt
  folding work.

**Non-Goals:**

- Replacing the blocker repair policy table.
- Allowing Controller to approve gates, mutate routes, read sealed bodies, or
  act as PM.
- Running heavyweight Meta and Capability regressions in this pass.
- Broadly rewriting reviewer, startup, or material repair flows.

## Decisions

### Plan kind is executable authority

Router SHALL branch on `repair_transaction.plan_kind`, not on
`recovery_option`. `recovery_option` remains useful because it says why the
policy allows the path, but it cannot by itself tell Router what to do.

### Use explicit executable plan kinds

Supported plan kinds are:

- `operation_replay`: replay a recorded, safely replayable Router or Controller
  operation.
- `controller_repair_work_packet`: create a bounded Controller repair work
  packet with allowed reads/writes and success evidence.
- `packet_reissue`: atomically generate/register/dispatch replacement packets.
- `role_reissue`: ask the original role to resubmit a bounded output.
- `router_internal_reconcile`: run a named Router reconciliation handler.
- `await_existing_event`: wait only when a current producer already exists for
  the awaited event.
- `route_mutation`: apply or stage a route/node/acceptance change through the
  existing route mutation path.
- `terminal_stop`: record user stop, protocol dead end, or human escalation.

Legacy `event_replay` is not a new execution path. It may be accepted only as a
deprecated alias for `await_existing_event` when the decision identifies an
already-existing producer for the awaited event. Otherwise it is rejected before
commit.

### Commit requires a next executable step

Before writing a committed repair transaction, Router validates one of these is
true:

- a concrete action has been queued;
- an existing pending producer for the awaited event has been found;
- a Router handler exists and has recorded its reconciliation result;
- a terminal stop has been recorded.

If none is true, Router returns a PM repair-decision error and leaves the old
blocker active.

### Controller repair packets are bounded

`controller_repair_work_packet` is for limited repair work that the PM cannot
perform directly but Controller can reason through as an AI. The packet must
include allowed reads, allowed writes, forbidden actions, success evidence, and
blocker output rules. Controller cannot use this path to approve gates, mutate
routes, inspect sealed bodies, or replace PM/reviewer/worker judgment.

## Risks / Trade-offs

- [Risk] Existing tests and PM cards still emit `event_replay` ->
  [Mitigation] Support a strict legacy alias only when a real existing producer
  is named, and update cards/tests to the new names.
- [Risk] Plan-kind validation becomes too broad in one pass -> [Mitigation]
  Implement focused executable checks first, with unsupported or incomplete
  plan-specific requests rejected before commit.
- [Risk] Conflicts with parallel mail-delivery receipt work -> [Mitigation]
  Preserve its helper functions and tests; this change only decides what PM
  repair transactions can commit after blocker escalation.
- [Risk] Long regressions block iteration -> [Mitigation] Run focused tests and
  repair-transaction FlowGuard checks; skip Meta/Capability checks by explicit
  user instruction.

## Migration Plan

1. Update OpenSpec and FlowGuard repair-transaction coverage.
2. Add Router plan-kind constants and validators.
3. Wire PM decision handling so commit requires an executable plan result.
4. Update role/phase cards and role-output contract choices.
5. Add focused runtime tests for dead-wait rejection and executable repair
   actions.
6. Run focused checks, sync the installed local FlowPilot skill, and inspect
   git state including parallel-agent changes.
