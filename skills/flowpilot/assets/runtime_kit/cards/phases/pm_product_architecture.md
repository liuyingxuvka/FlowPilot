<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: System-card ACKs go through the current runtime card check-in command; this is the current-runtime return path for card ACKs. Current work-package ACKs and completion outputs go through the assigned current packet lease when present. For formal role outputs, write the body only to a run-scoped packet, result, report, decision, or blocker file, then submit it with `flowpilot_new.py submit-result --lease-id <lease-id> --packet-id <packet-id> --body-file <sealed_result_body_file>` so the current runtime ledger records the event and later exposes only controller-visible envelope metadata with status, paths, and hashes. A local file write is only local storage and must not be treated as wait completion until the current runtime records the packet result. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
post_ack: ACK is receipt only; ACK is not completion. This is a work item when it asks for an output, report, decision, result, or blocker. After work-card ACK, do not stop or wait for another prompt; immediately continue the assigned work and submit the formal output or blocker through the current runtime path. The task remains unfinished until the current runtime receives that output or blocker.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. System-card ACKs, current work-package outputs, and formal role-output submissions go directly through the current runtime commands. Controller must follow the `flowpilot_new.py` lifecycle guard and foreground duty; no unsupported command text, stale runtime state, chat history, or historical artifact authorizes current-run progress.
runtime_context: Treat the runtime delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; submit a protocol blocker through the current runtime path.
-->
# PM Product Architecture Phase

## Role Capability Reminder

- Formal work products must live in run-scoped files or project artifacts. Handoff messages point to artifacts with paths/hashes, changed paths when applicable, output contract, inspection notes, and PM Suggestion Items; the message body is not the sole work product.
- PM may directly disposition suggestions when evidence is sufficient. Consultation is optional, not a mandatory step for every suggestion.
- If PM lacks basis, or the suggestion may affect route, product target, acceptance, process safety, replay, repair return path, or risk boundary, PM may request bounded consultation through an allowed role-work request, then must record a final PM disposition after reading the advice artifact.
- If a PM-owned decision still lacks evidence, modeling, research, review, or implementation support, register a bounded `pm_registers_role_work_request` only when the router's current `allowed_external_events` includes that event; otherwise record the limitation or blocker instead of emitting it.
- Treat the router's current `allowed_external_events` as the active authority for what this card may return.
- For a blocked PM-owned decision, choose the smallest valid path among repair, sender reissue, route mutation, evidence quarantine, or user stop; do not skip required recheck.
- Put reviewer, worker, and FlowGuard operator advice that needs PM disposition into the PM suggestion/blocker ledger instead of leaving it only in prose.
- For non-trivial product, acceptance, validation, or evidence-freshness judgement, cite a FlowGuard Work Order and FlowGuard Report with `flowguard_work_order_id`, `flowguard_report_id`, `flowguard_report_freshness`, and PM acceptance, or record a scoped `flowguard_not_required_reason`.
- In mature FlowGuard projects, read `docs/flowguard_project_topology.md` as background architecture before product modeling decisions. It guides relevant model/test/code/evidence inspection, but it is not a FlowGuard Report and is not gate evidence. If this phase changes topology sources, rebuild and check the topology before claiming done.


Write `.flowpilot/runs/<run-id>/product_function_architecture.json` from
reviewed material only.

Use the startup release as the first high-quality current-run posture source.
Before choosing features or route implications, state the strongest useful
result the final user should receive and what proof would make PM comfortable
handing it to a stakeholder. Short or sparse startup wording is not a reason to
lower the product target.

Before writing the product architecture, read the startup FlowGuard capability
snapshot at `.flowpilot/runs/<run-id>/flowguard/capability_snapshot.json`.
FlowGuard is a required foundation for every FlowPilot run, not an ordinary
optional child skill. If the snapshot is missing, stale for this run, or lacks
the current FlowGuard skill routes and source paths, block and request snapshot
generation instead of selecting ordinary child skills or drafting a route.

Also write `.flowpilot/runs/<run-id>/flowguard/product_modeling_plan.json`
before asking FlowGuard operator to model the product. The plan is
PM-owned and must say which product model families are required, merged, or
skipped with reasons. Do not assume one product model is enough when the
product has distinct behavior, UI/interaction, data/state,
failure/recovery, capability, validation, or evidence risks.
The plan is the FlowGuard Work Order source for FlowGuard operator modeling and
must assign `flowguard_work_order_id`, expected report path, freshness rule,
and affected downstream gate. The FlowGuard operator's FlowGuard Report must be
PM-accepted before this architecture can feed root contract, child-skill
selection, or route drafting.

