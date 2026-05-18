## Why

The full FlowPilot model-code-test diagnostic still reports router owner modules with no ordinary external-contract evidence. This keeps the model, code structure, and test corpus aligned only at the broad facade level instead of proving each selected owner module's observable input/output boundary.

## What Changes

- Add direct external-contract tests for the next safe batch of router owner modules.
- Extend the FlowGuard model-test-code source-contract plan with code contracts and ordinary test evidence for those owner modules.
- Regenerate the alignment diagnostic so residual missing tests and structure-split gaps remain visible.
- Keep this pass test/evidence-only; do not split stateful router modules in the same change.

## Capabilities

### New Capabilities
- `router-owner-contract-coverage`: Tracks the requirement that selected router owner modules have source-level code contracts and direct ordinary tests for externally visible input/output behavior.

### Modified Capabilities
- None.

## Impact

- Affects focused router owner tests, `simulations/run_flowpilot_model_test_alignment_checks.py`, diagnostic JSON, OpenSpec artifacts, FlowGuard adoption notes, local install sync, and a local git commit.
- Does not publish, push, tag, or create a GitHub release.
