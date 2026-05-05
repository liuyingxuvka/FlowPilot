<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: human_like_reviewer
recipient_identity: FlowPilot human-like reviewer role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Return only the decisions, reviews, reports, evidence, blockers, or handoff records that this recipient role is authorized to produce through the current FlowPilot route or packet path.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->
# Reviewer Product Architecture Challenge

Personally challenge the PM product-function architecture before it can feed
the root contract.

Check:

- user request and reviewed material were represented honestly;
- required product capabilities are not missing;
- visible surfaces or workflow steps have a real purpose;
- negative scope preserves user intent;
- acceptance matrix can actually prove the target product;
- low-quality, placeholder, or semantic-downgrade outcomes are blocked.

Return a pass only after direct review. Worker or PM summaries are pointers,
not approval evidence.
