## ADDED Requirements

### Requirement: Packet results carry semantic outcomes
The new FlowPilot runtime SHALL parse semantic packet outcomes separately from
mechanical envelope validity before applying packet side effects.

#### Scenario: Reviewer block is not accepted as pass
- **WHEN** a reviewer packet result body says the review blocked or failed
- **THEN** the runtime MUST record a non-pass packet outcome
- **AND** the reviewed result MUST NOT be accepted.

#### Scenario: System validation failure is not accepted as pass
- **WHEN** system validation derives a failed outcome from current evidence
- **THEN** the runtime MUST record failed validation evidence
- **AND** the runtime MUST NOT record system closure from that evidence.

#### Scenario: Successful rehearsal bodies use explicit pass outcomes
- **WHEN** a fake or rehearsal packet result body is accepted
- **THEN** the result MUST provide an explicit pass/accept/complete outcome
- **AND** silent compatibility defaults MUST NOT be required for completion.

### Requirement: Non-pass outcomes create active blockers
The runtime SHALL create an active blocker for each reviewer block, system
validation fail, FlowGuard fail, or worker blocked/needs-PM outcome.

#### Scenario: Active blocker records repair owner
- **WHEN** a semantic non-pass outcome is recorded
- **THEN** the blocker MUST identify the packet, subject packet, gate kind,
  owner role, required recheck role, blocker class, recommendation, repair
  generation, and stale evidence ids.

#### Scenario: Failed evidence stays stale until recheck
- **WHEN** a PM repair decision starts a repair for a blocker
- **THEN** the old blocked result or failed validation evidence MUST remain
  stale context
- **AND** it MUST NOT satisfy downstream closure by itself.

### Requirement: PM repair-decision packet resolves semantic blockers
The runtime SHALL issue a PM repair-decision packet for each active semantic
blocker that has no current repair-decision packet.

#### Scenario: PM chooses same-node repair
- **WHEN** a blocker belongs to a route node
- **AND** PM selects `same_node_repair`
- **THEN** the runtime MUST keep the same node active, increment repair
  generation, stale prior node evidence, and issue fresh bounded work.

#### Scenario: PM chooses sender reissue
- **WHEN** PM selects `sender_reissue`
- **THEN** the runtime MUST issue a fresh packet to the original repair target
  role
- **AND** the blocked artifact MUST remain stale context only.

#### Scenario: PM chooses route mutation
- **WHEN** PM selects `mutate_route`
- **THEN** the runtime MUST create a new route version or route-mutation record
  through the existing route mutation primitive
- **AND** affected old evidence MUST become stale.

### Requirement: Same-class recheck clears semantic blockers
The runtime SHALL clear an active semantic blocker only after a current pass
from the required same role/gate class, unless PM records an explicit
authorized waiver.

#### Scenario: Reviewer pass clears reviewer blocker
- **WHEN** a reviewer blocker is active for a subject packet
- **AND** a newer reviewer packet for that same subject records `pass`
- **THEN** the active blocker MAY be marked cleared
- **AND** downstream system validation may proceed.

#### Scenario: PM cannot impersonate reviewer pass
- **WHEN** PM records a repair decision after reviewer block
- **THEN** that PM result MUST NOT clear the reviewer blocker by itself.
