<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write any role-output body only to a run-scoped packet, result, report, or decision file, then return to Controller only a controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->
# PM Evidence Quality Package Phase

Build the current-run evidence quality package before final ledger work.
Read the latest route-memory prior path context first so completed nodes,
superseded nodes, stale evidence, route mutations, and prior experiments are
represented before final ledger work starts.

Write:

- `evidence/evidence_ledger.json`;
- `generated_resource_ledger.json`;
- `quality/quality_package.json`.

Every current evidence item must be concrete, non-stale, and tied to the
current route/frontier. Generated resources, screenshots, route diagrams,
concept images, and visual assets must have terminal disposition. Old visuals
or assets may be cited as historical context only; they cannot close a current
UI or quality gate.

If the route includes UI or visual work, include screenshot paths and visual
review notes. If it does not, mark UI/visual evidence as not applicable.
