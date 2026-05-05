<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Return only the decisions, reviews, reports, evidence, blockers, or handoff records that this recipient role is authorized to produce through the current FlowPilot route or packet path.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->
# PM Root Contract Phase

Freeze the root acceptance contract after product architecture review and
Product FlowGuard Officer modelability pass.

Write:

- `.flowpilot/runs/<run-id>/root_acceptance_contract.json`;
- `.flowpilot/runs/<run-id>/standard_scenario_pack.json`;
- `.flowpilot/runs/<run-id>/contract.md`.

The root contract is the completion floor. It records project-level hard
requirements, high-risk requirements, proof obligations, scenario coverage, and
what cannot be closed by a report alone.

Do not draft a route until reviewer and Product FlowGuard Officer checks pass
for the frozen contract.
