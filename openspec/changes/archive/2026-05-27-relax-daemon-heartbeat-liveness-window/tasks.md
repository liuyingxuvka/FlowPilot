## 1. Runtime And Prompt

- [x] 1.1 Change the daemon heartbeat liveness window and daemon lock stale constants to thirty seconds and update reason labels to avoid five-second wording.
- [x] 1.2 Update startup heartbeat/manual-resume prompt text so Controller checks daemon liveness only after a thirty-second delayed heartbeat.

## 2. FlowGuard And Tests

- [x] 2.1 Update the daemon liveness FlowGuard model, runner labels, hazard text, and generated result JSON for the thirty-second window.
- [x] 2.2 Update focused foreground/startup daemon tests for the new threshold metadata and delayed-heartbeat behavior.
- [x] 2.3 Run focused FlowGuard and unit tests for daemon liveness, patrol timer, and startup daemon behavior.

## 3. Sync And Evidence

- [x] 3.1 Refresh repository-owned installed FlowPilot skill content and run install sync checks.
- [x] 3.2 Run broader model/test regressions in background artifact mode where available, then inspect exit artifacts before reporting pass/fail.
- [x] 3.3 Review git status and stage/commit only this heartbeat-window change if local git sync is requested and unrelated peer edits remain isolated.
