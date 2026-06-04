## ADDED Requirements

### Requirement: Current repair targets are explicit and current

FlowPilot SHALL route repair, review, FlowGuard, PM decision, recovery, and
final-preflight work only through a current packet/result/effect target in the
current run.

#### Scenario: Active blocker points to replaced packet
- **WHEN** an active or awaiting-recheck blocker references a packet that has
  been explicitly replaced by a current repair or reissue packet
- **THEN** runtime SHALL reject the old packet as a routing target
- **AND** runtime SHALL route through the current repair target or create one
  current control-plane blocker.

#### Scenario: Replaced result-submitted packet is no longer current
- **WHEN** a `result_submitted` packet without `accepted_result_id` is replaced
  by a fresh repair packet for the same blocker chain
- **THEN** runtime SHALL mark the replaced packet `superseded_after_repair`
- **AND** active blockers, router next actions, FlowGuard packets, review
  packets, and final-preflight SHALL NOT treat that old packet as current.

### Requirement: PM repair decision packets use one strict result format

FlowPilot SHALL accept PM repair decisions only when the submitted JSON object
contains a top-level allowed `decision` field.

#### Scenario: Nested PM decision wrapper is rejected
- **WHEN** a PM repair decision result places `decision` inside
  `repair_decision` or `pm_repair_decision`
- **THEN** runtime SHALL reject the result as mechanically invalid
- **AND** runtime SHALL NOT translate the nested wrapper into a valid current
  decision.

#### Scenario: Blocked PM decision packet is not reused
- **WHEN** a PM repair decision packet has been blocked, superseded,
  quarantined, or otherwise made noncurrent
- **THEN** runtime SHALL issue a fresh `pm_repair_decision` packet for the
  current blocker
- **AND** `_find_packet`-style lookup SHALL NOT return the old blocked packet.

### Requirement: Control-plane fallback inference is forbidden

FlowPilot SHALL NOT infer missing current responsibility, subject, packet, or
target result from fallback fields or historical artifacts.

#### Scenario: Recovery lacks packet responsibility
- **WHEN** recovery needs a role assignment command for a packet whose current
  envelope lacks responsibility
- **THEN** runtime SHALL report a control-plane blocker
- **AND** runtime SHALL NOT use next-action responsibility or another fallback
  value as the packet responsibility.

### Requirement: Staged effects converge without same-family expansion

FlowPilot SHALL keep a pending staged effect as the reviewable current effect
until it either commits exactly once or blocks as one current same-family
control-plane blocker.

#### Scenario: FlowGuard reviews pending staged effect
- **WHEN** a PM route mutation or node-plan staged effect is pending
- **THEN** FlowGuard SHALL review the pending effect and source result as the
  current artifact
- **AND** FlowGuard SHALL NOT require future committed route-node fields before
  gate closure.

#### Scenario: Same-family staged-effect loop repeats
- **WHEN** the same route node, blocker class, gate/effect kind, and current
  target family repeats without route progress
- **THEN** lifecycle or final-preflight checks SHALL collapse the loop into one
  current control-plane blocker
- **AND** runtime SHALL NOT keep issuing fresh FlowGuard/PM packets solely
  because packet ids changed.

### Requirement: Model and fake/bad packet coverage is current

FlowPilot SHALL include model and test coverage for stale current-target repair
hazards before the repair is considered complete.

#### Scenario: Current-target repair validation
- **WHEN** runtime, prompt, model, or test code changes for this repair
- **THEN** focused FlowGuard model checks, model-test alignment, fake/bad
  packet tests, current runtime tests, historical success replay, install sync
  audit, install check, and topology check SHALL run or be explicitly reported
  with concrete blockers.
