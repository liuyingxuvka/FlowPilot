# flowpilot-control-plane-lifecycle Delta

## ADDED Requirements

### Requirement: Final preflight only blocks on current effective blockers
FlowPilot SHALL report final-return semantic blockers only when the blocker is
still current for the active route, packet, node, and repair target.

#### Scenario: Accepted noncurrent repair packet does not block final return
- **WHEN** a semantic blocker has `status: repair_packet_open`
- **AND** its `repair_packet_id` points at a packet with status `accepted`,
  `quarantined_after_route_mutation`, or `superseded_after_repair`
- **THEN** final return preflight SHALL NOT emit
  `active_blocker_current_target` for that blocker
- **AND** the blocker SHALL remain visible as historical audit state rather
  than current terminal authority.

#### Scenario: Current open repair packet still blocks final return
- **WHEN** a semantic blocker has `status: repair_packet_open`
- **AND** its repair packet is current, open, assigned, acknowledged, or
  result-submitted without accepted closure
- **THEN** final return preflight SHALL continue to block terminal return.

### Requirement: Route mutation supersedes same-family obsolete repair blockers
FlowPilot SHALL collapse obsolete same-family repair blockers when a reviewed
route mutation replaces the failing repair path.

#### Scenario: Same-family old blocker is superseded by replacement route
- **WHEN** a route mutation replaces a missing-required-information repair path
- **AND** an older `repair_packet_open` blocker has the same blocker class,
  route scope, and repair target family
- **AND** the older repair packet is already noncurrent
- **THEN** FlowPilot SHALL mark the older blocker
  `superseded_by_route_mutation`
- **AND** FlowPilot SHALL NOT treat the older blocker as current final-return
  authority.

#### Scenario: Unrelated current blocker is not collapsed
- **WHEN** a route mutation replaces one missing-information repair path
- **AND** another blocker is still current or belongs to a different blocker
  class, route scope, or target family
- **THEN** FlowPilot SHALL leave that blocker current until its own repair,
  recheck, mutation, waiver, or terminal stop resolves it.

### Requirement: Material handoff lifecycle uses runtime authorized reads
FlowPilot SHALL treat cross-role material handoff as a current runtime
authorized-read lifecycle.

#### Scenario: Downstream PM must open producer handoff result
- **WHEN** a route introduces a producer node for a PM-readable authorized
  material receipt handoff
- **THEN** the downstream PM authorization packet SHALL receive the producer
  result through `authorized_result_reads`
- **AND** PM authorization SHALL require a runtime body-open receipt for that
  producer result before approving material reads.

#### Scenario: Summary or stale path does not authorize material reads
- **WHEN** downstream material authorization relies only on a summary, blocker
  report, review report, FlowGuard report, workspace path, packet id, role
  memory, historical artifact, or one-time active state
- **THEN** FlowPilot SHALL block or require PM repair instead of authorizing
  material reads.
