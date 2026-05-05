<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Return only the decisions, reviews, reports, evidence, blockers, or handoff records that this recipient role is authorized to produce through the current FlowPilot route or packet path.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->
# PM Node Acceptance Plan Phase

Before issuing a current-node work packet, write the active node acceptance
plan.

Use only the active route, active frontier, root acceptance contract, product
function architecture, approved child-skill gate manifest, and latest
route-memory prior path context. The plan must state:

- active route id, route version, and node id;
- prior path context files read and how completed, superseded, stale, blocked,
  or experimental history affects this node;
- concrete node requirements and proof obligations;
- experiments, checks, fixtures, and evidence paths;
- whether the node has children and therefore requires parent backward replay;
- forbidden low-standard or placeholder outcomes;
- recheck criteria proving the node still meets the frozen contract after
  worker output, repair, or route mutation.

Write
`.flowpilot/runs/<run-id>/routes/<route-id>/nodes/<node-id>/node_acceptance_plan.json`.
Do not register a current-node work packet until Reviewer passes this plan.
