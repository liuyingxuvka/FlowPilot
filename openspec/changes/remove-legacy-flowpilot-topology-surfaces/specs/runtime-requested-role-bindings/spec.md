## MODIFIED Requirements

### Requirement: Runtime binds only requested roles

FlowPilot SHALL create, attach, restore, or replace a role binding only when the current runtime action requires that responsibility. The runtime SHALL NOT preserve old responsibility aliases such as `process_flowguard_operator`, `product_flowguard_operator`, fixed worker cohorts, or fixed six-role recovery as accepted current inputs.

#### Scenario: Lease action binds requested role
- **WHEN** the current runtime action is `lease_agent` for a responsibility
- **THEN** Controller uses a host-supported role mechanism for that responsibility only
- **AND** Controller records the addressable role id returned by the host
- **AND** old Process/Product-scope FlowGuard operator responsibility names are rejected rather than mapped to the current `flowguard_operator` responsibility.

#### Scenario: Unrequested role is not opened
- **WHEN** no current runtime action requires a responsibility
- **THEN** Controller MUST NOT open, restore, or replace that role solely from historical startup topology, chat memory, old role records, or fixed role-count expectations.
