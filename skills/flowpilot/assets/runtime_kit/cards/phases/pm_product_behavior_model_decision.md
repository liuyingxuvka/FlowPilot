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
# PM Product Behavior Model Decision Phase

## Role Capability Reminder

- Formal work products must live in run-scoped files or project artifacts. Handoff messages point to artifacts with paths/hashes, changed paths when applicable, output contract, inspection notes, and PM Suggestion Items; the message body is not the sole work product.
- PM owns the route and product target. FlowGuard operator supplies model evidence; it does not replace PM judgement.
- Treat the router's current `allowed_external_events` as the active authority for what this card may return.
- If the report is not enough to decide, PM may ask another FlowPilot role for bounded `role_work_request` evidence before accepting.
- If accepting would hide a gap, choose an explicit repair path: route mutation, packet reissue, artifact quarantine, or stop for user input.

Read the PM product-function architecture and the FlowGuard operator's
product behavior model report. Also read the startup FlowGuard capability
snapshot and `.flowpilot/runs/<run-id>/flowguard/product_modeling_plan.json`.

Decide whether the model family is good enough to become the product basis for
ordinary child-skill selection, Reviewer challenge, root contract, and later
route planning.

Accept only when the report gives PM a concrete product model:

- modeled product states and user actions;
- failure/recovery paths;
- forbidden downgrades;
- completion evidence;
- explicit ambiguous or unmodeled behavior;
- `model_obligations` for FlowGuard scenarios, invariants, hazards,
  transitions, and contracts;
- `ordinary_test_evidence` bound to those obligations, with
  `missing_test_kinds` called out for absent or stale happy, failure, edge,
  negative, or replay evidence;
- `conformance_boundary` and `residual_blindspots` stating what the product
  model and ordinary tests do not prove;
- `background_artifact_completion` for any cited long/background test, including
  log root, stdout, stderr, combined, exit, and meta paths, exit code, latest
  update time, completion status, and valid proof reuse;
- a PM-readable coverage map from the user's real goal to the model.
- `product_model_family_coverage` that closes every PM-planned product family
  or gives an explicit PM-owned merge/skip reason.

If the model is acceptable, write
`.flowpilot/runs/<run-id>/flowguard/product_behavior_model_pm_decision.json`
and return `pm_accepts_product_behavior_model`.

If it is not acceptable, return
`pm_requests_product_behavior_model_rebuild` and state whether PM must rewrite
the product architecture, ask FlowGuard operator to rebuild the model, or both.
Do not let Reviewer challenge the product architecture until PM accepts the
current product behavior model.

The decision body must include:

- `decided_by_role: "project_manager"`;
- `decision: "accept_product_behavior_model"` or
  `decision: "request_product_behavior_model_rebuild"`;
- `source_paths` naming the product architecture and FlowGuard operator product model;
- `flowguard_capability_snapshot_path`;
- `product_modeling_plan_path`;
- `pm_model_fit_review` explaining what PM accepted or rejected;
- `product_model_family_coverage_review`;
- `product_goal_coverage`;
- `model_test_alignment_review`;
- `conformance_boundary`;
- `unmodeled_or_ambiguous_behavior`;
- `residual_blindspots`;
- `background_artifact_completion_review`;
- `next_action`.
