## Why

The material repair generation fix still leaves a split-brain progress source: the active material batch can show the current repair generation is not relayed or complete while old run-wide material flags still say the material scan is complete.

This change closes that gap by making active material generation and batch state authoritative for material repair progress.

## What Changes

- Derive material packet next actions from the active material batch and current material generation, not directly from run-wide material progress flags.
- Prevent stale run-state saves from restoring old material progress flags after a new active material repair generation clears them.
- Ensure material dispatch blocks and PM material disposition role-output reconciliation are scoped to the active repair transaction and current material generation.
- Add focused runtime tests and FlowGuard checks for active repair batches with stale run-wide flags.
- Sync the validated repository-owned FlowPilot skill into the local installed version and verify install freshness sequentially.

## Capabilities

### New Capabilities

- `material-progress-generation-projection`: Material repair progress is derived from the active material batch and current generation before any run-wide flag can drive next actions or wait closure.

### Modified Capabilities

- None. This adds an explicit contract around existing material repair, wait reconciliation, and runtime persistence behavior.

## Impact

- Affected runtime assets: material packet next-action selection, runtime state persistence merge policy, role-output bridge reconciliation, and material dispatch block generation metadata.
- Affected tests: focused router runtime material repair tests, runtime state persistence tests, role-output reconciliation/idempotency tests, and FlowGuard control-plane friction checks.
- Affected install surface: repository-owned FlowPilot skill must be synced after validation.
- No dependency, stack, release, deployment, or public publication change is included.
