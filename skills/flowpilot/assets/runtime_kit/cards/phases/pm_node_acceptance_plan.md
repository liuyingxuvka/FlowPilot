<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: System-card ACKs go through the current runtime card check-in command; this is the current-runtime return path for card ACKs. Current work-package ACKs and completion outputs go through the assigned current packet lease when present. For formal role outputs, write the body only to a run-scoped packet, result, report, decision, or blocker file, then submit it with `flowpilot_new.py submit-result --lease-id <lease-id> --packet-id <packet-id> --body <sealed_result_summary>` so the current runtime ledger records the event and later exposes only controller-visible envelope metadata with status, paths, and hashes. A local file write is only local storage and must not be treated as wait completion until the current runtime records the packet result. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
post_ack: ACK is receipt only; ACK is not completion. This is a work item when it asks for an output, report, decision, result, or blocker. After work-card ACK, do not stop or wait for another prompt; immediately continue the assigned work and submit the formal output or blocker through the current runtime path. The task remains unfinished until the current runtime receives that output or blocker.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. System-card ACKs, current work-package outputs, and formal role-output submissions go directly through the current runtime commands. Controller must follow the `flowpilot_new.py` lifecycle guard and foreground duty; no unsupported command text, stale runtime state, chat history, or historical artifact authorizes current-run progress.
runtime_context: Treat the runtime delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; submit a protocol blocker through the current runtime path.
-->
# PM Node Acceptance Plan Phase

## Role Capability Reminder

- Formal work products must live in run-scoped files or project artifacts. Handoff messages point to artifacts with paths/hashes, changed paths when applicable, output contract, inspection notes, and PM Suggestion Items; the message body is not the sole work product.
- PM may directly disposition suggestions when evidence is sufficient. Consultation is optional, not a mandatory step for every suggestion.
- If PM lacks basis, or the suggestion may affect route, product target, acceptance, process safety, replay, repair return path, or risk boundary, PM may request bounded consultation through an allowed role-work request, then must record a final PM disposition after reading the advice artifact.
- If a PM-owned decision still lacks evidence, modeling, research, review, or implementation support, register a bounded `pm_registers_role_work_request` only when the router's current `allowed_external_events` includes that event; otherwise record the limitation or blocker instead of emitting it.
- Treat the router's current `allowed_external_events` as the active authority for what this card may return.
- Put reviewer, worker, and FlowGuard operator advice that needs PM disposition into the PM suggestion/blocker ledger instead of leaving it only in prose.
- For non-trivial node, acceptance, proof, validation, test-obligation, repair-return, or evidence-freshness judgement, cite a FlowGuard Work Order and FlowGuard Report with `flowguard_work_order_id`, `flowguard_report_id`, `flowguard_report_freshness`, and PM acceptance, or record a scoped `flowguard_not_required_reason`.
- In mature FlowGuard projects, read `docs/flowguard_project_topology.md` as background architecture before node acceptance planning. It guides relevant model/test/code/evidence inspection, but it is not a FlowGuard Report and is not gate evidence. If this phase changes topology sources, rebuild and check the topology before claiming done.


Before issuing a current-node work packet, write the active node acceptance
plan.

Submit the node acceptance plan as a current packet result with a top-level
`node_context_package`. Runtime owns mechanical validation of required fields,
node identity, packet kind, route scope, hashes, and current-run identity. A
mechanically valid result is staged as `commit_node_acceptance_plan`; it is not
an accepted node plan and must not claim accepted `node_acceptance_plan_id` or
`node_context_package_id` until FlowGuard, Reviewer, and system closure pass.

Use only the active route, active frontier, root acceptance contract, product
function architecture, approved child-skill gate manifest, and latest
route-memory prior path context. The plan must state:

- active route id, route version, and node id;
- requirement traceability for this node: copy the active route node's
  `covers_requirement_ids`, `covers_scenario_ids`, and
  `source_product_capability_ids`; every node requirement, experiment,
  work-packet projection, and selected child-skill binding must state which
  requirement ids it covers;
- prior path context files read and how completed, superseded, stale, blocked,
  or experimental history affects this node;
- concrete node requirements and proof obligations;
- `test_obligation_matrix.pre_worker`: every FlowGuard-backed product,
  process, child-skill, acceptance-slice, and validation obligation that needs
  ordinary test or replay evidence before this node can close. Each row must
  name `obligation_id`, `source`, `required_test_kind`, `owner_role`,
  `expected_evidence`, `freshness_rule`, and current PM disposition. For any
  FlowGuard operator modeling used to derive these rows, include `role_skill_use_bindings`
  for the exact FlowGuard child skill or satellite route PM selected, such as
  Existing Model Preflight, DevelopmentProcessFlow, Model-Test Alignment, or
  TestMesh;
  each FlowGuard-derived row must retain originating `flowguard_work_order_id`,
  `flowguard_report_id`, `flowguard_report_freshness`, and PM disposition so
  stale, skipped, progress-only, or unaccepted reports cannot close the node;
- the product behavior model segment this node covers, or the reason this node
  is process-only;
- final-user intent and product usefulness self-check for this node when
  applicable: how the node changes the user's real outcome, what would make it
  unusable or semantically downgraded, and which evidence will prove that the
  user-facing claim is true;
- low-quality-success self-check for this node: inherited hard parts from the
  product architecture or root contract, the node-local hard part, the
  thin-success shortcut most likely to make the node look complete while still
  being low quality, warning signs PM and Reviewer should distrust, and proof
  of depth that must appear in the worker/FlowGuard operator result;
