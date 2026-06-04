## Why

FlowPilot currently has recurring control-plane friction where FlowGuard or
Reviewer gates expect future committed route/node state before runtime is
allowed to commit it. This creates repair loops around node acceptance planning,
route mutation gates, PM repair reissue, and stopped semantic blockers.

The fix must preserve the new runtime's small current-contract shape. It should
not recreate old-router complexity with multiple candidate ledgers or
compatibility surfaces.

## What Changes

- Introduce one lightweight staged-effect mechanism for gated side effects that
  must be reviewed before runtime commits them.
- Move mechanical result validation to runtime/router submission time so
  FlowGuard and Reviewer review real current artifacts instead of schema fields.
- Stage node acceptance plan/context binding until FlowGuard and Reviewer
  accept the submitted PM result.
- Stage route mutation effects until the PM gate passes, without changing the
  active route version early.
- Preserve packet kind and route scope when PM requests `sender_reissue` or
  `collect_more_evidence`.
- Add a formal stopped-blocker recovery command so `stop_for_user` does not rely
  on plain lifecycle resume.
- Remove FlowGuard API fallback behavior that manufactures manual block
  evaluations when the real toolchain fails.
- Keep install synchronization serialized: validated repository source first,
  then installed local FlowPilot skill and install audit/check.

## Capabilities

### New Capabilities

- `staged-gated-effects`: Defines how FlowPilot stages small current-contract
  side effects on existing result/gate surfaces before committing them after
  FlowGuard and Reviewer review.

### Modified Capabilities

None. Existing route repair, packet review, formal gate, resume, and known
friction behavior are exercised through this new staged-effect capability and
the focused regression tasks in this change.

## Impact

- Runtime mechanics in
  `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`.
- CLI command surface in `skills/flowpilot/assets/flowpilot_new.py`.
- Runtime cards for PM, FlowGuard operator, Reviewer, and resume decisions.
- Focused runtime, recursive route, high-standard control flow, entrypoint, and
  card instruction tests.
- Focused FlowGuard simulation runners for validation PM gates, route hard
  gates, prework FlowGuard gates, packet lifecycle, work orders, and decision
  liveness.
- Local install synchronization and audit after validation.