Also write or update a `flowpilot.self_interrogation_record.v1` with scope
`product_architecture`, then register it in
`.flowpilot/runs/<run-id>/self_interrogation_index.json`. Any hard or
current-gate finding from the product-architecture self-check must be
incorporated into the architecture, deferred to a named later node/gate,
entered into `pm_suggestion_ledger.jsonl`, rejected with reason, or waived with
authority before root contract freeze.

Include:

- user task map and target users;
- `requirement_trace`: assign stable `req-*` ids to important explicit user
  requirements, PM-added hard requirements, hard low-quality-success risks,
  proof obligations, and any external advisory material PM imports. External
  OpenSpec/OpenSpark/SparkKey-style files are only source material until PM
  imports them here; they never become route authority by themselves;
  preserve concrete source-intent in every user-sourced row. Keep the user's
  actual objects, requested actions, quality adjectives, quantities,
  constraints, and explicit exclusions when they define the work. Do not
  replace concrete source-intent with generic wording such as "satisfy the
  user", "complete the task", or "deliver a good result";
  preserve core deliverable non-downgrade for every user-sourced row. Do not
  replace a requested output, source, evidence, quality floor, quantity,
  material access, test, or prohibition with a reachable-only subset,
  status-only note, report-only artifact, honest missing explanation,
  external-only label, partial count, not-yet-done marker, or
  absence-of-fabrication proof unless the user explicitly accepts that lowered
  target. If the source, access, material, evidence, or test is unavailable,
  carry it as a blocker, research need, route decision, waiver need, or user
  stop instead of lowering the product architecture;
- `acceptance_item_registry_seed`: compile atomic current-run acceptance
  items from explicit user requirements, implicit user commitments, PM-added
  high standards, low-quality-success risks, child-skill standards, and
  FlowGuard obligations. Include at least one user-sourced item and at least
  one PM high-standard item. Each row must state `quality_floor`,
  `low_quality_failure_patterns`, `required_evidence`, expected owner nodes
  when known, reviewer or FlowGuard gates, and whether final backward replay
  must check it;
- final-user intent and product usefulness assumptions, including what would
  make the result feel incomplete, unusable, misleading, or below the user's
  real goal;
- `system_integration_intent`: describe the intended whole-product or
  whole-artifact structure, the major continuity/callback/handoff expectations,
  where repetition is useful reinforcement versus harmful duplication, and
  which artifact families could look locally complete while failing as one
  coherent product;
- product capability map;
- negative scope and explicit user prohibitions;
- semantic fidelity risks and forbidden downgrades;
- minimum sufficient complexity review;
- low-quality-success review: identify task-specific hard parts, tempting
  thin-success shortcuts, warning signs that the result merely looks complete,
  and proof of depth needed to show those hard parts were genuinely solved;
- highest achievable product target;
- higher-standard opportunities classified as hard requirement, current-scope
  improvement, future candidate, or rejected/deferred with reason;
- functional acceptance matrix;
- evidence and validation implications for the root contract.

Every user task, product capability, feature decision, missing-feature
decision, low-quality-success hard part, and functional acceptance row must
carry `source_requirement_ids` when it exists because of a user requirement,
PM-added hard risk, or imported advisory source. If an item has no supporting
requirement id, either put it in negative scope/deferred scope or record why it
is only PM decision-support.

The acceptance item seed is not a separate workflow. It is the checklist form
of the same product architecture and root contract. Later PM route planning
must assign every active item to route nodes, node acceptance plans must
project the node-owned items, PM dispositions must close or block them, and
the final ledger/backward replay must check every active item again.

Use Minimum Sufficient Complexity here. Every accepted capability, feature,
surface, and visible element must be tied to a user task, a hard acceptance
criterion, a verification need, or a real risk reduction. Put features or UI
elements with no such support into negative scope or defer them with a revisit
condition. If a simpler architecture can produce the same user-visible behavior
with the same proof strength, choose it and record the rejected extra
complexity.

The low-quality-success review is not a generic "avoid bad output" note. For
the user's actual task, name the hard parts that are easy to handle
superficially, the casual shortcuts a worker or PM might take, the evidence
that would be existence-only, and the proof of depth that would convince a
skeptical reviewer. Classify each item as hard current requirement,
current-scope improvement, future candidate, nonblocking note, or rejected with
reason. Hard low-quality risks must later be owned by existing route nodes when
possible; do not create new route nodes merely because a concern was named.

Do not draft or activate a route from this card. FlowGuard operator must
turn this architecture and the PM Product Modeling Plan into a concrete
product model family, then PM must explicitly accept that model family before
ordinary child-skill selection, Reviewer challenge, or route planning can run.
If PM finds that the model family does not represent the intended product,
rewrite the product architecture or Product Modeling Plan, or ask Product
FlowGuard to rebuild the missing family before continuing.
