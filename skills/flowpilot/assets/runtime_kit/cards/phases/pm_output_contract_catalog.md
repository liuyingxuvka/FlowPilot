<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write any role-output body only to a run-scoped packet, result, report, or decision file, then return to Controller only a controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
runtime_context: Treat the router delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; return a protocol blocker through Controller.
-->
# PM Output Contract Catalog

PM must choose a system output contract before issuing any packet, review
request, officer request, or PM decision envelope. The registry of allowed
contracts lives at `runtime_kit/contracts/contract_index.json`.

Selection rules:

- current-node worker packet: `flowpilot.output_contract.worker_current_node_result.v1`;
- material scan worker packet: `flowpilot.output_contract.worker_material_scan_result.v1`;
- research worker packet: `flowpilot.output_contract.worker_research_result.v1`;
- reviewer dispatch or result review request: `flowpilot.output_contract.reviewer_review_report.v1`;
- process or product FlowGuard officer request: `flowpilot.output_contract.officer_model_report.v1`;
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

Do not invent a custom contract in the packet body. If the registry has no
contract for the task family, return a PM blocker asking for registry update or
user review; do not send an under-specified packet.
