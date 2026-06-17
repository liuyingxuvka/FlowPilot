## ADDED Requirements

### Requirement: Acceptance Registry TestMesh Parent Gate
FlowPilot SHALL provide a TestMesh parent gate for acceptance-item registry release confidence. The parent gate MUST name child evidence partitions for registry compilation, route-node ownership, node acceptance planning, work-packet projection, PM disposition closure, terminal replay, route mutation recovery, and fake AI payload chaos.

#### Scenario: Parent gate consumes current child evidence
- **WHEN** acceptance-registry release confidence is claimed
- **THEN** the TestMesh parent gate reports every required child partition with current pass evidence or an explicit scoped gap

#### Scenario: Thick parent timeout is not pass evidence
- **WHEN** a broad router or quality-gate command times out or only produces progress output
- **THEN** the parent gate refuses to treat it as passed unless the required child suites have current final result artifacts

### Requirement: Acceptance Item Payload Cells
FlowPilot SHALL model fake AI/work-package payload checks as finite acceptance item cells. The required cells MUST include missing registry, orphan item id, missing route owner, missing node projection, missing worker result item matrix, missing PM disposition closure, stale route item, extra terminal segment, missing terminal segment, duplicate terminal segment, and route mutation item-disposition recovery.

#### Scenario: Missing payload cell blocks broad confidence
- **WHEN** a required acceptance item payload cell has no current child evidence
- **THEN** the parent TestMesh reports the cell as missing and blocks release-scope acceptance-registry confidence

#### Scenario: Known bad payload cell is detected
- **WHEN** fake AI submits an output with a missing, extra, stale, duplicate, or wrong-owner acceptance item or terminal segment field
- **THEN** the relevant child test detects the payload as a block, reissue, or repair path rather than terminal success

### Requirement: Repair Loop Coverage
FlowPilot SHALL prove that acceptance-item repair loops can return to the main route without losing item ownership or creating endless reissue. The proof MUST include reviewer block, PM repair or route redesign, FlowGuard/reviewer recheck, PM disposition, and final terminal replay closure or explicit blocker.

#### Scenario: Reviewer block returns through PM repair
- **WHEN** a reviewer blocks a node or terminal segment because an acceptance item is unresolved
- **THEN** the current repair loop records the blocker, issues the proper PM-owned repair or route redesign work, and returns through required FlowGuard/reviewer evidence before final closure

#### Scenario: Route mutation preserves item disposition
- **WHEN** PM redesigns a route after acceptance-item failure
- **THEN** replacement route nodes own every active acceptance item and old-route items are accepted, blocked, waived, or superseded before terminal closure can pass
