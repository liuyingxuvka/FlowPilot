## Context

The new `flowpilot_new.py` runtime intentionally removed old Router daemon authority and the old non-startup monitor UI. It now uses the current-run ledger, dynamic leases, sealed packets, lifecycle guard, and foreground duty as authority.

The observed live-run miss is narrower: `wait_for_result` repeated during a real reviewer wait, the guard escalated to replacement too quickly, the original reviewer later submitted a valid result, and the packet was then reassigned to a replacement lease even though it already had `accepted_result_id`. Old FlowPilot already handled the same class more carefully through a continuous standby wait target ladder. The repair should borrow that ladder, not restore the old monitor.

## Goals / Non-Goals

**Goals:**

- Keep new-runtime authority in the current ledger, lifecycle guard, dynamic leases, and foreground duty.
- Make wait recovery distinguish "still waiting", "role still working", "progress seen", "check liveness", "no output", and "inactive/dead" before replacement.
- Add a public progress command so a live role can record current-run progress without completing a packet.
- Prevent accepted packet state regression: assign, ACK, and replacement cannot reopen or overwrite an accepted packet.
- Repair the active run race by accepting the original reviewer result and cancelling/superseding the mistaken replacement lease.
- Add FlowGuard and fake AI evidence for slow live agents and assignment races.

**Non-Goals:**

- Do not restore the old daemon or old Controller action ledger as new-runtime authority.
- Do not restore a fixed six-person crew requirement for new runtime work.
- Do not let progress satisfy packet completion.
- Do not read sealed packet or result bodies for lifecycle guard decisions.
- Do not claim release confidence from progress-only background checks.

## Decisions

### Decision: Use a thin wait-target ladder in the new lifecycle guard

The new guard will keep `wait_patrol` as the foreground duty, but recovery will not be driven by repeated guard count alone. For packet waits, the guard will derive a wait recovery state from packet status, lease status, ACK, result presence, progress count, wait timestamps, and current-run events:

- `wait_patrol`: no threshold reached.
- `wait_reminder_due`: ACK reminder threshold reached.
- `liveness_check_due`: result/report wait threshold reached.
- `grace_wait`: liveness/progress says the role is still working.
- `reissue_or_replace_lease`: current no-output or inactive evidence is present.
- `repair_assignment_race`: accepted result and active replacement conflict.

Alternative considered: keep the existing repeated-count threshold and raise the number. That would reduce false positives but still lacks the old distinction between slow work and dead work.

### Decision: Borrow old wait thresholds without old daemon authority

The default patrol remains 60 seconds. ACK waits use a 3-minute reminder and 10-minute blocker threshold. Result/report waits use a 10-minute reminder plus fresh liveness check. These numbers match the old standby behavior, but their authority comes from the new ledger.

Alternative considered: introduce a new always-on background process. That is outside this repair and would reintroduce old monitor confusion.

### Decision: Progress is liveness only

The runtime already stores lease progress internally. The new CLI will expose it as `progress --lease-id --packet-id --status`. Progress increments `progress_count`, refreshes the guard, and keeps the packet incomplete. It only prevents premature replacement when the active lease is still current.

Alternative considered: infer liveness from ACK alone. The observed miss shows ACK alone is too weak after a long result wait.

### Decision: Accepted packets are immutable for assignment

`assign_packet` and `ack_lease` will fail if the packet already has an accepted result. The guard will also repair accepted-packet/active-lease races by preferring the accepted result and closing the mistaken replacement lease.

Alternative considered: let later replacement output override the old result. That breaks FlowPilot packet authority and makes valid result timing nondeterministic.

### Decision: Current-run repair is explicit and auditable

The active run will be repaired through runtime code or a narrow repair helper that records events for the mistaken replacement lease, restores `packet-0003` to accepted, and allows `packet-0004` validation to become the next action.

Alternative considered: manually edit JSON with no event trail. That would hide the exact failure the fix is meant to prevent.

## Risks / Trade-offs

- More wait states can make status output noisier -> keep them metadata-only and show concise public status.
- Real-time thresholds can slow tests -> tests use deterministic timestamp/config overrides and zero/short patrol sleeps.
- A progress command could be abused to avoid replacement forever -> progress only extends grace when it comes from the active lease and can be bounded by repeated liveness checks.
- Repairing the active run touches live `.flowpilot` state -> take a narrow before/after audit and do not read sealed bodies for the repair.

## Migration Plan

1. Add OpenSpec requirements and tasks.
2. Update the FlowGuard lifecycle model with the slow-live-agent and accepted-reassignment miss family.
3. Implement wait recovery metadata, progress command, assignment hard gates, and accepted-race repair.
4. Repair `run-20260530-102304`.
5. Add focused unit tests and public fake AI rehearsal coverage.
6. Run focused tests first, then model checks, OpenSpec validation, install checks, and background heavier checks where practical.
7. Sync the local installed `flowpilot` skill after the repository copy passes focused validation.

Rollback strategy: if validation fails, keep the OpenSpec change active, do not sync the installed skill as complete, and report the failing gate.
