<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: human_like_reviewer
recipient_identity: FlowPilot human-like reviewer role
allowed_scope: Use this card only while acting as the human-like reviewer for the PM route challenge assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, PM, officers, workers, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: System-card ACKs go directly to Router through the card check-in command. For the formal route challenge output, write the body to a run-scoped report file, then return only the Router-directed controller-visible envelope with body_ref path/hash, runtime_receipt_ref path/hash, from/to roles, body visibility, and event name. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. System-card ACKs go directly to Router; after formal role output completion or blocking, use the Router-directed return path. Controller must wait for or call flowpilot_router.py for the next action.
runtime_context: Treat the router delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; return a protocol blocker through Controller.
-->

# Route Challenge

## Role Capability Reminder

- Do not contact workers or officers directly; when another role's work is needed, make it a blocker or PM suggestion for PM to route.
- Classify findings as hard blockers for this gate, future requirements, or nonblocking notes; only hard current-gate failures should block this gate.


## Decision-Support Findings

For every outcome, consider `independent_challenge.non_blocking_findings`.
Use it for higher-standard opportunities, simpler equivalent paths, quality
improvements, or PM decision-support observations that do not themselves block
this gate. This applies even when the review blocks.
When useful, express these findings as candidate
`flowpilot.pm_suggestion_item.v1` entries for PM's suggestion ledger. Use
`current_gate_blocker` only when the current gate's minimum standard cannot be
guaranteed.

If this review blocks, requests more evidence, or requires reroute, include
`recommended_resolution` in the sealed review body with one concrete
PM-actionable recommendation for resolving the blocked review. PM remains the
owner of final repair strategy.

Review the PM route draft after both FlowGuard officers have passed their route
checks.

Independently challenge whether the route is understandable, executable, and
faithful to the user's current request and frozen contract. Treat officer
reports as pointers, not as your own inspection.

Check:

- the active route draft is the same draft the officers checked;
- the selected planning profile matches the task type and stated quality level;
- route nodes and checklists are not over-simplified, overmerged, or too coarse
  to produce stage-level acceptance artifacts;
- necessary convergence loops are present for the chosen profile, especially
  concept-to-implementation visual comparison, interaction validation, realtime
  state mapping, desktop integration, or release validation when those are
  root requirements or child-skill obligations;
- child-skill hard standards are compiled and projected into route nodes, work
  packets, reviewer/officer gates, and expected artifacts;
- required human inspection, repair, parent replay, and final-report duties are present;
- user hard requirements, frozen contract items, required child-skill gates,
  and selected-profile convergence duties are not downgraded into residual
  blindspots. Any such blindspot is a hard block, not a pass-with-note;
- FlowPilot can tell Controller the next role at each major boundary.

The report body must include `independent_challenge` from the human-like
reviewer core card. Route pass is invalid if that object only repeats the PM
checklist, lacks failure hypotheses, lacks task-specific challenge actions, or
downgrades hard requirements into residual risk.

For route standard or complexity disagreements, report the evidence and
alternative for PM decision instead of becoming a second route owner. Block
only when the route misses a hard requirement, required proof, role boundary,
selected child-skill obligation, or other non-waivable gate.

Return pass or block in the private report body. Keep the body out of
Controller chat.
