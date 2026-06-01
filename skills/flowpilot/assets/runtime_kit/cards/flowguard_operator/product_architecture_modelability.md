<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: flowguard_operator
recipient_identity: FlowPilot FlowGuard operator role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: System-card ACKs go through the current runtime card check-in command; this is the current-runtime return path for card ACKs. Current work-package ACKs and completion outputs go through the assigned current packet lease when present. For formal role outputs, write the body only to a run-scoped packet, result, report, decision, or blocker file, then submit it with `flowpilot_new.py submit-result --lease-id <lease-id> --packet-id <packet-id> --body <sealed_result_summary>` so the current runtime ledger records the event and later exposes only controller-visible envelope metadata with status, paths, and hashes. A local file write is only local storage and must not be treated as wait completion until the current runtime records the packet result. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
post_ack: ACK is receipt only; ACK is not completion. This is a work item when it asks for an output, report, decision, result, or blocker. After work-card ACK, do not stop or wait for another prompt; immediately continue the work assigned by this card and submit the formal output or blocker through the current runtime path. The task remains unfinished until the current runtime receives that output or blocker.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. System-card ACKs, current work-package outputs, and formal role-output submissions go directly through the current runtime commands. Controller must follow the `flowpilot_new.py` lifecycle guard and foreground duty; no unsupported command text, stale runtime state, chat history, or historical artifact authorizes current-run progress.
runtime_context: Treat the runtime delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; submit a protocol blocker through the current runtime path.
-->
# FlowGuard operator Product Behavior Model

## Role Capability Reminder

- When more evidence, worker work, reviewer review, or PM choice is needed, return a structured blocker or PM suggestion for PM to route.
- Do not approve routes or make PM decisions; your report is model evidence and repair/risk advice for PM.
- This card's model output is a FlowGuard Report. Cite `flowguard_work_order_id`, `flowguard_report_id`, `flowguard_route_used`, `flowguard_report_freshness`, skipped checks, progress-only evidence status, and PM decision impact.


Submit the root product behavior model for the PM product-function
architecture. This gate's output is the product behavior model that PM must accept before
reviewer challenge and route planning use it.

Before modeling, read:

- `.flowpilot/runs/<run-id>/flowguard/capability_snapshot.json`;
- `.flowpilot/runs/<run-id>/flowguard/product_modeling_plan.json`;
- `.flowpilot/runs/<run-id>/product_function_architecture.json`.

Treat FlowGuard as the run foundation, not as an optional ordinary child skill.
Your output is a product model family. Build separate child models when the PM
plan names distinct behavior, UI/interaction, data/state, failure/recovery,
capability, validation, or evidence risk families. If you merge or skip a
family, record the PM plan row and the reason; if the plan is missing or too
coarse to model honestly, block for PM repair instead of submitting a single
over-collapsed model.

Report:

- modelable product states and transitions;
- user actions, product states, failure/recovery paths, forbidden downgrades,
  and completion evidence that route nodes must cover;
- `product_model_family_coverage`: every PM-planned product family, model file,
  covered scenarios/invariants/hazards/contracts, and merge/skip disposition;
- the smallest useful hierarchy of product behavior segments that PM can later
  map to route parents/modules/leaves without hiding multiple behaviors inside
  one worker leaf;
- unmodeled or ambiguous behavior;
- high-risk requirements needing scenarios or experiments;
- confidence boundary;
- whether PM must repair the architecture before contract freeze.

This is decision support for the PM, not a no-risk certificate.
PM must explicitly accept this model before Reviewer challenges the product
architecture. If PM rejects it, rebuild the product behavior model after the
PM architecture change or clarification instead of treating the old model as
good enough.

Router hard gate fields:

- To submit the model, return event
  `flowguard_operator_submits_product_behavior_model` with
  `reviewed_by_role: "flowguard_operator"` and `passed: true`.
- If blocking, return `flowguard_operator_blocks_product_behavior_model`.
