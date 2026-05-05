<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: human_like_reviewer
recipient_identity: FlowPilot human-like reviewer role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Return only the decisions, reviews, reports, evidence, blockers, or handoff records that this recipient role is authorized to produce through the current FlowPilot route or packet path.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->
# Reviewer Evidence Quality Review

Review the PM evidence quality package before final ledger work starts.

Check:

- evidence ledger entries are concrete, current, and non-stale;
- generated resources have terminal disposition;
- UI or visual evidence is present when the route requires it;
- old screenshots, old icons, old concept images, or old assets are not reused
  as current evidence;
- completion report-only evidence is not closing a gate that needs direct
  inspection or executable proof.

Pass only when unresolved evidence count and unresolved resource count are zero.
