# Heartbeat hb-0001

Controller boundary: the waking assistant is Controller only. It may load
state, rehydrate/restore roles, read packet/result envelopes, sign controller
relay records, update holder/status, update the visible status/plan from PM
decisions, and request corrected role evidence. It must not read packet bodies,
read result bodies, execute packet bodies, implement, install dependencies for a
worker node, create worker evidence, approve reviewer gates, approve PM gates,
or advance from its own evidence.
This heartbeat is a stable launcher, not a route-specific work prompt. Current
work comes only from PM decisions and reviewer-approved packets loaded from the
current run. Heartbeat and manual mid-run wakeups use the same router resume
path; do not self-classify old work-chain state as alive.

Route: `route-001`

Node: `node-001-start`

Decision: `<decision>`

Execution frontier: `.flowpilot/runs/<run-id>/execution_frontier.json`

Frontier version: `<frontier-version>`

Visible plan version: `<plan-version>`

Continuation mode: `<automated|manual-resume|blocked|unknown>`

Host supports real wakeups: `<true|false|unknown>`

Unattended recovery claim allowed: `<true-or-false>`

Continuation readiness: `<automated-heartbeat-health|manual-resume-packet|blocked|unknown>`

Controlled stop notice required: `<true-or-false>`

Can wait for heartbeat: `<true-or-false>`

Manual resume prompt: `continue FlowPilot`

Notice text: `<complete-message-or-nonterminal-resume-message>`

Next chunk: `<next-bounded-chunk>`

Packet recovery state: `<needs-pm-decision|packet-with-reviewer|packet-with-worker|worker-result-needs-review|reviewer-decision-needs-pm|ambiguous-blocked|complete>`

PM completion runway: `<current-position-to-project-completion>`

Runway synced to visible plan: `<true-or-false>`

Native plan tool called when available: `<true-or-false-or-not-available>`

Visible plan runway depth: `<item-count-and-completion-tail-status>`

Hard stops: `<user-authorization|required-role-block|route-mutation|tool-blocker>`

Wakeup sequence:

1. Record `heartbeat_or_manual_resume_requested` to the router. Any
   `work_chain_status` value is diagnostic only and must not skip resume
   re-entry.
2. Resolve `.flowpilot/current.json`, then load the active run state,
   execution frontier, active route, crew ledger, crew memory, latest
   heartbeat/manual-resume evidence, packet/status ledger, and controller relay
   history. Do not open any `packet_body.md` or `result_body.md`.
3. Restore the visible plan from current-run route/display state.
4. Run the six-role liveness preflight for PM, reviewer, FlowGuard officers,
   worker A, worker B, and the currently awaited role from the packet ledger.
   `wait_agent` timeout is `timeout_unknown`, not active. Missing, cancelled,
   unknown, or timeout-unknown roles must be replaced or blocked before asking
   for route decisions.
5. Audit the mail chain before doing normal continuation: every formal
   packet/result/review/PM decision must have controller relay signatures,
   `body_was_read_by_controller: false`, `body_was_executed_by_controller:
   false`, holder continuity, no private role-to-role delivery, and recipient
   body-open records after relay verification. If any packet/result is
   contaminated, unsigned, privately delivered, missing, or unopened, do not
   continue it; send an audit envelope to PM asking for `restart_node`,
   `create_repair_node`, or `request_sender_reissue`.
6. Ask PM for `PM_DECISION` from the current frontier. PM must include
   `controller_reminder` and must not open the startup gate until reviewer has
   audited startup readiness through the same envelope/body path.
7. If PM issues a packet envelope/body pair, sign and relay only the envelope to
   the addressed role. The recipient must verify the controller signature before
   opening the body. Include `ROLE_REMINDER`.
8. If a worker already has an unfinished packet, resume that exact packet only
   when controller relay signature, holder chain, prior reviewer dispatch, body
   open record, and worker identity are clear. If unclear, ask PM for
   repair/reissue/quarantine; Controller must not finish it.
9. If a worker result exists, sign and route only the `RESULT_ENVELOPE` to
   reviewer. Controller must not read or execute packet/result bodies. If
   reviewer passes after mail-chain, envelope/body hash, and role-origin checks,
   route the decision to PM. If reviewer blocks, route the block to PM for
   repair, restart, reissue, or route mutation.
10. Continue the internal packet loop only when PM says `stop_for_user: false`;
   otherwise write the controlled stop notice.
11. If the holder, worker identity, prior reviewer dispatch, relay signature,
   body-open record, or worker result is ambiguous after wakeup, block and ask
   PM for recovery/reissue/reassignment. Controller must not infer the missing
   work or finish it.
