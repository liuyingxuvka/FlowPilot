## ADDED Requirements

### Requirement: Process projection blocks repeated no-progress actions
The router process liveness projection SHALL treat repeated same-action,
same-event-count current-run metadata above the configured threshold as a
process risk that blocks green continuation until a current progress event,
changed action, explicit wait, repair, stop, or break-glass disposition exists.

#### Scenario: Live repeated startup intake is not green
- **WHEN** the active current-run ledger repeats `open_startup_intake` above the
  configured threshold with the same observed event count and no startup intake
  event
- **THEN** the process liveness runner MUST report the run as repeated-action
  blocked or repair-required
- **AND** it MUST NOT report mesh-green or safe-to-continue live projection.

#### Scenario: Stuck absorption survives refresh
- **WHEN** a prior lifecycle guard refresh recorded `control_plane_stuck` for
  the same action key and event count
- **THEN** later projection MUST keep the stuck disposition visible until a new
  event, changed action key, explicit wait, repair, stop, or break-glass
  disposition is recorded.

