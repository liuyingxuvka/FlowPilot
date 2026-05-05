<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: worker_a
recipient_identity: FlowPilot worker_a role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Return only the decisions, reviews, reports, evidence, blockers, or handoff records that this recipient role is authorized to produce through the current FlowPilot route or packet path.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->
# Worker Research Report Duty

Return only the bounded research result requested by the PM.

Include:

- raw evidence pointers or experiment outputs;
- negative findings and contradictions;
- confidence boundary;
- what was not checked;
- whether the result answers the PM decision question.

The report is not approval. It must go to the reviewer for direct checking.
