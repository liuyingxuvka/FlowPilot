# Active Holder Fast Lane Plan

Date: 2026-05-11

## Plain-Language Goal

FlowPilot should stop making Controller handle every small mechanical retry
inside one active work packet. Once Router has assigned a packet to the current
worker, that worker may use a narrow fast lane to acknowledge the packet,
report safe progress, submit the result envelope, and fix mechanical envelope
problems.

The fast lane is not free chat and not role-to-role delivery. It is a
short-lived packet lease. Router accepts contact only from the currently
registered holder for the currently active packet and only for actions named by
that lease.

Router does not directly chat with Controller. Router writes a controller-visible
pending action or wake notice. Controller is activated when the host loop,
heartbeat/manual resume path, Cockpit, or the next Controller router call reads
that pending action.

## Optimization Checklist

| Order | Optimization | Files likely touched | Done when |
| --- | --- | --- | --- |
| 1 | Define the active-holder lease contract. It must bind `run_id`, `packet_id`, `holder_role`, `holder_agent_id`, `node_id`, `route_version`, `frontier_version`, allowed actions, result target paths, and body/result hashes. | `docs/active_holder_fast_lane_plan.md`, `simulations/flowpilot_router_loop_model.py`, `skills/flowpilot/assets/packet_runtime.py` | A wrong role, stale packet, stale route/frontier, missing agent id, or unlisted action is model-detectable and runtime-rejected. |
| 2 | Add Router/packet-runtime mechanics for local packet check-ins: ack, progress, result submission, mechanical reject, and same-holder resubmission. | `skills/flowpilot/assets/packet_runtime.py`, tests | The current worker can fix envelope/contract-shell problems without Controller reading the body or manually relaying each retry. |
| 3 | Add the return-to-Controller boundary. When the fast-lane packet closes, Router writes a controller-visible next-action notice and updates packet holder/status history. | `skills/flowpilot/assets/packet_runtime.py`, optionally `skills/flowpilot/assets/flowpilot_router.py`, tests | Controller never guesses from worker chat; it sees a router-authored notice such as `deliver_result_to_reviewer`. |
| 4 | Keep semantic gates outside the fast lane. Reviewer still opens result bodies through packet runtime; PM still completes nodes and mutates routes. | `simulations/flowpilot_router_loop_model.py`, tests, role cards only if needed | A worker cannot mark a node complete, bypass Reviewer, bypass PM, or convert a mechanical pass into semantic approval. |
| 5 | Provide fallback. If the fast lane is unavailable or rejects a state it cannot classify, existing Controller relay remains valid. | runtime/tests | Old Controller-mediated packet delivery still passes current tests. |

## Bug/Risk Checklist For FlowGuard

| Risk id | Possible bug | Model must catch | Runtime/test must catch |
| --- | --- | --- | --- |
| R1 | A non-holder role contacts Router for a packet. | `active_holder_contact_by_wrong_role` fails. | Runtime rejects `holder_role` mismatch. |
| R2 | A stale agent from an older run or packet submits a result. | `active_holder_contact_by_stale_agent` fails. | Runtime rejects `holder_agent_id` mismatch or missing lease. |
| R3 | Worker submits against an old route/frontier after mutation. | `active_holder_contact_after_stale_frontier` fails. | Runtime rejects stale `route_version` or `frontier_version`. |
| R4 | Worker uses fast lane before packet body was opened through packet runtime. | `fast_lane_result_before_packet_open` fails. | Result submission requires packet ledger open receipt. |
| R5 | Router routes result to Reviewer before result ledger absorption. | Existing result-ledger invariant plus fast-lane closure invariant fails. | Runtime rejects result relay notice without result absorption. |
| R6 | Mechanical rejection loop never returns to Controller or never terminates. | Progress/loop check catches closed nonterminal component. | Retry counter or same-holder reissue state is bounded. |
| R7 | Worker treats mechanical pass as semantic approval. | `fast_lane_mechanical_pass_marks_node_complete` fails. | Runtime/Router does not expose node-completion action to worker. |
| R8 | Controller is blind after fast-lane closure. | `fast_lane_closes_without_controller_notice` fails. | Packet ledger records next-action notice and holder/status history. |
| R9 | Controller reads, summarizes, or relays sealed body content during the fast lane. | Existing Controller body-boundary invariants still fail. | Existing contamination tests still pass. |
| R10 | A worker submits progress containing findings/evidence/sealed-body details. | Packet model treats progress as controller-visible metadata only. | Runtime rejects forbidden terms and oversized progress text. |
| R11 | Router accepts a result envelope that lacks required body/result aliases or output contract metadata. | Packet/result classification hazards fail. | Runtime validates `body_path`, `result_body_path`, result paths, and output contract. |
| R12 | Fast-lane fallback bypasses Reviewer/PM after a protocol blocker. | Repair/blocker hazards fail. | Runtime writes blocker/notice instead of next-holder success. |

## Proposed Implementation Sequence

1. Write this plan and use it as the acceptance checklist.
2. Upgrade `simulations/flowpilot_router_loop_model.py` with active-holder
   lease fields, safe transitions, and hazard states.
3. Update `simulations/run_flowpilot_router_loop_checks.py` so every risk above
   is represented as an expected failing hazard.
4. Run the router-loop model and confirm:
   - the safe graph still reaches success;
   - every listed fast-lane hazard is detected;
   - no stuck or nonterminating fast-lane loop exists.
5. Implement packet-runtime support for active-holder lease/check-in mechanics.
6. Add focused unit tests for accepted current-holder flow and rejected wrong,
   stale, missing, or overreaching flows.
7. Add Router integration only where needed to publish the controller-visible
   next-action notice.
8. Run focused tests after each slice, then run broader FlowPilot checks.
9. Sync the verified repository changes into the local installed FlowPilot
   skill, then verify install freshness. Do not push to GitHub.

## Acceptance Criteria

- Active-holder fast-lane behavior is represented in FlowGuard before runtime
  logic changes.
- Every risk in the checklist has either a model hazard, a runtime test, or
  both.
- Controller remains envelope-only and does not read sealed packet/result
  bodies.
- A current worker can complete mechanical result-envelope retries without
  Controller handling every retry.
- Cross-role handoff returns to Controller through a router-authored pending
  action/notice.
- Reviewer and PM semantic gates remain mandatory.
- Existing Controller-mediated packet flow remains valid.
- Local installed FlowPilot is refreshed from the repository and verified.
- GitHub remote is not pushed.
