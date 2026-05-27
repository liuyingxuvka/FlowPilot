## MODIFIED Requirements

### Requirement: Startup intake materialization consumes a FlowGuard capability child boundary
FlowPilot SHALL keep FlowGuard capability snapshot classification and writing
separately testable from startup intake materialization and deterministic seed
orchestration.

#### Scenario: FlowGuard capability snapshot is internally split without changing startup seed behavior
- **WHEN** deterministic startup seed writes or refreshes FlowGuard capability
  evidence
- **THEN** the startup intake materialization parent still exposes the existing
  helper names
- **AND** the FlowGuard capability child MUST own route classification, import
  snapshot, portable skill route discovery, and snapshot writeback
- **AND** the deterministic seed parent MUST consume the child boundary rather
  than duplicating route classification

#### Scenario: FlowGuard route classification output vocabulary stays closed
- **WHEN** the FlowGuard capability child classifies installed FlowGuard skills
- **THEN** known route families MUST map to the declared model-family fit lists
- **AND** unknown FlowGuard routes MUST remain available as generic
  product/process modeling routes
- **AND** the snapshot MUST avoid hardcoded user paths by recording portable
  search roots
