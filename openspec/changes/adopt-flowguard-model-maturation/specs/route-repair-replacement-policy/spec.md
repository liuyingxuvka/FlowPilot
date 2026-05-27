## ADDED Requirements

### Requirement: Replacement Activation Disposes Old Active Packets
FlowPilot route replacement SHALL explicitly dispose or supersede old active packets before a replacement route branch can become current.

#### Scenario: Old active packet is superseded
- **WHEN** PM activates a replacement branch for an active node or sibling branch
- **THEN** the mutation evidence records every old active packet as superseded, quarantined, migrated, or still blocking with a reason

#### Scenario: Undisposed packet blocks replacement
- **WHEN** a replacement branch is activated while an old active packet remains current without disposition
- **THEN** FlowPilot blocks current-route confidence and requires repair evidence

### Requirement: Replacement Reattaches Parent Evidence
FlowPilot SHALL record parent/child reattachment evidence for replacement branches before final route closure consumes the new branch.

#### Scenario: Replacement branch reattaches to parent
- **WHEN** a replacement branch replaces a child route segment
- **THEN** the parent evidence names the replacement child evidence id, affected sibling scope, stale prior evidence disposition, and replay scope

#### Scenario: Missing reattachment scopes confidence
- **WHEN** the replacement branch has no current parent reattachment evidence
- **THEN** FlowPilot reports scoped confidence instead of full route confidence
