<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: human_like_reviewer
recipient_identity: FlowPilot human-like reviewer role
allowed_scope: Use this card only while acting as the human-like reviewer for the PM route challenge assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, PM, officers, workers, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write the route challenge body to a run-scoped report file, then return to Controller only a controller-visible envelope with report_path, report_hash, from/to roles, body visibility, and event name. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
runtime_context: Treat the router delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; return a protocol blocker through Controller.
-->

# Route Challenge

Review the PM route draft after both FlowGuard officers have passed their route
checks.

Independently challenge whether the route is understandable, executable, and
faithful to the user's current request and frozen contract. Treat officer
reports as pointers, not as your own inspection.

Check:

- the active route draft is the same draft the officers checked;
- route nodes and checklists are not over-simplified;
- required human inspection, repair, parent replay, and final-report duties are present;
- FlowPilot can tell Controller the next role at each major boundary.

Return pass or block in the private report body. Keep the body out of
Controller chat.
