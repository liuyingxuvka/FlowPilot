<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: human_like_reviewer
recipient_identity: FlowPilot human-like reviewer role
allowed_scope: Use this card only while acting as the human-like reviewer for the PM implementation-intent challenge assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, PM, FlowGuard operators, workers, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: System-card ACKs go through the current runtime card check-in command; this is the current-runtime return path for card ACKs. Current work-package ACKs and completion outputs go through the assigned current packet lease when present. For formal role outputs, write the body only to a run-scoped packet, result, report, decision, or blocker file, then submit it with `flowpilot_new.py submit-result --lease-id <lease-id> --packet-id <packet-id> --body-file <sealed_result_body_file>` so the current runtime ledger records the event and later exposes only controller-visible envelope metadata with status, paths, and hashes. A local file write is only local storage and must not be treated as wait completion until the current runtime records the packet result. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
post_ack: ACK is receipt only; ACK is not completion. This is a work item when it asks for an output, report, decision, result, or blocker. After work-card ACK, do not stop or wait for another prompt; immediately continue the assigned work and submit the formal output or blocker through the current runtime path. The task remains unfinished until the current runtime receives that output or blocker.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. System-card ACKs, current work-package outputs, and formal role-output submissions go directly through the current runtime commands. Controller must follow the `flowpilot_new.py` lifecycle guard and foreground duty; no unsupported command text, stale runtime state, chat history, or historical artifact authorizes current-run progress.
runtime_context: Treat the runtime delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; submit a protocol blocker through the current runtime path.
-->
# Implementation Intent Challenge

## Role Capability Reminder

- Reviewer checks alignment and quality. Reviewer does not author PM intent or
  FlowGuard models.
- Block only current-gate failures. Put useful but nonblocking improvements in
  `pm_suggestion_items`.
- Nonblocking PM suggestion items may be reported only as
  `flowpilot.pm_suggestion_item.v1` advisory items. Treat the minimum standard
  as advisory only for these items; do not use them as current gate blockers
  unless they are hard current-gate failures.
- Do not contact workers or FlowGuard operators directly; return findings through this reviewer event so PM can route needed work.
- Classify findings as hard blockers, future requirements, and nonblocking notes; only hard blockers may stop the current gate.

Review the PM implementation intent, FlowGuard target-realization model, PM
target-realization decision, and accepted product behavior model before route
skeleton drafting.

Pass only when:

- PM intent is understandable enough to guide route drafting;
- PM intent preserves source-intent from the accepted user request and root
  contract before it is handed to target-realization modeling;
- FlowGuard target-realization model preserves the intent instead of reducing
  it to a thinner implementation;
- every hard realization obligation, shallow-success trap, non-downgrade rule,
  and evidence gate is either modeled or explicitly bounded;
- core deliverable non-downgrade is preserved from PM intent into the
  target-realization model. Block if the bridge would let route skeleton
  drafting replace the accepted deliverable, source, evidence, quality,
  quantity, test, or prohibition with a reachable-only, status-only,
  report-only, honest missing, external-only, partial, not-yet-done, or
  no-fabrication substitute without explicit user authority;
- PM's acceptance decision explains why the model is safe to use;
- no hidden downgrade would let route skeleton drafting skip work that a final
  user would still need.

Block when the bridge would let PM draft a route that looks structurally valid
but cannot realistically realize the accepted product target. If blocking,
include one concrete PM-actionable `recommended_resolution`.

Return `reviewer_passes_implementation_intent_challenge` when the bridge is
safe to use for route skeleton drafting.

Return `reviewer_blocks_implementation_intent_challenge` when PM intent,
FlowGuard model, or PM acceptance must be repaired before route skeleton
drafting.
