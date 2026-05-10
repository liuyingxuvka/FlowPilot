# Direct Packet Dispatch Optimization Plan

## Goal

Remove reviewer pre-dispatch review from PM-authored work packets. PM work
packets should go directly from router/runtime mechanical validation to the
target role. Reviewers remain responsible for worker result quality, stage
gates, and PM decision challenges, not for packet-envelope dispatch approval.

## Optimization Checklist

| Step | Change | Concrete Target | Done When |
| --- | --- | --- | --- |
| 1 | Record the direct-dispatch contract | This document and FlowGuard adoption notes | The intended behavior and risk coverage are explicit before production code changes |
| 2 | Upgrade the packet control FlowGuard model | `skills/flowpilot/assets/packet_control_plane_model.py` and runner labels | Model has a direct router dispatch transition and catches invalid packet-envelope hazards |
| 3 | Prove model hazard coverage | `skills/flowpilot/assets/run_packet_control_plane_checks.py` | Known-bad packet cases fail before worker result creation or PM advance |
| 4 | Strengthen runtime/router mechanical preflight | Packet relay path in `flowpilot_router.py` and/or `packet_runtime.py` | Direct relay checks envelope fields, body hash, target role, contract, sealed visibility, and result paths |
| 5 | Remove reviewer dispatch from PM work packet flow | Material scan and current-node packet next-action logic | PM packet issuance leads to packet relay after ledger check, not `reviewer.dispatch_request` |
| 6 | Keep result review intact | Result relay and reviewer result cards | Worker results still go to reviewer before PM may use them |
| 7 | Update tests and docs | Focused router/runtime tests plus preflight docs | Old "requires reviewer dispatch" tests become direct-dispatch tests |
| 8 | Sync local installation and local git | `scripts/install_flowpilot.py --sync-repo-owned`, checks, local commit | Installed skill is source-fresh and changes are committed locally without remote push |

## Bug/Risk Coverage Checklist

| Risk ID | Potential Bug From Optimization | Required Guard | FlowGuard Coverage Target |
| --- | --- | --- | --- |
| R1 | Worker packet is relayed without a packet envelope check | Router direct-dispatch preflight must record envelope check | Invariant: dispatch requires packet envelope check |
| R2 | Worker packet body hash mismatch reaches worker | Router preflight blocks before dispatch | Hazard case: `body_hash_mismatch_packet` blocks |
| R3 | Packet envelope/body hash identity drifts from ledger | Router preflight blocks before dispatch | Hazard case: `body_hash_identity_stale_packet` blocks |
| R4 | Packet is delivered to the wrong role | Router relay target must match envelope `to_role` | Hazard case: `wrong_delivery_packet` blocks |
| R5 | Packet lacks an output contract | Router preflight blocks before dispatch | Hazard case: `missing_output_contract_packet` blocks |
| R6 | Output contract recipient does not match `to_role` | Runtime contract validation blocks before dispatch | Hazard case: `contract_recipient_mismatch_packet` blocks |
| R7 | Result paths escape the run packet directory | Router preflight blocks before dispatch | Hazard case: `result_path_escape_packet` blocks |
| R8 | Controller reads or executes packet body while direct dispatching | Controller contamination still returns packet to sender | Existing hazard cases continue to block |
| R9 | Worker result bypasses reviewer after direct dispatch | Result relay and PM advance still require reviewer pass | Invariant: PM advance requires reviewer pass |
| R10 | Heartbeat/manual resume creates fresh packets without PM decision | Resume packet path still requires PM request and loaded state | Existing heartbeat invariants remain required |

## Explicit Non-Goals

| Item | Reason |
| --- | --- |
| Reviewer semantic pre-dispatch judgement | The optimization intentionally removes this wait point. Semantic adequacy is checked through PM packet authorship, worker execution boundaries, and reviewer result/stage review. |
| Remote GitHub synchronization | The user requested local repository, local installation, and local git only. |
| Active run state mutation | This side task must not mutate the currently running `.flowpilot/runs/<run-id>` control state. |

## FlowGuard Applicability

- Decision: `use_flowguard`
- Lens: `behavior_flow`
- Mode: `model_first_change`
- Risk intent: prevent direct-dispatch optimization from letting malformed,
  wrong-role, stale, controller-contaminated, or unverifiable packets reach
  workers or PM completion while removing only the reviewer pre-dispatch wait.
