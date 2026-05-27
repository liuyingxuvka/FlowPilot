## Why

FlowPilot has accumulated useful but expensive validation: broad pytest
collection, router runtime domains, install/public checks, smoke checks, and
heavy FlowGuard regressions. A flat "run everything" approach makes routine
work wait on ten-to-thirty-minute jobs and also lets accidental root-level
pytest collection pull in backup or temporary tests.

This change adds a layered test strategy so routine edits get a fast,
scoped signal, domain changes can run focused child suites, and release-level
or legacy full regressions stay visible without blocking every local loop.

## What Changes

- Scope default pytest collection to the real `tests/` tree and exclude
  backup, temp, cache, and local control directories.
- Add a tiered test runner with explicit tiers for collection, fast checks,
  router-domain slices, integration checks, release checks, and legacy full
  regressions.
- Add a FlowGuard TestMesh-style model that rejects known bad tiering hazards:
  foreground long regressions, hidden skips, stale child evidence, background
  progress reported as completion, missing exit artifacts, and release gates
  hidden from routine runs.
- Keep slow model and release regressions runnable in the background with
  stable log artifacts instead of tying up the foreground thread.
- Register the new runner, model, result, and tests in install checks so local
  source and installed skill validation can see the new validation surface.

## Capabilities

### New Capabilities

- `tiered-flowpilot-test-validation`: Defines parent/child test tiers and the
  evidence required before each tier can be trusted.
- `background-test-regression-evidence`: Requires background regressions to
  produce stdout, stderr, combined output, exit-code, and metadata artifacts
  before completion can be claimed.

### Modified Capabilities

- None. Runtime protocol behavior, persisted JSON shapes, router behavior, and
  release scope remain unchanged.

## Impact

- Affected tooling: pytest configuration, tiered test runner, install checks.
- Affected models: a new focused FlowGuard test-tiering model and result.
- Affected tests: new focused unit tests for tier command planning and
  background artifact contracts.
- No production runtime, protocol, dependency, release, or deployment change.
