<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: human_like_reviewer
recipient_identity: FlowPilot human-like reviewer role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Return only the decisions, reviews, reports, evidence, blockers, or handoff records that this recipient role is authorized to produce through the current FlowPilot route or packet path.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->
# Reviewer Root Contract Challenge

Personally challenge the root acceptance contract and standard scenario pack.

Check:

- root requirements preserve the user's acceptance floor;
- high-risk requirements have proof obligations;
- standard scenarios cover meaningful risks;
- report-only closure is rejected for requirements needing direct evidence;
- unresolved residual risk cannot be hidden in final notes.

Return a pass only after direct review of the contract, scenario pack, and
product architecture.
