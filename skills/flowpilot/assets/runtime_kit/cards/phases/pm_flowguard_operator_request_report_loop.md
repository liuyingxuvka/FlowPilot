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
# PM FlowGuard Operator Request-Report Loop

## Role Capability Reminder

- Formal work products must live in run-scoped files or project artifacts. Handoff messages point to artifacts with paths/hashes, changed paths when applicable, output contract, inspection notes, and PM Suggestion Items; the message body is not the sole work product.
- PM may directly disposition suggestions when evidence is sufficient. Consultation is optional, not a mandatory step for every suggestion.
- If PM lacks basis, or the suggestion may affect route, product target, acceptance, process safety, replay, repair return path, or risk boundary, PM may request bounded consultation through an allowed role-work request, then must record a final PM disposition after reading the advice artifact.
- If a PM-owned decision still lacks evidence, modeling, research, review, or implementation support, register a bounded `pm_registers_role_work_request` only when the router's current `allowed_external_events` includes that event; otherwise record the limitation or blocker instead of emitting it.
- Treat the router's current `allowed_external_events` as the active authority for what this card may return.
- For a blocked PM-owned decision, choose the smallest valid path among repair, sender reissue, route mutation, evidence quarantine, or user stop; do not skip required recheck.
- FlowGuard operator modeling requests are FlowGuard Work Orders. Every non-trivial request must carry `flowguard_work_order_id`, expected `flowguard_report_id` or report path, `flowguard_report_freshness`, affected gate, and PM acceptance expectations.


Use the FlowGuard operator through bounded request and report packets.

This loop is the common FlowGuard Work Order / FlowGuard Report mechanism for
formal product, process, validation, model-test, TestMesh, StructureMesh,
Model Miss Review, repair, resume, and closure-readiness questions. Do not let
separate phase prose replace the work-order id, report id, report freshness,
route used, skipped-check reasoning, background completion evidence, or PM
acceptance record.

Each FlowGuard operator request packet must include the registry `output_contract`
`flowpilot.output_contract.flowguard_operator_model_report.v1` in both the packet envelope
and packet body's `Output Contract` section.
The packet body must also include the generated `Report Contract For This Task`
block so the FlowGuard operator sees the exact report fields before modeling.
The packet body must also ask the FlowGuard operator to include a soft `PM Note` in the
sealed report body with exactly these labels: `In-scope quality choice` and
`PM consideration`. This note is PM decision-support, not a reviewer hard gate:
the FlowGuard operator should use the simplest high-quality modeling boundary that answers
PM's request, and report out-of-scope better ideas, route risks, or model
improvements to PM without expanding the packet.
The packet body must include the FlowGuard operator version of the
`Role-Scoped Quality Repair Boundary`: the FlowGuard operator must correct defects in the
FlowGuard operator's own model, report, check command, counterexample interpretation,
skipped-check reasoning, and evidence before returning. Product, process, route,
implementation, or authority defects are formal findings, model blockers, or
PM Suggestion Items unless PM explicitly granted bounded target repair in
allowed writes.
The packet body must also require a `PM Suggestion Items` section. FlowGuard operator
suggestions are candidate `flowpilot.pm_suggestion_item.v1` items for PM's
ledger disposition. They become `current_gate_blocker` items only for formal
model-gate findings inside PM's requested model boundary.

For each modeling need, write a request that states:

- process-model, product-model, or joint FlowGuard operator ownership;
- modeling kind: process, product, object/reference-system, migration
  equivalence, experiment-derived behavior, or combined;
- the exact current subject to simulate: the current route draft, staged
  `route_plan`, node context package, repair plan, validation plan, blocker,
  or closure package. For route or node process work, ask the FlowGuard
  operator to simulate the route traversal, work dispatch path,
  validation/check path, failure/blocker path, repair return path, stale
  evidence handling, and closure path for that subject;
- for model-miss work, the bug class definition, why the old model may have
  missed it, same-class search boundary, candidate repair comparison boundary,
  and post-repair model checks the PM needs before reviewer recheck;
- model boundary, hard invariants, observed/source behavior, expected target
  behavior, and decisions the PM needs;
