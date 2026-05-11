<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write any role-output body only to a run-scoped packet, result, report, or decision file, then return to Controller only a controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
runtime_context: Treat the router delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; return a protocol blocker through Controller.
-->
# PM Node Acceptance Plan Phase

## Role Capability Reminder

- If a PM-owned decision still lacks evidence, modeling, research, review, or implementation support, register a bounded `pm_registers_role_work_request` only when the router's current `allowed_external_events` includes that event; otherwise record the limitation or blocker instead of emitting it.
- Treat the router's current `allowed_external_events` as the active authority for what this card may return.
- Put reviewer, worker, and officer advice that needs PM disposition into the PM suggestion/blocker ledger instead of leaving it only in prose.


Before issuing a current-node work packet, write the active node acceptance
plan.

Use only the active route, active frontier, root acceptance contract, product
function architecture, approved child-skill gate manifest, and latest
route-memory prior path context. The plan must state:

- active route id, route version, and node id;
- prior path context files read and how completed, superseded, stale, blocked,
  or experimental history affects this node;
- concrete node requirements and proof obligations;
- the product behavior model segment this node covers, or the reason this node
  is process-only;
- inherited `skill_standard_projection`: every child-skill standard relevant
  to this node, grouped by `MUST`, `DEFAULT`, `FORBID`, `VERIFY`, `LOOP`,
  `ARTIFACT`, and `WAIVER`, with standard ids, source skill, source path,
  required artifact path, required reviewer/officer gate, and whether it is
  completed here, completed later, not applicable, or waived by PM authority;
- `active_child_skill_bindings`: for each selected child skill that supplies
  execution behavior for this node, name the exact child skill, source
  `SKILL.md` path, required reference paths, current-node slice, packet ids,
  selected standard ids, and result evidence required. The PM packet is the
  minimum floor; if the child skill has a stricter applicable requirement, the
  stricter child-skill requirement wins unless PM records an explicit waiver;
- `work_packet_projection`: the exact inherited standard ids that must be
  copied into each worker/officer packet, plus the active child-skill bindings
  that must be copied into each worker packet with direct-use instructions,
  allowed source paths, result-matrix rows, and `Child Skill Use Evidence`
  rows the recipient must return. Do not issue a work packet if this projection
  is missing for a selected child skill;
- minimum sufficient complexity review for this node;
- experiments, checks, fixtures, and evidence paths;
- whether the node has children and therefore requires parent backward replay;
- forbidden low-standard or placeholder outcomes;
- recheck criteria proving the node still meets the frozen contract after
  worker output, repair, or route mutation.

## Supporting Skill Fidelity

When a supporting child skill is selected for this node, do not summarize it
only at the theme level. Read the skill body and any directly referenced
required files, then preserve the skill's binding requirements in this node
acceptance plan.

Binding requirements include, when present: concrete counts or ranges,
required ordering, default iteration or retry budgets, required artifacts,
required evidence, forbidden substitutions, reviewer gates, final verdict
rules, waiver or blocker rules, and explicit non-goals.

Do not weaken a specific skill requirement into a generic phrase. If wording is
compressed, preserve the same acceptance force. If a skill requirement is
deferred, name the later node that will satisfy it and the evidence that will
close it.

Examples of weakening to avoid:

- replacing a required multi-candidate search, scoring, synthesis, and final
  selection process with "generate concepts";
- replacing required replay or check commands with "run validation";
- replacing required screenshot-after-each-iteration behavior with "iterate
  visually";
- replacing a forbidden-substitution rule with "use appropriate assets".

For a repair node, include the mainline node or parent segment it returns to
and the product-model, process-model, reviewer, or evidence checks that become
stale and must rerun before mainline work resumes.

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
