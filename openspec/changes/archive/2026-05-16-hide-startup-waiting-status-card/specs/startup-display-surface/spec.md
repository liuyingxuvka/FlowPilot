## ADDED Requirements

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
Before a canonical route exists, the system SHALL use the startup `FlowPilot
Route Sign` placeholder as the only user-visible route display.

#### Scenario: Startup route placeholder is displayed
- **WHEN** startup display surface status is written before route activation
- **THEN** the user-visible display is the startup `FlowPilot Route Sign` Mermaid placeholder

#### Scenario: Canonical route replaces placeholder
- **WHEN** PM activates a reviewed route as canonical `flow.json`
- **THEN** subsequent route display sync uses the canonical route sign, not startup placeholder semantics
