## ADDED Requirements

### Requirement: Relay and receipt packages require mechanical state agreement
The system SHALL include replay packages that prove a controller done receipt
does not count as completion unless the real runtime relay or Router state
mutation it claims can be observed.

#### Scenario: Done receipt without runtime mutation is blocked
- **WHEN** a replay package marks a controller relay, packet delivery, or
  completion action as done but the runtime ledger, envelope, receipt hash, or
  Router state mutation is missing
- **THEN** completion remains blocked and the package is classified as a
  mechanical evidence failure rather than a successful run
