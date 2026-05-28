## Why

FlowPilot already imports the real FlowGuard package and has many completed
FlowGuard adoption changes, but the latest full model-test-code diagnostic still
reports externally relevant runtime surfaces as internally tested only. That gap
prevents a credible claim that the FlowGuard kernel adoption, legacy-data
compatibility, install sync, and local acceptance pass are complete.

## What Changes

- Close the current FlowGuard model-test-code evidence gap for runtime-owner
  surfaces that are tested but not bound to external code contracts.
- Keep peer-agent OpenSpec work isolated: this change only governs the
  FlowGuard-kernel adoption closure path and must not mark or complete sibling
  change tasks.
- Recheck legacy-data and old-logic disposition through existing compatibility,
  install, and diagnostic gates instead of deleting or rewriting unrelated
  history.
- Require strict OpenSpec validation, focused tests, FlowGuard model-test
  alignment, background FlowGuard regression evidence, and local install
  freshness before completion is claimed.
- Preserve local git visibility for peer changes; final reporting must state
  which files were changed by this work and which dirty files were already
  present or peer-owned.

## Capabilities

### New Capabilities

- None. This is a maintenance closure change over existing FlowPilot and
  FlowGuard adoption capabilities.

### Modified Capabilities

- `runtime-owner-contract-coverage`: runtime owner modules used in the
  FlowGuard full diagnostic must have external code-contract rows and ordinary
  tests that directly exercise the claimed symbols.
- `flowguard-full-coverage-findings`: full diagnostic actionable findings must
  be treated as completion blockers or explicitly scoped, not hidden by subset
  alignment success.
- `repository-maintenance-guardrails`: final maintenance acceptance must include
  current OpenSpec, FlowGuard, background-regression, install-freshness, and
  local-git evidence while preserving peer-agent work.

## Impact

- Affects FlowGuard model-test-alignment evidence declarations under
  `simulations/`.
- May affect focused runtime-owner tests under `tests/` only where direct
  external-contract assertions are missing.
- Uses existing install and audit scripts under `scripts/`.
- Does not change public release, remote publish, destructive cleanup, or
  sibling OpenSpec task ownership.
