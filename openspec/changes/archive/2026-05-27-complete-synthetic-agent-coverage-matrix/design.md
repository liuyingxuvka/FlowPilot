## Context

FlowPilot already has FlowGuard family plans, model-test alignment diagnostics,
fast/router test tiers, and a first synthetic trace replay helper. The current
state is strong enough to prove several high-risk packet and evidence paths,
but not strong enough to claim that every currently modeled, testable AI action
branch has an explicit replay or test owner. The latest full diagnostic also
keeps three deferred structure-split findings visible, which prevents
`full_coverage_ok` from becoming true even though release convergence is green.

This design treats synthetic traces as deterministic control-flow evidence, not
as proof that a live AI wrote semantically good work. The implementation must
preserve that boundary while improving coverage accounting and closing the
known FlowGuard blockers.

## Goals / Non-Goals

**Goals:**

- Create a single machine-readable coverage matrix for all current FlowPilot
  model-test alignment obligations and synthetic AI trace branches.
- Make every currently testable branch declare a primary evidence owner:
  synthetic trace replay, ordinary focused runtime test, model/test alignment
  evidence, or background artifact contract.
- Add tests that fail when an obligation is missing branch-kind coverage,
  evidence ownership, or a valid trace/evidence status.
- Extend synthetic trace replay where real FlowPilot APIs can exercise a branch
  without relying on live AI output.
- Close or explicitly fail the remaining structure-split diagnostics so final
  coverage claims cannot hide them.
- Keep install synchronization serialized after source validation.

**Non-Goals:**

- Do not claim synthetic traces prove live AI semantic quality, product
  correctness, human approval quality, or final live project completion.
- Do not replace existing runtime tests with synthetic traces when ordinary
  focused tests already own a branch better.
- Do not weaken FlowGuard diagnostics or thresholds to make coverage pass.
- Do not absorb or revert unrelated peer-agent changes.

## Decisions

1. **Coverage matrix is generated from declared FlowGuard alignment plans plus
   explicit synthetic branch rows.**

   This avoids a stale hand-written list of branches. The generated matrix can
   consume existing `ModelTestAlignmentPlan` obligations and pair them with
   additional synthetic trace expectations that ordinary tests do not express.
   The alternative was to add more standalone tests only, but that would keep
   the "what is covered?" question scattered across files.

2. **Synthetic traces support control-flow gates only.**

   Matrix rows must distinguish `control_flow`, `evidence_boundary`,
   `background_artifact`, and `ordinary_runtime` coverage from live completion
   evidence. This prevents fixture/synthetic traces from accidentally closing
   live project gates.

3. **Gating tests validate ownership, not just happy-path execution.**

   A coverage row is valid only when it names model family, obligation id,
   branch kind, evidence owner, command/test id, and status. Missing ownership
   is a failure even if another broad parent test passes.

4. **Structure split blockers are fixed with compatibility-preserving helper
   extraction.**

   The three current blockers are line-threshold structure findings on existing
   runtime surfaces. They should be split by extracting cohesive helpers while
   preserving public import paths and existing tests. The alternative of marking
   them explicitly skipped is reserved for table-only or declarative surfaces,
   which these are not.

5. **Validation runs from narrow to broad.**

   Focused synthetic/coverage tests run first, then model-test alignment, fast
   tier, background meta/capability regressions, and finally install sync/audit.
   Background progress logs are liveness only; final exit/meta artifacts are the
   completion evidence.

## Risks / Trade-offs

- **Risk: The matrix becomes another stale artifact.** → Generate most rows
  from existing model-test alignment declarations and test the matrix itself.
- **Risk: Synthetic traces overclaim live correctness.** → Require explicit
  evidence category and non-live boundary assertions in the matrix tests.
- **Risk: Structure splits introduce behavior changes.** → Keep existing
  modules as compatibility facades, extract only cohesive helpers, and run
  focused runtime/model tests before broader tiers.
- **Risk: Peer agents write during validation.** → Recheck git state before
  edits, before install sync, and before final commit; rerun affected checks if
  owned files change.
- **Risk: Background regressions take time.** → Run them through the existing
  background artifact contract and inspect final exit/meta files before making
  final claims.
