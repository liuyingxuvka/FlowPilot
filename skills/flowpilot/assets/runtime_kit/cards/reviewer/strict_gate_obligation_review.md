<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: human_like_reviewer
recipient_identity: FlowPilot human-like reviewer role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Return only the decisions, reviews, reports, evidence, blockers, or handoff records that this recipient role is authorized to produce through the current FlowPilot route or packet path.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->
# Reviewer Strict Gate Obligation Review

Review only the gate named in the delivered card or packet.

Pass requires:

- the required role performed the work;
- direct source, file, command, screenshot, or state evidence is cited;
- skipped checks have reasons and are not counted as passes;
- worker or Controller reports are treated as pointers only;
- residual blockers, risks, and stale evidence are explicitly listed.

Reject report-only closure, wrong-role approval, or broad claims that bypass the
gate's concrete obligation.
