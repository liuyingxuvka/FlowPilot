## MODIFIED Requirements

### Requirement: Parent backward replay uses active child results only
FlowPilot SHALL treat accepted results from active child route nodes as the
current parent replay input and SHALL reject replay inputs that depend on
superseded child nodes.

#### Scenario: Superseded child result is not current replay evidence
- **GIVEN** a parent node originally referenced a child that is now superseded
- **WHEN** parent backward replay is issued
- **THEN** Runtime MUST resolve to the active replacement child before collecting result ids
- **AND** the old child's accepted result MUST NOT appear in `current_repair_child_result_ids`.
- **AND** Reviewer-submitted `child_evidence_refs` MUST match the active child accepted result ids exactly.

#### Scenario: Active replacement result is required
- **GIVEN** an active replacement child has no accepted result
- **WHEN** parent backward replay is requested
- **THEN** Runtime MUST block the replay as missing current child result evidence.
