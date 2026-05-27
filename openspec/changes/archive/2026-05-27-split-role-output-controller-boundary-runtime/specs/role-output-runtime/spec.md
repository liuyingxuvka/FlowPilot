## MODIFIED Requirements

### Requirement: Role-output runtime envelope ownership
FlowPilot SHALL submit role-output bodies through runtime-owned envelope,
receipt, and ledger mechanics while preserving controller visibility limits and
public compatibility helper names.

#### Scenario: Controller-boundary confirmation helpers are internally split without changing behavior
- **WHEN** FlowPilot builds or submits the controller-boundary confirmation
  output for a run
- **THEN** the existing role-output runtime facade still exposes the same helper
  names and returns the same body, envelope, receipt, and ledger shapes
- **AND** the child controller-boundary module MUST delegate actual role-output
  submission through the existing runtime submission callback rather than
  owning a separate envelope or ledger path
