<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: System-card ACKs go directly to Router through the card check-in command; this is the router-directed return path for card ACKs. Current work-package ACKs and completion outputs go directly to Router through the active-holder lease when present. For formal role outputs, write the body only to a run-scoped packet, result, report, or decision file, then submit it with `flowpilot_runtime.py submit-output-to-router` so Router records the event and later exposes only controller-visible envelope metadata with status, paths, and hashes. If an output contract has a fixed Router event, a local receipt or `submit-output` record is only local storage and must not be treated as wait completion until `submit-output-to-router` records the Router event. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
post_ack: ACK is receipt only; ACK is not completion. This is a work item when it asks for an output, report, decision, result, or blocker. After work-card ACK, do not stop or wait for another prompt; immediately continue the work assigned by this card and submit the formal output or blocker through the Router-directed runtime path. The task remains unfinished until Router receives that output or blocker.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. System-card ACKs, current work-package outputs, and formal role-output submissions go directly through the current runtime commands. Controller must follow the `flowpilot_new.py` lifecycle guard and foreground duty; old `flowpilot_router.py` commands are old-run diagnostics or explicit unsupported-run repair tools only.
runtime_context: Treat the runtime delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; submit a protocol blocker through the Router-directed runtime path.
-->
# PM Child Skill Gate Manifest Phase

## Role Capability Reminder

- Formal work products must live in run-scoped files or project artifacts. Handoff messages point to artifacts with paths/hashes, changed paths when applicable, output contract, inspection notes, and PM Suggestion Items; the message body is not the sole work product.
- PM may directly disposition suggestions when evidence is sufficient. Consultation is optional, not a mandatory step for every suggestion.
- If PM lacks basis, or the suggestion may affect route, product target, acceptance, process safety, replay, repair return path, or risk boundary, PM may request bounded consultation through an allowed role-work request, then must record a final PM disposition after reading the advice artifact.
- If a PM-owned decision still lacks evidence, modeling, research, review, or implementation support, register a bounded `pm_registers_role_work_request` only when the router's current `allowed_external_events` includes that event; otherwise record the limitation or blocker instead of emitting it.
- Treat the router's current `allowed_external_events` as the active authority for what this card may return.
- For a blocked PM-owned decision, choose the smallest valid path among repair, sender reissue, route mutation, evidence quarantine, or user stop; do not skip required recheck.
- Put reviewer, worker, and FlowGuard operator advice that needs PM disposition into the PM suggestion/blocker ledger instead of leaving it only in prose.
- For non-trivial skill-standard, role-skill, model-family, validation, or gate-projection judgement, cite a FlowGuard Work Order and FlowGuard Report with `flowguard_work_order_id`, `flowguard_report_id`, `flowguard_report_freshness`, and PM acceptance, or record a scoped `flowguard_not_required_reason`.


Extract the initial gate manifest for PM-selected ordinary child skills only
after PM has accepted the current product model family. FlowGuard itself is
already the required run foundation from the startup capability snapshot and
must not be reclassified here as an optional ordinary child skill.
FlowGuard satellite use belongs in `role_skill_use_bindings` and FlowGuard
Work Order / FlowGuard Report references. The manifest may project ordinary
child-skill standards into FlowGuard model families, but it cannot replace a
missing Product or FlowGuard operator report.

Write `.flowpilot/runs/<run-id>/child_skill_gate_manifest.json` with:

- source paths for the startup FlowGuard capability snapshot, Product Modeling
  Plan, FlowGuard operator product model-family report, and PM product model decision;
- selected skills and supported capabilities;
- whether each selected skill supports the deliverable, the FlowPilot process,
  or both;
- `role_skill_use_bindings` for every selected skill use that affects PM
  planning, route design, acceptance writing, worker execution, reviewer
  review, FlowGuard operator modeling, or validation. Each binding must name the
  `used_by_role`, `use_context`, source `SKILL.md` path, referenced paths,
  reason, evidence required, output or gate affected, and reviewer/check
  authority;
- references loaded now or deferred with reason;
- a `skill_standard_contracts` section for every selected or conditional skill.
  PM must extract the child skill's hard standards into structured entries:
  `MUST`, `DEFAULT`, `FORBID`, `VERIFY`, `LOOP`, `ARTIFACT`, and `WAIVER`.
  Cite source paths and distinguish default policy from user overrides;
- for every required standard, map it to route node ids, work packet slices,
  reviewer or FlowGuard operator gate ids, and expected artifact paths. A skill can be
  selected only after its standards have a route/work/review projection or a
  PM-owned waiver with reason and approver;
- required gates;
- required approver for each gate;
- controller self-approval forbidden;
- skipped child-skill steps with reason;
- role-skill evidence obligations for PM, reviewer, FlowGuard operator, or worker uses.
- `model_family_projection`: how each ordinary child skill standard maps to
  accepted product model families and later process model families.

Do not route from a child skill until the Reviewer check passes.
Do not use this manifest as a substitute for FlowGuard operator or Process
FlowGuard operator model-family coverage. A selected child skill can add standards,
evidence, gates, and role bindings, but it cannot close a missing product or
process FlowGuard model family.
Do not let a role self-attest selected skill use as complete without the
evidence named in the binding.
