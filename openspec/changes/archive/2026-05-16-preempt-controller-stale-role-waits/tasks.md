## 1. FlowGuard Model Gate

- [x] 1.1 Add a Router-ready foreground-wait hazard to the role-output/runtime or control-plane model.
- [x] 1.2 Add source/prompt checks that require Controller guidance to return to Router before foreground role waits.
- [x] 1.3 Run the focused FlowGuard model check and confirm the new hazard is detected.

## 2. Runtime And Protocol Implementation

- [x] 2.1 Update FlowPilot skill guidance so after relay/status boundaries Controller immediately calls Router or `run-until-wait`.
- [x] 2.2 Update Controller and resume cards to prohibit foreground role/chat waits when Router-ready evidence or notices exist.
- [x] 2.3 Add or update focused router runtime tests for Router-ready preemption and bounded liveness-only waits.

## 3. Verification And Sync

- [x] 3.1 Run focused tests and model checks for changed areas.
- [x] 3.2 Run required broader FlowPilot checks for project-control and capability impact.
- [x] 3.3 Sync repo-owned FlowPilot assets into the installed local skill and verify install freshness.
- [x] 3.4 Stage and commit the local repository changes without pushing remotely.
