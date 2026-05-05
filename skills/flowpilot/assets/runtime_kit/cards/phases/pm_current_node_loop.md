<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Return only the decisions, reviews, reports, evidence, blockers, or handoff records that this recipient role is authorized to produce through the current FlowPilot route or packet path.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->
# PM Current Node Loop Phase

For each active route node:

1. receive the node-started event card;
2. read the latest route-memory prior path context and active frontier;
3. issue a bounded packet for the current node only;
4. wait for reviewer dispatch before worker delivery;
5. wait for worker result and reviewer result review;
6. perform a PM high-standard recheck against the node acceptance plan;
7. complete the node only after reviewer pass or repair pass.

If reviewer blocks, enter review repair. If reviewed evidence shows route
structure is wrong, mutate the route and rerun required checks.

The PM recheck must cite reviewed evidence, remaining proof obligations, stale
evidence decisions, and why the result is not placeholder or report-only work.

Any packet, completion, repair, or mutation decision must include
`prior_path_context_review` showing which completed nodes, superseded nodes,
stale evidence, prior blocks, and experiments were considered.
