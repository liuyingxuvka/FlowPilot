## Why

The current FlowPilot control plane can still keep old repair-chain blockers,
accepted-but-superseded packet evidence, and compatibility parsing surfaces in
the live decision path. A later repair packet can exist, but final preflight can
still stop on an earlier blocker family because the old blocker was never made
non-authoritative.

This change is needed because the desired runtime contract is new-only: sealed
ledger history may remain audit evidence, but only one current packet/result,
blocker, PM decision, and gate path may drive the next action. Compatibility
aliases, prose parsing, implicit pass defaults, and old public bypass entrypoints
must not be part of the formal control path.

## What Changes

- Retire older same-family active blockers when a newer repair packet, PM repair
  decision packet, or recheck blocker becomes the current authority.
- Treat accepted-result plus superseded-packet state as historical evidence only,
  not as an active current target.
- Reject packet outcomes that do not provide the current strict JSON contract;
  missing or unknown `decision` becomes a mechanical protocol block, not an
  implicit pass.
- Keep PM repair decisions strict to one top-level JSON shape. No nested
  wrappers, no summary/recommended-resolution fallback, and no prose inference.
- Make final preflight report only current blockers and explicitly retired stale
  references; stale historical blockers must not continue to block completion.
- Remove formal CLI/documentation surfaces that describe or expose old router
  compatibility paths as a current option.
- Extend the existing FlowGuard control-plane friction model and focused tests
  with long repair-chain scenarios, including the first-node blocker family.
- Synchronize the installed FlowPilot skill and local git version after focused
  and long regression validation.

## Capabilities

### Modified Capabilities

- `flowpilot-control-plane-contract-kernel`: Adds the new-only control-plane
  convergence contract for blockers, packet outcomes, PM decisions, final
  preflight authority, and formal entrypoints.

## Impact

- Runtime mechanics in
  `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`.
- Formal FlowPilot entrypoint surface in `skills/flowpilot/assets/flowpilot_new.py`
  and related install/entrypoint checks.
- Existing FlowGuard control-plane friction models and runners.
- Focused runtime tests for packet outcome parsing, blocker convergence,
  accepted/superseded packet state, final preflight, and old-entrypoint absence.
- Installed skill synchronization and local git commit after validation.
