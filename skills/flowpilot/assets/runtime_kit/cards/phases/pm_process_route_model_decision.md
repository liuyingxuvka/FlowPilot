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
# PM Process Route Model Decision Phase

## Role Capability Reminder

- Formal work products must live in run-scoped files or project artifacts. Handoff messages point to artifacts with paths/hashes, changed paths when applicable, output contract, inspection notes, and PM Suggestion Items; the message body is not the sole work product.
- PM owns route activation. FlowGuard operator supplies the executable process model and reachability evidence; it does not activate the route.
- Treat the router's current `allowed_external_events` as the active authority for what this card may return.
- If the route model evidence is not enough to decide, PM may ask another FlowPilot role for bounded `role_work_request` evidence before accepting.
- If accepting would hide a process gap, choose an explicit repair path: route mutation, packet reissue, artifact quarantine, or stop for user input.

Read the PM route draft and the FlowGuard operator's route process
check.

Decide whether the route process model is good enough to become the serial
execution basis for Reviewer route challenge.

Accept only when FlowGuard operator has modeled the route as one executable
serial line:

- every effective root, parent/module, child, leaf, and repair segment is
  reachable in order;
- each non-leaf has a local entry loop before child execution, including its
  own accepted `node_acceptance_plan` and current `node_context_package`;
- every leaf is worker-ready or promoted to a parent/module before dispatch;
- parent completion and final completion include backward coverage review;
- model-miss handling updates the model, searches same-class omissions, adds
  supplemental nodes when needed, and reruns stale gates;
- `model_obligations` are explicit and matched to `ordinary_test_evidence`;
- `missing_test_kinds` names absent or stale happy, failure, edge, negative, or
  replay evidence instead of hiding it in prose;
- `conformance_boundary` and `residual_blindspots` state what the process model
  and ordinary tests do not prove;
- any cited long/background test has `background_artifact_completion` with log
  root, stdout, stderr, combined, exit, and meta paths, exit code, latest
  update time, completion status, and valid proof reuse;
- no hidden parallel subwork remains inside a supposedly dispatchable leaf.

Reject a route process model that can enter a child before the active
parent/module entry gate is accepted. Child plan/context evidence cannot close
the parent/module entry gate.

If the model is acceptable, write
`.flowpilot/runs/<run-id>/flowguard/process_route_model_pm_decision.json`
and return `pm_accepts_process_route_model`.

If it is not acceptable, return `pm_requests_process_route_model_rebuild` and
state whether PM must rewrite the route draft, ask FlowGuard operator to rebuild
the model, split/promote nodes, or add supplemental nodes.

The decision body must include:

- `decided_by_role: "project_manager"`;
- `decision: "accept_process_route_model"` or
  `decision: "request_process_route_model_rebuild"`;
- `source_paths` naming the route draft and FlowGuard operator report;
- `serial_execution_line_review`;
- `recursive_node_entry_review`;
- `leaf_worker_readiness_review`;
- `parent_and_final_backward_review_policy`;
- `model_miss_repair_policy`;
- `model_test_alignment_review`;
- `conformance_boundary`;
- `residual_blindspots`;
- `background_artifact_completion_review`;
- `next_action`.
