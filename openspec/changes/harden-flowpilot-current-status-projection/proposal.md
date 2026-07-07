## Why

Recent FlowPilot run audits showed a control-plane projection miss: the current
run authority could reach terminal completion while derived display surfaces
still exposed null, unknown, awaiting, or historical blocker state as if it were
current. That confuses users and later agents, and it weakens the current-only
runtime contract.

The fix is not to add target-application fields or compatibility surfaces. The
fix is to make the existing current-run authority project through one coherent
status path, and to prove stale history cannot leak into current control
surfaces.

## What Changes

- Make current status projection derive top-level run, closure, lifecycle, and
  final-return fields from the current run ledger, lifecycle guard, foreground
  duty, and final preflight.
- Keep historical blockers, repaired nodes, and repair dossiers as history only;
  current display surfaces must expose only current-effective blockers and
  current-effective repair state.
- Refresh the existing `status_projection` during run-shell ledger saves instead
  of leaving it null after completion.
- Make node closure and repair dossier projections converge when PM disposition,
  blocker clearing, route replacement, or terminal closure makes their previous
  current pointer noncurrent.
- Add focused FlowGuard and unit-test coverage for the finite Cartesian product
  of closure state, blocker state, node closure state, repair-dossier state, and
  projection surface.

## Non-Goals

- No target-application-specific fields, examples, or runtime branches.
- No compatibility aliases, legacy field reads, newest-run fallback, missing
  field defaults, prose guessing, or automatic translation from old shapes.
- No new packet family, role, ledger, or second status authority.
- No production natural-language judge for review quality.

## Impact

- Affected code: FlowPilot core runtime status projection, run-shell artifact
  materialization, node closure state convergence, repair-dossier projection,
  and role-memory current blocker projection.
- Affected tests/models: focused runtime unit tests, a FlowGuard current status
  projection model, topology freshness, install/self-check evidence, and
  OpenSpec validation.
