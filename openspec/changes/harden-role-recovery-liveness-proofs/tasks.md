## 1. Grounding And Failing Evidence

- [x] 1.1 Verify real FlowGuard import and record the relevant existing model/spec boundaries.
- [x] 1.2 Add targeted failing tests for stale recovery report transaction reuse, unknown role liveness, replacement-not-active lease proof, and compact daemon state output.
- [x] 1.3 Add or extend FlowGuard singleton/daemon model evidence for role recovery liveness proof hazards.

## 2. Recovery Proof Runtime

- [x] 2.1 Make role recovery ready-context validation require the latest transaction, affected role set, crew slot transaction markers, and host liveness proof.
- [x] 2.2 Make active role lookup reject unknown, missing, cancelled, completed, and timeout liveness even when an agent id or replacement decision exists.
- [x] 2.3 Make active-holder lease validation require current active host proof instead of treating replacement intent as proof.
- [x] 2.4 Make role recovery report writing and report reclaim expose separate recovery-requested, replacement-created, memory-seeded, and host-liveness-verified states.

## 3. Daemon Diagnostics And Output Shape

- [x] 3.1 Add bounded fatal-error diagnostics for daemon crashes, including MemoryError traceback metadata, current action/wait identity, and artifact size summary.
- [x] 3.2 Make routine CLI state output compact by default while preserving an explicit full-output option.

## 4. Validation, Sync, And Evidence

- [x] 4.1 Run targeted router runtime and singleton/daemon tests; fix failures without broad unrelated refactors.
- [x] 4.2 Run relevant FlowGuard model/check scripts, then run heavyweight meta/capability checks through the background artifact contract when required.
- [x] 4.3 Sync the repository FlowPilot skill to the local installed copy and run install audit/checks.
- [x] 4.4 Update OpenSpec tasks, adoption/KV evidence, and final git/worktree summary without reverting peer-agent changes.
