## ADDED Requirements

### Requirement: PM material disposition closes waits only for the current generation
FlowPilot SHALL close material-scan PM disposition waits only when the accepted disposition belongs to the active current material generation.

#### Scenario: Current-generation disposition closes wait
- **WHEN** PM submits `pm_records_material_scan_result_disposition` through the role-output runtime
- **AND** the disposition batch id, packet ids, result envelope paths, and body hash match the active current material generation
- **THEN** Router MAY complete the registered `result_absorption` control transaction and close the PM disposition wait

#### Scenario: Stale disposition is quarantined
- **WHEN** PM disposition artifacts exist for a superseded material generation
- **THEN** Router MUST NOT mark the current PM disposition wait complete from those artifacts
- **AND** Router MUST quarantine or block the stale artifacts instead of restoring them as current success.
