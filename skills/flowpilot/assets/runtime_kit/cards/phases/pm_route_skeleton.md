<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write any role-output body only to a run-scoped packet, result, report, or decision file, then return to Controller only a controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->
# PM Route Skeleton Phase

Draft the route from reviewed material and product understanding.

Before drafting, read the latest
`.flowpilot/runs/<run-id>/route_memory/pm_prior_path_context.json` and
`route_history_index.json`. If this is a fresh route, cite that the context
contains no completed or superseded nodes yet. Do not draft from chat history,
old route files, or Controller summaries.

Route requirements:

- fresh current run only;
- large nodes expanded horizontally;
- each large node owns concrete checklist items;
- include a concise PM-authored visible route summary suitable for
  `display_plan.json`; it may be high level, but it must name the route nodes
  that Controller is allowed to show in the host visible plan;
- worker-capable nodes must close with all checklist items complete;
- human manual checks belong in final reports or review gates, not as fake
  unfinished worker nodes;
- officer and reviewer route checks are required before activation.

Do not activate a route until Process Officer, Product Officer, and Reviewer
checks pass.

Return `prior_path_context_review` with the route-memory source paths and how
prior completed, superseded, stale, blocked, or experimental work affects this
route draft.
