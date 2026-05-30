## Context

The new `flowpilot_new.py` path deliberately avoids the old heavy Router
monitor and fixed six-agent topology. It starts through the reused startup
intake UI, writes a current-run ledger, issues sealed packets, leases dynamic
responsibilities, and advances with `router_next_action`.

The missing piece is lifecycle authority. A ledger plus `next_action` proves
the run can be resumed, but it does not prove that the foreground controller is
allowed to stop, that waits are being patrolled, or that stale/late role output
will be quarantined instead of silently accepted.

## Goals / Non-Goals

**Goals:**

- Add a minimal guard layer that says whether the foreground Controller can
  stop, continue, wait, recover, or report a control-plane blocker.
- Keep the guard metadata-only. It can read packets, envelopes, leases, route
  state, result timestamps, and next action, but it must not expose sealed
  packet or result bodies.
- Persist guard snapshots under the current run so manual resume and heartbeat
  wakeups can rehydrate from files instead of chat memory.
- Detect practical failures from prior FlowPilot experience: missing ACK,
  ACK-only wait, inactive lease, no result, stale result, repeated unchanged
  action, route mutation stale packet, and terminal claims without stop
  authority.
- Extend FlowGuard and fake AI rehearsals so the tests prove these branches.

**Non-Goals:**

- Do not restore a non-startup monitor UI requirement.
- Do not restore the old Router as authority for the new runtime.
- Do not require a fixed six-person team before a new runtime run can progress.
- Do not let the guard approve product work, route mutation, FlowGuard checks,
  reviews, validation, or completion.
- Do not use chat prose as recovery evidence.

## Decisions

### Decision: Guard is metadata authority, not product authority

The guard will produce a `lifecycle_guard` snapshot with the current next
action, terminal stop flag, waiting packet, lease health, patrol decision,
recovery reason, and resume source. It may decide that the Controller must not
stop, but it does not decide whether a product node passed.

Alternative considered: reuse old Controller standby/daemon files directly.
That would reintroduce old surface area and make the clean runtime depend on
old monitor assumptions.

### Decision: Terminal completion requires explicit stop authorization

`terminal_complete` remains the final router action, but the guard is the only
runtime surface that marks `controller_stop_allowed: true`. All nonterminal
snapshots set it to false and name the next legal guard action.

Alternative considered: treat `terminal_complete` from `router_next_action` as
enough. That misses the user's concern because a nonterminal status could still
be reported as "we know next action" and then the foreground thread exits.

### Decision: Resume is a first-class command path

The new entrypoint will support a manual resume/patrol operation that loads the
current shell and ledger, records a resume request, computes guard status, and
persists the snapshot. Heartbeat automation can call the same path later, but
the runtime must not depend on heartbeat availability.

### Decision: Wait patrol classifies failures before recovery

The guard records a bounded patrol outcome:

- `process_next_action` when work can continue now;
- `wait_for_ack` or `wait_for_result` when a live lease is still pending;
- `reissue_or_replace_lease` when ACK/result wait is overdue or inactive;
- `quarantine_stale_result` when a result no longer matches current route,
  packet, lease, or source generation;
- `control_plane_stuck` when the same action repeats too many times without a
  new event;
- `terminal_return` only when final closure and stop authorization are present.

### Decision: Recovery is recorded, not improvised

Recovery decisions become guard events/snapshots first. Later work can turn
them into PM recovery packets or reissue operations, but the guard itself must
not invent product work or silently advance a node.

## Risks / Trade-offs

- More state files can become stale -> write snapshots from the canonical
  ledger every time the guard runs and include the current event count.
- A guard could overclaim live-host autonomy -> fake rehearsals must record
  fake/scoped confidence separately from live host confidence.
- Overdue timing can be flaky -> tests use deterministic timestamps and event
  counters rather than wall-clock sleeps.
- A minimal guard will not be a full daemon -> document the boundary: this
  upgrade prevents legal foreground exit and supports manual/heartbeat resume;
  it is not a separate always-on process unless a host schedules it.

## Migration Plan

1. Add OpenSpec requirements and FlowGuard lifecycle-guard model coverage.
2. Extend the runtime ledger schema with `lifecycle_guard`, patrol snapshots,
   stop authority, and action-history fields.
3. Add entrypoint commands for `patrol` and `resume` and include guard state in
   status output.
4. Add focused unit tests and fake AI rehearsals for good path and bad paths.
5. Run OpenSpec validation, FlowGuard checks, focused tests, fake rehearsal,
   install sync/audit/check-install, and background meta/capability checks.
6. Commit the completed change without push, tag, release, or deploy.

Rollback strategy: the change is isolated to the new runtime path. If the
guard fails validation, keep this OpenSpec change active and do not sync the
installed skill as complete.
