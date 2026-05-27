## Why

FlowPilot now has a prioritized full model-code-test diagnostic, but most
surfaces still report missing or weak alignment evidence. The next pass should
burn down the highest-value gaps so model blocks, owner code, facades, script
entrypoints, and tests are bound by external contracts rather than only listed.

## What Changes

- Convert high-priority `missing_test` and `internal_only_test` findings into
  direct external-contract evidence, starting with release/validation gates and
  model-check runner surfaces.
- Convert selected `missing_model` and `extra_code` findings into explicit
  model bindings or diagnostic classifications so owner code is not left
  outside the model architecture.
- Add aggregate conformance tests that verify model-check runner entrypoints,
  test-tier command surfaces, and script-entrypoint contracts through stable
  input/output behavior.
- Keep broad structure-split candidates actionable but avoid unsafe wide
  refactors while peer agents may be active.
- Update diagnostic docs, result JSON, install sync evidence, FlowGuard
  adoption records, and local git state after validation.

## Capabilities

### New Capabilities

- `model-code-test-gap-burn-down`: Covers prioritized reduction of FlowPilot
  model-code-test diagnostic gaps through external-contract tests, model
  bindings, code classification, and safe structure-split repair planning.

### Modified Capabilities

- None.

## Impact

- Affected diagnostics: `simulations/run_flowpilot_model_test_alignment_checks.py`
  and `simulations/flowpilot_model_test_alignment_results.json`.
- Affected tests: model-test alignment tests, public CLI/script entrypoint
  tests, model-check runner contract tests, and tier/background evidence tests.
- Affected docs: model-test-code alignment guidance and full diagnostic report.
- Affected operations: background regression evidence, local FlowPilot skill
  install sync, FlowGuard adoption log, KB postflight, and local git commit.
