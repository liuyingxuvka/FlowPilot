# FlowPilot Daemon Projection Reconciliation Plan

## Risk Intent Brief

This change uses FlowGuard because it changes daemon control flow, durable
state reconciliation, idempotency, and sleep/continue behavior. The protected
harm is a Router daemon that either asks Controller to repeat work that is
already durably complete, or waits one second even though only Router's own
per-tick budget stopped immediate progress.

The model gate for this change is narrow and focused. Heavyweight Meta and
Capability model suites are deferred by user direction.

## Optimization Sequence

| Order | Optimization | Concrete Work | Verification Gate |
| --- | --- | --- | --- |
| 1 | Paper plan and risk ledger | Record this ordered plan, risk catalog, and model coverage matrix before code edits. | OpenSpec artifacts and this document exist before runtime edits. |
| 2 | Boundary projection model hardening | Extend `flowpilot_daemon_reconciliation_model.py` so it models artifact, receipt/action row, scheduler row, Router flags, pending action, queue stop reason, and sleep decision separately. | Known-bad hazards for stale flags, reissue, action-without-pending, bad sleep, and bad fast-loop are detected. |
| 3 | Intended model pass | Model the intended flow: reconcile projections first, compute next work only after convergence, skip sleep only after queue budget exhaustion. | Focused FlowGuard runner passes model graph, hazards, and intended path checks. |
| 4 | Router projection helper | Add one idempotent helper that reclaims valid Controller-boundary durable evidence into Router flags/events even when `pending_action` is empty. | Runtime test starts with valid artifact plus reconciled ledgers plus false flags and does not reissue boundary action. |
| 5 | Reconciliation barrier placement | Call the helper before returning existing pending work or computing a new action in foreground and daemon paths. | Controller-boundary focused tests and daemon reconciliation check pass. |
| 6 | Daemon fast-loop sleep rule | After each tick, sleep only for real waits (`barrier`, `no_action`, `pending_action_changed`); immediately continue after `max_actions_per_tick`. | Test patches sleep and proves no sleep after budget exhaustion while normal barriers still sleep. |
| 7 | Local sync | Sync repo-owned assets to the installed FlowPilot skill, audit install, and check local git state. | Install sync/audit succeeds; final status reports touched files and any peer-agent changes preserved. |

## Possible Bug Checklist

| ID | Possible Bug | What Would Go Wrong | Required FlowGuard Coverage |
| --- | --- | --- | --- |
| P1 | Stale boundary flags after valid evidence | Router thinks Controller has not taken over even though artifact, receipt, action row, and scheduler row are complete. | Invariant fails when boundary projections are complete but flags remain false before next action. |
| P2 | Reissue completed boundary action | Controller sees the same `confirm_controller_core_boundary` row again. | Hazard fails if boundary action is reissued after valid reconciled evidence. |
| P3 | Action exposed without pending row | History shows Router computed the boundary action while `pending_action` is empty or the Controller table says done. | Hazard fails when boundary action is exposed without a matching pending action. |
| P4 | Action/scheduler disagreement hidden | Controller action ledger says complete but Router scheduler row says open, or the reverse. | Invariant fails unless both ledgers agree before flags are trusted. |
| P5 | Projection helper accepts bad artifact | A handwritten or wrong-run artifact flips Router flags. | Model keeps artifact validity separate; runtime helper must reuse existing validator. |
| P6 | Reconciliation runs after next-action selection | Router decides from stale state before reading durable evidence. | Existing and extended invariant fails on next-action computation before reconciliation barrier. |
| P7 | Daemon sleeps while only queue budget stopped it | Router has immediate internal queue work but waits one second between chunks. | Hazard fails when `queue_stop_reason=max_actions_per_tick` and sleep is taken. |
| P8 | Daemon busy-loops after a real wait | Router skips sleep even though it hit a barrier or no work. | Hazard fails when fast-loop continues after `barrier` or `no_action`. |
| P9 | Fast loop ignores bounded budget | Internal actions continue forever without yielding. | Model keeps per-tick budget distinct; runtime still honors `max_ticks` and max queue size. |
| P10 | Other agents' changes overwritten | Concurrent OpenSpec/runtime changes are lost. | Not modelled by FlowGuard; covered by git status checks and scoped edits. |

## Risk-To-Model Coverage Matrix

| Risk IDs | Model State/Event | Invariant Or Oracle | Runtime Evidence |
| --- | --- | --- | --- |
| P1, P4 | `controller_boundary_artifact_valid`, `controller_boundary_action_reconciled`, `controller_boundary_scheduler_reconciled`, `controller_boundary_flags_synced` | Flags must sync after all durable projections agree. | Boundary stale-flag runtime test and live projection adapter. |
| P2, P3 | `controller_boundary_reissued_after_reconcile`, `controller_boundary_action_returned_without_pending` | Completed boundary evidence must not produce a new exposed action. | Runtime test checks next action is not boundary and pending action is not stale. |
| P5 | `controller_boundary_artifact_valid` | Invalid artifacts cannot satisfy projection convergence. | Existing handwritten-artifact repair tests remain in scope. |
| P6 | `reconciliation_barrier_started`, `computed_before_reconciliation` | Durable evidence requires barrier before next action. | Focused daemon reconciliation runner. |
| P7, P8 | `queue_stop_reason`, `sleep_taken`, `immediate_tick_requested` | Sleep only after real waits; continue immediately after budget exhaustion. | Sleep-patched daemon runtime test. |
| P9 | `fast_loop_budget_remaining`, `max_actions_per_tick` | Immediate loops remain bounded by existing tick and queue limits. | Runtime test uses `max_ticks` to prove bounded continuation. |
| P10 | Not a daemon state | Out of FlowGuard scope; use repo coordination and git checks. | `git status --short --untracked-files=all` before and after slices. |

## Deferred Checks

- `python simulations/run_meta_checks.py` is deferred because it is a
  heavyweight Meta model outside this focused projection slice.
- `python simulations/run_capability_checks.py` is deferred because it is a
  heavyweight Capability model outside this focused projection slice.
