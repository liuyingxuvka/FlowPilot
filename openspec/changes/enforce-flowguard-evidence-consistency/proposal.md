## Why

Live FlowPilot runs exposed a model miss: a FlowGuard result could use the current
packet shape, set top-level `passed: true`, and still contain machine-readable
child evidence or self-check fields that said the work was blocked. Runtime
accepted the top-level pass before the contradiction reached the FlowGuard
operator or Reviewer boundary, so scoped green tests gave false confidence.

## What Changes

- Add a hard current-contract consistency gate for FlowGuard result packets:
  top-level pass is legal only when machine-readable self-check and child
  evidence status also pass.
- Treat evidence consistency as runtime/router mechanical validity, not a
  Reviewer quality judgement.
- Extend FlowGuard field, information-flow, and model-test alignment coverage
  so child evidence status projects into the FlowGuard result outcome, work
  order decision, and Reviewer handoff.
- Extend fake AI and historical/synthetic replay tests with current-shaped
  contradictory FlowGuard results that must fail before Reviewer dispatch.
- Dispose repair-open blockers when route mutation quarantines their repair
  packets, and bind that repair transaction hazard to runtime evidence.
- Keep old generic decision/summary, fallback prose, and compatibility paths
  rejected; this change introduces no legacy acceptance path.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `flowpilot-packet-review-flow`: FlowGuard result acceptance must pass a hard
  evidence-consistency gate before a Reviewer packet can be issued.
- `flowguard-boundary-test-alignment`: FlowGuard model-test alignment must bind
  evidence-consistency obligations to owner code contracts and ordinary tests.
- `end-to-end-synthetic-agent-chaos-replay`: fake AI chaos replay must include
  current-shaped internally contradictory FlowGuard outputs and prove they are
  rejected without route progress.
- `synthetic-agent-trace-replay`: synthetic trace packs must replay the same
  contradictory FlowGuard result family through real packet/result APIs.

## Impact

- Runtime packet-result validation for `flowguard_check` result families.
- FlowGuard field contract, information-flow alignment, and model-test
  alignment models/results.
- Fake e2e and focused runtime unit tests.
- Historical or synthetic fixture coverage for the observed blocked-child-report
  failure class.
- Local install/FlowGuard adoption evidence because the project FlowGuard record
  is upgraded to the installed 0.42.0 toolchain.
