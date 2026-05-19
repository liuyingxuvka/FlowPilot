## Context

FlowPilot keeps several durable records for one logical action: `router_state.json`, Controller receipts, packet ledgers, packet batches, PM role-work indexes, officer lifecycle indexes, scheduler rows, wait reminder state, and result envelopes. The incident showed that these records can diverge even when every individual file write is atomic.

The upgraded FlowGuard model `flowpilot_control_plane_state_consistency_model.py` now rejects the observed same-class states and rejects repair candidates that only patch one symptom. The only passing candidate is a shared durable reconciliation barrier before next-action computation, plus stale-save protection and true-holder recipient-busy semantics.

## Goals / Non-Goals

**Goals:**

- Reconcile durable control-plane facts before Router exposes new Controller work or passive waits.
- Keep receipt-fold effects complete and idempotent across flags, batch lifecycle, PM role-work indexes, and Router projections.
- Terminalize superseded PM role-work requests and remove them from active busy sources.
- Treat recipient roles as busy only when the role truly holds unresolved work.
- Prevent daemon stale snapshots from erasing newer foreground event/state changes.
- Keep wait reminders deduplicated by stable durable identity.
- Fix result body self-check projection so valid `# Contract Self-Check` and `## Contract Self-Check` sections are reflected in envelope metadata.

**Non-Goals:**

- Do not redesign packet runtime, role authority, prompt cards, startup UI, or Cockpit.
- Do not read sealed packet/result bodies in Controller or Router reconciliation.
- Do not run repo-wide formatters or broad structure cleanup.
- Do not push to GitHub, publish a release, or change dependencies.

## Decisions

1. **One reconciliation barrier owns cross-ledger projection.**

   Before next-action providers decide work, Router must rebuild or validate the current projection from durable sources. The barrier should be narrow and idempotent: it reads known ledgers and updates only derived Router projection fields and lifecycle fields that have explicit durable evidence.

2. **Receipt folds must include lifecycle side effects.**

   A fold for `relay_material_scan_results_to_pm` is incomplete if it sets only `material_scan_results_relayed_to_pm`. It must also advance the active material batch to `results_relayed_to_pm` and refresh the Router projection from the durable batch.

3. **Supersession is a terminal lifecycle transition.**

   When PM registers request B with `supersedes_request_id=A`, request A must become `superseded` or `canceled`, must leave active request lists, and must not count as a target-role busy source. Replacement metadata should be visible in the new packet envelope/index.

4. **Recipient busy means true holder, not stale open row.**

   Dispatch can wait when the target role has a relayed packet, active holder lease, open ACK obligation, or unresolved result obligation. A stale open request that is still Controller-held and unrelayed is a control-plane cleanup/reconciliation case, not a reason to wait for the target role.

5. **Daemon writes must be freshness-aware.**

   Atomic file replacement prevents torn JSON but not lost updates. Daemon save paths must detect when `router_state.json` changed after the daemon snapshot, reload/merge durable facts, and then save or retry.

6. **Reminder and metadata projections are derived facts.**

   Wait reminders should use stable wait identity and persisted last-reminder data. Result-envelope self-check metadata should be derived from the result body with compatible heading recognition.

## Risks / Trade-offs

- **Over-broad reconciliation:** keep the barrier scoped to current-run known ledgers and explicit lifecycle contracts.
- **Masking invalid evidence:** missing or contradictory evidence must produce a control blocker or repair lane, not silently set success flags.
- **Breaking parallel role work:** dispatch busy logic must still block truly active role-held work.
- **Lost peer changes:** edits must avoid unrelated README/design-skill changes already present in the worktree.

## Migration Plan

1. Validate the new control-plane state consistency model and keep the observed hazards red against weaker candidates.
2. Add focused runtime tests for material result receipt fold lifecycle, PM role-work supersession, unrelayed old request dispatch gate behavior, daemon stale-save protection, wait reminder dedupe, and self-check heading projection.
3. Implement the smallest production helpers needed for those tests: lifecycle-aware receipt folds, PM role-work supersession terminalization, true-holder dispatch busy logic, freshness-aware router-state saves, stable reminder cooldown, and self-check heading parsing.
4. Run focused tests and FlowGuard model checks.
5. Start heavy meta/capability checks through `tmp/flowguard_background/` and inspect exit artifacts.
6. Sync repo-owned FlowPilot into the local installed skill and run install audit/check.
7. Review local git state and preserve unrelated peer edits.
