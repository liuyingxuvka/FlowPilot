## Context

The audited run `run-20260527-212331` showed a control-plane convergence
failure across existing FlowPilot surfaces:

- Controller rehydrated all six roles, but Router did not durably replay the
  receipt/report into `resume_roles_restored`.
- PM wrote many `pm_control_blocker_repair_decision` bodies, but they were
  submitted through the local `submit-output` path, so Router received no
  durable decision event for most of them.
- The same `rehydrate_role_agents` control-blocker attempt family was
  regenerated hundreds of times instead of coalescing.
- PM selected `protocol_dead_end`, but the current lifecycle did not stop the
  repeated blocker family.
- Break-glass recorded an incident and patches but left no recovery
  transaction, validation closure, or blocked disposition.
- Heartbeat exposed repeated wakeups, but it is a launcher and diagnostic
  surface, not a durable Controller worker.

The fix must stay inside the existing FlowPilot workflow. The change will not
introduce a parallel scheduler, a second Router writer, or a new recovery
framework. It hardens the existing Router, Controller action ledger,
role-output runtime, control-blocker policy, break-glass repair lane, daemon
status, prompts, and regression gates.

## Goals / Non-Goals

**Goals:**

- Make fixed-router-event role outputs impossible to mistake for Router
  consumption when they only wrote local receipts.
- Make resume rehydration postconditions replayable and idempotent from
  existing Controller receipts and crew rehydration reports.
- Coalesce repeated control blockers by attempt family and preserve terminal
  family disposition.
- Make PM `terminal_stop` and `protocol_dead_end` decisions close the active
  blocker through existing repair transaction and lifecycle state.
- Require break-glass incidents to produce a recovery transaction, closure, or
  explicit blocked disposition.
- Keep heartbeat/manual resume as the existing attach/recover launcher while
  daemon/status projections show the real work boundary.
- Add historical-live-run regression evidence for the audited failure class.
- Sync the installed local FlowPilot skill after code, prompt, and contract
  changes pass validation.

**Non-Goals:**

- Do not add a new top-level FlowPilot workflow or a second control plane.
- Do not make Controller approve gates, read sealed bodies, mutate routes, or
  do target-project work during break-glass.
- Do not treat heartbeat as proof that role work is alive.
- Do not weaken existing hard gates or remove current FlowGuard obligations.
- Do not revert unrelated peer-agent changes in the working tree.

## Decisions

### Decision 1: Fixed-router-event outputs must be Router-directed

The existing role-output runtime already distinguishes local output submission
from direct Router submission. The hardening will enforce that distinction:

- `submit-output` remains available for local receipt writing only when the
  output contract does not require a fixed Router event.
- Output types whose contract has a fixed `router_event` must either use
  `submit-output-to-router` or receive a mechanical runtime error.
- Status packets must expose separate local and Router milestones instead of
  one ambiguous `submitted` state.

Alternative considered: have Router periodically scan all role-output receipts
and infer missing events. This is risky because it introduces a second event
source and could double-apply old outputs. The chosen route keeps the existing
Router-directed submission boundary and only adds a safety net where the
contract proves a fixed event is required.

### Decision 2: Resume rehydration replay owns postcondition repair

The existing resume rehydration report writer already sets
`resume_roles_restored`. The failure happened when Router could not replay or
trust the existing Controller receipt/report after wake. The hardening will add
an idempotent reconcile helper that checks current-run rehydration evidence
before materializing a control blocker.

The helper will accept only current-run evidence with all six roles ready and
memory status available or otherwise explicitly accepted by the existing resume
rules. It will not infer liveness from old crew state or wait-agent timeout.

### Decision 3: Control blockers coalesce by attempt family

The existing blocker writer computes an `attempt_key`, but it always creates a
new artifact. The hardening will preserve the existing artifact and policy
model while adding family-state checks before new materialization:

- active same-family blocker: return or refresh the existing blocker;
- PM decision pending for same family: keep waiting for the current PM lane;
- terminal/protocol-dead-end same family: return the terminal family state;
- exhausted same family without PM decision: deliver the one existing PM lane.

This avoids unbounded replacement files while keeping existing policy rows,
sealed repair packets, direct retry budgets, and PM escalation semantics.

### Decision 4: Protocol dead-end is a terminal repair outcome, not text

Existing repair decision handling can write repair transactions and has
terminal-stop handling. The hardening will make `protocol_dead_end` produce a
durable terminal lifecycle record for the blocker family and prevent subsequent
heartbeat/manual resume from reopening the same failed action family.

The lifecycle record will identify the active blocker, PM decision body/ref,
repair transaction, originating Controller action, originating Router row, and
terminal reason. Status projection will use that record instead of falling
back to generic resume work.

### Decision 5: Break-glass must close or block through the existing lane

Break-glass already has helpers for incidents, patches, and recovery
transactions. The hardening will require an incident to reach one of the
existing durable dispositions:

- closed after validated diagnostic-only disposition;
- closed after recovery transaction;
- quarantined or weak-evidence with validation boundary;
- blocked for human/protocol repair.

An open incident with only `not_run` validations and no recovery transaction
will become a model/test failure.

### Decision 6: Heartbeat remains attach/recover; daemon/status owns standby

Heartbeat and manual resume will continue to record
`heartbeat_or_manual_resume_requested`, inspect daemon lock/status/process,
and attach or restore the current-run daemon. They will not claim the work
chain is alive from old route state or old agent ids.

