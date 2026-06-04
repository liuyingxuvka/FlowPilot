## 1. OpenSpec And FlowGuard Grounding

- [x] 1.1 Create staged-effect OpenSpec artifacts and validate the change.
- [x] 1.2 Verify FlowGuard package/schema/version and project audit.
- [x] 1.3 Reuse existing FlowPilot model families and route the implementation
      through DevelopmentProcessFlow with the AGENTS minimal-repair rule.

## 2. Runtime Mechanics

- [x] 2.1 Sync the known installed-runtime `issue_flowguard_packet` fix back
      into repository runtime source.
- [x] 2.2 Add submission-time mechanical validation for route plan and repair
      decision families without compatibility aliases or prose fallback.
- [x] 2.3 Add lightweight staged-effect helpers on existing result/gate records.
- [x] 2.4 Stage node acceptance plan/context binding until FlowGuard, Reviewer,
      and system closure accept the PM result.
- [x] 2.5 Stage `mutate_route` PM decision effects until PM gate closure commits
      the route mutation exactly once.
- [x] 2.6 Preserve packet kind and route scope for `sender_reissue` and
      `collect_more_evidence`.
- [x] 2.7 Add current-runtime stopped-blocker recovery command and ensure plain
      `resume` does not clear semantic blockers.
- [x] 2.8 Remove or hard-block FlowGuard API fallback evidence paths.

## 3. Runtime Cards And Prompts

- [x] 3.1 Update PM node acceptance plan instructions to describe staged effects
      and current-result submission without accepted-field assumptions.
- [x] 3.2 Update Reviewer node acceptance review instructions to review the real
      artifact and quality, not runtime-owned field mechanics.
- [x] 3.3 Update FlowGuard operator instructions to review process/state/evidence
      risks from the staged effect without demanding future committed fields.
- [x] 3.4 Update PM repair/route mutation/resume instructions for staged route
      effects, type-preserving reissue, and explicit stopped-blocker recovery.

## 4. Tests And Models

- [x] 4.1 Add or update core runtime tests for early route-plan rejection,
      staged node-plan effects, type-preserving reissue, stopped blockers, and
      no FlowGuard fallback evidence.
- [x] 4.2 Add or update high-standard/recursive runtime tests for staged route
      mutation and delayed node plan/context commit.
- [x] 4.3 Add or update entrypoint tests for stopped-blocker recovery.
- [x] 4.4 Add or update card instruction coverage for mechanical vs substantive
      review ownership.
- [x] 4.5 Update focused FlowGuard models/runners for staged effects, known-bad
      future-state assumptions, premature mutation, type-loss reissue,
      stopped-blocker dead-end, and fallback evidence.

## 5. Validation, Sync, And Local Git

- [x] 5.1 Run focused pytest suites for runtime, high-standard, recursive route,
      entrypoint, and card instruction coverage.
- [x] 5.2 Run focused FlowGuard model checks for runtime, validation PM gate,
      route hard gate, prework FlowGuard gate, packet lifecycle, work order, and
      decision liveness.
- [x] 5.3 Run or complete background Meta and Capability regressions and inspect
      their stable log artifacts before claiming pass.
- [x] 5.4 Rebuild and check project topology after prompt/model/runtime/test
      changes.
- [x] 5.5 Sync repository-owned installed FlowPilot skill, then run local install
      sync audit and install check serially.
- [x] 5.6 Record FlowGuard adoption/postflight evidence and KB observation when
      reusable lessons appear.
- [x] 5.7 Stage only intended repository changes and create a local git commit.
