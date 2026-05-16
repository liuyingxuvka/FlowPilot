## 1. Paper Plan And Model Scope

- [x] 1.1 Record the detailed optimization order table.
- [x] 1.2 Record the risk/bug checklist and required FlowGuard detection.
- [x] 1.3 Verify real FlowGuard import and inspect peer-agent dirty files.
- [x] 1.4 Validate this OpenSpec change before production edits.

## 2. FlowGuard Before Runtime Edits

- [x] 2.1 Extend the two-table async scheduler model with scheduler progress
      classes: true barrier, phase handoff, parallel obligation, and local
      dependency.
- [x] 2.2 Add known-bad hazards for banner/display global barriers, heartbeat
      global barrier, role-spawn global barrier, premature role-dependent work,
      early Reviewer review, true-barrier demotion, duplicate nonblocking row
      issue, stale startup receipt/bootstrap state, and reconciliation status
      downgrade.
- [x] 2.3 Run focused scheduler checks and prove the known-bad hazards are
      detected.
- [x] 2.4 Run the candidate optimized plan through the focused scheduler model
      and confirm it passes.
- [x] 2.5 Run the daemon microstep lifecycle model if touched or needed for the
      startup receipt/bootstrap drift slice.

## 3. Runtime Slice 1: Classification And Queue Continue

- [x] 3.1 Add Router action progress classification helpers without changing
      Controller authority.
- [x] 3.2 Update daemon queue-filling decisions so parallel obligations and
      local dependencies do not globally stop unrelated queueing.
- [x] 3.3 Preserve true barriers for user input, terminal actions, control
      blockers, resume/rehydration gates, current-scope waits, and non-startup
      ACK/result waits.
- [x] 3.4 Run focused runtime tests for queueing after banner/heartbeat/role
      obligations and for true barriers still stopping.

## 4. Runtime Slice 2: Startup Open-Row Skip And Local Dependencies

- [x] 4.1 Teach startup bootloader selection to skip already scheduled/open
      nonblocking obligations without marking them complete.
- [x] 4.2 Add role-slot local dependency checks for role-dependent card delivery
      and review freshness work.
- [x] 4.3 Add duplicate/idempotency protections for nonblocking startup
      obligations across daemon retries.
- [x] 4.4 Run targeted tests for no duplicate rows and no premature
      role-dependent work.

## 5. Runtime Slice 3: Receipt And Join Hardening

- [x] 5.1 Ensure consumed startup Controller receipts update bootstrap flags,
      clear pending state, reconcile Router scheduler rows, and compute the
      next row or true barrier.
- [x] 5.2 Prevent scheduler row reconciliation status from downgrading after a
      later receipt sync.
- [x] 5.3 Ensure startup pre-review reconciliation blocks Reviewer review until
      all startup obligations and startup-local blockers are clean.
- [x] 5.4 Run targeted tests for startup receipt drift, reconciliation
      monotonicity, and startup review gating.

## 6. Final Verification, Sync, And Git

- [x] 6.1 Run focused FlowGuard checks and targeted runtime tests for all
      touched behavior.
- [x] 6.2 Record FlowGuard adoption results, including that meta/capability
      heavy checks were skipped by explicit user request.
- [x] 6.3 Sync the local installed FlowPilot skill from the repository and
      audit source freshness.
- [x] 6.4 Review the working tree with peer-agent changes preserved.
- [x] 6.5 Stage and commit the local git result if validation passes.
