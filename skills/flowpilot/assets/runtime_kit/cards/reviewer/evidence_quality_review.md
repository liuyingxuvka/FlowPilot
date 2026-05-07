<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: human_like_reviewer
recipient_identity: FlowPilot human-like reviewer role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write any role-output body only to a run-scoped packet, result, report, or decision file, then return to Controller only a controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
runtime_context: Treat the router delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; return a protocol blocker through Controller.
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

Router ledgers and router-owned proofs may settle counts, hashes, freshness
markers, and stale/resource disposition only when the proof is non-self-attested
and `mechanical_only`. They do not replace your evidence legitimacy and
route-fit judgement.

Pass only when unresolved evidence count and unresolved resource count are zero.
