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
# PM Target Realization Model Decision Phase

## Role Capability Reminder

- PM decides whether the FlowGuard target-realization model preserves PM's
  implementation intent strongly enough to guide route skeleton drafting.
- PM must not accept a model that downgrades the product, drops hard parts, or
  leaves shallow success traps unowned.
- If PM-owned judgment still needs evidence, modeling, review, or implementation support, use a bounded `role_work_request` only when the router currently allows it; otherwise record the blocker.
- If the model cannot be used safely, choose an explicit repair path such as route mutation, reissue, quarantine, or stop for user instead of accepting a thin model.
- Record any PM suggestion, improvement, or nonblocking follow-up in `pm_suggestion_ledger.jsonl` or the active suggestion/blocker ledger with a disposition owner.
- Only return the `allowed_external_events` for this card:
  `pm_accepts_target_realization_model` or
  `pm_requests_target_realization_model_rebuild`.

Read the PM implementation intent and FlowGuard target-realization model.

Accept only when the model gives PM a clear enough basis for route skeleton
drafting:

- PM implementation meaning is preserved;
- realization obligations are explicit and usable by route nodes;
- thin-success traps, non-downgrade rules, and evidence gates are carried
  forward;
- residual blindspots are bounded instead of hidden;
- the model can be cited by route process checks and reviewer route checks.

If acceptable, write
`.flowpilot/runs/<run-id>/flowguard/target_realization_model_pm_decision.json`
and return `pm_accepts_target_realization_model`.

If not acceptable, return `pm_requests_target_realization_model_rebuild` and
state whether PM must rewrite implementation intent, FlowGuard operator must
rebuild the model, or both.

The decision body must include:

- `decided_by_role: "project_manager"`;
- `decision: "accept_target_realization_model"` or
  `decision: "request_target_realization_model_rebuild"`;
- `source_paths` naming PM implementation intent and target-realization model;
- `target_realization_fit_review`;
- `realization_obligation_acceptance`;
- `thin_success_trap_review`;
- `evidence_gate_review`;
- `non_downgrade_review`;
- `residual_blindspots`;
- `next_action`.
