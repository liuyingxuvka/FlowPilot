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
- select a `planning_profile` before drafting. At minimum classify the task as
  one of `interactive_software_ui_product`, `software_engineering`,
  `research_writing`, `release_delivery`, `debug_repair`,
  `simple_repair`, or `long_running_multi_role`. Record why the profile fits
  the user's quality level and why a lighter profile would lose required proof
  strength. For a small task, use `simple_repair` with an explicit waiver
  instead of importing heavyweight UI/product loops;
- Minimum Sufficient Complexity: choose the smallest route structure that can
  satisfy the frozen contract with the required proof strength;
- use the Product FlowGuard Officer's product behavior model as route input:
  map the route to its essential user actions, product states,
  failure/recovery paths, forbidden downgrades, and completion evidence;
- Router will not activate the route unless the Product Officer's product
  behavior model report already exists, the route receives a role-owned
  product-model review pass, and Process Officer returns
  `process_viability_verdict: "pass"`;
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

Also return `planning_profile_review` with:

- selected profile and task-class rationale;
- how the selected route covers the product behavior model without lowering
  the product target;
- required horizontal modules inserted for this profile, such as skill-standard
  compilation, concept convergence, interaction validation, realtime-state
  mapping, desktop integration, release delivery, or user-facing final report;
- route nodes that own those modules;
- evidence artifacts expected from each major node;
- explicit self-check that the route is not too coarse for the user's stated
  quality level.

Also return a complexity review. If a node could have been merged with an
adjacent node, record why separation is still necessary. If two routes produce
the same outcome and proof strength, choose the one with fewer nodes, handoffs,
artifacts, and dependencies.

For repair or route-mutation paths, state which mainline node the repair
returns to and which product-model checks or evidence must be rerun before
mainline work continues.

For any route mutation, include `repair_return_to_node_id`. Router will clear
stale route approvals after mutation, so PM must redraft or confirm the changed
route and rerun the route checks before current-node work continues.
