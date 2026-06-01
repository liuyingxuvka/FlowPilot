## Why

The `run-20260531-210441` review exposed a completed FlowPilot run with high
control-plane friction: accepted packets retained stale active leases after
replacement, controller/status projections could expose too much body-oriented
state, recovery duty did not provide a direct next command, node context package
schema drift caused repair loops, FlowGuard evidence summaries were easy to
generate in an unstable order, current status stayed visually stale after
terminal return, and full JSON status output was too heavy for long runs.

The earlier 60-packet run (`run-20260531-111236`) did not hit these paths, so
this is not a request to roll back to the old system. The change should keep the
new runtime's stricter gates and add the missing mechanical cleanup,
projection, and validation paths that make those gates usable.

## What Changes

- Reassigning a packet must supersede any older active lease for that packet,
  and final preflight must block if an accepted packet still has stale active
  leases.
- Controller-facing status and ledger projections must remain body-free unless
  an explicit terminal summary or authorized role body-open path is used. A
  reviewer or PM seeing body content through an authorized review path is not a
  hard failure by itself; only cross-role execution, wrong-authority submission,
  or public/controller projection leakage is hard-blocking.
- Recovery foreground duty must include a concrete lease-agent command plan
  naming the packet, responsibility, host kind, and stale lease cleanup target.
- Node acceptance plan extraction must accept only the intended top-level
  `node_context_package` contract and reject the known nested
  `node_acceptance_plan.node_context_package` shape as a structured repair
  blocker instead of silently normalizing it.
- Evidence summary manifests must be written in a stable finalization order and
  must not include unstable self-referential summary artifacts.
- Current-run pointer status must reflect terminal completion when final
  preflight allows terminal return.
- Long-run status output must have a compact default path, with full ledger
  output reserved for explicit debug calls.

## Capabilities

### Modified Capabilities

- `runtime-ledger-persistence`: add accepted-packet stale lease cleanup and
  final preflight health checks.
- `packet-open-authority-exits`: add body-free controller projections and
  reinforce authorized body-open boundaries.
- `controller-foreground-standby`: add actionable recovery duty payloads.
- `runtime-state`: derive current pointer lifecycle/status from terminal
  closure state.
- `known-friction-regression-gates`: add historical replay coverage for the
  `run-20260531-210441` friction family.
- `flowpilot-packet-review-flow`: normalize node context package shape before
  reviewer repair loops.

## Impact

- Affected runtime modules include `flowpilot_core_runtime/runtime.py`,
  `run_shell.py`, `control_surface.py`, and `flowpilot_new.py`.
- Affected tests include new runtime/core runtime tests and known-friction
  regression checks.
- Affected evidence includes FlowGuard focused runtime checks, project topology
  freshness, install sync checks, local install audit, and smoke checks.
