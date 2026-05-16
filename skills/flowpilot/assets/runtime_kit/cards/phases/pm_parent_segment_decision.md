<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: System-card ACKs go directly to Router through the card check-in command; this is the router-directed return path for card ACKs. Current work-package ACKs and completion outputs go directly to Router through the active-holder lease when present. For formal role outputs, write the body only to a run-scoped packet, result, report, or decision file, then submit it with `flowpilot_runtime.py submit-output-to-router` so Router records the event and later exposes only controller-visible envelope metadata with status, paths, and hashes. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
post_ack: ACK is receipt only; ACK is not completion. This is a work item when it asks for an output, report, decision, result, or blocker. After work-card ACK, do not stop or wait for another prompt; immediately continue the work assigned by this card and submit the formal output or blocker through the Router-directed runtime path. The task remains unfinished until Router receives that output or blocker.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. System-card ACKs, current work-package outputs, and formal role-output submissions go directly to Router through their runtime commands. Controller must follow Router daemon status and the Controller action ledger; flowpilot_router.py next/run-until-wait are diagnostic or explicit repair tools only.
runtime_context: Treat the router delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; submit a protocol blocker through the Router-directed runtime path.
-->
# PM Parent Segment Decision Phase

## Role Capability Reminder

- Formal work products must live in run-scoped files or project artifacts. Handoff messages point to artifacts with paths/hashes, changed paths when applicable, output contract, inspection notes, and PM Suggestion Items; the message body is not the sole work product.
- PM may directly disposition suggestions when evidence is sufficient. Consultation is optional, not a mandatory step for every suggestion.
- If PM lacks basis, or the suggestion may affect route, product target, acceptance, process safety, replay, repair return path, or risk boundary, PM may request bounded consultation through an allowed role-work request, then must record a final PM disposition after reading the advice artifact.
- If a PM-owned decision still lacks evidence, modeling, research, review, or implementation support, register a bounded `pm_registers_role_work_request` only when the router's current `allowed_external_events` includes that event; otherwise record the limitation or blocker instead of emitting it.
- Treat the router's current `allowed_external_events` as the active authority for what this card may return.
- Put reviewer, worker, and officer advice that needs PM disposition into the PM suggestion/blocker ledger instead of leaving it only in prose.


After Reviewer passes local parent backward replay, record the PM segment
decision.

Before deciding, read the latest route-memory prior path context. The decision
must cite whether completed children, superseded children, stale evidence,
prior repairs, and experiments support continuing or require route mutation.

Allowed decisions:

- continue;
- repair existing child;
- add sibling child;
- rebuild child subtree;
- bubble to parent;
- PM stop.

Only `continue` can close the active parent node. Other decisions require route
mutation, stale evidence marking, and rerun of the same parent replay after
repair.

If repair affects sibling, ancestor, child-skill, or terminal evidence, record
those stale scopes now so the final ledger cannot count old passes as current.

## Decision Contract For This Task

Use contract `flowpilot.output_contract.pm_parent_segment_decision.v1`.

Return event: `pm_records_parent_segment_decision`.

Write the decision body to a run-scoped decision JSON file and return only a
runtime-generated role-output envelope with `body_ref` and
`runtime_receipt_ref`. Do not include the decision body in chat. Use
`flowpilot_runtime.py prepare-output` and `flowpilot_runtime.py submit-output-to-router`
for new submissions; legacy `decision_path`/`decision_hash` envelopes are
not the live handoff path.

Copy this body shape exactly. Use the current run id and current route-memory
paths from the router delivery envelope.

```json
{
  "schema_version": "flowpilot.parent_segment_decision.v1",
  "run_id": "<current-run-id>",
  "decision_owner": "project_manager",
  "decision": "continue",
  "prior_path_context_review": {
    "reviewed": true,
    "source_paths": [
      ".flowpilot/runs/<run-id>/route_memory/pm_prior_path_context.json",
      ".flowpilot/runs/<run-id>/route_memory/route_history_index.json"
    ],
    "completed_nodes_considered": [],
    "superseded_nodes_considered": [],
    "stale_evidence_considered": [],
    "prior_blocks_or_experiments_considered": [],
    "impact_on_decision": "Parent backward replay passed and current route memory does not require mutation.",
    "controller_summary_used_as_evidence": false
  },
  "decision_rationale": "The reviewer passed parent backward replay and the current prior-path context supports continuing.",
  "same_parent_replay_rerun_plan": null,
  "stale_evidence_to_mark": [],
  "superseded_nodes": [],
  "contract_self_check": {
    "all_required_fields_present": true,
    "exact_field_names_used": true,
    "empty_required_arrays_explicit": true,
    "current_run_route_memory_paths_cited": true
  }
}
```

Allowed `decision` values:

- `continue`
- `repair_existing_child`
- `add_sibling_child`
- `rebuild_child_subtree`
- `bubble_to_parent`
- `pm_stop`

For any decision other than `continue`, fill `decision_rationale`,
`stale_evidence_to_mark` or `superseded_nodes` when applicable, and
`same_parent_replay_rerun_plan` because the router will mutate the route and
require the same parent replay again.
