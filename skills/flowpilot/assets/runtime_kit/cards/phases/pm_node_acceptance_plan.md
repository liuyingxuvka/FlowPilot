<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: System-card ACKs go directly to Router through the card check-in command; this is the router-directed return path for card ACKs. Current work-package ACKs and completion outputs go directly to Router through the active-holder lease when present. For formal role outputs, write the body only to a run-scoped packet, result, report, or decision file, then submit it with `flowpilot_runtime.py submit-output-to-router` so Router records the event and later exposes only controller-visible envelope metadata with status, paths, and hashes. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
post_ack: ACK is receipt only; ACK is not completion. After work-card ACK, continue the work assigned by this card and submit the formal output or blocker through the Router-directed runtime path.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. System-card ACKs, current work-package outputs, and formal role-output submissions go directly to Router through their runtime commands. Controller must wait for Router status or call flowpilot_router.py for the next action.
runtime_context: Treat the router delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; submit a protocol blocker through the Router-directed runtime path.
-->
# PM Node Acceptance Plan Phase

## Role Capability Reminder

- Formal work products must live in run-scoped files or project artifacts. Handoff messages point to artifacts with paths/hashes, changed paths when applicable, output contract, inspection notes, and PM Suggestion Items; the message body is not the sole work product.
- PM may directly disposition suggestions when evidence is sufficient. Consultation is optional, not a mandatory step for every suggestion.
- If PM lacks basis, or the suggestion may affect route, product target, acceptance, process safety, replay, repair return path, or risk boundary, PM may request bounded consultation through an allowed role-work request, then must record a final PM disposition after reading the advice artifact.
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
- final-user intent and product usefulness self-check for this node when
  applicable: how the node changes the user's real outcome, what would make it
  unusable or semantically downgraded, and which evidence will prove that the
  user-facing claim is true;
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
- whether the active node is a parent/module, leaf, or repair node. If it has
  children, this plan must mark the node as not worker-dispatchable and route
  execution into the child subtree or parent backward replay instead of issuing
  a worker packet for the parent;
- for a leaf or repair node, include a `leaf_readiness_gate` with `status`,
  `single_outcome`, `worker_executable_without_replanning`, `proof_defined`,
  `dependency_boundary_defined`, `failure_isolation_defined`, and
  `over_decomposition_checked`. Use `status: "pass"` only when the node can be
  completed by a worker from the packet without PM replanning;
- at node entry, re-ask whether this apparent leaf is still too broad. If it
  is too broad, split it into children through route mutation before worker
  dispatch. If it is over-split, merge or waive the extra structure with a PM
  complexity reason before dispatch;
- when a leaf is promoted to parent/module, mark old leaf approvals stale,
  attach the new ordered children, and require the local Product FlowGuard
  model, PM model decision, Reviewer product challenge, Process FlowGuard
  serial child route, PM process decision, and Reviewer route challenge before
  dispatching those children;
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
Classify every higher-standard opportunity as hard current requirement,
current-node improvement, future-route candidate, nonblocking note, or rejected
with reason. Do not turn a nonessential improvement into a hard blocker unless
it exposes a hard user-intent failure, missing proof, semantic downgrade,
unusable outcome, or unverifiable user-facing claim.

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
