## Why

FlowPilot already has heavyweight Meta/Capability models and many focused
boundary models, but recent Router failures show a missing middle evidence
tier. The heavyweight models compress the Router execution mechanics too much,
while focused models do not prove end-to-end control-flow convergence.

## What Changes

- Add a fast FlowGuard model for the end-to-end Router process loop that keeps
  tick settlement, wait/event authority, blocker lanes, retry budgets, PM repair
  returns, route mutation, evidence freshness, per-node reviewer coverage,
  blocker lane classification, and terminal ledger convergence explicit.
- Add a runner that reports safe graph, progress/stuck, hazard coverage, and a
  current-run projection/audit.
- Use the new model to simulate known bad process outcomes and report current
  process risks without running heavyweight Meta/Capability checks.

## Capabilities

### New Capabilities

- `router-process-liveness`: FlowPilot has a fast middle-layer model that
  checks whether Router-controlled work can progress or block cleanly without
  compressing the control mechanics that caused recent misses.

### Modified Capabilities

- None.

## Impact

- FlowGuard model/checks:
  - `simulations/flowpilot_process_liveness_model.py`
  - `simulations/run_flowpilot_process_liveness_checks.py`
- OpenSpec change artifacts for this validation capability.
- No runtime Router behavior changes.
