<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Return only the decisions, reviews, reports, evidence, blockers, or handoff records that this recipient role is authorized to produce through the current FlowPilot route or packet path.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->
# PM Product Architecture Phase

Write `.flowpilot/runs/<run-id>/product_function_architecture.json` from
reviewed material only.

Include:

- user task map and target users;
- product capability map;
- negative scope and explicit user prohibitions;
- semantic fidelity risks and forbidden downgrades;
- highest achievable product target;
- functional acceptance matrix;
- evidence and validation implications for the root contract.

Do not draft or activate a route from this card. Reviewer challenge and Product
FlowGuard Officer modelability must pass first.
