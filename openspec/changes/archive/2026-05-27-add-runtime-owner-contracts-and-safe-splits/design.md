## Approach

This change continues the previous diagnostic burn-down in two passes:

1. **Direct runtime owner contracts first.** For each selected runtime owner module, add or reuse a test that directly calls its public or owner-boundary function and asserts the externally visible input/output contract. Then add a `CodeContract` and `TestEvidence` row to the FlowGuard source-contract alignment plan.
2. **Safe structure splits second.** Split only modules whose owner boundary is stable, whose functions are isolated enough to move without state-ordering risk, and whose files are not currently being edited by peer agents.

## Contract Coverage Rules

- A module is not upgraded merely because a test file mentions it.
- The source-contract plan must contain the code path and symbol.
- The test evidence must call the symbol and assert an externally visible result or failure.
- Aggregate tests may remain useful for broad inventory coverage, but they do not replace source-level owner contract tests.
- Release evidence that used `--skip-url-check` remains `release_local_only`.

## Structure Split Rules

- Keep compatibility facades stable.
- Prefer child-owner extraction that preserves imports and existing public names.
- Do not edit `scripts/run_test_tier.py` or `tests/test_flowpilot_test_tiers.py` while peer-agent changes are visible there, unless validation proves integration is required.
- Do not split state-ordering-sensitive modules without a specific StructureMesh target.

## Validation

Use the real FlowGuard package and executable checks:

- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
- `python simulations/run_flowpilot_model_test_alignment_checks.py --json-out simulations/flowpilot_model_test_alignment_results.json`
- Focused unit tests for the new owner-contract coverage.
- OpenSpec strict validation.
- Background fast tier validation with final artifact inspection.
- Local install sync and audit checks.

## Risks / Trade-offs

- [Risk] Direct tests could still be too shallow.
  Mitigation: each evidence row calls the contract symbol and asserts a concrete value, path, schema, or failure boundary.
- [Risk] Structure split work can collide with peer agents.
  Mitigation: skip currently dirty files owned by peers and keep deferred split metadata visible.
- [Risk] Diagnostic count improvements could hide residual runtime risk.
  Mitigation: keep residual `missing_test`, `internal_only_test`, `needs_structure_split`, and `stale_evidence` counts in the docs and JSON.
