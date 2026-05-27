# startup-display-surface Specification

## Purpose
TBD - created by archiving change hide-startup-waiting-status-card. Update Purpose after archive.
## Requirements
### Requirement: Startup waiting state is internal-only
When FlowPilot has started but no PM-approved route exists, the system SHALL
keep the waiting-for-PM-route state in internal run records and SHALL NOT emit a
separate `FlowPilot Startup Status` waiting card into the user dialog.

#### Scenario: No PM route exists during startup
- **WHEN** the controller synchronizes display state before any canonical route exists
- **THEN** the sync records the waiting state internally without user-dialog display text for `FlowPilot Startup Status`

#### Scenario: Controller still cannot invent route items
- **WHEN** no PM-approved route exists
- **THEN** the display plan authority remains `none_until_pm_display_plan` and controller-invented route items remain forbidden

### Requirement: Startup Route Sign remains the visible route placeholder
Before a canonical route exists, the system SHALL use the startup `FlowPilot Route Sign` placeholder as the only user-visible route display.

#### Scenario: Startup route placeholder completion is reclaimable
- **WHEN** the startup route placeholder display files and user-dialog display ledger prove the route sign was shown for the current run
- **AND** the matching `write_display_surface_status` Controller receipt is done
- **THEN** Router MUST be able to set `startup_display_status_written=true` during reconciliation even if the action row already says Router-reconciled

#### Scenario: Completed startup display is not reissued
- **WHEN** startup route placeholder display completion has been proven or can be reclaimed from durable evidence
- **THEN** Router MUST NOT issue another ordinary `write_display_surface_status` command for that startup scope
