<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: System-card ACKs go directly to Router through the card check-in command; this is the router-directed return path for card ACKs. Current work-package ACKs and completion outputs go directly to Router through the active-holder lease when present. For formal role outputs, write the body only to a run-scoped packet, result, report, or decision file, then submit it with `flowpilot_runtime.py submit-output-to-router` so Router records the event and later exposes only controller-visible envelope metadata with status, paths, and hashes. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
post_ack: ACK is receipt only; ACK is not completion. This is a work item when it asks for an output, report, decision, result, or blocker. After work-card ACK, do not stop or wait for another prompt; immediately continue the work assigned by this card and submit the formal output or blocker through the Router-directed runtime path. The task remains unfinished until Router receives that output or blocker.
work_authority: Identity/system cards may ACK or explain routing, but they do not by themselves authorize formal report work. Any card that asks a role to produce a formal output must carry current Router wait authority, PM role-work packet/result contract, or active-holder lease; otherwise stop and return a protocol blocker.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. System-card ACKs, current work-package outputs, and formal role-output submissions go directly to Router through their runtime commands. Controller must follow Router daemon status and the Controller action ledger; flowpilot_router.py next/run-until-wait are diagnostic or explicit repair tools only.
runtime_context: Treat the router delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; submit a protocol blocker through the Router-directed runtime path.
-->
# PM Output Contract Catalog

PM must choose a system output contract before issuing any packet, review
request, officer request, or PM decision envelope. The registry of allowed
contracts lives at `runtime_kit/contracts/contract_index.json`.

Selection rules:

- current-node worker packet: `flowpilot.output_contract.worker_current_node_result.v1`;
- material scan worker packet: `flowpilot.output_contract.worker_material_scan_result.v1`;
- research worker packet: `flowpilot.output_contract.worker_research_result.v1`;
- reviewer formal gate review request: `flowpilot.output_contract.reviewer_review_report.v1`;
- process or product FlowGuard officer request: `flowpilot.output_contract.officer_model_report.v1`;
- PM, reviewer, process officer, or product officer gate decision: `flowpilot.output_contract.gate_decision.v1`;
- PM startup, repair, resume, segment, route, or closure decision: the matching `flowpilot.output_contract.pm_*` contract from the registry.

Every PM-authored dispatch packet must include `output_contract` copied from
the registry. The contract must match packet type, recipient role, node
acceptance, required result sections, evidence expectations, and reviewer block
conditions. The packet body must repeat the same contract in its `Output
Contract` section so the recipient sees the requirements before working.
The recipient's sealed result, report, or decision body must include a
`Contract Self-Check` section before it returns an envelope.

When assigning any task that expects a result, report, review, model report,
approval, repair decision, or PM decision, do not write only "submit a report".
The packet body must include a `Report Contract For This Task` block that tells
the final reporter exactly how this task's body and chat envelope must be
written:

- the selected `output_contract.contract_id`;
- the sealed body file or packet result body target;
- the exact required body fields, sections, and required values;
- the exact return envelope fields;
- the pass path and blocked/needs-PM path;
- the rule that required fields must still appear when they are `[]`, `false`,
  or `null`;
- the rule that field names must not be replaced with synonyms.

If the packet runtime appends this block from the selected registry contract,
use that generated block. If you are writing a manual PM request, copy the
matching registry contract into the task packet and include the same
task-specific report-writing rules before sending it.

For formal file-backed role outputs that are not packet result envelopes, use `flowpilot_runtime.py prepare-output` and `flowpilot_runtime.py submit-output-to-router` with the matching `output_type` and concrete `--agent-id`. Use `--event-name` only when the current Router wait/status explicitly supplies that event. PM role-work packets and active-holder work return through their packet runtime; if no current authority exists, return a protocol blocker instead of guessing an event. The available role-output types come from the `role_output_runtime` bindings in `runtime_kit/contracts/contract_index.json`; the binding row owns the output type, body schema, allowed roles, path/hash keys, default file location, and fixed Router event when applicable. The runtime generates the contract skeleton, fills mechanical fixed fields, explicit empty arrays, and generic quality-pack checklist rows when route quality packs are declared, validates exact field names and allowed values, writes the body hash, records a receipt and role-output ledger entry, then submits the compact envelope with `body_ref` and `runtime_receipt_ref` directly to Router. It does not judge semantic sufficiency or pack-specific UI/desktop/localization quality.

`progress_status`: every formal role-output work item has default
Controller-visible metadata progress. Use `flowpilot_runtime.py
progress-output` while working and keep messages brief; do not include sealed
body content, findings, evidence, recommendations, decisions, or result
details. Progress is status only and must not be used as pass/fail evidence.

When a gate can pass, block, waive, skip, repair locally, mutate the route, or
affect completion, require a file-backed `GateDecision` body using
`flowpilot.output_contract.gate_decision.v1`. It must use the exact fields
`gate_decision_version`, `gate_id`, `gate_kind`, `owner_role`, `risk_type`,
`gate_strength`, `decision`, `blocking`, `required_evidence`,
`evidence_refs`, `reason`, `next_action`, and `contract_self_check`. Router
checks only field shape, enums, evidence path/hash mechanics, and routeable
next action. Semantic sufficiency stays with PM, reviewer, and officers.

Do not invent a custom contract in the packet body. If the registry has no
contract for the task family, return a PM blocker asking for registry update or
user review; do not send an under-specified packet.
