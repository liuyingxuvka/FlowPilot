## Context

FlowPilot has two different kinds of stateful Controller receipts:

- Controller work that produces Router-visible evidence, such as a delivered
  artifact, packet relay record, result envelope, or mail artifact.
- Router-owned state loading work, such as `load_resume_state`, where the
  authoritative effect is the Router action handler mutating Router state.

The existing receipt folding work handled evidence-backed Controller work, but
`load_resume_state` exposed a second ownership class. The Router handler can
load resume state and set `resume_state_loaded`, but the Controller ledger
projection can also represent the same step as a Controller `done` receipt. If
receipt reconciliation does not replay the Router-owned handler, the receipt is
neither sufficient proof nor a valid state transition.

## Goals / Non-Goals

**Goals:**

- Represent Router-owned state loader receipt folding as its own ownership
  class.
- Reuse the existing Router action handler for replay so direct action and
  receipt reconciliation stay behaviorally aligned.
- Make the allowed replay set explicit in a shared contract registry.
- Extend FlowGuard and source audit coverage so future `load_*_state` direct
  flag writers cannot miss the replay registry.
- Keep local install synchronization and model evidence current after the
  repair.

**Non-Goals:**

- Do not let Controller receipts become sufficient proof for Router-owned
  state.
- Do not redesign the two-table scheduler, packet runtime, sealed body
  boundaries, or PM repair lanes.
- Do not cleanse historical active-run blocker artifacts in this change; the
  change prevents the same unsupported path from recurring.
- Do not perform release, publish, or dependency changes.

## Decisions

1. **Use a small replay registry for Router-owned state loaders.**

   The shared control-plane contract lists action types such as
   `load_resume_state` and `load_role_recovery_state` that may be replayed from
   receipt reconciliation. This is narrower than a generic "any stateful
   receipt can run an action" rule and avoids making Controller receipts too
   powerful.

2. **Call the registered Router action handler instead of duplicating logic.**

   Receipt reconciliation invokes the same registered action application path
   used by direct Router action execution. That makes the postcondition writer,
   state mutation, and side effects match the direct path and avoids a parallel
   mini-implementation.

3. **Keep unsupported stateful receipts as blockers when no registry entry
   exists.**

   A Controller receipt for an unknown stateful action still routes to the
   existing unsupported/missing-postcondition blocker behavior. The new registry
   is an allow-list, not a fallback.

4. **Use FlowGuard to model both the safe and unsafe ownership cases.**

   The focused receipt-fold model now includes a safe state-loader replay case
   and a known-bad `router_owned_state_projected_without_replay` case. The
   source audit scans `load_*_state` direct flag writers and compares them to
   the replay registry.

## Risks / Trade-offs

- **Risk: replaying too broad a class of actions** -> Mitigation: only
  registry-listed Router-owned state loader actions are replayable.
- **Risk: duplicate state mutation on repeated daemon ticks** -> Mitigation:
  replay uses idempotent Router handlers and existing reconciliation tracking.
- **Risk: model source audit misses a differently named state loader** ->
  Mitigation: the audit covers the current `load_*_state` naming pattern and
  keeps manual review visible for actions outside that convention.
- **Risk: active-run live audit still reports stale historical blockers** ->
  Mitigation: treat live-run cleanup as a separate operational repair; this
  change updates the code/model path and reports stale live evidence as scoped
  residual state.

## Migration Plan

1. Add the OpenSpec deltas for Router-owned state receipt replay.
2. Extend the focused FlowGuard model and source audit with safe and known-bad
   state-loader replay cases.
3. Add the shared replay registry and hook it into Controller receipt
   reconciliation before unsupported-postcondition handling.
4. Add a resume runtime regression for `load_resume_state` receipt replay.
5. Run focused foreground checks plus background meta/capability and router
   regression checks, then inspect final artifacts.
6. Sync the installed local FlowPilot skill and run install audit/checks after
   code and generated evidence settle.
7. Keep git synchronization scoped to this change set and do not mix unrelated
   peer-agent changes into a commit without explicit selection.
