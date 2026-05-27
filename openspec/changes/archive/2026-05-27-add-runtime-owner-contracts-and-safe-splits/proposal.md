## Why

The full FlowPilot model-code-test diagnostic still reports runtime owner modules whose tests are internal-only or missing. This blocks a credible claim that model obligations, code surfaces, and ordinary tests agree at each module boundary.

## What Changes

- Add direct external-contract tests for prioritized runtime owner modules instead of relying only on aggregate facade or mention-based evidence.
- Extend the FlowGuard model-test-code source-contract plan so those runtime owner modules are bound to explicit code contracts and ordinary test evidence.
- Apply only safe structure improvements where a stable owner boundary is already modeled and no peer-agent edit is active.
- Preserve local-only release evidence as local-only; do not turn `--skip-url-check` into public release proof.

## Capabilities

### New Capabilities
- `runtime-owner-contract-coverage`: Tracks the requirement that runtime owner modules have direct external-contract tests tied to model obligations and code contracts.
- `safe-runtime-structure-splits`: Tracks the requirement that structure splits happen only after the owner boundary is modeled and verified.

### Modified Capabilities
- None.

## Impact

- Affects `simulations/run_flowpilot_model_test_alignment_checks.py`, focused runtime owner tests, diagnostic result JSON, docs, and local install sync.
- May touch small runtime owner helper modules only when the split target is isolated and verified.
- Does not publish, push, tag, or create a GitHub release.
