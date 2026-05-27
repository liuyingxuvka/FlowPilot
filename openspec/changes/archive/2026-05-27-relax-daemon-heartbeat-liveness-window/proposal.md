## Why

The Router daemon can remain alive and actively process startup/controller work while its status heartbeat is delayed longer than the current five-second monitor window. That window creates noisy liveness checks and makes healthy busy work look like a daemon problem.

## What Changes

- Relax the daemon heartbeat liveness-check window and daemon lock stale threshold from five seconds/ten seconds to thirty seconds.
- Keep the existing safety rule: heartbeat age alone must never trigger restart or lock replacement.
- Keep Controller as the owner of the actual process/lock/status liveness check after the relaxed window is exceeded.
- Update runtime prompt wording, executable FlowGuard model evidence, focused tests, and local install sync so installed FlowPilot matches the repository source.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `daemon-heartbeat-liveness`: Change the monitor grace window from five seconds to thirty seconds while preserving Controller-owned attach/recover decisions.
- `controller-patrol-timer`: Change the patrol timer delayed-daemon-heartbeat trigger from older-than-five-seconds to older-than-thirty-seconds.
- `persistent-router-daemon`: Align the run-scoped daemon lock stale threshold with the thirty-second heartbeat check window while preserving single-writer recovery rules.

## Impact

- Affected runtime code: `skills/flowpilot/assets/flowpilot_router_startup_daemon.py`, status projection code that reads daemon lock liveness, and related heartbeat prompt text.
- Affected model evidence: `simulations/flowpilot_daemon_liveness_model.py`, its runner expectations, and result JSON.
- Affected tests: focused Router foreground/startup-daemon tests that assert heartbeat metadata or delayed-heartbeat behavior.
- Affected install surface: repository-owned installed `flowpilot` skill copy must be refreshed after verification.
