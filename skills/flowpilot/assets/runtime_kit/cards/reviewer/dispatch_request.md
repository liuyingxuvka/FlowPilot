<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: human_like_reviewer
recipient_identity: FlowPilot human-like reviewer role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: System-card ACKs go directly to Router through the card check-in command. For formal role outputs, write the body only to a run-scoped packet, result, report, or decision file, then return only the Router-directed controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. System-card ACKs go directly to Router; after formal role output completion or blocking, use the Router-directed return path. Controller must wait for or call flowpilot_router.py for the next action.
runtime_context: Treat the router delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; return a protocol blocker through Controller.
-->
# Reviewer Dispatch Request

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

Review whether the PM packet may be dispatched.

Check:

- current node and current phase match;
- for `material_scan` packets, this is pre-route material intake:
  `is_current_node=false` is expected, `packet_type` must be `material_scan`,
  and the run frontier/status must be in the material scan phase rather than a
  current route node;
- packet is bounded and addressed to the right role;
- packet envelope includes `output_contract`, the packet body repeats the same
  `Output Contract`, and the contract matches `to_role`, `packet_type`, node
  acceptance, required evidence, and reviewer block conditions;
- allowed reads/writes are explicit;
- forbidden actions prevent route, PM, reviewer, and Controller authority drift;
- Controller relay and ledger requirements are present;
- worker receives least necessary context only.

The dispatch report body must include `Contract Self-Check` against the source
packet `output_contract`; missing or failed contract checks block dispatch.
The report body must also include `independent_challenge` from the human-like
reviewer core card, including task-specific failure hypotheses for how this
packet could be too broad, under-specified, wrong-role, stale, or unverifiable.

Return `dispatch_allowed` or a concrete blocker. If dispatch is blocked, return
the file-backed report through event `reviewer_blocks_material_scan_dispatch`;
do not invent a new event name.
