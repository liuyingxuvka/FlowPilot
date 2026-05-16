## 1. Model Hardening Gate

- [x] 1.1 Extend a focused FlowGuard model for invocation intent isolation.
- [x] 1.2 Add known-bad hazards for fresh startup attaching to one old run, fresh startup attaching when multiple parallel runs exist, fresh startup mutating an existing run, and ambiguous resume silently choosing current.
- [x] 1.3 Add safe scenarios for fresh startup creating a new run and explicit resume attaching to a selected existing run.
- [x] 1.4 Run focused FlowGuard checks before production edits and record that Meta/Capability checks are skipped by user direction.

## 2. Startup And Resume Runtime

- [x] 2.1 Inspect router/launcher entry points that distinguish `--new-invocation` from resume/default-target behavior.
- [x] 2.2 Patch fresh startup so existing active runs are discovered only as independent background context and cannot become the foreground target.
- [x] 2.3 Patch resume/default-target behavior so existing runs are used only after explicit resume intent or target selection.
- [x] 2.4 Update launcher-facing FlowPilot instructions to state the new-start versus resume distinction in plain terms.

## 3. Regression Tests

- [x] 3.1 Add runtime tests where current points to a running run and fresh startup creates a different run.
- [x] 3.2 Add runtime tests where multiple active runs exist and fresh startup creates another independent run without mutating the others.
- [x] 3.3 Add runtime tests where explicit resume can target an existing run, and ambiguous resume does not silently choose current.

## 4. Verification And Sync

- [x] 4.1 Run the focused FlowGuard checks after production edits.
- [x] 4.2 Run targeted runtime tests and install self-checks.
- [x] 4.3 Sync the installed local FlowPilot skill copy and verify freshness.
- [x] 4.4 Update FlowGuard adoption logs with commands, skipped heavy checks, findings, and residual risk.
- [x] 4.5 Recheck git status and preserve peer-agent work for final submission.
