## Why

FlowPilot already permits multiple runs or Flow blocks to be active in
parallel, but current validation can still treat "many active things" as
ambiguous when the UI/status surface does not prove their identities,
ownership, and operation targets. This change prevents a legal multi-flow
run from being confused with stale active residue while preserving parallel
execution and merge behavior.

## What Changes

- Add an explicit active-set authority contract for user-visible parallel
  Flow blocks.
- Distinguish two valid parallel forms: multiple live agents inside one Flow
  block, and multiple independent Flow blocks or runs active at the same time.
- Require each displayed active Flow block to carry a stable identity, scope,
  status, default UI focus marker, targetable operation identifiers, and
  stale/residue classification.
- Require global operations such as continue, stop, inspect, resume, merge, or
  apply-to-all to declare whether they target one Flow block/run or all
  selected blocks/runs.
- Preserve the existing rule that `.flowpilot/current.json` is UI
  focus/default-target metadata only, not daemon authority or a global main
  route.
- Add FlowGuard and runtime tests that accept legal A/B/C parallelism and
  reject stale active residue, wrong target routing, or accidental all-run
  operations.

## Capabilities

### New Capabilities

- `parallel-flow-block-authority`: Active-set identity, UI focus, targetable
  operations, and stale-residue handling for parallel Flow blocks/runs.

### Modified Capabilities

- `parallel-flowpilot-run-isolation`: Clarify that independent running runs
  are legal background active entries only when the active-set projection
  exposes them with explicit identity and operation boundaries.
- `controller-user-status`: Extend plain-language status summaries so users can
  tell whether they are viewing all Flow blocks, one focused block, or a
  targeted operation.

## Impact

- Affected code: route/frontier status snapshot and active UI task catalog
  projection, control-plane friction live audit, Router status/CLI output, and
  targeted operation metadata.
- Affected validation: OpenSpec strict validation, FlowGuard control-plane
  friction checks, model-test alignment, focused router runtime tests, fast
  tier, background Meta and Capability regressions, install sync, and local git
  commit.
- No breaking change: this does not disable parallel FlowPilot runs or require
  a single global main line.
