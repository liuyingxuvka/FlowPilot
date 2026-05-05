<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Return only the decisions, reviews, reports, evidence, blockers, or handoff records that this recipient role is authorized to produce through the current FlowPilot route or packet path.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->
# PM Child Skill Gate Manifest Phase

Extract the initial gate manifest for PM-selected child skills.

Write `.flowpilot/runs/<run-id>/child_skill_gate_manifest.json` with:

- selected skills and supported capabilities;
- references loaded now or deferred with reason;
- required gates;
- required approver for each gate;
- controller self-approval forbidden;
- skipped child-skill steps with reason.

Do not route from a child skill until reviewer and officer checks pass.
