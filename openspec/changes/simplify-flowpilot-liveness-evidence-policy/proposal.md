## Why

FlowPilot currently mixes current-run ACK/progress evidence with host liveness
probe outcomes such as `timeout_unknown`, which can make a still-working
background agent eligible for replacement after one ambiguous probe. The runtime
needs one auditable current-contract liveness path that is easy for Controller,
roles, tests, and fake-agent rehearsals to follow.

## What Changes

- Replace the current host-liveness driven wait decision with a single
  ACK/progress evidence-age policy:
  - Controller patrols every 5 minutes.
  - Before ACK, 5 minutes without ACK reminds the role to ACK and 10 minutes
    without ACK reissues or replaces the lease.
  - After ACK, ACK is the first liveness evidence and `progress +1` is the only
    subsequent liveness evidence.
  - After ACK, 10 minutes without fresh evidence triggers a strong progress
    reminder and 30 minutes without fresh evidence reissues or replaces the
    lease.
- **BREAKING**: Remove `timeout_unknown` and host-liveness probe fields from
  the current wait/replacement contract instead of preserving compatibility.
- **BREAKING**: Reject or delete current-runtime commands and payloads whose
  only purpose is to submit `timeout_unknown`/host-liveness status as the wait
  authority.
- Update role cards and packet prompts so every background role sees the same
  `progress +1` instruction and reminder behavior.
- Expand lifecycle, field-lifecycle, and fake-agent Cartesian coverage so old
  liveness fields cannot return through runtime, prompts, models, or rehearsal
  fixtures.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `wait-reconciliation`: wait decisions are based on current result, ACK, and
  progress evidence age rather than host liveness probe status.
- `work-packet-ack-and-no-output-retry`: ACK is receipt only, and no-output
  waits use strong progress reminders before reissue/replacement.
- `router-process-liveness`: the process model must prove the simplified
  liveness ladder and reject legacy timeout/host-liveness branches.
- `synthetic-agent-coverage-matrix`: fake-agent rehearsal must cover the
  Cartesian ACK/progress/evidence-age/legacy-field matrix for the new flow.

## Impact

- Runtime wait guard and foreground duty state in
  `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`.
- Current `flowpilot_new.py` command exports and CLI command set.
- Runtime role cards, packet identity prompts, and progress-status contract
  text under `skills/flowpilot/assets/runtime_kit/`.
- FlowGuard simulations for lifecycle guard, role recovery/liveness, field
  lifecycle, process liveness, and fake project rehearsal coverage.
- Unit tests, fake-agent replay tests, field lifecycle checks, install checks,
  and local installed `flowpilot` skill synchronization.
