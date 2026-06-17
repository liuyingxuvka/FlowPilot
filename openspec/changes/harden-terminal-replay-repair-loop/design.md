## Context

FlowPilot terminal backward replay is the final quality gate for recursive
high-standard runs. A terminal replay blocker is special because there is no
active route node left when it fires; the frontier is already
`ready_for_final_closure`. The repair path therefore cannot rely on the normal
node repair shape alone.

The observed failure has two connected parts:

1. `repair_current_scope` for a terminal replay blocker opens a generic
   current-scope repair packet with `packet_kind=review` and
   `route_scope=terminal_backward_replay`, but the packet body lacks
   `segment_targets`. A Reviewer cannot submit a valid terminal replay result
   against that packet.
2. `router_next_action` checks final-ready closure before current open packet
   dispatch, so it can return `close_project` while the terminal repair or
   reissue packet is still open.

## Goals / Non-Goals

**Goals:**

- Keep terminal replay repair inside the current packet/result protocol.
- Preserve the runtime-issued terminal segment map on repair packets and
  reissue packets.
- Prefer current open packets over final closure attempts.
- Prove the full return loop with focused unit tests and fake E2E coverage.
- Bind the new tests to Model-Test Alignment evidence.

**Non-Goals:**

- Do not add a new role, ledger family, compatibility parser, or old-result
  fallback.
- Do not treat a terminal blocker or waiver as terminal replay closure
  evidence.
- Do not broaden route mutation semantics in this change.

## Decisions

1. Terminal current-scope repair packets reuse `packet_kind=review` and
   `route_scope=terminal_backward_replay`, but their body is specialized with
   terminal replay fields.
   - Rationale: the result family is already keyed by packet kind and route
     scope, so the smallest current-contract repair is to make the packet body
     satisfy the existing terminal replay contract.

2. Router final-ready closure is blocked by any current active packet.
   - Rationale: an open current packet is live work. Final closure is only a
     valid next action after all current packet obligations are accepted,
     superseded, stopped, or blocked with a concrete recovery action.

3. The full terminal replay repair loop is the required regression, not merely
   the first failing branch.
   - Rationale: the model miss was a false confidence gap between fragment
     tests and the composed state machine.

## FlowGuard Route

- Existing model preflight: reuse terminal/closure/resume and repair
  transaction boundaries.
- Model-miss route: classify as `boundary_missing` plus
  `evidence_overclaimed`; the old claim covered first blocker capture, not the
  full return loop.
- Model-test alignment: add observed-regression evidence for the terminal
  repair loop and same-class fake E2E evidence.
- DevelopmentProcessFlow: source, model, tests, topology, and install evidence
  must be rerun after the behavior and evidence rows change.

## Validation

- Focused unit tests for terminal replay repair packet context and router
  open-packet priority.
- Fake E2E test that injects one terminal replay blocker and then repairs it to
  terminal completion.
- Model-test alignment check.
- Field/contract checks for packet fields and terminal repair context.
- Core runtime checks, high-standard control flow, new entrypoint tests,
  topology build/check, install sync/check/audit.
