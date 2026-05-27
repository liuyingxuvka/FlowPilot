## ADDED Requirements

### Requirement: External wait grouping excludes Router-owned postconditions
FlowPilot SHALL NOT include Router-owned internal postconditions in passive
external-event wait groups.

#### Scenario: Internal postcondition remains unsynced
- **WHEN** an expected event is marked as a Router-owned internal
  postcondition
- **AND** its prerequisite flag is satisfied
- **AND** the event flag is still false
- **THEN** Router MUST route the event through internal postcondition
  reconciliation
- **AND** Router MUST NOT create a Controller `await_role_decision` row for
  that event

### Requirement: Manual event compatibility does not change ownership
FlowPilot SHALL keep any idempotent manual external-event recording path for a
Router-owned internal postcondition separate from ownership classification, so
that compatibility path SHALL NOT make the postcondition a role-owned wait.

#### Scenario: Manual capability sync event is replayed
- **WHEN** `capability_evidence_synced` is manually recorded after its source
  artifacts are valid
- **THEN** Router MAY reuse the same capability sync writer
- **AND** repeated recording MUST remain idempotent
- **AND** the event MUST remain excluded from future passive role waits
