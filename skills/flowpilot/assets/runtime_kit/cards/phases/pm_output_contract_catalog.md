<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write any role-output body only to a run-scoped packet, result, report, or decision file, then return to Controller only a controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
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

Do not invent a custom contract in the packet body. If the registry has no
contract for the task family, return a PM blocker asking for registry update or
user review; do not send an under-specified packet.
