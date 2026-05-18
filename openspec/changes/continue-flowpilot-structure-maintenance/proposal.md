## Why

FlowPilot's model-code-test diagnostic now shows zero missing model, code,
test, stale-evidence, and internal-only-test gaps, but it still reports
explicit StructureMesh debt. The next maintenance pass should reduce the
largest safe-to-touch files without changing public behavior, hiding remaining
debt, or colliding with parallel agent work.

## What Changes

- Split oversized validation entrypoints into thin compatibility facades plus
  focused helper modules, starting with the model-test-code alignment runner.
- Preserve public CLI commands, importable helper names, JSON report shapes,
  and background-evidence semantics.
- Apply runtime owner-module splits only where the file is clean, the boundary
  is already pinned by external-contract tests, and the split can stay
  behavior-preserving.
- Keep dirty peer-agent scopes out of this change.
- Refresh StructureMesh/model-test diagnostic metadata, docs, adoption notes,
  local installed skill sync, and local git state after validation.
- Do not push, tag, publish, or create a GitHub release.

## Capabilities

### New Capabilities

- `flowpilot-structure-maintenance`: FlowPilot can continue reducing
  StructureMesh debt through facade-preserving, model-backed splits while
  keeping current diagnostic gaps honest.

### Modified Capabilities

- `flowpilot-diagnostic-convergence`: Diagnostics must distinguish completed
  splits, newly reduced validation entrypoints, and remaining deferred
  StructureMesh debt after each maintenance pass.

## Impact

- Affected model/check surfaces: oversized `simulations/run_*checks.py`
  validation entrypoints, especially
  `simulations/run_flowpilot_model_test_alignment_checks.py`.
- Affected runtime surfaces: only clean `skills/flowpilot/assets/*.py` owner
  modules with existing external-contract tests and no active peer-agent edits.
- Affected validation: model-test alignment, StructureMesh maintenance,
  focused unit tests, tier checks, install sync, local install audit, and local
  git commit.
