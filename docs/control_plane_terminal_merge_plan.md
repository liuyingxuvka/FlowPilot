# Control-Plane Terminal Merge Plan

This plan records the implementation scope for making FlowPilot control-plane
ledgers terminal-state monotone. It exists so the repair can proceed in small
verified steps without narrowing the fix to the first observed ACK symptom.

## Goal

All control-plane ledgers that decide whether route work can continue must use
one shared rule:

> For the same scoped identity, a terminal record wins. Duplicate, late, or
> replayed inputs may update audit metadata, but they must not downgrade the
> main control state or create duplicate side effects. A genuinely new scoped
> identity must still be processed normally.

## In-Scope Ledger Families

| ID | Ledger family | Identity boundary | Terminal proof | Duplicate or late input behavior | New identity behavior |
| --- | --- | --- | --- | --- | --- |
| L1 | Card ACK pending/completed return | `return_kind`, `delivery_attempt_id`, `card_return_event` | `status=resolved`, `resolved_at`, matching `completed_returns` row | Audit-only; preserve resolved pending status and completed proof | Normal pending/check/resolve flow |
| L2 | Bundle ACK pending/completed return | `return_kind`, `card_bundle_id`, `card_return_event` | `status=resolved`, `resolved_at`, matching `completed_returns` row | Audit-only; incomplete late ACK cannot downgrade resolved bundle | Normal bundle pending/check/recovery flow |
| L3 | Gate pass/block records | `gate_id`, `route_version`, `decided_by_role` | pass/accepted terminal decision for that gate identity | Audit-only; stale block cannot reactivate passed gate | Normal handling for a different gate identity |
| L4 | Control blocker and resolution records | `blocker_id`, or same blocker source when superseding | `resolution_status`, `resolved_at`, `superseded_by_blocker_id` | Audit-only; resolved/superseded blocker cannot become active again | New blocker may become active and supersede older compatible blockers |
| L5 | PM control-blocker repair decision | `control_blocker_id`, `repair_transaction_id` | `pm_repair_decision_status=recorded`, committed repair transaction | Already-recorded/audit-only; no duplicate transaction or blocker | New blocker or new transaction identity is accepted |
| L6 | Repair transaction/generation outcome | `repair_transaction_id`, `packet_generation_id`, outcome event | committed/success/superseded generation status | Old generation failure is audit-only after newer terminal success | New generation outcome is processed under its own generation |
| L7 | Result return and PM/reviewer disposition | `request_id`/`packet_id`/`result_hash`, plus disposition event identity | PM/reviewer disposition recorded for the scoped result | Audit-only; duplicate result return cannot reopen wait | New result identity is processed normally |

## Implementation Checklist

| Step | Change | Files likely touched | Done when |
| --- | --- | --- | --- |
| 1 | Strengthen the FlowGuard terminal-state model so every row in the ledger-family table has a safe path and a known-bad hazard. | `simulations/flowpilot_terminal_state_monotonicity_model.py`, `simulations/run_flowpilot_terminal_state_monotonicity_checks.py` | Model detects every risk in the risk table and the safe plan passes. |
| 2 | Add a small shared terminal-merge helper for control records. | `skills/flowpilot/assets/flowpilot_router.py` and/or `skills/flowpilot/assets/card_runtime.py` | Helper answers: same identity, terminal proof present, update vs audit-only vs new identity. |
| 3 | Apply the helper to card ACK pending/completed return writes. | `skills/flowpilot/assets/card_runtime.py`, card runtime tests | Duplicate ACK after Router resolution preserves terminal status and writes audit metadata only. |
| 4 | Apply the helper to bundle ACK pending/completed return writes. | `skills/flowpilot/assets/card_runtime.py`, router/card runtime tests | Duplicate bundle ACK and incomplete late bundle ACK cannot downgrade resolved bundles. |
| 5 | Ensure Router pending-return reads use effective status everywhere. | `skills/flowpilot/assets/flowpilot_router.py`, router tests | Raw `returned` or `bundle_ack_incomplete` is pending only without terminal proof. |
| 6 | Apply the helper shape to control blocker repair decisions and blocker resolution indexes. | `skills/flowpilot/assets/flowpilot_router.py`, control blocker tests | Duplicate PM repair decisions do not create duplicate transactions; new blockers still work. |
| 7 | Apply the same identity/terminal policy to gate and result-disposition paths where existing scoped event idempotency is not enough. | `skills/flowpilot/assets/flowpilot_router.py`, focused gate/result tests | Stale gate/block/result inputs cannot reopen terminal waits; true new identities still route. |
| 8 | Run full model and runtime verification, then sync the installed local skill. | `simulations/*results.json`, `scripts/install_flowpilot.py` | Repository tests pass, install sync/check pass, no GitHub push. |

## Risk Table for This Repair

