<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write any role-output body only to a run-scoped packet, result, report, or decision file, then return to Controller only a controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->
# PM Parent Segment Decision Phase

After Reviewer passes local parent backward replay, record the PM segment
decision.

Before deciding, read the latest route-memory prior path context. The decision
must cite whether completed children, superseded children, stale evidence,
prior repairs, and experiments support continuing or require route mutation.

Allowed decisions:

- continue;
- repair existing child;
- add sibling child;
- rebuild child subtree;
- bubble to parent;
- PM stop.

Only `continue` can close the active parent node. Other decisions require route
mutation, stale evidence marking, and rerun of the same parent replay after
repair.

If repair affects sibling, ancestor, child-skill, or terminal evidence, record
those stale scopes now so the final ledger cannot count old passes as current.
