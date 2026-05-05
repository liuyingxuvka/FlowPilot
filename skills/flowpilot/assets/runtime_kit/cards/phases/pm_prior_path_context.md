<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write any role-output body only to a run-scoped packet, result, report, or decision file, then return to Controller only a controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->
# PM Prior Path Context Phase

Before route draft, node acceptance planning, repair, route mutation, resume
continuation, final ledger, or closure, read the latest current-run prior path
context:

- `.flowpilot/runs/<run-id>/route_memory/pm_prior_path_context.json`;
- `.flowpilot/runs/<run-id>/route_memory/route_history_index.json`;
- any source paths cited by those files that are relevant to the decision.

Treat Controller-written route memory as an index of current-run facts and
source paths only. It is not acceptance evidence and cannot replace reviewer,
officer, worker, or PM-owned source files.

Every protected PM decision must return `prior_path_context_review` with:

- `reviewed: true`;
- `source_paths` citing both current route-memory files;
- completed nodes considered;
- superseded nodes considered;
- stale evidence considered;
- prior blocks or experiments considered;
- impact on the route, node, repair, resume, ledger, or closure decision;
- `controller_summary_used_as_evidence: false`.

If the context is missing, stale, cross-run, or inconsistent with active
frontier, stop and ask Controller to refresh route memory through the router.
