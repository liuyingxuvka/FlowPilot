<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: project_manager
recipient_identity: FlowPilot project manager role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: System-card ACKs go through the current runtime card check-in command; this is the current-runtime return path for card ACKs. Current work-package ACKs and completion outputs go through the assigned current packet lease when present. For formal role outputs, write the body only to a run-scoped packet, result, report, decision, or blocker file, then submit it with `flowpilot_new.py submit-result --lease-id <lease-id> --packet-id <packet-id> --body-file <sealed_result_body_file>` so the current runtime ledger records the event and later exposes only controller-visible envelope metadata with status, paths, and hashes. A local file write is only local storage and must not be treated as wait completion until the current runtime records the packet result. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
post_ack: ACK is receipt only; ACK is not completion. After event-card ACK, process this event card only through its paired PM card path or an explicitly Router-authorized output event; if no authorized path exists, return a protocol blocker.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. System-card ACKs, current work-package outputs, and formal role-output submissions go directly through the current runtime commands. Controller must follow the `flowpilot_new.py` lifecycle guard and foreground duty; no unsupported command text, stale runtime state, chat history, or historical artifact authorizes current-run progress.
runtime_context: Treat the runtime delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; submit a protocol blocker through the current runtime path.
-->
# PM Event: Reviewer Blocked

## Role Capability Reminder

- If a PM-owned decision still lacks evidence, modeling, research, review, or implementation support, register a bounded `pm_registers_role_work_request` only when the router's current `allowed_external_events` includes that event; otherwise record the limitation or blocker instead of emitting it.
- Treat the router's current `allowed_external_events` as the active authority for what this card may return.
- Put reviewer, worker, and FlowGuard operator advice that needs PM disposition into the PM suggestion/blocker ledger instead of leaving it only in prose.
- If the block involves FlowGuard-backed judgement, record `flowguard_work_order_id`, `flowguard_report_id`, `flowguard_report_freshness`, skipped/progress-only status, and the repair path for the report or work order.


Reviewer blocked dispatch, result acceptance, route activation, or replay.

If the blocked report also includes PM-actionable `pm_suggestion_items`,
disposition them through the existing PM suggestion ledger or the current PM
repair decision. A suggestion may be rejected with reason when it is not worth
current scope, or bound to an already named downstream node/gate when that gate
will decide it with evidence; do not leave it as unresolved later work.

When the blocker report includes `Quality score: X/10; target: 9/10; minimum
hard gate passed: true|false`, PM must interpret it with the same Reviewer
score rubric used in the review packet: `6/10` means the minimum user standard
is just met, `9/10` is the high-quality FlowPilot target, and `10/10`
substantially exceeds the user's standard. Scores below `9/10` are PM
decision-support when the hard gate is met; PM always owns the optimization
choice, including whether to continue, optimize, bind the item to an already
named node/gate, reject with reason, waive, stop, ask the user, or issue
repair. This remains true even when Reviewer reports no blocker.

If the Reviewer blocker identifies a current quantitative gap, such as required
item count, word count, coverage rows, required ids, evidence count, or named
sections where delivered quantity is short, PM must carry the
required/delivered/gap detail into the repair decision and repair packet.

PM must choose one:

- repair packet;
- sender reissue;
- Controller break-glass for FlowPilot control-plane blocker repair when the
  normal repair lane cannot form a legal next action;
- route mutation;
- quarantine evidence;
- user stop.

For control-plane blockers such as non-replayable package scripts, package
handoff defects, event-authority contradictions, or evidence-entry defects,
prefer Controller break-glass repair before user stop when the normal PM repair
lane cannot form a legal next action. User stop is the terminal boundary when a human
decision is genuinely required or break-glass is unavailable, unsafe, or outside
authority.

For reviewer-blocked repair or sender reissue, prefer returning the work to the
same worker who produced the blocked result so the repair keeps local context,
unless that worker is unavailable, the issue shows a fundamental
misunderstanding, or the repair has become separable new work.

The blocked gate remains incomplete until the same required review class passes.
If the root cause is missing, stale, wrongly scoped, skipped, progress-only, or
unaccepted FlowGuard evidence, PM must repair or rerun the FlowGuard Work Order
and get the same review class recheck before advancing the gate.
