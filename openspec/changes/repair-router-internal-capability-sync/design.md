## Context

The stuck run has completed the child-skill manifest review chain:
reviewer ACK exists, reviewer result passed, PM approval exists, and
`capabilities.json` exists. The missing piece is
`capabilities/capability_sync.json`, which Router can derive from those inputs.

The bug is an ownership mismatch. The wait scheduler treats every unrecorded
event in the expected-event table as something a role must provide. That is
correct for real role decisions, but wrong for deterministic Router
postconditions whose inputs already live in the run directory.

## Goals / Non-Goals

**Goals:**

- Make Router-owned internal postconditions explicit instead of relying on
  event-name conventions.
- Materialize `capability_evidence_synced` before passive role waits are
  selected.
- If inputs are missing or invalid, expose a Router/control-plane blocker, not
  a Controller role wait.
- Reconcile stale Controller wait/projection rows after authoritative evidence
  exists.
- Keep manual/idempotent `record_external_event("capability_evidence_synced")`
  compatibility.

**Non-Goals:**

- Do not redesign the whole expected-event table or Controller action ledger.
- Do not turn all external events into Router-internal actions.
- Do not mutate frozen route acceptance, publish, deploy, or handle secrets.
- Do not erase unrelated active-run artifacts created by parallel agents.

## Decisions

1. **Use explicit event metadata.**

   Add metadata identifying `capability_evidence_synced` as a Router-owned
   internal postcondition. Expected external wait grouping filters these events
   out of passive role waits.

2. **Run an internal-postcondition reconciliation pass first.**

   The next-action path checks internal postconditions whose prerequisite flags
   are satisfied and whose event flag is still false. If source artifacts are
   present and valid, Router writes the sync artifact, records the event/flag,
   and asks next-action selection to recompute from fresh state.

3. **Use the existing capability sync writer.**

   The same sync function used by the manual event dispatcher remains the
   source of truth for writing `capability_sync.json`. This avoids a second
   implementation with different proof rules.

4. **Treat missing inputs as control-plane blockers.**

   If the prerequisite flag is true but the source artifacts are absent or
   invalid, the issue is local Router/material evidence drift. It should not be
   represented as waiting for Controller to invent an event.

5. **Clear stale projections from authoritative evidence.**

   Once `capability_sync.json` exists and the event/flag is recorded, old
   `await_role_decision` or blocked reminder rows for the same event are stale
   projections. Reconciliation should mark them resolved rather than leaving a
   live wait next to satisfied evidence.

## Risks / Trade-offs

- **Risk: over-internalizing real role events.** Mitigation: only events marked
  with the internal-postcondition metadata are filtered and materialized.
- **Risk: import cycles around the event dispatcher.** Mitigation: keep the
  postcondition reconciler in a narrow helper and call the existing capability
  sync function without importing the whole dispatcher path.
- **Risk: stale active-run artifacts remain from older code.** Mitigation:
  runtime reconciliation clears same-event projections when authoritative
  evidence exists; unrelated historical artifacts are left untouched.

## Migration Plan

1. Add OpenSpec deltas for Router-owned capability sync ownership.
2. Add runtime metadata and internal-postcondition reconciliation.
3. Update tests so daemon/Router path proves auto-materialization without a
   manual external event call.
4. Run focused tests and FlowGuard checks, with heavy meta/capability checks in
   background logs.
5. Sync the installed FlowPilot skill after code and evidence settle.
6. Keep git synchronization scoped away from unrelated peer-agent edits.
