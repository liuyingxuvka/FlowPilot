## Why

FlowPilot now has a model-test alignment gate, but the current gate only covers
a selected core subset of runtime obligations. The next maintenance risk is
false confidence: owner modules, compatibility facades, script entrypoints, and
test tiers may drift outside the model-test-code map while existing checks still
report green.

## What Changes

- Add a full software diagnostic pass that inventories owner modules, facades,
  script entrypoints, and test tiers as first-class model-test-code surfaces.
- Extend the FlowGuard model-test alignment evidence so each diagnostic surface
  can be classified as covered, missing-model, missing-code, missing-test,
  extra-code, internal-only-test, stale-evidence, or needs-structure-split.
- Produce a machine-readable and human-readable gap report for the current
  FlowPilot repository state.
- Add known-bad diagnostics proving that the checker rejects orphan code,
  unmodeled tests, wrapper-only evidence, progress-only background evidence,
  and broad modules that should be split before a release claim.
- Keep this change local and diagnostic-oriented; no GitHub push, tag, or
  release publication is part of this change.

## Capabilities

### New Capabilities

- `full-model-test-code-diagnostics`: FlowGuard-backed full-repository
  diagnostic coverage for model, code, and test alignment across owner modules,
  facades, script entrypoints, and test tiers.

### Modified Capabilities

- `repository-maintenance-guardrails`: Maintenance evidence must distinguish a
  full diagnostic pass from selected subset alignment and must not treat
  progress-only background artifacts as release evidence.

## Impact

- Affected artifacts:
  - `simulations/run_flowpilot_model_test_alignment_checks.py`
  - new or updated diagnostic result artifacts under `simulations/`
  - tests covering the full diagnostic report and known-bad cases
  - documentation for interpreting model/test/code diagnostic gaps
- No external API change.
- No new third-party dependency.
- Local install sync is required after repository-owned FlowPilot skill files
  are changed or if the diagnostic identifies install-boundary drift.
