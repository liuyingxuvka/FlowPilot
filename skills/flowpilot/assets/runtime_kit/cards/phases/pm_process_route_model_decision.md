<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: System-card ACKs go directly to Router through the card check-in command; this is the router-directed return path for card ACKs. Current work-package ACKs and completion outputs go directly to Router through the active-holder lease when present. For formal role outputs, write the body only to a run-scoped packet, result, report, or decision file, then submit it with `flowpilot_runtime.py submit-output-to-router` so Router records the event and later exposes only controller-visible envelope metadata with status, paths, and hashes. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
post_ack: ACK is receipt only; ACK is not completion. After work-card ACK, continue the work assigned by this card and submit the formal output or blocker through the Router-directed runtime path.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. System-card ACKs, current work-package outputs, and formal role-output submissions go directly to Router through their runtime commands. Controller must follow Router daemon status and the Controller action ledger; flowpilot_router.py next/run-until-wait are diagnostic or explicit repair tools only.
runtime_context: Treat the router delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; submit a protocol blocker through the Router-directed runtime path.
-->
# PM Process Route Model Decision Phase

## Role Capability Reminder

- Formal work products must live in run-scoped files or project artifacts. Handoff messages point to artifacts with paths/hashes, changed paths when applicable, output contract, inspection notes, and PM Suggestion Items; the message body is not the sole work product.
- PM owns route activation. Process FlowGuard supplies the executable process model and reachability evidence; it does not activate the route.
- Treat the router's current `allowed_external_events` as the active authority for what this card may return.
- If the route model evidence is not enough to decide, PM may ask another FlowPilot role for bounded `role_work_request` evidence before accepting.
- If accepting would hide a process gap, choose an explicit repair path: route mutation, packet reissue, artifact quarantine, or stop for user input.

Read the PM route draft and the Process FlowGuard Officer's route process
check.

Decide whether the route process model is good enough to become the serial
execution basis for Reviewer route challenge.

Accept only when Process FlowGuard has modeled the route as one executable
serial line:

- every effective root, parent/module, child, leaf, and repair segment is
  reachable in order;
- each non-leaf has a local entry loop before child execution;
- every leaf is worker-ready or promoted to a parent/module before dispatch;
- parent completion and final completion include backward coverage review;
- model-miss handling updates the model, searches same-class omissions, adds
  supplemental nodes when needed, and reruns stale gates;
- no hidden parallel subwork remains inside a supposedly dispatchable leaf.

If the model is acceptable, write
`.flowpilot/runs/<run-id>/flowguard/process_route_model_pm_decision.json`
and return `pm_accepts_process_route_model`.

If it is not acceptable, return `pm_requests_process_route_model_rebuild` and
state whether PM must rewrite the route draft, ask Process FlowGuard to rebuild
the model, split/promote nodes, or add supplemental nodes.

The decision body must include:

- `decided_by_role: "project_manager"`;
- `decision: "accept_process_route_model"` or
  `decision: "request_process_route_model_rebuild"`;
- `source_paths` naming the route draft and Process FlowGuard report;
- `serial_execution_line_review`;
- `recursive_node_entry_review`;
- `leaf_worker_readiness_review`;
- `parent_and_final_backward_review_policy`;
- `model_miss_repair_policy`;
- `next_action`.
