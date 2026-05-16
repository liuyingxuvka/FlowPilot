## 1. Model And Risk Gate

- [x] 1.1 Write the FlowGuard risk intent and adoption note for the daemon heartbeat liveness boundary.
- [x] 1.2 Extend the focused daemon/patrol model to cover `ok`, `check_liveness`, alive-after-delay, dead-after-delay, and attach-first recovery.
- [x] 1.3 Run the focused FlowGuard check and inspect counterexamples before production edits.

## 2. Runtime Behavior

- [x] 2.1 Add heartbeat age fields and five-second threshold metadata to daemon monitor/status projection.
- [x] 2.2 Change patrol/monitor output so heartbeat age above five seconds returns `check_liveness` instead of `daemon_repair_or_restart`.
- [x] 2.3 Add Controller liveness-check instruction text: inspect process/lock/status, continue if alive, recover only if stopped.
- [x] 2.4 Preserve attach-first recovery when a live daemon appears during recovery.

## 3. Tests And Regression

- [x] 3.1 Add runtime tests for heartbeat under threshold, delayed heartbeat with live daemon, delayed heartbeat with dead daemon, and active daemon found during recovery.
- [x] 3.2 Run focused pytest coverage for patrol/daemon recovery behavior.
- [x] 3.3 Run required FlowGuard model checks affected by project-control flow in background with stable artifacts.

## 4. Sync And Review

- [x] 4.1 Update install/self-check coverage if new model artifacts or result files are introduced.
- [x] 4.2 Sync the installed local FlowPilot skill from this repository and verify the install.
- [x] 4.3 Review the combined diff, including compatible peer-agent changes, before final commit preparation.
