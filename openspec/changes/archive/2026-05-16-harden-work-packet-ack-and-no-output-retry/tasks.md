## 1. Specification And Model Coverage

- [x] 1.1 Add OpenSpec scenarios for universal post-ACK continuation and no-output reissue before role recovery.
- [x] 1.2 Add FlowGuard prompt-boundary coverage for work ACK continuing to formal output submission.
- [x] 1.3 Add FlowGuard scheduler coverage for no-output reissue before role recovery and unavailable-role recovery.

## 2. Runtime Prompt Hardening

- [x] 2.1 Strengthen runtime-generated card ACK post-ACK policy.
- [x] 2.2 Strengthen work-card post_ack text across the runtime kit.
- [x] 2.3 Strengthen packet body and runtime packet identity boundary text.

## 3. Router Wait-Target Reissue

- [x] 3.1 Add no-output wait-target classification separate from unavailable-role liveness faults.
- [x] 3.2 Add Router-owned no-output replacement row creation with durable replacement-before-supersede ordering.
- [x] 3.3 Add a bounded retry budget and PM/control-blocker escalation when the budget is exhausted.
- [x] 3.4 Preserve existing role recovery for unavailable roles.

## 4. Verification And Sync

- [x] 4.1 Add focused runtime tests for no-output reissue and liveness recovery separation.
- [x] 4.2 Run focused FlowGuard checks and focused runtime tests.
- [x] 4.3 Record the user-approved skip for heavyweight FlowGuard meta/capability regressions because they are too heavy for this pass.
- [x] 4.4 Sync repository-owned FlowPilot skill to the local installed version and verify source freshness.
- [x] 4.5 Review the combined worktree, preserving compatible parallel-agent work for final git submission.
