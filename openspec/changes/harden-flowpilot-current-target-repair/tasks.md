## 1. OpenSpec And FlowGuard Grounding

- [x] 1.1 Create current-target OpenSpec proposal, design, spec, and task plan.
- [x] 1.2 Verify FlowGuard package/schema/project audit and keep evidence fresh.
- [x] 1.3 Route implementation through existing-model preflight, model-miss
      review, development-process flow, and model-test alignment.

## 2. Runtime Current-Target Mechanics

- [x] 2.1 Add current-target helper logic using existing packet, result,
      blocker, gate, repair transaction, and route-node records.
- [x] 2.2 Supersede explicitly replaced `result_submitted` packets after repair
      or reissue, without retiring ordinary pending submissions.
- [x] 2.3 Prevent active blockers and semantic blocker creation from inheriting
      stale old subjects as repair targets.
- [x] 2.4 Prevent FlowGuard/review/PM dispatch from selecting noncurrent,
      blocked, superseded, quarantined, stale-route, or missing-responsibility
      packets.
- [x] 2.5 Make final-preflight reject active blockers, next actions, PM gates,
      and staged effects that reference noncurrent targets.

## 3. PM Decision And Recovery Contracts

- [x] 3.1 Keep PM repair decision parsing strict top-level `decision` only.
- [x] 3.2 Update PM repair decision packet instructions to show the exact valid
      JSON shape and reject nested wrappers.
- [x] 3.3 Reissue fresh PM repair decision packets when prior PM decision
      packets are blocked or noncurrent.
- [x] 3.4 Remove recovery responsibility fallback; missing current packet
      responsibility becomes a control-plane blocker.

## 4. FlowGuard Models And Test Mesh

- [x] 4.1 Extend control-plane friction model for replaced `result_submitted`
      packets, stale active blocker targets, blocked PM decision reuse, fallback
      responsibility, and same-family staged-effect expansion.
- [x] 4.2 Extend validation PM gate model for staged-effect convergence and
      no future committed-state review demands.
- [x] 4.3 Update model-test alignment evidence for current-target repair
      obligations.
- [x] 4.4 Add fake/bad packet fixtures or tests for old packet references,
      nested PM wrappers, blocked PM decision reuse, stale route versions, and
      missing responsibility.

## 5. Runtime Tests

- [x] 5.1 Add core runtime tests for current pending `result_submitted` still
      receiving FlowGuard/review while replaced submissions are superseded.
- [x] 5.2 Add tests for active blocker old-target rejection and PM decision
      packet reissue after block.
- [x] 5.3 Add tests for no fallback responsibility and final-preflight stale
      reference blockers.
- [x] 5.4 Add staged-effect same-family loop regression tests.
- [x] 5.5 Keep historical 53-packet success replay green.

## 6. Validation, Sync, And Git

- [x] 6.1 Run focused pytest suites for core runtime, high-standard control
      flow, lifecycle guard, historical replay, router/runtime, entrypoint, and
      fake/bad packet coverage.
- [x] 6.2 Run focused FlowGuard model checks and model-test alignment.
- [x] 6.3 Run long meta/capability regressions in background and inspect stable
      artifacts before claiming pass.
- [x] 6.4 Rebuild/check FlowGuard project topology after model/test/runtime
      changes.
- [x] 6.5 Sync local installed FlowPilot skill and Gate/install surfaces, then
      run install check and local install sync audit.
- [x] 6.6 Run final git status, stage intended changes, create local git commit,
      and record KB postflight.
