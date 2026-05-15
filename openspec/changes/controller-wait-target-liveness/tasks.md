## 1. Model And Contract

- [ ] 1.1 Extend the persistent Router daemon FlowGuard model with wait classes, ACK reminder/blocker timing, report/result reminder liveness probes, Controller-local self-audit, and known-bad stale-liveness hazards.
- [ ] 1.2 Run the focused persistent Router daemon model checks and preserve updated result evidence.

## 2. Runtime Implementation

- [ ] 2.1 Extend Router daemon status and Controller standby payloads with `current_wait` wait-target metadata.
- [ ] 2.2 Implement ACK wait reminder and ten-minute blocker behavior using controller-visible metadata only.
- [ ] 2.3 Implement report/result reminder cycles that require a fresh target-role liveness check before continuing standby.
- [ ] 2.4 Implement Controller-local wait self-audit behavior without sending reminders.
- [ ] 2.5 Route unhealthy wait targets into the existing Router blocker/PM recovery path without letting Controller replace roles or advance the route.

## 3. Prompt And Protocol Guidance

- [ ] 3.1 Update Controller guidance so it follows wait-target metadata, does not trust cached liveness, and does not remind itself for Controller-local actions.
- [ ] 3.2 Update protocol references or install checks that assert Controller standby behavior.

## 4. Verification, Sync, And Commit

- [ ] 4.1 Add or update focused runtime tests for ACK reminder/blocker, report reminder liveness, lost-role blocker, and Controller-local self-audit.
- [ ] 4.2 Run focused tests, OpenSpec validation, install checks, sync/audit checks, and skip `run_meta_checks.py` plus `run_capability_checks.py` by user request.
- [ ] 4.3 Sync the local installed FlowPilot skill version from the repository.
- [ ] 4.4 Commit the repository, including compatible parallel-agent work already present in the worktree.
