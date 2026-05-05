<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Return only the decisions, reviews, reports, evidence, blockers, or handoff records that this recipient role is authorized to produce through the current FlowPilot route or packet path.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->
# PM Crew Rehydration Freshness

Before resume or startup activation, decide whether the six role slots are
fresh for the current formal task.

Accept only:

- live roles spawned for this run after the current startup answers;
- same-task role memory packets rehydrated into replacement roles;
- explicit user-approved single-agent six-role fallback.

Prior-run `agent_id` values are audit history only. If any required role is
missing, stale, cross-run, or unverifiable, block route work until PM records a
replacement or fallback decision.
