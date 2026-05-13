# FlowPilot RouterError Recovery Plan

## Risk Intent Brief

This change uses FlowGuard to review the FlowPilot runtime path where a role
output is submitted directly to Router and Router rejects it after writing a
control blocker. The protected harm is a Controller execution chain that stops
only because the runtime command exits with an exception, leaving heartbeat or
manual resume to rediscover the Router-owned next step.

The model and implementation must keep these boundaries:

- Router decides the next legal action; Controller must not infer or repair.
- Control blocker bodies remain sealed to the target role.
- Non-control Router errors still fail loudly.
- The original rejected role event is not treated as accepted.
- A control blocker response returns enough metadata for Controller to continue
  with Router's next action in the same execution chain.

## Optimization Checklist

| Step | Optimization point | Concrete change | Verification |
| --- | --- | --- | --- |
| 1 | Paper plan and risk list | Record the intended runtime recovery behavior, known hazards, and model coverage in this file. | Human-readable plan exists before production edits. |
| 2 | Dedicated FlowGuard model | Add a narrow model for `submit-output-to-router -> RouterError(control_blocker) -> next_action`. | Known-bad hazard states fail; safe graph passes. |
| 3 | Runtime conversion | In `flowpilot_runtime.py`, catch `RouterError` only when it carries `control_blocker`, then call `flowpilot_router.next_action(root)` and return a normal JSON result. | CLI unit test proves no exception/exit break for control-blocker errors. |
| 4 | Preserve ordinary failures | Leave plain `RouterError` and validation errors as failures. | Unit test proves non-control errors are still raised. |
| 5 | Controller-visible result | Include `ok`, `blocked`, `event`, `router_error`, `control_blocker`, and `next_action` in the returned JSON. | Test asserts `next_action.action_type == handle_control_blocker` for an unresolved blocker case. |
| 6 | Local install sync | Sync the repo-owned FlowPilot skill/runtime into the local installed copy only after checks pass. | `install_flowpilot.py --sync-repo-owned --json` and install check pass. |
| 7 | Local git only | Commit the local repository changes without pushing GitHub. | Local commit exists; no remote push is performed. |

## Failure Modes The Model Must Catch

| Risk id | Possible bug | Why it matters | Model coverage |
| --- | --- | --- | --- |
| R1 | Runtime exits failure after Router has already written a control blocker. | Controller stops and heartbeat becomes the accidental recovery mechanism. | `control_blocker_error_broke_controller_chain` invariant. |
| R2 | Runtime swallows a normal Router error that has no control blocker. | Real protocol failures could look successful. | `plain_router_errors_remain_failures` invariant. |
| R3 | Runtime returns `blocked=true` but omits the control blocker metadata. | Controller cannot route the sealed blocker to the right role. | `blocked_result_includes_control_blocker_and_next_action` invariant. |
| R4 | Runtime returns blocker metadata but does not ask Router for `next_action`. | Controller still has to guess or stop. | `blocked_result_includes_control_blocker_and_next_action` invariant. |
| R5 | Controller treats the rejected original event as accepted. | Route state advances from an event Router explicitly rejected. | `rejected_event_is_not_accepted_or_retried_by_controller` invariant. |
| R6 | Controller self-repairs or opens sealed blocker details. | Breaks FlowPilot role boundaries and sealed-body rules. | `controller_does_not_self_repair_or_read_sealed_body` invariant. |
| R7 | Runtime hard-codes PM instead of following Router. | Future non-PM blockers would route incorrectly. | The safe path requires `next_action_source == router`, not a hard-coded target. |
| R8 | Duplicate control-blocker side effects are created during recovery. | Retry paths could produce multiple blockers for the same rejection. | State tracks single blocker write and next-action conversion only. |

## Expected Runtime Evolution

| Current behavior | Target behavior |
| --- | --- |
| Role output submits to Router. | Same. |
| Router rejects event and writes `control_blocker`. | Same. |
| Runtime raises `RouterError`; current Controller execution chain stops. | Runtime catches only `RouterError` with `control_blocker`. |
| Heartbeat/manual resume later asks Router what to do. | Runtime immediately calls `flowpilot_router.next_action(root)`. |
| Controller resumes only after heartbeat or manual intervention. | Controller receives a normal JSON result containing Router's next action and can continue now. |

## Out Of Scope

- The ACK pre-consumption fix is being handled separately by another agent.
- This change does not alter PM repair semantics, reviewer report semantics, or
  card ACK validation.
- This change does not push to GitHub.
