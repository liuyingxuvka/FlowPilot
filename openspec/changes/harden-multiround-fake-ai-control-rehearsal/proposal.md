## Why

FlowPilot already rejects many single-step fake AI mistakes, but the recent control-plane failure showed that a bad PM repair can still look valid while producing a dead wait. We need a repeatable multi-round rehearsal gate that exercises bad package, bad repair, corrected repair, stale evidence, and producer-proof paths before serious FlowPilot work starts.

## What Changes

- Add a multi-round fake-AI control rehearsal capability that requires stateful bad-then-repair sequences rather than single-boundary rejection rows.
- Extend rehearsal matrices and runtime tests so PM repair decisions that lack a concrete event producer are treated as known-bad rows and executable replay cases.
- Register the new rehearsal evidence in fast validation and model-test alignment so future changes cannot silently drop the control-plane coverage.
- Keep the live-AI quality boundary explicit: prepared fake AI packages prove control-plane handling, not semantic quality of live model output.

## Capabilities

### New Capabilities
- `multiround-fake-ai-control-rehearsal`: Covers prepared fake AI work-package runs that intentionally include multiple sequential control-plane errors and prove rejection, recovery, producer evidence, and legal continuation.

### Modified Capabilities
- `executable-repair-transactions`: PM repair transaction requirements now require multi-round rehearsal evidence for no-producer repair waits and corrected producer-backed repairs.

## Impact

- Affected OpenSpec artifacts: new change specs and tasks for multi-round fake AI rehearsal.
- Affected simulations: real-Router dry-run matrix, end-to-end synthetic chaos matrix, repair transaction/model-test alignment evidence.
- Affected tests: real-Router rehearsal matrix tests, E2E synthetic chaos replay tests, model-test alignment tests, fast-tier registration tests.
- Affected validation: focused unit tests, matrix generation, FlowGuard repair transaction checks, model-test alignment, fast tier, Meta/Capability background regressions, and local install sync checks.
