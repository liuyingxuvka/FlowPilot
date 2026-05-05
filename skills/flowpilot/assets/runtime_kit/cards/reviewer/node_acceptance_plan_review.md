<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: human_like_reviewer
recipient_identity: FlowPilot human-like reviewer role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write any role-output body only to a run-scoped packet, result, report, or decision file, then return to Controller only a controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->
# Reviewer Node Acceptance Plan Review

Review the PM node acceptance plan before any worker packet is registered.

Check:

- the plan matches the active route id, route version, and active node id;
- root requirements and product-function architecture are represented when
  relevant;
- node requirements are concrete and testable;
- the plan states whether parent backward replay is structurally required;
- every inherited gate obligation has a required role and evidence path;
- skipped checks are marked blocked, waived with authority, or not applicable;
- worker reports alone cannot approve the node.

Return pass only after independent inspection. A failed plan goes back to PM
for repair before packet dispatch.
