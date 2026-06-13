## Context

FlowPilot already contains the required high-quality completion flow:
product architecture, root contract, route skeleton, node acceptance, Worker
execution, FlowGuard evidence, Reviewer checks, PM disposition, final route-wide
ledger, final requirement evidence matrix, terminal backward replay, and
closure. The remaining risk is mechanical looseness at the end of the flow:
some final rows can look covered when the runtime sees an id, even if the
underlying review, FlowGuard order, or validation record is blocked, stale, or
failed.

The repository rule is current-contract only. This design must not add legacy
shape acceptance, old-route migration, newest-run fallback, repo-root fallback,
or a second quality workflow. All repairs use the existing packet/result/gate
surfaces and current runtime records.

## Goals / Non-Goals

**Goals:**

- Make final quality evidence checks inspect the referenced record, not only
  the presence of a reference id.
- Keep blocked review, stale FlowGuard, failed validation, and incomplete
  terminal replay evidence visible as final blockers.
- Preserve the existing FlowPilot flow and final artifacts while tightening
  their acceptance logic.
- Add focused negative tests and FlowGuard/model-test evidence for the bug
  classes this pass hardens.
- Sync the installed skill after validation.

**Non-Goals:**

- No new FlowPilot process route, role family, ledger family, packet kind, or
  compatibility lane.
- No support for old result shapes, old route evidence, historical promotion,
  or automatic migration from earlier construction-period artifacts.
- No product/project-specific quality rules for ProjectRadar or any other
  target project.
- No release, tag, push, deploy, or public publication.

## Decisions

1. Harden existing final-gate builders instead of adding a new quality layer.

   The final route-wide ledger and final requirement evidence matrix already
   own completion visibility. They should call small helper predicates for
   accepted review, current FlowGuard, and passing validation evidence. This
   avoids a parallel final-quality framework.

2. Treat evidence validity as record-level mechanical validation.

   Runtime/router owns the mechanical question: does the referenced record
   exist, belong to the current route/generation, and have a passing status
   with no blockers? Reviewer and FlowGuard still own semantic quality and
   modeling judgment; runtime only refuses to count invalid records as proof.

3. Require terminal replay target parity.

   Runtime already issues terminal backward replay segment targets. A submitted
   terminal replay result must include exactly those segment ids, with no
   missing, duplicate, or unexpected ids, before it can close the replay gate.
   This keeps the existing terminal replay path but prevents partial replay
   from satisfying closure.

4. Preserve current-contract repair behavior.

   When final evidence is invalid, closure remains blocked and PM/Controller
   must use the existing reissue, repair, route mutation, quarantine, or stop
   paths. The runtime must not translate invalid historical evidence into valid
   current evidence.

## Risks / Trade-offs

- [Risk] Existing in-progress local runs may contain blocked review ids in a
  route node's evidence list.
  → Mitigation: This is intended current-contract behavior for new evidence.
  Blocked rows stay historical and must be repaired or superseded by current
  passing evidence rather than silently counted.

- [Risk] Final gate checks become stricter and expose previously hidden
  incomplete work.
  → Mitigation: Focused negative tests document each stricter behavior. The
  failure mode is a visible final blocker, not a fallback path.

- [Risk] Broad regressions are slow.
  → Mitigation: Run focused tests in foreground and use the repository's
  background log contract for heavyweight Meta/Capability checks, then inspect
  final exit artifacts before claiming completion.
