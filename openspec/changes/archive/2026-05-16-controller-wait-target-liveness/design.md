## Context

Formal FlowPilot startup now uses a Router daemon and foreground
Controller standby. The daemon owns progress; Controller watches daemon status
and the Controller action ledger while the run is active. The remaining gap is
that standby can still be generic: it can say "waiting for a role" without
making Controller track who is being waited on, what evidence is expected, and
what liveness check must be repeated during reminders.

The design must preserve the existing authority split. Router remains the
progress owner, PM owns recovery decisions, and Controller is a metadata-only
watcher and host-action executor.

## Goals / Non-Goals

**Goals:**

- Add a small Router-authored wait-target block to daemon status.
- Keep the monitor simple enough for Controller to follow directly.
- Handle only three wait classes: ACK waits, role report/result waits, and
  Controller-local action waits.
- Make role liveness an active check obligation, not a cached truth field.
- Route unhealthy background-role waits through the existing Router blocker and
  PM recovery path.
- Keep standby metadata-only and free of sealed packet/result/report body
  access.

**Non-Goals:**

- Do not add a new recovery framework.
- Do not let Controller replace background agents by itself.
- Do not add a hard total timeout for long report/result work.
- Do not run `next` or `run-until-wait` as a normal standby metronome.
- Do not change the user-visible FlowPilot startup questions or frozen
  acceptance contract.

## Decisions

1. **Extend daemon status with a wait-target block.**

   Router writes `current_wait.wait_class`, `target_role`, `wait_reason`,
   `started_at`, reminder cadence, expected event/path metadata, and
   controller-visible reminder text. This attaches the new behavior to the
   existing monitor instead of creating a second watch file.

2. **Do not write "role is alive" as monitor truth.**

   The monitor may say `liveness_check_required: true`, identify the target
   role, and record the last probe timestamp/result/evidence. Controller must
   refresh that check on each report/result reminder cycle. This avoids stale
   status being mistaken for current liveness.

3. **Use simple wait timing.**

   ACK waits remind after three minutes and escalate to blocker after ten
   minutes without ACK. Report/result waits remind every ten minutes and do not
   have a hard total timeout by default; they escalate only when the target role
   is missing, cancelled, unknown, unresponsive, or returns a blocker.

4. **Controller-local waits are self-audits.**

   If Router status says the wait is for Controller-local work, Controller does
   not send a reminder. It scans pending/in-progress actions, checks receipts,
   fixes any missed local action it can perform, and records a Controller
   blocker only when it cannot complete the local action.

5. **Recovery remains PM-routed.**

   Controller raises a Router-visible blocker event with controller-visible
   facts. Router enters the existing blocker path, then PM decides whether to
   continue waiting, re-remind, reissue cards/tasks, supersede the old role, or
   start a replacement role seeded from current role memory and the current
   packet/card authority.

## Risks / Trade-offs

- Stale liveness data could hide failed roles -> Store liveness as a required
  probe and last-check evidence only; never as current truth.
- Reminders could become noisy -> Use fixed reminder cadences and Router-authored
  reminder text; Controller does not invent extra wording.
- Long work could be interrupted too aggressively -> Report/result waits have
  no default hard total timeout; healthy working roles continue.
- Controller could drift into route ownership -> Model and tests assert that
  Controller only reminds, self-audits local actions, or raises blockers.

## Migration Plan

1. Extend the FlowGuard persistent Router daemon model with wait classes,
   reminder cycles, liveness probes, and blocker escalation hazards.
2. Add focused tests for ACK reminder/blocker, report reminder with repeated
   liveness probe, missing-role blocker, and Controller-local self-audit.
3. Extend Router daemon status and standby payloads with the wait-target block.
4. Update Controller card guidance to follow the wait-target monitor.
5. Sync the installed FlowPilot skill and run focused install/audit checks.
6. Skip the two heavyweight meta/capability model checks for this task by user
   request.
