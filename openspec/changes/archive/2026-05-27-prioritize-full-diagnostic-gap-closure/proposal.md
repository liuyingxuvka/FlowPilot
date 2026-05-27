## Why

FlowPilot's full model-test-code diagnostic can now enumerate gaps, but the
report still needs stronger triage, direct external-contract evidence for the
highest-risk code surfaces, and trustworthy background validation status before
it can drive repair work without manual reinterpretation.

## What Changes

- Add prioritized diagnostic metadata for every full model-test-code finding:
  severity, surface owner, release relevance, repair type, dedupe key, and a
  top actionable finding list.
- Expand source-contract coverage around high-priority FlowPilot surfaces,
  including packet runtime facades, router receipt/PM-role helpers, terminal
  closure/runtime closure, and daemon lock/status/queue behavior.
- Add public CLI behavior tests for installer, sync audit, release audit, test
  tier, and packet/output/lifecycle script entrypoints.
- Strengthen background evidence classification so final artifacts, stale
  evidence, incomplete runs, progress-only logs, and release local-only proofs
  are reported distinctly.
- Record structure split candidates as immediate or deferred repair items,
  without forcing risky broad splits while owner-module polish is still fresh.

## Capabilities

### New Capabilities

- `model-test-code-diagnostic-gap-closure`: Covers prioritized full-software
  model-code-test diagnostics, external-contract evidence expansion, CLI
  evidence, background run classification, and structure-split repair planning.

### Modified Capabilities

- None.

## Impact

- Affected diagnostics: `simulations/run_flowpilot_model_test_alignment_checks.py`
  and its generated result JSON.
- Affected tests: focused model-test-code alignment tests, router boundary
  tests, and new or expanded CLI/background evidence tests.
- Affected documentation: model-test-code alignment and full-diagnostic repair
  guidance.
- Affected local operations: install sync and background test tier evidence
  reporting, without changing public FlowPilot protocol APIs.
