## Context

FlowPilot already has `review_window` metadata on Reviewer packets, structured
authorized-result reads, subject stage evidence, contract-exhaustion coverage,
and a `ContractDrivenFakeAIResponder`. The current hardening proves important
representative flows, but it does not yet prove that every runtime-issued
Reviewer flow has a complete material window and matching fake-AI Cartesian
coverage.

The design must extend existing surfaces only. It must not add a second
Reviewer lane, a second fake-AI framework, compatibility aliases, prose parsing,
or PM authority to bypass Reviewer blockers.

## Goals / Non-Goals

**Goals:**

- Give every active Reviewer flow a stable `review_flow_id` and a declared
  completeness row.
- Make the declared row checkable against the actual emitted packet envelope and
  `current_handoff_contract.review_window`.
- Generate ContractExhaustionMesh/current-contract cells from the declared
  rows, including mutation cells for missing or wrong subject, stage, material,
  authorized reads, future-stage boundary, and repair-return path.
- Extend fake-AI rehearsals so Reviewer and PM behavior mistakes are generated
  from the same declared rows.
- Keep the ordinary path simple: Reviewer blocks, PM creates or selects repair
  work, repaired evidence returns to Reviewer, and repeated unrepaired failures
  use the existing threshold path.

**Non-Goals:**

- Do not prove live AI semantic quality or every possible natural-language
  Reviewer mistake.
- Do not grant Reviewer, PM, or Controller broad sealed-body access outside the
  existing authorized-read and break-glass rules.
- Do not introduce a new runtime packet kind, legacy fallback shape, or
  compatibility translation layer.
- Do not make PM an appeal authority over Reviewer quality decisions.

## Decisions

1. **Represent completeness as a generated model surface, not prose.**

   Add a review-window completeness model/table that declares expected rows for
   current review flows. The rows become the source for tests and matrix cells,
   while Reviewer cards remain explanatory.

2. **Use stable flow ids derived from current runtime families.**

   Each row names the current subject/result family, lifecycle stage, review
   kind, required window paths, required materials, and PM repair return. Tests
   fail when runtime can issue a review packet whose family/stage pair is not
   covered by a row.

3. **Keep `review_window` as the minimal runtime-checkable window.**

   Existing `subject_stage_evidence_matrix`, `authorized_result_reads`,
   `current_handoff_contract`, `gate_kind`, and `reviewer_review_scope` remain
   the first sources. The `review_window` summarizes and binds them so tests can
   inspect one machine-owned surface.

4. **Extend the existing fake AI responder.**

   The responder will gain review-window-aware behavior profiles instead of
   separate fixtures. Each profile records the expected runtime reaction:
   reject, block, reissue, PM repair/recheck, no glass break before threshold,
   or break-glass at threshold.

5. **Treat matrix readiness as necessary but not sufficient.**

   ContractExhaustionMesh generates cell ids and oracles. Focused tests and
   model-test alignment prove those cell ids are consumed by current code/tests
   before a broad claim is allowed.

## Risks / Trade-offs

- **Matrix explosion** -> Keep axes bounded to declared review flows, declared
  material states, declared mutation families, declared fake-AI profiles, and
  retry-count classes.
- **Over-scoping Reviewer** -> Add only material needed for the current review
  stage, and explicitly list forbidden future-stage demands.
- **False confidence from synthetic traces** -> Keep confidence boundary as
  non-live control-plane evidence and preserve live semantic quality as out of
  scope.
- **Drift between runtime and model rows** -> Add tests that compare emitted
  review packets to completeness rows and fail on orphan runtime review flows
  or row paths not present in emitted packets.
- **Peer-agent conflicts** -> Keep edits scoped to review-window/fake-AI/matrix
  artifacts and avoid the separate in-progress PM-visible-summary change.

## Migration Plan

1. Add completeness declarations and generated cell helpers.
2. Add fake-AI review-window profiles and expected outcome oracles.
3. Add focused runtime tests and matrix tests.
4. Run FlowGuard model checks and focused unit tests.
5. Refresh topology, install sync, and version/release artifacts after
   validation passes.
