<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write any role-output body only to a run-scoped packet, result, report, or decision file, then return to Controller only a controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->
# PM Officer Request-Report Loop

Use FlowGuard officers through bounded request and report packets.

For each modeling need, write a request that states:

- process, product, or joint officer ownership;
- modeling kind: process, product, object/reference-system, migration
  equivalence, experiment-derived behavior, or combined;
- model boundary, hard invariants, observed/source behavior, expected target
  behavior, and decisions the PM needs;
- required commands or replay checks;
- evidence paths, source materials, samples, traces, or experiment outputs the
  officer may inspect;
- how the report can change the route.

The officer report supports PM decisions; it cannot approve completion, waive
reviewer gates, or claim no risk beyond its model boundary.
