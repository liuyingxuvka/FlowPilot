<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Return only the decisions, reviews, reports, evidence, blockers, or handoff records that this recipient role is authorized to produce through the current FlowPilot route or packet path.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->
# PM Material Understanding Phase

Write `.flowpilot/runs/<run-id>/pm_material_understanding.json` from reviewed
material and, when required, reviewer-approved research.

Include:

- material source summary and authority;
- freshness, contradictions, and deferred sources;
- capability and host facts discovered during scan;
- PM decision on whether research was not required or has been absorbed;
- open questions or route consequences.

This memo is the only material basis for product architecture. Do not proceed
from raw worker reports or unchecked research.
