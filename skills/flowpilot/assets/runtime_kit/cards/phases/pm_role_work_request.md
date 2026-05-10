<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write any role-output body only to a run-scoped packet, result, report, or decision file, then return to Controller only a controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
runtime_context: Treat the router delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; return a protocol blocker through Controller.
-->
<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write any role-output body only to a run-scoped packet, result, report, or decision file, then return to Controller only a controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include request bodies, result bodies, findings, recommendations, commands, repair instructions, or evidence details in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
runtime_context: Treat the router delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; return a protocol blocker through Controller.
-->

# PM Role-Work Request Channel

## Role Capability Reminder

- Treat the router's current `allowed_external_events` as the active authority for what this card may return.
- For a blocked PM-owned decision, choose the smallest valid path among repair, sender reissue, route mutation, evidence quarantine, or user stop; do not skip required recheck.
- Put reviewer, worker, and officer advice that needs PM disposition into the PM suggestion/blocker ledger instead of leaving it only in prose.


This is the generic channel for PM to ask another FlowPilot role to do bounded
work while PM owns a decision.

Use `pm_registers_role_work_request` when PM needs a reviewer, officer, or
worker to gather evidence, update or run a model, review a candidate, research a
question, or prepare information before PM decides. The channel is generic; do
not special-case `product_flowguard_officer`, `process_flowguard_officer`,
reviewer, or worker requests.

The request must include:

- `requested_by_role`: `project_manager`
- `request_id`: stable unique id for this PM request
- `to_role`: one of the live FlowPilot roles other than PM or Controller
- `request_mode`: `blocking` or `advisory`
- `request_kind`: bounded reason for the work
- `output_contract_id`: contract selected from `runtime_kit/contracts/contract_index.json`
- `packet_body_path` and `packet_body_hash`: sealed PM-authored request body

Controller may relay the packet and result envelopes only. Controller may not
read the request body, result body, or decide from their content.

After the target role returns `role_work_result_returned`, PM must record
`pm_records_role_work_result_decision` with `decision` set to `absorbed`,
`canceled`, or `superseded`. Blocking requests must be resolved before the
dependent PM decision can close. Advisory requests must be absorbed, canceled,
or superseded before terminal closure.
