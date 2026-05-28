## ADDED Requirements

### Requirement: Break-glass incidents require recovery disposition
FlowPilot SHALL ensure every opened Controller break-glass incident reaches a
durable recovery, closure, quarantine, or blocked disposition.

#### Scenario: Incident cannot remain open without recovery path
- **WHEN** Controller opens a break-glass incident
- **THEN** the incident MUST eventually reference a recovery transaction,
  validated diagnostic-only closure, quarantine/weak-evidence disposition, or
  explicit human/protocol blocked disposition
- **AND** final status MUST NOT remain open with no recovery path.

#### Scenario: Permanent fix needed requires explicit disposition
- **WHEN** a break-glass patch records `permanent_fix_needed=true`
- **THEN** the incident or patch MUST record whether the permanent fix was
  completed, deferred into a FlowPilot maintenance change, quarantined, or
  blocked
- **AND** `not_run` validation rows MUST include a reason and confidence
  boundary.

#### Scenario: Break-glass does not bypass normal gates
- **WHEN** break-glass records recovery or closure
- **THEN** it MUST NOT approve route gates, read sealed bodies, mutate target
  project scope, or count as normal completion evidence by itself.
