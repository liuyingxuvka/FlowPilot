## MODIFIED Requirements

### Requirement: Controller Body-Free Runtime Projection

Controller-facing status and recovery projections SHALL exclude sealed packet
and result body text unless an explicit authorized body-open or terminal summary
path is used.

Authorized reviewer or PM body visibility SHALL NOT be treated as a hard
failure by itself. Hard failures are reserved for controller/default projection
leakage, cross-role execution of body instructions, wrong-authority submission,
or role relabeling.

#### Scenario: Compact status projection redacts sealed bodies

- **GIVEN** a run ledger contains sealed packet and result body text
- **WHEN** the controller requests the default status projection
- **THEN** the output contains envelope metadata, status, hashes, and ids
- **AND** it does not contain sealed body text or body fields
