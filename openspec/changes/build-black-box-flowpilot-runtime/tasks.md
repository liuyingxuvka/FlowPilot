## 1. OpenSpec And Contract

- [x] 1.1 Create proposal, design, capability spec, and task checklist for the
  clean black-box runtime.
- [x] 1.2 Validate the OpenSpec change strictly before implementation
  confidence is claimed.

## 2. Runtime Assets

- [x] 2.1 Add the clean runtime package under
  `skills/flowpilot/assets/ai_project_runtime/`.
- [x] 2.2 Add a readable runtime README that explains the ledger, leases,
  packets, FlowGuard work orders, review, console, reuse boundaries, and
  completion gates.
- [x] 2.3 Keep old assets as reference material only; do not import old runtime
  state or fixed-role startup requirements.

## 3. Ledger, Lease, Packet, And Router

- [x] 3.1 Implement the serializable black-box ledger.
- [x] 3.2 Implement dynamic agent leases with ACK, progress, timeout, close,
  replacement, and stale-output rejection.
- [x] 3.3 Implement sealed task/result packet helpers with envelope/body hash
  checks.
- [x] 3.4 Implement deterministic router next-action selection.

## 4. FlowGuard, Review, Closure, And Console

- [x] 4.1 Implement FlowGuard work-order scheduling from modeled target to
  selected skill.
- [x] 4.2 Implement independent review gates that reject self-review, weak
  review, wrong route, stale evidence, wrong FlowGuard target, and invalid
  result shape.
- [x] 4.3 Implement final backward closure from user goal to current route,
  accepted packets, review, FlowGuard evidence, validation, and gaps.
- [x] 4.4 Implement a minimal safe console/status projection that does not leak
  sealed bodies.

## 5. FlowGuard Models And Simulations

- [x] 5.1 Add a FlowGuard development-process model for the implementation
  order and release evidence gates.
- [x] 5.2 Add a runtime scenario runner for replacement success, wrong
  FlowGuard target, self-review, stale route output, stale evidence, ACK-only
  timeout, and console isolation.
- [x] 5.3 Write TestMesh-style result artifacts that separate routine rows from
  release-only background/install rows.

## 6. Tests And Regressions

- [x] 6.1 Add focused pytest coverage for runtime assets, leases, packets,
  router decisions, review gates, FlowGuard target selection, closure, and
  console isolation.
- [x] 6.2 Run existing protocol kernel and stress checks.
- [x] 6.3 Run runtime development and runtime scenario checks.
- [x] 6.4 Run focused pytest and relevant install inventory tests.
- [x] 6.5 Run background Meta and Capability regressions and inspect final
  artifacts before release confidence is claimed.

## 7. Install Sync, Version, And Local Git

- [x] 7.1 Update install inventory so new runtime assets, simulations, result
  artifacts, and tests are required.
- [x] 7.2 Update version and changelog.
- [x] 7.3 Sync the repo-owned FlowPilot skill into the local installed skill,
  then run install audit and install checks.
- [x] 7.4 Review final git scope, stage intended files only, and create a local
  git commit without remote push, tag, deploy, or release.
