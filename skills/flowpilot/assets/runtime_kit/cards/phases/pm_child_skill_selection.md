<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write any role-output body only to a run-scoped packet, result, report, or decision file, then return to Controller only a controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->
# PM Child Skill Selection Phase

Select child skills from product need, not from raw availability.

Read:

- product-function architecture;
- frozen root contract;
- capabilities manifest;
- local skill inventory.

Write `.flowpilot/runs/<run-id>/pm_child_skill_selection.json` with each
candidate skill classified as `required`, `conditional`, `deferred`, or
`rejected`. Raw inventory must never be route authority.

Apply Minimum Sufficient Complexity to every candidate. `required` means the
skill closes a product, verification, or safety gap that the simpler main route
cannot reliably close. `conditional` must name the trigger. `deferred` and
`rejected` are valid high-quality decisions when a skill would add handoffs,
references, gates, or artifacts without changing the user's outcome or the
proof needed to trust it.