| Risk ID | Possible bug introduced by repair | Required FlowGuard coverage | Runtime/test coverage |
| --- | --- | --- | --- |
| R1 | Same delivery ACK still downgrades a resolved pending return. | Known-bad hazard must fail: `resolved_card_return_reopened_by_duplicate_ack`. | Duplicate card ACK test asserts pending status remains terminal and downstream events are not blocked. |
| R2 | Same bundle ACK downgrades a resolved bundle return. | Known-bad hazard must fail: `resolved_bundle_return_reopened_by_duplicate_ack`. | Duplicate bundle ACK test asserts resolved bundle stays resolved. |
| R3 | Incomplete bundle ACK after resolution reopens the bundle wait. | Known-bad hazard must fail: `resolved_bundle_return_downgraded_to_incomplete`. | Late incomplete bundle ACK test asserts audit-only and no `bundle_ack_incomplete` wait. |
| R4 | Pending-return selector still uses raw status only. | Known-bad hazards must fail: `pending_selector_ignores_resolved_at`, `pending_selector_ignores_completed_return`. | Direct selector/router event test with dirty raw status and terminal proof. |
| R5 | Repair channel is blocked by stale terminal return metadata. | Known-bad hazard must fail: `repair_channel_blocked_by_resolved_return`. | Router event test verifies PM/reviewer repair events can proceed past terminal-proven stale return. |
| R6 | Gate pass is reopened by a late old block. | Known-bad hazard must fail: `gate_pass_reopened_by_late_block`. | Focused gate decision test or source audit confirms same gate identity is terminal-monotone. |
| R7 | Resolved control blocker becomes active again. | Known-bad hazard must fail: `resolved_control_blocker_reactivated_by_stale_artifact`. | Control-blocker sync/resolution test verifies resolved artifacts do not become active. |
| R8 | Duplicate PM repair decision creates another blocker or repair transaction. | Known-bad hazard must fail: `duplicate_pm_repair_created_new_blocker`. | PM repair duplicate test asserts one transaction and already-recorded/audit behavior. |
| R9 | Old repair generation failure reopens a newer success. | Known-bad hazard must fail: `old_repair_generation_failure_reopened_success`. | Repair generation test or model/source audit confirms old generation is audit-only. |
| R10 | New repair generation is incorrectly swallowed by an old terminal record. | Known-bad hazard must fail: `new_repair_generation_failure_swallowed`. | New generation test confirms separate scoped identity is accepted. |
| R11 | Duplicate result return reopens a PM/reviewer disposition wait. | Known-bad hazard must fail: `result_disposition_reopened_by_duplicate_result`. | Result disposition test or scoped-event audit confirms duplicate result is audit-only. |
| R12 | Same-identity replay writes a duplicate side effect even though status is preserved. | Known-bad hazard must fail: `same_identity_replay_writes_duplicate_side_effect`. | Tests count completed returns, transactions, blockers, or disposition records. |
| R13 | Repair is too broad and suppresses true new work. | Safe model path must accept `new_pm_repair_decision_new_blocker`, `new_repair_failure_new_generation`, and new result/gate identities. | Existing "new blocker/new generation" tests stay green and new focused tests cover new identity acceptance. |
| R14 | Helper becomes a new hidden bypass that lets real unresolved items through. | Model safe path distinguishes terminal proof from raw terminal-looking status. | Tests assert genuinely pending returns/blockers remain blocking. |

## Model-Gate Sequence

1. Extend the terminal-state model and runner with every risk row above.
2. Run the model with source/live metadata audit before production edits.
3. Confirm each known-bad hazard is detected.
4. Confirm every planned safe path reaches a terminal passing state.
5. Only then edit runtime code.
6. After each runtime step, rerun the focused model and the relevant tests.
7. Run broader FlowPilot meta/capability checks in the background when they are long.

## Verification Commands

Short checks:

```powershell
python -m py_compile simulations\flowpilot_terminal_state_monotonicity_model.py simulations\run_flowpilot_terminal_state_monotonicity_checks.py skills\flowpilot\assets\card_runtime.py skills\flowpilot\assets\flowpilot_router.py
python simulations\run_flowpilot_terminal_state_monotonicity_checks.py --json-out simulations\flowpilot_terminal_state_monotonicity_results.json
python -m pytest tests\test_flowpilot_card_runtime.py -q
python -m pytest tests\test_flowpilot_router_runtime.py -q -k "card_return or control_blocker or repair_decision or gate_decision or result_disposition"
```

Long checks, run in the background when possible:

```powershell
python simulations\run_meta_checks.py
python simulations\run_capability_checks.py
```

Local install sync:

```powershell
python scripts\install_flowpilot.py --sync-repo-owned --json
python scripts\audit_local_install_sync.py --json
python scripts\install_flowpilot.py --check --json
python scripts\check_install.py
```

## Explicit Non-Goals

- Do not push to remote GitHub.
- Do not read sealed packet/card/result/report bodies.
- Do not rewrite unrelated peer-agent changes.
- Do not add a large new state-machine framework.
- Do not bypass unresolved-return or control-blocker checks.
- Do not add broad new schema fields unless a specific ledger lacks an existing identity or terminal proof.

## Implementation Status

| Area | Status | Evidence |
| --- | --- | --- |
| FlowGuard model expansion | Implemented | The terminal-state model now covers duplicate ACKs, bundle ACKs, stale gate/blocker reactivation, duplicate repair/result side effects, new identity acceptance, and real unresolved waits. |
| Card ACK writer monotonicity | Implemented | `card_runtime` preserves terminal pending returns and records `terminal_replay_ack` audit metadata for same-identity duplicate ACKs. |
| Bundle ACK writer monotonicity | Implemented | `card_runtime` applies the same merge behavior to bundle ACK pending returns and completed return records. |
| Pending-return read side | Covered | Router pending selection already computes effective pending status from `resolved_at` and resolved completed-return keys; the model source audit confirms this. |
| Gate, repair, and result event replay | Covered by existing scoped identity layer | `flowpilot_event_idempotency` source audit confirms scoped policies for gate decisions, PM repair decisions, PM role-work requests/results, current-node results, and PM result decisions. |
| Control blocker active/resolved index | Covered by existing resolution/index logic | Focused control-blocker tests confirm resolved blockers leave the active slot, duplicate repair decisions are already-recorded, and new blockers can still receive decisions. |
| Local install sync | Pending final verification | Run after all tests and long model checks finish. |
