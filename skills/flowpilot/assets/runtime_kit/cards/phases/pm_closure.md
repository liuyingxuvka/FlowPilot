<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write any role-output body only to a run-scoped packet, result, report, or decision file, then return to Controller only a controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->
# PM Closure Phase

Close only after final ledger and backward replay pass.
Read the latest route-memory prior path context before closure. Closure must
not rely on a stale view of completed nodes, superseded nodes, stale evidence,
route mutations, terminal replay, or lifecycle state.

Closure order:

1. reconcile state, frontier, route, current pointer, and run index;
2. reconcile pause, stopped, resumed, and terminal lifecycle records;
3. stop heartbeat or record manual-resume no-automation evidence;
4. archive crew and role memory without treating archived roles as live;
5. write nonblocking FlowPilot skill-improvement observations;
6. record PM completion decision;
7. emit final report.

Completion cannot list unresolved risks as accepted completion payload.
If closure evidence disagrees with the current pointer, frontier, heartbeat, or
run index, block closure and repair lifecycle state first.
