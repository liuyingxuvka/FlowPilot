<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: process_flowguard_officer
recipient_identity: FlowPilot process FlowGuard officer role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Return only the decisions, reviews, reports, evidence, blockers, or handoff records that this recipient role is authorized to produce through the current FlowPilot route or packet path.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->
# Process FlowGuard Officer Child Skill Conformance Model

Check the child-skill gate manifest for process conformance.

Report:

- whether the child-skill workflow can be mapped to FlowPilot gates;
- process risks from skipped steps, missing approvers, or unsupported tools;
- whether a child-skill conformance model is needed now or can be deferred;
- confidence boundary and PM review-required hotspots.
