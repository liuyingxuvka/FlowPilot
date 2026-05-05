<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write any role-output body only to a run-scoped packet, result, report, or decision file, then return to Controller only a controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->
# PM Dependency Policy Phase

Record the dependency and installation policy for this run.

Rules:

- no host-level, paid, private-account, destructive, or non-reversible install
  may proceed without explicit user approval;
- local availability is only candidate evidence;
- companion skills are not invoked only because they exist;
- route work may use only capabilities selected by PM for product need;
- unapproved installs, stale dependencies, old assets, private-account
  dependencies, and contaminated outputs must be quarantined with reason.

Write:

1. `.flowpilot/runs/<run-id>/dependency_policy.json`;
2. `.flowpilot/runs/<run-id>/capabilities.json`, mapping product capabilities
   from the product-function architecture and root contract to capability needs.

Record allowed, blocked, deferred, and quarantined dependencies separately.
Quarantined items cannot close gates unless PM later records approved repair
and reviewer evidence.

Only after both files exist may the router deliver the child-skill selection
card.
