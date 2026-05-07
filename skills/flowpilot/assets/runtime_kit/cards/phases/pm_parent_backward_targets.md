<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write any role-output body only to a run-scoped packet, result, report, or decision file, then return to Controller only a controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
runtime_context: Treat the router delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; return a protocol blocker through Controller.
-->
# PM Parent Backward Targets Phase

If the active node has children, assess composition risk from the active route,
frontier, node acceptance plan, and child evidence pointers.

Build local parent backward replay targets when composition risk is high or
when the PM cannot justify a low-risk waiver from current evidence. For a
low-risk waiver, write the waiver reason and cited source paths before the
parent node can close.

Write
`.flowpilot/runs/<run-id>/routes/<route-id>/parent_backward_targets.json`
from the active route, active frontier, node acceptance plan, and child node
evidence pointers.
