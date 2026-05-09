<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write any role-output body only to a run-scoped packet, result, report, or decision file, then return to Controller only a controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
runtime_context: Treat the router delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; return a protocol blocker through Controller.
-->
# PM Parent Segment Decision Phase

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
`flowpilot_runtime.py prepare-output` and `flowpilot_runtime.py submit-output`
for new submissions; legacy `decision_path`/`decision_hash` envelopes are
compatibility inputs only.

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
