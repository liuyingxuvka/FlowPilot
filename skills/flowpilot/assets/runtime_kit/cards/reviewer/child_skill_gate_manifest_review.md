<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: human_like_reviewer
recipient_identity: FlowPilot human-like reviewer role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Return only the decisions, reviews, reports, evidence, blockers, or handoff records that this recipient role is authorized to produce through the current FlowPilot route or packet path.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->
# Reviewer Child Skill Gate Manifest Review

Personally review the PM child-skill gate manifest.

Check:

- selected skills follow product needs and frozen contract;
- raw inventory is not used as authority;
- skipped references or skipped steps have reasons;
- each child-skill gate has a real approver;
- Controller is not an approver;
- evidence expectations are concrete enough for route work;
- skipped child-skill steps are not silently waived;
- officer checks are requested where process or product fit remains uncertain.

Pass only after direct review.
