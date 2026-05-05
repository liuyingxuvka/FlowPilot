<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write any role-output body only to a run-scoped packet, result, report, or decision file, then return to Controller only a controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->
# PM Startup Intake Phase

Current task: read the `user_intake` mail after Controller ledger delivery.

Allowed PM decisions:

- reset Controller role;
- request material and capability scan packets;
- request prior-work import boundaries;
- request startup cleanup or capability evidence;
- block for user if startup answers are incomplete or contradictory.

Forbidden:

- do not write the final route yet;
- do not issue implementation packets;
- do not use worker material before reviewer sufficiency review.
