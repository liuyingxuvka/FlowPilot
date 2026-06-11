<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: flowguard_operator
recipient_identity: FlowPilot FlowGuard operator role
allowed_scope: Use this card only while acting as the FlowGuard operator for the PM route draft check assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, PM, reviewer, worker, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: System-card ACKs go through the current runtime card check-in command; this is the current-runtime return path for card ACKs. Current work-package ACKs and completion outputs go through the assigned current packet lease when present. For formal role outputs, write the body only to a run-scoped packet, result, report, decision, or blocker file, then submit it with `flowpilot_new.py submit-result --lease-id <lease-id> --packet-id <packet-id> --body <sealed_result_summary>` so the current runtime ledger records the event and later exposes only controller-visible envelope metadata with status, paths, and hashes. A local file write is only local storage and must not be treated as wait completion until the current runtime records the packet result. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
post_ack: ACK is receipt only; ACK is not completion. This is a work item when it asks for an output, report, decision, result, or blocker. After work-card ACK, do not stop or wait for another prompt; immediately continue the assigned work and submit the formal output or blocker through the current runtime path. The task remains unfinished until the current runtime receives that output or blocker.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. System-card ACKs, current work-package outputs, and formal role-output submissions go directly through the current runtime commands. Controller must follow the `flowpilot_new.py` lifecycle guard and foreground duty; no unsupported command text, stale runtime state, chat history, or historical artifact authorizes current-run progress.
runtime_context: Treat the runtime delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; submit a protocol blocker through the current runtime path.
-->

# Process Route Model

## Role Capability Reminder

- When more evidence, worker work, reviewer review, or PM choice is needed, return a structured blocker or PM suggestion for PM to route.
- Do not approve routes or make PM decisions; your report is model evidence and repair/risk advice for PM.
- This card's model output is a FlowGuard Report. Cite `flowguard_work_order_id`, `flowguard_report_id`, `flowguard_route_used`, `flowguard_report_freshness`, skipped checks, progress-only evidence status, and PM decision impact.


Submit the process route model for the PM route draft as the FlowGuard operator process-model
FlowGuard operator. This gate's output is the serial process route model that PM must accept before
Reviewer route challenge uses it.

Before modeling, read:

- `.flowpilot/runs/<run-id>/flowguard/capability_snapshot.json`;
- `.flowpilot/runs/<run-id>/flowguard/product_modeling_plan.json`;
- `.flowpilot/runs/<run-id>/flowguard/product_behavior_model_pm_decision.json`;
- `.flowpilot/runs/<run-id>/child_skill_gate_manifest.json`;
- `.flowpilot/runs/<run-id>/flowguard/process_modeling_plan.json`;
- the PM route draft.

Treat the Process Modeling Plan as the PM-owned scope contract for your model
family. Build separate child models when the plan names distinct route
hierarchy, serial execution, child-skill conformance, validation/evidence,
repair/mutation, or terminal closure risk families. If you merge or skip a
family, record the PM plan row and reason; if the plan is missing or does not
consume the accepted product model family and child-skill manifest, block for
PM repair.

Model only the process shape and route viability against the product behavior
model:

- route draft was written by PM after the current prior-path context;
- for a PM structural route change, the current `route_plan` is the simulation
  subject. Simulate that route plan's node traversal, work dispatch path,
  validation/check path, failure/blocker path, repair return path, stale
  evidence handling, and closure path. Do not model an unrelated route or treat
  the operator report as the route mutation commit;
- route nodes map to the FlowGuard operator's product behavior model and
  can reach the modeled completion state;
- the canonical process model is serial: every effective root, parent/module,
  child, leaf, and repair segment has a definite ordered predecessor/successor
  path, and all required nodes are reachable before completion;
- no product-model state, failure/recovery path, or completion evidence is left
  only partially covered by the route;
- route nodes preserve the frozen root contract and child-skill gate manifest;
- every ordinary child-skill standard that affects route design, worker
  execution, FlowGuard operator modeling, review, or validation is represented in the
  process model family or explicitly deferred/waived by PM;
