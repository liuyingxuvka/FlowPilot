<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Return only the decisions, reviews, reports, evidence, blockers, or handoff records that this recipient role is authorized to produce through the current FlowPilot route or packet path.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->
# PM Continuation Capability Binding

Bind continuation to the user's startup answer and current-run evidence.

Check:

- heartbeat is allowed only when startup answers selected scheduled continuation;
- manual resume is valid when heartbeat is unavailable or not authorized;
- continuation evidence names current-run state, frontier, packet ledger, and crew memory;
- any heartbeat claim cites the latest current-run heartbeat record, not old state;
- unsupported continuation capability becomes a PM blocker or manual-resume plan.

Do not let Controller continue route work from a heartbeat status note alone.
