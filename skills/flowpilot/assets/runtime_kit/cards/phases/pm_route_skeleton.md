<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write any role-output body only to a run-scoped packet, result, report, or decision file, then return to Controller only a controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
runtime_context: Treat the router delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; return a protocol blocker through Controller.
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
- Minimum Sufficient Complexity: choose the smallest route structure that can
  satisfy the frozen contract with the required proof strength;
- large nodes expanded horizontally;
- each large node owns concrete checklist items;
- each separate node must close a distinct risk, produce distinct evidence,
  enforce a role boundary, enable real parallelism, isolate failure recovery,
  or represent a user-visible milestone;
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

Also return a complexity review. If a node could have been merged with an
adjacent node, record why separation is still necessary. If two routes produce
the same outcome and proof strength, choose the one with fewer nodes, handoffs,
artifacts, and dependencies.
