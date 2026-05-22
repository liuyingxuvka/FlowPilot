# Design

## Approach

Use the existing full model coverage inventory as the source of truth for the
test backlog. The implementation should add a focused ordinary test suite that
is intentionally evidence-oriented:

1. Load `simulations/flowpilot_full_model_coverage_inventory_results.json`.
2. Assert that all known gap classes are assigned to a closure strategy.
3. For abstract model runners, run or inspect the associated model runner so
   ordinary tests mention and exercise the model boundary.
4. For replay/scoped/skipped gaps, assert the scoped boundary explicitly so it
   remains visible and cannot be reported as passed.
5. For not-OK or unparsed runners, assert their current diagnostic state until
   separate implementation fixes make them green.

## Test Strategy Categories

- `runner-exec`: run the model runner in a subprocess and assert it emits
  parseable JSON with the expected status.
- `result-contract`: inspect a current result artifact when the runner is too
  broad or already executed by the sweep.
- `scoped-boundary`: assert that skipped/scoped replay evidence is visible and
  not counted as pass evidence.
- `failure-sentinel`: assert that a known not-OK or unparsed runner remains a
  tracked failure, preventing accidental overclaim.

## FlowGuard Boundary

The new tests strengthen evidence visibility. They do not change model
semantics, production route state, or live run data. If a test exposes a real
bug, that bug should be reported as an implementation/model gap for a later
repair unless the fix is small, clearly safe, and inside the same evidence
boundary.

## Validation Plan

Run:

- syntax checks for new tests/scripts;
- the new focused coverage-gap test suite;
- the full inventory builder;
- FlowGuard model-test alignment;
- OpenSpec strict validation.

Heavy parent regressions may remain out of scope unless production behavior or
parent model code changes.