The visible standby boundary will come from existing daemon status and
Controller action ledger state:

- live daemon attached;
- waiting for role/event;
- standby with no legal action;
- terminal stopped;
- protocol dead-end;
- blocked for human/protocol repair.

### Decision 7: Status uses evidence milestones

Existing status packets and summaries will expose explicit milestones for
control-plane evidence:

- local receipt written;
- Router event recorded;
- Router state changed;
- postcondition satisfied;
- control blocker closed;
- terminal lifecycle written;
- validation current.

This prevents `done`, `passed`, or `submitted` from being overpromoted.

### Decision 8: The audited failure becomes a known-friction family

The regression suite will add a compact fixture derived from the audited
failure shape. It will not read sealed bodies. It will preserve public control
metadata, role-output receipts, status packets, and Router state fields needed
to reproduce the failure class.

The fixture will cover:

- local receipt without Router event;
- successful role rehydration without postcondition replay;
- repeated same-family blocker materialization;
- protocol-dead-end decision not consumed;
- break-glass incident left open without recovery transaction or closure;
- heartbeat treated only as diagnostic wakeup.

### Decision 9: Runtime gateway adoption is all-path, not top-N

FlowPilot critical state writes will be treated as a runtime contract, not a
best-effort coding convention. The implementation will maintain a declared set
of critical state surfaces and owning gateway IDs:

- Router JSON gateway for run state, current/index pointers, route/frontier,
  Controller action state, scheduler state, daemon state, lifecycle/closure,
  control blockers, repair transactions, and generic run-scoped JSON state.
- Packet runtime gateway for packet/result envelopes, packet bodies, packet
  ledgers, active-holder leases, sessions, progress, and packet events.
- Role-output gateway for local role-output receipts, ledgers, sessions,
  statuses, and output bodies.
- Card runtime gateway for card ledgers, card receipts, ACKs, and return event
  state.
- Break-glass gateway for incidents, patches, recovery transactions, body
  access grants, reinjections, and break-glass blocker ledgers.
- User-flow gateway for route-sign display evidence artifacts.

The check is intentionally stricter than "wire the dangerous few paths":

- all direct production write sites in `skills/flowpilot/assets` are scanned;
- critical direct writes must live inside an approved gateway module;
- approved gateway modules must call `assert_runtime_gateway_write` before the
  file write or append;
- the FlowGuard runtime-gateway adoption plan must include complete inventory
  evidence, gateway contracts, code-boundary IDs, step contract IDs, proof
  artifacts, and current writer observations for every critical surface;
- a declared legacy bypass is still a blocking finding, not a pass.

This creates the missing bottom-level step: future code can still add new
writers, but it cannot quietly bypass the gateway and keep green evidence.

## Risks / Trade-offs

- Fixed-router-event rejection may expose old callers that used local-only
  output submission. Mitigation: update prompts/cards and tests together with
  runtime behavior, and make the error message name the required command.
- Receipt replay can accidentally trust stale evidence. Mitigation: require
  current-run ids, current resume tick or compatible current-run report, all
  role keys, and no timeout-as-active shortcut.
- Blocker coalescing can hide a genuinely new error. Mitigation: coalesce by
  attempt family only when origin action, responsible role, policy row, and
  postcondition match; otherwise materialize a distinct blocker.
- Terminal lifecycle can stop useful recovery too early. Mitigation: only PM
  `terminal_stop` with allowed `protocol_dead_end` or `user_stop` recovery can
  write the terminal family disposition.
- Break-glass closure requirements can make development-mode repair stricter.
  Mitigation: allow explicit blocked dispositions when validation or permanent
  repair cannot be done in the current run.
- Heavy regression checks can be slow. Mitigation: run heavyweight Meta,
  Capability, and router tier checks through the existing background artifact
  contract and inspect completion artifacts before claiming pass.
- Static writer inventory can over-classify a diagnostic artifact as critical.
  Mitigation: keep explicit noncritical exceptions narrow and visible in the
  scanner while keeping runtime JSON/JSONL state strict by default.

## Migration Plan

1. Add OpenSpec deltas and task list for the existing capabilities.
2. Update FlowGuard model obligations and known-friction rows before code
   claims are made.
3. Harden role-output runtime and prompt/card guidance.
4. Harden resume rehydration postcondition replay.
5. Harden control-blocker family coalescing and terminal family lifecycle.
6. Harden break-glass recovery closure.
7. Harden daemon/status projections around heartbeat and terminal states.
8. Add regression and model-test alignment evidence.
9. Add the all-path runtime gateway inventory, runtime assertions, and
   FlowGuard adoption check before claiming full closure.
10. Run focused tests first, then background router/meta/capability checks.
11. Sync the installed local FlowPilot skill with the repo-owned version and
    run install audit/check commands.

Rollback is file-level: each change stays inside existing modules and
contracts. If a focused validation fails, revert only the failing patch slice
or keep the OpenSpec task unchecked while preserving unrelated peer changes.

## Open Questions

- Whether the fixed-router-event contract should auto-upgrade local
  `submit-output` calls into Router submissions in a compatibility mode, or
  fail hard immediately. The safer default is fail hard.
- Whether protocol-dead-end lifecycle should reuse the startup-specific flag
  name for compatibility or add a separate generic
  `control_blocker_protocol_dead_end_declared` flag. The safer default is add
  the specific generic flag while preserving existing startup behavior.
