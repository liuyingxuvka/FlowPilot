## Why

Recent live FlowPilot runs still produced a flat plan with only a handful of
broad leaf nodes even after recursive route guidance was installed. The runtime
can now refuse parent/module worker dispatch, but that is a late mechanical
guard. The higher-quality behavior must happen earlier: PM should design a
fine-grained executable route, FlowGuard Operator should check that the process
can actually traverse it, and Reviewer should block any route whose leaves are
still too broad.

The user specifically wants the simplified new FlowPilot model preserved. This
change must not add a large field mesh or a second human-readable plan. It
should reuse the existing planning, FlowGuard, Reviewer, blocker, and PM repair
flow.

## What Changes

- Make the PM planning packet explicitly warn that Reviewer will judge whether
  leaves are small, single-purpose, non-overlapping, and worker-ready before
  route materialization.
- Update PM guidance so examples like "research, implement, validate" are
  treated as stage names that usually need deeper children, not final leaves.
- Update FlowGuard Operator route-process guidance to identify worker-decision
  leakage: any route that only works because a Worker invents subtasks, orders
  child work, or decides decomposition must fail the process check.
- Update Reviewer route guidance so Reviewer is the semantic decomposition
  quality gate. Reviewer may suggest concrete splits, but PM owns the revised
  route.
- Keep runtime schema conservative: no new persistent route-node fields unless
  later tests prove existing fields cannot carry the guarantee.
- Add focused tests showing a broad route can be blocked by Reviewer before
  materialization and then repaired through the existing PM repair/recheck
  path.

## Impact

- `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`
- Runtime card prompts under `skills/flowpilot/assets/runtime_kit/cards/`
- Focused FlowPilot tests under `tests/`
- OpenSpec validation, targeted unit tests, FlowGuard model checks, topology
  checks, and installed skill sync.
