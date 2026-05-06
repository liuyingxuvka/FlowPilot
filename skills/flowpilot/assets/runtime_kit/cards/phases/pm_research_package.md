<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write any role-output body only to a run-scoped packet, result, report, or decision file, then return to Controller only a controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->
# PM Research Package Phase

Use this card only after the reviewer reports material insufficient.

Write a bounded research package that names:

- the decision the PM cannot safely make yet;
- allowed source or experiment types;
- host capability or approval constraints;
- worker owner and stop conditions;
- direct-source or experiment-output checks the reviewer must perform;
- how the result can affect material understanding, route mutation, user
  questions, or blocking.

Any research worker packet created from the package must include the registry
`output_contract` `flowpilot.output_contract.worker_research_result.v1` in both
the packet envelope and packet body's `Output Contract` section.
The packet body must also include the generated `Report Contract For This Task`
block, including the required research result sections and the blocked/needs-PM
return path. Do not rely on the worker to infer the research report format from
this phase card alone.

Do not proceed to product architecture until reviewed research is absorbed or
the route is explicitly changed or blocked.
