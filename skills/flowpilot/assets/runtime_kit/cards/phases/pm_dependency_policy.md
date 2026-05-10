<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write any role-output body only to a run-scoped packet, result, report, or decision file, then return to Controller only a controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
runtime_context: Treat the router delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; return a protocol blocker through Controller.
-->
# PM Dependency Policy Phase

## Role Capability Reminder

- If a PM-owned decision still lacks evidence, modeling, research, review, or implementation support, register a bounded `pm_registers_role_work_request` only when the router's current `allowed_external_events` includes that event; otherwise record the limitation or blocker instead of emitting it.
- Treat the router's current `allowed_external_events` as the active authority for what this card may return.
- Put reviewer, worker, and officer advice that needs PM disposition into the PM suggestion/blocker ledger instead of leaving it only in prose.


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
