## Why

FlowPilot's model-code-test diagnostic has converged on behavior coverage, but it still reports 48 explicit StructureMesh gaps caused by oversized validation runners and runtime contract modules. Clearing those gaps now makes future bugs easier to localize because the public facade, model block, code owner, and external contract tests will point to the same small unit.

## What Changes

- Split the remaining oversized validation runners behind thin CLI-compatible entrypoints.
- Split low-conflict runtime contract modules behind compatibility facades while preserving public imports, CLI behavior, and external data contracts.
- Add or extend external contract tests that prove split child modules combine to the same public surface exposed before the split.
- Regenerate the model-code-test diagnostic and update structure documentation with the exact remaining debt, if any.
- Preserve peer-agent work by touching only scoped clean files and staging only this change's files.

## Capabilities

### New Capabilities
- `flowpilot-structure-debt-convergence`: governs clearing the remaining model-code-test StructureMesh gaps through facade-preserving splits and current evidence.

### Modified Capabilities

## Impact

- Affected code: `simulations/run_*checks.py`, selected `skills/flowpilot/assets/*.py`, and focused tests for model-check runner and runtime external contracts.
- Affected evidence: `simulations/flowpilot_model_test_alignment_results.json`, FlowGuard adoption notes, and local install sync/audit records.
- No breaking API change is intended; existing script commands and module imports must keep working.
