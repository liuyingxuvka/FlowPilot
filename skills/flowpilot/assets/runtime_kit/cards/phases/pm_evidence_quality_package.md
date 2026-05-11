<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: System-card ACKs go directly to Router through the card check-in command. For formal role outputs, write the body only to a run-scoped packet, result, report, or decision file, then return only the Router-directed controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. System-card ACKs go directly to Router; after formal role output completion or blocking, use the Router-directed return path. Controller must wait for or call flowpilot_router.py for the next action.
runtime_context: Treat the router delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; return a protocol blocker through Controller.
-->
# PM Evidence Quality Package Phase

## Role Capability Reminder

- Formal work products must live in run-scoped files or project artifacts. Handoff messages point to artifacts with paths/hashes, changed paths when applicable, output contract, inspection notes, and PM Suggestion Items; the message body is not the sole work product.
- PM may directly disposition suggestions when evidence is sufficient. Consultation is optional, not a mandatory step for every suggestion.
- If PM lacks basis, or the suggestion may affect route, product target, acceptance, process safety, replay, repair return path, or risk boundary, PM may request bounded consultation through an allowed role-work request, then must record a final PM disposition after reading the advice artifact.
- If a PM-owned decision still lacks evidence, modeling, research, review, or implementation support, register a bounded `pm_registers_role_work_request` only when the router's current `allowed_external_events` includes that event; otherwise record the limitation or blocker instead of emitting it.
- Treat the router's current `allowed_external_events` as the active authority for what this card may return.
- Put reviewer, worker, and officer advice that needs PM disposition into the PM suggestion/blocker ledger instead of leaving it only in prose.


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

Apply Minimum Sufficient Complexity here as evidence hygiene. Identify
artifacts, resources, route diagrams, reports, or evidence branches that no
longer change product trust, verification strength, or final delivery. They
must be consumed, superseded, quarantined, or discarded with reason rather than
left as unresolved complexity for the final ledger. Unnecessary evidence
surfaces are not quality; they are maintenance cost unless they prove a current
gate.

If the route includes UI or visual work, include screenshot paths and visual
review notes. If it does not, mark UI/visual evidence as not applicable.
