<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: System-card ACKs go through the current runtime card check-in command; this is the current-runtime return path for card ACKs. Current work-package ACKs and completion outputs go through the assigned current packet lease when present. For formal role outputs, write the body only to a run-scoped packet, result, report, decision, or blocker file, then submit it with `flowpilot_new.py submit-result --lease-id <lease-id> --packet-id <packet-id> --body-file <sealed_result_body_file>` so the current runtime ledger records the event and later exposes only controller-visible envelope metadata with status, paths, and hashes. A local file write is only local storage and must not be treated as wait completion until the current runtime records the packet result. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
post_ack: ACK is receipt only; ACK is not completion. This is a work item when it asks for an output, report, decision, result, or blocker. After work-card ACK, do not stop or wait for another prompt; immediately continue the assigned work and submit the formal output or blocker through the current runtime path. The task remains unfinished until the current runtime receives that output or blocker.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. System-card ACKs, current work-package outputs, and formal role-output submissions go directly through the current runtime commands. Controller must follow the `flowpilot_new.py` lifecycle guard and foreground duty; no unsupported command text, stale runtime state, chat history, or historical artifact authorizes current-run progress.
runtime_context: Treat the runtime delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; submit a protocol blocker through the current runtime path.
-->
# PM Evidence Quality Package Phase

## Role Capability Reminder

- Formal work products must live in run-scoped files or project artifacts. Handoff messages point to artifacts with paths/hashes, changed paths when applicable, output contract, inspection notes, and PM Suggestion Items; the message body is not the sole work product.
- PM may directly disposition suggestions when evidence is sufficient. Consultation is optional, not a mandatory step for every suggestion.
- If PM lacks basis, or the suggestion may affect route, product target, acceptance, process safety, replay, repair return path, or risk boundary, PM may request bounded consultation through an allowed role-work request, then must record a final PM disposition after reading the advice artifact.
- If a PM-owned decision still lacks evidence, modeling, research, review, or implementation support, register a bounded `pm_registers_role_work_request` only when the router's current `allowed_external_events` includes that event; otherwise record the limitation or blocker instead of emitting it.
- Treat the router's current `allowed_external_events` as the active authority for what this card may return.
- Put reviewer, worker, and FlowGuard operator advice that needs PM disposition into the PM suggestion/blocker ledger instead of leaving it only in prose.


Build the current-run evidence quality package before final ledger work.
Read the latest route-memory prior path context first so completed nodes,
superseded nodes, stale evidence, route mutations, and prior experiments are
represented before final ledger work starts.

Write:

- `evidence/evidence_ledger.json`;
- `generated_resource_ledger.json`;
- `quality/quality_package.json`.
- `quality/final_artifact_hygiene_inventory.json` when the run has any
  delivered artifact, code/document/UI/model/test/process output, generated
  resource, or terminal ledger surface that a final user, reader, operator, or
  maintainer will inherit.

Every current evidence item must be concrete, non-stale, and tied to the
current route/frontier. Generated resources, screenshots, route diagrams,
concept images, and visual assets must have terminal disposition. Old visuals
or assets may be cited as historical context only; they cannot close a current
UI or quality gate.
For user-facing claims, evidence must also map back to the accepted
source-intent acceptance rows. A file, report, screenshot, command log, or
ledger row may prove existence, but it does not prove that the delivered
artifact preserved the user's concrete object, action, quality floor, quantity,
constraint, or prohibition. Record missing source-intent evidence as an
evidence gap for PM disposition before final ledger work. Do not accept a
generic evidence summary as a substitute for this mapping.

For every FlowGuard-backed gate in scope, include a model-test alignment row:
`model_obligations`, `ordinary_test_evidence`, `missing_test_kinds`,
`conformance_boundary`, `residual_blindspots`, and PM's
current PM evidence disposition. Ordinary test evidence must be current,
passing, and bound to explicit FlowGuard obligations before it can close model
coverage. Missing, stale, skipped, failed, not-run, progress-only, or
undispositioned test rows are evidence gaps, not residual notes. If a report
cites long/background tests, record
`background_artifact_completion` with log root, stdout, stderr, combined, exit,
and meta paths, exit code, latest update time, completion status, and valid
proof reuse. Progress lines are liveness evidence only.
For terminal completion readiness, attach or cite
`flowguard_terminal_coverage_pack` evidence. It must point to the current
terminal FlowGuard coverage report, fresh coverage matrix, model-test
alignment status, blocker disposition, PM suggestion disposition, and PM
acceptance evidence. Progress-only FlowGuard logs are liveness evidence only,
not terminal coverage proof.

Apply Minimum Sufficient Complexity here as evidence hygiene. Identify
artifacts, resources, route diagrams, reports, or evidence branches that no
longer change product trust, verification strength, or final delivery. They
must be consumed, superseded, quarantined, or discarded with reason rather than
left as unresolved complexity for the final ledger. Unnecessary evidence
surfaces are not quality; they are maintenance cost unless they prove a current
gate.

Also include structure debt dispositions as evidence hygiene. Patch stacks,
fallback-like paths, compatibility branches, duplicate adapters, stale
generated artifacts, non-current evidence, and intentionally retained
maintenance layers must be marked
removed, rejected, preserved as negative rejection evidence, retained as owned
current-runtime recovery, retained as an owned maintenance layer, or blocked.
Retained current-runtime or maintenance surfaces must cite owner, scope,
validation evidence, and sunset or next-disposition criteria. Block final
ledger work while any structure debt disposition is missing or unresolved.

If the route includes UI or visual work, include screenshot paths and visual
review notes. If it does not, mark UI/visual evidence as not applicable.

Also inventory final artifact hygiene. For each applicable artifact family,
record the checked surface, whether cleanup is required, whether it is current
goal required, clean-delivery required, PM decision support, or a future
contract candidate, and what evidence would close it. Examples include code
module split or readability, tests that must be added, model/test alignment,
document revision cleanup, citation/table consistency, UI polish, stale
generated artifact disposal, and process-ledger cleanup. Do not invent cleanup
work for inapplicable families; explicitly mark them not applicable.
