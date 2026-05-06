<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write any role-output body only to a run-scoped packet, result, report, or decision file, then return to Controller only a controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
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
- minimum sufficient complexity review for this node;
- experiments, checks, fixtures, and evidence paths;
- whether the node has children and therefore requires parent backward replay;
- forbidden low-standard or placeholder outcomes;
- recheck criteria proving the node still meets the frozen contract after
  worker output, repair, or route mutation.

The returned plan must include a complete `prior_path_context_review` object
with `reviewed`, `source_paths`, `completed_nodes_considered`,
`superseded_nodes_considered`, `stale_evidence_considered`,
`prior_blocks_or_experiments_considered`, and `impact_on_decision`.

The returned plan must include a complete `high_standard_recheck` object with
`ideal_outcome`, `unacceptable_outcomes`, `higher_standard_opportunities`,
`semantic_downgrade_risks`, `decision`, and
`why_current_plan_meets_highest_reasonable_standard`. Use `decision:
proceed` only when the plan already reaches the highest reasonable standard
for this node without unnecessary complexity.

For Minimum Sufficient Complexity, record whether a simpler equivalent node
plan exists, why the chosen packet/check/evidence structure is the smallest
structure that still proves the node, and which extra complexity sources are
justified by real risk, role authority, verification strength, failure
isolation, or user-visible value.

Write
`.flowpilot/runs/<run-id>/routes/<route-id>/nodes/<node-id>/node_acceptance_plan.json`.
When the router's `validate-artifact` command is available, run it with
`--type node_acceptance_plan` against that file before asking for reviewer
approval, then repair all missing fields in one pass.
Do not register a current-node work packet until Reviewer passes this plan.
