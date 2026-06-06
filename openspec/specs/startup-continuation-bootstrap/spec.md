# startup-continuation-bootstrap Specification

## Purpose
Define the current startup continuation bootstrap after the historical
scheduled-continuation and fixed-role startup path has been removed.

## Requirements
### Requirement: Startup background acknowledgement gates Controller bootstrap
FlowPilot startup SHALL continue only when startup answers use the current
startup field set and record `background_collaboration_authorized=true`.
The native startup UI SHALL record the background-collaboration switch state as
the user's startup answer. A switched-on state is explicit user authorization
for current-run background or parallel agents. A switched-off state is an
explicit startup block, not permission to continue through a foreground-only
route.

#### Scenario: Current startup acknowledgement is present
- **WHEN** startup answers contain `background_collaboration_authorized=true`
- **AND** the startup answer payload contains only current startup fields
- **THEN** Router may materialize deterministic startup artifacts and expose
  `load_controller_core`
- **AND** Router MUST NOT expose historical continuation automation or fixed role-slot
  startup actions.

#### Scenario: Background acknowledgement is disabled or missing
- **WHEN** startup answers omit `background_collaboration_authorized` or record
  it as false
- **THEN** Router records a startup blocker for required background
  collaboration
- **AND** Router MUST NOT expose Controller, PM, route, role, or implementation
  work.
- **AND** Router MUST NOT attempt a foreground-only FlowPilot fallback route.

### Requirement: Startup rejects unsupported continuation fields
FlowPilot SHALL not translate historical startup continuation fields into a
current startup result.

#### Scenario: Old continuation field is submitted
- **WHEN** startup answers include an unsupported continuation or fixed-role
  field
- **THEN** Router rejects the startup result as unsupported current input
- **AND** no current startup field is inferred from that field.

### Requirement: Controller core consumes current startup state
After `load_controller_core`, Controller SHALL consume the current startup
state and reviewer fact-review evidence, not historical continuation or
fixed-role bootstrap
state.

#### Scenario: Controller startup fact review
- **WHEN** Controller enters startup fact review
- **THEN** the startup facts include current background-collaboration
  acknowledgement and current-field mechanical audit evidence
- **AND** no historical continuation binding or fixed role-slot bootstrap evidence is
  required.
