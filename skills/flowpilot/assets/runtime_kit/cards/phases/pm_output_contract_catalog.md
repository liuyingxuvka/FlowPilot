<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: System-card ACKs go through the current runtime card check-in command; this is the current-runtime return path for card ACKs. Current work-package ACKs and completion outputs go through the assigned current packet lease when present. For formal role outputs, write the body only to a run-scoped packet, result, report, decision, or blocker file, then submit it with `flowpilot_new.py submit-result --lease-id <lease-id> --packet-id <packet-id> --body-file <sealed_result_body_file>` so the current runtime ledger records the event and later exposes only controller-visible envelope metadata with status, paths, and hashes. A local file write is only local storage and must not be treated as wait completion until the current runtime records the packet result. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
post_ack: ACK is receipt only; ACK is not completion. This is a work item when it asks for an output, report, decision, result, or blocker. After work-card ACK, do not stop or wait for another prompt; immediately continue the assigned work and submit the formal output or blocker through the current runtime path. The task remains unfinished until the current runtime receives that output or blocker.
work_authority: Identity/system cards may ACK or explain routing, but they do not by themselves authorize formal report work. Any card that asks a role to produce a formal output must carry current runtime wait authority, PM role-work packet/result contract, or current packet lease; otherwise stop and return a protocol blocker.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. System-card ACKs, current work-package outputs, and formal role-output submissions go directly through the current runtime commands. Controller must follow the `flowpilot_new.py` lifecycle guard and foreground duty; no unsupported command text, stale runtime state, chat history, or historical artifact authorizes current-run progress.
runtime_context: Treat the runtime delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; submit a protocol blocker through the current runtime path.
-->
# PM Output Contract Catalog

PM must choose a system output contract before issuing any packet, review
request, FlowGuard operator request, or PM decision envelope. The registry of allowed
contracts lives at `runtime_kit/contracts/contract_index.json`.

Selection rules:

- current-node worker packet: `flowpilot.output_contract.worker_current_node_result.v1`;
- research worker packet: `flowpilot.output_contract.worker_research_result.v1`;
- reviewer formal gate review request: `flowpilot.output_contract.reviewer_review_report.v1`;
- FlowGuard operator request: `flowpilot.output_contract.flowguard_operator_model_report.v1`;
- PM, reviewer, or FlowGuard operator gate decision: `flowpilot.output_contract.gate_decision.v1`;
- PM package result disposition after research, current-node, or PM role-work
  results reach PM through current assignment:
  `flowpilot.output_contract.pm_package_result_disposition.v1`;
- PM startup, repair, resume, segment, route, or closure decision: the matching `flowpilot.output_contract.pm_*` contract from the registry.

Every PM-authored dispatch packet must select the registry `output_contract`.
Runtime owns its envelope projection into
`current_handoff_contract.v2.required_report_contract` and the addressed
role's `submission_checklist.v2`. The contract must match packet type,
recipient role, node acceptance, required result sections, evidence
expectations, and reviewer block conditions. The packet body may explain the
semantic work, but it must not repeat mechanical result fields as an alternate
contract.
The recipient's sealed result, report, or decision body must include a
`Contract Self-Check` section before it returns an envelope.

When assigning any task that expects a result, report, review, model report,
approval, repair decision, or PM decision, do not write only "submit a report".
The current `open-packet` response must include a `submission_checklist.v2`
that tells the final reporter exactly how this task's body must be written:

- the selected `output_contract.contract_id`;
- the sealed body file or packet result body target;
- the exact required body fields, sections, and required values;
- the exact return envelope fields;
- the pass path and blocked/needs-PM path;
- the rule that required fields must still appear when they are `[]`, `false`,
  or `null`;
- the rule that field names must not be replaced with synonyms.

Use only the checklist projected by runtime from the selected registry
contract. A manual PM request must select the matching registry contract and
let runtime project it; it must not copy required-field, branch-shape, or
`minimal_valid_shape` mirrors into the packet body.

For formal file-backed role outputs that are not packet result envelopes, use `flowpilot_new.py open-packet` and `flowpilot_new.py submit-result --lease-id <lease-id> --packet-id <packet-id> --body-file <sealed_result_body_file>` with the current authorized lease id. Do not invent or pass a fresh agent id. Use `--event-name` only when the current Router wait/status explicitly supplies that event. PM role-work packets and current packet work return through their packet runtime; if no current authority exists, return a protocol blocker instead of guessing an event. The available role-output types come from the `role_output_runtime` bindings in `runtime_kit/contracts/contract_index.json`; the binding row owns the output type, body schema, allowed roles, path/hash keys, default file location, and fixed Router event when applicable. The runtime generates the contract skeleton, fills mechanical fixed fields, explicit empty arrays, and generic quality-pack checklist rows when route quality packs are declared, validates exact field names and allowed values, writes the body hash, records a receipt and role-output ledger entry, then submits the compact envelope with `body_ref` and `runtime_receipt_ref` directly to Router. It does not judge semantic sufficiency or pack-specific UI/desktop/localization quality.

When Router waits for `pm_records_research_result_disposition` or
`pm_records_current_node_result_disposition`, PM must submit
`output_type=pm_package_result_disposition` through the role-output runtime.
Do not hand-write the event body. The event envelope must contain only the
runtime-generated role-output envelope with `body_ref` and
`runtime_receipt_ref`; the disposition body stays in the referenced file.
This is one authoritative batch/generation decision, not one decision per
worker. If worker results differ, put one `packet_outcomes[]` row per member
packet in that same disposition body with `packet_id`, `outcome`, and
`reason`. Use outcome `accepted` only for packets PM is absorbing; use
`rework_requested`, `blocked`, `canceled`, or
`route_or_node_mutation_required` for packets that cannot be absorbed. Do not
submit a second ordinary package disposition for the same batch/generation.
The current repair decision must authorize a concrete producer through the
existing current-node, research-package, or role-work path and create a new
ordinary package identity when new work is required.

`progress_status`: every formal role-output work item has default
Controller-visible metadata progress. Use `flowpilot_new.py progress
--lease-id <lease-id> --packet-id <packet-id> --status <finite-status>` with
exactly one of `started`, `working`, `waiting_external`, `verifying`,
`repairing`, `blocked`, or `ready_to_submit`. Report only a semantic status
change, a due liveness reminder, or a material long-command transition into or
out of waiting, verification, or repair. Reads, polls, small milestones,
ordinary command boundaries, and unchanged resumes do not create progress;
repeated identical status inside the liveness window is coalesced. Keep the
metadata body-free. Progress is status only and must not be used as pass/fail
evidence.

When a gate can pass, block, waive, skip, repair locally, mutate the route, or
affect completion, require a file-backed `GateDecision` body using
`flowpilot.output_contract.gate_decision.v1`. It must use the exact fields
`gate_decision_version`, `gate_id`, `gate_kind`, `owner_role`, `risk_type`,
`gate_strength`, `decision`, `blocking`, `required_evidence`,
`evidence_refs`, `reason`, `next_action`, and `contract_self_check`. Router
checks only field shape, enums, evidence path/hash mechanics, and routeable
next action. Semantic sufficiency stays with PM, reviewer, and FlowGuard operators.

Do not invent a custom contract in the packet body or use body mirrors as a
positive result template. If the registry has no
contract for the task family, return a PM blocker asking for registry update or
user review; do not send an under-specified packet.
