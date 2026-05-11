<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: System-card ACKs go directly to Router through the card check-in command. For formal role outputs, write the body only to a run-scoped packet, result, report, or decision file, then return only the Router-directed controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. System-card ACKs go directly to Router; after formal role output completion or blocking, use the Router-directed return path. Controller must wait for or call flowpilot_router.py for the next action.
runtime_context: Treat the router delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; return a protocol blocker through Controller.
-->
# PM Model-Miss Triage Phase

## Role Capability Reminder

- Formal work products must live in run-scoped files or project artifacts. Handoff messages point to artifacts with paths/hashes, changed paths when applicable, output contract, inspection notes, and PM Suggestion Items; the message body is not the sole work product.
- PM may directly disposition suggestions when evidence is sufficient. Consultation is optional, not a mandatory step for every suggestion.
- If PM lacks basis, or the suggestion may affect route, product target, acceptance, process safety, replay, repair return path, or risk boundary, PM may request bounded consultation through an allowed role-work request, then must record a final PM disposition after reading the advice artifact.
- Treat the router's current `allowed_external_events` as the active authority for what this card may return.
- Put reviewer, worker, and officer advice that needs PM disposition into the PM suggestion/blocker ledger instead of leaving it only in prose.


Current state contains a reviewer block. Before normal repair planning, close
the model-miss obligation: ask why the existing FlowGuard model did not catch
this bug class.

Do not route directly to repair from the single observed failure. First decide
whether this bug class is within FlowGuard capability.

If it is modelable:

- issue a bounded FlowGuard officer request for the bug class, not just the
  current error message;
- require the officer report to state why the old model missed it, what same
  class means, which same-class findings were discovered, what coverage was
  added, which repair candidates were compared, and which repair is minimal and
  sufficient;
- use the officer report as PM decision support only. PM still owns the repair
  path and route decision;
- authorize repair only after the report also names the post-repair model
  checks that must pass before reviewer recheck.

If it is not modelable, record the concrete incapability reason before repair
can proceed.

Allowed PM decisions:

- request officer model-miss analysis;
- proceed with model-backed repair;
- mark out of scope / not modelable and proceed by another route;
- request evidence before modeling;
- stop for user.

When choosing `request_officer_model_miss_analysis` or
`needs_evidence_before_modeling`, do not wait for a special-purpose router
path. Register the follow-up work through the generic PM role-work channel:
`pm_registers_role_work_request`. Select a concrete target role, request mode,
request kind, output contract, and sealed file-backed request body. Controller
will relay the packet and result envelopes only; PM must later record
`pm_records_role_work_result_decision` after the result returns.

## Decision Contract For This Task

Use contract `flowpilot.output_contract.pm_model_miss_triage_decision.v1`.
Return it through router event `pm_records_model_miss_triage_decision`.

Write the full PM decision body to a run-scoped decision file. Return in chat
only a controller-visible envelope with the decision path and hash.

Use these exact field names:

```json
{
  "schema_version": "flowpilot.pm_model_miss_triage_decision.v1",
  "run_id": "<current run id>",
  "decided_by_role": "project_manager",
  "decision": "proceed_with_model_backed_repair",
  "defect_or_blocker_id": "<stable id>",
  "reviewer_block_source_path": "<path to reviewer block or router state>",
  "model_miss_scope": {
    "bug_class_definition": "<one class, not just one error>",
    "representative_current_failure": "<short summary>",
    "same_class_search_boundary": []
  },
  "flowguard_capability": {
    "can_model_bug_class": true,
    "incapability_reason": null
  },
  "officer_report_refs": [
    {
      "officer_role": "process_flowguard_officer",
      "report_path": "<path>",
      "report_hash": "<sha256>"
    }
  ],
  "same_class_findings_reviewed": true,
  "repair_recommendation_reviewed": true,
  "candidate_repairs_considered": [],
  "minimal_sufficient_repair_recommendation": {},
  "post_repair_model_checks_required": [],
  "selected_next_action": "<repair route PM selected>",
  "why_repair_may_start": "<why the model-miss obligation is closed>",
  "blockers": [],
  "contract_self_check": {
    "all_required_fields_present": true,
    "exact_field_names_used": true,
    "empty_required_arrays_explicit": true
  }
}
```

Router will not deliver `pm.review_repair` until this contract authorizes a
model-backed repair or records an explicit out-of-scope FlowGuard reason.
