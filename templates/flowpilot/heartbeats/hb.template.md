# Heartbeat hb-0001

Controller boundary: the waking assistant is Controller only. It may load
state, rehydrate/restore roles, relay packets and decisions, update the visible
status/plan from PM decisions, and request corrected role evidence. It must not
implement, install dependencies for a worker node, create worker evidence,
approve reviewer gates, approve PM gates, or advance from its own evidence.
This heartbeat is a stable launcher, not a route-specific work prompt. Current
work comes only from PM decisions and reviewer-approved packets loaded from the
current run.

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

1. Resolve `.flowpilot/current.json`, then load the active run state,
   execution frontier, active route, crew ledger, crew memory, latest
   heartbeat/manual-resume evidence, and packet/status ledger.
2. Rehydrate or restore PM, reviewer, FlowGuard officers, worker A, and worker
   B before asking for route decisions. If a required role cannot be restored
   or explicitly replaced, block rather than continuing as Controller.
3. Ask PM for `PM_DECISION` from the current frontier. PM must include
   `controller_reminder`.
4. If PM issues `NODE_PACKET`, send it to reviewer for dispatch approval before
   any worker receives it. Include `ROLE_REMINDER`.
5. If a worker already has an unfinished packet, resume that exact packet only
   when prior reviewer dispatch and worker identity are clear. If unclear, ask
   PM for repair/reissue/quarantine; Controller must not finish it.
6. If a worker result exists, route `NODE_RESULT` to reviewer. If reviewer
   passes, route the decision to PM. If reviewer blocks, route the block to PM
   for repair or mutation.
7. Continue the internal packet loop only when PM says `stop_for_user: false`;
   otherwise write the controlled stop notice.
8. If the holder, worker identity, prior reviewer dispatch, or worker result is
   ambiguous after wakeup, block and ask PM for recovery/reissue/reassignment.
   Controller must not infer the missing work or finish it.
