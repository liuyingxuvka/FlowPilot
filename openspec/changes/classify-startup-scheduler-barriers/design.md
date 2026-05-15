# Design: Classify Startup Scheduler Barriers

## Optimization Order

| Order | Optimization Point | Current Problem | Desired Rule | Required Evidence |
| --- | --- | --- | --- | --- |
| 1 | Define scheduler progress classes | Runtime treats broad mechanics as barriers. `requires_payload`, display confirmation, host spawn, and host automation can stop queue filling even when no next-step dependency exists. | Router classifies each action by scheduling meaning: `true_barrier`, `phase_handoff`, `parallel_obligation`, or `local_dependency`. Mechanics remain evidence requirements, not automatic queue barriers. | FlowGuard model rejects broad-mechanic blocking and accepts dependency-based classification. Runtime tests show real barriers still stop. |
| 2 | Demote startup parallel obligations | Startup banner, heartbeat binding, and startup display/status actions are required before review, but unrelated startup work can proceed while their receipts are pending. | These rows may be enqueued and remain unresolved while Router queues independent startup work. Startup Reviewer review still waits until they are reconciled. | Model hazards catch banner/heartbeat/display blocking independent queueing and catch Reviewer review before reconciliation. |
| 3 | Demote startup role-slot spawn to local dependency | Background role spawn currently behaves like a global barrier because it needs payload/host spawn proof. | Role-slot spawn blocks only role-dependent card delivery, role memory injection, or role freshness review. It does not block independent heartbeat, display/status, mechanical audit, or Controller-core queueing. | Model hazards catch role-dependent work before role slots are ready and catch role spawn blocking unrelated work. |
| 4 | Repair startup receipt/bootstrap reconciliation drift | A Controller row can be done/reconciled while bootstrap `pending_action`, startup flags, or scheduler row state remain stale, causing reissue or false wait. | When a startup Controller receipt is consumed, Router updates the matching startup flag, clears bootstrap pending state, marks the scheduler row reconciled, and computes the next startup row unless a true barrier is reached. | Existing peer model additions plus new hazards catch stale pending, stale flag, stale scheduler row, and same-action reissue. Runtime tests reproduce the stale-drift shape. |
| 5 | Route queue filling through dependency-aware skip/continue | Startup bootloader selection can reselect the same unresolved obligation if only completion flags are checked. | For nonblocking obligations, Router records that the row is already scheduled/open, skips duplicate issue, and continues to the next independent action. True barriers remain pending until resolved. | Model rejects duplicate startup side effects and accepts one open row per idempotency key. Runtime tests assert no duplicate rows. |
| 6 | Keep final startup join strong | Demoting obligations can accidentally let Reviewer review or PM activation start too early. | Startup pre-review reconciliation is the hard join for all startup obligations. PM activation keeps existing same-role ACK gating after Reviewer facts. | Model hazards and runtime tests catch early Reviewer review, early Reviewer report acceptance, and PM activation without same-role ACK. |

## Risk And Bug Checklist

| Risk | Possible Bug | FlowGuard Must Catch | Runtime/Test Evidence |
| --- | --- | --- | --- |
| R1 | Banner/display confirmation is still treated as a global barrier, so Router queues one row at a time. | Safe plan cannot pass unless parallel startup obligations allow unrelated queueing. | Daemon tick queues later independent startup rows while banner/display row remains open. |
| R2 | Heartbeat binding blocks Controller core or unrelated startup work even though review-time reconciliation is enough. | Hazard for host automation as global barrier fails. | Startup heartbeat row can remain pending while independent startup rows are queued; Reviewer review still waits. |
| R3 | Role-slot spawn blocks all startup work, or the opposite: role-dependent cards are delivered before role slots exist. | Hazards for global role-spawn barrier and premature role-dependent delivery both fail. | Tests cover independent work after role spawn and delayed role-dependent card delivery. |
| R4 | Startup Reviewer fact review starts while banner, heartbeat, display, role-slot, prep card, or startup Controller rows are unresolved. | Early startup review/report hazards fail. | Tests assert `reviewer.startup_fact_check` is blocked by startup reconciliation until obligations clear. |
| R5 | True barriers are accidentally demoted, so Router queues past user input, terminal summary, control blockers, non-startup ACK/result waits, or resume/rehydration gates. | True-barrier demotion hazards fail. | Tests assert user intake, terminal summary, and non-startup wait barriers still stop. |
| R6 | Startup done receipts leave bootstrap pending state or scheduler rows stale, causing duplicate issue or dead wait. | Existing stale-pending hazard plus new reconciliation hazard fail. | Test consumes a done startup receipt and asserts flag update, pending clear, scheduler reconciliation, and no reissue. |
| R7 | Queue filling duplicates a host side effect because scheduled/open rows are skipped by completion flag only. | Duplicate nonblocking startup obligation hazard fails. | Tests assert deterministic idempotency row count stays one across daemon retries. |
| R8 | A row is marked reconciled from self-attested Controller text without Router-visible host/display/role evidence. | Missing evidence/postcondition hazard fails. | Tests assert reconciliation requires the action's Router-visible proof fields before review. |
| R9 | Scheduler/Controller ledger status drifts, for example Router row goes from `reconciled` back to `receipt_done`. | Monotonic reconciliation hazard fails. | Runtime test prevents receipt resync from downgrading reconciled scheduler rows. |
| R10 | Heavy model checks are skipped and the skip is mistaken for a pass. | Model report and adoption note must record focused-only validation. | Final validation states meta/capability checks were skipped by explicit user request. |

## Classification Contract

- `true_barrier`: stops queue filling until resolved. Includes user input,
  terminal actions, control blockers, resume/rehydration gates, current-scope
  reconciliation waits, non-startup ACK/result waits, and any action whose next
  step directly depends on its completed evidence.
- `phase_handoff`: may be enqueued at a phase edge, but later protected work
  cannot cross its handoff boundary until required evidence is reconciled.
- `parallel_obligation`: can remain open while Router queues unrelated work,
  but must be reconciled before the protected join that depends on it.
- `local_dependency`: can remain open while unrelated work proceeds, but blocks
  only actions that explicitly need the local evidence, such as role ids or
  role freshness.

## Model Scope

The focused model for this change is the two-table async scheduler model,
augmented by the daemon microstep lifecycle model already present in the
workspace. The model must prove three things before production edits:

1. The known-bad hazards in the risk checklist fail for the intended reason.
2. The candidate optimization plan passes with parallel obligations, local
   dependencies, and strong startup join semantics.
3. The existing stale-bootstrap receipt hazards stay covered and continue to
   pass in the repaired plan.

The heavyweight `run_meta_checks.py` and `run_capability_checks.py` regressions
are intentionally not run in this change unless the user later asks for them.
