## Why

FlowPilot currently has strong abstract FlowGuard models and many focused
runtime tests, but agent-driven workflows still rely on live AI behavior or
scattered fixtures for several end-to-end branches. This change adds a
deterministic way to replay fake PM, Worker, Reviewer, and officer actions
through the real packet/runtime/router surfaces so control-flow regressions are
caught before live runs.

## What Changes

- Add a synthetic agent trace replay capability for regression tests.
- Define reusable trace packages whose role outputs are fake but whose packet,
  result, hash, ledger, and router paths are real.
- Add positive and negative trace packs for the first critical surfaces:
  packet/result handoff, ACK-not-completion, sealed-body isolation, PM
  disposition, raw-result rejection, route mutation stale evidence, resume
  handoff, fixture evidence boundaries, and progress-only background evidence.
- Keep synthetic and fixture evidence explicitly separate from live project
  completion evidence.
- No breaking protocol or runtime behavior changes are intended.

## Capabilities

### New Capabilities

- `synthetic-agent-trace-replay`: deterministic replay of fake role actions
  through real FlowPilot control-plane APIs, with explicit synthetic/fixture
  evidence boundaries.

### Modified Capabilities

- None.

## Impact

- Affected tests: new trace replay tests plus targeted integration into
  existing packet/router/model-test alignment coverage.
- Affected support code: small test-only helpers under the FlowPilot test
  surface.
- Affected validation: focused unittest/pytest checks, FlowGuard
  model-test-alignment checks, and background model regressions where
  appropriate.
- Affected install flow: after source validation, the local installed
  FlowPilot skill must be synchronized and checked serially.
