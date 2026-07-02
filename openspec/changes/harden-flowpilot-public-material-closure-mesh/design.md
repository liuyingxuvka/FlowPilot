## Context

FlowPilot already has a current-contract packet runtime, sealed body handling, `authorized_result_reads`, material artifact maps, terminal replay, terminal supplemental repair, break-glass, and extensive model/test infrastructure. The observed miss is not lack of infrastructure; it is unclear role-facing policy and incomplete coverage across existing surfaces.

The change must preserve the current ownership split:

- Runtime/Router owns mechanical validity, sealed body protection, packet/result identity, current run state, accepted-result projection, and terminal replay target validation.
- PM owns route, repair strategy, user-intent contract, and final ledger construction.
- FlowGuard Operator owns the current FlowGuard work order and explicit check items; it does not replace Reviewer judgment.
- Reviewer owns independent quality, evidence credibility, final user-intent satisfaction, and terminal pass/block judgment.

## Goals / Non-Goals

**Goals:**

- Make ordinary project/run files readable by all formal work roles unless the file is a sealed body.
- Keep sealed bodies protected by runtime authorization.
- Make PM repair packets and downstream reports close blocker items concretely with existing fields.
- Ensure final closure proves the current final artifact, public user-intent contract, FlowGuard terminal coverage, and terminal quality.
- Add model/test evidence for the full declared finite universe, not just example cases.
- Preserve current-contract minimality and avoid field sprawl.

**Non-Goals:**

- No compatibility aliases or legacy result-shape fallback.
- No new role type or parallel material-permission subsystem.
- No broad new runtime ledger family unless an existing record cannot express a required mechanical fact.
- No Controller body-reading authority.
- No novel/story-specific behavior; all rules apply to generic FlowPilot tasks.

## Decisions

1. Ordinary material policy is denylist-based.

   PM, Worker, Reviewer, and FlowGuard Operator may read files under the current project root and current run root unless the path is a sealed body. Runtime continues to mark startup/user-intake bodies, packet bodies, result bodies, PM decision bodies, Reviewer review bodies, and any `body_ref` with `sealed` or `requires_runtime_open` as sealed. This avoids fragile allowlists that miss relevant ordinary artifacts.

2. `material_artifact_map` is navigation and audit evidence, not permission.

   The map should help roles find important artifacts and help tests prove indexing freshness. It must not imply that unindexed non-sealed project/run files are forbidden. It must keep sealed body text excluded and surface sealed body refs only as metadata.

3. Blocker closure uses existing fields.

   PM uses current repair reason/resolution/context fields to state prior failure, required repair, and gate checks. Worker, FlowGuard Operator, and Reviewer use existing summaries, findings, blockers, and suggestion fields. No new top-level blocker-item schema is introduced in this change.

4. FlowGuard Operator is checklist/work-order strict, not final quality judge.

   A FlowGuard pass is invalid if the report answers only field shape, hashes, current-contract mechanics, or role boundary while leaving requested work-order/check items unanswered. But final product quality, user satisfaction, and acceptance sufficiency remain Reviewer responsibilities.

5. Terminal closure is product-first.

   Runtime must issue terminal replay targets for delivered product, root/user acceptance, final artifact hygiene, FlowGuard coverage governance, active acceptance items, route nodes, route mutations, parent/repair segments, and supplemental repairs as applicable. Reviewer terminal replay must cover every runtime-issued segment and block stale/superseded final projections.

6. Test coverage is a declared finite universe.

   ContractExhaustionMesh defines bounded axes and canonical bad cases; TestMesh owns shards and freshness; Model-Test Alignment maps each obligation to code contracts and tests. "Full Cartesian" means all declared finite axes and required interaction groups are covered, with explicit exclusions for unbounded natural-language variants.

## Risks / Trade-offs

- [Risk] Broad ordinary-file readability could be misread as permission to read sealed bodies by path.
  -> Mitigation: Prompt cards and tests state sealed body paths are metadata only unless runtime opens them for the role.
- [Risk] Material map no longer being an allowlist could reduce discipline.
  -> Mitigation: It remains required navigation/audit evidence for important artifacts and terminal closure, but not the source of read permission.
- [Risk] FlowGuard Operator may drift into Reviewer work.
  -> Mitigation: Cards explicitly separate work-order/checklist closure from final quality/user-intent judgment.
- [Risk] Cartesian coverage becomes unbounded.
  -> Mitigation: Tests declare finite axes, generated case ids, and scoped exclusions.
- [Risk] Dirty parallel work makes evidence stale.
  -> Mitigation: Keep edits scoped, run focused checks after each implementation group, rebuild topology and install sync before final closure.
