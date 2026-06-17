## Context

FlowPilot already has a high-standard closure path: frozen contract, route
nodes, acceptance-item registry, final route-wide ledger, final requirement
matrix, terminal backward replay, and PM completion approval. Recent work also
hardens final evidence validity and terminal replay blocker repair.

The remaining gap is terminal convergence. A final Reviewer may discover that
the delivered work still misses implementation, validation, evidence strength,
or latent high-standard work required to satisfy the user's original goal. The
current repair paths can reissue packets or mutate route nodes, but there is no
single PM-authored supplemental contract that records these terminal additions,
binds them to repair nodes, and limits the number of terminal repair rounds.

The repository rule is current-contract only. This design must preserve the
original frozen contract, avoid compatibility surfaces, and reuse the existing
packet/result/gate/runtime ledgers rather than creating a second workflow.

## Goals / Non-Goals

**Goals:**

- Preserve the original frozen contract unchanged.
- Add a PM-owned supplemental repair contract layered on top of the original
  contract for terminal gaps that are necessary to satisfy the original user
  goal at high standard.
- Convert structured Reviewer terminal gap rows into repair items, repair
  nodes, and terminal replay targets.
- Require repair nodes/subnodes to follow existing FlowPilot gate rules.
- Enforce a hard three-round terminal repair cap in runtime.
- Make final ledger, final requirement matrix, final preflight, and terminal
  backward replay consume supplemental repair evidence before completion.
- Add FlowGuard, model-test alignment, field lifecycle, focused unit, and fake
  E2E evidence.

**Non-Goals:**

- No mutation of the original frozen contract.
- No unlimited repair-loop continuation after round three.
- No new role family, old-router fallback, legacy field alias, missing-field
  default, prose parser, or compatibility migration.
- No release, push, tag, deploy, or public publication.
- No broad structure split beyond what the supplemental repair feature needs.

## Decisions

1. Add a supplemental contract layer instead of editing the frozen contract.

   The runtime records `terminal_supplemental_repair` state and individual
   `supplemental_repair_contracts`. Each contract cites the original contract
   and terminal Reviewer gap report. This keeps original acceptance evidence
   auditable while allowing PM to add required terminal repair work.

2. Treat latent original-goal high-standard gaps as repair items, not optional
   suggestions.

   If Reviewer finds work that is necessary to satisfy the user's original
   goal at FlowPilot's high standard, PM must either add it as a supplemental
   repair item or record a blocking terminal stop. Nonblocking improvements can
   still be recorded separately, but they do not close active repair gaps.

3. Use existing route/node packet mechanics for repair execution.

   Supplemental repair contracts create repair nodes/subnodes with
   `supplemental_contract_id` and `repair_item_ids`. Those nodes reuse current
   route mutation, node acceptance, Worker, FlowGuard, Reviewer, PM
   disposition, final ledger, and terminal replay behavior.

4. Runtime owns the three-round hard cap.

   Rounds one and two may end with terminal Reviewer gap recheck and PM repair
   contract update. Round three is the final attempt. If closure is still not
   clean after round three, runtime records `repair_rounds_exhausted` and
   returns terminal stopped status instead of dispatching another Reviewer or
   PM repair packet.

5. Final closure consumes both original and supplemental contract evidence.

   Final route-wide ledger and final requirement matrix include supplemental
   contract rows, repair item closure rows, and unresolved blockers. Terminal
   backward replay targets include supplemental contract and repair item
   segments.

6. Keep field additions explicit and current-schema only.

   New persisted fields are added under current ledger and current result
   contracts only. Missing supplemental fields mechanically block or reissue
   the current packet; runtime does not infer them from old fields or prose.

## Risks / Trade-offs

- [Risk] The supplemental contract becomes a parallel workflow.
  -> Mitigation: no new role family or alternate execution loop; repair nodes
  reuse existing route/node mechanics and terminal ledgers.

- [Risk] The repair loop keeps extending because Reviewer finds more issues.
  -> Mitigation: runtime enforces an absolute three-round cap. Round three ends
  in complete or exhausted.

- [Risk] PM over-adds new scope under the repair contract.
  -> Mitigation: every repair item must state why it is necessary for the
  original user goal. True unrelated future work is recorded as nonblocking or
  stopped, not required for current closure.

- [Risk] Final closure appears clean while supplemental items remain open.
  -> Mitigation: final ledger, final requirement matrix, final preflight, and
  terminal replay all consume supplemental repair rows and unresolved counts.

- [Risk] Existing broad regressions are slow in a dirty worktree.
  -> Mitigation: add focused foreground checks first, use background log
  contracts for broad/heavy suites, and inspect exit artifacts before claiming
  completion.

## Migration Plan

This is a current-contract addition. New runs that reach terminal supplemental
repair use the new fields and output contracts. Existing historical runs are
not migrated into a valid current supplemental repair state. If an old run lacks
the supplemental fields, runtime treats them as absent until a current terminal
gap path creates them.

## Open Questions

None for implementation. The hard round limit is fixed at three and is not
PM-overridable.
