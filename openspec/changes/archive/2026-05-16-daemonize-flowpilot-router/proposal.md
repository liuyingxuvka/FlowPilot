## Why

FlowPilot currently depends on the foreground Controller repeatedly calling the
Router after cards, bundles, packets, ACKs, reports, and result envelopes. A
live run showed the weak point: PM wrote the expected bundle ACK, but Router did
not advance because no active Controller turn called Router again.

This change makes Router a persistent per-run scheduler and makes Controller a
persistent executor of Router-authored work. Router owns waiting and route
state; Controller owns host actions and must clear a Router-authored action
ledger instead of stopping at ordinary role waits.

## What Changes

- Add a per-run Router daemon mode that ticks every one second while the run is
  active.
- Persist Router daemon status, heartbeat, lock, current wait, and recovery
  data under the current run root.
- Add a Controller action ledger where Router writes every Controller-visible
  command as a checklist item with dependencies, status, and required receipts.
- Change Controller from "ask Router once, execute once, then maybe stop" to
  "continuously clear Router action ledger items while the run is active."
- Keep all authority boundaries: Router decides, Controller executes host
  actions, roles write ACKs/reports/results, and no role directly advances the
  route.
- Change heartbeat/manual resume into lifecycle recovery: verify Router daemon,
  Controller executor, and six role slots; restart or rehydrate missing pieces
  from persisted run state.
- Replace ordinary nonterminal card/bundle/packet wait stops with Router-owned
  one-second polling of the expected mailbox evidence.
- Preserve current packet/card/runtime envelopes and existing Router
  `next`/`apply` logic by wrapping them in a persistent loop rather than
  replacing the control plane.
- Add FlowGuard and runtime tests for daemon liveness, single-Router locking,
  ACK/result consumption, Controller ledger clearing, idempotency, crash
  recovery, and terminal cleanup.

## Capabilities

### New Capabilities

- `persistent-router-daemon`: A per-run Router daemon continuously reconciles
  mailbox evidence and advances Router state on a fixed one-second tick.
- `controller-action-ledger`: Router and Controller communicate through a
  durable action checklist; Controller clears pending actions and writes one
  receipt per completed action.
- `daemon-lifecycle-recovery`: Heartbeat/manual resume restores the Router
  daemon, Controller executor, and role cohort from current-run persisted
  state instead of manually advancing route work.

### Modified Capabilities

- None. There are no existing OpenSpec specs in this repository; this change
  introduces the first spec contracts for this behavior.

## Impact

- Router runtime:
  - `skills/flowpilot/assets/flowpilot_router.py`
  - current run files under `.flowpilot/runs/<run-id>/`
- Controller prompt and runtime kit:
  - `skills/flowpilot/assets/runtime_kit/cards/roles/controller.md`
  - `skills/flowpilot/SKILL.md`
  - `skills/flowpilot/references/protocol.md`
- Role and packet prompt surfaces:
  - PM, reviewer, worker, and officer role cards
  - packet body/result templates and check-in instructions
- Heartbeat/manual resume:
  - continuation binding records
  - role rehydration flow
  - run lifecycle reconciliation
- Tests and models:
  - new persistent-router FlowGuard model/check runner
  - router runtime tests
  - card/packet instruction coverage tests
  - install sync and audit checks
