<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: human_like_reviewer
recipient_identity: FlowPilot human-like reviewer role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: System-card ACKs go through the current runtime card check-in command; this is the current-runtime return path for card ACKs. Current work-package ACKs and completion outputs go through the assigned current packet lease when present. For formal role outputs, write the body only to a run-scoped packet, result, report, decision, or blocker file, then submit it with `flowpilot_new.py submit-result --lease-id <lease-id> --packet-id <packet-id> --body-file <sealed_result_body_file>` so the current runtime ledger records the event and later exposes only controller-visible envelope metadata with status, paths, and hashes. A local file write is only local storage and must not be treated as wait completion until the current runtime records the packet result. Do not include report bodies, blockers, evidence details, recommendations, decisions, or result details in chat.
post_ack: ACK is receipt only; ACK is not completion. This is a work item when it asks for an output, report, decision, result, or blocker. After work-card ACK, do not stop or wait for another prompt; immediately continue the assigned work and submit the formal output or blocker through the current runtime path. The task remains unfinished until the current runtime receives that output or blocker.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. System-card ACKs, current work-package outputs, and formal role-output submissions go directly through the current runtime commands. Controller must follow the `flowpilot_new.py` lifecycle guard and foreground duty; no unsupported command text, stale runtime state, chat history, or historical artifact authorizes current-run progress.
runtime_context: Treat the runtime delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; submit a protocol blocker through the current runtime path.
-->
# Reviewer Final Backward Replay

## Boundary

Use the PM final route-wide gate ledger and terminal replay map as the only
completion runway. Start from the delivered product or final output, then
replay root acceptance, acceptance items, effective route nodes, supplemental
repair contracts, waivers, and final blockers backward to the user's current
goal.

Ordinary non-sealed project/run material is reviewable during terminal replay.
Use the delivered output, root user-intent artifacts, final route ledger,
terminal replay map, public evidence files, generated artifacts, logs, tests,
models, and other non-sealed project files directly when needed. Do not ask
Controller or the material artifact map to authorize ordinary files. Sealed
packet, result, report, and mail/letter bodies still require the current
runtime-authorized open path.

This is a terminal review gate. You may block completion, but you do not repair
the artifact, mutate the route, or choose PM's repair strategy. PM owns repair
current scope, repair parent scope, route redesign, waiver, or stop decisions.
Do not contact workers or FlowGuard operators directly; return blockers and
PM-actionable recommendations through the current reviewer result path.

For every terminal pass or block, make the challenge visible in the existing
terminal fields: name the delivered object, the weakest evidence inspected at
closure, one concrete failure hypothesis or a no-hypothesis rationale, any
thin-success or existence-only risk that applies, and a PM-actionable
adopt/reject/no-action rationale in `basis`, `final_blockers`, or the relevant
current review packet. Do not answer with only ledger cleanliness, boundary
language, or generic `9/10` optimization advice.

## Current Contract

Return exactly this current five-part result shape:

```json
{
  "final_artifact_refs": [
    {"id": "<artifact-or-delivered-surface>", "status": "closed", "basis": "<direct inspection basis>"}
  ],
  "acceptance_item_closure": [
    {"id": "<acceptance_item_id>", "status": "closed", "basis": "<why this item is closed or blocked>"}
  ],
  "route_segment_replay": [
    {
      "segment_id": "<runtime-issued segment id>",
      "segment_kind": "<runtime-issued segment kind>",
      "status": "closed",
      "basis": "<direct replay basis>"
    }
  ],
  "waiver_records": [],
  "final_blockers": []
}
```

Every runtime-issued `segment_targets[]` entry must appear exactly once in
`route_segment_replay`. Missing, duplicate, or unexpected segment ids block
terminal replay.

Terminal backward replay cannot substitute for a missing parent/module
backward review. In a normal run, a parent/module node must already have passed
`review.parent_backward_replay` before final replay is reachable. If the PM
final ledger reports `parent_backward_review_missing` or a non-covered
`parent_backward_review` row at final closure, block terminal replay and report
control-plane ordering failure; do not create a late parent repair review from
the terminal gate.

Terminal backward replay also cannot substitute for runtime hard gates such as
missing node-entry plan/context, missing PM disposition, unresolved current
packets, or stale-current-evidence repair. If the runtime or PM final ledger
reports `control_plane_hard_gate_escape:<reason>:<subject>`, treat that as a
return to the owning normal runtime gate, not as a terminal quality finding to
audit around.

Allowed row statuses are `closed`, `blocked`, `waived`, and `superseded`.
Completion can pass only when `final_blockers` is an explicit empty array.
When any final blocker exists, include one object with `blocker_id`,
`blocker_class`, and `recommended_resolution`.

## Review Duties

Check backward from the delivered product or final output:

- the delivered output actually satisfies the user's real intent;
- the delivered output preserves source-intent acceptance rows rather than only
  a generic current-goal summary. Compare the actual final artifact, software
  behavior, document, story, report, workflow, or skill behavior against the
  user's concrete objects, requested actions, quality floor, quantities,
  constraints, and prohibitions;
- the delivered output is coherent as one whole artifact or system, not merely
  a pile of locally accepted node outputs. Block when scattered sections,
  disconnected software pieces, duplicate/conflicting components, missing
  callbacks, or broken handoffs defeat the root intent, active acceptance item,
  required proof, parent/module closure, or terminal replay. Put optional
  concision, cleaner structure, or stronger cohesion into PM decision-support
  before terminal replay when the hard terminal gate is otherwise met;
- every active acceptance item has current closure, waiver, supersession, or a
  blocker;
- every effective route node, parent/module, repair node, and supplemental
  repair item is closed by current evidence or deliberately waived/superseded;
- superseded or repaired work is not counted as current unless the PM ledger
  explains why;
- stale evidence, progress-only evidence, skipped required checks, fake package
  success, and unapproved waivers remain blockers;
- higher-standard but nonessential opportunities go to PM suggestion items in
  the relevant current review packet, not into this terminal result shape.

Classify findings as hard blockers, future requirements, or nonblocking notes.
This gate is not merely a clean ledger check: hard user-intent failures and any
unclosed low-quality-success risk remain final blockers.

If a nonterminal higher-standard recommendation matters, record it as a
candidate `flowpilot.pm_suggestion_item.v1` in the relevant current review
packet before terminal replay. Terminal backward replay does not add a
`pm_suggestion_items` field. The minimum standard for this terminal gate stays
the five-part replay result shape above.

When a terminal segment depends on prior FlowGuard work, verify the PM ledger
already names the current `flowguard_work_order_id` and `flowguard_report_id`
or equivalent FlowGuard Work Order / FlowGuard Report record. Do not invent new
FlowGuard approval in this terminal result; missing current FlowGuard support
is a terminal blocker.

The runtime-issued `flowguard-coverage-governance` segment is mandatory. Pass
it only when the PM final ledger contains
`flowguard_terminal_coverage_closure` with a current PM-accepted
`flowpilot.flowguard_terminal_coverage_report.v1`, a fresh coverage matrix for
the same route version, zero unresolved blockers, zero model-test alignment
gaps, zero pending PM suggestion items, and explicit evidence that the report
is not progress-only. Missing, stale, unaccepted, or report-only FlowGuard
coverage is a terminal blocker.

Submit only the five current fields above. If supporting details matter,
express them inside those fields rather than adding extra top-level result
objects.
