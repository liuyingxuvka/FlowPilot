## MODIFIED Requirements

### Requirement: Controller receipt effect reconciliation
FlowPilot SHALL reconcile Controller receipt effects through router-owned
receipt helpers that preserve startup bootstrap/run-state authority, receipt
postcondition checks, and compatibility facade helper names.

#### Scenario: Startup bootloader receipt policy is internally split without changing behavior
- **WHEN** FlowPilot applies a startup bootloader Controller receipt after the
  bootloader receipt policy has moved into a child module
- **THEN** the existing receipt-effects facade still exposes the same helper
  names and returns the same applied/not-applied result shapes
- **AND** the child bootloader module MUST receive the router facade explicitly
  rather than importing the receipt-effects facade or becoming a second state
  authority
