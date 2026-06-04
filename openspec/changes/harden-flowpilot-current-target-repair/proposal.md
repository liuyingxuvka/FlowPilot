## Why

FlowPilot repair loops can keep old or unaccepted packet evidence on the active
control path after fresh repair evidence exists. This creates recurring
FlowGuard/PM repair expansion where blockers, PM decisions, or staged effects
continue to target stale `result_submitted` packets, blocked PM decision
packets, or future route state instead of a single current runtime target.

This change is needed now because the current run and a separate FlowPilot run
showed the same root family: repair generated new evidence, but the control
plane did not remove old evidence from routing authority.

## What Changes

- Add a runtime/router current-target gate that rejects noncurrent packets,
  stale route nodes, blocked PM decision packets, missing responsibilities, and
  replaced `result_submitted` packets before routing, blocker creation, PM
  repair dispatch, FlowGuard dispatch, review dispatch, and final preflight.
- Retire replaced `result_submitted` packets with
  `superseded_after_repair` when a current repair or reissue packet supersedes
  them.
- Keep PM repair decision parsing strict: only top-level `decision` JSON is
  valid. Nested wrappers remain unsupported.
- Reissue a fresh PM repair decision packet when an earlier PM decision packet
  is blocked or noncurrent; do not reuse it.
- Remove control-plane fallback responsibility/subject recovery. Missing
  current responsibility or current target becomes a hard control-plane
  blocker.
- Ensure pending staged effects converge to either a committed effect or one
  current blocker without same-family packet expansion.
- Extend FlowGuard models, model-test alignment, runtime tests, historical
  replay tests, and fake/bad packet tests for this repair family.
- Keep repository, installed skill, and local git state synchronized after
  validation.

## Capabilities

### New Capabilities

- `current-target-repair`: Defines how FlowPilot keeps one current
  packet/result/effect target during repair, blocks stale targets, rejects
  fallback/legacy shapes, and stops same-family control-plane expansion.

### Modified Capabilities

None. This change tightens the current-runtime repair contract without adding a
legacy migration or compatibility surface.

## Impact

- Runtime mechanics in
  `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`.
- FlowPilot formal entrypoint/final-preflight behavior through existing runtime
  helpers.
- Core runtime, high-standard control flow, lifecycle guard, historical replay,
  router/runtime, fake bad-packet, and install-sync tests.
- FlowGuard simulation models and runners for control-plane friction,
  validation PM gates, model-test alignment, and current-contract regression
  hazards.
- Installed FlowPilot skill synchronization and local git commit after all
  validation passes.
