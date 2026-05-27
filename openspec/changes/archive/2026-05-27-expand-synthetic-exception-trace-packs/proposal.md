## Why

The current synthetic agent trace replay package proves the highest-risk packet,
ACK, body-boundary, raw-result, fixture, and background-artifact cases. The
remaining real-world failures are concentrated in exceptional control-plane
paths rather than normal happy paths: control blockers, PM repair decisions,
resume ambiguity, stale route evidence, role-output authority, material repair
generation, and dirty terminal closure.

This change expands synthetic replay from "representative fake AI actions" into
a governed exception-trace package set. High-risk exceptional branches should
have an explicit fake AI replay row whenever the branch can be exercised through
real FlowPilot runtime APIs. Branches that cannot be replayed synthetically must
carry a concrete reason and stay covered by ordinary runtime/model evidence.

## What Changes

- Add P0 synthetic replay packages for control blocker reissue/escalation, PM
  repair decision accept/reject paths, fatal blocker rejection, resume
  preemption, and ACK-only semantic-work boundaries.
- Add P1 synthetic replay packages for route mutation stale proof, PM package
  disposition envelope authority, controller boundary repair escalation,
  material repair generation/stale flags, and dirty terminal ledger completion
  blockers.
- Extend the synthetic coverage matrix with risk tier, replay requirement, and
  replay status fields so high-risk branches cannot silently rely only on broad
  ordinary tests.
- Keep synthetic and fixture evidence scoped to control-flow/runtime behavior;
  never claim live AI semantic quality or live project completion from fake
  packages.
- Keep the local installed FlowPilot skill synchronized after implementation
  and run model/test/install evidence in the correct order.

## Capabilities

### Modified Capabilities

- `synthetic-agent-coverage-matrix`: now distinguishes ordinary runtime
  evidence from high-risk exception branches that require synthetic replay or an
  explicit non-replayable reason.

## Impact

- Affected tests: synthetic agent trace replay tests, synthetic coverage matrix
  tests, model-test alignment tests, router control-blocker/resume/route/
  material/terminal focused suites, and fast tier.
- Affected FlowGuard artifacts: model-test alignment evidence JSON, synthetic
  coverage matrix JSON, and any model evidence consumed by the fast tier.
- Affected install flow: repository-owned `flowpilot` skill must be synced
  after source validation and audited serially.
