## Why

The new FlowPilot runtime has the right shape: current-run ledgers, sealed
packets, dynamic leases, FlowGuard officer packets, reviewer packets,
system validation, system closure, and PM disposition packets. The remaining control
gap is semantic gate outcome handling. A reviewer can write a body that means
"block" or "fail", or the system validation pass can fail,
while the fresh packet path still treats the packet family as accepted unless a
mechanical envelope blocker is present.

That recreates an old FlowPilot failure mode: a gate has a pass path, but its
non-pass path is not routable. The old protocol solved this with explicit
pass/block outcomes, active blockers, PM repair decisions, same-class recheck,
and stale-evidence invalidation. The new runtime should borrow that contract
without restoring the old fixed-role stack.

## What Changes

- Add a compact semantic outcome parser for worker, FlowGuard officer,
  reviewer, and PM repair-decision packet bodies, plus system validation
  outcomes.
- Record every parsed outcome in the run ledger with role, packet, subject,
  target result, decision, blocker class, recommendation, and evidence refs.
- Convert reviewer blocks, system validation failures, FlowGuard failures, and
  worker blocked/needs-PM results into active blockers instead of accepted
  evidence.
- Automatically issue a PM repair-decision packet for each active semantic
  blocker.
- Apply PM repair decisions through the existing new runtime primitives:
  same-node repair, sender reissue, more evidence or validation rerun, route
  mutation, evidence quarantine, controlled stop, or authorized waiver.
- Clear an active blocker only through a current same-gate/same-review-class
  pass after repair.
- Extend FlowGuard and ordinary tests so a body-level block/fail cannot be
  silently treated as pass.
- Sync the installed local `flowpilot` skill after validation.

## Capabilities

### New Capabilities

- `new-flowpilot-semantic-gate-outcomes`: Fresh runtime semantic
  pass/block/fail parsing, active blocker lifecycle, PM repair-decision routing,
  same-class recheck, and stale evidence handling.

### Modified Capabilities

- `black-box-packet-lifecycle`: Packet acceptance depends on semantic outcome
  as well as mechanical envelope validity.
- `high-standard-flowpilot-control-flow`: High-standard gates cannot advance
  through reviewer prose or system validation evidence that says the gate
  failed.
- `new-flowpilot-liveness-recovery`: `repair_packet` remains nonterminal, but
  semantic blockers now route to PM repair-decision packets instead of passive
  stuck states.

## Impact

- Runtime: `skills/flowpilot/assets/ai_project_runtime/runtime.py`
- Entrypoint behavior: `skills/flowpilot/assets/flowpilot_new.py` through the
  existing submit-result/status paths.
- Models: new focused FlowGuard semantic gate-outcome model plus result
  artifact.
- Tests: focused high-standard/new-entrypoint tests for reviewer block, system
  validation fail, worker blocked, PM repair decisions, same-class recheck, and
  no silent pass.
- Install sync: local installed `flowpilot` skill under the active Codex skills
  directory.
