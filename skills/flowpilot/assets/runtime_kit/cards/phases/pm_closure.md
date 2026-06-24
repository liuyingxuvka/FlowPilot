<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: System-card ACKs go through the current runtime card check-in command; this is the current-runtime return path for card ACKs. Current work-package ACKs and completion outputs go through the assigned current packet lease when present. For formal role outputs, write the body only to a run-scoped packet, result, report, decision, or blocker file, then submit it with `flowpilot_new.py submit-result --lease-id <lease-id> --packet-id <packet-id> --body <sealed_result_summary>` so the current runtime ledger records the event and later exposes only controller-visible envelope metadata with status, paths, and hashes. A local file write is only local storage and must not be treated as wait completion until the current runtime records the packet result. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
post_ack: ACK is receipt only; ACK is not completion. This is a work item when it asks for an output, report, decision, result, or blocker. After work-card ACK, do not stop or wait for another prompt; immediately continue the assigned work and submit the formal output or blocker through the current runtime path. The task remains unfinished until the current runtime receives that output or blocker.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. System-card ACKs, current work-package outputs, and formal role-output submissions go directly through the current runtime commands. Controller must follow the `flowpilot_new.py` lifecycle guard and foreground duty; no unsupported command text, stale runtime state, chat history, or historical artifact authorizes current-run progress.
runtime_context: Treat the runtime delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; submit a protocol blocker through the current runtime path.
-->
# PM Closure Phase

## Role Capability Reminder

- Formal work products must live in run-scoped files or project artifacts. Handoff messages point to artifacts with paths/hashes, changed paths when applicable, output contract, inspection notes, and PM Suggestion Items; the message body is not the sole work product.
- PM may directly disposition suggestions when evidence is sufficient. Consultation is optional, not a mandatory step for every suggestion.
- If PM lacks basis, or the suggestion may affect route, product target, acceptance, process safety, replay, repair return path, or risk boundary, PM may request bounded consultation through an allowed role-work request, then must record a final PM disposition after reading the advice artifact.
- If a PM-owned decision still lacks evidence, modeling, research, review, or implementation support, register a bounded `pm_registers_role_work_request` only when the router's current `allowed_external_events` includes that event; otherwise record the limitation or blocker instead of emitting it.
- Treat the router's current `allowed_external_events` as the active authority for what this card may return.
- Put reviewer, worker, and FlowGuard operator advice that needs PM disposition into the PM suggestion/blocker ledger instead of leaving it only in prose.
- For non-trivial closure, lifecycle, model-coverage, validation, evidence-freshness, or final-user outcome judgement, cite FlowGuard Work Order and FlowGuard Report ids with freshness and PM acceptance, or record a scoped `flowguard_not_required_reason`.
- In mature FlowGuard projects, read `docs/flowguard_project_topology.md` as background architecture before terminal closure and confirm it was rebuilt and checked after any topology-affecting model, test, code, prompt/card, install, or readiness change. It is not a FlowGuard Report, is not gate evidence, and cannot close a FlowGuard or validation gap.


