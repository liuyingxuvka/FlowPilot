<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write any role-output body only to a run-scoped packet, result, report, or decision file, then return to Controller only a controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
runtime_context: Treat the router delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; return a protocol blocker through Controller.
-->
# PM Closure Phase

## Role Capability Reminder

- If a PM-owned decision still lacks evidence, modeling, research, review, or implementation support, register a bounded `pm_registers_role_work_request` only when the router's current `allowed_external_events` includes that event; otherwise record the limitation or blocker instead of emitting it.
- Treat the router's current `allowed_external_events` as the active authority for what this card may return.
- Put reviewer, worker, and officer advice that needs PM disposition into the PM suggestion/blocker ledger instead of leaving it only in prose.


Close only after final ledger and backward replay pass.
Read the latest route-memory prior path context before closure. Closure must
not rely on a stale view of completed nodes, superseded nodes, stale evidence,
route mutations, terminal replay, or lifecycle state.

Closure order:

1. reconcile state, frontier, route, current pointer, and run index;
2. reconcile pause, stopped, resumed, and terminal lifecycle records;
3. stop heartbeat or record manual-resume no-automation evidence;
4. archive crew and role memory without treating archived roles as live;
5. write nonblocking FlowPilot skill-improvement observations;
6. record PM completion decision;
7. emit final report.

Completion cannot list unresolved risks as accepted completion payload.
If closure evidence disagrees with the current pointer, frontier, heartbeat, or
run index, block closure and repair lifecycle state first.

Apply Minimum Sufficient Complexity before final approval. The completion
decision must not depend on unused route branches, unconsumed generated
resources, leftover skill invocations, or broad artifacts that never changed
the delivered product or verification confidence. Close only after they are
resolved by the final ledger as consumed, superseded, quarantined, or discarded
with reason.

## Decision Contract For This Task

Use contract `flowpilot.output_contract.pm_terminal_closure_decision.v1`.

Return event: `pm_approves_terminal_closure`.

Write the closure decision body to a run-scoped decision JSON file and return
only a runtime-generated role-output envelope with `body_ref` and
`runtime_receipt_ref`. Do not include the decision body in chat. Use
`flowpilot_runtime.py prepare-output` and `flowpilot_runtime.py submit-output`
for new submissions; legacy `decision_path`/`decision_hash` envelopes are
compatibility inputs only.

Copy this body shape exactly. Use the current run id and current route-memory
paths from the router delivery envelope.

```json
{
  "schema_version": "flowpilot.terminal_closure_decision.v1",
  "run_id": "<current-run-id>",
  "approved_by_role": "project_manager",
  "decision": "approve_terminal_closure",
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
    "impact_on_decision": "Clean final ledger, passed terminal backward replay, and current route memory support terminal closure.",
    "controller_summary_used_as_evidence": false
  },
  "lifecycle_reconciliation": {
    "final_route_wide_gate_ledger_clean": true,
    "terminal_backward_replay_passed": true,
    "task_completion_projection_ready_for_pm_terminal_closure": true,
    "execution_frontier_current": true,
    "crew_ledger_current": true,
    "continuation_binding_current": true,
    "current_ledgers_clean": true
  },
  "final_report": {},
  "contract_self_check": {
    "all_required_fields_present": true,
    "exact_field_names_used": true,
    "empty_required_arrays_explicit": true,
    "current_run_route_memory_paths_cited": true
  }
}
```

Allowed `decision` value:

- `approve_terminal_closure`
