## Context

FlowPilot already has several local gate mechanisms: system-card ACK pending returns, startup pre-review ACK joins, current-node result review, PM result disposition, node completion ledgers, route mutation supersede/stale evidence handling, and final route-wide ledger checks. These mechanisms are not yet unified around the moment that matters most for reviewer quality: before a reviewer starts judging a startup gate or current node, the review package must be stable and local pending work must already be resolved or explicitly classified.

The key boundary is scope locality. A reconciliation for startup or a current node must not sweep future nodes, sibling nodes, or route-wide closure obligations. It only proves that the object being reviewed will not be changed by hidden obligations inside the current scope.

## Goals / Non-Goals

**Goals:**
- Add a focused model and runtime rule for current-scope pre-review reconciliation.
- Require startup and current-node reviewer work to wait until local review-affecting obligations are resolved or explicitly carried forward.
- Require obligations created by the review itself to close before node/gate completion.
- Require scopes without final review to reconcile before boundary transition.
- Preserve explicit carry-forward for intentionally deferred work, with target scope and reason.
- Keep checks focused and skip heavyweight meta/capability regressions by user request.

**Non-Goals:**
- Do not clear route-wide, future-node, sibling-node, or terminal-closure obligations from a local reconciliation.
- Do not make ACKs count as semantic work completion.
- Do not introduce a separate global wait table that duplicates existing ledgers.
- Do not rewrite all existing gate logic in this change.
- Do not run `simulations/run_meta_checks.py` or `simulations/run_capability_checks.py`.

## Decisions

1. Model the rule as a local reconciliation join, not a boundary cleanup.
   - Rationale: the reviewer needs a stable review package before review begins; boundary transition is too late to protect review quality.
   - Alternative considered: clean at node exit only. Rejected because the reviewer could still pass a moving target.

2. Scope every reconciliation by current startup gate or active node.
   - Rationale: local review should not mutate future work or siblings. Future work may only appear as an explicit carry-forward with target scope and join condition.
   - Alternative considered: scan all route pending items before each review. Rejected because it overblocks unrelated scopes and risks deleting valid future obligations.

3. Reuse existing durable sources first.
   - Rationale: pending card returns, controller action ledger, run-state pending actions, node completion ledgers, and route frontier already define much of the live state.
   - Alternative considered: add a fully separate obligation database immediately. Rejected for this step because it would drift unless all writers are migrated at once.

4. Add a small Router-owned reconciliation summary for review/block explanations.
   - Rationale: when review is blocked, Controller and roles need to see which local item is blocking and what action closes it.
   - Alternative considered: rely only on individual wait actions. Rejected because the new rule needs one auditable local-scope reason.

5. Treat review-created obligations as part of the same scope.
   - Rationale: a reviewer pass/report can itself create ACK, receipt, PM disposition, or completion-ledger obligations. The scope is not clean until those close.
   - Alternative considered: allow review output to cross automatically. Rejected because it would recreate the same hidden-tail problem after review.

## Risks / Trade-offs

- [Risk] A local reconciliation may block too aggressively if an obligation is truly future work.  
  Mitigation: support explicit `carried_forward` records with reason, target scope, owner, and join condition.

- [Risk] Existing ledgers may not have enough scope metadata for every pending item.  
  Mitigation: start with concrete known current-scope sources and mark unsupported sources as out of scope in the focused model; extend metadata in later changes when a real writer requires it.

- [Risk] Focused checks do not prove every route-wide behavior.  
  Mitigation: run targeted FlowGuard and Router runtime tests, record skipped heavyweight checks clearly, and keep final route-wide ledger checks separate.

## Migration Plan

1. Add focused FlowGuard model coverage for local pre-review reconciliation.
2. Add Router helpers for current-scope local pending item detection and reconciliation summary.
3. Enforce the helper at reviewer-start/reviewer-pass and no-final-review transition points that are reachable in current runtime tests.
4. Add focused tests for startup, current-node review, review-created obligations, and local-scope-only behavior.
5. Sync local installed FlowPilot skill and run install/source freshness checks.

## Open Questions

- Which future scope transfer fields should become canonical once more obligation writers are migrated?
- Should current-scope reconciliation eventually be written to a dedicated durable ledger for every node, or remain a derived summary until enough writers are migrated?
