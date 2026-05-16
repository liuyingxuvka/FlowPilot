## Context

FlowPilot already has direct Router ACKs, active-holder packet returns,
controller-visible next-action notices, pending return ledgers, and
`run-until-wait`. The remaining latency is an orchestration gap: after
Controller relays a card or packet, the foreground host can wait on the role's
chat/subagent response even though Router already has enough durable evidence
to expose the next legal action.

The existing safety constraints stay intact. Controller is envelope-only, PM
owns package-result disposition and route decisions, reviewers own human-like
inspection gates, FlowGuard officers own model reports, and active-holder
mechanics are not semantic approval.

## Goals / Non-Goals

**Goals:**

- Make Router-ready state preempt foreground role waits after card, bundle,
  packet, and role-output relay boundaries.
- Preserve the existing `run-until-wait` safety boundary: it may fold only
  safe internal Router actions and must stop at user, host, role, payload,
  card, packet, ledger, or final-replay boundaries.
- Keep bounded `wait_agent` only for Router-requested liveness or recovery
  preflights. A timeout remains `timeout_unknown`, not active continuity.
- Add model/test coverage for the stale wait hazard.
- Sync the repository-owned skill to the installed Codex skill after
  verification.

**Non-Goals:**

- No PM/reviewer/officer authority reduction.
- No Controller reads of sealed packet/result/report bodies.
- No change to heartbeat cadence or startup question policy.
- No remote GitHub push, release, or PR.
- No broad rewrite of packet runtime or route planning.

## Decisions

### Decision 1: Router-ready evidence wins over foreground waits

After a router-authored relay boundary, Controller must immediately check
Router status/`next`/`run-until-wait` before waiting on a role response.
Router-ready evidence includes resolved card returns, active-holder
`controller_next_action_notice.json`, returned result envelopes, and pending
actions already stored in router state.

Alternative considered: shorten the host wait timeout. That reduces visible
delay in some cases but preserves the wrong authority source and can still
idle when the Router has already advanced.

### Decision 2: Waits become controlled state, not foreground sleep

If Router truly has no consumable next action and exposes an
`await_card_return_event` or `await_role_decision`, Controller records that
controlled wait and stops or resumes through heartbeat/manual continuation.
It should not spend the foreground turn repeatedly waiting on an unrelated
subagent response.

Alternative considered: add local polling loops around every relay. That risks
busy loops and duplicate side effects. The existing Router reconciliation and
idempotent ledgers are the correct polling boundary.

### Decision 3: Liveness wait stays explicit

`wait_agent` remains useful only for Router-requested liveness/recovery
preflight. The liveness result is diagnostic: missing, cancelled, unknown,
completed, or `timeout_unknown` roles enter restore/replacement handling
rather than ordinary waiting.

Alternative considered: treat a short timeout as "probably still working."
That repeats the current waste and can hide dead role slots.

### Decision 4: Model the host-facing bad state

The existing role-output runtime model already rejects "Controller waits role
instead of Router." This change strengthens that with a concrete
Router-ready-after-relay hazard and prompt/source checks so future text changes
do not reintroduce the stale wait habit.

## Risks / Trade-offs

- Router-ready evidence is stale -> Mitigation: keep existing hash, role,
  route/frontier, packet id, and pending-return validation before consuming.
- Controller crosses a real role/user boundary -> Mitigation: `run-until-wait`
  remains bounded by `SAFE_RUN_UNTIL_WAIT_ACTION_TYPES` and stops at cards,
  packets, payloads, host actions, and role decisions.
- Prompt text promises unsupported automation -> Mitigation: source checks scan
  cards/protocol docs for explicit Router-first and bounded-liveness wording.
- A role is genuinely still working -> Mitigation: Router exposes controlled
  waits and heartbeat/manual resume; foreground Controller records the wait
  instead of idling.
- Installed skill drifts from repository -> Mitigation: run repo-owned install
  sync and audit after tests.

## Migration Plan

1. Add FlowGuard model coverage for the Router-ready foreground-wait hazard.
2. Update Controller and skill protocol text to require immediate Router
   re-entry after relay/status notices.
3. Add focused runtime/source checks that fail if Controller guidance allows
   role/chat waiting when Router-ready evidence exists.
4. Run focused model and router tests, then required broader FlowPilot checks.
5. Sync repo-owned assets into the installed FlowPilot skill and verify the
   install.
6. Stage and commit local git changes only.
