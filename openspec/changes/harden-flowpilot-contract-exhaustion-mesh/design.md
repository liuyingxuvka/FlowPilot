## Context

FlowPilot already has FlowGuard models for packet/result contracts, synthetic
agent traces, layered boundary coverage, model-test alignment, blocker repair
information flow, and Controller break-glass. The latest observed failure was
not caused by an unbounded AI semantic judgment. It was a finite control-plane
contract gap: a FlowGuard reissue lost packet-owned evidence policy, result
acceptance and work-order decision diverged, and downstream review continued
without a matching FlowGuard evidence read.

The current repair must preserve the new-only runtime rule. It must not add
legacy fallbacks, old-shape aliases, or prose guessing. Recovery remains
current-run, current-packet, current-result, owner-scoped, and evidence-backed.

## Goals / Non-Goals

**Goals:**

- Derive a finite matrix from current FlowPilot packet, result, evidence,
  reviewer, blocker, repair, and loop contracts.
- Exercise missing-body, missing-field, wrong-type, wrong-target, missing-read,
  evidence-path, manifest, reissue-inheritance, and no-delta repeat variants
  through real runtime contracts.
- Attach history-derived failure families from known friction, live-run replay,
  hard-gate, install, and synthetic-chaos evidence to the same matrix.
- Make every generated variant produce one explicit oracle outcome: accepted,
  blocked, reissued with concrete feedback, downstream review stopped,
  root-cause loop counted, or GlassBreak alarmed as a non-success condition.
- Ensure parent closure consumes matching current child evidence ids and does
  not accept split-brain FlowGuard states.
- Ensure every matrix-emitted evidence owner is registered and consumed by a
  current TestMesh child suite before downstream synthetic coverage, MTA, or
  layered proof claims can pass.
- Bind new model obligations to runtime code contracts and tests through
  Model-Test Alignment and TestMesh.
- Treat current live-run replay as a hard acceptance gate: coverage inventory
  must not retain `live_runtime_or_state_findings`, and ModelMesh/process
  liveness must not project `lifecycle_guard=control_plane_stuck` as
  continuable.

**Non-Goals:**

- Do not run or repair target-project WorldGuard/SkillGuard work.
- Do not make synthetic matrix evidence count as live target-project completion
  or human quality evidence.
- Do not create compatibility shims for old packet/result shapes.
- Do not replace existing FlowGuard model families; extend and reattach them.

## Decisions

1. **Generate from contracts, not hand-written lists.**

   The matrix should read declared current contract families and fixture
   builders, then apply reusable mutations. This keeps future fields from being
   invisible until a human remembers to add a bespoke test.

   Alternative considered: add only the observed WorldGuard regression. That
   would fix one path but leave the same-class finite field/path space weak.

2. **Use runtime oracle expectations as the authority.**

   Each generated case should state the expected runtime disposition. The
   generator is not a replacement for runtime validation; it is a producer of
   concrete bad inputs and expected outcomes.

   Alternative considered: keep the matrix as a documentation table. That would
   not prevent green claims from hiding unexecuted branches.

3. **Treat FlowGuard evidence consistency as one parent closure.**

   Result acceptance, packet outcome, work-order decision, evidence artifact,
   reviewer authorized read, reviewer manifest, and system validation must all
   refer to the same current FlowGuard proof chain. Any disagreement is a
   control-plane blocker before downstream review can progress.

   Alternative considered: let system validation catch late mismatches. The
   observed miss shows that this creates confusing PM repair packets after the
   wrong reviewer path has already opened.

4. **Track GlassBreak by root cause as an alarm, not as a success path.**

   Repeated same-root-cause evidence-chain loops can change surface labels
   across FlowGuard, reviewer, and system-validation stages. The loop detector
   should retain a stable root-cause key for no-delta control-plane repeats.
   Five repeated same-root blockers prove the alarm is reachable, but a formal
   rehearsal that reaches GlassBreak remains a failure until the normal repair
   route is fixed.

   Alternative considered: lower the existing surface-family threshold. That
   would increase false break-glass on ordinary repair progress and still miss
   renamed blockers.

5. **Keep scope current-contract and minimal.**

   Runtime changes should prefer existing packet/result/blocker/reissue/review
   surfaces. Add state only when the matrix proves no existing surface can
   express the required repair feedback or root-cause loop identity.

6. **Treat matrix output consumption as a hard handoff.**

   Each generated contract-exhaustion row names a required evidence owner. The
   parent TestMesh must derive the required child-suite set from those owners,
   register each suite, and fail on any unregistered, stale, or zero-cell
   child. Synthetic coverage, Model-Test Alignment, and layered proof consume
   that TestMesh output instead of trusting row existence alone.

7. **Do not baseline live blockers as expected green.**

   A live-run replay finding means the current repo state or current run needs
   repair or explicit terminal disposition. Tests may assert that the finding is
   detected, but final coverage inventory and full-leaf evidence must require
   zero current live-runtime blockers.

## Risks / Trade-offs

- **Matrix becomes too broad or slow** -> Partition through TestMesh into fast
  routine cells and release/background cells, with explicit freshness.
- **Generated cases drift from real contracts** -> Generate from current
  contract declarations and fail when a required contract family lacks a
  fixture builder.
- **False GlassBreak escalation** -> Require no-delta evidence and stable
  root-cause identity; ordinary repair progress resets or scopes the loop.
- **GlassBreak-as-success overclaim** -> Treat GlassBreak as an alarm only;
  accepted rehearsals must repair before the threshold.
- **Matrix rows not consumed downstream** -> Derive TestMesh child suites from
  `required_evidence_owner` values and fail on unregistered owners.
- **Detected live blocker becomes a permanent accepted baseline** -> Keep
  `live_runtime_or_state_findings` in the hard-blocking gap class set and add
  regression tests for current `control_plane_stuck` projection.
- **Overclaiming synthetic proof** -> Specs classify matrix evidence as
  control-plane regression evidence only.
- **Parallel agent edits stale evidence** -> DevelopmentProcessFlow must record
  changed artifacts and rerun minimum affected checks before completion.

## Migration Plan

1. Add OpenSpec requirements and tasks for contract exhaustion, parent closure,
   break-glass root-cause loops, synthetic coverage integration, and diagnostic
   reporting.
2. Inventory existing contract builders, models, tests, and FlowGuard evidence
   runtime paths.
3. Add focused model/test machinery for the matrix and closure obligations.
4. Apply minimal runtime fixes exposed by the observed miss and generated
   same-class cases.
5. Rerun targeted tests, affected FlowGuard model checks, topology build/check,
   install checks, and local installed-skill sync.

Rollback is normal git revert of this change set. No persisted user project
state migration is required because the change targets runtime validation and
new matrix evidence, not historical run compatibility.

## Open Questions

- Which existing fixture builders can cover all current packet/result families,
  and which families need minimal builders added?
- Which generated cells are routine-fast enough for local validation versus
  release/background TestMesh evidence?
