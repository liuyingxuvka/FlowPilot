## 1. OpenSpec And Evidence Contract

- [x] 1.1 Create proposal, design, capability specs, and task checklist for
  the protocol stress-testing change.
- [x] 1.2 Validate the OpenSpec change strictly before implementation
  confidence is claimed.

## 2. Protocol Stress Assets

- [x] 2.1 Add readable stress-testing documentation beside the existing AI
  project protocol assets.
- [x] 2.2 Record stress scenario families, FlowGuard target choices, and
  TestMesh child evidence expectations in the asset documentation.

## 3. Fake-Agent Stress Harness

- [x] 3.1 Add a deterministic fake-agent stress model that represents
  multi-round leases, packets, route versions, reviews, FlowGuard targets,
  evidence generations, and final closure.
- [x] 3.2 Add scripted multi-round scenarios for happy-path replacement,
  ACK-only timeout, closed-agent late output, route mutation stale output,
  weak review, self-review, stale evidence, wrong FlowGuard target, and final
  closure gap.
- [x] 3.3 Add seeded random long-run checks that report reproducible seed,
  step, event, and state summaries on violations.
- [x] 3.4 Add historical bad-case replay cases for known FlowPilot failure
  families.

## 4. FlowGuard And TestMesh Evidence

- [x] 4.1 Use the real FlowGuard package to explore the stress model and enforce
  the acceptance invariant.
- [x] 4.2 Generate a stress result artifact with named child evidence rows for
  focused kernel compatibility, deterministic scenarios, seeded random runs,
  historical replay, FlowGuard exploration, background regressions, and install
  surface parity.
- [x] 4.3 Ensure the parent stress gate fails if any required child row is
  failed, stale, skipped, progress-only, missing, or not run.

## 5. Tests And Install Surface

- [x] 5.1 Add focused pytest coverage for stress scenario names, all bad-path
  blocks, replacement success, seeded random reproducibility, historical replay,
  and TestMesh evidence rows.
- [x] 5.2 Update install-check inventory so the new stress assets, runner,
  result artifact, and tests are part of local source/install parity.
- [x] 5.3 Update version/changelog and FlowGuard adoption notes for the stress
  testing capability.

## 6. Validation, Sync, And Local Git

- [x] 6.1 Run focused protocol checks, stress checks, focused pytest, and strict
  OpenSpec validation.
- [x] 6.2 Run Meta and Capability model regressions under the background log
  contract and inspect final artifacts before claiming pass.
- [x] 6.3 Sync the repo-owned skill into the local installed skill, then run
  install audit and install checks sequentially.
- [x] 6.4 Review final git scope, stage intended files only, and create a local
  git commit without push, tag, deploy, or release.