- `structure_hygiene_expectation`: the node-local expectation for patch stacks,
  fallback-like paths, compatibility branches, duplicate adapters, generated
  leftovers, and maintenance layers. State whether the node must remove,
  reject, preserve as negative rejection evidence, retain as owned
  current-runtime recovery, retain as an owned maintenance layer, or block on
  each surface. Any retained surface must have owner, scope, validation
  evidence, and sunset or next-disposition criteria;
- inherited `skill_standard_projection`: every child-skill standard relevant
  to this node, grouped by `MUST`, `DEFAULT`, `FORBID`, `VERIFY`, `LOOP`,
  `ARTIFACT`, and `WAIVER`, with standard ids, source skill, source path,
  required artifact path, required reviewer/FlowGuard operator gate, and whether it is
  completed here, completed later, not applicable, or waived by PM authority;
- `active_child_skill_bindings`: for each selected child skill that supplies
  execution behavior for this node, name the exact child skill, source
  `SKILL.md` path, required reference paths, current-node slice, packet ids,
  selected standard ids, and result evidence required. The PM packet is the
  minimum floor; if the child skill has a stricter applicable requirement, the
  stricter child-skill requirement wins unless PM records an explicit waiver;
- `role_skill_use_bindings`: for each selected child skill that supports this
  node or gate through PM planning, specification, route design, reviewer
  review, FlowGuard operator modeling, validation, or worker execution, name the exact
  role, use context, source `SKILL.md`, referenced paths, selected standard
  ids, affected output or gate, and Role Skill Use Evidence required. Include
  PM's own planning skill use when it materially shapes acceptance criteria,
  route structure, node proof, or validation expectations;
- `work_packet_projection`: the exact inherited standard ids that must be
  copied into each worker/FlowGuard operator packet, plus the active child-skill bindings
  that must be copied into each worker packet with direct-use instructions,
  allowed source paths, result-matrix rows, and `Child Skill Use Evidence`
  rows the recipient must return. When a packet or role-output request carries
  `role_skill_use_bindings`, also copy the Role Skill Use Evidence rows the
  recipient must return. When the node declares test obligations, copy the
  relevant `test_obligation_matrix.pre_worker` rows into the worker or FlowGuard operator
  packet and require `Test Obligation Coverage` rows in the result for every
  packet-scoped test obligation. Also copy the relevant
  `structure_hygiene_expectation` rows into every worker or repair packet and
  require `Structure Hygiene Delta` in the result. Do not issue a work packet if this projection
  is missing for a selected child skill or required test obligation;
- minimum sufficient complexity review for this node;
- experiments, checks, fixtures, and evidence paths;
- direct evidence closure rules: report prose, file existence, or a clean
  ledger row is not enough to close a covered requirement unless the root
  contract explicitly allowed that evidence type. Name direct evidence,
  scenario replay, reviewer/FlowGuard operator check, waiver authority, or unresolved
  reason for every covered requirement;
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
  attach the new ordered children, and require the local FlowGuard operator product-model
  model, PM model decision, Reviewer product challenge, FlowGuard operator process-model
  serial child route, PM process decision, and Reviewer route challenge before
  dispatching those children;
- forbidden low-standard or placeholder outcomes;
- forbidden thin-success outcomes where an artifact, command, report,
  screenshot, or ledger entry exists but the hard part was only handled
  casually;
- recheck criteria proving the node still meets the frozen contract after
  worker output, repair, or route mutation.

After worker, FlowGuard operator, or reviewer output returns, PM must update
`test_obligation_matrix.post_worker` before approving node completion. The
post-worker matrix must absorb changed paths, new or stale evidence, skipped
checks, failed checks, background tests without complete exit/meta artifacts,
and FlowGuard operator `missing_test_kinds`. Every row must be dispositioned as
`covered`, `worker_test_packet_required`, `testmesh_required`,
`model_test_alignment_required`, `waived_with_authority`,
`deferred_to_named_node`, or `blocked`. Undispositioned rows block PM
node-completion approval.

## Supporting Skill Fidelity

When a supporting child skill is selected for this node, do not summarize it
only at the theme level. Read the skill body and any directly referenced
required files, then preserve the skill's binding requirements in this node
acceptance plan.

Binding requirements include, when present: which formal role must use the
skill, concrete counts or ranges, required ordering, default iteration or retry
budgets, required artifacts, required evidence, forbidden substitutions,
reviewer gates, final verdict rules, waiver or blocker rules, and explicit
non-goals.

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
Also list impacted requirement ids, superseded requirement ids, stale evidence
refs, and required rerun models/checks. Old evidence cannot close a changed or
superseded requirement.

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
It must also include a concrete low-quality-success mapping for this node:
hard parts, thin-success shortcut, proof of depth, reviewer probe, and whether
the concern is a hard current requirement or PM decision-support.
It must also include `structure_hygiene_expectation`, even when the expected
answer is that no fallback-like path, compatibility branch, stale generated
artifact, duplicate adapter, or maintenance layer is expected. A missing
structure hygiene expectation blocks packet dispatch.
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
Then write or update a `flowpilot.self_interrogation_record.v1` with scope
`node_entry`, the active route version, and the active node id. Register it in
`self_interrogation_index.json`. Current-node packet registration and relay
are blocked until this node-entry record is clean and all hard/current
findings are dispositioned by PM.
When the router's `validate-artifact` command is available, run it with
`--type node_acceptance_plan` against that file before asking for reviewer
approval, then repair all missing fields in one pass.
Do not register a current-node work packet until Reviewer passes this plan.
