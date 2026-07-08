## ADDED Requirements

### Requirement: Repair Guidance Uses Existing Current Paths First
FlowPilot PM repair guidance SHALL use existing blocker, packet, result,
repair, route mutation, and opened-body receipt paths before adding any new
field or repair surface.

#### Scenario: Concrete repair guidance exists in current fields
- **WHEN** a blocking result already carries current structured repair guidance, blocker id, current packet/result ids, evidence refs, or required opened-body receipts
- **THEN** PM repair packets SHALL use those existing current fields
- **AND** the maintenance change SHALL NOT add a duplicate guidance field.

#### Scenario: New guidance field is proposed
- **WHEN** a repair-policy change proposes a new guidance, summary, or read-grant field
- **THEN** FieldLifecycleMesh SHALL prove why existing current paths cannot express the repair
- **AND** ContractExhaustionMesh SHALL generate missing, wrong-type, stale, old-field, and unauthorized cases.
