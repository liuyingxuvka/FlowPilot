<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write any role-output body only to a run-scoped packet, result, report, or decision file, then return to Controller only a controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
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

Apply Minimum Sufficient Complexity when freezing the contract. The root
contract must freeze outcomes, hard risks, and proof obligations, not an
unnecessary implementation shape. Do not turn a complex route, tool choice,
child skill, or artifact family into a hard requirement unless the user asked
for it or the proof obligation cannot be met without it.

Do not draft a route until reviewer and Product FlowGuard Officer checks pass
for the frozen contract.
