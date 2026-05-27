## MODIFIED Requirements

### Requirement: Startup Route Sign remains the visible route placeholder
Before a canonical route exists, the system SHALL use the startup `FlowPilot Route Sign` placeholder as the only user-visible route display.

#### Scenario: Startup route placeholder completion is reclaimable
- **WHEN** the startup route placeholder display files and user-dialog display ledger prove the route sign was shown for the current run
- **AND** the matching `write_display_surface_status` Controller receipt is done
- **THEN** Router MUST be able to set `startup_display_status_written=true` during reconciliation even if the action row already says Router-reconciled

#### Scenario: Completed startup display is not reissued
- **WHEN** startup route placeholder display completion has been proven or can be reclaimed from durable evidence
- **THEN** Router MUST NOT issue another ordinary `write_display_surface_status` command for that startup scope
