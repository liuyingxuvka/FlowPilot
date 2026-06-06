## Why

FlowPilot runs are long-lived and multi-turn, so temporary patches, legacy
recovery branches, duplicate adapters, and unclear maintenance layers can
silently become permanent structural debt. The runtime already rejects many
old-shape inputs, but each route also needs an explicit convergence check so
completed work leaves one clear, maintainable current-contract path unless a
named maintenance layer is intentionally owned and validated.

## What Changes

- Add a route-wide structural convergence requirement to FlowPilot planning:
  every route must identify expected cleanup, allowed current-runtime recovery,
  and any intentionally retained maintenance surface.
- Add node/work-packet/result expectations for structure hygiene so workers
  report whether they introduced, removed, rejected, or intentionally retained
  fallback-like paths.
- Require reviewers and final PM closure to block unresolved structural debt,
  unowned compatibility branches, stale generated artifacts, and unsupported
  old paths.
- Extend FlowGuard planning-quality coverage with negative scenarios for
  missing structural review, missing node hygiene expectations, unowned
  fallback retention, repair paths that leave compatibility branches, and
  final ledgers that do not dispose of structure debt.
- Keep allowed recovery narrow: it may reissue, block, or ask for a current
  structured result, but it must not silently translate old input into current
  completion evidence.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `flowpilot-structure-debt-convergence`: Route planning, work packets,
  worker results, reviewer gates, and final closure must explicitly dispose of
  structural debt and fallback-like paths before a FlowPilot route can be
  claimed complete.

## Impact

- FlowPilot runtime prompt cards and templates under `skills/flowpilot/assets`
  and `templates/flowpilot`.
- FlowGuard planning-quality model and tests under `simulations/` and `tests/`.
- OpenSpec change artifacts, topology/adoption records, local install sync,
  and focused plus background validation evidence.
