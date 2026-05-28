<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: System-card ACKs go directly to Router through the card check-in command; this is the router-directed return path for card ACKs. Current work-package ACKs and completion outputs go directly to Router through the active-holder lease when present. For formal role outputs, write the body only to a run-scoped packet, result, report, or decision file, then submit it with `flowpilot_runtime.py submit-output-to-router` so Router records the event and later exposes only controller-visible envelope metadata with status, paths, and hashes. If an output contract has a fixed Router event, a local receipt or `submit-output` record is only local storage and must not be treated as wait completion until `submit-output-to-router` records the Router event. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
post_ack: ACK is receipt only; ACK is not completion. This is a work item when it asks for an output, report, decision, result, or blocker. After work-card ACK, do not stop or wait for another prompt; immediately continue the work assigned by this card and submit the formal output or blocker through the Router-directed runtime path. The task remains unfinished until Router receives that output or blocker.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. System-card ACKs, current work-package outputs, and formal role-output submissions go directly to Router through their runtime commands. Controller must follow Router daemon status and the Controller action ledger; flowpilot_router.py next/run-until-wait are diagnostic or explicit repair tools only.
runtime_context: Treat the router delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; submit a protocol blocker through the Router-directed runtime path.
-->
# PM Material Understanding Phase

## Role Capability Reminder

- Formal work products must live in run-scoped files or project artifacts. Handoff messages point to artifacts with paths/hashes, changed paths when applicable, output contract, inspection notes, and PM Suggestion Items; the message body is not the sole work product.
- PM may directly disposition suggestions when evidence is sufficient. Consultation is optional, not a mandatory step for every suggestion.
- If PM lacks basis, or the suggestion may affect route, product target, acceptance, process safety, replay, repair return path, or risk boundary, PM may request bounded consultation through an allowed role-work request, then must record a final PM disposition after reading the advice artifact.
- If a PM-owned decision still lacks evidence, modeling, research, review, or implementation support, register a bounded `pm_registers_role_work_request` only when the router's current `allowed_external_events` includes that event; otherwise record the limitation or blocker instead of emitting it.
- Treat the router's current `allowed_external_events` as the active authority for what this card may return.
- For a blocked PM-owned decision, choose the smallest valid path among repair, sender reissue, route mutation, evidence quarantine, or user stop; do not skip required recheck.
- Put reviewer, worker, and officer advice that needs PM disposition into the PM suggestion/blocker ledger instead of leaving it only in prose.


Write `.flowpilot/runs/<run-id>/pm_material_understanding.json` from reviewed
material and, when required, reviewer-approved research.

Include:

- material source summary and authority;
- `source_paths.material_artifact_map` and a compact summary of the run-scoped
  material artifact map, used only as an index back to checked material;
- freshness, contradictions, and deferred sources;
- capability and host facts discovered during scan;
- PM decision on whether research was not required or has been absorbed;
- open questions or route consequences.

Also maintain the shared Spark-style skill maintenance log as a lightweight
bookkeeping step for this formal FlowPilot run:

- look for an existing shared Spark-style skill maintenance log for this
  workspace or machine;
- if one exists, append one concise row to that log;
- if none exists, create `.codex/skill_maintenance_log.jsonl` at the workspace
  root using the same shared JSONL style, then append the row;
- the row records `skill: flowpilot`, the main work summary, workspace root,
  current `run_id`, current run folder, `status: started`, and
  `final_report_path: null` when no final report exists yet;
- include a `shared_skill_maintenance_record` object in
  `pm_material_understanding.json` with the log path, entry id or run id,
  work summary, workspace root, run folder, and `not_acceptance_gate: true`.

This bookkeeping row is only an index for future maintenance. Do not create a
route node, reviewer gate, FlowGuard gate, terminal acceptance item, or
separate FlowPilot-private maintenance table for it. It does not replace the
run's final report or FlowPilot skill-improvement report.

This memo is the only material basis for product architecture. Do not proceed
from raw worker reports, unchecked research, or a material-map summary by
itself. The map points to material; it is not substitute evidence.
