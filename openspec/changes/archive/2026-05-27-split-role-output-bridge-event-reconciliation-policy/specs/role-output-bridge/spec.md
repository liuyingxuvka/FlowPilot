## MODIFIED Requirements

### Requirement: Router role-output bridge event reconciliation
FlowPilot SHALL reconcile role-output ledger events through router-owned
authority checks while preserving public router facade helper names and
avoiding duplicate state ownership.

#### Scenario: Role-output event reconciliation is internally split without changing behavior
- **WHEN** FlowPilot reconciles startup fact role-output ledgers, material
  review role-output ledgers, or other direct role-output events
- **THEN** the existing role-output bridge facade still exposes the same helper
  names and returns the same reconciliation result shapes
- **AND** the child event module MUST receive the router facade explicitly
  rather than importing the bridge facade or becoming a second router state
  authority
