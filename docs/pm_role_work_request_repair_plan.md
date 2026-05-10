# PM Role Work Request Repair Plan

Date: 2026-05-10

## Goal

Add an always-available PM-to-role work request channel so the project manager
can ask another FlowPilot role for information, modeling, review, evidence, or
implementation support before making a decision. The router should not judge the
request body. It should enforce the envelope, recipient role, output contract,
packet ledger, result return, and PM absorption state.

This is a model-first repair. Production router changes must start only after
the FlowGuard model proves the planned protocol and catches the risk cases
listed below.

## Optimization Sequence

| Step | Change | Concrete outcome | Verification |
| --- | --- | --- | --- |
| 1 | Document the PM work-request protocol | This file records the intended behavior, risk list, and verification plan | Review this checklist before production edits |
| 2 | Upgrade the decision-liveness FlowGuard model | Model an always-open PM role-work-request channel, blocking/advisory requests, report return, PM absorption, controlled user stop, and model-miss decisions mapped to that channel | `python simulations\run_flowpilot_decision_liveness_checks.py --json-out simulations\flowpilot_decision_liveness_results.json` |
| 3 | Prove hazards are caught before code edits | Known-bad states for dead-end decisions, missing contracts, invalid recipients, lost outstanding requests, premature PM final decisions, duplicate request ids, and Controller body reads must all fail | Hazard section in `flowpilot_decision_liveness_results.json` |
| 4 | Implement the smallest router primitive | Add PM role-work-request event, request ledger, generic packet creation, next-action relay, result return event, result relay to PM, and PM absorption event | Focused router runtime tests |
| 5 | Map existing model-miss nonterminal decisions to the primitive | `request_officer_model_miss_analysis` opens a blocking officer model-miss request; `needs_evidence_before_modeling` opens or requires a PM work request; `stop_for_user` records a controlled pause | Model-miss focused tests |
| 6 | Preserve existing repair behavior | Repair-authorizing decisions still unlock `pm.review_repair` only after required officer report evidence; route mutation still requires closed model-miss triage | Existing model-miss and repair tests |
| 7 | Run scoped and broader checks | Compile, focused router tests, decision-liveness checks, adjacent router-loop checks, and practical fast meta/capability checks | Command results recorded in adoption log |
| 8 | Sync local installation and local git only | Install local FlowPilot skill from this repository and stage/commit locally; do not push to GitHub | `install_flowpilot.py --sync-repo-owned`, install check, local git status/commit |

## Required Behavior

| Requirement | Meaning |
| --- | --- |
| Always-open PM channel | Whenever PM is the current decision owner, PM may open a role work request before finalizing the decision. |
| Router is envelope-only | Router records and relays request/result envelopes, ids, paths, hashes, recipients, and contracts. It must not read or summarize sealed bodies. |
| Request ledger is source of truth | Every PM request has a durable `request_id`, status, recipient, output contract, blocking/advisory mode, packet path, result path, and PM absorption state. |
| Blocking requests block dependent PM final decisions | PM may keep issuing other requests, but cannot claim a blocking request result before it returns and is absorbed. |
| Advisory requests do not freeze progress | PM can continue, but the returned result must be absorbed, canceled, or superseded before terminal closure. |
| Results return to PM by default | Role outputs produced for PM work requests go back to PM, not directly to repair, route mutation, reviewer pass, or completion. |
| Model-miss uses the generic channel | Officer model-miss analysis is one use of the generic channel, not a one-off special patch. |
| User stop is explicit | `stop_for_user` records a controlled pause/user stop. It must not loop back to the same PM triage event. |

## Risk List and Model Coverage

| Risk id | Possible bug introduced by this repair | FlowGuard model must catch it by |
| --- | --- | --- |
| R1 | PM legal decision is accepted but no next channel opens | Invariant: accepted nonterminal PM decision must open role-work request or controlled pause |
| R2 | Router accepts a PM work request without a recipient role | Hazard: request registered with missing/invalid recipient fails |
| R3 | Router accepts a PM work request without an output contract | Hazard: request registered without contract fails |
| R4 | Controller reads or summarizes sealed request/result body | Hazard: controller body read fails |
| R5 | Blocking request is outstanding but PM records a dependent final repair/route decision | Hazard: premature PM final decision fails |
| R6 | Advisory request returns but is never absorbed, canceled, or superseded before terminal closure | Hazard: terminal closure with unresolved advisory result fails |
| R7 | Request result is routed to PM before packet-ledger check | Hazard: result relay without ledger check fails |
| R8 | Result is accepted from the wrong role or for the wrong request id | Hazard: result identity/request mismatch fails |
| R9 | Duplicate request id overwrites an open request | Hazard: duplicate open request id fails |
| R10 | `request_officer_model_miss_analysis` becomes a special patch instead of generic PM work request | Static audit: model-miss officer request must be represented as generic PM role-work request |
| R11 | `needs_evidence_before_modeling` still loops back to the same PM event | Static audit and hazard: evidence decision must open PM work request or explicit wait channel |
| R12 | `stop_for_user` still loops back to the same PM event | Static audit and hazard: user stop must create controlled pause |
| R13 | Repair-authorizing model-miss decisions start repair without officer model-miss evidence | Hazard: model-backed repair without PM-reviewed officer report fails |
| R14 | Existing route mutation/repair gates are weakened | Existing router tests and router-loop model must still pass |

## Minimal Implementation Boundary

The first production patch should avoid broad architecture churn:

- Add a generic PM work request ledger under the run root, such as
  `pm_work_requests/index.json`.
- Add a PM event for registering a request packet.
- Add a role result event for returning a request result envelope.
- Add a PM event for absorbing, canceling, or superseding a request result.
- Reuse `packet_runtime.create_packet`, packet ledger relay, and sealed-body
  rules.
- Keep request bodies sealed to the target role.
- Keep result bodies sealed until PM opens them.
- Do not change unrelated route planning, UI, or release logic.

## Non-Goals

- Do not push to GitHub in this task.
- Do not replace all existing material/research/current-node packet flows.
- Do not allow Controller to spawn role work without PM request authority.
- Do not auto-apply officer or worker results to the route without PM decision.
