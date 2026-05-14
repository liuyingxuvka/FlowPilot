<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: System-card ACKs go directly to Router through the card check-in command; this is the router-directed return path for card ACKs. Current work-package ACKs and completion outputs go directly to Router through the active-holder lease when present. For formal role outputs, write the body only to a run-scoped packet, result, report, or decision file, then submit it with `flowpilot_runtime.py submit-output-to-router` so Router records the event and later exposes only controller-visible envelope metadata with status, paths, and hashes. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
post_ack: ACK is receipt only; ACK is not completion. After work-card ACK, continue the work assigned by this card and submit the formal output or blocker through the Router-directed runtime path.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. System-card ACKs, current work-package outputs, and formal role-output submissions go directly to Router through their runtime commands. Controller must follow Router daemon status and the Controller action ledger; flowpilot_router.py next/run-until-wait are diagnostic or explicit repair tools only.
runtime_context: Treat the router delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; submit a protocol blocker through the Router-directed runtime path.
-->
# PM Product Architecture Phase

## Role Capability Reminder

- Formal work products must live in run-scoped files or project artifacts. Handoff messages point to artifacts with paths/hashes, changed paths when applicable, output contract, inspection notes, and PM Suggestion Items; the message body is not the sole work product.
- PM may directly disposition suggestions when evidence is sufficient. Consultation is optional, not a mandatory step for every suggestion.
- If PM lacks basis, or the suggestion may affect route, product target, acceptance, process safety, replay, repair return path, or risk boundary, PM may request bounded consultation through an allowed role-work request, then must record a final PM disposition after reading the advice artifact.
- If a PM-owned decision still lacks evidence, modeling, research, review, or implementation support, register a bounded `pm_registers_role_work_request` only when the router's current `allowed_external_events` includes that event; otherwise record the limitation or blocker instead of emitting it.
- Treat the router's current `allowed_external_events` as the active authority for what this card may return.
- For a blocked PM-owned decision, choose the smallest valid path among repair, sender reissue, route mutation, evidence quarantine, or user stop; do not skip required recheck.
- Put reviewer, worker, and officer advice that needs PM disposition into the PM suggestion/blocker ledger instead of leaving it only in prose.


Write `.flowpilot/runs/<run-id>/product_function_architecture.json` from
reviewed material only.

Also write or update a `flowpilot.self_interrogation_record.v1` with scope
`product_architecture`, then register it in
`.flowpilot/runs/<run-id>/self_interrogation_index.json`. Any hard or
current-gate finding from the product-architecture self-check must be
incorporated into the architecture, deferred to a named later node/gate,
entered into `pm_suggestion_ledger.jsonl`, rejected with reason, or waived with
authority before root contract freeze.

Include:

- user task map and target users;
- `requirement_trace`: assign stable `req-*` ids to important explicit user
  requirements, PM-added hard requirements, hard low-quality-success risks,
  proof obligations, and any external advisory material PM imports. External
  OpenSpec/OpenSpark/SparkKey-style files are only source material until PM
  imports them here; they never become route authority by themselves;
- final-user intent and product usefulness assumptions, including what would
  make the result feel incomplete, unusable, misleading, or below the user's
  real goal;
- product capability map;
- negative scope and explicit user prohibitions;
- semantic fidelity risks and forbidden downgrades;
- minimum sufficient complexity review;
- low-quality-success review: identify task-specific hard parts, tempting
  thin-success shortcuts, warning signs that the result merely looks complete,
  and proof of depth needed to show those hard parts were genuinely solved;
- highest achievable product target;
- higher-standard opportunities classified as hard requirement, current-scope
  improvement, future candidate, or rejected/deferred with reason;
- functional acceptance matrix;
- evidence and validation implications for the root contract.

Every user task, product capability, feature decision, missing-feature
decision, low-quality-success hard part, and functional acceptance row must
carry `source_requirement_ids` when it exists because of a user requirement,
PM-added hard risk, or imported advisory source. If an item has no supporting
requirement id, either put it in negative scope/deferred scope or record why it
is only PM decision-support.

Use Minimum Sufficient Complexity here. Every accepted capability, feature,
surface, and visible element must be tied to a user task, a hard acceptance
criterion, a verification need, or a real risk reduction. Put features or UI
elements with no such support into negative scope or defer them with a revisit
condition. If a simpler architecture can produce the same user-visible behavior
with the same proof strength, choose it and record the rejected extra
complexity.

The low-quality-success review is not a generic "avoid bad output" note. For
the user's actual task, name the hard parts that are easy to handle
superficially, the casual shortcuts a worker or PM might take, the evidence
that would be existence-only, and the proof of depth that would convince a
skeptical reviewer. Classify each item as hard current requirement,
current-scope improvement, future candidate, nonblocking note, or rejected with
reason. Hard low-quality risks must later be owned by existing route nodes when
possible; do not create new route nodes merely because a concern was named.

Do not draft or activate a route from this card. Product FlowGuard Officer must
turn this architecture into a concrete product behavior model, then PM must
explicitly accept that model before Reviewer challenge can run. If PM finds
that the model does not represent the intended product, rewrite the product
architecture or ask Product FlowGuard to rebuild the model before continuing.
