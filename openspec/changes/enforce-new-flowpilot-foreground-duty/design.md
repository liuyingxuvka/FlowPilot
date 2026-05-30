## Context

The new FlowPilot path uses `flowpilot_new.py` and the `ai_project_runtime`
ledger instead of the old `flowpilot_router.py` daemon authority. The current
new path already writes `next_action` and `lifecycle_guard` snapshots, and
those snapshots can say `controller_stop_allowed=false`. The observed miss is
at the outer foreground boundary: after a scoped closure, the runtime can still
have an open next packet while the live foreground Controller stops because no
code-level duty forced it to continue or patrol.

There are also misleading terms in the current surface. `cockpit`, `console`,
`monitor`, `standby`, and old Router daemon references describe different
things, but they are easy to read as one surviving kanban/monitor system. The
new design must separate display projection from runtime authority.

## Goals / Non-Goals

**Goals:**

- Add a small foreground duty contract for the new runtime.
- Make every nonterminal state return an executable duty:
  process the next action, wait through a timed patrol, recover, or report a
  control-plane blocker.
- Make passive waiting impossible. If no immediate work can progress, the
  runtime returns a timed patrol duty with the subject, reason, delay, and
  refresh command.
- Add a hard pre-final gate for final answers, done claims, and Controller
  shutdown.
- Preserve the clean new runtime: ledger authority, dynamic leases, sealed
  bodies, and no old Router daemon dependency.
- Clean naming so status display is not mistaken for the old kanban/monitor.
- Extend FlowGuard and fake AI rehearsals to cover the live foreground boundary
  that the previous tests missed.

**Non-Goals:**

- Do not restore a non-startup monitoring UI.
- Do not make the old Router daemon or old Controller action ledger required
  for new `flowpilot_new.py` runs.
- Do not restore a fixed six-role startup team.
- Do not let the foreground duty layer decide product correctness, route-node
  acceptance, or final project quality. It only enforces continuation,
  waiting, recovery, and stop authority.

## Decisions

### Decision: Foreground duty is a thin runtime layer

The new runtime will derive a `foreground_duty` object from the canonical
ledger and lifecycle guard. It is not a second router. It cannot invent product
work. It only translates the current legal state into one of:

- `process_next_action`
- `wait_patrol`
- `recover_or_reissue`
- `control_plane_blocker`
- `terminal_return`

Alternative considered: reuse old Controller standby and patrol timer files.
That would solve the exit problem but would reintroduce old daemon authority,
old monitor assumptions, and confusing compatibility paths.

### Decision: Waiting is a first-class duty action

When no immediate progress action is legal, the runtime must return a
`wait_patrol` duty. The duty names the packet or run subject, the wait reason,
the delay seconds, the refresh command, and the stop-preflight result. A quiet
wait is still work for the foreground Controller.

Alternative considered: rely on prompt text telling the Controller to wait.
That already failed in the observed run, because prompt intent does not create
a hard execution boundary.

### Decision: Final return is guarded by a code-level preflight

The new runtime will expose a final-return preflight. It passes only when the
lifecycle guard says `controller_stop_allowed=true`, the guard decision is
terminal, no nonterminal duty remains, and final closure evidence exists. All
other states produce a nonterminal duty and block final return.

Alternative considered: let final-answer policy live only in `SKILL.md`.
That helps human-readable instruction but cannot be trusted as the only guard.

### Decision: Scoped closure immediately re-enters duty derivation

A packet or phase closure is not project closure. After a scoped closure result
is accepted, the runtime must immediately recompute the guard and foreground
duty. If the next packet exists, the duty is to process that packet. If the
runtime is waiting on a role, the duty is a wait patrol. Only true final
closure may produce `terminal_return`.

### Decision: Terminology becomes explicit

The new surface will use these meanings:

- `status_projection`: display-only summary derived from the ledger.
- `startup_display`: the reused startup UI/Cockpit intake boundary.
- `lifecycle_guard`: metadata stop/continue authority.
- `foreground_duty`: executable Controller duty derived from the guard.
- `legacy_monitor`: old Router daemon/Controller action-ledger monitor, not
  required by new runtime runs.

Code and prompt surfaces should avoid using `cockpit`, `console`, `monitor`, or
`standby` as if they were new-runtime authority.

## Risks / Trade-offs

- Risk: A foreground duty loop could become a second router.
  Mitigation: duty actions are derived from `router_next_action` and guard
  state; they cannot create product nodes or accept evidence independently.

- Risk: Real 60-second sleeps make tests slow or flaky.
  Mitigation: production commands can default to a bounded delay, while tests
  inject deterministic `--once`, `--no-sleep`, or short interval behavior.

- Risk: Repeated nonterminal actions can loop forever.
  Mitigation: reuse guard repeated-action history and classify repeated
  unchanged action as `control_plane_stuck` or recovery instead of quiet wait.

- Risk: Terminology cleanup could remove useful display behavior.
  Mitigation: keep status projection files, but rename/explain them as
  display-only and keep authority in ledger/guard/duty.

## Migration Plan

1. Add OpenSpec requirements for `new-flowpilot-foreground-duty`, runtime
   ledger persistence, and fake AI foreground-boundary rehearsal.
2. Add a FlowGuard model-miss scenario for scoped closure followed by open
   work and foreground final-answer attempt.
3. Implement foreground duty derivation in the new runtime.
4. Add public CLI commands or output fields for duty status and final-return
   preflight.
5. Update `SKILL.md` to route new-runtime foreground behavior through the new
   duty contract and remove misleading old-monitor wording from the formal
   new path.
6. Add unit tests and fake rehearsal cases for:
   scoped closure continuation, open packet stop rejection, wait patrol,
   repeated action recovery, stale result quarantine, and terminal return.
7. Run focused tests, OpenSpec validation, FlowGuard project audit, model
   checks, fake rehearsals, local install sync, install audit, and git status.

Rollback strategy: keep the OpenSpec change active and do not sync the
installed skill as complete if foreground duty tests or final-return preflight
fail.