Close only after final ledger and backward replay pass.
Closure also requires the final ledger to show zero unresolved active
acceptance items and the terminal backward replay to pass every
`acceptance_item` segment the runtime issued. PM may not approve closure while
any user-sourced or PM high-standard item lacks direct evidence, reviewer or
FlowGuard gate closure, valid waiver authority, or final replay coverage.
If terminal supplemental repair was entered, PM may approve normal closure only
when `terminal_supplemental_repair.status` is `clean` and every
`supplemental_repair_closure` row is covered. `repair_rounds_exhausted` is a
terminal stop state, not a completion approval. Do not reopen a fourth repair
round from closure; record the exhausted summary and stop.
Closure also requires all active FlowGuard Work Orders to be closed by current
FlowGuard Reports that PM accepted, or explicitly dispositioned by PM with a
scoped waiver, deferral, quarantine, or user stop. Missing, stale, skipped,
progress-only, blocked, or unaccepted FlowGuard reports block terminal
closure.
Closure also requires the runtime final ledger's
`flowguard_terminal_coverage_closure` to be clean and the terminal Reviewer to
have passed the `flowguard-coverage-governance` replay segment. PM may not
approve terminal closure from scattered node-level FlowGuard notes, stale
reports, progress-only logs, unaccepted reports, unresolved model-test gaps, or
undispositioned FlowGuard PM suggestion items.
Closure also requires all active target-realization obligations from
`flowguard/target_realization_model.json` to be dispositioned in the final
ledger. PM cannot close by saying the route ran if a thin-success trap,
non-downgrade rule, or evidence gate from the target-realization model remains
unproved, stale, waived without authority, or unresolved.
Read the latest route-memory prior path context before closure. Closure must
not rely on a stale view of completed nodes, superseded nodes, stale evidence,
route mutations, terminal replay, or lifecycle state.
Before approval, PM must self-check the delivered product or final output from
the final user's, reader's, operator's, maintainer's, or recipient's point of
view. Closure is blocked by a hard user-intent failure, unusable outcome,
semantic downgrade, missing proof, or unverifiable user-facing quality claim.
Better but nonessential experience, simplicity, or quality opportunities must
be dispositioned as PM suggestion items before closure.
Closure also requires `self_interrogation_index.json` to be clean. Do not
approve terminal closure while any startup, product-architecture, node-entry,
repair, completion, or role-result self-interrogation record has an unresolved
hard/current finding.
If terminal closure is blocked by a router `control_blocker`, read the policy
row and treat it as PM recovery work. PM may rebuild terminal evidence, roll
back to the final ledger or affected replay segment, quarantine stale evidence,
mutate the route, or stop for the user. Do not close the run by waiver when the
policy row lists hard-stop conditions.
PM must also self-check hard low-quality-success risks. Closure is blocked
when a task-specific hard part was closed only by artifact existence, report
prose, a screenshot, a command run, or a clean ledger row instead of proof of
depth. Nonessential quality improvements stay in PM suggestion disposition and
do not become surprise hard blockers.
PM must also self-check shallow-completion traps from the final user's point of
view. Closure is blocked when the delivered output still only looks complete
because it contains a design, definition, report, ledger row, file existence
proof, screenshot, or command record while the practical next step implied by
the accepted user outcome remains undefined. Do not add a new closure schema
for this check; use the existing `final_user_outcome_replay`,
`hard_user_intent_failures`, PM suggestion, blocker, waiver, repair, or route
mutation paths to disposition each current trap. If the route was explicitly
planning-only, the final report must preserve that boundary and must not claim
runnable, operational, or implementation-ready completion.
PM must also self-check structural convergence. Closure is blocked while the
final ledger has unresolved structure debt, unowned fallback-like paths,
compatibility branches, duplicate adapters, stale generated artifacts,
non-current evidence, or maintenance layers without owner, scope, validation
evidence, and sunset or next-disposition criteria. Historical context and
negative rejection evidence must stay separate from current completion
evidence.
PM must also self-check final artifact hygiene. Closure is blocked while any
`current_goal_required_repair` or `clean_delivery_required_repair` hygiene
finding remains unresolved in the final ledger or latest terminal Reviewer
replay. Nonblocking hygiene opportunities must have PM disposition before
closure, but they do not require a repair node unless PM imports them into the
current supplemental repair contract.
PM must also accept the runtime's final-quality evidence classification.
Invalid final matrix rows, blocked review ids, stale/progress-only FlowGuard
ids, failed validation ids, and terminal replay target mismatches are closure
blockers until repaired through the existing current-runtime path.

Closure order:

1. reconcile state, frontier, route, current pointer, and run index;
2. reconcile pause, stopped, resumed, and terminal lifecycle records;
3. confirm there is no pending manual-resume lifecycle duty or foreground
   patrol obligation;
4. archive role binding and role memory without treating archived roles as live;
5. write nonblocking FlowPilot skill-improvement observations;
6. record PM completion decision;
7. emit final report.

Completion cannot list unresolved risks as accepted completion payload.
If closure evidence disagrees with the current pointer, frontier, lifecycle
guard, status projection, or run index, block closure and repair lifecycle
state first.

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
`flowpilot_new.py open-packet` and `flowpilot_new.py submit-result --lease-id <lease-id> --packet-id <packet-id> --body <sealed_result_summary>`
for submissions; plain `decision_path`/`decision_hash` envelopes are
not the live handoff path.

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
    "role_assignment_and_lease_state_current": true,
    "continuation_binding_current": true,
    "current_ledgers_clean": true,
    "pm_suggestion_ledger_clean": true,
    "self_interrogation_index_clean": true,
    "flowguard_terminal_coverage_closure_clean": true
  },
  "final_user_outcome_replay": {
    "reviewed": true,
    "delivered_output_satisfies_user_intent": true,
    "user_facing_claims_have_evidence": true,
    "hard_low_quality_success_risks_dispositioned": true,
    "existence_only_hard_part_closures": [],
    "hard_user_intent_failures": [],
    "nonblocking_higher_standard_opportunities_dispositioned": true
  },
  "structure_convergence_replay": {
    "reviewed": true,
    "final_ledger_structure_debt_dispositions_present": true,
    "unresolved_structure_debt_count": 0,
    "unowned_fallback_like_paths": [],
    "compatibility_branches_retained": [],
    "old_artifacts_used_as_current_completion_evidence": false,
    "retained_surfaces_have_owner_scope_validation_and_sunset": true
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
