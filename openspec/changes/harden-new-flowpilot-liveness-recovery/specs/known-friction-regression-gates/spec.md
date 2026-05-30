## ADDED Requirements

### Requirement: Slow-live-agent replacement is a known friction regression gate
FlowPilot SHALL treat premature replacement of a slow but live role as a known friction regression family.

#### Scenario: Regression gate fails before fix
- **WHEN** a test or replay models a slow active lease with current progress and no submitted result yet
- **THEN** a runtime that replaces the lease solely because patrol repeated MUST fail the regression gate.

#### Scenario: Regression gate passes after liveness ladder
- **WHEN** the same slow active lease records progress and later submits a result
- **THEN** the regression gate MUST pass only if the original lease result is accepted and no replacement lease owns the packet.

### Requirement: Accepted-packet reassignment is a known friction regression gate
FlowPilot SHALL treat reassignment of a packet with an accepted result as a known friction regression family.

#### Scenario: Reassignment after accepted result fails
- **WHEN** a packet has `accepted_result_id`
- **AND** the runtime attempts to assign a new active lease to the same packet
- **THEN** the regression gate MUST fail unless the runtime rejects or repairs the assignment before the next action is claimed.
