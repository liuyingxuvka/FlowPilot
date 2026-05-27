## Why

FlowPilot already has focused fake-AI package tests, hard-gate red-team cells,
control-plane canaries, and end-to-end synthetic chaos replay. The remaining
confidence gap is narrower but important: a test can pass while still bypassing
the same Router CLI/runtime boundaries a real run uses. The user specifically
needs proof that prepared fake AI work packages can drive a real FlowPilot run
from startup to terminal closure through real Router waits, cards, packets,
role-output envelopes, daemon/resume state, proof gates, and terminal cleanup.

This change adds a stricter rehearsal layer above the existing coverage. It is
not a claim that live AI semantic quality is guaranteed. It is a claim that, if
AI actors obey FlowPilot's runtime protocols, the control plane has executable
coverage for correct flows, common bad packages, compounded errors, recovery
paths, and standard-state restoration.

## What Changes

- Add a real-Router dry-run rehearsal coverage matrix that names required
  phases, fake AI artifacts, real Router entrypoints, ACK/receipt gates,
  allowed-event boundaries, recovery expectations, and final-state evidence.
- Add matrix tests that reject overclaims: missing ACK/receipt gates, invented
  external events, direct state mutation, progress-only background proof,
  incomplete terminal state, and live-AI semantic-quality guarantees.
- Add an executable rehearsal test that drives a prepared fake AI work package
  through startup, material scan, route planning, packet dispatch, active-holder
  result submission, PM/reviewer disposition, evidence quality, final ledger,
  terminal replay, PM closure, and lifecycle terminalization.
- Add a CLI boundary test that exercises real `start`, `state`, `next`, `apply`,
  `record-event`, and `run-until-wait` commands with prepared fake role output.
- Add a control-plane recovery rehearsal that combines dead-daemon resume,
  duplicate heartbeat idempotency, and progress-only background proof rejection
  before final proof is accepted.
- Register this rehearsal as FlowGuard Model-Test Alignment evidence and as a
  fast-tier gate so future changes cannot silently drop it.
- Refresh OpenSpec, FlowGuard adoption, generated matrix result, alignment
  result, and local install evidence after implementation.

## Capabilities

### New Capabilities

- `real-router-dry-run-rehearsal`: Defines full fake-AI package rehearsal
  scenarios that must use real Router/runtime entrypoints and produce runtime
  receipts before claiming coverage.
- `real-router-rehearsal-coverage-matrix`: Defines required matrix metadata and
  known-bad rejection rules for whole-run fake-AI rehearsal evidence.

### Modified Capabilities

- `end-to-end-synthetic-agent-chaos-replay`: Existing full-flow chaos tests
  become supporting evidence for this stricter rehearsal layer.
- `control-plane-failure-canary`: Existing lock/daemon/resume/proof canaries
  become supporting evidence for compounded recovery rehearsal rows.
- `flowpilot-test-tiering`: The fast tier gains a new rehearsal matrix and
  focused runtime rehearsal tests.
- `flowpilot-model-test-alignment`: Router loop/daemon alignment gains a
  distinct obligation for real-Router dry-run rehearsal evidence.

## Impact

- Affected tests: new real-Router dry-run rehearsal matrix and runtime tests;
  fast-tier assertions; model-test alignment assertions.
- Affected simulations: new rehearsal matrix script/results and refreshed
  model-test alignment results.
- Affected docs/records: OpenSpec artifacts and FlowGuard adoption log.
- Affected install surface: repository-owned local FlowPilot skill sync and
  local install audit.
- Out of scope: remote push, public release, tag, deployment, OpenSpec archive,
  and guarantees about real AI reasoning quality outside runtime protocols.
