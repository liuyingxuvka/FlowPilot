## 1. Baseline And Scope

- [x] 1.1 Confirm repository, remote, peer-agent, OpenSpec, and FlowGuard baseline.
- [x] 1.2 Validate this OpenSpec change strictly before runtime edits.

## 2. FlowGuard Route Repair Model

- [x] 2.1 Add or extend focused FlowGuard coverage for route repair/replacement topology, stale evidence, frontier rewrite, sibling replacement, replay, and completion blocking.
- [x] 2.2 Run the focused route repair/replacement model and inspect known-bad hazards.

## 3. Runtime And Tests

- [x] 3.1 Harden route mutation activation so return, supersede, and sibling replacement strategies preserve explicit topology and stale evidence disposition.
- [x] 3.2 Add focused runtime tests for sibling replacement, stale evidence reuse blocking, replacement frontier activation, and final-ledger blocking before replay.

## 4. Public Boundary, Docs, Version, And Install

- [x] 4.1 Update README, HANDOFF, CHANGELOG, VERSION, install checks, and relevant release/privacy docs.
- [x] 4.2 Run public release/privacy preflight and record Meta/Capability regressions as skipped by user request.
- [x] 4.3 Sync the local installed FlowPilot skill and audit installed freshness.

## 5. Verification, Git, And KB

- [x] 5.1 Run focused model, route/runtime, release, install, smoke, and OpenSpec validation checks without Meta/Capability.
- [x] 5.2 Re-check worktree for peer-agent overlap, stage, commit, and push the branch to origin without tag/release/deploy.
- [x] 5.3 Run KB postflight and record any reusable maintenance lesson.