- the full route tree may have arbitrary depth when needed, and the visible
  user route projection is explicitly shallow instead of being the execution
  source of truth;
- PM authored one canonical executable route tree. `display_plan.json` or any
  chat route sign is only a Router-derived projection/cache and must not be
  treated as a second route plan;
- Router-visible traversal can distinguish parent/module nodes from
  dispatchable leaves, dispatch only leaf/repair nodes with no `child_node_ids`
  and with enough existing acceptance criteria, outputs, and checks to be
  worker-ready, enter every unresolved child before a parent/module worker
  dispatch could occur, and trigger parent backward review after all child
  nodes complete, implemented as parent backward replay. Do not require a large
  new route-node field mesh to make this judgement;
- each non-leaf node has a local entry loop before child execution: PM local
  product goal, FlowGuard operator local product model, PM decision, Reviewer product
  challenge, FlowGuard operator serial child-route model, PM decision, Reviewer route
  challenge;
- each leaf is small enough for one bounded worker packet. If a leaf hides
  multiple ordered work packages, require promotion to parent/module and deeper
  child decomposition before dispatch;
- simulate at least one route traversal from first executable node through
  final closure: parent/module entry, child node sequence, child skill
  projection, parent backward replay, PM parent disposition, and terminal
  closure gate. Block if the route can only pass by dispatching a parent/module
  or by letting a Worker replan a broad leaf;
- explicitly check worker-decision leakage. If the route only works because a
  Worker must invent subtasks, choose child order, define dependency
  boundaries, or decide acceptance boundaries, return repair-required process
  evidence and recommend PM route deepening before any Worker dispatch;
- parent completion and final completion include backward coverage review, and
  any omission first checks whether the process model missed a class of work,
  upgrades the model when needed, searches same-class omissions, adds
  supplemental nodes, and reruns stale gates;
- root or parent/module node-entry gaps before executable child work are handled
  as route replanning or ordinary node expansion, not as repair-node creation;
- if the draft adds or changes capability, the FlowGuard operator product-capability fit
  check happened before this process check, and the process route uses that
  product-approved capability shape;
- node ordering has no missing reviewer, FlowGuard operator, or worker authority gate;
- repair or route-mutation branches define where they rejoin the mainline and
  which product/process checks must rerun;
- route mutation defines the stale subtree/frontier reset policy so a repaired
  child cannot accidentally advance the old parent/module path;
- route structure avoids obvious no-op detours or complexity that does not add
  product coverage, evidence strength, role authority, or failure isolation;
- route mutation, stale evidence, frontier rewrite, parent replay, and terminal closure paths remain represented;
- Controller remains relay-only and never becomes a route decision maker.

Return `process_model_family_coverage`: every PM-planned process family, model
file, covered scenarios/invariants/hazards/contracts, child-skill conformance
mapping, and merge/skip disposition. Manifest-only coverage is not enough.

Return pass or block in the private report body. If blocking, name the process
failure and the route artifact path, but keep the body out of Controller chat.

Router hard gate fields:

- To pass, include `process_viability_verdict: "pass"`,
  `product_behavior_model_checked: true`, `route_can_reach_product_model:
  true`, `repair_return_policy_checked: true`,
  `serial_execution_model_checked: true`,
  `all_effective_nodes_reachable_in_order: true`, and
  `recursive_child_routes_serialized: true`, then return event
  `flowguard_operator_submits_process_route_model`.
- If the route needs PM repair, return event
  `flowguard_operator_requests_process_route_model_repair` with
  `process_viability_verdict: "repair_required"` and a concrete
  `recommended_resolution`.
- If the route cannot safely proceed without a larger PM/user decision, return
  event `flowguard_operator_blocks_process_route_model` with
  `process_viability_verdict: "blocked"` and the blocking reason.
- Do not approve a repair or mutation path unless the report checks where it
  rejoins the mainline and which product/process checks must rerun.
