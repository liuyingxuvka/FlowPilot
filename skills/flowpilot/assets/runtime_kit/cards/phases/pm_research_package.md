<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write any role-output body only to a run-scoped packet, result, report, or decision file, then return to Controller only a controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
runtime_context: Treat the router delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; return a protocol blocker through Controller.
-->
# PM Research Package Phase

## Role Capability Reminder

- If a PM-owned decision still lacks evidence, modeling, research, review, or implementation support, register a bounded `pm_registers_role_work_request` only when the router's current `allowed_external_events` includes that event; otherwise record the limitation or blocker instead of emitting it.
- Treat the router's current `allowed_external_events` as the active authority for what this card may return.


Use this card only after the reviewer reports material insufficient.

Write a bounded research package that names:

- the decision the PM cannot safely make yet;
- allowed source or experiment types;
- host capability or approval constraints;
- worker owner and stop conditions;
- direct-source or experiment-output checks the reviewer must perform;
- how the result can affect material understanding, route mutation, user
  questions, or blocking.

Before assigning a worker packet, consider worker balance and packet shape. For
light or single-scope work, choose either `worker_a` or `worker_b` while keeping
worker opportunities roughly balanced across the current run. For heavy work
that naturally splits into disjoint scopes, create bounded separate packets for
`worker_a` and `worker_b` so they can run in parallel without overlapping files,
evidence duties, or review ownership.

Any research worker packet created from the package must include the registry
`output_contract` `flowpilot.output_contract.worker_research_result.v1` in both
the packet envelope and packet body's `Output Contract` section.
The packet body must also include the generated `Report Contract For This Task`
block, including the required research result sections and the blocked/needs-PM
return path. Do not rely on the worker to infer the research report format from
this phase card alone.
The packet body must also ask the worker to include a soft `PM Note` in the
sealed result body with exactly these labels: `In-scope quality choice` and
`PM consideration`. This note is PM decision-support, not a reviewer hard gate:
the worker should use the simplest high-quality approach inside the packet
boundary, and report out-of-scope better ideas or route risks to PM without
expanding the packet.
The packet body must also require a `PM Suggestion Items` section. Worker
suggestions are candidate `flowpilot.pm_suggestion_item.v1` items for PM's
ledger disposition and never authorize current-gate blocking by themselves.

Do not proceed to product architecture until reviewed research is absorbed or
the route is explicitly changed or blocked.
