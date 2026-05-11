# FlowPilot Control-Plane Event Contract Repair Plan

## Risk Intent Brief

This change repairs a control-plane event contract gap: the Router can persist
an `await_role_decision` wait whose `allowed_external_events` contains a string
that is not registered in `EXTERNAL_EVENTS`. The next `record-event` call then
rejects that string as unknown, so the run can become stuck between a written
wait state and an unrecordable event.

Protected harms:

- PM repair decisions must not convert internal Router action labels into
  role-recordable external events.
- Every persisted role wait must contain only registered, currently receivable
  external events.
- Direct Router ACK/check-in changes must preserve the semantic wait that comes
  after a mechanical card ACK.
- Repair transactions must not leave stale active transactions, stale pending
  actions, or unresolvable control blockers.
- Local install sync must not leave the installed `flowpilot` skill older than
  the local repository.

Modeling boundary:

- Behavior flow: `Input x State -> Set(Output x State)`.
- Inputs: PM repair decision, repair rerun target, Router wait construction,
  direct ACK/check-in, role event recording, duplicate/retry repair decisions.
- State: active control blocker, PM repair decision status, repair transaction,
  pending action, allowed external events, role event registry, card ACK state.
- Side effects: persisted run state, control blocker artifact, repair
  transaction artifact, event ledger, installed skill copy.

## Optimization Checklist

| Step | Optimization point | Concrete change | Done when |
| --- | --- | --- | --- |
| 1 | Make the event contract explicit | Add a focused FlowGuard model for event classes: external role events, internal Router actions, direct ACK/check-in events, and unknown strings. | Model has hazard cases for the current `router_selects...` dead wait and related event-class mistakes. |
| 2 | Validate PM repair rerun targets before state write | Reject `rerun_target` unless it resolves to a registered external event. Keep the existing rejection for rerunning the PM repair decision itself. | A bad PM repair decision fails before `active_control_blocker.allowed_resolution_events` or `pending_action.allowed_external_events` can be written. |
| 3 | Validate every persisted wait boundary | Centralize validation for `await_role_decision.allowed_external_events`, including control-blocker waits and generic expected-role waits. | No Router writer can persist an unknown, non-string, or not-currently-receivable event wait. |
| 4 | Preserve direct Router ACK semantics | Treat direct ACK/check-in as mechanical receipt only; after ACK consumption, the next semantic role wait must still be present and valid. | ACK completion cannot satisfy or erase reviewer/PM semantic outcome waits. |
| 5 | Keep repair transactions resolvable | Ensure repair outcome tables only expose registered events and continue to support material-scan success/blocker/protocol-blocker outcomes. | Material repair paths still have separate success, blocker, and protocol-blocker events. |
| 6 | Add runtime regression tests | Add focused tests for invalid PM rerun targets, valid PM route-draft rerun targets, material repair outcomes, and invalid persisted waits. | Tests fail on the old behavior and pass after the repair. |
| 7 | Run validation in layers | Run the new FlowGuard model before production edits, then targeted tests after each repair, then broader router/control-plane checks. | Validation evidence shows model hazards caught, safe plan passed, and runtime checks passed. |
| 8 | Sync local install and local git only | After validation, sync the installed skill from the local repository and commit only this task's files locally. Do not push to GitHub. | Installed copy matches repo-owned FlowPilot files; local git contains a scoped commit; remote stays untouched. |

## Bug/Risk Checklist

| Risk id | Possible bug introduced by this optimization | Why it matters | FlowGuard must catch it by |
| --- | --- | --- | --- |
| R1 | PM submits an internal Router action, such as `router_selects_next_legal_action_after_pm_records_control_blocker_repair_decision`, as `rerun_target`. | Router would wait for an event no role can record. | Rejecting internal-action rerun targets before a wait is persisted. |
| R2 | PM submits an unknown typo as `rerun_target`. | Same dead wait, but from ordinary misspelling. | Rejecting unregistered external events. |
| R3 | PM submits the PM repair decision event itself as `rerun_target`. | The system could loop on the same PM decision instead of asking for the corrected follow-up. | Preserving the existing self-loop rejection. |
| R4 | Valid external events are accidentally rejected. | This would block legitimate route repair, for example `pm_writes_route_draft`. | Safe scenario proving registered non-PM repair events pass. |
| R5 | Material-scan repair loses its separate success/blocker/protocol-blocker events. | A failed recheck would become unroutable or success-only. | Safe material scenario requiring all three material repair outcome events. |
| R6 | A wait is built from a valid event whose prerequisite flag is false. | The UI says "wait for X" before X can legally be recorded. | Wait-boundary invariant for currently receivable events. |
| R7 | Direct ACK/check-in consumes the mechanical receipt and also erases the real semantic wait. | The role checked in, but reviewer/PM outcome never happens. | ACK scenario requiring a valid semantic wait after ACK. |
| R8 | ACK/check-in is treated as a normal role event and put in `allowed_external_events`. | Controller and roles would mix receipt mechanics with project decisions. | Event-class invariant separating ACK/check-in from external role events. |
| R9 | Duplicate PM repair decisions create a new blocker or transaction. | Retries would multiply state instead of staying idempotent. | Duplicate scenario requiring no new blocker and no duplicate active transaction. |
| R10 | State cleanup only catches the bad wait after it is already persisted. | The current run can still deadlock or expose broken UI state for one cycle. | Producer-side invariant: unsafe write is rejected before persistence. |
| R11 | Local install remains stale after repo repair. | The next FlowPilot invocation would still run the old bug. | Install-sync check after repo validation. |
| R12 | Other agents' concurrent edits are overwritten. | Parallel optimization work must be preserved. | Scope control: stage/commit only files changed for this repair. |

## FlowGuard Coverage Contract

| Coverage item | Required model evidence | Required runtime evidence |
| --- | --- | --- |
| Current bug class is visible | Hazard `internal_router_action_as_pm_rerun_target` fails the unsafe plan. | Regression test rejects the same `router_selects...` target. |
| Unknown event strings are blocked | Hazard `unknown_string_as_pm_rerun_target` fails. | Regression test rejects an arbitrary typo before state write. |
| Valid PM repair target remains usable | Safe path with `pm_writes_route_draft` passes. | Regression test records a valid PM decision and next wait exposes only `pm_writes_route_draft`. |
| Material repair still supports non-success outcomes | Safe material repair path passes with success, blocker, and protocol-blocker events. | Existing material repair tests continue to pass. |
| Direct ACK does not erase semantic wait | Hazard `ack_consumed_semantic_wait_lost` fails; safe ACK path passes. | Existing card return/ACK tests continue to pass. |
| Persisted waits are always recordable | Invariant checks every persisted `allowed_external_events` item is a registered external event and currently receivable. | Targeted test for stale/invalid pending waits and broader router checks pass. |

## Execution Order

1. Add/upgrade the FlowGuard model and runner for this control-plane event
   contract.
2. Run the model and confirm that all listed hazards are detected and the safe
   plan passes.
3. Only after the model passes, patch Router validation at the producer/write
   boundary.
4. Add runtime regression tests and run the focused test set.
5. Run broader required checks: py_compile, the new model, relevant existing
   control-plane models, router runtime tests, `run_meta_checks.py`,
   `run_capability_checks.py`, and `scripts/check_install.py`.
6. Sync the local installed skill from the repository, audit install freshness,
   and make a local git commit containing only this task's files.

## Non-Goals

- Do not redesign the product route for ProjectRadar.
- Do not read sealed packet/result/report bodies.
- Do not push to remote GitHub.
- Do not overwrite unrelated uncommitted work from peer agents.
