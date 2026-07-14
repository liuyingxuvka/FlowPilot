<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: human_like_reviewer
recipient_identity: FlowPilot human-like reviewer role
allowed_scope: Use this card only while acting as the human-like reviewer for the PM route challenge assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, PM, FlowGuard operators, workers, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: System-card ACKs go through the current runtime card check-in command; this is the current-runtime return path for card ACKs. Current work-package ACKs and completion outputs go through the assigned current packet lease when present. For formal role outputs, write the body only to a run-scoped packet, result, report, decision, or blocker file, then submit it with `flowpilot_new.py submit-result --lease-id <lease-id> --packet-id <packet-id> --body-file <sealed_result_body_file>` so the current runtime ledger records the event and later exposes only controller-visible envelope metadata with status, paths, and hashes. A local file write is only local storage and must not be treated as wait completion until the current runtime records the packet result. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
post_ack: ACK is receipt only; ACK is not completion. This is a work item when it asks for an output, report, decision, result, or blocker. After work-card ACK, do not stop or wait for another prompt; immediately continue the assigned work and submit the formal output or blocker through the current runtime path. The task remains unfinished until the current runtime receives that output or blocker.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. System-card ACKs, current work-package outputs, and formal role-output submissions go directly through the current runtime commands. Controller must follow the `flowpilot_new.py` lifecycle guard and foreground duty; no unsupported command text, stale runtime state, chat history, or historical artifact authorizes current-run progress.
runtime_context: Treat the runtime delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; submit a protocol blocker through the current runtime path.
-->

# Route Challenge

## Role Capability Reminder

- Do not contact workers or FlowGuard operators directly; when another role's work is needed, make it a blocker or PM suggestion for PM to route.
- Classify findings as hard blockers for this gate, future requirements, or nonblocking notes; only hard current-gate failures should block this gate.


## Decision-Support Findings

For every outcome, consider PM decision-support observations. Put
higher-standard opportunities, simpler equivalent paths, and quality
improvements that do not themselves block this gate into `pm_suggestion_items`.
When useful, express these findings as candidate
`flowpilot.pm_suggestion_item.v1` entries for PM's suggestion ledger. Use
`current_gate_blocker` only when the current gate's minimum standard cannot be
guaranteed.

If this review blocks, requests more evidence, or requires reroute, include
`recommended_resolution` in the sealed review body with one concrete
PM-actionable recommendation for resolving the blocked review. PM remains the
owner of final repair strategy.

For every pass or block, make the challenge visible in existing fields: name
the current-stage object, the weakest evidence inspected, one concrete failure
hypothesis or a no-hypothesis rationale, any thin-success or existence-only
risk that applies, and a PM-actionable adopt/reject/no-action rationale. Do not
answer with only mechanical completeness, boundary language, or generic `9/10`
optimization advice.

Review the PM route draft after FlowGuard operator product-model has produced the product
behavior model, PM has written implementation intent, FlowGuard operator has
produced the target-realization model, Reviewer has passed that bridge,
FlowGuard operator process-model has produced a serial route model, and PM has
accepted that process model.

Independently challenge whether the route is understandable, executable, and
faithful to the user's current request and frozen contract. Treat source-intent
from those artifacts as part of route fidelity. Treat FlowGuard operator
reports as pointers, not as your own inspection.

Check:

- the active route draft is the same draft the FlowGuard operator
  checked;
- the route carries the accepted target-realization obligations, thin-success
  traps, non-downgrade rules, and evidence gates into route nodes, packet
  boundaries, reviewer checks, FlowGuard checks, and final closure;
- the route keeps core deliverable non-downgrade on the single execution path.
  Block if any node or closure path can mark the original target complete with
  a reachable-only subset, status-only note, report-only artifact, honest
  missing explanation, external-only label, partial count, not-yet-done marker,
  or absence-of-fabrication proof unless the route cites explicit user
  authority to lower that target;
- the process route is a single ordered execution line, including ordered
  children for every parent/module and ordered deeper children as needed;
- the ordered route satisfies producer-before-consumer dependency direction.
  Challenge whether any node artifact, acceptance criterion, required output,
  deliverable check, or validation check consumes output or evidence that is
  only produced by a later unfinished node. If so, block route approval through
  the existing review result fields and recommend PM route repair without
  becoming the route author;
- the selected planning profile matches the task type and stated quality level;
- the selected planning profile does not create a light/simple FlowPilot mode.
  Formal FlowPilot use must keep the full protocol; if PM treats a small task
  as a reason to waive core gates, block the route;
- the route preserves the startup and product high-quality current-run posture.
  Block if a structurally valid route has lowered a sparse startup request into
  a merely passable plan without concrete user-useful output, acceptance
  evidence, or proof of depth;
- route nodes and checklists are not over-simplified, overmerged, or too coarse
  to produce concrete acceptance artifacts. Do not block merely because PM did
  not add broad explanatory route-node fields. Instead, inspect whether the
  existing route shape, acceptance criteria, outputs, checks, and requirement
  or skill ids make the scope reviewable;
- the route is not artificially capped at two levels. Complex parent/module
  nodes must be recursively decomposed until every executable leaf is one
  independently accountable bounded workstream, and the route must still provide a shallow
  user-visible projection for display;
- a complex flat all-leaf route plan is under-decomposed even if it has many
  named nodes. If related leaves share a broad stage, dependency order, or
  acceptance boundary, block and require PM to group them under parent/module
  scopes in the canonical route tree;
