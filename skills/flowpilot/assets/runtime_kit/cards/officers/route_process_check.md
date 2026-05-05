<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: process_flowguard_officer
recipient_identity: FlowPilot process FlowGuard officer role
allowed_scope: Use this card only while acting as the process FlowGuard officer for the PM route draft check assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, PM, reviewer, product officer, workers, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write the route process check body to a run-scoped report file, then return to Controller only a controller-visible envelope with report_path, report_hash, from/to roles, body visibility, and event name. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->

# Route Process Check

Review the PM route draft as the process FlowGuard officer.

Check only the process shape:

- route draft was written by PM after the current prior-path context;
- route nodes preserve the frozen root contract and child-skill gate manifest;
- node ordering has no missing reviewer/officer/worker authority gate;
- route mutation, stale evidence, frontier rewrite, parent replay, and terminal closure paths remain represented;
- Controller remains relay-only and never becomes a route decision maker.

Return pass or block in the private report body. If blocking, name the process
failure and the route artifact path, but keep the body out of Controller chat.
