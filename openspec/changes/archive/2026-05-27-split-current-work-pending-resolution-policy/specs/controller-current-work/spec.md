## MODIFIED Requirements

### Requirement: Controller current-work projection
FlowPilot SHALL project current work through router-owned scheduler helpers
that preserve controller-ledger authority, scheduler-row durability checks,
current-work display payloads, and compatibility facade helper names.

#### Scenario: Pending-action resolution policy is internally split without changing behavior
- **WHEN** FlowPilot derives current work for a run whose pending action may be
  open, durably resolved, or better represented by active batch status
- **THEN** the existing current-work facade still exposes the same helper names
  and returns the same owner/projection/resolution result shapes
- **AND** the child pending-resolution module MUST receive the router facade
  explicitly rather than importing the current-work facade or becoming a
  second controller/scheduler state authority
