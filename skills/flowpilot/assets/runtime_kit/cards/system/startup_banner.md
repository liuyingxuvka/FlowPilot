<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: bootloader
recipient_identity: FlowPilot bootloader startup display recipient
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Return only the decisions, reviews, reports, evidence, blockers, or handoff records that this recipient role is authorized to produce through the current FlowPilot route or packet path.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->
FLOWPILOT PROMPT-ISOLATED STARTUP

Startup answers are recorded. This banner is display-only data.

Do not infer the next action from this file. Return to `flowpilot_router.py`
and execute only the next JSON action envelope.
