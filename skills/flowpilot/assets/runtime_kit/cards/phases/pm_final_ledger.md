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
# PM Final Ledger Phase

## Role Capability Reminder

- Formal work products must live in run-scoped files or project artifacts. Handoff messages point to artifacts with paths/hashes, changed paths when applicable, output contract, inspection notes, and PM Suggestion Items; the message body is not the sole work product.
- PM may directly disposition suggestions when evidence is sufficient. Consultation is optional, not a mandatory step for every suggestion.
- If PM lacks basis, or the suggestion may affect route, product target, acceptance, process safety, replay, repair return path, or risk boundary, PM may request bounded consultation through an allowed role-work request, then must record a final PM disposition after reading the advice artifact.
- If a PM-owned decision still lacks evidence, modeling, research, review, or implementation support, register a bounded `pm_registers_role_work_request` only when the router's current `allowed_external_events` includes that event; otherwise record the limitation or blocker instead of emitting it.
- Treat the router's current `allowed_external_events` as the active authority for what this card may return.
- Put reviewer, worker, and officer advice that needs PM disposition into the PM suggestion/blocker ledger instead of leaving it only in prose.


Build the final route-wide gate ledger from the current route, not the initial
route.
Before building it, read the latest route-memory prior path context and use it
to make sure every completed, superseded, stale, repaired, blocked, and
experiment-influenced path is represented.

Write `.flowpilot/runs/<run-id>/final_route_wide_gate_ledger.json` as the
source of truth for completion.

Resolve:

- effective and superseded nodes;
- every major node, parent/module, child subtree, promoted former leaf, repair
  node, and supplemental node in the current route. Before project completion,
  walk backward over the whole route and prove that no major node or subtree
  was skipped;
- final-user intent and delivered-product usefulness claims, including the
  evidence that proves each current user-facing claim instead of merely proving
  that an artifact exists;
- child-skill and review gates;
- product/process FlowGuard gates;
- minimum sufficient complexity dispositions for route nodes, skills, and
  artifacts that were considered, superseded, deferred, or discarded;
- generated-resource lineage;
- stale, invalid, missing, waived, blocked, or superseded evidence;
- zero unresolved count;
- zero unresolved residual risks.

If the final backward walk finds an omitted major node, omitted subtree,
unclosed bug class, or stale evidence class, first decide whether the
Product/Process FlowGuard model missed the class. When it did, update the
model, search the same class across the whole route, add supplemental or repair
nodes, rerun stale gates, rebuild this ledger, and only then request terminal
Reviewer replay.

Return `prior_path_context_review` and cite both route-memory files. If any
repair or route mutation happened after that context was refreshed, block and
ask Controller to refresh route memory before building the ledger.

Then build `terminal_human_backward_replay_map.json` as ordered segments from
delivered output to root, parents, leaves, child-skill gates, repairs, and
generated resources. Request terminal backward replay from Reviewer; any repair
or stale evidence found there requires ledger rebuild before closure.
The replay map must start from the delivered product or final output as a
final user, reader, operator, maintainer, or recipient would experience it, and
then walk backward to route evidence and root intent.

Do not let unused complexity survive as a completion note. Extra nodes, skills,
resources, reports, or validation branches must either prove a current gate,
be explicitly superseded, be quarantined, or be discarded with a concrete
reason before unresolved count can be zero.
