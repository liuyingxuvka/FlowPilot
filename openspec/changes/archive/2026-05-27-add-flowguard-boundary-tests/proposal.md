## Why

The upgraded FlowGuard model-test alignment pass now surfaces ordinary-test
coverage gaps that were previously hidden behind broad model checks. FlowPilot
needs focused boundary tests for these gaps so model confidence does not
overclaim runtime-contract coverage.

## What Changes

- Add ordinary external-contract tests for the highest-priority FlowGuard
  model-test alignment gaps:
  - `controller_process_aside`, currently covered only by internal references.
  - `flowpilot_material_artifact_map`, currently lacking ordinary test
    evidence in the diagnostic corpus.
- Update FlowGuard model-test alignment evidence so the new tests are mapped to
  explicit model obligations and code contracts.
- Run the focused model checks and tests, then fix any implementation defects
  the new boundary tests expose.
- Do not split files or prune branches as part of this change.

## Capabilities

### New Capabilities

- `flowguard-boundary-test-alignment`: model-to-code-to-test alignment for
  FlowPilot runtime-contract boundary surfaces that need ordinary test
  evidence.

### Modified Capabilities

- None.

## Impact

- Affects FlowGuard model-test alignment metadata under `simulations/`.
- Affects ordinary tests under `tests/`.
- May affect runtime code only if a newly added boundary test exposes a real
  defect.
- Requires local FlowPilot install sync if any repo-owned skill code changes.
