<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: System-card ACKs go directly to Router through the card check-in command; this is the router-directed return path for card ACKs. Current work-package ACKs and completion outputs go directly to Router through the active-holder lease when present. For formal role outputs, write the body only to a run-scoped packet, result, report, or decision file, then submit it with `flowpilot_runtime.py submit-output-to-router` so Router records the event and later exposes only controller-visible envelope metadata with status, paths, and hashes. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. System-card ACKs, current work-package outputs, and formal role-output submissions go directly to Router through their runtime commands. Controller must wait for Router status or call flowpilot_router.py for the next action.
runtime_context: Treat the router delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; submit a protocol blocker through the Router-directed runtime path.
-->
# PM Officer Request-Report Loop

## Role Capability Reminder

- Formal work products must live in run-scoped files or project artifacts. Handoff messages point to artifacts with paths/hashes, changed paths when applicable, output contract, inspection notes, and PM Suggestion Items; the message body is not the sole work product.
- PM may directly disposition suggestions when evidence is sufficient. Consultation is optional, not a mandatory step for every suggestion.
- If PM lacks basis, or the suggestion may affect route, product target, acceptance, process safety, replay, repair return path, or risk boundary, PM may request bounded consultation through an allowed role-work request, then must record a final PM disposition after reading the advice artifact.
- If a PM-owned decision still lacks evidence, modeling, research, review, or implementation support, register a bounded `pm_registers_role_work_request` only when the router's current `allowed_external_events` includes that event; otherwise record the limitation or blocker instead of emitting it.
- Treat the router's current `allowed_external_events` as the active authority for what this card may return.
- For a blocked PM-owned decision, choose the smallest valid path among repair, sender reissue, route mutation, evidence quarantine, or user stop; do not skip required recheck.


Use FlowGuard officers through bounded request and report packets.

Each officer request packet must include the registry `output_contract`
`flowpilot.output_contract.officer_model_report.v1` in both the packet envelope
and packet body's `Output Contract` section.
The packet body must also include the generated `Report Contract For This Task`
block so the officer sees the exact report fields before modeling.
The packet body must also ask the officer to include a soft `PM Note` in the
sealed report body with exactly these labels: `In-scope quality choice` and
`PM consideration`. This note is PM decision-support, not a reviewer hard gate:
the officer should use the simplest high-quality modeling boundary that answers
PM's request, and report out-of-scope better ideas, route risks, or model
improvements to PM without expanding the packet.
The packet body must also require a `PM Suggestion Items` section. Officer
suggestions are candidate `flowpilot.pm_suggestion_item.v1` items for PM's
ledger disposition. They become `current_gate_blocker` items only for formal
model-gate findings inside PM's requested model boundary.

For each modeling need, write a request that states:

- process, product, or joint officer ownership;
- modeling kind: process, product, object/reference-system, migration
  equivalence, experiment-derived behavior, or combined;
- for model-miss work, the bug class definition, why the old model may have
  missed it, same-class search boundary, candidate repair comparison boundary,
  and post-repair model checks the PM needs before reviewer recheck;
- model boundary, hard invariants, observed/source behavior, expected target
  behavior, and decisions the PM needs;
- for product-model-first route design, whether the officer report should
  define product behavior for PM route drafting, validate PM route viability
  against that behavior, or check a repair branch's return to the mainline;
- required commands or replay checks;
- evidence paths, source materials, samples, traces, or experiment outputs the
  officer may inspect;
- how the report can change the route.

The officer report body must include these fields exactly:

```json
{
  "schema_version": "flowpilot.officer_model_report.v1",
  "run_id": "<current run id>",
  "modeled_boundary": "<scope modeled>",
  "commands_run": [],
  "counterexamples_or_absence": "<counterexample summary or explicit absence>",
  "hard_invariants": [],
  "skipped_checks": [],
  "confidence_boundary": "<what this model does and does not prove>",
  "pm_suggestion_items": [],
  "contract_self_check": {
    "all_required_fields_present": true,
    "exact_field_names_used": true,
    "empty_required_arrays_explicit": true
  }
}
```

The officer report supports PM decisions; it cannot approve completion, waive
reviewer gates, or claim no risk beyond its model boundary.

PM must convert the report into a concrete route decision: continue, repair,
add evidence, split a node, mutate the route, or block. A report that only says
the model ran, without telling PM how it changes route or node design, is not
sufficient.

For model-miss reports that support `pm.model_miss_triage`, include these
additional fields exactly:

```json
{
  "old_model_miss_reason": "<why the old model did not catch this bug class>",
  "bug_class_definition": "<same-class definition>",
  "same_class_findings": [],
  "coverage_added": [],
  "candidate_repairs": [],
  "minimal_sufficient_repair_recommendation": {},
  "rejected_larger_repairs": [],
  "rejected_smaller_repairs": [],
  "post_repair_model_checks_required": [],
  "residual_blindspots": []
}
```
