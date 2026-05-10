# System Card Bundle Optimization Plan

Date: 2026-05-10

## Risk Intent Brief

This change upgrades FlowPilot's startup-only command folding discussion into a
global router boundary optimization for system-card delivery. The optimization
must reduce repeated Controller-to-role handoffs without letting the Controller
read card bodies, skip role acknowledgement, merge semantic approval gates, or
parallelize hidden dependencies.

Protected harms:

- Controller advances past a role boundary without target-role runtime opens.
- A bundle acknowledgement replaces independent per-card read receipts.
- A card is bundled across role, run, agent, resume tick, or dependency
  boundaries.
- A card that should wait for a PM, reviewer, officer, packet, mail, host, or
  user event is silently batched with later work.
- Resume or replacement roles process stale bundle envelopes.
- Existing single-card delivery compatibility regresses.
- A recoverable incomplete bundle ACK becomes a dead-end instead of returning
  to the same role with explicit missing-card evidence.

Residual blindspot: the model can prove control-plane guard shape, but runtime
tests still have to compare the router's concrete `SYSTEM_CARD_SEQUENCE`
resolver, persisted ledgers, CLI/install sync, and real ack validation.

## Optimization Work Items

| Order | Optimization | Current Friction | Target Behavior | Scope Guard |
| --- | --- | --- | --- | --- |
| 1 | Add global same-role card-bundle model path | `card_bundle_fold` is currently rejected because generic bundling lacks dedicated replay semantics | A guarded same-role system-card bundle passes only with same run, role, agent, resume tick, manifest hashes, per-card receipts, and one bundle ACK referencing every card | Model only; no runtime change until hazards are proven catchable |
| 2 | Add bundle envelope and runtime ACK support | `card_runtime` opens and ACKs one card envelope at a time | `open_card_bundle` writes one read receipt per card; `submit_card_bundle_ack` writes one envelope-only ACK that references all per-card receipts | No body text in ACK; no semantic approval from receipts |
| 3 | Add router bundle resolver | `_next_system_card_action` emits one `deliver_system_card` at a time | Router scans the next contiguous safe card segment and emits `deliver_system_card_bundle` when at least two cards are globally eligible | Fallback to existing single-card path when eligibility is not proven |
| 4 | Add router bundle commit/check loop | Return ledger currently tracks one pending card return per card | Bundle delivery records per-card deliveries plus one pending bundle return; `check_card_bundle_return_event` validates all receipts and resolves member returns | `run-until-wait` still stops at role/card boundary |
| 5 | Remove startup-specific framing from docs/checks | Prior startup plan says same-role card batching is future-only | Documentation distinguishes rejected generic folds from supported guarded same-role bundles | Do not add cross-role batches, packet relay folding, role-output folding, or artifact merge |
| 6 | Add incomplete bundle ACK recovery | A missing member receipt could otherwise be a hard protocol error | Router records `bundle_ack_incomplete`, lists `missing_card_ids`, keeps the pending return unresolved, and waits for the same role to submit a corrected bundle ACK | Invalid ACKs still fail; only missing member receipts get this recovery path |
| 7 | Sync local install and local git | Installed skill may stay stale unless explicitly synced | Repository source, installed local skill, and local commit all include the same bundle support | No remote GitHub push |

## Bug/Hazard Checklist

| ID | Possible Bug | Required Model Detection |
| --- | --- | --- |
| B1 | Bundle crosses target roles | Fail as `same_role bundle crossed role or run boundary` |
| B2 | Bundle crosses run, agent, or resume tick | Fail as `same_role bundle crossed role or run boundary` |
| B3 | Bundle includes a card whose dependency is not already satisfied or produced by an earlier bundled delivery flag | Fail as `same_role bundle included an unsafe dependency` |
| B4 | Bundle hides a required role output, packet relay, mail relay, host action, user action, or semantic gate | Fail as `same_role bundle included an unsafe dependency` |
| B5 | Bundle ACK has fewer receipt refs than bundled cards | Fail as `same_role bundle missing per-card receipts or ack join` |
| B6 | Bundle receipt is treated as a substitute for per-card receipts | Fail as `bundle receipt replaced independent per-card receipts` |
| B7 | Controller reads bundled card body or mutates router-authored bundle | Fail as existing controller-envelope-only invariant |
| B8 | Router advances before bundle ACK is checked | Fail as `same_role bundle missing per-card receipts or ack join` |
| B9 | Single-card fallback is removed or broken | Runtime tests must still pass existing single-card card-delivery tests |
| B10 | `run-until-wait` silently applies the role-boundary bundle | Runtime test must prove it stops at `deliver_system_card_bundle` |
| B11 | Resume/replacement processes stale bundle without current role I/O receipt | Existing role I/O ack invariant must still fail |
| B12 | Read receipts replace PM/reviewer/officer semantic judgement | Existing semantic-gate invariant must still fail |
| B13 | Incomplete bundle ACK stops the route forever | FlowGuard and runtime tests must prove missing card ids are listed, pending return stays unresolved, the same-role recovery wait is returned, a corrected ACK is accepted, and the mainline resumes |

## Implementation Sequence

1. Update the FlowGuard card-envelope model with a guarded same-role bundle
   success and recovery path plus hazard cases B1-B8/B11-B13.
2. Run the model checks and confirm every known-bad hazard is detected before
   changing runtime code.
3. Add bundle schemas and functions to `card_runtime.py`.
4. Add global bundle eligibility and delivery commit/check support to
   `flowpilot_router.py`, keeping the single-card path as fallback.
5. Add the incomplete bundle ACK branch: record `bundle_ack_incomplete`, keep
   the pending return, wait for the same role, and resume after a corrected ACK.
6. Add focused router/runtime tests for bundle success, incomplete ACK recovery,
   fallback, invalid ACK, unsafe dependency stop, cross-role stop, and
   `run-until-wait` boundary.
7. Run targeted tests after each implementation slice, then run broader
   local checks before sync.
8. Sync the local installed FlowPilot skill, verify install check/audit, stage
   and commit locally. Do not push.