- PM authored one canonical executable route tree, not one tree for execution
  plus a second PM-maintained display plan. Treat `display_plan.json` and chat
  route signs as Router-derived projection/cache only;
- Reviewer is the semantic decomposition quality gate for route planning.
  Every executable leaf must have one bounded accountable outcome, no `child_node_ids`,
  clear proof, clear dependency boundary, clear failure boundary, and no hidden
  child-ordering decision. Every parent/module must have children,
  parent/module acceptance intent, and a parent backward review path. Block if
  a parent/module can receive a worker packet directly, if a leaf carries
  children, or if a leaf is too broad for one bounded packet; this is the
  required under-decomposition check;
- broad stage labels such as research, design, implement, integrate, validate,
  or final report are not automatically bad, but if they hide multiple
  ordered deliverables, role handoffs, evidence families, or acceptance
  boundaries, block and require PM to turn that stage into a parent/module with
  ordered child leaves;
- every non-leaf entry has the local product/process/reviewer loop represented
  before child execution. Block if the route jumps straight from parent entry
  to worker dispatch without local modeling and PM decision;
- leaf promotion is allowed and required when PM discovers an apparent leaf is
  too broad at entry. Block if stale approvals remain valid after a promoted
  leaf becomes a parent/module, or if the promotion bypasses mandatory
  FlowGuard route simulation, PM absorption of that FlowGuard result, and
  Reviewer inspection of the PM absorption package. Also block if the promoted
  active scope is implemented as peer-appended split leaves rather than a
  replacement parent/module with children;
- Worker-local planning is required inside every bounded leaf. It may contain
  numbered substeps, bounded delegation, integration, verification, and repair.
  Block only when successful execution would require the Worker to create or
  reorder route nodes, define cross-node dependency boundaries, or change
  acceptance boundaries; those changes require PM to deepen the canonical route
  tree first;
- when blocking for under-decomposition, include one concrete PM-actionable
  split recommendation in `recommended_resolution`: name the broad leaf, the
  child leaves or parent/module shape you expect, and why the old leaf could
  not be completed by one bounded worker packet. PM owns the repaired route;
  you are not the route author;
- the route does not disguise a planning/root/parent node-entry gap as a
  repair node before any executable child work or reviewed work evidence
  exists. In that situation, require route replanning, ordinary node expansion,
  or parent splitting instead;
- any capability expansion was reviewed in product-fit order before process
  route approval. Block if the route depends on new product behavior that was
  only justified by a process mutation;
- the route passes an over-decomposition check. Extra nodes that do not add evidence,
  role authority, real parallelism, failure isolation, recovery boundary, or a
  user-visible milestone should be merged, waived with reason, or treated as a
  nonblocking PM suggestion depending on risk;
- every hard low-quality-success risk from product architecture or the root
  contract is owned by an existing route node when possible, with proof of
  depth named. Block if a hard risk is unowned. Treat a new risk-only node as
  route bloat unless PM shows distinct evidence, role authority, failure
  isolation, recovery boundary, or user-visible milestone value that an
  existing node could not provide;
- every active `acceptance_item_id` from the accepted registry is assigned to
  one or more route nodes, and every user-sourced item and PM high-standard
  item has an explicit reviewer or FlowGuard gate. Block route pass if an item
  is missing, orphaned, assigned only to a vague parent with no executable
  proof path, or silently downgraded into prose;
- necessary convergence loops are present for the chosen profile, especially
  concept-to-implementation visual comparison, interaction validation, realtime
  state mapping, desktop integration, or release validation when those are
  root requirements or child-skill obligations;
- child-skill hard standards are compiled and projected into route nodes, work
  packets, reviewer/FlowGuard operator gates, and expected artifacts;
- required human inspection, repair, parent replay, and final-report duties are present;
- user hard requirements, frozen contract items, required child-skill gates,
  and selected-profile convergence duties are not downgraded into residual
  blindspots. Any such blindspot is a hard block, not a pass-with-note;
- route mutations, if present, list impacted requirements, stale evidence,
  superseded ids, and required model/check reruns before any affected evidence
  is reused;
- material or report handoff nodes name the producer, the required report
  contract, the downstream consumer, and the downstream authorized read path.
  Block if the route expects a later actor to infer required materials from
  summaries, stale files, chat history, or old repair packets instead of the
  current runtime handoff;
- public docs, final reports, release notes, demos, package docs, examples, or
  similar summary artifacts are not special-cased, but they often consume other
  node outputs. Block only when the route orders such a consumer before the
  unfinished producer it needs, or when its current node boundary cannot be
  reviewed from already available material;
- after a route mutation, same-family obsolete repair blockers must no longer
  be treated as current work. Block if accepted, superseded, or stale repair
  packets can still appear as current final-preflight blockers while unrelated
  blockers are not intentionally changed;
- FlowPilot can tell Controller the next role at each major boundary.

Use the current review result contract from the human-like reviewer core card.
Route pass is invalid if the review only repeats the PM checklist, lacks
failure hypotheses, lacks task-specific challenge actions, or downgrades hard
requirements into nonblocking notes.

For route standard or complexity disagreements, report the evidence and
alternative for PM decision instead of becoming a second route owner. Block
only when the route misses a hard requirement, required proof, role boundary,
selected child-skill obligation, or other non-waivable gate.

Return pass or block in the private report body. Keep the body out of
Controller chat.
