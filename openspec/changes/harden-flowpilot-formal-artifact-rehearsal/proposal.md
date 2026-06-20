## Why

Live FlowPilot runs exposed a model-miss class where a role can submit a valid
result body while omitting, misplacing, or under-filling a runtime-required
formal artifact such as `flowguard_evidence.json`. Existing fake-AI coverage
treated those artifacts as helper-written happy-path files, so the matrix did
not catch unclear reissue instructions, missing PM repair context, or repeated
mechanical artifact loops that should reach break-glass on the fifth same
failure.

## What Changes

- Extend the synthetic fake-AI coverage matrix to exercise formal artifact
  lifecycle failures as first-class Cartesian axes, not helper-hidden setup.
- Require runtime reissue packets for formal artifacts to identify the missing
  artifact, target path, required internal fields, allowed values, and whether
  body-only resubmission is insufficient.
- Ensure PM repair packets for formal FlowGuard failures carry the already
  modeled formal evidence path and PM-actionable failed-check summary from the
  existing current-contract surfaces.
- Count same-family mechanical formal-artifact failures toward the existing
  break-glass threshold without converting them into semantic blockers or
  adding compatibility/fallback acceptance.
- Add historical live-run replay coverage for the WorldGuard failure class so
  future green claims must prove the observed body-plus-artifact loop is
  closed.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `synthetic-agent-coverage-matrix`: Add formal-artifact lifecycle axes,
  fake-AI responder fault modes, feedback-clarity oracles, and same-failure
  retry/glassbreak cells.
- `flowpilot-artifact-authority`: Require runtime-owned formal artifacts to be
  projected, validated, and repaired through the current packet path with no
  body-only or old-path fallback.
- `controller-break-glass-repair`: Extend break-glass threshold coverage to
  repeated same-family mechanical formal-artifact loops while preserving the
  normal repair path for attempts 1-4.

## Impact

- Runtime packet/result contract checks and reissue packet construction.
- Fake-AI end-to-end rehearsal helpers and matrix tests.
- PM repair packet projection for FlowGuard failure details.
- Focused runtime tests, historical live-run replay tests, and FlowGuard
  model/test alignment evidence.
- Local install sync and repository version evidence after validation.