- model-test alignment expectations: `model_obligations`,
  `ordinary_test_evidence`, `missing_test_kinds`, `conformance_boundary`,
  `residual_blindspots`, and `background_artifact_completion`;
- `role_skill_use_bindings` for every FlowGuard child skill or satellite route
  PM expects the FlowGuard operator to use when deriving test obligations or validation
  gaps. Use the smallest applicable route: Existing Model Preflight for model
  ownership, DevelopmentProcessFlow for validation freshness and staged
  process risk, Model-Test Alignment for model/code/test comparison, and
  TestMesh for broad, slow, layered, stale, skipped, progress-only, or
  release-only validation;
- for product-model-first route design, whether the FlowGuard operator report should
  define product behavior for PM route drafting, validate PM route viability
  against that behavior, or check a repair branch's return to the mainline;
- required commands or replay checks;
- evidence paths, source materials, samples, traces, or experiment outputs the
  FlowGuard operator may inspect;
- how the report can change the route.

The FlowGuard operator report body must include these fields exactly:

```json
{
  "schema_version": "flowpilot.flowguard_operator_model_report.v1",
  "run_id": "<current run id>",
  "flowguard_work_order_id": "<work-order id>",
  "flowguard_report_id": "<report id>",
  "flowguard_route_used": "<FlowGuard route or satellite skill>",
  "flowguard_report_freshness": "<current, stale, blocked, skipped, or progress_only>",
  "modeled_boundary": "<scope modeled>",
  "commands_run": [],
  "counterexamples_or_absence": "<counterexample summary or explicit absence>",
  "hard_invariants": [],
  "skipped_checks": [],
  "model_obligations": [],
  "ordinary_test_evidence": [],
  "missing_test_kinds": [],
  "conformance_boundary": "<abstract model only, ordinary tests, conformance replay, or bounded combination>",
  "confidence_boundary": "<what this model does and does not prove>",
  "residual_blindspots": [],
  "background_artifact_completion": [],
  "pm_suggestion_items": [],
  "evidence_consistency": {
    "self_check_passed": true,
    "child_reports_all_passed": true,
    "blocking_child_reports": [],
    "hard_evidence_decision": "pass"
  },
  "contract_self_check": {
    "all_required_fields_present": true,
    "exact_field_names_used": true,
    "empty_required_arrays_explicit": true,
    "runtime_mechanical_validation_passed": true,
    "semantic_sufficiency_reviewed_by_runtime": false
  }
}
```

Use `model_obligations` for FlowGuard scenarios, invariants, hazards,
transitions, and contracts that matter to the PM decision. Use
`ordinary_test_evidence` for non-FlowGuard test, replay, or manual command
evidence bound to those obligations. Use `missing_test_kinds` for required
happy, failure, edge, negative, or replay evidence that is absent or stale. If
the report cites any long or background test, `background_artifact_completion`
must list the log root, stdout, stderr, combined, exit, and meta paths, exit
code, latest update time, completion status, and whether a valid proof was
reused. Progress lines alone are not completion evidence.

If any child FlowGuard/model-test/development-process report says blocked,
missing code contract, revalidation required, stale, failed, or not ok, the
report's top-level `passed` must be false and `evidence_consistency` must name
the blocking child report. Do not send `passed: true` when hard evidence inside
the report says blocked.

The FlowGuard operator report supports PM decisions; it cannot approve completion, waive
reviewer gates, or claim no risk beyond its model boundary.

After PM receives a FlowGuard operator report, PM must copy every relevant
`model_obligations`, `ordinary_test_evidence`, and `missing_test_kinds` row into
the current `test_obligation_matrix`. Missing, stale, skipped, failed,
not-run, or progress-only evidence must be dispositioned by PM before the
dependent node, evidence-quality package, final ledger, or closure gate can
pass. FlowGuard operator prose does not close a test gap.

PM must convert the report into a concrete route decision: continue, repair,
add evidence, split a node, mutate the route, or block. For structural route
changes, even a passing FlowGuard report is not enough by itself: PM must
submit a `pm_flowguard_acceptance` result that absorbs the report, states
whether to accept or rewrite the route plan, and only then may Reviewer inspect
the PM absorption package. A report that only says the model ran, without
telling PM how it changes route or node design, is not sufficient.

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
