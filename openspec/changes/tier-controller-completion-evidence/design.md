## Context

The persistent Router changed FlowPilot from human-supervised handoff into an
autonomous control loop. That makes evidence stricter for workflow-critical
decisions, but it should not turn small display/status actions into route
blockers.

The concrete failure class is a display/status sync action that wrote
`visible_plan_sync` but did not set the legacy `visible_plan_synced` flag. The
Router then treated the missing flag as a hard stateful receipt failure and
escalated to PM repair. A separate PM repair decision still correctly requires
formal file-backed role-output evidence.

## Goals / Non-Goals

**Goals:**

- Distinguish four classes of work: Router-owned state writes, Controller
  display/communication work, external keepalive actions, and heavyweight role
  decisions.
- Make display/status work nonblocking: Router may write and soft-record it,
  but route progress must not wait on a display-only receipt.
- Keep lightweight hard confirmation only for external actions that can break
  autonomous continuation if missing.
- Keep PM, reviewer, worker, and control-blocker repair decisions on the
  existing role-output runtime path with body refs, hashes, and runtime
  receipts.
- Update FlowGuard coverage to encode the evidence-tier distinction.

**Non-Goals:**

- Do not require screenshots, user-dialog proof, or additional proof artifacts
  for display/status Controller actions.
- Do not make display/status sync a hard blocker for main route progress.
- Do not weaken file-backed evidence requirements for semantic decisions,
  worker results, reviewer reports, or PM repair decisions.
- Do not change Controller authority to read sealed bodies or decide workflow
  outcomes.
- Do not rewrite the parallel user-status/progress-summary work.

## Decisions

- Treat `sync_display_plan` as a nonblocking display action. It writes public
  display/status files and a soft `visible_plan_sync` marker, but the next
  Router step may continue without waiting on a hard postcondition.
- Remove hard `visible_plan_synced` postconditions from Router-generated
  display sync actions. Keep `flags.visible_plan_synced` as a compatibility
  marker written when display sync happens.
- Keep `_pending_action_postcondition_satisfied` for actions that genuinely
  require hard confirmation, such as host heartbeat binding or role
  rehydration. Do not route display-only misses into PM repair.
- Preserve the current role-output runtime validation for control-blocker
  repair decisions. The minimal repair does not accept progress packets or
  chat summaries as decisions.

## Risks / Trade-offs

- [Risk] A nonblocking display sync might fail silently. -> Mitigation:
  record a soft marker/history entry and keep status/display files best-effort;
  display polish does not authorize route advancement.
- [Risk] Future developers could put semantic decisions in the lightweight
  tier. -> Mitigation: FlowGuard hazards keep role-output events separate and
  require file-backed bodies for PM/reviewer/worker decisions.
- [Risk] Old active runs may still contain historical blocker artifacts. ->
  Mitigation: the runtime fix prevents recurrence and allows pending receipt
  reconciliation; historical blocker files remain audit evidence unless an
  explicit run repair is requested.
